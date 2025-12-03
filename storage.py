# ============================================================================
# storage.py - Database and graph persistence
# ============================================================================
from sqlmodel import Session, create_engine, select, SQLModel
from typing import Optional, Generator
from contextlib import contextmanager
import networkx as nx
import json
from functools import lru_cache

from schemas import Entity, Timeline, SystemPrompt, ExposureEvent, Timepoint, Dialog, RelationshipTrajectory, QueryHistory, ConvergenceSet


class TransactionContext:
    """
    Context for atomic database operations within a transaction.

    Provides save methods that use a shared session. The transaction
    is committed when the context exits normally, or rolled back on exception.

    Example:
        with store.transaction() as tx:
            tx.save_entity(entity)
            tx.save_timepoint(timepoint)
            tx.save_exposure_event(event)
            # All succeed or all rollback
    """

    def __init__(self, session: Session):
        self._session = session

    def save_entity(self, entity: Entity) -> Entity:
        """Save an entity within the transaction"""
        from sqlalchemy.orm.attributes import flag_modified

        existing = self._session.exec(
            select(Entity).where(Entity.entity_id == entity.entity_id)
        ).first()

        if existing:
            existing.entity_type = entity.entity_type
            existing.timepoint = entity.timepoint
            existing.temporal_span_start = entity.temporal_span_start
            existing.temporal_span_end = entity.temporal_span_end
            existing.tensor = entity.tensor
            existing.training_count = entity.training_count
            existing.query_count = entity.query_count
            existing.eigenvector_centrality = entity.eigenvector_centrality
            existing.resolution_level = entity.resolution_level
            existing.entity_metadata = entity.entity_metadata
            flag_modified(existing, "entity_metadata")
            self._session.add(existing)
            return existing
        else:
            self._session.add(entity)
            flag_modified(entity, "entity_metadata")
            return entity

    def save_timepoint(self, timepoint: Timepoint) -> Timepoint:
        """Save a timepoint within the transaction"""
        self._session.add(timepoint)
        return timepoint

    def save_exposure_event(self, event: ExposureEvent) -> ExposureEvent:
        """Save an exposure event within the transaction"""
        self._session.add(event)
        return event

    def save_exposure_events(self, events: list[ExposureEvent]) -> None:
        """Batch save exposure events within the transaction"""
        for event in events:
            self._session.add(event)

    def save_dialog(self, dialog: Dialog) -> Dialog:
        """Save a dialog within the transaction"""
        self._session.add(dialog)
        return dialog

    def save_relationship_trajectory(self, trajectory: RelationshipTrajectory) -> RelationshipTrajectory:
        """Save a relationship trajectory within the transaction"""
        self._session.add(trajectory)
        return trajectory

    def save_timeline(self, timeline: Timeline) -> Timeline:
        """Save a timeline within the transaction"""
        self._session.add(timeline)
        return timeline

    def save_query_history(self, query_history: QueryHistory) -> QueryHistory:
        """Save query history within the transaction"""
        self._session.add(query_history)
        return query_history

    def save_prospective_state(self, prospective_state) -> None:
        """Save a prospective state within the transaction"""
        self._session.add(prospective_state)
        return prospective_state

