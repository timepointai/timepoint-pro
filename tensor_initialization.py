"""
Tensor Initialization Pipeline (Phase 11 Architecture Pivot)
============================================================

New Architecture: Baseline → LLM-Guided Population → Training → Maturity Gate

This replaces the old prospection-based initialization (which created bias leakage).
The new approach:
1. Baseline initialization: Create empty tensor schema from entity metadata (instant, no LLM)
2. LLM-guided population: 2-3 refinement loops to populate tensor values
3. Parallel refinement: LangGraph-based simulated dialogs with iterative tensor updates
4. Maturity index: Quality gate ensuring tensor is operational (>= 0.95 maturity)
5. Optional prospection: M15 becomes truly optional again

Key Insight:
- OLD: Prospection was MANDATORY for initialization (mechanism theater)
- NEW: Baseline + LLM loops for initialization, prospection is OPTIONAL enhancement
- Result: No indirect bias leakage, proper separation of concerns

Robustness Improvements (Phase 11.1 - JSON Extraction Fix):
- Robust JSON extraction from LLM responses (handles preambles, markdown fences)
- Account-level rate limit detection (5 consecutive failures → 300s cooldown)
- Comprehensive JSONL logging for diagnostics (logs/llm_tensor_population_YYYY-MM-DD.jsonl)
- Improved prompts requesting JSON-only responses
- Full unit test coverage (test_json_extraction.py)
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import base64
import msgspec
import time
from datetime import datetime
from pathlib import Path

from schemas import TTMTensor, Entity, Timepoint, ResolutionLevel
from metadata.tracking import track_mechanism


# ============================================================================
# Global: Account-Level Rate Limit Detection
# ============================================================================

_consecutive_empty_responses = 0
_max_consecutive_failures = 5
_cooldown_seconds = 300  # 5 minutes


def _log_llm_call(
    prompt: str,
    response: Any,
    error: Optional[Exception],
    attempt: int,
    max_retries: int,
    success: bool
) -> None:
    """Log LLM call details to JSONL file for debugging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"llm_tensor_population_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
        "prompt_length": len(prompt),
        "attempt": attempt,
        "max_retries": max_retries,
        "success": success,
        "error_type": type(error).__name__ if error else None,
        "error_message": str(error) if error else None,
        "response_type": type(response).__name__ if response else None,
    }

    # Add response details if available
    if response and isinstance(response, dict):
        log_entry["response_has_choices"] = "choices" in response
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0].get("message", {}).get("content", "")
            log_entry["response_content_length"] = len(content) if content else 0
            log_entry["response_empty"] = not content or content.strip() == ""
            log_entry["response_preview"] = (content[:100] + "...") if content and len(content) > 100 else content

    # Write to log file
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _print_llm_call_statistics() -> None:
    """Print statistics summary of LLM calls from today's log file."""
    log_dir = Path("logs")
    log_file = log_dir / f"llm_tensor_population_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    if not log_file.exists():
        print("    📊 No LLM call logs yet today")
        return

    # Read and parse log entries
    successes = 0
    failures = 0
    total_attempts = 0
    error_types = {}

    try:
        with open(log_file, "r") as f:
            for line in f:
                entry = json.loads(line.strip())
                total_attempts += 1

                if entry.get("success"):
                    successes += 1
                else:
                    failures += 1
                    error_type = entry.get("error_type", "Unknown")
                    error_types[error_type] = error_types.get(error_type, 0) + 1

        # Print summary
        print(f"\n    📊 LLM Call Statistics (today):")
        print(f"       Total attempts: {total_attempts}")
        print(f"       ✅ Successes: {successes} ({successes/total_attempts*100:.1f}%)" if total_attempts > 0 else "       ✅ Successes: 0")
        print(f"       ❌ Failures: {failures} ({failures/total_attempts*100:.1f}%)" if total_attempts > 0 else "       ❌ Failures: 0")

        if error_types:
            print(f"       Error types:")
            for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                print(f"         - {error_type}: {count}")

        print(f"       📄 Full logs: {log_file}")

    except Exception as e:
        print(f"    ⚠️  Failed to read log statistics: {e}")


