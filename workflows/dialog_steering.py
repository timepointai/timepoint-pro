# ============================================================================
# workflows/dialog_steering.py - Per-Turn Dialog Generation with LangGraph
# ============================================================================
"""
LangGraph-based per-character dialog generation with steering agent.

Three nodes + routing:
  steering_node: Selects next speaker, evaluates narrative, injects mood shifts
  character_node: Generates ONE dialog turn for current_speaker
  quality_gate_node: Semantic quality evaluation (configurable per-turn or per-dialog)

Flow: steering -> character -> quality_gate -> (steering | END | retry)

Also contains semantic quality gates (Component 6) that replace surface-level
checks with frontier model evaluation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging
import copy

from metadata.tracking import track_mechanism
from schemas import DialogState

logger = logging.getLogger(__name__)


# ============================================================================
# Semantic Quality Gates (Component 6)
# ============================================================================

@dataclass
class SemanticQualityResult:
    """Result of semantic quality evaluation."""
    narrative_goals_advanced: bool = False
    specific_disagreement_present: bool = False
    character_voices_distinct: bool = False
    narrative_advancement_score: float = 0.0
    conflict_specificity_score: float = 0.0
    voice_distinctiveness_score: float = 0.0
    evaluation_text: str = ""
    passed: bool = True
    failures: List[str] = field(default_factory=list)


def evaluate_dialog_semantically(
    turns: List[Dict[str, Any]],
    narrative_goals: List[str],
    contexts: Dict[str, Any],
    llm: 'LLMClient',
    model: Optional[str] = None,
) -> SemanticQualityResult:
    """
    Per-dialog semantic quality evaluation.

    Checks: Did this advance narrative goals? Is there specific disagreement?
    Are character voices distinct?

    Uses a frontier model call to evaluate rather than surface heuristics.
    """
    if not turns or len(turns) < 2:
        return SemanticQualityResult(passed=True)

    # Build evaluation prompt
    turns_text = "\n".join(
        f"  {t.get('speaker', '?')}: {t.get('content', '')[:200]}"
        for t in turns
    )
    goals_text = "\n".join(f"  - {g}" for g in narrative_goals) if narrative_goals else "  (none specified)"

    system_prompt = (
        "You are a dialog quality evaluator. Analyze the dialog and return a JSON "
        "object with scores. Be rigorous — most dialog fails at least one check."
    )
    user_prompt = f"""Evaluate this dialog:

DIALOG:
{turns_text}

NARRATIVE GOALS:
{goals_text}

Score each dimension 0.0-1.0 and explain:
1. narrative_advancement: Did the dialog move the story forward? New information revealed? Decisions made?
2. conflict_specificity: Are disagreements specific (naming numbers, dates, consequences) or vague platitudes?
3. voice_distinctiveness: Could you identify speakers without labels? Different sentence lengths, vocabulary, tone?

