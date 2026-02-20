"""
Tests for Phase 1: Inline Dialog in FORWARD Loop — DialogOutcomeContext,
_extract_dialog_outcome, and tensor seeding.
"""
import json
import pytest
from datetime import datetime
from schemas import Entity, Dialog, Timepoint, PhysicalTensor, CognitiveTensor
from workflows.dialog_synthesis import (
    DialogOutcomeContext,
    _extract_dialog_outcome,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(entity_id: str, **extra_metadata) -> Entity:
    return Entity(
        entity_id=entity_id,
        entity_type="human",
        entity_metadata={"age": 35.0, **extra_metadata},
    )


def _make_timepoint(tp_id: str = "tp_1", desc: str = "Test event", entities: list = None) -> Timepoint:
    return Timepoint(
        timepoint_id=tp_id,
        timestamp=datetime(2025, 3, 15),
        event_description=desc,
        entities_present=entities or ["entity_a", "entity_b"],
    )


def _make_dialog(
    dialog_id: str = "d1",
    tp_id: str = "tp_1",
    turns: list = None,
    context: dict = None,
) -> Dialog:
    if turns is None:
        turns = [
            {"speaker": "entity_a", "content": "We need to discuss the pressure readings from yesterday.", "emotional_tone": "concerned"},
            {"speaker": "entity_b", "content": "I agree, the numbers look off.", "emotional_tone": "neutral"},
            {"speaker": "entity_a", "content": "The gauge showed 150 psi which is above tolerance.", "emotional_tone": "worried"},
        ]
    return Dialog(
        dialog_id=dialog_id,
        timepoint_id=tp_id,
        participants=json.dumps(["entity_a", "entity_b"]),
        turns=json.dumps(turns),
        context_used=json.dumps(context or {}),
    )


# ---------------------------------------------------------------------------
# DialogOutcomeContext
# ---------------------------------------------------------------------------

class TestDialogOutcomeContext:

    def test_default_construction(self):
        ctx = DialogOutcomeContext()
        assert ctx.dialog_id == ""
        assert ctx.topics_raised == []
        assert ctx.summary == ""

    def test_to_dict(self):
        ctx = DialogOutcomeContext(
            dialog_id="d1",
            timepoint_id="tp_1",
            topics_raised=["pressure readings"],
            summary="Two entities discussed pressure.",
        )
        d = ctx.to_dict()
        assert d["dialog_id"] == "d1"
        assert d["topics_raised"] == ["pressure readings"]
        assert isinstance(d, dict)

    def test_to_dict_is_json_serializable(self):
        ctx = DialogOutcomeContext(
            dialog_id="d1",
            timepoint_id="tp_1",
            topics_raised=["topic_a"],
            emotional_deltas={"entity_a": {"turn_count": 2, "final_tone": "worried"}},
            relationship_shifts={"entity_a-entity_b": 0.1},
        )
        # Should not raise
        json_str = json.dumps(ctx.to_dict())
        assert "topic_a" in json_str


# ---------------------------------------------------------------------------
# _extract_dialog_outcome
# ---------------------------------------------------------------------------

class TestExtractDialogOutcome:

    def test_extracts_topics_from_turns(self):
        dialog = _make_dialog()
        entities = [_make_entity("entity_a"), _make_entity("entity_b")]
        tp = _make_timepoint()
        outcome = _extract_dialog_outcome(dialog, entities, tp)

        assert isinstance(outcome, DialogOutcomeContext)
        assert len(outcome.topics_raised) > 0
        assert outcome.timepoint_id == "tp_1"
        assert outcome.dialog_id == "d1"

    def test_extracts_emotional_deltas(self):
        dialog = _make_dialog()
        entities = [_make_entity("entity_a"), _make_entity("entity_b")]
        tp = _make_timepoint()
        outcome = _extract_dialog_outcome(dialog, entities, tp)

        assert "entity_a" in outcome.emotional_deltas
        assert outcome.emotional_deltas["entity_a"]["turn_count"] == 2
        assert outcome.emotional_deltas["entity_a"]["final_tone"] == "worried"

    def test_extracts_relationship_shifts(self):
        context = {"relationship_impacts": {"entity_a-entity_b": 0.2}}
        dialog = _make_dialog(context=context)
        entities = [_make_entity("entity_a"), _make_entity("entity_b")]
        tp = _make_timepoint()
        outcome = _extract_dialog_outcome(dialog, entities, tp)

        assert outcome.relationship_shifts == {"entity_a-entity_b": 0.2}

    def test_handles_empty_turns(self):
        dialog = _make_dialog(turns=[])
        entities = [_make_entity("entity_a")]
        tp = _make_timepoint()
        outcome = _extract_dialog_outcome(dialog, entities, tp)

        assert outcome.topics_raised == []
        assert outcome.emotional_deltas == {}

    def test_handles_invalid_turns_json(self):
        dialog = Dialog(
            dialog_id="bad",
            timepoint_id="tp_1",
            participants="[]",
            turns="not valid json {{{",
            context_used="{}",
        )
        entities = [_make_entity("entity_a")]
        tp = _make_timepoint()
        outcome = _extract_dialog_outcome(dialog, entities, tp)
        # Should not raise, returns empty-ish context
        assert isinstance(outcome, DialogOutcomeContext)

    def test_summary_includes_speaker_count(self):
        dialog = _make_dialog()
        entities = [_make_entity("entity_a"), _make_entity("entity_b")]
        tp = _make_timepoint()
        outcome = _extract_dialog_outcome(dialog, entities, tp)
        assert "3 turns" in outcome.summary

    def test_topics_capped_at_10(self):
        # Create 15 turns with distinct long content
        turns = [
            {"speaker": f"entity_{'a' if i % 2 == 0 else 'b'}", "content": f"Topic number {i}: " + "x" * 20}
            for i in range(15)
        ]
        dialog = _make_dialog(turns=turns)
        entities = [_make_entity("entity_a"), _make_entity("entity_b")]
        tp = _make_timepoint()
        outcome = _extract_dialog_outcome(dialog, entities, tp)
        assert len(outcome.topics_raised) <= 10


# ---------------------------------------------------------------------------
# Tensor Seeding (test the pattern used by _seed_entity_tensors)
# ---------------------------------------------------------------------------

class TestTensorSeeding:

    def test_entity_without_tensors_can_be_seeded(self):
        entity = _make_entity("Chen")
        assert entity.entity_metadata.get("physical_tensor") is None

        # Replicate seeding logic
        physical = PhysicalTensor(
            age=35.0, health_status=1.0, pain_level=0.0,
            fever=36.5, mobility=1.0, stamina=1.0,
            sensory_acuity={"vision": 1.0, "hearing": 1.0},
        )
        cognitive = CognitiveTensor(
            knowledge_state=[], emotional_valence=0.0, emotional_arousal=0.2,
            energy_budget=100.0, decision_confidence=0.8,
        )
        entity.entity_metadata["physical_tensor"] = physical.model_dump()
        entity.entity_metadata["cognitive_tensor"] = cognitive.model_dump()

        # Now the property accessors should work
        assert entity.physical_tensor is not None
        assert entity.physical_tensor.age == 35.0
        assert entity.cognitive_tensor is not None
        assert entity.cognitive_tensor.emotional_valence == 0.0

    def test_seeding_does_not_overwrite_existing(self):
        entity = _make_entity("Chen")
        entity.entity_metadata["physical_tensor"] = PhysicalTensor(
            age=60.0, health_status=0.7, pain_level=0.2,
            fever=37.0, mobility=0.8, stamina=0.6,
            sensory_acuity={"vision": 0.8},
        ).model_dump()

        # Seeding check: only seed if missing
        if not entity.entity_metadata.get("physical_tensor"):
            entity.entity_metadata["physical_tensor"] = PhysicalTensor(age=35.0).model_dump()

        # Should still be 60.0, not overwritten
        assert entity.physical_tensor.age == 60.0

    def test_string_age_conversion(self):
        entity = _make_entity("Chen", age="42")
        age = entity.entity_metadata.get("age", 35.0)
        if isinstance(age, str):
            age = float(age)
        assert age == 42.0
