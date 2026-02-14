# evaluation/convergence.py - Core causal graph convergence logic
"""
Causal graph extraction and convergence measurement for Timepoint simulations.

The unique value of Timepoint: it predicts causal mechanisms, not just outcomes.
This module measures whether multiple runs of the same scenario produce
consistent causal chains - convergence indicates robust mechanisms.

Two levels of convergence analysis are provided:

1. **Structural consistency** (edge-level): Measures whether runs produce the
   same causal graph edges via Jaccard similarity. High structural convergence
   means runs agree on exact causal links (who told whom, which timepoints
   connect). See ``graph_similarity`` and ``compute_convergence``.

2. **Outcome convergence** (outcome-level): Measures whether runs reach the
   same high-level conclusions even when the specific edges differ. Two runs
   where different characters discover contamination should count as convergent
   for the outcome, even if the precise information-flow paths diverge. See
   ``extract_outcome_summary``, ``outcome_similarity``, and
   ``compute_outcome_convergence``.

Key concepts:
- CausalGraph: Structured representation of timepoint chains + knowledge flow
- Convergence: Agreement across independent runs (different models/seeds/modes)
- Divergence points: Specific causal links where runs disagree
- Outcome summary: High-level characterisation (knowledge discovered, entity
  roles, critical entities, event ordering) derived from graph structure
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Set, Tuple, Dict, Optional, Any
from datetime import datetime
from itertools import combinations
import hashlib
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


# ---------------------------------------------------------------------------
# Outcome-level convergence analysis
# ---------------------------------------------------------------------------


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets.  Returns 1.0 when both are empty."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _classify_entity_role(in_degree: int, out_degree: int) -> str:
    """Classify an entity's role from its knowledge-edge degrees.

    * **source**: only outgoing knowledge edges (out > 0, in == 0)
    * **sink**: only incoming knowledge edges (in > 0, out == 0)
    * **relay**: both incoming and outgoing knowledge edges
    * **isolated**: no knowledge edges at all
    """
    if out_degree > 0 and in_degree == 0:
        return "source"
    elif in_degree > 0 and out_degree == 0:
        return "sink"
    elif in_degree > 0 and out_degree > 0:
        return "relay"
    else:
        return "isolated"


def _betweenness_from_knowledge_edges(
    entities: Set[str],
    knowledge_edges: Set[Tuple[str, str]],
) -> Dict[str, float]:
    """Approximate betweenness centrality for entities on the knowledge graph.

    Uses Brandes-style BFS from every source node.  The graph is treated as
    directed (knowledge flows from source to target).  Entities that sit on
    more shortest paths between other entities are considered more "critical"
    to the information flow.

    Returns a dict mapping entity_id -> betweenness score (unnormalised).
    """
    # Build adjacency list
    adjacency: Dict[str, List[str]] = {e: [] for e in entities}
    for src, tgt in knowledge_edges:
        if src in adjacency:
            adjacency[src].append(tgt)

    betweenness: Dict[str, float] = {e: 0.0 for e in entities}

    for source in entities:
        # BFS from source
        stack: List[str] = []
        predecessors: Dict[str, List[str]] = {e: [] for e in entities}
        sigma: Dict[str, int] = {e: 0 for e in entities}
        sigma[source] = 1
        dist: Dict[str, int] = {e: -1 for e in entities}
        dist[source] = 0
        queue: List[str] = [source]

        while queue:
            v = queue.pop(0)
            stack.append(v)
            for w in adjacency.get(v, []):
                # First visit?
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                # Shortest path via v?
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        # Back-propagation of dependencies
        delta: Dict[str, float] = {e: 0.0 for e in entities}
        while stack:
            w = stack.pop()
            for v in predecessors[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != source:
                betweenness[w] += delta[w]

    return betweenness


def extract_outcome_summary(graph: CausalGraph) -> Dict[str, Any]:
    """Extract high-level outcome characteristics from a causal graph.

    Rather than comparing individual edges, this function distills the graph
    into an *outcome summary* that captures what happened at a macro level:

    * ``knowledge_discovered`` -- set of information items that were
      propagated, derived from the endpoints of knowledge edges.
    * ``entity_roles`` -- mapping of each entity to its role in the
      information flow (``source``, ``sink``, ``relay``, or ``isolated``).
    * ``critical_entities`` -- the entities with the highest betweenness
      centrality in the knowledge graph (most knowledge edges pass through
      them).
    * ``event_sequence_hash`` -- a deterministic hash of the normalised
      temporal-edge sequence, useful for checking whether two runs follow
      the same event ordering.

    Args:
        graph: A :class:`CausalGraph` extracted from a single simulation run.

    Returns:
        Dictionary with the four keys described above.
    """
    # -- knowledge_discovered ------------------------------------------------
    # Each knowledge edge (source, target) represents a piece of information
    # being transferred.  We treat the frozenset {source, target} as the
    # canonical name for that information item so that direction does not
    # matter when comparing across runs.
    knowledge_discovered: Set[frozenset] = set()
    for src, tgt in graph.knowledge_edges:
        knowledge_discovered.add(frozenset({src, tgt}))

    # -- entity_roles --------------------------------------------------------
    in_degree: Counter = Counter()
    out_degree: Counter = Counter()
    for src, tgt in graph.knowledge_edges:
        out_degree[src] += 1
        in_degree[tgt] += 1

    entity_roles: Dict[str, str] = {}
    for entity in graph.entities:
        entity_roles[entity] = _classify_entity_role(
            in_degree.get(entity, 0),
            out_degree.get(entity, 0),
        )

    # -- critical_entities ---------------------------------------------------
    betweenness = _betweenness_from_knowledge_edges(
        graph.entities, graph.knowledge_edges,
    )
    if betweenness:
        max_score = max(betweenness.values())
        # Threshold: entities with betweenness >= 80 % of max are "critical".
        # When max_score is 0 (no paths), nothing is critical.
        if max_score > 0:
            threshold = max_score * 0.8
            critical_entities: Set[str] = {
                e for e, score in betweenness.items() if score >= threshold
            }
        else:
            critical_entities = set()
    else:
        critical_entities = set()

    # -- event_sequence_hash -------------------------------------------------
    # Sort temporal edges into a deterministic sequence and hash the result.
    # Sorting by (source, target) gives a canonical ordering that is stable
    # across runs regardless of insertion order.
    sorted_temporal = sorted(graph.temporal_edges)
    sequence_str = json.dumps(sorted_temporal, sort_keys=True)
    event_sequence_hash = hashlib.sha256(sequence_str.encode("utf-8")).hexdigest()

    return {
        "knowledge_discovered": knowledge_discovered,
        "entity_roles": entity_roles,
        "critical_entities": critical_entities,
        "event_sequence_hash": event_sequence_hash,
    }


def outcome_similarity(o1: Dict[str, Any], o2: Dict[str, Any]) -> float:
    """Compute weighted similarity between two outcome summaries.

    The similarity is a weighted combination of four components:

    * **knowledge Jaccard** (weight 0.4) -- Jaccard similarity between the
      ``knowledge_discovered`` sets.
    * **critical-entity Jaccard** (weight 0.3) -- Jaccard similarity between
      the ``critical_entities`` sets.
    * **role match rate** (weight 0.2) -- fraction of entities (present in
      either summary) that are assigned the same role.
    * **sequence similarity** (weight 0.1) -- 1.0 if the
      ``event_sequence_hash`` values are identical, 0.0 otherwise.

    Args:
        o1: Outcome summary from :func:`extract_outcome_summary`.
        o2: Outcome summary from :func:`extract_outcome_summary`.

    Returns:
        Similarity score in [0.0, 1.0].
    """
    # 1. Knowledge Jaccard (0.4)
    knowledge_sim = _jaccard(o1["knowledge_discovered"], o2["knowledge_discovered"])

    # 2. Critical-entity Jaccard (0.3)
    critical_sim = _jaccard(o1["critical_entities"], o2["critical_entities"])

    # 3. Role match rate (0.2)
    all_entities = set(o1["entity_roles"].keys()) | set(o2["entity_roles"].keys())
    if all_entities:
        matches = sum(
            1 for e in all_entities
            if o1["entity_roles"].get(e) == o2["entity_roles"].get(e)
        )
        role_sim = matches / len(all_entities)
    else:
        role_sim = 1.0  # Both empty

    # 4. Sequence similarity (0.1)
    sequence_sim = 1.0 if o1["event_sequence_hash"] == o2["event_sequence_hash"] else 0.0

    return (
        0.4 * knowledge_sim
        + 0.3 * critical_sim
        + 0.2 * role_sim
        + 0.1 * sequence_sim
    )


def compute_outcome_convergence(
    graphs: List[CausalGraph],
) -> Dict[str, Any]:
    """Compute outcome-level convergence across multiple simulation runs.

    This complements :func:`compute_convergence_from_graphs` (which measures
    *structural consistency* at the edge level) by measuring whether the runs
    reach the same high-level outcomes.

    Args:
        graphs: List of :class:`CausalGraph` objects (at least 2).

    Returns:
        Dictionary with the following keys:

        * ``outcome_mean_similarity`` -- average pairwise outcome similarity.
        * ``structural_mean_similarity`` -- average pairwise edge-level
          Jaccard similarity (the existing metric, included for comparison).
        * ``knowledge_convergence`` -- fraction of knowledge items that appear
          in *every* run.
        * ``role_stability`` -- fraction of entities that are assigned the
          same role in *every* run in which they appear.

    Raises:
        ValueError: If fewer than 2 graphs are provided.
    """
    if len(graphs) < 2:
        raise ValueError("Need at least 2 graphs to compute outcome convergence")

    # Extract outcome summaries
    summaries = [extract_outcome_summary(g) for g in graphs]

    # -- outcome_mean_similarity ---------------------------------------------
    outcome_sims: List[float] = []
    for s1, s2 in combinations(summaries, 2):
        outcome_sims.append(outcome_similarity(s1, s2))
    outcome_mean = sum(outcome_sims) / len(outcome_sims) if outcome_sims else 0.0

    # -- structural_mean_similarity ------------------------------------------
    structural_sims: List[float] = []
    for g1, g2 in combinations(graphs, 2):
        structural_sims.append(graph_similarity(g1, g2))
    structural_mean = (
        sum(structural_sims) / len(structural_sims) if structural_sims else 0.0
    )

    # -- knowledge_convergence -----------------------------------------------
    # Fraction of distinct knowledge items that appear in ALL runs.
    all_knowledge: Set[frozenset] = set()
    knowledge_counts: Counter = Counter()
    for s in summaries:
        for item in s["knowledge_discovered"]:
            all_knowledge.add(item)
            knowledge_counts[item] += 1
    n_runs = len(graphs)
    if all_knowledge:
        universal_knowledge = sum(
            1 for item in all_knowledge if knowledge_counts[item] == n_runs
        )
        knowledge_convergence = universal_knowledge / len(all_knowledge)
    else:
        knowledge_convergence = 1.0  # No knowledge in any run -- vacuously converged

    # -- role_stability ------------------------------------------------------
    # For each entity that appears in at least one run, check whether it has
    # the same role in every run where it appears.
    entity_role_sets: Dict[str, Set[str]] = {}
    for s in summaries:
        for entity, role in s["entity_roles"].items():
            if entity not in entity_role_sets:
                entity_role_sets[entity] = set()
            entity_role_sets[entity].add(role)

    if entity_role_sets:
        stable_count = sum(
            1 for roles in entity_role_sets.values() if len(roles) == 1
        )
        role_stability = stable_count / len(entity_role_sets)
    else:
        role_stability = 1.0  # No entities -- vacuously stable

    return {
        "outcome_mean_similarity": outcome_mean,
        "structural_mean_similarity": structural_mean,
        "knowledge_convergence": knowledge_convergence,
        "role_stability": role_stability,
    }
