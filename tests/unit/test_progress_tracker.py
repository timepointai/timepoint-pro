"""
Tests for Progress Tracking (Sprint 1.4)

Tests progress updates, ETA calculation, cost tracking, and export functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
import time

from generation.progress_tracker import ProgressTracker, GenerationMetrics


class TestGenerationMetrics:
    """Tests for GenerationMetrics dataclass"""

    def test_metrics_initialization(self):
        """Test metrics default initialization"""
        metrics = GenerationMetrics()
        assert metrics.entities_generated == 0
        assert metrics.entities_failed == 0
        assert metrics.tokens_consumed == 0
        assert metrics.llm_calls_successful == 0
        assert metrics.llm_retries == 0

    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary"""
        metrics = GenerationMetrics(
            entities_generated=10,
            tokens_consumed=5000
        )
        data = metrics.to_dict()
        assert data["entities_generated"] == 10
        assert data["tokens_consumed"] == 5000


class TestProgressTracker:
    """Tests for ProgressTracker"""

    def test_tracker_initialization(self):
        """Test tracker initialization"""
        tracker = ProgressTracker(
            total_entities=100,
            total_timepoints=5
        )
        assert tracker.total_entities == 100
        assert tracker.total_timepoints == 5
        assert tracker.metrics.entities_generated == 0

    def test_start_tracking(self):
        """Test starting progress tracking"""
        tracker = ProgressTracker(total_entities=10)
        tracker.start()

        assert tracker.metrics.start_time is not None
        assert tracker._last_update_time is not None

    def test_update_entity_generated(self):
        """Test entity generation updates"""
        tracker = ProgressTracker(total_entities=100)
        tracker.start()

        tracker.update_entity_generated()
        assert tracker.metrics.entities_generated == 1

        tracker.update_entity_generated(count=9)
        assert tracker.metrics.entities_generated == 10

    def test_update_entity_failed(self):
        """Test entity failure updates"""
        tracker = ProgressTracker(total_entities=100)
        tracker.start()

        tracker.update_entity_failed()
        assert tracker.metrics.entities_failed == 1

        tracker.update_entity_failed(count=4)
        assert tracker.metrics.entities_failed == 5

    def test_update_timepoint_generated(self):
        """Test timepoint generation updates"""
        tracker = ProgressTracker(total_timepoints=50)
        tracker.start()

        tracker.update_timepoint_generated()
        assert tracker.metrics.timepoints_generated == 1

        tracker.update_timepoint_generated(count=9)
        assert tracker.metrics.timepoints_generated == 10

    def test_update_tokens(self):
        """Test token consumption tracking"""
        tracker = ProgressTracker()
        tracker.start()

        tracker.update_tokens(1000)
        assert tracker.metrics.tokens_consumed == 1000

        tracker.update_tokens(500)
        assert tracker.metrics.tokens_consumed == 1500

    def test_update_llm_calls(self):
        """Test LLM call tracking"""
        tracker = ProgressTracker()
        tracker.start()

        tracker.update_llm_call_success()
        tracker.update_llm_call_success()
        assert tracker.metrics.llm_calls_successful == 2

        tracker.update_llm_call_failure()
        assert tracker.metrics.llm_calls_failed == 1

        tracker.update_llm_retry()
        tracker.update_llm_retry()
        assert tracker.metrics.llm_retries == 2

    def test_complete_tracking(self):
        """Test completing tracking"""
        tracker = ProgressTracker(total_entities=10)
        tracker.start()

        for i in range(10):
            tracker.update_entity_generated()

        tracker.complete()
        assert tracker.metrics.end_time is not None

    def test_progress_percentages(self):
        """Test progress percentage calculations"""
        tracker = ProgressTracker(total_entities=100, total_timepoints=50)
        tracker.start()

        # Generate 50 entities
        tracker.update_entity_generated(count=50)
        state = tracker.get_current_state()
        assert state["entity_progress_percent"] == 50.0

        # Generate 25 timepoints
        tracker.update_timepoint_generated(count=25)
        state = tracker.get_current_state()
        assert state["timepoint_progress_percent"] == 50.0

        # Overall progress: (50 + 25) / (100 + 50) = 50%
        assert state["overall_progress_percent"] == 50.0

    def test_eta_calculation(self):
        """Test ETA calculation"""
        tracker = ProgressTracker(total_entities=100)
        tracker.start()

        # Generate some entities
        for i in range(10):
            tracker.update_entity_generated()

        # Small delay to ensure elapsed time > 0
        time.sleep(0.1)

        state = tracker.get_current_state()
        # Should have ETA since we've made progress
        assert state["eta_seconds"] is not None
        assert state["eta_seconds"] > 0

    def test_get_summary(self):
        """Test summary statistics"""
        tracker = ProgressTracker(total_entities=100)
        tracker.start()

        # Simulate some work
        for i in range(50):
            tracker.update_entity_generated()
        tracker.update_entity_failed(count=5)
        tracker.update_tokens(10000)
        tracker.update_llm_call_success()
        tracker.update_llm_call_success()
        tracker.update_llm_call_failure()

        tracker.complete()

        summary = tracker.get_summary()

        # Check all expected keys present
        assert "entities_generated" in summary
        assert "entity_success_rate" in summary
        assert "llm_success_rate" in summary
        assert "duration_seconds" in summary
        assert "estimated_cost_usd" in summary
        assert "tokens_per_second" in summary

        # Verify calculations
        assert summary["entities_generated"] == 50
        assert summary["entity_success_rate"] == 50 / 55  # 50 success / 55 total
        assert summary["llm_success_rate"] == 2 / 3  # 2 success / 3 total
        assert summary["tokens_consumed"] == 10000

    def test_cost_estimation(self):
        """Test cost estimation"""
        tracker = ProgressTracker()
        tracker.start()

        # Consume 10,000 tokens
        tracker.update_tokens(10000)

        summary = tracker.get_summary()
        # $0.002 per 1K tokens = $0.02 for 10K tokens
        expected_cost = 10000 / 1000 * 0.002
        assert abs(summary["estimated_cost_usd"] - expected_cost) < 0.0001

    def test_export_to_json(self):
        """Test exporting progress to JSON"""
        tracker = ProgressTracker(total_entities=50)
        tracker.start()

        for i in range(25):
            tracker.update_entity_generated()
        tracker.update_tokens(5000)

        tracker.complete()

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            tracker.export_to_json(temp_path)

            # Verify file exists and is valid JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert data["entities_generated"] == 25
            assert data["tokens_consumed"] == 5000
            assert "duration_seconds" in data
        finally:
            Path(temp_path).unlink()

    def test_reset_tracker(self):
        """Test resetting tracker"""
        tracker = ProgressTracker(total_entities=100)
        tracker.start()

        tracker.update_entity_generated(count=50)
        tracker.update_tokens(10000)

        tracker.reset()

        assert tracker.metrics.entities_generated == 0
        assert tracker.metrics.tokens_consumed == 0
        assert tracker.metrics.start_time is None

    def test_progress_callback(self):
        """Test progress callback functionality"""
        callback_data = []

        def callback(state):
            callback_data.append(state)

        tracker = ProgressTracker(
            total_entities=10,
            progress_callback=callback
        )

        tracker.start()
        tracker.update_entity_generated()

        # Should have received at least 2 callbacks (start + update)
        assert len(callback_data) >= 2
        assert "entities_generated" in callback_data[-1]

    def test_success_rates_with_no_failures(self):
        """Test success rates when there are no failures"""
        tracker = ProgressTracker()
        tracker.start()

        tracker.update_entity_generated(count=10)
        tracker.update_llm_call_success()

        summary = tracker.get_summary()
        assert summary["entity_success_rate"] == 1.0
        assert summary["llm_success_rate"] == 1.0

    def test_zero_division_handling(self):
        """Test handling of zero division cases"""
        tracker = ProgressTracker(total_entities=0, total_timepoints=0)
        tracker.start()

        state = tracker.get_current_state()
        assert state["entity_progress_percent"] == 0.0
        assert state["timepoint_progress_percent"] == 0.0
        assert state["overall_progress_percent"] == 0.0
        assert state["eta_seconds"] is None

    def test_token_rate_calculation(self):
        """Test tokens per second calculation"""
        tracker = ProgressTracker()
        tracker.start()

        tracker.update_tokens(1000)

        # Allow some time to pass
        time.sleep(0.1)

        tracker.complete()

        summary = tracker.get_summary()
        assert summary["tokens_per_second"] > 0
        assert summary["duration_seconds"] > 0
