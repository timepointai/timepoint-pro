"""
Tests for Checkpoint Management (Sprint 1.4)

Tests checkpoint creation, resume functionality, cleanup, and corruption handling.
"""

import pytest
import tempfile
import json
from pathlib import Path

from generation.checkpoint_manager import CheckpointManager


class TestCheckpointCreation:
    """Tests for checkpoint creation"""

    def test_create_checkpoint(self):
        """Test creating a checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            metadata = {
                "config": {"entities": 100},
                "random_seed": 42
            }

            manager.create_checkpoint(job_id="job_1", metadata=metadata)

            assert manager.has_checkpoint("job_1")

    def test_checkpoint_metadata_saved(self):
        """Test checkpoint metadata is saved to disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            metadata = {
                "config": {"entities": 100},
                "random_seed": 42
            }

            manager.create_checkpoint(job_id="job_1", metadata=metadata)

            # Verify metadata file exists
            metadata_path = Path(tmpdir) / "job_1_metadata.json"
            assert metadata_path.exists()

            # Verify metadata content
            with open(metadata_path, 'r') as f:
                saved_metadata = json.load(f)

            assert saved_metadata["job_id"] == "job_1"
            assert saved_metadata["metadata"] == metadata

    def test_has_checkpoint(self):
        """Test checking if checkpoint exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            assert not manager.has_checkpoint("job_1")

            manager.create_checkpoint(job_id="job_1", metadata={})

            assert manager.has_checkpoint("job_1")


class TestCheckpointSaving:
    """Tests for saving checkpoints"""

    def test_save_checkpoint(self):
        """Test saving a checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint(job_id="job_1", metadata={})
            manager.update_progress("job_1", items_completed=10)

            state = {"entities": ["alice", "bob"]}
            manager.save_checkpoint("job_1", state=state)

            # Verify checkpoint file exists
            checkpoint_path = Path(tmpdir) / "job_1_checkpoint_0.json"
            assert checkpoint_path.exists()

    def test_save_checkpoint_without_create_raises_error(self):
        """Test saving checkpoint without creating first raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            with pytest.raises(ValueError, match="No checkpoint metadata"):
                manager.save_checkpoint("job_1", state={})

    def test_multiple_checkpoints(self):
        """Test saving multiple checkpoints"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint(job_id="job_1", metadata={})

            # Save 3 checkpoints
            for i in range(3):
                manager.update_progress("job_1", items_completed=(i+1)*10)
                manager.save_checkpoint("job_1", state={"step": i})

            # Verify all 3 checkpoint files exist
            for i in range(3):
                checkpoint_path = Path(tmpdir) / f"job_1_checkpoint_{i}.json"
                assert checkpoint_path.exists()

    def test_checkpoint_metadata_updates(self):
        """Test checkpoint metadata updates after saving"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint(job_id="job_1", metadata={})
            initial_metadata = manager.get_checkpoint_metadata("job_1")
            assert initial_metadata["checkpoint_count"] == 0

            manager.save_checkpoint("job_1", state={})
            updated_metadata = manager.get_checkpoint_metadata("job_1")
            assert updated_metadata["checkpoint_count"] == 1
            assert updated_metadata["last_checkpoint_at"] is not None


class TestCheckpointLoading:
    """Tests for loading checkpoints"""

    def test_load_checkpoint(self):
        """Test loading a checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint(job_id="job_1", metadata={"seed": 42})
            manager.update_progress("job_1", items_completed=50)

            state = {"entities": ["alice", "bob", "charlie"]}
            manager.save_checkpoint("job_1", state=state)

            # Load checkpoint
            loaded = manager.load_checkpoint("job_1")

            assert loaded["job_id"] == "job_1"
            assert loaded["items_completed"] == 50
            assert loaded["state"] == state
            assert loaded["metadata"]["seed"] == 42

    def test_load_latest_checkpoint(self):
        """Test loading returns most recent checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint(job_id="job_1", metadata={})

            # Save multiple checkpoints
            for i in range(3):
                manager.save_checkpoint("job_1", state={"step": i})

            # Load should return the latest (step 2)
            loaded = manager.load_checkpoint("job_1")
            assert loaded["state"]["step"] == 2

    def test_load_nonexistent_checkpoint_raises_error(self):
        """Test loading nonexistent checkpoint raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            with pytest.raises(ValueError, match="No checkpoint found"):
                manager.load_checkpoint("nonexistent_job")