class GraphStore:
    """Unified storage for entities, timelines, and graphs"""

    def __init__(self, db_url: str = "sqlite:///timepoint.db"):
        self.engine = create_engine(db_url)
        SQLModel.metadata.create_all(self.engine)
        # Enable WAL mode for better concurrent write performance
        # (allows multiple readers + one writer simultaneously)
        if "sqlite" in db_url:
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()

    @contextmanager
    def transaction(self) -> Generator[TransactionContext, None, None]:
        """
        Create a transaction context for atomic database operations.

        All operations within the context use the same session and are
        committed together. If any exception occurs, all changes are
        rolled back.

        Example:
            with store.transaction() as tx:
                tx.save_entity(entity)
                tx.save_timepoint(timepoint)
                tx.save_exposure_event(event)
                # All succeed or all rollback

        Yields:
            TransactionContext: Context with save methods for atomic operations
        """
        with Session(self.engine) as session:
            tx = TransactionContext(session)
            try:
                yield tx
                session.commit()
            except Exception:
                session.rollback()
                raise

    def save_entity(self, entity: Entity) -> Entity:
        from sqlalchemy.orm.attributes import flag_modified
        with Session(self.engine) as session:
            # Check if entity already exists by entity_id (unique constraint)
            existing = session.exec(
                select(Entity).where(Entity.entity_id == entity.entity_id)
            ).first()

            if existing:
                # Update existing entity with new values
                existing.entity_type = entity.entity_type
                existing.timepoint = entity.timepoint
                existing.temporal_span_start = entity.temporal_span_start
                existing.temporal_span_end = entity.temporal_span_end
                existing.tensor = entity.tensor
                existing.training_count = entity.training_count
                existing.query_count = entity.query_count
                existing.eigenvector_centrality = entity.eigenvector_centrality
                existing.resolution_level = entity.resolution_level
                existing.entity_metadata = entity.entity_metadata
                # Mark entity_metadata as modified since it's a JSON column
                flag_modified(existing, "entity_metadata")
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # Insert new entity
                session.add(entity)
                flag_modified(entity, "entity_metadata")
                session.commit()
                session.refresh(entity)
                return entity

    def save_exposure_event(self, event: ExposureEvent) -> ExposureEvent:
        """Save a single exposure event"""
        with Session(self.engine) as session:
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    def save_exposure_events(self, exposure_events: list[ExposureEvent]) -> None:
        """Batch save exposure events"""
        with Session(self.engine) as session:
            for event in exposure_events:
                session.add(event)
            session.commit()

    def get_exposure_events(self, entity_id: str, limit: Optional[int] = None) -> list[ExposureEvent]:
        """
        Get exposure events for an entity.

        Args:
            entity_id: Entity identifier
            limit: Optional maximum number of events to return (most recent first if limited)

        Returns:
            List of exposure events
        """
        with Session(self.engine) as session:
            statement = select(ExposureEvent).where(ExposureEvent.entity_id == entity_id)

            # If limit specified, order by timestamp descending and apply limit
            if limit is not None:
                statement = statement.order_by(ExposureEvent.timestamp.desc()).limit(limit)

            return list(session.exec(statement).all())

    def save_timepoint(self, timepoint: Timepoint) -> Timepoint:
        """Save a timepoint"""
        with Session(self.engine) as session:
            session.add(timepoint)
            session.commit()
            session.refresh(timepoint)
            return timepoint

    @lru_cache(maxsize=500)
    def get_timepoint(self, timepoint_id: str) -> Optional[Timepoint]:
        """Get a timepoint by ID with LRU caching"""
        with Session(self.engine) as session:
            statement = select(Timepoint).where(Timepoint.timepoint_id == timepoint_id)
            return session.exec(statement).first()

    def get_all_timepoints(self) -> list[Timepoint]:
        """Get all timepoints ordered by timestamp"""
        with Session(self.engine) as session:
            statement = select(Timepoint).order_by(Timepoint.timestamp)
            return list(session.exec(statement).all())

    def get_timepoints_by_run(self, run_id: str) -> list[Timepoint]:
        """Get all timepoints for a specific run, ordered by timestamp"""
        with Session(self.engine) as session:
            statement = select(Timepoint).where(
                Timepoint.run_id == run_id
            ).order_by(Timepoint.timestamp)
            return list(session.exec(statement).all())

    def get_exposure_events_by_run(self, run_id: str) -> list[ExposureEvent]:
        """Get all exposure events for a specific run, ordered by timestamp"""
        with Session(self.engine) as session:
            statement = select(ExposureEvent).where(
                ExposureEvent.run_id == run_id
            ).order_by(ExposureEvent.timestamp)
            return list(session.exec(statement).all())

    def get_entity_knowledge_at_timepoint(self, entity_id: str, timepoint_id: str) -> list[str]:
        """Get what an entity knew at a specific timepoint"""
        with Session(self.engine) as session:
            # Get the timepoint timestamp
            timepoint = session.exec(
                select(Timepoint).where(Timepoint.timepoint_id == timepoint_id)
            ).first()

            if not timepoint:
                return []

            # Get all exposure events for this entity up to and including this timepoint
            statement = select(ExposureEvent).where(
                ExposureEvent.entity_id == entity_id,
                ExposureEvent.timestamp <= timepoint.timestamp
            ).order_by(ExposureEvent.timestamp)

            exposure_events = list(session.exec(statement).all())
            return [event.information for event in exposure_events]

    def get_all_entities(self) -> list[Entity]:
        """Get all entities"""
        with Session(self.engine) as session:
            statement = select(Entity)
            return list(session.exec(statement).all())

    def _clear_database(self) -> None:
        """Clear all data from database (for testing)"""
        from sqlalchemy import text
        from schemas import Timeline
        with Session(self.engine) as session:
            # Delete in order to respect foreign keys
            session.exec(text("DELETE FROM queryhistory"))
            session.exec(text("DELETE FROM exposureevent"))
            session.exec(text("DELETE FROM entity"))
            session.exec(text("DELETE FROM timepoint"))
            session.exec(text("DELETE FROM timeline"))
            session.exec(text("DELETE FROM systemprompt"))
            session.exec(text("DELETE FROM validationrule"))
            session.commit()

    def get_entity(self, entity_id: str, timepoint: Optional[str] = None) -> Optional[Entity]:
        """
        Get entity by ID with optional timepoint filter.

        Args:
            entity_id: Entity identifier
            timepoint: Optional timepoint filter (for compatibility)

        Returns:
            Entity if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(Entity).where(Entity.entity_id == entity_id)
            if timepoint:
                statement = statement.where(Entity.timepoint == timepoint)
            return session.exec(statement).first()
    
    def save_graph(self, graph: nx.Graph, timepoint_id: str):
        """Serialize NetworkX graph to database"""
        graph_dict = nx.to_dict_of_dicts(graph)
        with Session(self.engine) as session:
            timeline = session.exec(
                select(Timeline).where(Timeline.timepoint_id == timepoint_id)
            ).first()
            if timeline:
                timeline.graph_data = json.dumps(graph_dict)
                session.add(timeline)
                session.commit()
    
    def load_graph(self, timepoint_id: str) -> Optional[nx.Graph]:
        """Deserialize NetworkX graph from database"""
        with Session(self.engine) as session:
            timeline = session.exec(
                select(Timeline).where(Timeline.timepoint_id == timepoint_id)
            ).first()
            if timeline and timeline.graph_data:
                graph_dict = json.loads(timeline.graph_data)
                return nx.from_dict_of_dicts(graph_dict)
        return None
    
    def get_prompt(self, name: str) -> Optional[SystemPrompt]:
        with Session(self.engine) as session:
            return session.exec(
                select(SystemPrompt).where(SystemPrompt.name == name)
            ).first()

    # ============================================================================
    # Dialog Storage (Mechanism 11)
    # ============================================================================

    def save_dialog(self, dialog: Dialog) -> Dialog:
        """Save a dialog conversation"""
        with Session(self.engine) as session:
            session.add(dialog)
            session.commit()
            session.refresh(dialog)
            return dialog

    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """Get a dialog by ID"""
        with Session(self.engine) as session:
            statement = select(Dialog).where(Dialog.dialog_id == dialog_id)
            return session.exec(statement).first()

    def get_dialogs_at_timepoint(self, timepoint_id: str) -> list[Dialog]:
        """Get all dialogs that occurred at a specific timepoint"""
        with Session(self.engine) as session:
            statement = select(Dialog).where(Dialog.timepoint_id == timepoint_id)
            return list(session.exec(statement).all())

    def get_dialogs_for_entities(self, entity_ids: list[str]) -> list[Dialog]:
        """Get all dialogs involving any of the specified entities"""
        with Session(self.engine) as session:
            # Find dialogs where participants JSON contains any of the entity_ids
            all_dialogs = session.exec(select(Dialog)).all()
            matching_dialogs = []

            for dialog in all_dialogs:
                participants = json.loads(dialog.participants)
                if any(entity_id in participants for entity_id in entity_ids):
                    matching_dialogs.append(dialog)

            return matching_dialogs

    # ============================================================================
    # Relationship Trajectory Storage (Mechanism 13)
    # ============================================================================

    def save_relationship_trajectory(self, trajectory: RelationshipTrajectory) -> RelationshipTrajectory:
        """Save a relationship trajectory"""
        with Session(self.engine) as session:
            session.add(trajectory)
            session.commit()
            session.refresh(trajectory)
            return trajectory

    def get_relationship_trajectory(self, trajectory_id: str) -> Optional[RelationshipTrajectory]:
        """Get a relationship trajectory by ID"""
        with Session(self.engine) as session:
            statement = select(RelationshipTrajectory).where(RelationshipTrajectory.trajectory_id == trajectory_id)
            return session.exec(statement).first()

    def get_relationship_trajectory_between(self, entity_a: str, entity_b: str) -> Optional[RelationshipTrajectory]:
        """Get the most recent relationship trajectory between two entities"""
        with Session(self.engine) as session:
            statement = select(RelationshipTrajectory).where(
                RelationshipTrajectory.entity_a == entity_a,
                RelationshipTrajectory.entity_b == entity_b
            ).order_by(RelationshipTrajectory.id.desc())  # Most recent first
            return session.exec(statement).first()

    def get_entity_relationships(self, entity_id: str) -> list[RelationshipTrajectory]:
        """Get all relationship trajectories involving an entity"""
        with Session(self.engine) as session:
            statement = select(RelationshipTrajectory).where(
                (RelationshipTrajectory.entity_a == entity_id) |
                (RelationshipTrajectory.entity_b == entity_id)
            )
            return list(session.exec(statement).all())

    # ============================================================================
    # Additional Helper Methods
    # ============================================================================

    def get_entity_at_timepoint(self, entity_id: str, timepoint_id: str) -> Optional[Entity]:
        """Get entity state at a specific timepoint"""
        # For now, return current entity state (could be enhanced to track historical states)
        return self.get_entity(entity_id)

    def get_timepoints_in_range(self, start_time=None, end_time=None) -> list[Timepoint]:
        """Get timepoints within a time range"""
        with Session(self.engine) as session:
            statement = select(Timepoint)
            if start_time:
                statement = statement.where(Timepoint.timestamp >= start_time)
            if end_time:
                statement = statement.where(Timepoint.timestamp <= end_time)
            statement = statement.order_by(Timepoint.timestamp)
            return list(session.exec(statement).all())

    # ============================================================================
    # Timeline Storage (Mechanism 12: Counterfactual Branching)
    # ============================================================================

    def save_timeline(self, timeline: Timeline) -> Timeline:
        """Save a timeline to the database"""
        with Session(self.engine) as session:
            session.add(timeline)
            session.commit()
            session.refresh(timeline)
        return timeline

    def get_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """Get a timeline by ID"""
        with Session(self.engine) as session:
            return session.exec(
                select(Timeline).where(Timeline.timeline_id == timeline_id)
            ).first()

    def get_timelines(self) -> list[Timeline]:
        """Get all timelines"""
        with Session(self.engine) as session:
            return list(session.exec(select(Timeline)).all())

    def get_child_timelines(self, parent_timeline_id: str) -> list[Timeline]:
        """Get all child timelines of a parent timeline"""
        with Session(self.engine) as session:
            return list(session.exec(
                select(Timeline).where(Timeline.parent_timeline_id == parent_timeline_id)
            ).all())

    def get_successor_timepoints(self, timepoint_id: str) -> list[Timepoint]:
        """Get all timepoints that have the given timepoint as their causal parent"""
        with Session(self.engine) as session:
            statement = select(Timepoint).where(Timepoint.causal_parent == timepoint_id)
            return list(session.exec(statement).all())

    def get_predecessor_timepoints(self, timepoint_id: str) -> list[Timepoint]:
        """Get the causal parent(s) of a given timepoint"""
        with Session(self.engine) as session:
            # Get the timepoint to find its causal parent
            timepoint = session.exec(
                select(Timepoint).where(Timepoint.timepoint_id == timepoint_id)
            ).first()

            if not timepoint or not timepoint.causal_parent:
                return []

            # Get the parent timepoint
            parent = session.exec(
                select(Timepoint).where(Timepoint.timepoint_id == timepoint.causal_parent)
            ).first()

            return [parent] if parent else []

    # ============================================================================
    # Query History Storage (Mechanism 5: Query Resolution)
    # ============================================================================

    def save_query_history(self, query_history: QueryHistory) -> QueryHistory:
        """Save a query history entry for resolution tracking"""
        with Session(self.engine) as session:
            session.add(query_history)
            session.commit()
            session.refresh(query_history)
            return query_history

    def get_query_history_for_entity(self, entity_id: str, limit: int = 100) -> list[QueryHistory]:
        """Get query history for an entity (most recent first)"""
        with Session(self.engine) as session:
            statement = select(QueryHistory).where(
                QueryHistory.entity_id == entity_id
            ).order_by(QueryHistory.timestamp.desc()).limit(limit)
            return list(session.exec(statement).all())

    def get_entity_query_count(self, entity_id: str) -> int:
        """Get total number of queries for an entity"""
        with Session(self.engine) as session:
            statement = select(QueryHistory).where(QueryHistory.entity_id == entity_id)
            return len(list(session.exec(statement).all()))

    def get_entity_elevation_count(self, entity_id: str) -> int:
        """Get number of times resolution was elevated for an entity"""
        with Session(self.engine) as session:
            statement = select(QueryHistory).where(
                QueryHistory.entity_id == entity_id,
                QueryHistory.resolution_elevated == True
            )
            return len(list(session.exec(statement).all()))

    # ============================================================================
    # Prospective State Storage (Mechanism 15: Entity Prospection)
    # ============================================================================

    def save_prospective_state(self, prospective_state) -> None:
        """Save a prospective state for an entity"""
        from schemas import ProspectiveState
        with Session(self.engine) as session:
            session.add(prospective_state)
            session.commit()
            session.refresh(prospective_state)
            return prospective_state

    def get_prospective_state(self, prospective_id: str):
        """Get a prospective state by ID"""
        from schemas import ProspectiveState
        with Session(self.engine) as session:
            statement = select(ProspectiveState).where(ProspectiveState.prospective_id == prospective_id)
            return session.exec(statement).first()

    def get_prospective_states_for_entity(self, entity_id: str):
        """Get all prospective states for an entity"""
        from schemas import ProspectiveState
        with Session(self.engine) as session:
            statement = select(ProspectiveState).where(
                ProspectiveState.entity_id == entity_id
            ).order_by(ProspectiveState.created_at.desc())
            return list(session.exec(statement).all())

    # ============================================================================
    # Convergence Evaluation Storage (Cross-run causal graph comparison)
    # ============================================================================

    def save_convergence_set(self, convergence_set: ConvergenceSet) -> ConvergenceSet:
        """
        Save a convergence analysis result.

        Args:
            convergence_set: ConvergenceSet object with analysis results

        Returns:
            Saved ConvergenceSet with ID populated
        """
        with Session(self.engine) as session:
            session.add(convergence_set)
            session.commit()
            session.refresh(convergence_set)
            return convergence_set

    def get_convergence_set(self, set_id: str) -> Optional[ConvergenceSet]:
        """Get a convergence set by ID"""
        with Session(self.engine) as session:
            statement = select(ConvergenceSet).where(ConvergenceSet.set_id == set_id)
            return session.exec(statement).first()

    def get_convergence_sets(
        self,
        template_id: Optional[str] = None,
        min_score: Optional[float] = None,
        limit: int = 100
    ) -> list[ConvergenceSet]:
        """
        Get convergence sets with optional filtering.

        Args:
            template_id: Filter by template ID
            min_score: Filter by minimum convergence score
            limit: Maximum results to return

        Returns:
            List of matching ConvergenceSet objects
        """
        with Session(self.engine) as session:
            statement = select(ConvergenceSet)

            if template_id:
                statement = statement.where(ConvergenceSet.template_id == template_id)

            if min_score is not None:
                statement = statement.where(ConvergenceSet.convergence_score >= min_score)

            statement = statement.order_by(ConvergenceSet.created_at.desc()).limit(limit)
            return list(session.exec(statement).all())

    def get_convergence_stats(self) -> dict:
        """
        Get aggregate convergence statistics across all sets.

        Returns:
            Dictionary with count, average score, grade distribution
        """
        with Session(self.engine) as session:
            all_sets = session.exec(select(ConvergenceSet)).all()

            if not all_sets:
                return {
                    "total_sets": 0,
                    "average_score": 0.0,
                    "grade_distribution": {},
                    "template_coverage": {}
                }

            scores = [s.convergence_score for s in all_sets]
            grades = [s.robustness_grade for s in all_sets]
            templates = [s.template_id for s in all_sets if s.template_id]

            grade_distribution = {}
            for grade in grades:
                grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

            template_coverage = {}
            for template in templates:
                template_coverage[template] = template_coverage.get(template, 0) + 1

            return {
                "total_sets": len(all_sets),
                "average_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
                "grade_distribution": grade_distribution,
                "template_coverage": template_coverage
            }
