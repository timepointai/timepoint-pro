# evaluation/convergence.py - Core causal graph convergence logic
"""
Causal graph extraction and convergence measurement for Timepoint simulations.

The unique value of Timepoint: it predicts causal mechanisms, not just outcomes.
This module measures whether multiple runs of the same scenario produce
consistent causal chains - convergence indicates robust mechanisms.

Key concepts:
- CausalGraph: Structured representation of timepoint chains + knowledge flow
- Convergence: Agreement across independent runs (different models/seeds/modes)
- Divergence points: Specific causal links where runs disagree
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Dict, Optional, Any
from datetime import datetime
from itertools import combinations
import json
import logging

logger = logging.getLogger(__name__)


def normalize_timepoint_id(timepoint_id: str, run_id: str) -> str:
    """
    Normalize a timepoint ID by stripping the run_id prefix if present.

    This enables convergence comparison across runs - e.g.,
    "run_123_tp_001_opening" -> "tp_001_opening"

    Args:
        timepoint_id: The timepoint ID (possibly with run_id prefix)
        run_id: The run ID to strip

    Returns:
        Normalized timepoint ID without run_id prefix
    """
    prefix = f"{run_id}_"
    if timepoint_id.startswith(prefix):
        return timepoint_id[len(prefix):]
    return timepoint_id


@dataclass
class CausalEdge:
    """A single causal link in the graph."""
    source: str  # Entity or timepoint ID
    target: str  # Entity or timepoint ID
    edge_type: str  # "temporal" (timepoint chain) or "knowledge" (exposure event)
    label: Optional[str] = None  # Additional context (e.g., information transferred)

    def __hash__(self):
        return hash((self.source, self.target, self.edge_type))

    def __eq__(self, other):
        if not isinstance(other, CausalEdge):
            return False
        return (self.source == other.source and self.target == other.target and
                self.edge_type == other.edge_type)

    def to_tuple(self) -> Tuple[str, str, str]:
        """Convert to hashable tuple for set operations."""
        return (self.source, self.target, self.edge_type)


@dataclass
class CausalGraph:
    """
    Structured representation of causal relationships in a simulation run.

    Contains two types of edges:
    1. Temporal edges: timepoint → timepoint (causal chain)
    2. Knowledge edges: entity → entity (information flow via exposure events)
    """
    run_id: str
    template_id: Optional[str] = None
    temporal_edges: Set[Tuple[str, str]] = field(default_factory=set)
    knowledge_edges: Set[Tuple[str, str]] = field(default_factory=set)
    entities: Set[str] = field(default_factory=set)
    timepoints: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_edges(self) -> Set[Tuple[str, str, str]]:
        """All edges as (source, target, type) tuples."""
        temporal = {(s, t, "temporal") for s, t in self.temporal_edges}
        knowledge = {(s, t, "knowledge") for s, t in self.knowledge_edges}
        return temporal | knowledge

    @property
    def edge_count(self) -> int:
        """Total number of causal edges."""
        return len(self.temporal_edges) + len(self.knowledge_edges)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage/export."""
        return {
            "run_id": self.run_id,
            "template_id": self.template_id,
            "temporal_edges": list(self.temporal_edges),
            "knowledge_edges": list(self.knowledge_edges),
            "entities": list(self.entities),
            "timepoints": list(self.timepoints),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalGraph":
        """Deserialize from dictionary."""
        return cls(
            run_id=data["run_id"],
            template_id=data.get("template_id"),
            temporal_edges=set(tuple(e) for e in data.get("temporal_edges", [])),
            knowledge_edges=set(tuple(e) for e in data.get("knowledge_edges", [])),
            entities=set(data.get("entities", [])),
            timepoints=set(data.get("timepoints", [])),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DivergencePoint:
    """A specific causal link where runs disagree."""
    edge: Tuple[str, str, str]  # (source, target, type)
    present_in_runs: List[str]  # run_ids that have this edge
    absent_in_runs: List[str]  # run_ids that don't have this edge
    agreement_ratio: float  # fraction of runs with this edge


@dataclass
class ConvergenceResult:
    """
    Results of convergence analysis across multiple runs.

    High convergence (>0.8) indicates robust causal mechanisms.
    Low convergence (<0.5) indicates high sensitivity to model/seed choice.
    """
    run_ids: List[str]
    template_id: Optional[str]

    # Core metrics
    mean_similarity: float  # Average pairwise graph similarity
    min_similarity: float  # Worst-case similarity
    max_similarity: float  # Best-case similarity

    # Divergence analysis
    divergence_points: List[DivergencePoint]
    consensus_edges: Set[Tuple[str, str, str]]  # Edges present in all runs
    contested_edges: Set[Tuple[str, str, str]]  # Edges present in some runs

    # Metadata
    computed_at: datetime = field(default_factory=datetime.utcnow)
    run_count: int = 0

    def __post_init__(self):
        self.run_count = len(self.run_ids)

    @property
    def convergence_score(self) -> float:
        """Alias for mean_similarity - the headline metric."""
        return self.mean_similarity

    @property
    def robustness_grade(self) -> str:
        """Human-readable grade based on convergence score."""
        if self.mean_similarity >= 0.9:
            return "A"
        elif self.mean_similarity >= 0.8:
            return "B"
        elif self.mean_similarity >= 0.7:
            return "C"
        elif self.mean_similarity >= 0.5:
            return "D"
        else:
            return "F"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage/export."""
        return {
            "run_ids": self.run_ids,
            "template_id": self.template_id,
            "mean_similarity": self.mean_similarity,
            "min_similarity": self.min_similarity,
            "max_similarity": self.max_similarity,
            "convergence_score": self.convergence_score,
            "robustness_grade": self.robustness_grade,
            "divergence_points": [
                {
                    "edge": dp.edge,
                    "present_in_runs": dp.present_in_runs,
                    "absent_in_runs": dp.absent_in_runs,
                    "agreement_ratio": dp.agreement_ratio,
                }
                for dp in self.divergence_points
            ],
            "consensus_edges": list(self.consensus_edges),
            "contested_edges": list(self.contested_edges),
            "computed_at": self.computed_at.isoformat(),
            "run_count": self.run_count,
        }


def extract_causal_graph(
    run_id: str,
    db_path: str = "metadata/runs.db",
    template_id: Optional[str] = None,
) -> CausalGraph:
    """
    Extract causal graph from a completed simulation run.

    Pulls from existing database structures:
    - Timepoint.causal_parent for temporal chains (filtered by run_id)
    - ExposureEvent.source/entity_id for knowledge flow (filtered by run_id)

    Args:
        run_id: Simulation run identifier (used to filter timepoints/events)
        db_path: Path to database (default: metadata/runs.db)
        template_id: Optional template ID for metadata

    Returns:
        CausalGraph with extracted causal structure for the specific run
    """
    from storage import GraphStore
    from sqlmodel import Session, select
    from schemas import Timepoint, ExposureEvent, Entity

    # Initialize store
    store = GraphStore(f"sqlite:///{db_path}")

    temporal_edges: Set[Tuple[str, str]] = set()
    knowledge_edges: Set[Tuple[str, str]] = set()
    entities: Set[str] = set()
    timepoints: Set[str] = set()

    with Session(store.engine) as session:
        # Extract temporal chain from timepoints - FILTER BY RUN_ID
        run_timepoints = session.exec(
            select(Timepoint).where(Timepoint.run_id == run_id)
        ).all()

        logger.debug(f"Extracting causal graph for run {run_id}: found {len(run_timepoints)} timepoints")

        for tp in run_timepoints:
            # Normalize timepoint IDs by stripping run_id prefix for convergence comparison
            normalized_tp_id = normalize_timepoint_id(tp.timepoint_id, run_id)
            timepoints.add(normalized_tp_id)
            if tp.causal_parent:
                normalized_parent = normalize_timepoint_id(tp.causal_parent, run_id)
                temporal_edges.add((normalized_parent, normalized_tp_id))
            # Track entities present
            if tp.entities_present:
                for eid in tp.entities_present:
                    entities.add(eid)

        # Extract knowledge flow from exposure events - FILTER BY RUN_ID
        run_events = session.exec(
            select(ExposureEvent).where(ExposureEvent.run_id == run_id)
        ).all()

        logger.debug(f"Found {len(run_events)} exposure events for run {run_id}")

        for event in run_events:
            entities.add(event.entity_id)
            if event.source and event.source != event.entity_id:
                # Knowledge flowed from source to entity
                knowledge_edges.add((event.source, event.entity_id))
                entities.add(event.source)

    return CausalGraph(
        run_id=run_id,
        template_id=template_id,
        temporal_edges=temporal_edges,
        knowledge_edges=knowledge_edges,
        entities=entities,
        timepoints=timepoints,
        metadata={
            "extracted_at": datetime.utcnow().isoformat(),
            "db_path": db_path,
            "timepoint_count": len(timepoints),
            "temporal_edge_count": len(temporal_edges),
            "knowledge_edge_count": len(knowledge_edges),
        }
    )


def graph_similarity(g1: CausalGraph, g2: CausalGraph) -> float:
    """
    Compute Jaccard similarity between two causal graphs.

    Measures overlap in causal edges (both temporal and knowledge).
    Returns 1.0 for identical graphs, 0.0 for completely disjoint.

    Args:
        g1: First causal graph
        g2: Second causal graph

    Returns:
        Similarity score in [0.0, 1.0]
    """
    edges1 = g1.all_edges
    edges2 = g2.all_edges

    if not edges1 and not edges2:
        return 1.0  # Both empty = identical

    if not edges1 or not edges2:
        return 0.0  # One empty, one not = no overlap

    intersection = edges1 & edges2
    union = edges1 | edges2

    return len(intersection) / len(union) if union else 0.0


def find_divergence_points(graphs: List[CausalGraph]) -> List[DivergencePoint]:
    """
    Identify specific causal links where graphs diverge.

    For each edge that appears in some but not all graphs,
    returns information about which runs agree/disagree.

    Args:
        graphs: List of CausalGraph objects to compare

    Returns:
        List of DivergencePoint objects sorted by agreement ratio
    """
    if len(graphs) < 2:
        return []

    # Collect all edges across all graphs
    all_edges: Set[Tuple[str, str, str]] = set()
    edge_to_runs: Dict[Tuple[str, str, str], List[str]] = {}

    for g in graphs:
        for edge in g.all_edges:
            all_edges.add(edge)
            if edge not in edge_to_runs:
                edge_to_runs[edge] = []
            edge_to_runs[edge].append(g.run_id)

    # Find edges with partial agreement
    divergence_points = []
    run_ids = [g.run_id for g in graphs]
    n_runs = len(graphs)

    for edge, present_runs in edge_to_runs.items():
        if 0 < len(present_runs) < n_runs:
            # This edge is contested (not in all runs, but in some)
            absent_runs = [rid for rid in run_ids if rid not in present_runs]
            agreement_ratio = len(present_runs) / n_runs

            divergence_points.append(DivergencePoint(
                edge=edge,
                present_in_runs=present_runs,
                absent_in_runs=absent_runs,
                agreement_ratio=agreement_ratio,
            ))

    # Sort by agreement ratio (most contested first)
    divergence_points.sort(key=lambda dp: dp.agreement_ratio)

    return divergence_points


def compute_convergence(
    run_ids: List[str],
    db_path: str = "metadata/runs.db",
    template_id: Optional[str] = None,
) -> ConvergenceResult:
    """
    Compute convergence across multiple runs of the same scenario.

    This is the main entry point for convergence analysis.

    Args:
        run_ids: List of run identifiers to compare
        db_path: Path to database
        template_id: Optional template identifier

    Returns:
        ConvergenceResult with full analysis
    """
    if len(run_ids) < 2:
        raise ValueError("Need at least 2 runs to compute convergence")

    # Extract causal graphs from all runs
    graphs = []
    for rid in run_ids:
        try:
            g = extract_causal_graph(rid, db_path, template_id)
            graphs.append(g)
        except Exception as e:
            logger.warning(f"Failed to extract graph for run {rid}: {e}")

    if len(graphs) < 2:
        raise ValueError(f"Could only extract {len(graphs)} graphs, need at least 2")

    # Compute pairwise similarities
    similarities = []
    for g1, g2 in combinations(graphs, 2):
        sim = graph_similarity(g1, g2)
        similarities.append(sim)

    # Find consensus and contested edges
    all_edges: Set[Tuple[str, str, str]] = set()
    edge_counts: Dict[Tuple[str, str, str], int] = {}

    for g in graphs:
        for edge in g.all_edges:
            all_edges.add(edge)
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    n_graphs = len(graphs)
    consensus_edges = {e for e, count in edge_counts.items() if count == n_graphs}
    contested_edges = {e for e, count in edge_counts.items() if 0 < count < n_graphs}

    # Find divergence points
    divergence_points = find_divergence_points(graphs)

    return ConvergenceResult(
        run_ids=run_ids,
        template_id=template_id,
        mean_similarity=sum(similarities) / len(similarities) if similarities else 0.0,
        min_similarity=min(similarities) if similarities else 0.0,
        max_similarity=max(similarities) if similarities else 0.0,
        divergence_points=divergence_points,
        consensus_edges=consensus_edges,
        contested_edges=contested_edges,
    )


def compute_convergence_from_graphs(graphs: List[CausalGraph]) -> ConvergenceResult:
    """
    Compute convergence from pre-extracted graphs.

    Use this when you already have CausalGraph objects
    (e.g., from in-memory simulation results).

    Args:
        graphs: List of CausalGraph objects

    Returns:
        ConvergenceResult with full analysis
    """
    if len(graphs) < 2:
        raise ValueError("Need at least 2 graphs to compute convergence")

    run_ids = [g.run_id for g in graphs]
    template_id = graphs[0].template_id  # Assume all same template

    # Compute pairwise similarities
    similarities = []
    for g1, g2 in combinations(graphs, 2):
        sim = graph_similarity(g1, g2)
        similarities.append(sim)

    # Find consensus and contested edges
    all_edges: Set[Tuple[str, str, str]] = set()
    edge_counts: Dict[Tuple[str, str, str], int] = {}

    for g in graphs:
        for edge in g.all_edges:
            all_edges.add(edge)
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    n_graphs = len(graphs)
    consensus_edges = {e for e, count in edge_counts.items() if count == n_graphs}
    contested_edges = {e for e, count in edge_counts.items() if 0 < count < n_graphs}

    # Find divergence points
    divergence_points = find_divergence_points(graphs)

    return ConvergenceResult(
        run_ids=run_ids,
        template_id=template_id,
        mean_similarity=sum(similarities) / len(similarities) if similarities else 0.0,
        min_similarity=min(similarities) if similarities else 0.0,
        max_similarity=max(similarities) if similarities else 0.0,
        divergence_points=divergence_points,
        consensus_edges=consensus_edges,
        contested_edges=contested_edges,
    )