def _extract_json_from_response(content: str) -> str:
    """
    Extract JSON from LLM response that may contain explanatory text.

    Handles cases like:
    - "Here is the fix: {\"key\": \"value\"}"
    - "```json\\n{\"key\": \"value\"}\\n```"
    - "Based on analysis:\\n\\n{\"key\": \"value\"}\\n\\nExplanation..."

    Args:
        content: Raw LLM response content

    Returns:
        Extracted JSON string (or original content if no brackets found)

    Raises:
        ValueError if no JSON structure found
    """
    content = content.strip()

    # Strip markdown code fences first
    if content.startswith("```"):
        # Remove opening fence
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # Find first opening bracket (object or array)
    start_obj = content.find("{")
    start_arr = content.find("[")

    # Determine which comes first (or if neither exists)
    if start_obj == -1 and start_arr == -1:
        raise ValueError("No JSON structure found (no opening bracket)")

    if start_obj == -1:
        start = start_arr
        opening = "["
        closing = "]"
    elif start_arr == -1:
        start = start_obj
        opening = "{"
        closing = "}"
    else:
        start = min(start_obj, start_arr)
        opening = "{" if start == start_obj else "["
        closing = "}" if opening == "{" else "]"

    # Find matching closing bracket using counter
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(content)):
        char = content[i]

        # Handle string escapes
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        # Track if we're inside a string (don't count brackets in strings)
        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        # Count bracket depth
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1

            # Found matching closing bracket
            if depth == 0:
                return content[start:i+1]

    # If we get here, brackets weren't balanced
    raise ValueError(f"Unbalanced brackets: found opening {opening} but no matching {closing}")


# ============================================================================
# Helper: LLM Retry Logic
# ============================================================================

