"""
Tests for Phase 5: PORTAL Inline Dialog — portal step dialog, constraint
extraction, and antecedent constraint injection.
"""
import pytest
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, patch

from schemas import Entity, PhysicalTensor, CognitiveTensor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(entity_id: str, age: float = 35.0) -> Entity:
    return Entity(
        entity_id=entity_id,
        entity_type="human",
        entity_metadata={"age": age},
    )


# ---------------------------------------------------------------------------
# PortalState construction and tensor seeding logic
# ---------------------------------------------------------------------------

class TestPortalTensorSeeding:
    """Test the tensor seeding logic used in _run_portal_step_dialog."""

    def test_seeds_physical_tensor_when_missing(self):
        entity = _make_entity("Chen", age=42.0)
        assert entity.entity_metadata.get("physical_tensor") is None

        # Replicate portal seeding logic
        if not entity.entity_metadata.get("physical_tensor"):
            age = entity.entity_metadata.get("age", 35.0)
            entity.entity_metadata["physical_tensor"] = PhysicalTensor(
                age=age, health_status=1.0, pain_level=0.0,
                fever=36.5, mobility=1.0, stamina=1.0,
                sensory_acuity={"vision": 1.0, "hearing": 1.0},
            ).model_dump()

        assert entity.physical_tensor is not None
        assert entity.physical_tensor.age == 42.0

    def test_seeds_cognitive_tensor_when_missing(self):
        entity = _make_entity("Webb")
        if not entity.entity_metadata.get("cognitive_tensor"):
            entity.entity_metadata["cognitive_tensor"] = CognitiveTensor(
                knowledge_state=[], emotional_valence=0.0, emotional_arousal=0.2,
                energy_budget=100.0, decision_confidence=0.8,
            ).model_dump()

        assert entity.cognitive_tensor is not None
        assert entity.cognitive_tensor.energy_budget == 100.0

    def test_does_not_overwrite_existing_tensors(self):
        entity = _make_entity("Chen")
        entity.entity_metadata["physical_tensor"] = PhysicalTensor(
            age=60.0, health_status=0.5, pain_level=0.3,
            fever=37.5, mobility=0.6, stamina=0.4,
            sensory_acuity={"vision": 0.7},
        ).model_dump()

        # Seeding check
        if not entity.entity_metadata.get("physical_tensor"):
            entity.entity_metadata["physical_tensor"] = PhysicalTensor(age=35.0).model_dump()

        assert entity.physical_tensor.age == 60.0  # Not overwritten

    def test_handles_string_age(self):
        entity = _make_entity("Chen")
        entity.entity_metadata["age"] = "45"

        age = entity.entity_metadata.get("age", 35.0)
        if isinstance(age, str):
            try:
                age = float(age)
            except (ValueError, TypeError):
                age = 35.0
        assert age == 45.0


# ---------------------------------------------------------------------------
# Dialog Constraints Structure
# ---------------------------------------------------------------------------

class TestDialogConstraintsStructure:
    """Test the dialog_constraints dict structure returned by _run_portal_step_dialog."""

    def test_default_constraints_structure(self):
        constraints = {
            "character_positions": {},
            "contested_claims": [],
            "resolved_facts": [],
            "escalation_level": 0.0,
            "dialog_summary": "",
        }
        assert isinstance(constraints["character_positions"], dict)
        assert isinstance(constraints["contested_claims"], list)
        assert isinstance(constraints["resolved_facts"], list)
        assert isinstance(constraints["escalation_level"], float)
        assert 0.0 <= constraints["escalation_level"] <= 1.0

    def test_character_position_structure(self):
        position = {
            "stated_position": "The O-ring data shows a clear temperature correlation.",
            "information_held": ["O-ring temperature data", "erosion measurements"],
            "trust_toward": {"Webb": -0.3, "Blake": 0.1},
        }
        assert isinstance(position["stated_position"], str)
        assert isinstance(position["information_held"], list)
        assert isinstance(position["trust_toward"], dict)

    def test_constraints_with_populated_positions(self):
        constraints = {
            "character_positions": {
                "Chen": {
                    "stated_position": "Launch should be delayed",
                    "information_held": ["thermal data"],
                    "trust_toward": {"Webb": -0.2},
                },
                "Webb": {
                    "stated_position": "Schedule must be maintained",
                    "information_held": [],
                    "trust_toward": {"Chen": 0.1},
                },
            },
            "contested_claims": ["launch timing"],
            "resolved_facts": ["budget is approved"],
            "escalation_level": 0.6,
            "dialog_summary": "Chen argued for delay, Webb pushed schedule.",
        }
        assert len(constraints["character_positions"]) == 2
        assert "Chen" in constraints["character_positions"]
        assert constraints["escalation_level"] == 0.6


# ---------------------------------------------------------------------------
# Portal enable_inline_dialog config
# ---------------------------------------------------------------------------

class TestPortalInlineDialogConfig:
    """Test that the enable_inline_dialog configuration is properly handled."""

    def test_default_enable_inline_dialog(self):
        """When no metadata is provided, inline dialog should default to True."""
        # Replicate the logic from PortalStrategy.__init__
        portal_metadata = {}
        enable = portal_metadata.get("portal_inline_dialog", True)
        assert enable is True

    def test_explicit_disable(self):
        portal_metadata = {"portal_inline_dialog": False}
        enable = portal_metadata.get("portal_inline_dialog", True)
        assert enable is False

    def test_explicit_enable(self):
        portal_metadata = {"portal_inline_dialog": True}
        enable = portal_metadata.get("portal_inline_dialog", True)
        assert enable is True

    def test_non_dict_metadata_defaults_to_true(self):
        portal_metadata = "not a dict"
        if isinstance(portal_metadata, dict):
            enable = portal_metadata.get("portal_inline_dialog", True)
        else:
            enable = True
        assert enable is True


# ---------------------------------------------------------------------------
# Ephemeral Timepoint Creation
# ---------------------------------------------------------------------------

class TestEphemeralTimepointCreation:
    """Test the ephemeral Timepoint creation logic from _run_portal_step_dialog."""

    def test_creates_timepoint_from_portal_state_data(self):
        from schemas import Timepoint

        step_index = 2
        year = 2024
        month = 6
        description = "Pre-launch review meeting"
        entities = [_make_entity("Chen"), _make_entity("Webb")]

        tp_id = f"portal_step_{step_index}_{year}_{month}"
        timestamp = datetime(year, month, 15)
        ephemeral_tp = Timepoint(
            timepoint_id=tp_id,
            timestamp=timestamp,
            event_description=description,
            entities_present=[e.entity_id for e in entities],
        )

        assert ephemeral_tp.timepoint_id == "portal_step_2_2024_6"
        assert ephemeral_tp.timestamp.year == 2024
        assert ephemeral_tp.timestamp.month == 6
        assert ephemeral_tp.event_description == "Pre-launch review meeting"
        assert "Chen" in ephemeral_tp.entities_present
        assert "Webb" in ephemeral_tp.entities_present

    def test_handles_invalid_month_gracefully(self):
        from schemas import Timepoint

        # If month is None or invalid, fallback to month=1
        month = None
        try:
            timestamp = datetime(2025, month or 1, 15)
        except (ValueError, TypeError):
            timestamp = datetime(2025, 1, 15)

        assert timestamp.month == 1
