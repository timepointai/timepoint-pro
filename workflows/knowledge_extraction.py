# ============================================================================
# workflows/knowledge_extraction.py - M19 Knowledge Extraction Agent
# ============================================================================
"""
LLM-based knowledge extraction from dialog turns.

Replaces the naive capitalization-based extraction with an intelligent agent
that understands semantic meaning and extracts only valuable knowledge items.

The agent is passed:
1. The dialog turns to analyze
2. Causal graph context (what knowledge already exists)
3. Entity metadata (who is speaking, who is listening)

It returns structured KnowledgeItem objects with:
- Semantic content (complete thoughts, not single words)
- Speaker/listener attribution
- Category (fact, decision, opinion, plan, revelation, question, agreement)
- Confidence and causal relevance scores

This is mechanism M19 in the MECHANICS.md documentation.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import json
import logging

from schemas import KnowledgeItem, KnowledgeExtractionResult, DialogTurn, Entity
from llm_service.model_selector import ActionType, select_model_for_action, get_fallback_models
from metadata.tracking import track_mechanism

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic models for LLM structured output
# ============================================================================

class ExtractedKnowledge(BaseModel):
    """Single knowledge item as extracted by the LLM agent."""
    content: str = Field(description="The complete semantic knowledge unit (not a single word)")
    speaker: str = Field(description="Entity ID who communicated this knowledge")
    category: str = Field(description="One of: fact, decision, opinion, plan, revelation, question, agreement")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="How confident the extraction is")
    causal_relevance: float = Field(default=0.5, ge=0.0, le=1.0, description="How important for causal chains")
    context: Optional[str] = Field(default=None, description="Why this knowledge matters")
    source_turn_index: Optional[int] = Field(default=None, description="Which turn (0-indexed)")


class KnowledgeExtractionResponse(BaseModel):
    """LLM response for knowledge extraction."""
    items: List[ExtractedKnowledge] = Field(default_factory=list, description="Extracted knowledge items")
    reasoning: Optional[str] = Field(default="", description="Brief reasoning about what was extracted and why")
    skipped_content: Optional[Any] = Field(default=None, description="Content that was intentionally not extracted")

    @field_validator("skipped_content", mode="before")
    @classmethod
    def coerce_skipped_content(cls, v):
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return v


# ============================================================================
# Helper functions for JSON parsing
# ============================================================================

def extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling edge cases.

    Handles:
    - Clean JSON responses
    - JSON wrapped in markdown code blocks
    - Reasoning model output with thinking before JSON
    - Multiple JSON objects (takes last one)

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    import re

    if not text or not text.strip():
        return None

    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try removing markdown code blocks
    if "```json" in text:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    if "```" in text:
        match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # Try to find JSON object in text (for reasoning models)
    # Look for the last complete JSON object
    brace_count = 0
    json_start = -1
    json_end = -1

    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                json_start = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and json_start >= 0:
                json_end = i + 1
                # Don't break - keep looking for later JSON objects

    if json_start >= 0 and json_end > json_start:
        try:
            return json.loads(text[json_start:json_end])
        except json.JSONDecodeError:
            pass

    return None


def parse_extraction_response_manual(text: str, entity_ids: List[str]) -> KnowledgeExtractionResponse:
    """
    Manually parse extraction response with fallbacks.

    Args:
        text: Raw LLM response
        entity_ids: Valid entity IDs for validation

    Returns:
        KnowledgeExtractionResponse with extracted items
    """
    data = extract_json_from_response(text)

    if not data:
        logger.warning("[M19] Could not extract JSON from response")
        return KnowledgeExtractionResponse(items=[], reasoning="JSON parsing failed")

    # Handle items array
    items = []
    raw_items = data.get("items", [])
    if isinstance(raw_items, list):
        for raw_item in raw_items:
            if isinstance(raw_item, dict):
                try:
                    # Validate and normalize the item
                    item = ExtractedKnowledge(
                        content=raw_item.get("content", ""),
                        speaker=raw_item.get("speaker", "unknown"),
                        category=raw_item.get("category", "fact"),
                        confidence=float(raw_item.get("confidence", 0.9)),
                        causal_relevance=float(raw_item.get("causal_relevance", 0.5)),
                        context=raw_item.get("context"),
                        source_turn_index=raw_item.get("source_turn_index")
                    )
                    # Only keep items with meaningful content
                    if item.content and len(item.content) > 10:
                        items.append(item)
                except Exception as e:
                    logger.debug(f"[M19] Skipping invalid item: {e}")

    return KnowledgeExtractionResponse(
        items=items,
        reasoning=data.get("reasoning", ""),
        skipped_content=data.get("skipped_content")
    )


# ============================================================================
# Core extraction functions
# ============================================================================

def build_causal_context(
    entities: List[Entity],
    store: Optional['GraphStore'] = None,
    limit_per_entity: int = 10
) -> str:
    """
    Build causal graph context for the knowledge extraction agent.

    This gives the agent awareness of what knowledge already exists so it can:
    1. Avoid redundant extraction (same facts already known)
    2. Recognize novel information (new facts worth storing)
    3. Understand semantic relationships (related concepts)

    Args:
        entities: Entities involved in the dialog
        store: GraphStore for retrieving existing exposure events
        limit_per_entity: Max events per entity to include

    Returns:
        Formatted string describing existing knowledge state
    """
    if not store:
        return "No prior knowledge available (new simulation)."

    context_parts = []

    for entity in entities:
        entity_id = entity.entity_id

        # Get recent exposure events for this entity
        try:
            exposure_events = store.get_exposure_events(entity_id, limit=limit_per_entity)
            if exposure_events:
                knowledge_items = [f"- {exp.information}" for exp in exposure_events[:limit_per_entity]]
                context_parts.append(f"**{entity_id}** already knows:\n" + "\n".join(knowledge_items))
        except Exception as e:
            logger.debug(f"Could not retrieve exposures for {entity_id}: {e}")

        # Also include static knowledge from metadata
        static_knowledge = entity.entity_metadata.get("knowledge_state", [])
        if static_knowledge:
            static_items = static_knowledge[:5]  # Limit static knowledge
            if static_items:
                context_parts.append(f"**{entity_id}** background knowledge:\n" + "\n".join(f"- {k}" for k in static_items))

    if not context_parts:
        return "This is the first interaction - no prior knowledge in the system."

    return "\n\n".join(context_parts)


def build_extraction_prompt(
    dialog_turns: List[Dict[str, Any]],
    entities: List[Entity],
    causal_context: str,
    timepoint_description: str
) -> str:
    """
    Build the prompt for the knowledge extraction agent.

    Args:
        dialog_turns: List of dialog turns (dicts with speaker, content, etc.)
        entities: Entities participating in the dialog
        causal_context: Prior knowledge context from build_causal_context
        timepoint_description: Description of the scene/event

    Returns:
        Complete prompt string for the LLM
    """
    # Format dialog turns
    dialog_text = []
    for i, turn in enumerate(dialog_turns):
        speaker = turn.get("speaker", "Unknown")
        content = turn.get("content", turn.get("text", ""))
        dialog_text.append(f"[Turn {i}] {speaker}: {content}")

    dialog_formatted = "\n".join(dialog_text)

    # Build entity context
    entity_info = []
    for entity in entities:
        traits = entity.entity_metadata.get("personality_traits", [])
        goals = entity.entity_metadata.get("current_goals", [])
        entity_info.append(f"- {entity.entity_id}: traits={traits[:3]}, goals={goals[:2]}")

    entity_context = "\n".join(entity_info) if entity_info else "No entity metadata available."

    # Determine listeners (all entities except speaker for each turn)
    entity_ids = [e.entity_id for e in entities]

    prompt = f"""You are a Knowledge Extraction Agent. Your task is to extract MEANINGFUL knowledge items from dialog.