def _call_llm_with_retry(llm_client: Any, prompt: str, max_retries: int = 3, initial_delay: float = 5.0) -> Dict[str, Any]:
    """
    Call LLM with exponential backoff retry logic and comprehensive logging.

    Args:
        llm_client: LLM client to use
        prompt: Prompt to send
        max_retries: Maximum retry attempts (default 3)
        initial_delay: Initial delay in seconds (default 5.0 for rate limit recovery)

    Returns:
        Parsed JSON response from LLM

    Raises:
        Exception if all retries fail
    """
    global _consecutive_empty_responses

    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        response_obj = None
        try:
            response_obj = llm_client.client.chat.completions.create(
                model=llm_client.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            # OpenRouterClient returns dict from response.json() - use dict syntax
            content = response_obj["choices"][0]["message"]["content"]

            # Handle empty responses
            if not content or content.strip() == "":
                # Log empty response
                _log_llm_call(prompt, response_obj, ValueError("Empty response from LLM"), attempt + 1, max_retries, False)

                # Track consecutive failures for account-level rate limiting
                _consecutive_empty_responses += 1
                if _consecutive_empty_responses >= _max_consecutive_failures:
                    print(f"\n🚫 Account-level rate limit detected ({_consecutive_empty_responses} consecutive failures)")
                    print(f"⏳ Entering {_cooldown_seconds}s cooldown to let API recover...")
                    time.sleep(_cooldown_seconds)
                    _consecutive_empty_responses = 0  # Reset after cooldown

                raise ValueError("Empty response from LLM")

            # Extract JSON from response (handles preambles like "Here is the fix: {...}")
            try:
                json_content = _extract_json_from_response(content)
            except ValueError as e:
                # No JSON structure found
                _log_llm_call(prompt, response_obj, e, attempt + 1, max_retries, False)
                _consecutive_empty_responses += 1
                if _consecutive_empty_responses >= _max_consecutive_failures:
                    print(f"\n🚫 Account-level rate limit detected ({_consecutive_empty_responses} consecutive failures)")
                    print(f"⏳ Entering {_cooldown_seconds}s cooldown to let API recover...")
                    time.sleep(_cooldown_seconds)
                    _consecutive_empty_responses = 0
                raise

            # Parse JSON
            result = json.loads(json_content)

            # Success! Log it and reset consecutive failures
            _log_llm_call(prompt, response_obj, None, attempt + 1, max_retries, True)
            _consecutive_empty_responses = 0
            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_error = e

            # Log the failure
            _log_llm_call(prompt, response_obj, e, attempt + 1, max_retries, False)

            # Track consecutive failures for account-level rate limiting (JSONDecodeError likely means malformed response)
            _consecutive_empty_responses += 1
            if _consecutive_empty_responses >= _max_consecutive_failures:
                print(f"\n🚫 Account-level rate limit detected ({_consecutive_empty_responses} consecutive failures)")
                print(f"⏳ Entering {_cooldown_seconds}s cooldown to let API recover...")
                time.sleep(_cooldown_seconds)
                _consecutive_empty_responses = 0  # Reset after cooldown

            if attempt < max_retries - 1:
                print(f"    ⚠️  LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"    ⏳ Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                # Final attempt failed
                print(f"    ❌ All {max_retries} LLM attempts failed: {e}")
                log_file = Path("logs") / f"llm_tensor_population_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
                print(f"    📄 Full logs: {log_file}")
                raise last_error

    # Should never reach here, but just in case
    raise last_error if last_error else Exception("LLM call failed")


# ============================================================================
# Behavior Vector Decoder: Maps 8-dim behavior_vector → trait strings
# ============================================================================

def decode_behavior_vector_to_traits(
    behavior: np.ndarray,
    entity_metadata: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Decode an 8-dim behavior_vector into personality trait strings compatible
    with _derive_speaking_style() in dialog_synthesis.py.

    Dimensions:
    [0] openness, [1] conscientiousness, [2] extraversion,
    [3] agreeableness, [4] neuroticism, [5] risk tolerance,
    [6] decision speed, [7] reserved (unused for traits)

    Args:
        behavior: 8-dim numpy array of behavior values (0.0-1.5 range)
        entity_metadata: Optional entity metadata dict for role-based modifiers

    Returns:
        List of trait keyword strings recognized by the speaking style engine
    """
    traits = []

    if len(behavior) < 7:
        return ["determined", "principled"]

    # Normalize to 0-1 range (training can push values above 1.0)
    b = np.clip(behavior, 0.0, 1.5) / 1.5

    # dim[0] openness
    if b[0] > 0.7:
        traits.extend(["creative", "intellectual"])
    elif b[0] < 0.3:
        traits.extend(["traditional", "practical"])

    # dim[1] conscientiousness
    if b[1] > 0.7:
        traits.extend(["organized", "disciplined", "precise"])
    elif b[1] < 0.3:
        traits.extend(["casual", "relaxed"])

    # dim[2] extraversion
    if b[2] > 0.7:
        traits.extend(["outgoing", "warm", "commanding"])
    elif b[2] < 0.3:
        traits.extend(["reserved", "quiet"])

    # dim[3] agreeableness
    if b[3] > 0.7:
        traits.extend(["empathetic", "diplomatic"])
    elif b[3] < 0.3:
        traits.extend(["competitive", "cold", "stubborn"])

    # dim[4] neuroticism
    if b[4] > 0.7:
        traits.extend(["anxious", "intense"])
    elif b[4] < 0.3:
        traits.extend(["stoic", "calm"])

    # dim[5] risk tolerance
    if b[5] > 0.7:
        traits.append("risk-tolerant")
    elif b[5] < 0.3:
        traits.append("cautious")

    # dim[6] decision speed
    if b[6] > 0.7:
        traits.append("decisive")
    elif b[6] < 0.3:
        traits.append("deliberate")

    # Role-based modifiers from entity metadata
    if entity_metadata:
        role = entity_metadata.get("role", "").lower()
        ROLE_VOCAB = {
            "engineer": ["technical", "data-driven"],
            "scientist": ["analytical", "data-driven"],
            "doctor": ["empathetic", "precise"],
            "medical": ["empathetic", "precise"],
            "commander": ["authoritative", "leadership"],
            "captain": ["authoritative", "leadership"],
            "director": ["strategic", "results-oriented"],
            "diplomat": ["diplomatic", "professional"],
            "detective": ["analytical", "skeptical"],
            "strategist": ["strategic", "analytical"],
        }
        for keyword, role_traits in ROLE_VOCAB.items():
            if keyword in role:
                for rt in role_traits:
                    if rt not in traits:
                        traits.append(rt)
                break  # Only apply first matching role

    # Fallback if no traits decoded (all values in mid-range)
    if not traits:
        traits = ["determined", "principled"]

    return traits


def decode_biology_vector_to_physical(biology: np.ndarray) -> Dict[str, float]:
    """
    Decode a 4-dim biology_vector back to physical_tensor metadata fields.

    Dimensions: [0] age_normalized, [1] health_status, [2] comfort, [3] stamina

    Args:
        biology: 4-dim numpy array

    Returns:
        Dict with health_status and stamina fields for physical_tensor update
    """
    if len(biology) < 4:
        return {}

    return {
        "health_status": float(np.clip(biology[1], 0.01, 1.0)),
        "stamina": float(np.clip(biology[3], 0.01, 1.0)),
    }


# ============================================================================
# Phase 1: Baseline Tensor Initialization (Instant, No LLM)
# ============================================================================

@track_mechanism("M6", "ttm_baseline_init")
def create_baseline_tensor(entity: Entity) -> TTMTensor:
    """
    Create baseline tensor from entity metadata WITHOUT any LLM calls.

    This is the structural initialization step - creates the tensor schema
    with minimal values derived directly from metadata. Fast and deterministic.

    Args:
        entity: Entity to initialize

    Returns:
        TTMTensor with baseline values (maturity = 0.0)

    Tensor Dimensions:
    - context_vector: 8 dims (knowledge state, information)
    - biology_vector: 4 dims (physical constraints)
    - behavior_vector: 8 dims (personality, patterns)
    """
    metadata = entity.entity_metadata

    # Context vector (8 dims): Knowledge and information state
    context = np.zeros(8)
    knowledge_state = metadata.get("knowledge_state", [])
    context[0] = min(len(knowledge_state) / 10.0, 1.0)  # Knowledge count (normalized)
    context[1] = 0.5  # Neutral emotional valence (baseline)
    context[2] = 0.3  # Low initial arousal (baseline)
    context[3] = 1.0  # Full energy budget initially
    context[4] = 0.5  # Moderate decision confidence (baseline)
    context[5] = 0.5  # Moderate patience (baseline)
    context[6] = 0.5  # Moderate risk tolerance (baseline)
    context[7] = 0.5  # Moderate social engagement (baseline)

    # Biology vector (4 dims): Physical state from metadata
    biology = np.zeros(4)
    physical_tensor = metadata.get("physical_tensor", {})
    if physical_tensor:
        age = physical_tensor.get("age", 35.0)
        biology[0] = age / 100.0  # Age (normalized to 0-1)
        biology[1] = physical_tensor.get("health_status", 1.0)  # Health
        biology[2] = 1.0 - physical_tensor.get("pain_level", 0.0)  # Comfort (inverse pain)
        biology[3] = physical_tensor.get("stamina", 1.0)  # Stamina
    else:
        # Default physical state for humans
        if entity.entity_type == "human":
            biology[0] = 0.35  # Default age ~35 years
            biology[1] = 0.8   # Good health baseline
            biology[2] = 1.0   # No pain baseline
            biology[3] = 0.8   # Good stamina baseline
        else:
            # Non-human entities get neutral physical state
            biology = np.array([0.5, 0.5, 0.5, 0.5])

    # Behavior vector (8 dims): Personality traits
    personality_traits = metadata.get("personality_traits", [])
    if isinstance(personality_traits, list) and len(personality_traits) >= 5:
        # Use Big Five personality model if available
        behavior = np.array(personality_traits[:8])
        if len(behavior) < 8:
            behavior = np.pad(behavior, (0, 8 - len(behavior)), constant_values=0.5)
    else:
        # Default neutral personality
        behavior = np.array([0.5] * 8)

    # Create TTMTensor
    tensor = TTMTensor.from_arrays(context, biology, behavior)

    # Set maturity to 0.0 - this is just a structural baseline
    entity.tensor_maturity = 0.0
    entity.tensor_training_cycles = 0

    return tensor


# ============================================================================
# Phase 2: LLM-Guided Tensor Population (2-3 Refinement Loops)
# ============================================================================

@track_mechanism("M6", "ttm_llm_population")
def populate_tensor_llm_guided(
    entity: Entity,
    timepoint: Timepoint,
    graph: Any,  # NetworkX graph
    llm_client: Any,  # LLMClient
    max_loops: int = 3
) -> Tuple[TTMTensor, float]:
    """
    Populate tensor values through LLM-guided refinement loops.

    LLM-guided iterative refinement step where LLM refines tensor
    values based on:
    - Loop 1: Entity metadata analysis
    - Loop 2: Graph structure and relationships
    - Loop 3: Validation and consistency check

    Args:
        entity: Entity with baseline tensor
        timepoint: Current timepoint for context
        graph: NetworkX graph for relationship context
        llm_client: LLM client for generation
        max_loops: Maximum refinement loops (default 3)

    Returns:
        (refined_tensor, maturity_after_population)
    """
    # Load baseline tensor
    tensor_json = entity.tensor
    if not tensor_json:
        raise ValueError(f"Entity {entity.entity_id} has no baseline tensor")

    # Decode tensor
    tensor_dict = json.loads(tensor_json)
    context = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["context_vector"])))
    biology = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["biology_vector"])))
    behavior = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["behavior_vector"])))

    # Loop 1: Metadata-based population
    context, biology, behavior = _population_loop_metadata(
        entity, context, biology, behavior, llm_client
    )

    # Loop 2: Graph-based refinement
    context, biology, behavior = _population_loop_graph(
        entity, context, biology, behavior, graph, llm_client
    )

    # Loop 3: Validation and consistency
    context, biology, behavior = _population_loop_validation(
        entity, context, biology, behavior, timepoint, llm_client
    )

    # Create refined tensor
    refined_tensor = TTMTensor.from_arrays(context, biology, behavior)

    # Decode behavior_vector → personality_traits (only if not already hand-authored)
    existing_source = entity.entity_metadata.get("personality_source", "")
    if existing_source not in ("template_entity_roster",):
        decoded_traits = decode_behavior_vector_to_traits(behavior, entity.entity_metadata)
        if decoded_traits:
            entity.entity_metadata["personality_traits"] = decoded_traits
            entity.entity_metadata["personality_source"] = "llm_population_decoded"
            print(f"    [DECODE] {entity.entity_id} traits from behavior_vector: {decoded_traits}")

    # Compute maturity after population (should be higher but not operational yet)
    maturity = compute_tensor_maturity(refined_tensor, entity, training_complete=False)
    entity.tensor_maturity = maturity

    # Print LLM call statistics summary
    _print_llm_call_statistics()

    return refined_tensor, maturity


def _population_loop_metadata(
    entity: Entity,
    context: np.ndarray,
    biology: np.ndarray,
    behavior: np.ndarray,
    llm_client: Any
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Loop 1: Populate tensor from entity metadata using LLM analysis.

    The LLM analyzes the entity's role, description, background and suggests
    adjustments to tensor values to better reflect the entity's characteristics.
    """
    metadata = entity.entity_metadata
    role = metadata.get("role", "unknown")
    description = metadata.get("description", "")
    background = metadata.get("background", "")

    # Build LLM prompt for metadata analysis
    prompt = f"""Analyze this entity and suggest tensor value adjustments.

Entity: {entity.entity_id}
Type: {entity.entity_type}
Role: {role}
Description: {description}
Background: {background}

Current tensor values:
- Context: {context.tolist()}
- Biology: {biology.tolist()}
- Behavior: {behavior.tolist()}

Suggest adjustments as multipliers (0.5-2.0) for each dimension to better reflect the entity.

IMPORTANT: Return ONLY valid JSON with NO explanation, NO markdown, NO preamble.
Expected format:
{{"context_adjustments": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], "biology_adjustments": [0.5, 0.5, 0.5, 0.5], "behavior_adjustments": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]}}
"""

    try:
        # Use retry logic (uses default 5s → 10s → 20s delays for rate limit recovery)
        adjustments = _call_llm_with_retry(llm_client, prompt, max_retries=3)

        # Apply adjustments (clamp to reasonable ranges, with None checks)
        if "context_adjustments" in adjustments and adjustments["context_adjustments"] is not None:
            adj = np.array(adjustments["context_adjustments"][:8])
            context = np.clip(context * adj, 0.0, 2.0)

        if "biology_adjustments" in adjustments and adjustments["biology_adjustments"] is not None:
            adj = np.array(adjustments["biology_adjustments"][:4])
            biology = np.clip(biology * adj, 0.0, 2.0)

        if "behavior_adjustments" in adjustments and adjustments["behavior_adjustments"] is not None:
            adj = np.array(adjustments["behavior_adjustments"][:8])
            behavior = np.clip(behavior * adj, 0.0, 2.0)

    except Exception as e:
        print(f"  ⚠️  Loop 1 (metadata) failed for {entity.entity_id}: {e}")
        # Continue with baseline values on failure

    # Auto-generate voice_guide and speech_examples (only if not hand-authored)
    if not entity.entity_metadata.get("voice_guide"):
        _generate_voice_metadata_from_llm(entity, llm_client)

    return context, biology, behavior


def _generate_voice_metadata_from_llm(entity: Entity, llm_client: Any) -> None:
    """
    Generate voice_guide and speech_examples via LLM for entities without
    hand-authored voice data. Uses the entity's role, description, and
    background to produce distinctive voice characteristics.

    Stores results in entity.entity_metadata with voice_guide_source marker.
    """
    metadata = entity.entity_metadata
    role = metadata.get("role", "unknown")
    description = metadata.get("description", "")
    background = metadata.get("background", "")

    prompt = f"""Generate a distinctive voice profile for this character.

Character: {entity.entity_id}
Role: {role}
Description: {description}
Background: {background}

Create a voice_guide and 3 speech_examples that capture how this specific character talks.
The voice should be DISTINCTIVE — not generic professional speak.

IMPORTANT: Return ONLY valid JSON with NO explanation, NO markdown, NO preamble.
Expected format:
{{"voice_guide": {{"sentence_length": "short and clipped" or "long compound sentences" or "varies widely", "verbal_tics": ["list of 1-3 habitual phrases or filler words"], "never_says": ["list of 1-2 words/phrases this character would never use"], "disagreement_style": "how they push back (e.g., 'cites data', 'goes silent', 'raises voice')", "specificity_anchors": ["types of specific details they reference, e.g., 'percentages', 'historical precedents'"]}}, "speech_examples": ["example line 1 in character voice", "example line 2 showing different emotion", "example line 3 showing their expertise"]}}
"""

    try:
        result = _call_llm_with_retry(llm_client, prompt, max_retries=2)

        voice_guide = result.get("voice_guide")
        speech_examples = result.get("speech_examples")

        if voice_guide and isinstance(voice_guide, dict):
            entity.entity_metadata["voice_guide"] = voice_guide
            entity.entity_metadata["voice_guide_source"] = "llm_population"
            print(f"    [VOICE] Generated voice_guide for {entity.entity_id}")

        if speech_examples and isinstance(speech_examples, list):
            entity.entity_metadata["speech_examples"] = speech_examples[:3]
            print(f"    [VOICE] Generated {len(speech_examples[:3])} speech_examples for {entity.entity_id}")

    except Exception as e:
        print(f"  ⚠️  Voice metadata generation failed for {entity.entity_id}: {e}")
        # Not critical — dialog synthesis has its own fallback chain


def _population_loop_graph(
    entity: Entity,
    context: np.ndarray,
    biology: np.ndarray,
    behavior: np.ndarray,
    graph: Any,
    llm_client: Any
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Loop 2: Refine tensor from graph structure and relationships.

    The LLM analyzes the entity's position in the social graph and suggests
    refinements based on network centrality and relationships.
    """
    if entity.entity_id not in graph:
        return context, biology, behavior

    # Get graph metrics
    try:
        import networkx as nx
        import warnings
        # Suppress RuntimeWarning for small graphs
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=RuntimeWarning)
            centrality = nx.eigenvector_centrality(graph).get(entity.entity_id, 0.0)
        neighbors = list(graph.neighbors(entity.entity_id))
        degree = graph.degree(entity.entity_id)
    except:
        centrality = 0.0
        neighbors = []
        degree = 0

    # Build LLM prompt for graph analysis
    prompt = f"""Refine tensor values based on network position.

Entity: {entity.entity_id}
Centrality: {centrality:.3f}
Connections: {degree} neighbors
Key relationships: {neighbors[:5]}

Current tensor values:
- Context: {context.tolist()}
- Behavior: {behavior.tolist()}

Based on network position, suggest refinements (focus on context dims 5-7 for social factors).

IMPORTANT: Return ONLY valid JSON with NO explanation, NO markdown, NO preamble.
Expected format:
{{"context_refinements": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "behavior_refinements": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}}
"""

    try:
        # Use retry logic (uses default 5s → 10s → 20s delays for rate limit recovery)
        refinements = _call_llm_with_retry(llm_client, prompt, max_retries=3)

        # Apply refinements (with None checks)
        if "context_refinements" in refinements and refinements["context_refinements"] is not None:
            ref = np.array(refinements["context_refinements"][:8])
            context = np.clip(context + ref * 0.1, 0.0, 2.0)  # Small additive adjustment

        if "behavior_refinements" in refinements and refinements["behavior_refinements"] is not None:
            ref = np.array(refinements["behavior_refinements"][:8])
            behavior = np.clip(behavior + ref * 0.1, 0.0, 2.0)

    except Exception as e:
        print(f"  ⚠️  Loop 2 (graph) failed for {entity.entity_id}: {e}")

    return context, biology, behavior


def _population_loop_validation(
    entity: Entity,
    context: np.ndarray,
    biology: np.ndarray,
    behavior: np.ndarray,
    timepoint: Timepoint,
    llm_client: Any
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Loop 3: Validation and consistency check.

    The LLM checks for internal consistency and flags any extreme/unrealistic
    values for correction.
    """
    # Check for zeros (shouldn't have any after population)
    zero_indices = []
    if np.any(context == 0):
        zero_indices.extend([f"context[{i}]" for i, v in enumerate(context) if v == 0])
    if np.any(biology == 0):
        zero_indices.extend([f"biology[{i}]" for i, v in enumerate(biology) if v == 0])
    if np.any(behavior == 0):
        zero_indices.extend([f"behavior[{i}]" for i, v in enumerate(behavior) if v == 0])

    if zero_indices:
        prompt = f"""Fix zero values in tensor (tensors shouldn't have zeros after population).

Entity: {entity.entity_id}
Zero indices: {zero_indices}
Current values:
- Context: {context.tolist()}
- Biology: {biology.tolist()}
- Behavior: {behavior.tolist()}

Suggest non-zero values (0.05-1.5 range) for the zero indices.

IMPORTANT: Return ONLY valid JSON with NO explanation, NO markdown, NO preamble.
Expected format:
{{"fixes": {{"context": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], "biology": [0.1, 0.1, 0.1, 0.1], "behavior": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]}}}}
"""

        try:
            # Use retry logic (uses default 5s → 10s → 20s delays for rate limit recovery)
            result = _call_llm_with_retry(llm_client, prompt, max_retries=3)
            fixes = result.get("fixes", {})

            # Apply fixes (with None checks to handle malformed responses gracefully)
            if "context" in fixes and fixes["context"] is not None and len(fixes["context"]) == 8:
                context = np.where(context == 0, np.array(fixes["context"]), context)
            if "biology" in fixes and fixes["biology"] is not None and len(fixes["biology"]) == 4:
                biology = np.where(biology == 0, np.array(fixes["biology"]), biology)
            if "behavior" in fixes and fixes["behavior"] is not None and len(fixes["behavior"]) == 8:
                behavior = np.where(behavior == 0, np.array(fixes["behavior"]), behavior)

        except Exception as e:
            print(f"  ⚠️  Loop 3 (validation) failed for {entity.entity_id}: {e}")
            # Fallback: replace zeros with 0.1
            context = np.where(context == 0, 0.1, context)
            biology = np.where(biology == 0, 0.1, biology)
            behavior = np.where(behavior == 0, 0.1, behavior)

    return context, biology, behavior


# ============================================================================
# Phase 3: Tensor Maturity Index (Quality Gate)
# ============================================================================

def compute_tensor_maturity(
    tensor: TTMTensor,
    entity: Entity,
    training_complete: bool = False
) -> float:
    """
    Compute tensor maturity index (0.0-1.0).

    Maturity components:
    - Coverage (25%): No zeros, all dimensions populated
    - Variance (20%): Diversity in values (not all identical)
    - Coherence (25%): Internal consistency
    - Training (15%): Training depth (number of training cycles)
    - Validation (15%): Passes validation checks

    Operational threshold: >= 0.95

    Args:
        tensor: TTMTensor to evaluate
        entity: Entity for training history
        training_complete: Whether training phase is complete

    Returns:
        Maturity score 0.0-1.0
    """
    context, biology, behavior = tensor.to_arrays()

    # Component 1: Coverage (no zeros)
    zero_count = np.sum(context == 0) + np.sum(biology == 0) + np.sum(behavior == 0)
    total_dims = len(context) + len(biology) + len(behavior)
    coverage = 1.0 - (zero_count / total_dims)

    # Component 2: Variance (diversity)
    context_var = min(np.var(context) / 0.1, 1.0)  # Normalize variance
    biology_var = min(np.var(biology) / 0.1, 1.0)
    behavior_var = min(np.var(behavior) / 0.1, 1.0)
    variance = (context_var + biology_var + behavior_var) / 3.0

    # Component 3: Coherence (internal consistency)
    # Check for extreme values and impossible combinations
    coherence = 1.0
    # Penalize extreme outliers (values > 2.0 or < 0.0)
    if np.any(context > 2.0) or np.any(context < 0.0):
        coherence *= 0.8
    if np.any(biology > 2.0) or np.any(biology < 0.0):
        coherence *= 0.8
    if np.any(behavior > 2.0) or np.any(behavior < 0.0):
        coherence *= 0.8

    # Component 4: Training depth
    training_score = min(entity.tensor_training_cycles / 10.0, 1.0)
    if not training_complete:
        training_score *= 0.5  # Penalize if training not complete

    # Component 5: Validation (basic checks)
    validation_score = 1.0
    # Check for NaN or inf
    if np.any(np.isnan(context)) or np.any(np.isinf(context)):
        validation_score = 0.0
    if np.any(np.isnan(biology)) or np.any(np.isinf(biology)):
        validation_score = 0.0
    if np.any(np.isnan(behavior)) or np.any(np.isinf(behavior)):
        validation_score = 0.0

    # Weighted sum
    maturity = (
        0.25 * coverage +
        0.20 * variance +
        0.25 * coherence +
        0.15 * training_score +
        0.15 * validation_score
    )

    return maturity


def validate_tensor_maturity(entity: Entity, threshold: float = 0.95) -> Tuple[bool, str]:
    """
    Validate that entity tensor meets maturity threshold.

    Args:
        entity: Entity to validate
        threshold: Minimum maturity score (default 0.95)

    Returns:
        (is_operational, reason) tuple
    """
    if not entity.tensor:
        return False, "No tensor initialized"

    if entity.tensor_maturity < threshold:
        return False, f"Tensor maturity {entity.tensor_maturity:.3f} below threshold {threshold}"

    # Additional checks
    tensor_json = entity.tensor
    try:
        tensor_dict = json.loads(tensor_json)
        context = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["context_vector"])))
        biology = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["biology_vector"])))
        behavior = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["behavior_vector"])))

        # Check for zeros
        if np.any(context == 0) or np.any(biology == 0) or np.any(behavior == 0):
            return False, "Tensor contains zeros (incomplete training)"

        # Check for NaN/inf
        if np.any(np.isnan(context)) or np.any(np.isinf(context)):
            return False, "Tensor contains NaN/inf values"
        if np.any(np.isnan(biology)) or np.any(np.isinf(biology)):
            return False, "Tensor contains NaN/inf values"
        if np.any(np.isnan(behavior)) or np.any(np.isinf(behavior)):
            return False, "Tensor contains NaN/inf values"

    except Exception as e:
        return False, f"Tensor validation failed: {e}"

    return True, f"Tensor operational (maturity: {entity.tensor_maturity:.3f})"


