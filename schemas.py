# schemas.py - SQLModel schemas serving as ORM, validation, and API spec
from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import numpy as np
from pydantic import field_validator

class ResolutionLevel(str, Enum):
    TENSOR_ONLY = "tensor_only"
    SCENE = "scene"
    GRAPH = "graph"
    DIALOG = "dialog"
    TRAINED = "trained"

class TTMTensor(SQLModel):
    """Timepoint Tensor Model - context, biology, behavior"""
    context_vector: bytes  # Serialized numpy array (knowledge, information)
    biology_vector: bytes  # Serialized numpy array (age, health, physical constraints)
    behavior_vector: bytes  # Serialized numpy array (personality, patterns, momentum)
    
    @classmethod
    def from_arrays(cls, context: np.ndarray, biology: np.ndarray, behavior: np.ndarray):
        import msgspec
        return cls(
            context_vector=msgspec.msgpack.encode(context.tolist()),
            biology_vector=msgspec.msgpack.encode(biology.tolist()),
            behavior_vector=msgspec.msgpack.encode(behavior.tolist())
        )
    
    def to_arrays(self):
        import msgspec
        return (
            np.array(msgspec.msgpack.decode(self.context_vector)),
            np.array(msgspec.msgpack.decode(self.biology_vector)),
            np.array(msgspec.msgpack.decode(self.behavior_vector))
        )

class Entity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_id: str = Field(unique=True, index=True)
    entity_type: str  # person, location, event
    temporal_span_start: Optional[datetime] = None
    temporal_span_end: Optional[datetime] = None
    tensor: Optional[str] = Field(default=None, sa_column=Column(JSON))  # Serialized TTM
    training_count: int = Field(default=0)
    query_count: int = Field(default=0)
    eigenvector_centrality: float = Field(default=0.0)
    resolution_level: ResolutionLevel = Field(default=ResolutionLevel.TENSOR_ONLY)
    entity_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # Renamed from metadata

class Timeline(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timepoint_id: str = Field(unique=True, index=True)
    timestamp: datetime
    resolution: str  # year, month, day, hour
    entities_present: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    events: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    training_status: str = Field(default="untrained")
    graph_data: Optional[str] = Field(default=None, sa_column=Column(JSON))

class SystemPrompt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    template: str
    version: int = Field(default=1)
    variables: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class ValidationRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    rule_type: str  # energy, temporal, biological, information
    severity: str  # ERROR, WARNING, INFO
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class ExposureEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_id: str = Field(foreign_key="entity.entity_id", index=True)
    event_type: str  # witnessed, learned, told, experienced
    information: str  # what was learned
    source: Optional[str] = None  # who/what provided the information
    timestamp: datetime
    confidence: float = Field(default=1.0)
    timepoint_id: Optional[str] = Field(default=None, index=True)  # link to timepoint

class Timepoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timepoint_id: str = Field(unique=True, index=True)
    timestamp: datetime
    event_description: str
    entities_present: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    causal_parent: Optional[str] = Field(default=None, index=True)  # previous timepoint_id
    resolution_level: ResolutionLevel = Field(default=ResolutionLevel.SCENE)