class TestCheckpointCleanup:
    """Tests for checkpoint cleanup"""

    def test_automatic_cleanup_old_checkpoints(self):
        """Test automatic cleanup of old checkpoints"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(
                checkpoint_dir=tmpdir,
                max_checkpoints_per_job=3
            )

            manager.create_checkpoint(job_id="job_1", metadata={})

            # Save 5 checkpoints
            for i in range(5):
                manager.save_checkpoint("job_1", state={"step": i})

            # Should only keep latest 3
            checkpoint_dir = Path(tmpdir)
            checkpoints = list(checkpoint_dir.glob("job_1_checkpoint_*.json"))
            assert len(checkpoints) == 3

            # Oldest (0, 1) should be deleted, keeping (2, 3, 4)
            assert not (checkpoint_dir / "job_1_checkpoint_0.json").exists()
            assert not (checkpoint_dir / "job_1_checkpoint_1.json").exists()
            assert (checkpoint_dir / "job_1_checkpoint_2.json").exists()
            assert (checkpoint_dir / "job_1_checkpoint_3.json").exists()
            assert (checkpoint_dir / "job_1_checkpoint_4.json").exists()

    def test_delete_checkpoint(self):
        """Test deleting all checkpoints for a job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint(job_id="job_1", metadata={})
            manager.save_checkpoint("job_1", state={})

            assert manager.has_checkpoint("job_1")

            manager.delete_checkpoint("job_1")

            assert not manager.has_checkpoint("job_1")

            # Verify files are deleted
            checkpoint_dir = Path(tmpdir)
            assert not (checkpoint_dir / "job_1_metadata.json").exists()
            assert not (checkpoint_dir / "job_1_checkpoint_0.json").exists()


class TestProgressTracking:
    """Tests for progress tracking in checkpoints"""

    def test_update_progress(self):
        """Test updating progress counter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint(job_id="job_1", metadata={})

            manager.update_progress("job_1", items_completed=25)
            assert manager._checkpoint_metadata["job_1"]["items_completed"] == 25

            manager.update_progress("job_1", items_completed=50)
            assert manager._checkpoint_metadata["job_1"]["items_completed"] == 50

    def test_should_save_checkpoint(self):
        """Test auto-save interval checking"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(
                checkpoint_dir=tmpdir,
                auto_save_interval=10
            )

            manager.create_checkpoint(job_id="job_1", metadata={})

            # Should save at multiples of 10
            manager.update_progress("job_1", items_completed=10)
            assert manager.should_save_checkpoint("job_1")

            manager.update_progress("job_1", items_completed=15)
            assert not manager.should_save_checkpoint("job_1")

            manager.update_progress("job_1", items_completed=20)
            assert manager.should_save_checkpoint("job_1")


