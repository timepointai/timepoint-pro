"""
Tests for Phase 3: Strategic Steering Agent — dialog moves, move instructions,
and information asymmetry computation.
"""
import pytest
from workflows.dialog_steering import (
    _MOVE_INSTRUCTIONS,
    _get_move_instruction,
)
from workflows.dialog_context import (
    _compute_information_asymmetry,
    FourthWallContext,
    BackLayerContext,
    FrontLayerContext,
)


# ---------------------------------------------------------------------------
# _MOVE_INSTRUCTIONS
# ---------------------------------------------------------------------------

class TestMoveInstructions:

    EXPECTED_MOVES = [
        "direct_statement", "deflection", "strategic_question",
        "alliance_signal", "partial_disclosure", "status_move", "humor",
    ]

    def test_all_expected_moves_present(self):
        for move in self.EXPECTED_MOVES:
            assert move in _MOVE_INSTRUCTIONS, f"Missing move: {move}"

    def test_direct_statement_is_empty(self):
        assert _MOVE_INSTRUCTIONS["direct_statement"] == ""

    def test_non_direct_moves_have_content(self):
        for move in self.EXPECTED_MOVES:
            if move != "direct_statement":
                assert len(_MOVE_INSTRUCTIONS[move]) > 10, f"{move} instruction too short"


# ---------------------------------------------------------------------------
# _get_move_instruction
# ---------------------------------------------------------------------------

class TestGetMoveInstruction:

    def test_direct_statement_returns_empty(self):
        assert _get_move_instruction("direct_statement") == ""

    def test_deflection_returns_instruction(self):
        result = _get_move_instruction("deflection")
        assert "MOVE:" in result
        assert "redirect" in result.lower() or "avoid" in result.lower()

    def test_target_substitution(self):
        result = _get_move_instruction("strategic_question", "Webb")
        assert "Webb" in result
        assert "{target}" not in result

    def test_target_fallback_when_no_target(self):
        result = _get_move_instruction("strategic_question")
        assert "the other speaker" in result
        assert "{target}" not in result

    def test_unknown_move_returns_empty(self):
        assert _get_move_instruction("nonexistent_move") == ""

    def test_alliance_signal_mentions_coalition(self):
        result = _get_move_instruction("alliance_signal", "Chen")
        assert "coalition" in result.lower() or "agreement" in result.lower() or "Chen" in result

    def test_partial_disclosure_mentions_hint(self):
        result = _get_move_instruction("partial_disclosure", "Webb")
        assert "hint" in result.lower() or "reveal" in result.lower()


# ---------------------------------------------------------------------------
# _compute_information_asymmetry
# ---------------------------------------------------------------------------

class TestComputeInformationAsymmetry:

    def _make_fw_context(
        self,
        entity_id: str,
        withheld: list,
        knowledge_items: list,
    ) -> FourthWallContext:
        back = BackLayerContext(
            withheld_knowledge=withheld,
            suppressed_impulses=[],
        )
        front = FrontLayerContext(
            knowledge_items=knowledge_items,
            scene_context="test scene",
        )
        return FourthWallContext(
            entity_id=entity_id,
            back_layer=back,
            front_layer=front,
        )

    def test_exclusive_knowledge_detected(self):
        ctxs = {
            "Chen": self._make_fw_context(
                "Chen",
                withheld=[{"content": "O2 fault reading was 150psi"}],
                knowledge_items=[],
            ),
            "Webb": self._make_fw_context(
                "Webb",
                withheld=[],
                knowledge_items=[],
            ),
        }
        result = _compute_information_asymmetry(ctxs)
        assert "Chen" in result
        assert any("O2 fault" in item for item in result["Chen"])

    def test_no_asymmetry_when_all_knowledge_shared(self):
        shared_item = {"content": "Launch scheduled for March"}
        ctxs = {
            "Chen": self._make_fw_context(
                "Chen",
                withheld=[shared_item],
                knowledge_items=[shared_item],
            ),
            "Webb": self._make_fw_context(
                "Webb",
                withheld=[],
                knowledge_items=[shared_item],
            ),
        }
        result = _compute_information_asymmetry(ctxs)
        # Chen's withheld item IS in Webb's knowledge, so no exclusive
        assert "Chen" not in result or len(result.get("Chen", [])) == 0

    def test_empty_contexts_returns_empty(self):
        result = _compute_information_asymmetry({})
        assert result == {}

    def test_multiple_entities_with_different_exclusive_items(self):
        ctxs = {
            "A": self._make_fw_context(
                "A",
                withheld=[{"content": "Secret alpha information for entity A"}],
                knowledge_items=[],
            ),
            "B": self._make_fw_context(
                "B",
                withheld=[{"content": "Secret beta information for entity B"}],
                knowledge_items=[],
            ),
        }
        result = _compute_information_asymmetry(ctxs)
        assert "A" in result
        assert "B" in result
