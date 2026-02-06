"""
Tests for World Management System (Sprint 1.1)

Tests world creation, isolation, retrieval, and deletion.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from generation.world_manager import WorldManager, IsolationMode, WorldMetadata
from generation.config_schema import (
    SimulationConfig,
    EntityConfig,
    CompanyConfig,
    TemporalConfig,
    TemporalMode,
    OutputConfig,
    VariationConfig,
)
from generation.templates.loader import TemplateLoader

_loader = TemplateLoader()


class TestWorldManager:
    """Tests for WorldManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create WorldManager instance for tests"""
        return WorldManager(base_path=temp_dir)

    def test_create_world_separate_db(self, manager):
        """Test creating a world with separate database"""
        world = manager.create_world(
            world_id="test_world_1",
            isolation_mode=IsolationMode.SEPARATE_DB,
            description="Test world"
        )

        assert world.world_id == "test_world_1"
        assert world.isolation_mode == IsolationMode.SEPARATE_DB
        assert world.description == "Test world"
        assert Path(world.db_path).exists()

    def test_create_world_shared_db(self, manager):
        """Test creating a world with shared database"""
        world = manager.create_world(
            world_id="test_world_2",
            isolation_mode=IsolationMode.SHARED_DB_PARTITIONED,
            description="Shared world"
        )

        assert world.world_id == "test_world_2"
        assert world.isolation_mode == IsolationMode.SHARED_DB_PARTITIONED
        assert "shared.db" in world.db_path

    def test_create_world_hybrid_demo(self, manager):
        """Test creating a demo world with hybrid isolation"""
        world = manager.create_world(
            world_id="demo_test",
            isolation_mode=IsolationMode.HYBRID,
            description="Demo world"
        )

        assert world.world_id == "demo_test"
        assert "shared_demo_test.db" in world.db_path

    def test_create_world_hybrid_production(self, manager):
        """Test creating a production world with hybrid isolation"""
        world = manager.create_world(
            world_id="production_world",
            isolation_mode=IsolationMode.HYBRID,
            description="Production world"
        )

        assert world.world_id == "production_world"
        assert "production_world.db" in world.db_path

    def test_create_duplicate_world_fails(self, manager):
        """Test that creating duplicate world raises error"""
        manager.create_world(world_id="test_dup")

        with pytest.raises(ValueError, match="already exists"):
            manager.create_world(world_id="test_dup")

    def test_get_world(self, manager):
        """Test retrieving world metadata"""
        created = manager.create_world(world_id="test_get")
        retrieved = manager.get_world("test_get")

        assert retrieved.world_id == created.world_id
        assert retrieved.isolation_mode == created.isolation_mode

    def test_get_nonexistent_world_fails(self, manager):
        """Test that getting nonexistent world raises error"""
        with pytest.raises(KeyError, match="not found"):
            manager.get_world("nonexistent")

    def test_list_worlds(self, manager):
        """Test listing all worlds"""
        manager.create_world(world_id="world_1")
        manager.create_world(world_id="world_2")
        manager.create_world(world_id="world_3")

        worlds = manager.list_worlds()
        assert len(worlds) == 3

        world_ids = {w.world_id for w in worlds}
        assert world_ids == {"world_1", "world_2", "world_3"}

    def test_delete_world_separate_db(self, manager):
        """Test deleting a world with separate database"""
        world = manager.create_world(
            world_id="test_delete",
            isolation_mode=IsolationMode.SEPARATE_DB
        )
        db_path = Path(world.db_path)

        assert db_path.exists()
        assert manager.world_exists("test_delete")

        manager.delete_world("test_delete", confirm=True)

        assert not db_path.exists()
        assert not manager.world_exists("test_delete")

    def test_delete_world_requires_confirmation(self, manager):
        """Test that deletion requires confirmation"""
        manager.create_world(world_id="test_confirm")

        with pytest.raises(ValueError, match="confirm=True"):
            manager.delete_world("test_confirm", confirm=False)

        # World should still exist
        assert manager.world_exists("test_confirm")

    def test_world_isolation_separate_dbs(self, manager):
        """Test that separate DB worlds are isolated"""
        world1 = manager.create_world(
            world_id="isolated_1",
            isolation_mode=IsolationMode.SEPARATE_DB
        )
        world2 = manager.create_world(
            world_id="isolated_2",
            isolation_mode=IsolationMode.SEPARATE_DB
        )

        # Different database files
        assert world1.db_path != world2.db_path
        assert Path(world1.db_path).exists()
        assert Path(world2.db_path).exists()

    def test_world_isolation_shared_db(self, manager):
        """Test that shared DB worlds use same file"""
        world1 = manager.create_world(
            world_id="shared_1",
            isolation_mode=IsolationMode.SHARED_DB_PARTITIONED
        )
        world2 = manager.create_world(
            world_id="shared_2",
            isolation_mode=IsolationMode.SHARED_DB_PARTITIONED
        )

        # Same database file
        assert world1.db_path == world2.db_path
        assert Path(world1.db_path).exists()

    def test_get_world_engine(self, manager):
        """Test getting SQLAlchemy engine for a world"""
        manager.create_world(world_id="test_engine")
        engine = manager.get_world_engine("test_engine")

        assert engine is not None
        assert str(engine.url).startswith("sqlite:///")

    def test_get_world_session(self, manager):
        """Test getting SQLModel session for a world"""
        manager.create_world(world_id="test_session")
        session = manager.get_world_session("test_session")

        assert session is not None

    def test_world_exists(self, manager):
        """Test checking if world exists"""
        assert not manager.world_exists("nonexistent")

        manager.create_world(world_id="exists_test")
        assert manager.world_exists("exists_test")

        manager.delete_world("exists_test", confirm=True)
        assert not manager.world_exists("exists_test")

    def test_get_world_stats(self, manager):
        """Test getting statistics for a world"""
        manager.create_world(world_id="stats_test")
        stats = manager.get_world_stats("stats_test")

        assert "entities" in stats
        assert "timepoints" in stats
        assert "dialogs" in stats
        assert "exposure_events" in stats

        # Empty world should have zero counts
        assert all(count == 0 for count in stats.values())

    def test_clone_world_separate_db(self, manager):
        """Test cloning a world with separate database"""
        source = manager.create_world(
            world_id="clone_source",
            isolation_mode=IsolationMode.SEPARATE_DB,
            description="Original world"
        )

        cloned = manager.clone_world(
            source_world_id="clone_source",
            target_world_id="clone_target",
            description="Cloned world"
        )

        assert cloned.world_id == "clone_target"
        assert cloned.isolation_mode == source.isolation_mode
        assert Path(cloned.db_path).exists()
        assert cloned.metadata.get("cloned_from") == "clone_source"

    def test_export_world_sqlite(self, manager, temp_dir):
        """Test exporting a world to SQLite file"""
        manager.create_world(world_id="export_test")
        export_path = Path(temp_dir) / "exported.db"

        manager.export_world("export_test", str(export_path), format="sqlite")

        assert export_path.exists()

    def test_import_world_sqlite(self, manager, temp_dir):
        """Test importing a world from SQLite file"""
        # Create and export a world
        manager.create_world(world_id="import_source")
        export_path = Path(temp_dir) / "import.db"
        manager.export_world("import_source", str(export_path), format="sqlite")

        # Import as new world
        imported = manager.import_world(
            import_path=str(export_path),
            world_id="import_target",
            format="sqlite",
            description="Imported world"
        )

        assert imported.world_id == "import_target"
        assert Path(imported.db_path).exists()

    def test_world_metadata_persistence(self, temp_dir):
        """Test that world metadata persists across manager instances"""
        # Create manager and world
        manager1 = WorldManager(base_path=temp_dir)
        manager1.create_world(
            world_id="persistent",
            description="Persistent world",
            metadata={"key": "value"}
        )

        # Create new manager instance (should load registry)
        manager2 = WorldManager(base_path=temp_dir)
        world = manager2.get_world("persistent")

        assert world.world_id == "persistent"
        assert world.description == "Persistent world"
        assert world.metadata == {"key": "value"}

    def test_concurrent_world_access(self, manager):
        """Test accessing same world from multiple sessions"""
        manager.create_world(world_id="concurrent_test")

        session1 = manager.get_world_session("concurrent_test")
        session2 = manager.get_world_session("concurrent_test")

        # Both sessions should be valid
        assert session1 is not None
        assert session2 is not None

    def test_world_cleanup_on_delete(self, manager):
        """Test that world deletion cleans up all resources"""
        world = manager.create_world(
            world_id="cleanup_test",
            isolation_mode=IsolationMode.SEPARATE_DB
        )
        db_path = Path(world.db_path)

        # Ensure database exists
        assert db_path.exists()

        # Delete world
        manager.delete_world("cleanup_test", confirm=True)

        # Database file should be gone
        assert not db_path.exists()

        # World should not be in registry
        assert "cleanup_test" not in manager.worlds


class TestSimulationConfig:
    """Tests for SimulationConfig schema"""

    def test_config_validation_basic(self):
        """Test basic configuration validation"""
        from generation.config_schema import EntityConfig

        config = SimulationConfig(
            scenario_description="Test scenario",
            world_id="test_world",
            entities=EntityConfig(count=5)
        )

        assert config.scenario_description == "Test scenario"
        assert config.world_id == "test_world"
        assert config.entities.count >= 1

    def test_config_example_board_meeting(self):
        """Test example board meeting configuration"""
        config = _loader.load_template("showcase/board_meeting")

        assert config.world_id == "board_meeting_example"
        assert config.entities.count == 5
        assert config.timepoints.count == 3

    def test_config_example_jefferson_dinner(self):
        """Test example Jefferson dinner configuration"""
        config = _loader.load_template("showcase/jefferson_dinner")

        assert config.world_id == "jefferson_dinner"
        assert config.entities.count == 3
        assert config.timepoints.before_count == 2
        assert config.timepoints.after_count == 2

    def test_config_example_variations(self):
        """Test example variations configuration"""
        config = SimulationConfig(
            scenario_description="Generate variations of a negotiation scenario",
            world_id="negotiation_variations",
            entities=EntityConfig(count=4, types=["human"]),
            timepoints=CompanyConfig(count=2, resolution="hour"),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            outputs=OutputConfig(
                formats=["jsonl"],
                export_ml_dataset=True
            ),
            variations=VariationConfig(
                enabled=True,
                count=100,
                strategies=["vary_personalities", "vary_outcomes"]
            )
        )

        assert config.variations.enabled is True
        assert config.variations.count == 100
        assert "vary_personalities" in config.variations.strategies

    def test_config_entity_count_validation(self):
        """Test entity count validation"""
        with pytest.raises(Exception):  # Pydantic validation error
            SimulationConfig(
                scenario_description="Test",
                world_id="test",
                entities={"count": 0}  # Invalid: too low
            )

    def test_config_invalid_entity_type(self):
        """Test invalid entity type validation"""
        with pytest.raises(Exception):  # Pydantic validation error
            SimulationConfig(
                scenario_description="Test",
                world_id="test",
                entities={"count": 5, "types": ["invalid_type"]}
            )

    def test_config_invalid_temporal_resolution(self):
        """Test invalid temporal resolution validation"""
        with pytest.raises(Exception):  # Pydantic validation error
            SimulationConfig(
                scenario_description="Test",
                world_id="test",
                timepoints={"count": 5, "resolution": "invalid"}
            )

    def test_config_cost_estimation(self):
        """Test cost estimation"""
        config = _loader.load_template("showcase/board_meeting")
        estimate = config.estimate_cost()

        assert "min_usd" in estimate
        assert "max_usd" in estimate
        assert "tokens_estimated" in estimate
        assert estimate["min_usd"] >= 0
        assert estimate["max_usd"] >= estimate["min_usd"]

    def test_config_serialization(self):
        """Test configuration serialization"""
        config = _loader.load_template("showcase/board_meeting")
        data = config.to_dict()

        assert isinstance(data, dict)
        assert "scenario_description" in data
        assert "world_id" in data

        # Deserialize
        config2 = SimulationConfig.from_dict(data)
        assert config2.world_id == config.world_id

    def test_config_coherence_validation(self):
        """Test configuration coherence validation"""
        from generation.config_schema import EntityConfig, VariationConfig

        # This should work
        config = SimulationConfig(
            scenario_description="Test",
            world_id="test",
            entities=EntityConfig(count=5),
            variations=VariationConfig(enabled=True, count=10, strategies=["vary_personalities"])
        )
        assert config.variations.enabled

        # This should fail (variations enabled but no strategies)
        with pytest.raises(Exception):  # Validation error
            SimulationConfig(
                scenario_description="Test",
                world_id="test",
                entities=EntityConfig(count=5),
                variations=VariationConfig(enabled=True, count=10, strategies=[])
            )


@pytest.mark.integration
class TestWorldManagerIntegration:
    """Integration tests for world management"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    def test_full_world_lifecycle(self, temp_dir):
        """Test complete world lifecycle: create, use, delete"""
        manager = WorldManager(base_path=temp_dir)

        # Create world
        world = manager.create_world(
            world_id="lifecycle_test",
            description="Test world lifecycle"
        )
        assert manager.world_exists("lifecycle_test")

        # Get engine and session
        engine = manager.get_world_engine("lifecycle_test")
        assert engine is not None

        session = manager.get_world_session("lifecycle_test")
        assert session is not None

        # Get stats
        stats = manager.get_world_stats("lifecycle_test")
        assert all(count == 0 for count in stats.values())

        # Delete world
        manager.delete_world("lifecycle_test", confirm=True)
        assert not manager.world_exists("lifecycle_test")

    def test_multiple_worlds_coexist(self, temp_dir):
        """Test that multiple worlds can coexist"""
        manager = WorldManager(base_path=temp_dir)

        # Create multiple worlds
        worlds = []
        for i in range(5):
            world = manager.create_world(
                world_id=f"world_{i}",
                isolation_mode=IsolationMode.SEPARATE_DB
            )
            worlds.append(world)

        # All should exist
        all_worlds = manager.list_worlds()
        assert len(all_worlds) == 5

        # All should be accessible
        for i in range(5):
            assert manager.world_exists(f"world_{i}")
            engine = manager.get_world_engine(f"world_{i}")
            assert engine is not None