Return JSON:
{{
  "narrative_advancement_score": float,
  "conflict_specificity_score": float,
  "voice_distinctiveness_score": float,
  "narrative_goals_advanced": boolean,
  "specific_disagreement_present": boolean,
  "character_voices_distinct": boolean,
  "evaluation_text": "brief explanation",
  "failures": ["list of specific failures"]
}}"""

    try:
        response = llm.service.call(
            system=system_prompt,
            user=user_prompt,
            temperature=0.1,
            max_tokens=500,
            model=model,
            call_type="dialog_quality_semantic",
        )

        if response.success:
            parsed = json.loads(response.content)
            failures = parsed.get("failures", [])
            scores = [
                parsed.get("narrative_advancement_score", 0.5),
                parsed.get("conflict_specificity_score", 0.5),
                parsed.get("voice_distinctiveness_score", 0.5),
            ]
            passed = all(s >= 0.4 for s in scores) and len(failures) < 2

            return SemanticQualityResult(
                narrative_goals_advanced=parsed.get("narrative_goals_advanced", False),
                specific_disagreement_present=parsed.get("specific_disagreement_present", False),
                character_voices_distinct=parsed.get("character_voices_distinct", False),
                narrative_advancement_score=parsed.get("narrative_advancement_score", 0.5),
                conflict_specificity_score=parsed.get("conflict_specificity_score", 0.5),
                voice_distinctiveness_score=parsed.get("voice_distinctiveness_score", 0.5),
                evaluation_text=parsed.get("evaluation_text", ""),
                passed=passed,
                failures=failures,
            )
    except Exception as e:
        logger.warning(f"Semantic quality evaluation failed: {e}")

    return SemanticQualityResult(passed=True, evaluation_text="evaluation_skipped")


def evaluate_cross_dialog_progression(
    current_turns: List[Dict[str, Any]],
    prior_beats: Optional[List[str]],
    llm: 'LLMClient',
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cross-dialog progression check.

    Does the dialog sequence show progression? Are themes developing?
    """
    if not prior_beats:
        return {"progression_detected": True, "score": 1.0, "notes": "first_dialog"}

    beats_text = "\n".join(f"  - {b}" for b in prior_beats[-5:])
    current_text = "\n".join(
        f"  {t.get('speaker', '?')}: {t.get('content', '')[:100]}"
        for t in current_turns[:5]
    )

    system_prompt = "You evaluate narrative progression between dialogs."
    user_prompt = f"""PREVIOUS DIALOG BEATS:
{beats_text}

CURRENT DIALOG:
{current_text}

Does the current dialog advance beyond the previous beats? Score 0.0-1.0.
Return JSON: {{"progression_detected": bool, "score": float, "notes": "explanation"}}"""

    try:
        response = llm.service.call(
            system=system_prompt,
            user=user_prompt,
            temperature=0.1,
            max_tokens=200,
            model=model,
            call_type="dialog_quality_semantic",
        )
        if response.success:
            return json.loads(response.content)
    except Exception as e:
        logger.warning(f"Cross-dialog progression check failed: {e}")

    return {"progression_detected": True, "score": 0.5, "notes": "evaluation_failed"}


