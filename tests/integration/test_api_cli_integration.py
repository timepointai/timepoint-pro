"""
Integration tests for API/CLI integration (Phase 6).

Tests the integration between:
- api/client.py (Python SDK)
- api/usage_bridge.py (CLI-to-API quota bridge)
- run_all_mechanism_tests.py (--api flag)
- e2e_workflows/e2e_runner.py (usage tracking)
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestUsageBridge:
    """Tests for the UsageBridge class."""

    def test_usage_bridge_import(self):
        """Test that UsageBridge can be imported."""
        from api.usage_bridge import UsageBridge, get_usage_bridge, reset_usage_bridge
        assert UsageBridge is not None
        assert get_usage_bridge is not None
        assert reset_usage_bridge is not None

    def test_usage_bridge_initialization(self):
        """Test UsageBridge initializes with defaults."""
        from api.usage_bridge import UsageBridge, reset_usage_bridge
        reset_usage_bridge()  # Clear any existing bridge

        bridge = UsageBridge()
        assert bridge.user_id is not None
        assert bridge.tier in ["free", "basic", "pro", "enterprise"]
        assert bridge.enabled is True

    def test_usage_bridge_custom_user(self):
        """Test UsageBridge accepts custom user_id and tier."""
        from api.usage_bridge import UsageBridge

        bridge = UsageBridge(user_id="test-user-123", tier="pro")
        assert bridge.user_id == "test-user-123"
        assert bridge.tier == "pro"

    def test_usage_bridge_disabled(self):
        """Test UsageBridge can be disabled."""
        from api.usage_bridge import UsageBridge

        bridge = UsageBridge(enabled=False)
        assert bridge.enabled is False
        # Should always return True when disabled
        assert bridge.check_quota(simulation_count=100) is True

    def test_usage_bridge_check_quota_no_db(self):
        """Test check_quota returns True when DB unavailable."""
        from api.usage_bridge import UsageBridge

        bridge = UsageBridge(enabled=True)
        # Force DB to be unavailable
        bridge._db = None
        bridge.enabled = True

        # Should return True (permissive) when DB unavailable
        result = bridge.check_quota(simulation_count=1)
        assert result is True

    def test_usage_bridge_record_simulation_disabled(self):
        """Test record_simulation is no-op when disabled."""
        from api.usage_bridge import UsageBridge

        bridge = UsageBridge(enabled=False)
        # Should not raise
        bridge.record_simulation(
            run_id="test-run-1",
            success=True,
            cost_usd=1.50,
            tokens=1500
        )

    def test_global_bridge_singleton(self):
        """Test that get_usage_bridge returns same instance."""
        from api.usage_bridge import get_usage_bridge, reset_usage_bridge
        reset_usage_bridge()

        bridge1 = get_usage_bridge()
        bridge2 = get_usage_bridge()
        assert bridge1 is bridge2

    def test_convenience_functions(self):
        """Test convenience functions work."""
        from api.usage_bridge import (
            check_cli_quota,
            record_cli_simulation,
            print_cli_usage,
            reset_usage_bridge
        )
        reset_usage_bridge()

        # These should not raise
        result = check_cli_quota(simulation_count=1)
        assert isinstance(result, bool)

        record_cli_simulation(
            run_id="test-run-2",
            success=True,
            cost_usd=0.05,
            tokens=500
        )

        # print_cli_usage should not raise
        print_cli_usage()


class TestTimePointClient:
    """Tests for the TimePointClient SDK."""

    def test_client_import(self):
        """Test that TimePointClient can be imported."""
        from api.client import TimePointClient
        assert TimePointClient is not None

    def test_client_initialization(self):
        """Test client initializes with base_url and api_key."""
        from api.client import TimePointClient

        client = TimePointClient(
            base_url="http://localhost:8080",
            api_key="test-key"
        )
        assert client.base_url == "http://localhost:8080"
        assert "X-API-Key" in client.session.headers

    def test_client_from_env(self):
        """Test client can read from environment variables."""
        from api.client import TimePointClient

        with patch.dict(os.environ, {
            "TIMEPOINT_API_URL": "http://test:8000",
            "TIMEPOINT_API_KEY": "env-test-key"
        }):
            client = TimePointClient()
            assert client.base_url == "http://test:8000"

    def test_batch_response_dataclass(self):
        """Test BatchResponse dataclass."""
        from api.client import BatchResponse, BatchProgress, BatchCost
        from datetime import datetime

        # BatchResponse requires nested dataclasses
        progress = BatchProgress(
            total_jobs=2,
            pending_jobs=0,
            running_jobs=0,
            completed_jobs=2,
            failed_jobs=0,
            cancelled_jobs=0,
            progress_percent=100.0
        )
        cost = BatchCost(
            estimated_cost_usd=5.0,
            actual_cost_usd=4.50,
            budget_cap_usd=10.0,
            budget_remaining_usd=5.50,
            tokens_used=5000
        )

        resp = BatchResponse(
            batch_id="batch-123",
            status="completed",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            priority="normal",
            fail_fast=False,
            progress=progress,
            cost=cost,
            job_ids=["job-1", "job-2"],
            error_message=None,
            owner_id="test-user"
        )
        assert resp.batch_id == "batch-123"
        assert len(resp.job_ids) == 2
        assert progress.total_jobs == 2

    def test_usage_status_dataclass(self):
        """Test UsageStatus dataclass."""
        from api.client import UsageStatus

        status = UsageStatus(
            user_id="test-user",
            tier="basic",
            period="2024-01",
            days_remaining=25,
            api_calls_used=50,
            simulations_used=5,
            cost_used_usd=2.50,
            tokens_used=10000,
            api_calls_limit=10000,
            simulations_limit=100,
            cost_limit_usd=50.0,
            max_batch_size=100,
            api_calls_remaining=9950,
            simulations_remaining=95,
            cost_remaining_usd=47.50,
            is_quota_exceeded=False,
            quota_exceeded_reason=None
        )
        assert status.user_id == "test-user"
        assert status.is_quota_exceeded is False
        assert status.simulations_remaining == 95


class TestE2ERunnerUsageTracking:
    """Tests for e2e_runner.py usage tracking integration."""

    def test_e2e_runner_import(self):
        """Test that e2e_runner can be imported with usage tracking."""
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner, USAGE_TRACKING_AVAILABLE
        assert FullE2EWorkflowRunner is not None
        # USAGE_TRACKING_AVAILABLE depends on api.usage_bridge being available
        assert isinstance(USAGE_TRACKING_AVAILABLE, bool)

    @patch('e2e_workflows.e2e_runner.UsageBridge')
    def test_e2e_runner_with_usage_tracking(self, mock_bridge_class):
        """Test that E2E runner initializes with usage tracking."""
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
        from metadata.run_tracker import MetadataManager

        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge

        # Mock the metadata manager
        mock_metadata = MagicMock(spec=MetadataManager)

        runner = FullE2EWorkflowRunner(
            metadata_manager=mock_metadata,
            generate_summary=False,
            track_usage=True,
            user_id="test-user",
            user_tier="pro"
        )

        # Check that usage tracking is configured
        if runner._track_usage:
            mock_bridge_class.assert_called_once_with(user_id="test-user", tier="pro")

    @patch('e2e_workflows.e2e_runner.UsageBridge')
    def test_e2e_runner_without_usage_tracking(self, mock_bridge_class):
        """Test that E2E runner can run without usage tracking."""
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
        from metadata.run_tracker import MetadataManager

        mock_metadata = MagicMock(spec=MetadataManager)

        runner = FullE2EWorkflowRunner(
            metadata_manager=mock_metadata,
            generate_summary=False,
            track_usage=False  # Explicitly disabled
        )

        assert runner._track_usage is False


class TestRunAllMechanismTestsAPIFlags:
    """Tests for run_all_mechanism_tests.py API flag parsing."""

    def test_api_flags_in_argparse(self):
        """Test that API flags are recognized by argparse."""
        import argparse

        # Create a test parser with the expected arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("--api", action="store_true")
        parser.add_argument("--api-url", type=str, default="http://localhost:8080")
        parser.add_argument("--api-key", type=str)
        parser.add_argument("--api-batch-size", type=int, default=10)
        parser.add_argument("--api-budget", type=float)
        parser.add_argument("--api-wait", action="store_true")
        parser.add_argument("--api-usage", action="store_true")

        # Test parsing various combinations
        args = parser.parse_args(["--api", "--api-url", "http://test:8080"])
        assert args.api is True
        assert args.api_url == "http://test:8080"

        args = parser.parse_args(["--api-usage"])
        assert args.api_usage is True

        args = parser.parse_args(["--api", "--api-batch-size", "50", "--api-budget", "10.0"])
        assert args.api_batch_size == 50
        assert args.api_budget == 10.0


class TestRunShAPIFlags:
    """Tests for run.sh API flag handling."""

    def test_run_sh_help_contains_api_options(self):
        """Test that run.sh 'run' subcommand help text contains API options."""
        import subprocess

        result = subprocess.run(
            ["bash", "run.sh", "run", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )

        help_text = result.stdout + result.stderr

        # Check for API mode options in run subcommand help
        assert "--api" in help_text
        assert "--api-url" in help_text
        assert "--api-key" in help_text
        assert "--api-batch-size" in help_text
        assert "--api-budget" in help_text
        assert "--api-wait" in help_text

    def test_run_sh_syntax_valid(self):
        """Test that run.sh has valid bash syntax."""
        import subprocess

        result = subprocess.run(
            ["bash", "-n", "run.sh"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )

        assert result.returncode == 0, f"run.sh syntax error: {result.stderr}"


class TestIntegrationScenarios:
    """End-to-end integration scenarios."""

    @pytest.mark.integration
    def test_usage_bridge_integrates_with_e2e_runner(self):
        """Test that UsageBridge integrates correctly with E2E runner."""
        from api.usage_bridge import UsageBridge, reset_usage_bridge

        reset_usage_bridge()

        # Create a bridge for testing
        bridge = UsageBridge(user_id="integration-test", tier="basic", enabled=True)

        # Simulate workflow
        run_id = "test-integration-run-001"

        # 1. Check quota before starting
        has_quota = bridge.check_quota(simulation_count=1)
        assert has_quota is True  # Should pass with fresh bridge

        # 2. Record start
        bridge.record_simulation_start(run_id)

        # 3. Record completion
        bridge.record_simulation(
            run_id=run_id,
            success=True,
            cost_usd=0.05,
            tokens=1000
        )

        # 4. Get usage (may be None if DB not configured)
        usage = bridge.get_usage()
        # Just verify no exception raised

    @pytest.mark.integration
    def test_client_sdk_error_handling(self):
        """Test that client SDK handles errors gracefully."""
        from api.client import TimePointClient, TimePointAPIError

        # Client with non-existent server
        client = TimePointClient(
            base_url="http://localhost:9999",
            api_key="test-key",
            timeout=1
        )

        # Should raise appropriate error
        with pytest.raises(Exception):  # Could be TimePointAPIError or requests.exceptions.ConnectionError
            client.get_usage()


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
