"""
Unit tests for the simulation runner.

Tests job creation, tracking, and management (not actual simulation execution).
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from api.models_simulation import (
    SimulationCreateRequest,
    SimulationStatus,
    TemporalModeAPI,
)
from api.simulation_runner import (
    SimulationJob,
    get_job,
    save_job,
    list_jobs,
    delete_job,
    clear_jobs,
    SimulationRunner,
    get_simulation_runner,
    reset_simulation_runner,
)


class TestSimulationJob:
    """Tests for SimulationJob data class."""

    def test_create_job(self):
        """Test creating a job."""
        job = SimulationJob(
            job_id="test_job_1",
            owner_id="user1",
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        assert job.job_id == "test_job_1"
        assert job.owner_id == "user1"
        assert job.status == SimulationStatus.PENDING
        assert job.progress_percent == 0.0
        assert job.error_message is None

    def test_job_default_values(self):
        """Test default values for job."""
        job = SimulationJob(
            job_id="test_job_2",
            owner_id="user1",
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        assert job.entity_count == 4
        assert job.timepoint_count == 5
        assert job.temporal_mode == "pearl"
        assert job.generate_summaries is True
        assert job.export_formats == ["json", "markdown"]


class TestJobStorage:
    """Tests for job storage functions."""

    def setup_method(self):
        """Clear jobs before each test."""
        clear_jobs()

    def teardown_method(self):
        """Clear jobs after each test."""
        clear_jobs()

    def test_save_and_get_job(self):
        """Test saving and retrieving a job."""
        job = SimulationJob(
            job_id="test_job_1",
            owner_id="user1",
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        save_job(job)
        retrieved = get_job("test_job_1")

        assert retrieved is not None
        assert retrieved.job_id == "test_job_1"

    def test_get_nonexistent_job(self):
        """Test retrieving nonexistent job returns None."""
        assert get_job("nonexistent") is None

    def test_list_jobs(self):
        """Test listing jobs."""
        for i in range(5):
            job = SimulationJob(
                job_id=f"job_{i}",
                owner_id="user1",
                status=SimulationStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            save_job(job)

        jobs, total = list_jobs()
        assert total == 5
        assert len(jobs) == 5

    def test_list_jobs_with_owner_filter(self):
        """Test listing jobs filtered by owner."""
        save_job(SimulationJob(
            job_id="job_1",
            owner_id="user1",
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
        ))
        save_job(SimulationJob(
            job_id="job_2",
            owner_id="user2",
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
        ))

        jobs, total = list_jobs(owner_id="user1")
        assert total == 1
        assert jobs[0].owner_id == "user1"

    def test_list_jobs_with_status_filter(self):
        """Test listing jobs filtered by status."""
        save_job(SimulationJob(
            job_id="job_1",
            owner_id="user1",
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
        ))
        save_job(SimulationJob(
            job_id="job_2",
            owner_id="user1",
            status=SimulationStatus.COMPLETED,
            created_at=datetime.utcnow(),
        ))

        jobs, total = list_jobs(status=SimulationStatus.PENDING)
        assert total == 1
        assert jobs[0].status == SimulationStatus.PENDING

    def test_list_jobs_with_pagination(self):
        """Test listing jobs with pagination."""
        for i in range(10):
            job = SimulationJob(
                job_id=f"job_{i:02d}",
                owner_id="user1",
                status=SimulationStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            save_job(job)

        jobs, total = list_jobs(limit=3, offset=0)
        assert total == 10
        assert len(jobs) == 3

        jobs, total = list_jobs(limit=3, offset=3)
        assert total == 10
        assert len(jobs) == 3

    def test_delete_job(self):
        """Test deleting a job."""
        job = SimulationJob(
            job_id="test_job",
            owner_id="user1",
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        save_job(job)

        assert delete_job("test_job") is True
        assert get_job("test_job") is None

    def test_delete_nonexistent_job(self):
        """Test deleting nonexistent job returns False."""
        assert delete_job("nonexistent") is False


class TestSimulationRunner:
    """Tests for SimulationRunner class."""

    def setup_method(self):
        """Reset runner before each test."""
        reset_simulation_runner()

    def teardown_method(self):
        """Reset runner after each test."""
        reset_simulation_runner()

    def test_create_job_from_template(self):
        """Test creating job from template ID."""
        runner = get_simulation_runner()

        request = SimulationCreateRequest(
            template_id="board_meeting",
            entity_count=5,
            timepoint_count=3,
        )

        job = runner.create_job(request, "user1")

        assert job.job_id.startswith("sim_")
        assert job.owner_id == "user1"
        assert job.status == SimulationStatus.PENDING
        assert job.template_id == "board_meeting"
        assert job.entity_count == 5
        assert job.timepoint_count == 3

    def test_create_job_from_description(self):
        """Test creating job from natural language description."""
        runner = get_simulation_runner()

        request = SimulationCreateRequest(
            description="A board meeting where executives discuss merger options",
            entity_count=4,
        )

        job = runner.create_job(request, "user1")

        assert job.job_id.startswith("sim_")
        assert job.description == "A board meeting where executives discuss merger options"
        assert job.template_id is None

    def test_get_stats(self):
        """Test getting runner statistics."""
        runner = get_simulation_runner()

        # Create some jobs
        for i, status in enumerate([
            SimulationStatus.PENDING,
            SimulationStatus.RUNNING,
            SimulationStatus.COMPLETED,
            SimulationStatus.FAILED,
        ]):
            job = SimulationJob(
                job_id=f"job_{i}",
                owner_id="user1",
                status=status,
                created_at=datetime.utcnow(),
            )
            if status == SimulationStatus.COMPLETED:
                job.cost_usd = 0.05
                job.tokens_used = 1000
            save_job(job)

        stats = runner.get_stats()

        assert stats["total_jobs"] == 4
        assert stats["pending_jobs"] == 1
        assert stats["running_jobs"] == 1
        assert stats["completed_jobs"] == 1
        assert stats["failed_jobs"] == 1
        assert stats["total_cost_usd"] == 0.05
        assert stats["total_tokens"] == 1000

    def test_get_stats_filtered_by_owner(self):
        """Test getting stats filtered by owner."""
        runner = get_simulation_runner()

        save_job(SimulationJob(
            job_id="job_1",
            owner_id="user1",
            status=SimulationStatus.COMPLETED,
            created_at=datetime.utcnow(),
            cost_usd=0.10,
        ))
        save_job(SimulationJob(
            job_id="job_2",
            owner_id="user2",
            status=SimulationStatus.COMPLETED,
            created_at=datetime.utcnow(),
            cost_usd=0.20,
        ))

        stats = runner.get_stats(owner_id="user1")

        assert stats["total_jobs"] == 1
        assert stats["total_cost_usd"] == 0.10


class TestSimulationCreateRequest:
    """Tests for SimulationCreateRequest validation."""

    def test_valid_request_with_template(self):
        """Test valid request with template ID."""
        request = SimulationCreateRequest(
            template_id="board_meeting",
        )
        assert request.template_id == "board_meeting"

    def test_valid_request_with_description(self):
        """Test valid request with description."""
        request = SimulationCreateRequest(
            description="Test simulation",
        )
        assert request.description == "Test simulation"

    def test_invalid_request_no_source(self):
        """Test that request without template or description raises error."""
        with pytest.raises(ValueError):
            SimulationCreateRequest()

    def test_entity_count_bounds(self):
        """Test entity count validation."""
        # Valid
        request = SimulationCreateRequest(
            template_id="test",
            entity_count=10,
        )
        assert request.entity_count == 10

        # Too low
        with pytest.raises(ValueError):
            SimulationCreateRequest(
                template_id="test",
                entity_count=0,
            )

        # Too high
        with pytest.raises(ValueError):
            SimulationCreateRequest(
                template_id="test",
                entity_count=25,
            )

    def test_export_formats_validation(self):
        """Test export formats validation."""
        # Valid formats
        request = SimulationCreateRequest(
            template_id="test",
            export_formats=["json", "markdown", "pdf"],
        )
        assert "json" in request.export_formats

        # Invalid format
        with pytest.raises(ValueError):
            SimulationCreateRequest(
                template_id="test",
                export_formats=["invalid_format"],
            )
