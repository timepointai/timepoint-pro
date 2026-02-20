"""
Tests for Phase 6: Full-Run Evaluation Metrics — tactic evolution score,
information asymmetry utilization score, and subtext density score.
"""
import pytest
from workflows.dialog_steering import (
    _compute_tactic_evolution_score,
    _compute_info_asymmetry_utilization_score,
    _compute_subtext_density_score,
)


# ---------------------------------------------------------------------------
# _compute_tactic_evolution_score
# ---------------------------------------------------------------------------

class TestTacticEvolutionScore:

    def test_empty_arcs_returns_zero(self):
        assert _compute_tactic_evolution_score({}) == 0.0

    def test_single_attempt_returns_zero(self):
        arcs = {
            "Chen": {
                "dialog_attempts": [{"tactic_used": "data_argument"}],
            }
        }
        assert _compute_tactic_evolution_score(arcs) == 0.0

    def test_same_tactic_every_time_scores_low(self):
        arcs = {
            "Chen": {
                "dialog_attempts": [
                    {"tactic_used": "data_argument"},
                    {"tactic_used": "data_argument"},
                    {"tactic_used": "data_argument"},
                    {"tactic_used": "data_argument"},
                ],
            }
        }
        score = _compute_tactic_evolution_score(arcs)
        # variety = 1/4 = 0.25, transitions = 0/3 = 0.0, avg = 0.125
        assert score < 0.2

    def test_diverse_tactics_score_high(self):
        arcs = {
            "Chen": {
                "dialog_attempts": [
                    {"tactic_used": "data_argument"},
                    {"tactic_used": "emotional_appeal"},
                    {"tactic_used": "authority_claim"},
                    {"tactic_used": "humor_deflection"},
                ],
            }
        }
        score = _compute_tactic_evolution_score(arcs)
        # variety = 4/4 = 1.0, transitions = 3/3 = 1.0, avg = 1.0
        assert score >= 0.8

    def test_multiple_entities_averaged(self):
        arcs = {
            "Chen": {
                "dialog_attempts": [
                    {"tactic_used": "data_argument"},
                    {"tactic_used": "emotional_appeal"},
                ],
            },
            "Webb": {
                "dialog_attempts": [
                    {"tactic_used": "authority_claim"},
                    {"tactic_used": "authority_claim"},
                ],
            },
        }
        score = _compute_tactic_evolution_score(arcs)
        # Chen: variety=1.0, transitions=1.0, score=1.0
        # Webb: variety=0.5, transitions=0.0, score=0.25
        # Average: 0.625
        assert 0.3 < score < 0.9

    def test_returns_bounded_0_to_1(self):
        arcs = {
            f"E{i}": {
                "dialog_attempts": [
                    {"tactic_used": t}
                    for t in ["data_argument", "emotional_appeal", "humor_deflection",
                              "alliance_appeal", "threat_escalation", "procedural_challenge"]
                ]
            }
            for i in range(5)
        }
        score = _compute_tactic_evolution_score(arcs)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _compute_info_asymmetry_utilization_score
# ---------------------------------------------------------------------------

class TestInfoAsymmetryUtilizationScore:

    def test_empty_inputs_returns_zero(self):
        assert _compute_info_asymmetry_utilization_score({}, []) == 0.0

    def test_no_unspoken_returns_half(self):
        arcs = {"Chen": {"unspoken_accumulation": []}}
        turns = [[{"speaker": "Chen", "content": "Hello"}]]
        score = _compute_info_asymmetry_utilization_score(arcs, turns)
        assert score == 0.5  # No info asymmetry to utilize

    def test_entity_with_unspoken_using_strategic_moves(self):
        arcs = {
            "Chen": {
                "unspoken_accumulation": [{"content": "secret", "urgency": 0.5}],
            }
        }
        # 3 out of 5 turns are strategic → 60% > 15% threshold
        turns = [[
            {"speaker": "Chen", "content": "line1", "dialog_move": "strategic_question"},
            {"speaker": "Chen", "content": "line2", "dialog_move": "partial_disclosure"},
            {"speaker": "Chen", "content": "line3", "dialog_move": "deflection"},
            {"speaker": "Chen", "content": "line4", "dialog_move": "direct_statement"},
            {"speaker": "Chen", "content": "line5", "dialog_move": "direct_statement"},
        ]]
        score = _compute_info_asymmetry_utilization_score(arcs, turns)
        assert score == 1.0

    def test_entity_with_unspoken_not_using_strategic_moves(self):
        arcs = {
            "Chen": {
                "unspoken_accumulation": [{"content": "secret", "urgency": 0.5}],
            }
        }
        # All direct_statement → 0% strategic, below 15% threshold
        turns = [[
            {"speaker": "Chen", "content": "line1", "dialog_move": "direct_statement"},
            {"speaker": "Chen", "content": "line2", "dialog_move": "direct_statement"},
        ]]
        score = _compute_info_asymmetry_utilization_score(arcs, turns)
        assert score == 0.0


# ---------------------------------------------------------------------------
# _compute_subtext_density_score
# ---------------------------------------------------------------------------

class TestSubtextDensityScore:

    def test_empty_returns_zero(self):
        assert _compute_subtext_density_score([], {}) == 0.0

    def test_all_direct_statements(self):
        turns = [[
            {"speaker": "A", "content": "Hello", "dialog_move": "direct_statement"},
            {"speaker": "B", "content": "Hi", "dialog_move": "direct_statement"},
        ]]
        score = _compute_subtext_density_score(turns, {})
        assert score == 0.0

    def test_all_non_direct_statements(self):
        turns = [[
            {"speaker": "A", "content": "Hello", "dialog_move": "deflection"},
            {"speaker": "B", "content": "Hi", "dialog_move": "strategic_question"},
        ]]
        score = _compute_subtext_density_score(turns, {})
        assert score == 1.0

    def test_mixed_moves(self):
        turns = [[
            {"speaker": "A", "content": "a", "dialog_move": "direct_statement"},
            {"speaker": "B", "content": "b", "dialog_move": "deflection"},
            {"speaker": "A", "content": "c", "dialog_move": "humor"},
            {"speaker": "B", "content": "d", "dialog_move": "direct_statement"},
        ]]
        score = _compute_subtext_density_score(turns, {})
        assert score == pytest.approx(0.5, abs=0.01)

    def test_default_move_treated_as_direct(self):
        # Turns without dialog_move field default to direct_statement
        turns = [[
            {"speaker": "A", "content": "a"},
            {"speaker": "B", "content": "b"},
        ]]
        score = _compute_subtext_density_score(turns, {})
        assert score == 0.0

    def test_multiple_dialogs(self):
        turns = [
            [
                {"speaker": "A", "content": "a", "dialog_move": "deflection"},
            ],
            [
                {"speaker": "B", "content": "b", "dialog_move": "direct_statement"},
            ],
        ]
        score = _compute_subtext_density_score(turns, {})
        assert score == pytest.approx(0.5, abs=0.01)
