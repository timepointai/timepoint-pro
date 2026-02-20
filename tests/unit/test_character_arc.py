"""
Tests for Phase 2: Character Arc Tracking — tactic classification, outcome
classification, arc updates, urgency growth, and context formatting.
"""
import pytest
from schemas import Entity
from workflows.dialog_synthesis import (
    _classify_tactic,
    _classify_outcome,
    _update_character_arc,
    _get_character_arc_for_context,
    TACTIC_VOCABULARY,
    OUTCOME_VOCABULARY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(entity_id: str, **extra_metadata) -> Entity:
    """Create a minimal Entity for testing."""
    return Entity(
        entity_id=entity_id,
        entity_type="human",
        entity_metadata={"age": 40.0, **extra_metadata},
    )


def _make_turns(data: list[tuple[str, str]]) -> list[dict]:
    """Convert [(speaker, content), ...] to dialog turn dicts."""
    return [{"speaker": s, "content": c} for s, c in data]


# ---------------------------------------------------------------------------
# _classify_tactic
# ---------------------------------------------------------------------------

class TestClassifyTactic:

    def test_data_argument_keywords(self):
        assert _classify_tactic("The data shows a 5 percent increase in pressure readings") == "data_argument"

    def test_emotional_appeal_keywords(self):
        assert _classify_tactic("I'm worried about the families and lives at stake") == "emotional_appeal"

    def test_authority_claim_keywords(self):
        assert _classify_tactic("As the commander, my authority here is clear, per protocol") == "authority_claim"

    def test_humor_deflection_keywords(self):
        assert _classify_tactic("That's a funny joke, ha, let's lighten the mood") == "humor_deflection"

    def test_procedural_challenge_keywords(self):
        assert _classify_tactic("We should follow procedure and schedule a formal review") == "procedural_challenge"

    def test_alliance_appeal_keywords(self):
        assert _classify_tactic("I agree with Chen, we should join together and support this") == "alliance_appeal"

    def test_threat_escalation_keywords(self):
        assert _classify_tactic("I will escalate this and report the consequences unless you comply") == "threat_escalation"

    def test_default_when_no_keywords(self):
        # With no matching keywords, default should be data_argument (score 0 == best_score 0, so initial best stays)
        result = _classify_tactic("Hello there, nice weather today")
        assert result == "data_argument"  # default

    def test_returns_valid_vocabulary(self):
        samples = [
            "data shows 10 percent",
            "worried about lives",
            "as the commander",
            "just a joke ha",
            "follow procedure",
            "agree with you",
            "escalate and report",
        ]
        for s in samples:
            assert _classify_tactic(s) in TACTIC_VOCABULARY


# ---------------------------------------------------------------------------
# _classify_outcome
# ---------------------------------------------------------------------------

class TestClassifyOutcome:

    def test_accepted(self):
        next_turns = [{"speaker": "B", "content": "Good point, I agree with that."}]
        assert _classify_outcome("Some argument", next_turns, "B") == "accepted"

    def test_dismissed(self):
        next_turns = [{"speaker": "B", "content": "No, that is wrong and absurd nonsense."}]
        assert _classify_outcome("Some argument", next_turns, "B") == "dismissed"

    def test_deferred(self):
        next_turns = [{"speaker": "B", "content": "Let's table this and revisit later."}]
        assert _classify_outcome("Some argument", next_turns, "B") == "deferred"

    def test_partially_acknowledged(self):
        next_turns = [{"speaker": "B", "content": "There is perhaps some merit, but also concerns."}]
        assert _classify_outcome("Some argument", next_turns, "B") == "partially_acknowledged"

    def test_ignored_when_no_match(self):
        next_turns = [{"speaker": "B", "content": "The sky is blue."}]
        assert _classify_outcome("Some argument", next_turns, "B") == "ignored"

    def test_deferred_when_no_next_turns(self):
        assert _classify_outcome("Some argument", [], "B") == "deferred"

    def test_ignored_when_target_not_in_next_turns(self):
        next_turns = [{"speaker": "C", "content": "I agree completely"}]
        assert _classify_outcome("Some argument", next_turns, "B") == "ignored"


# ---------------------------------------------------------------------------
# _update_character_arc
# ---------------------------------------------------------------------------

class TestUpdateCharacterArc:

    def test_creates_arc_on_first_call(self):
        entity = _make_entity("Chen")
        other = _make_entity("Webb")
        turns = _make_turns([
            ("Chen", "The data shows a 5 percent reading."),
            ("Webb", "No, that's wrong."),
        ])
        _update_character_arc(entity, turns, [entity, other], "T1")
        arc = entity.entity_metadata["character_arc"]
        assert "dialog_attempts" in arc
        assert len(arc["dialog_attempts"]) >= 1

    def test_records_tactic_and_outcome(self):
        entity = _make_entity("Chen")
        other = _make_entity("Webb")
        turns = _make_turns([
            ("Chen", "The data shows a measurement of 10 percent."),
            ("Webb", "No, that's absolutely wrong."),
        ])
        _update_character_arc(entity, turns, [entity, other], "T1")
        arc = entity.entity_metadata["character_arc"]
        attempt = arc["dialog_attempts"][0]
        assert attempt["tactic_used"] == "data_argument"
        assert attempt["outcome"] == "dismissed"
        assert attempt["target_entity"] == "Webb"
        assert attempt["timepoint_id"] == "T1"

    def test_trust_decreases_on_dismissal(self):
        entity = _make_entity("Chen")
        other = _make_entity("Webb")
        turns = _make_turns([
            ("Chen", "The evidence indicates a problem."),
            ("Webb", "No, that is wrong and absurd nonsense."),
        ])
        _update_character_arc(entity, turns, [entity, other], "T1")
        arc = entity.entity_metadata["character_arc"]
        assert arc["trust_ledger"].get("Webb", 0) < 0

    def test_trust_increases_on_acceptance(self):
        entity = _make_entity("Chen")
        other = _make_entity("Webb")
        turns = _make_turns([
            ("Chen", "The reading shows elevated pressure."),
            ("Webb", "Yes, good point, I agree."),
        ])
        _update_character_arc(entity, turns, [entity, other], "T1")
        arc = entity.entity_metadata["character_arc"]
        assert arc["trust_ledger"].get("Webb", 0) > 0

    def test_urgency_grows_for_unspoken_items(self):
        entity = _make_entity("Chen")
        # Pre-seed an unspoken item
        entity.entity_metadata["character_arc"] = {
            "dialog_attempts": [],
            "trust_ledger": {},
            "alliance_history": [],
            "unspoken_accumulation": [
                {"content": "secret about o2 fault", "urgency": 0.3, "first_formed": "T0"}
            ],
        }
        other = _make_entity("Webb")
        # Dialog where Chen does NOT mention the o2 fault
        turns = _make_turns([
            ("Chen", "Let's discuss the schedule for next week."),
            ("Webb", "Sounds good."),
        ])
        _update_character_arc(entity, turns, [entity, other], "T1")
        arc = entity.entity_metadata["character_arc"]
        unspoken = arc["unspoken_accumulation"][0]
        # Urgency should have grown from 0.3 by 0.15
        assert unspoken["urgency"] == pytest.approx(0.45, abs=0.01)

    def test_accumulates_over_multiple_timepoints(self):
        entity = _make_entity("Chen")
        other = _make_entity("Webb")
        for tp_id in ("T1", "T2", "T3"):
            turns = _make_turns([
                ("Chen", f"Data shows problems in {tp_id}."),
                ("Webb", "No, I disagree."),
            ])
            _update_character_arc(entity, turns, [entity, other], tp_id)

        arc = entity.entity_metadata["character_arc"]
        assert len(arc["dialog_attempts"]) == 3
        timepoints = [a["timepoint_id"] for a in arc["dialog_attempts"]]
        assert timepoints == ["T1", "T2", "T3"]


# ---------------------------------------------------------------------------
# _get_character_arc_for_context
# ---------------------------------------------------------------------------

class TestGetCharacterArcForContext:

    def test_empty_arc_returns_empty_string(self):
        entity = _make_entity("Chen")
        assert _get_character_arc_for_context(entity) == ""

    def test_no_arc_returns_empty_string(self):
        entity = _make_entity("Chen")
        entity.entity_metadata.pop("character_arc", None)
        assert _get_character_arc_for_context(entity) == ""

    def test_formats_dismissed_tactics(self):
        entity = _make_entity("Chen")
        entity.entity_metadata["character_arc"] = {
            "dialog_attempts": [
                {"tactic_used": "data_argument", "target_entity": "Webb", "outcome": "dismissed", "timepoint_id": "T1"},
                {"tactic_used": "data_argument", "target_entity": "Webb", "outcome": "dismissed", "timepoint_id": "T2"},
            ],
            "trust_ledger": {},
            "alliance_history": [],
            "unspoken_accumulation": [],
        }
        result = _get_character_arc_for_context(entity)
        assert result.startswith("[Arc:")
        assert "data_argument" in result
        assert "Webb" in result

    def test_formats_urgent_unspoken_items(self):
        entity = _make_entity("Chen")
        entity.entity_metadata["character_arc"] = {
            "dialog_attempts": [],
            "trust_ledger": {},
            "alliance_history": [],
            "unspoken_accumulation": [
                {"content": "O2 fault reading was critical", "urgency": 0.8, "first_formed": "T0"},
            ],
        }
        result = _get_character_arc_for_context(entity)
        assert "has not yet disclosed" in result
        assert "O2 fault" in result
        assert "0.8" in result

    def test_formats_low_trust(self):
        entity = _make_entity("Chen")
        entity.entity_metadata["character_arc"] = {
            "dialog_attempts": [],
            "trust_ledger": {"Webb": -0.5},
            "alliance_history": [],
            "unspoken_accumulation": [],
        }
        result = _get_character_arc_for_context(entity)
        assert "low trust toward Webb" in result