def evaluate_full_run_coherence(
    all_dialog_summaries: List[str],
    llm: 'LLMClient',
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full-run coherence check. Called once after all dialogs.

    Does the complete chain tell a coherent story?
    """
    if not all_dialog_summaries:
        return {"coherent": True, "score": 1.0, "notes": "no_dialogs"}

    summaries_text = "\n".join(
        f"  {i+1}. {s}" for i, s in enumerate(all_dialog_summaries)
    )

    system_prompt = "You evaluate narrative coherence across a complete dialog sequence."
    user_prompt = f"""DIALOG SEQUENCE (in chronological order):
{summaries_text}

Does this sequence tell a coherent story? Score 0.0-1.0.
Check for: logical progression, character consistency, thematic development, no plot holes.

Return JSON: {{"coherent": bool, "score": float, "character_consistency": float, "thematic_development": float, "notes": "explanation"}}"""

    try:
        response = llm.service.call(
            system=system_prompt,
            user=user_prompt,
            temperature=0.1,
            max_tokens=300,
            model=model,
            call_type="dialog_quality_semantic",
        )
        if response.success:
            return json.loads(response.content)
    except Exception as e:
        logger.warning(f"Full-run coherence check failed: {e}")

    return {"coherent": True, "score": 0.5, "notes": "evaluation_failed"}


# ============================================================================
# LangGraph Nodes
# ============================================================================

@track_mechanism("M11", "dialog_steering")
def steering_node(state: 'DialogState') -> 'DialogState':
    """
    Selects next speaker, evaluates narrative, injects mood shifts.

    Uses configurable model (defaults to 405B for quality).
    Characters can choose not to speak — steering decides.
    """
    state = dict(state)  # Mutable copy
    llm = state.get("llm")
    turns = state.get("turns", [])
    active_speakers = state.get("active_speakers", [])
    narrative_goals = state.get("narrative_goals", [])
    narrative_progress = state.get("narrative_progress", {})
    mood_register = state.get("mood_register", "neutral")
    suppressed = state.get("suppressed_impulses", {})

    # Build steering prompt
    turns_summary = ""
    if turns:
        recent = turns[-6:]  # Last 6 turns for context
        turns_summary = "\n".join(
            f"  {t.get('speaker', '?')}: {t.get('content', '')[:150]}"
            for t in recent
        )

    goals_text = "\n".join(f"  - {g}: {'DONE' if narrative_progress.get(g) else 'pending'}" for g in narrative_goals)

    # Proception awareness for steering
    proception_text = ""
    proception_states = state.get("proception_states", {})
    if proception_states:
        lines = []
        for eid, ps in proception_states.items():
            anxiety = ps.get("anxiety_level", 0.0)
            if anxiety > 0.3:
                lines.append(f"  {eid}: anxiety={anxiety:.1f}")
        if lines:
            proception_text = "\nCharacter anxiety levels:\n" + "\n".join(lines)

    system_prompt = (
        "You are a dialog steering agent. You decide who speaks next, "
        "whether to escalate or de-escalate tension, and when to end the dialog. "
        "Return ONLY valid JSON."
    )

    user_prompt = f"""DIALOG SO FAR ({len(turns)} turns):
{turns_summary or '(dialog starting)'}

AVAILABLE SPEAKERS: {', '.join(active_speakers)}
NARRATIVE GOALS:
{goals_text or '  (none)'}
CURRENT MOOD: {mood_register}
{proception_text}

Decide the next action. Return JSON:
{{
  "next_speaker": "entity_id" or null (if ending),
  "mood_shift": "escalate" | "de-escalate" | "maintain",
  "narrative_notes": "hint for next speaker about what to say/do",
  "suppress_speaker": ["entity_ids to skip"],
  "end_dialog": false,
  "end_reason": null
}}

Rules:
- Don't use round-robin order. Some characters speak multiple times in a row.
- If narrative goals are all done and tension has resolved, end the dialog.
- If turn count exceeds {state.get('max_turns', 12)}, strongly consider ending.
- Characters with high anxiety should speak more urgently."""

    steering_model = state.get("steering_model")

    try:
        if llm and hasattr(llm, 'service'):
            response = llm.service.call(
                system=system_prompt,
                user=user_prompt,
                temperature=0.3,
                max_tokens=200,
                model=steering_model,
                call_type="dialog_steering",
            )

            if response.success:
                decision = json.loads(response.content)

                # Apply steering decision
                state["current_speaker"] = decision.get("next_speaker")

                # Update mood
                mood_shift = decision.get("mood_shift", "maintain")
                if mood_shift == "escalate":
                    state["mood_register"] = "escalating"
                elif mood_shift == "de-escalate":
                    state["mood_register"] = "de-escalating"

                # Track suppressed speakers
                for sid in decision.get("suppress_speaker", []):
                    suppressed.setdefault(sid, []).append(
                        f"steering_suppressed_turn_{len(turns)}"
                    )
                state["suppressed_impulses"] = suppressed

                # Check end condition
                if decision.get("end_dialog"):
                    state["current_speaker"] = None

                logger.info(
                    f"[Steering] Next: {state['current_speaker']}, "
                    f"mood: {mood_shift}, end: {decision.get('end_dialog')}"
                )

                return state
    except Exception as e:
        logger.warning(f"Steering agent failed: {e}. Using fallback round-robin.")

    # Fallback: simple next-speaker logic
    if turns and active_speakers:
        last_speaker = turns[-1].get("speaker")
        # Pick someone who didn't speak last
        candidates = [s for s in active_speakers if s != last_speaker]
        if candidates:
            import random
            state["current_speaker"] = random.choice(candidates)
        else:
            state["current_speaker"] = active_speakers[0]
    elif active_speakers:
        state["current_speaker"] = active_speakers[0]

    # End if we've exceeded max turns
    if len(turns) >= state.get("max_turns", 12):
        state["current_speaker"] = None

    return state


@track_mechanism("M11", "character_generation")
def character_node(state: 'DialogState') -> 'DialogState':
    """
    Generates ONE dialog turn for current_speaker.

    Uses character-specific PersonaParams and FourthWallContext.
    Independent LLM call with per-character model params.
    """
    state = dict(state)
    llm = state.get("llm")
    current_speaker = state.get("current_speaker")
    turns = state.get("turns", [])

    if not current_speaker or not llm:
        return state

    # Get character context
    fourth_wall_contexts = state.get("fourth_wall_contexts", {})
    persona_params_dict = state.get("persona_params", {})

    ctx = fourth_wall_contexts.get(current_speaker)
    params = persona_params_dict.get(current_speaker)

    if not ctx or not params:
        logger.warning(f"Missing context/params for {current_speaker}")
        return state

    # Import here to avoid circular imports
    from workflows.dialog_context import format_context_for_prompt

    # Build character-specific prompt
    context_text = format_context_for_prompt(ctx)

    recent_turns = ""
    if turns:
        recent = turns[-8:]
        recent_turns = "\n".join(
            f"  {t.get('speaker', '?')}: {t.get('content', '')}"
            for t in recent
        )

    # Steering notes
    mood = state.get("mood_register", "neutral")

    system_prompt = (
        f"You are {current_speaker} in a conversation. "
        f"Speak in character using the voice guide below. "
        f"Generate ONLY the dialog line — no stage directions, no speaker label, "
        f"no quotes around the text. Just the words the character says."
    )

    user_prompt = f"""{context_text}

CONVERSATION SO FAR:
{recent_turns or '(conversation starting)'}

MOOD: {mood}
TURN POSITION: {state.get('turn_count', 0)} of {state.get('max_turns', 12)}

Generate {current_speaker}'s next line of dialog. Keep it natural and in-character.
The response must be ONLY the dialog text, nothing else.
If using specific knowledge, reference it naturally (don't quote metadata).

Return JSON: {{"content": "dialog line", "emotional_tone": "tone", "knowledge_references": ["items"]}}"""

    character_model = state.get("character_model")

    try:
        turn_result = llm.generate_single_turn(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            persona_params=params,
            model=character_model,
        )

        content = turn_result.get("content", "...")
        if content and content != "...":
            new_turn = {
                "speaker": current_speaker,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "emotional_tone": turn_result.get("emotional_tone"),
                "knowledge_references": turn_result.get("knowledge_references", []),
                "confidence": 0.9,
                "physical_state_influence": None,
                "persona_params_used": {
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                    "max_tokens": params.max_tokens,
                },
            }
            turns.append(new_turn)
            state["turns"] = turns
            state["turn_count"] = len(turns)

            logger.info(
                f"[Character] {current_speaker} (turn {len(turns)}): "
                f"{content[:80]}..."
            )
    except Exception as e:
        logger.warning(f"Character generation failed for {current_speaker}: {e}")

    return state


@track_mechanism("M11", "dialog_quality_gate")
def quality_gate_node(state: 'DialogState') -> 'DialogState':
    """
    Semantic quality evaluation. Configurable per-turn or per-dialog.

    If run_quality_per_turn is True, evaluates after every turn.
    Otherwise, only evaluates when dialog is about to end.
    """
    state = dict(state)
    llm = state.get("llm")
    turns = state.get("turns", [])
    run_per_turn = state.get("run_quality_per_turn", False)

    # Decide if we should run quality check
    at_end = state.get("current_speaker") is None
    should_evaluate = at_end or (run_per_turn and len(turns) > 0 and len(turns) % 3 == 0)

    if not should_evaluate or not llm:
        return state

    # First run cheap surface-level check
    from workflows.dialog_synthesis import _evaluate_dialog_quality
    surface_quality = _evaluate_dialog_quality(turns)

    if not surface_quality.get("passed", True):
        state.setdefault("quality_failures", []).extend(surface_quality.get("failures", []))
        logger.info(f"[QualityGate] Surface check failed: {surface_quality.get('failures')}")
        return state

    # If surface check passes, run semantic check (more expensive)
    quality_model = state.get("quality_gate_model")
    narrative_goals = state.get("narrative_goals", [])
    contexts = state.get("fourth_wall_contexts", {})

    semantic_result = evaluate_dialog_semantically(
        turns, narrative_goals, contexts, llm, model=quality_model
    )

    if not semantic_result.passed:
        state.setdefault("quality_failures", []).extend(semantic_result.failures)
        logger.info(f"[QualityGate] Semantic check: {semantic_result.evaluation_text}")
    else:
        # Clear failures if quality improved
        state["quality_failures"] = []

    return state


def should_continue(state: 'DialogState') -> str:
    """
    Routing function for LangGraph conditional edges.

    Returns:
        'steering': Continue dialog (select next speaker)
        'end': Dialog is complete
        'quality_retry': Quality failed, retry last turn
    """
    current_speaker = state.get("current_speaker")
    turns = state.get("turns", [])
    max_turns = state.get("max_turns", 12)
    quality_failures = state.get("quality_failures", [])

    # End conditions
    if current_speaker is None:
        return "end"

    if len(turns) >= max_turns:
        return "end"

    # Quality retry (only once per turn)
    if quality_failures and len(turns) > 0:
        last_retry = state.get("_last_quality_retry_at", -1)
        if last_retry < len(turns) - 1:
            state["_last_quality_retry_at"] = len(turns)
            return "quality_retry"

    return "steering"


# ============================================================================
# LangGraph Flow Builder
# ============================================================================

def build_dialog_graph():
    """
    Build the LangGraph StateGraph for per-turn dialog generation.

    Flow: steering -> character -> quality_gate -> conditional
                                                    |-> steering (continue)
                                                    |-> END (complete)
                                                    |-> character (retry)

    Returns:
        Compiled LangGraph StateGraph, or None if langgraph not available
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        logger.warning(
            "langgraph not installed. Per-turn dialog generation unavailable. "
            "Install with: pip install langgraph"
        )
        return None

    graph = StateGraph(DialogState)

    # Add nodes
    graph.add_node("steering", steering_node)
    graph.add_node("character", character_node)
    graph.add_node("quality_gate", quality_gate_node)

    # Add edges
    graph.set_entry_point("steering")
    graph.add_edge("steering", "character")
    graph.add_edge("character", "quality_gate")

    # Conditional routing from quality gate
    graph.add_conditional_edges(
        "quality_gate",
        should_continue,
        {
            "steering": "steering",
            "end": END,
            "quality_retry": "character",
        }
    )

    # Compile without checkpointer — state contains non-serializable
    # objects (llm, store) that MemorySaver can't msgpack-serialize
    compiled = graph.compile()

    return compiled


def run_dialog_graph(
    initial_state: 'DialogState',
    config: Optional[Dict[str, Any]] = None,
) -> 'DialogState':
    """
    Execute the dialog generation graph.

    If LangGraph is not available, falls back to a simple sequential loop.

    Args:
        initial_state: Starting DialogState with all contexts populated
        config: LangGraph config (thread_id for checkpointing, etc.)

    Returns:
        Final DialogState with generated turns
    """
    try:
        graph = build_dialog_graph()
    except Exception as e:
        logger.error(f"LangGraph graph build failed: {e}. Falling back to sequential.")
        graph = None

    if graph is not None:
        # LangGraph available — run the compiled graph
        lconfig = config or {"configurable": {"thread_id": initial_state.get("timepoint_id", "dialog")}}
        try:
            final_state = graph.invoke(initial_state, lconfig)
            return final_state
        except Exception as e:
            logger.error(f"LangGraph execution failed: {e}. Falling back to sequential.")

    # Fallback: sequential loop without LangGraph
    return _run_sequential_fallback(initial_state)


def _run_sequential_fallback(state: 'DialogState') -> 'DialogState':
    """
    Simple sequential fallback when LangGraph is not available.

    Runs steering -> character -> quality_gate in a loop.
    """
    state = dict(state)
    max_iterations = state.get("max_turns", 12) + 2  # Safety bound

    for _ in range(max_iterations):
        # Steering
        state = steering_node(state)

        # Check if dialog should end
        if state.get("current_speaker") is None:
            break

        # Character generation
        state = character_node(state)

        # Quality gate
        state = quality_gate_node(state)

        # Check routing
        route = should_continue(state)
        if route == "end":
            break
        elif route == "quality_retry":
            # Retry: re-run character node for same speaker
            state = character_node(state)

    return state