class TestCheckpointListing:
    """Tests for listing checkpoints"""

    def test_list_all_checkpoints(self):
        """Test listing all checkpoints"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint("job_1", metadata={"type": "horizontal"})
            manager.create_checkpoint("job_2", metadata={"type": "vertical"})

            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) == 2

            job_ids = [cp["job_id"] for cp in checkpoints]
            assert "job_1" in job_ids
            assert "job_2" in job_ids

    def test_list_specific_job_checkpoints(self):
        """Test listing checkpoints for specific job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint("job_1", metadata={})
            manager.create_checkpoint("job_2", metadata={})

            checkpoints = manager.list_checkpoints(job_id="job_1")
            assert len(checkpoints) == 1
            assert checkpoints[0]["job_id"] == "job_1"

    def test_list_empty_checkpoints(self):
        """Test listing when no checkpoints exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) == 0


class TestCheckpointIntegrity:
    """Tests for checkpoint integrity verification"""

    def test_verify_valid_checkpoint(self):
        """Test verifying valid checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint("job_1", metadata={})
            manager.save_checkpoint("job_1", state={})

            result = manager.verify_checkpoint_integrity("job_1")
            assert result["is_valid"] is True
            assert len(result["errors"]) == 0
            assert result["checkpoint_count"] == 1

    def test_verify_nonexistent_checkpoint(self):
        """Test verifying nonexistent checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            result = manager.verify_checkpoint_integrity("nonexistent")
            assert result["is_valid"] is False
            assert "No checkpoint found" in result["errors"][0]

    def test_verify_corrupted_checkpoint(self):
        """Test verifying corrupted checkpoint file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint("job_1", metadata={})
            manager.save_checkpoint("job_1", state={})

            # Corrupt the checkpoint file
            checkpoint_path = Path(tmpdir) / "job_1_checkpoint_0.json"
            with open(checkpoint_path, 'w') as f:
                f.write("invalid json{{{")

            result = manager.verify_checkpoint_integrity("job_1")
            assert result["is_valid"] is False
            assert any("corrupted" in error for error in result["errors"])


class TestCheckpointResume:
    """Integration tests for checkpoint resume workflow"""

    def test_resume_from_checkpoint(self):
        """Test complete resume workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            # Simulate job that fails partway through
            manager.create_checkpoint("job_1", metadata={"total": 100})

            # Process 50 items, then "crash"
            processed_items = []
            for i in range(50):
                processed_items.append(f"item_{i}")
                manager.update_progress("job_1", items_completed=i+1)

                if (i+1) % 10 == 0:
                    manager.save_checkpoint("job_1", state={"processed": processed_items})

            # Simulate restart - load checkpoint
            checkpoint = manager.load_checkpoint("job_1")
            resume_from = checkpoint["items_completed"]
            previous_items = checkpoint["state"]["processed"]

            assert resume_from == 50
            assert len(previous_items) == 50

            # Continue processing from checkpoint
            for i in range(resume_from, 100):
                previous_items.append(f"item_{i}")

            # Verify all items processed
            assert len(previous_items) == 100

    def test_multiple_job_checkpoints_isolated(self):
        """Test multiple jobs have isolated checkpoints"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint("job_1", metadata={"type": "horizontal"})
            manager.create_checkpoint("job_2", metadata={"type": "vertical"})

            manager.save_checkpoint("job_1", state={"data": "job1_data"})
            manager.save_checkpoint("job_2", state={"data": "job2_data"})

            # Load job_1 checkpoint
            job1_checkpoint = manager.load_checkpoint("job_1")
            assert job1_checkpoint["state"]["data"] == "job1_data"
            assert job1_checkpoint["metadata"]["type"] == "horizontal"

            # Load job_2 checkpoint
            job2_checkpoint = manager.load_checkpoint("job_2")
            assert job2_checkpoint["state"]["data"] == "job2_data"
            assert job2_checkpoint["metadata"]["type"] == "vertical"


class TestCheckpointMetadata:
    """Tests for checkpoint metadata management"""

    def test_get_checkpoint_metadata(self):
        """Test getting checkpoint metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            manager.create_checkpoint("job_1", metadata={"seed": 42, "config": {}})

            metadata = manager.get_checkpoint_metadata("job_1")
            assert metadata["job_id"] == "job_1"
            assert metadata["metadata"]["seed"] == 42

    def test_get_metadata_nonexistent_raises_error(self):
        """Test getting metadata for nonexistent job raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)

            with pytest.raises(ValueError, match="No checkpoint found"):
                manager.get_checkpoint_metadata("nonexistent")
