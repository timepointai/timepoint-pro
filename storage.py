# ============================================================================
# storage.py - Database and graph persistence
# ============================================================================
from sqlmodel import Session, create_engine, select, SQLModel
from typing import Optional
import networkx as nx
import json

from schemas import Entity, Timeline, SystemPrompt, ExposureEvent, Timepoint

class GraphStore:
    """Unified storage for entities, timelines, and graphs"""
    
    def __init__(self, db_url: str = "sqlite:///timepoint.db"):
        self.engine = create_engine(db_url)
        SQLModel.metadata.create_all(self.engine)
    
    def save_entity(self, entity: Entity) -> Entity:
        from sqlalchemy.orm.attributes import flag_modified
        with Session(self.engine) as session:
            session.add(entity)
            # Mark entity_metadata as modified since it's a JSON column
            flag_modified(entity, "entity_metadata")
            session.commit()
            session.refresh(entity)
            return entity

    def save_exposure_events(self, exposure_events: list[ExposureEvent]) -> None:
        """Batch save exposure events"""
        with Session(self.engine) as session:
            for event in exposure_events:
                session.add(event)
            session.commit()

    def get_exposure_events(self, entity_id: str) -> list[ExposureEvent]:
        """Get all exposure events for an entity"""
        with Session(self.engine) as session:
            statement = select(ExposureEvent).where(ExposureEvent.entity_id == entity_id)
            return list(session.exec(statement).all())

    def save_timepoint(self, timepoint: Timepoint) -> Timepoint:
        """Save a timepoint"""
        with Session(self.engine) as session:
            session.add(timepoint)
            session.commit()
            session.refresh(timepoint)
            return timepoint

    def get_timepoint(self, timepoint_id: str) -> Optional[Timepoint]:
        """Get a timepoint by ID"""
        with Session(self.engine) as session:
            statement = select(Timepoint).where(Timepoint.timepoint_id == timepoint_id)
            return session.exec(statement).first()

    def get_all_timepoints(self) -> list[Timepoint]:
        """Get all timepoints ordered by timestamp"""
        with Session(self.engine) as session:
            statement = select(Timepoint).order_by(Timepoint.timestamp)
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
            session.exec(text("DELETE FROM exposureevent"))
            session.exec(text("DELETE FROM entity"))
            session.exec(text("DELETE FROM timepoint"))
            session.exec(text("DELETE FROM timeline"))
            session.exec(text("DELETE FROM systemprompt"))
            session.exec(text("DELETE FROM validationrule"))
            session.commit()

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        with Session(self.engine) as session:
            statement = select(Entity).where(Entity.entity_id == entity_id)
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