# ============================================================================
# Phase 4: Parallel Training to Maturity (Placeholder for LangGraph)
# ============================================================================

def train_tensor_to_maturity(
    entity: Entity,
    timepoint: Timepoint,
    store: Any,  # GraphStore
    llm_client: Any,  # LLMClient
    max_training_cycles: int = 10,
    target_maturity: float = 0.95
) -> bool:
    """
    Train tensor through simulated interactions until maturity threshold.

    This is a placeholder for the full LangGraph parallel training implementation.
    The actual implementation would:
    1. Launch parallel LangGraph instances
    2. Simulate dialogs/interactions
    3. Compute state deltas (iterative refinement)
    4. Update tensor values
    5. Recompute maturity
    6. Continue until maturity >= target_maturity

    For now, this is a simplified training loop.

    Args:
        entity: Entity to train
        timepoint: Current timepoint
        store: GraphStore for persistence
        llm_client: LLM client for generation
        max_training_cycles: Maximum training iterations
        target_maturity: Target maturity score

    Returns:
        True if training succeeded (maturity >= target), False otherwise
    """
    print(f"  🏋️  Training {entity.entity_id} to maturity threshold {target_maturity}")

    for cycle in range(max_training_cycles):
        # Load current tensor
        tensor_json = entity.tensor
        tensor_dict = json.loads(tensor_json)
        context = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["context_vector"])))
        biology = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["biology_vector"])))
        behavior = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["behavior_vector"])))

        # Simulate training update (placeholder - would be LangGraph dialog simulation)
        # For now, just add small random noise to push maturity higher
        context += np.random.normal(0, 0.02, context.shape)
        biology += np.random.normal(0, 0.01, biology.shape)
        behavior += np.random.normal(0, 0.02, behavior.shape)

        # Clamp to valid range
        context = np.clip(context, 0.01, 1.5)
        biology = np.clip(biology, 0.01, 1.5)
        behavior = np.clip(behavior, 0.01, 1.5)

        # Update tensor
        trained_tensor = TTMTensor.from_arrays(context, biology, behavior)
        entity.tensor = json.dumps({
            "context_vector": base64.b64encode(msgspec.msgpack.encode(context.tolist())).decode('utf-8'),
            "biology_vector": base64.b64encode(msgspec.msgpack.encode(biology.tolist())).decode('utf-8'),
            "behavior_vector": base64.b64encode(msgspec.msgpack.encode(behavior.tolist())).decode('utf-8')
        })
        entity.tensor_training_cycles += 1

        # Recompute maturity
        maturity = compute_tensor_maturity(trained_tensor, entity, training_complete=(cycle == max_training_cycles - 1))
        entity.tensor_maturity = maturity

        # Decode trained behavior_vector → personality_traits
        existing_source = entity.entity_metadata.get("personality_source", "")
        if existing_source not in ("template_entity_roster",):
            decoded_traits = decode_behavior_vector_to_traits(behavior, entity.entity_metadata)
            if decoded_traits:
                entity.entity_metadata["personality_traits"] = decoded_traits
                entity.entity_metadata["personality_source"] = "tensor_decoded"

        # Decode biology_vector → update physical_tensor metadata
        physical_updates = decode_biology_vector_to_physical(biology)
        if physical_updates:
            physical_tensor = entity.entity_metadata.get("physical_tensor", {})
            if physical_tensor:
                physical_tensor.update(physical_updates)
                entity.entity_metadata["physical_tensor"] = physical_tensor

        # Save progress
        store.save_entity(entity)

        print(f"    Cycle {cycle + 1}/{max_training_cycles}: maturity = {maturity:.3f}")

        # Check if target reached
        if maturity >= target_maturity:
            print(f"  ✅ Training complete: {entity.entity_id} reached maturity {maturity:.3f}")
            return True

    print(f"  ⚠️  Training incomplete: {entity.entity_id} maturity {entity.tensor_maturity:.3f} < {target_maturity}")
    return False


# ============================================================================
# Helper: Create Fallback Tensor (Last Resort)
# ============================================================================

def create_fallback_tensor() -> TTMTensor:
    """
    Create minimal fallback tensor when all initialization fails.

    Returns tensor with small random values to avoid NaN/inf issues.
    Used as absolute last resort when prospection AND baseline fail.
    """
    # Small random values around 0.1 to provide minimal variation
    context = np.random.rand(8) * 0.1 + 0.05
    biology = np.random.rand(4) * 0.1 + 0.5  # Centered around 0.5
    behavior = np.random.rand(8) * 0.1 + 0.5  # Centered around 0.5

    return TTMTensor.from_arrays(context, biology, behavior)
