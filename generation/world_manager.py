"""
World Management System for Simulation Isolation

Provides isolated namespaces for simulations with three isolation modes:
- SEPARATE_DB: Each world gets its own SQLite file
- SHARED_DB_PARTITIONED: Single DB with world_id partitioning
- HYBRID: Separate DBs for production, shared for demos/tests

This enables clean separation between demo/test/user data.
"""

import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import create_engine, Session, select, SQLModel
from sqlalchemy import text


class IsolationMode(str, Enum):
    """World isolation strategies"""
    SEPARATE_DB = "separate_db"  # Each world has its own database file
    SHARED_DB_PARTITIONED = "shared_db_partitioned"  # Single DB with world_id column
    HYBRID = "hybrid"  # Separate for production, shared for demo/test


class WorldMetadata:
    """Metadata for a simulation world"""
    def __init__(
        self,
        world_id: str,
        isolation_mode: IsolationMode,
        created_at: datetime,
        db_path: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.world_id = world_id
        self.isolation_mode = isolation_mode
        self.created_at = created_at
        self.db_path = db_path
        self.description = description
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "world_id": self.world_id,
            "isolation_mode": self.isolation_mode.value,
            "created_at": self.created_at.isoformat(),
            "db_path": self.db_path,
            "description": self.description,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldMetadata":
        """Create from dictionary"""
        return cls(
            world_id=data["world_id"],
            isolation_mode=IsolationMode(data["isolation_mode"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            db_path=data["db_path"],
            description=data.get("description"),
            metadata=data.get("metadata")
        )


class WorldManager:
    """
    Manage isolated simulation worlds with configurable isolation.

    Example:
        # Create world manager
        manager = WorldManager(
            base_path="./worlds",
            default_isolation=IsolationMode.SEPARATE_DB
        )

        # Create a new world
        world = manager.create_world(
            world_id="jefferson_dinner",
            description="Historical simulation of 1790 compromise dinner"
        )

        # Get database connection for world
        engine = manager.get_world_engine("jefferson_dinner")

        # List all worlds
        worlds = manager.list_worlds()

        # Delete a world
        manager.delete_world("jefferson_dinner")
    """

    def __init__(
        self,
        base_path: str = "./worlds",
        default_isolation: IsolationMode = IsolationMode.SEPARATE_DB
    ):
        """
        Initialize world manager.

        Args:
            base_path: Base directory for world storage
            default_isolation: Default isolation mode for new worlds
        """
        self.base_path = Path(base_path)
        self.default_isolation = default_isolation
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Registry file to track worlds
        self.registry_path = self.base_path / "world_registry.json"
        self._load_registry()

    def _load_registry(self):
        """Load world registry from disk"""
        import json

        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                self.worlds = {
                    k: WorldMetadata.from_dict(v)
                    for k, v in data.items()
                }
        else:
            self.worlds = {}

    def _save_registry(self):
        """Save world registry to disk"""
        import json

        with open(self.registry_path, 'w') as f:
            json.dump(
                {k: v.to_dict() for k, v in self.worlds.items()},
                f,
                indent=2
            )

    def create_world(
        self,
        world_id: str,
        isolation_mode: Optional[IsolationMode] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorldMetadata:
        """
        Create a new simulation world.

        Args:
            world_id: Unique identifier for the world
            isolation_mode: Isolation mode (defaults to manager's default)
            description: Human-readable description
            metadata: Additional metadata

        Returns:
            WorldMetadata object

        Raises:
            ValueError: If world already exists
        """
        if world_id in self.worlds:
            raise ValueError(f"World '{world_id}' already exists")

        isolation_mode = isolation_mode or self.default_isolation

        # Determine database path based on isolation mode
        if isolation_mode == IsolationMode.SEPARATE_DB:
            db_path = str(self.base_path / f"{world_id}.db")
        elif isolation_mode == IsolationMode.HYBRID:
            # Use separate DB for user worlds, shared for demo/test
            if world_id.startswith(("demo_", "test_")):
                db_path = str(self.base_path / "shared_demo_test.db")
            else:
                db_path = str(self.base_path / f"{world_id}.db")
        else:  # SHARED_DB_PARTITIONED
            db_path = str(self.base_path / "shared.db")

        # Create world metadata
        world_metadata = WorldMetadata(
            world_id=world_id,
            isolation_mode=isolation_mode,
            created_at=datetime.utcnow(),
            db_path=db_path,
            description=description,
            metadata=metadata
        )

        # Initialize database
        self._initialize_world_database(world_id, db_path, isolation_mode)

        # Register world
        self.worlds[world_id] = world_metadata
        self._save_registry()

        return world_metadata

    def _initialize_world_database(
        self,
        world_id: str,
        db_path: str,
        isolation_mode: IsolationMode
    ):
        """Initialize database schema for a world"""
        # Import all SQLModel tables
        from schemas import (
            Entity, Timeline, Timepoint, ExposureEvent, QueryHistory,
            Dialog, RelationshipTrajectory, ProspectiveState,
            EnvironmentEntity, AtmosphereEntity, CrowdEntity,
            SystemPrompt, ValidationRule
        )

        # Create engine
        engine = create_engine(f"sqlite:///{db_path}")

        # Create tables
        SQLModel.metadata.create_all(engine)

        # For SHARED_DB_PARTITIONED, we need to add world_id columns
        if isolation_mode == IsolationMode.SHARED_DB_PARTITIONED:
            self._add_world_id_columns(engine, world_id)

    def _add_world_id_columns(self, engine, world_id: str):
        """Add world_id columns to tables for partitioned isolation"""
        # Table names are hardcoded — safe for interpolation.
        # world_id is validated to prevent SQL injection via the DEFAULT clause.
        tables = [
            "entity", "timeline", "timepoint", "exposureevent",
            "queryhistory", "dialog", "relationshiptrajectory",
            "prospectivestate", "environmententity", "atmosphereentity",
            "crowdentity", "systemprompt", "validationrule"
        ]

        # Validate world_id contains only safe characters (alphanumeric, dash, underscore)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', world_id):
            raise ValueError(f"Invalid world_id format: {world_id}")

        with engine.begin() as conn:
            for table in tables:
                # Check if world_id column exists
                result = conn.execute(text(
                    f"PRAGMA table_info({table})"
                ))
                columns = [row[1] for row in result]

                if "world_id" not in columns:
                    # Add world_id column with default
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN world_id TEXT DEFAULT :world_id"
                    ), {"world_id": world_id})

                    # Create index on world_id
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS idx_{table}_world_id ON {table}(world_id)"
                    ))

    def get_world(self, world_id: str) -> WorldMetadata:
        """
        Get metadata for a world.

        Args:
            world_id: World identifier

        Returns:
            WorldMetadata object

        Raises:
            KeyError: If world doesn't exist
        """
        if world_id not in self.worlds:
            raise KeyError(f"World '{world_id}' not found")
        return self.worlds[world_id]

    def list_worlds(self) -> List[WorldMetadata]:
        """
        List all worlds.

        Returns:
            List of WorldMetadata objects
        """
        return list(self.worlds.values())

    def delete_world(
        self,
        world_id: str,
        confirm: bool = False
    ):
        """
        Delete a world and its data.

        Args:
            world_id: World identifier
            confirm: Must be True to actually delete

        Raises:
            ValueError: If confirm is False
            KeyError: If world doesn't exist
        """
        if not confirm:
            raise ValueError("Must set confirm=True to delete world")

        if world_id not in self.worlds:
            raise KeyError(f"World '{world_id}' not found")

        world = self.worlds[world_id]

        # Handle deletion based on isolation mode
        if world.isolation_mode == IsolationMode.SEPARATE_DB:
            # Delete the database file
            db_file = Path(world.db_path)
            if db_file.exists():
                db_file.unlink()

        elif world.isolation_mode == IsolationMode.SHARED_DB_PARTITIONED:
            # Delete rows with this world_id
            self._delete_world_data_from_shared_db(world_id, world.db_path)

        elif world.isolation_mode == IsolationMode.HYBRID:
            # Check if it's a dedicated DB or shared
            if world_id.startswith(("demo_", "test_")):
                # Shared DB - delete rows
                self._delete_world_data_from_shared_db(world_id, world.db_path)
            else:
                # Dedicated DB - delete file
                db_file = Path(world.db_path)
                if db_file.exists():
                    db_file.unlink()

        # Remove from registry
        del self.worlds[world_id]
        self._save_registry()

    def _delete_world_data_from_shared_db(self, world_id: str, db_path: str):
        """Delete all data for a world from a shared database"""
        engine = create_engine(f"sqlite:///{db_path}")

        tables = [
            "entity", "timeline", "timepoint", "exposureevent",
            "queryhistory", "dialog", "relationshiptrajectory",
            "prospectivestate", "environmententity", "atmosphereentity",
            "crowdentity", "systemprompt", "validationrule"
        ]

        with engine.begin() as conn:
            for table in tables:
                conn.execute(text(
                    f"DELETE FROM {table} WHERE world_id = :world_id"
                ), {"world_id": world_id})

    def get_world_engine(self, world_id: str):
        """
        Get SQLAlchemy engine for a world's database.

        Args:
            world_id: World identifier

        Returns:
            SQLAlchemy Engine object

        Raises:
            KeyError: If world doesn't exist
        """
        world = self.get_world(world_id)
        engine = create_engine(f"sqlite:///{world.db_path}")
        return engine

    def get_world_session(self, world_id: str) -> Session:
        """
        Get SQLModel session for a world's database.

        Args:
            world_id: World identifier

        Returns:
            SQLModel Session object

        Raises:
            KeyError: If world doesn't exist
        """
        engine = self.get_world_engine(world_id)
        return Session(engine)

    def world_exists(self, world_id: str) -> bool:
        """
        Check if a world exists.

        Args:
            world_id: World identifier

        Returns:
            True if world exists, False otherwise
        """
        return world_id in self.worlds

    def get_world_stats(self, world_id: str) -> Dict[str, int]:
        """
        Get statistics for a world.

        Args:
            world_id: World identifier

        Returns:
            Dictionary with counts: entities, timepoints, dialogs, etc.

        Raises:
            KeyError: If world doesn't exist
        """
        from schemas import Entity, Timepoint, Dialog, ExposureEvent

        engine = self.get_world_engine(world_id)
        world = self.get_world(world_id)

        stats = {
            "entities": 0,
            "timepoints": 0,
            "dialogs": 0,
            "exposure_events": 0
        }

        with Session(engine) as session:
            if world.isolation_mode == IsolationMode.SHARED_DB_PARTITIONED:
                # Filter by world_id (if column exists)
                # For now, just count all rows
                stats["entities"] = len(session.exec(select(Entity)).all())
                stats["timepoints"] = len(session.exec(select(Timepoint)).all())
                stats["dialogs"] = len(session.exec(select(Dialog)).all())
                stats["exposure_events"] = len(session.exec(select(ExposureEvent)).all())
            else:
                # Count all rows (dedicated DB)
                stats["entities"] = len(session.exec(select(Entity)).all())
                stats["timepoints"] = len(session.exec(select(Timepoint)).all())
                stats["dialogs"] = len(session.exec(select(Dialog)).all())
                stats["exposure_events"] = len(session.exec(select(ExposureEvent)).all())

        return stats

    def clone_world(
        self,
        source_world_id: str,
        target_world_id: str,
        description: Optional[str] = None
    ) -> WorldMetadata:
        """
        Clone an existing world.

        Args:
            source_world_id: World to clone from
            target_world_id: New world identifier
            description: Description for new world

        Returns:
            WorldMetadata for new world

        Raises:
            KeyError: If source world doesn't exist
            ValueError: If target world already exists
        """
        if target_world_id in self.worlds:
            raise ValueError(f"World '{target_world_id}' already exists")

        source_world = self.get_world(source_world_id)

        # Create new world with same isolation mode
        new_world = self.create_world(
            world_id=target_world_id,
            isolation_mode=source_world.isolation_mode,
            description=description or f"Clone of {source_world_id}",
            metadata={"cloned_from": source_world_id}
        )

        # Copy database file if separate DB mode
        if source_world.isolation_mode == IsolationMode.SEPARATE_DB:
            shutil.copy2(source_world.db_path, new_world.db_path)
        elif source_world.isolation_mode == IsolationMode.SHARED_DB_PARTITIONED:
            # For shared DB, we'd need to copy rows with world_id update
            # This is more complex - not implemented in initial version
            raise NotImplementedError(
                "Cloning not yet supported for SHARED_DB_PARTITIONED mode"
            )

        return new_world

    def export_world(
        self,
        world_id: str,
        export_path: str,
        format: str = "sqlite"
    ):
        """
        Export a world to a file.

        Args:
            world_id: World to export
            export_path: Destination path
            format: Export format (sqlite, json, etc.)

        Raises:
            KeyError: If world doesn't exist
            NotImplementedError: If format not supported
        """
        world = self.get_world(world_id)

        if format == "sqlite":
            # Copy database file
            shutil.copy2(world.db_path, export_path)
        elif format == "json":
            # Export as JSON (not implemented yet)
            raise NotImplementedError("JSON export not yet implemented")
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def import_world(
        self,
        import_path: str,
        world_id: str,
        format: str = "sqlite",
        description: Optional[str] = None
    ) -> WorldMetadata:
        """
        Import a world from a file.

        Args:
            import_path: Source file path
            world_id: Identifier for imported world
            format: Import format (sqlite, json, etc.)
            description: Description for imported world

        Returns:
            WorldMetadata for imported world

        Raises:
            ValueError: If world already exists
            NotImplementedError: If format not supported
        """
        if world_id in self.worlds:
            raise ValueError(f"World '{world_id}' already exists")

        if format == "sqlite":
            # Create world and copy database file
            world = self.create_world(
                world_id=world_id,
                isolation_mode=IsolationMode.SEPARATE_DB,
                description=description or f"Imported from {import_path}",
                metadata={"imported_from": import_path}
            )
            shutil.copy2(import_path, world.db_path)
            return world
        elif format == "json":
            raise NotImplementedError("JSON import not yet implemented")
        else:
            raise ValueError(f"Unsupported import format: {format}")