## CRITICAL RULES - READ CAREFULLY

1. **EXTRACT COMPLETE SEMANTIC UNITS** - Not single words!
   - BAD: "thanks", "what", "Michael", "we'll"
   - GOOD: "Michael believes the project deadline is unrealistic"
   - GOOD: "The board approved the $2M budget increase"

2. **ONLY extract information that was TRANSFERRED**
   - Someone learned something new
   - A decision was communicated
   - An opinion was expressed and received
   - A plan was shared

3. **DO NOT extract:**
   - Greetings, pleasantries, filler words
   - Sentence fragments without meaning
   - Single names without context
   - Contractions or common words (I'll, we're, that's)
   - Questions without answers (unless the question itself reveals information)

4. **Categories explained:**
   - **fact**: Verifiable information shared (e.g., "The meeting is at 3pm")
   - **decision**: A choice that was made and communicated
   - **opinion**: A subjective view expressed by someone
   - **plan**: Intended future action shared
   - **revelation**: New information that changes understanding
   - **question**: Only if the question itself reveals important information
   - **agreement**: Consensus reached between parties

## SCENE CONTEXT
{timepoint_description}

## PARTICIPANTS
{entity_context}

## PRIOR KNOWLEDGE (avoid redundant extraction)
{causal_context}

## DIALOG TO ANALYZE
{dialog_formatted}

## YOUR TASK
Extract 0-5 knowledge items per dialog turn. It's okay to extract NOTHING if a turn has no meaningful knowledge transfer.

For each item, provide:
- content: The complete semantic knowledge (a full thought/statement)
- speaker: Who communicated this
- category: One of fact, decision, opinion, plan, revelation, question, agreement
- confidence: 0.0-1.0 (how confident you are this is real knowledge transfer)
- causal_relevance: 0.0-1.0 (how important for understanding the causal chain of events)
- context: Brief note on why this matters (optional)
- source_turn_index: Which turn number this came from

Available listeners for each turn: {entity_ids}

Return a JSON object with:
- items: array of extracted knowledge items (can be empty if no real knowledge)
- reasoning: Brief explanation of what you extracted and why
- skipped_content: Note any content intentionally skipped
"""

    return prompt


@track_mechanism("M19", "knowledge_extraction")
def extract_knowledge_from_dialog(
    dialog_turns: List[Dict[str, Any]],
    entities: List[Entity],
    timepoint: 'Timepoint',
    llm: 'LLMClient',
    store: Optional['GraphStore'] = None,
    dialog_id: Optional[str] = None
) -> KnowledgeExtractionResult:
    """
    Extract knowledge items from dialog using LLM-based agent.

    This is the main entry point for M19 knowledge extraction.

    Args:
        dialog_turns: List of dialog turn dicts (speaker, content, timestamp, etc.)
        entities: Entities participating in the dialog
        timepoint: The timepoint context for this dialog
        llm: LLM client for making extraction calls
        store: GraphStore for causal context retrieval
        dialog_id: Optional dialog ID for tracking

    Returns:
        KnowledgeExtractionResult with extracted items and metadata
    """
    # Models known to be unavailable on OpenRouter (removed or deprecated)
    KNOWN_UNAVAILABLE = {
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-70b-versatile",
        "groq/llama-3.1-8b-instant",
        "groq/mixtral-8x7b-32768",
    }

    # Get fallback chain for robust model selection
    # This prevents failures when the primary model is unavailable
    model_fallback_chain = get_fallback_models(ActionType.KNOWLEDGE_EXTRACTION, chain_length=3)
    # Filter out known-unavailable models
    model_fallback_chain = [m for m in model_fallback_chain if m not in KNOWN_UNAVAILABLE]
    # Ensure we always have at least one valid model
    if not model_fallback_chain:
        model_fallback_chain = ["meta-llama/llama-3.1-70b-instruct"]
    model = model_fallback_chain[0]

    # Build causal context from existing knowledge
    causal_context = build_causal_context(entities, store)

    # Build extraction prompt
    timepoint_description = getattr(timepoint, 'event_description', 'Unknown event')
    prompt = build_extraction_prompt(
        dialog_turns=dialog_turns,
        entities=entities,
        causal_context=causal_context,
        timepoint_description=timepoint_description
    )

    # Call LLM for extraction
    logger.info(f"[M19] Extracting knowledge from {len(dialog_turns)} dialog turns")

    try:
        response = llm.generate_structured(
            prompt=prompt,
            response_model=KnowledgeExtractionResponse,
            model=model,
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=4000
        )

        # Get entity IDs for listener assignment
        entity_ids = [e.entity_id for e in entities]

        # Convert to KnowledgeItem objects with listener assignment
        knowledge_items = []
        for item in response.items:
            # Listeners are all entities except the speaker
            listeners = [eid for eid in entity_ids if eid != item.speaker]

            knowledge_items.append(KnowledgeItem(
                content=item.content,
                speaker=item.speaker,
                listeners=listeners,
                category=item.category,
                confidence=item.confidence,
                context=item.context,
                source_turn_index=item.source_turn_index,
                causal_relevance=item.causal_relevance
            ))

        # Log extraction results
        if knowledge_items:
            logger.info(f"[M19] Extracted {len(knowledge_items)} knowledge items")
            for ki in knowledge_items[:3]:  # Log first 3 for debugging
                logger.debug(f"  - [{ki.category}] {ki.content[:60]}...")
        else:
            logger.info("[M19] No meaningful knowledge extracted (may be normal for casual dialog)")

        if response.reasoning:
            logger.debug(f"[M19] Reasoning: {response.reasoning}")

        # Build result
        items_per_turn = len(knowledge_items) / max(1, len(dialog_turns))

        return KnowledgeExtractionResult(
            items=knowledge_items,
            dialog_id=dialog_id or f"dialog_{timepoint.timepoint_id}",
            timepoint_id=timepoint.timepoint_id,
            extraction_model=model,
            total_turns_analyzed=len(dialog_turns),
            items_per_turn=items_per_turn,
            extraction_timestamp=datetime.now()
        )

    except Exception as e:
        logger.warning(f"[M19] Structured extraction failed with model '{model}': {e}")

        # Try fallback models from the chain
        for fallback_model in model_fallback_chain[1:]:  # Skip first model (already tried)
            logger.info(f"[M19] Trying fallback model: {fallback_model}")
            try:
                response = llm.generate_structured(
                    prompt=prompt,
                    response_model=KnowledgeExtractionResponse,
                    model=fallback_model,
                    temperature=0.3,
                    max_tokens=4000
                )

                # Convert to KnowledgeItem objects
                entity_ids = [e.entity_id for e in entities]
                knowledge_items = []
                for item in response.items:
                    listeners = [eid for eid in entity_ids if eid != item.speaker]
                    knowledge_items.append(KnowledgeItem(
                        content=item.content,
                        speaker=item.speaker,
                        listeners=listeners,
                        category=item.category,
                        confidence=item.confidence,
                        context=item.context,
                        source_turn_index=item.source_turn_index,
                        causal_relevance=item.causal_relevance
                    ))

                if knowledge_items:
                    logger.info(f"[M19] Fallback model '{fallback_model}' extracted {len(knowledge_items)} items")
                    items_per_turn = len(knowledge_items) / max(1, len(dialog_turns))
                    return KnowledgeExtractionResult(
                        items=knowledge_items,
                        dialog_id=dialog_id or f"dialog_{timepoint.timepoint_id}",
                        timepoint_id=timepoint.timepoint_id,
                        extraction_model=fallback_model,
                        total_turns_analyzed=len(dialog_turns),
                        items_per_turn=items_per_turn,
                        extraction_timestamp=datetime.now()
                    )
                else:
                    # Empty result is valid (casual dialog may have no knowledge)
                    return KnowledgeExtractionResult(
                        items=[],
                        dialog_id=dialog_id or f"dialog_{timepoint.timepoint_id}",
                        timepoint_id=timepoint.timepoint_id,
                        extraction_model=fallback_model,
                        total_turns_analyzed=len(dialog_turns),
                        items_per_turn=0.0,
                        extraction_timestamp=datetime.now()
                    )

            except Exception as fallback_error:
                logger.warning(f"[M19] Fallback model '{fallback_model}' also failed: {fallback_error}")
                continue  # Try next fallback

        # All structured calls failed - try raw LLM call with manual parsing
        logger.warning(f"[M19] All structured models failed, trying raw LLM call with manual parser...")
        try:
            # Use a safe default model for raw call
            raw_model = "meta-llama/llama-3.1-70b-instruct"
            raw_response = llm.client.chat.completions.create(
                model=raw_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000
            )
            raw_text = raw_response["choices"][0]["message"]["content"]

            # Use manual parser
            entity_ids = [e.entity_id for e in entities]
            response = parse_extraction_response_manual(raw_text, entity_ids)

            # Convert to KnowledgeItem objects
            knowledge_items = []
            for item in response.items:
                listeners = [eid for eid in entity_ids if eid != item.speaker]
                knowledge_items.append(KnowledgeItem(
                    content=item.content,
                    speaker=item.speaker,
                    listeners=listeners,
                    category=item.category,
                    confidence=item.confidence,
                    context=item.context,
                    source_turn_index=item.source_turn_index,
                    causal_relevance=item.causal_relevance
                ))

            if knowledge_items:
                logger.info(f"[M19] Raw LLM call + manual parser extracted {len(knowledge_items)} items")
                items_per_turn = len(knowledge_items) / max(1, len(dialog_turns))
                return KnowledgeExtractionResult(
                    items=knowledge_items,
                    dialog_id=dialog_id or f"dialog_{timepoint.timepoint_id}",
                    timepoint_id=timepoint.timepoint_id,
                    extraction_model=raw_model,
                    total_turns_analyzed=len(dialog_turns),
                    items_per_turn=items_per_turn,
                    extraction_timestamp=datetime.now()
                )
        except Exception as raw_error:
            logger.error(f"[M19] Raw LLM fallback also failed: {raw_error}")

        # Return empty result on total failure (graceful degradation)
        logger.error(f"[M19] Knowledge extraction completely failed")
        return KnowledgeExtractionResult(
            items=[],
            dialog_id=dialog_id or f"dialog_{timepoint.timepoint_id}",
            timepoint_id=timepoint.timepoint_id,
            extraction_model=model,
            total_turns_analyzed=len(dialog_turns),
            items_per_turn=0.0,
            extraction_timestamp=datetime.now()
        )


def create_exposure_events_from_knowledge(
    extraction_result: KnowledgeExtractionResult,
    timepoint: 'Timepoint',
    store: Optional['GraphStore'] = None
) -> int:
    """
    Create exposure events from extracted knowledge items.

    This connects M19 (Knowledge Extraction) -> M3 (Exposure Events) by
    creating proper exposure records for each listener.

    Args:
        extraction_result: Result from extract_knowledge_from_dialog
        timepoint: Timepoint context
        store: GraphStore to save exposure events

    Returns:
        Number of exposure events created
    """
    if not store:
        logger.debug("[M19->M3] No store provided, skipping exposure event creation")
        return 0

    if not extraction_result.items:
        logger.debug("[M19->M3] No knowledge items to create exposures for")
        return 0

    # Import here to avoid circular imports
    from workflows.dialog_synthesis import create_exposure_event

    events_created = 0
    timestamp = getattr(timepoint, 'timestamp', datetime.now())

    for item in extraction_result.items:
        # Create exposure for each listener
        for listener in item.listeners:
            create_exposure_event(
                entity_id=listener,
                information=item.content,
                source=item.speaker,
                event_type="told",  # All dialog knowledge is "told"
                timestamp=timestamp,
                confidence=item.confidence,
                store=store,
                timepoint_id=timepoint.timepoint_id
            )
            events_created += 1

    logger.info(f"[M19->M3] Created {events_created} exposure events from {len(extraction_result.items)} knowledge items")
    return events_created


# ============================================================================
# Utility functions
# ============================================================================

def filter_high_relevance_knowledge(
    items: List[KnowledgeItem],
    min_relevance: float = 0.6
) -> List[KnowledgeItem]:
    """Filter knowledge items by causal relevance threshold."""
    return [item for item in items if item.causal_relevance >= min_relevance]


def get_knowledge_by_category(
    items: List[KnowledgeItem],
    category: str
) -> List[KnowledgeItem]:
    """Get knowledge items of a specific category."""
    return [item for item in items if item.category == category]


def summarize_extraction_result(result: KnowledgeExtractionResult) -> str:
    """Generate a human-readable summary of extraction results."""
    if not result.items:
        return f"No knowledge extracted from {result.total_turns_analyzed} dialog turns."

    # Count by category
    categories = {}
    for item in result.items:
        categories[item.category] = categories.get(item.category, 0) + 1

    category_summary = ", ".join(f"{cat}: {count}" for cat, count in sorted(categories.items()))

    return (
        f"Extracted {len(result.items)} knowledge items from {result.total_turns_analyzed} turns "
        f"({result.items_per_turn:.2f} items/turn). Categories: {category_summary}"
    )
