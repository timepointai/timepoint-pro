"""
ANDOS Layer Computer - Core Algorithm
======================================

Implements reverse topological ordering for entity training to solve
the circular tensor/dialog dependency that blocks M14 and M15.

Algorithm:
    1. Build interaction graph G = (V, E) from entity interactions
    2. Compute distances from target entity via reverse BFS
    3. Group entities by distance (periphery to core)
    4. Return layers for sequential training

Mathematical Definition:
    Given target entity A and interaction graph G:
    - Distance d(v) = shortest path length from v to A in G_reversed
    - Layer assignment: entities at distance d train before distance d-1
    - Invariant: All interaction partners have tensors before dialog synthesis
"""

import networkx as nx
from typing import List, Dict, Tuple, Optional, Any


def build_interaction_graph(
    interaction_config: Dict[str, Any]
) -> nx.DiGraph:
    """
    Build directed graph from interaction_graph configuration.

    Args:
        interaction_config: Dict with 'interactions' list containing:
            - from: source entity_id
            - to: target entity_id or list of entity_ids

    Returns:
        NetworkX directed graph with entity_id nodes and interaction edges

    Example:
        >>> config = {
        ...     "interactions": [
        ...         {"from": "holmes", "to": ["watson", "lestrade"]},
        ...         {"from": "watson", "to": ["mrs_hudson"]}
        ...     ]
        ... }
        >>> G = build_interaction_graph(config)
        >>> list(G.edges())
        [('holmes', 'watson'), ('holmes', 'lestrade'), ('watson', 'mrs_hudson')]
    """
    G = nx.DiGraph()

    interactions = interaction_config.get('interactions', [])

    for interaction in interactions:
        source = interaction['from']
        targets = interaction['to']

        # Handle both single target and list of targets
        if isinstance(targets, str):
            targets = [targets]

        # Add edges for each interaction
        for target in targets:
            G.add_edge(source, target)

    return G


def compute_entity_distances(
    graph: nx.DiGraph,
    target_entity_id: str
) -> Dict[str, int]:
    """
    Compute shortest path distance from each entity to target.

    Uses BFS on ORIGINAL graph to compute distance FROM each entity TO the target.
    This tells us how many steps away each entity is from being able to influence
    the target directly.

    Args:
        graph: Directed interaction graph (A→B means A talks to/influences B)
        target_entity_id: Core entity (distance 0)

    Returns:
        Dict mapping entity_id to distance (0 = core, higher = periphery)

    Raises:
        nx.NodeNotFound: If target_entity_id not in graph

    Example:
        >>> G = nx.DiGraph([('A', 'B'), ('B', 'C')])
        >>> distances = compute_entity_distances(G, 'A')
        >>> distances
        {'A': 0, 'B': 1, 'C': 2}
        # A is target (0), B is 1 step away from A, C is 2 steps away from A
    """
    try:
        # Use BFS on ORIGINAL graph to find distance FROM target TO each entity
        # In graph A→B→C, we want: A=0, B=1, C=2
        distances = nx.single_source_shortest_path_length(graph, target_entity_id)
        return distances
    except nx.NodeNotFound:
        raise nx.NodeNotFound(
            f"Target entity '{target_entity_id}' not found in interaction graph. "
            f"Available nodes: {list(graph.nodes())}"
        )


def group_by_distance(
    entity_ids: List[str],
    distances: Dict[str, int]
) -> List[List[str]]:
    """
    Group entity IDs by distance into training layers.

    Layers are ordered periphery-to-core:
        - layers[0] = periphery entities (max distance, train first)
        - layers[-1] = core entity (distance 0, train last)

    Args:
        entity_ids: List of all entity IDs to group
        distances: Dict mapping entity_id to distance from target

    Returns:
        List of entity ID lists, one per layer, ordered periphery-to-core

    Example:
        >>> entity_ids = ['A', 'B', 'C', 'orphan']
        >>> distances = {'A': 0, 'B': 1, 'C': 2}
        >>> layers = group_by_distance(entity_ids, distances)
        >>> layers
        [['C', 'orphan'], ['B'], ['A']]
    """
    if not distances:
        # No distance data - put all entities in one layer
        return [entity_ids]

    max_distance = max(distances.values())

    # Create layer buckets (0 to max_distance)
    layer_buckets = [[] for _ in range(max_distance + 1)]

    # Add entities to appropriate layer based on distance
    for entity_id in entity_ids:
        distance = distances.get(entity_id)

        if distance is not None:
            # Reverse: larger distance = earlier layer (periphery)
            layer_idx = max_distance - distance
            layer_buckets[layer_idx].append(entity_id)
        else:
            # Entity not in graph - add to periphery (seeds)
            layer_buckets[0].append(entity_id)

    # Remove empty layers
    layers = [layer for layer in layer_buckets if layer]

    return layers


def compute_andos_layers(
    entities: List[Any],
    target_entity_id: str,
    interaction_graph: Dict[str, Any]
) -> List[List[Any]]:
    """
    Compute ANDOS training layers via reverse topological ordering.

    This is the main ANDOS algorithm that solves the M14/M15 circular dependency
    by determining the correct order to train entities such that:
        - Entities at periphery (seeds) train first
        - Entities closer to target train later
        - All interaction partners have tensors before dialog synthesis

    Args:
        entities: List of Entity objects to order
        target_entity_id: Core entity (distance 0, trains last)
        interaction_graph: Dict with 'interactions' list defining entity interactions

    Returns:
        List of entity lists (layers), where:
            - layers[0] = periphery entities (seeds, max distance, train first)
            - layers[-1] = core entity (target, distance 0, trains last)

    Raises:
        ValueError: If interaction graph contains cycles (not a DAG)
        nx.NodeNotFound: If target_entity_id not in graph

    Example:
        >>> # Simple chain: A talks to B, B talks to C
        >>> entities = [EntityA, EntityB, EntityC]
        >>> graph_config = {
        ...     "interactions": [
        ...         {"from": "A", "to": "B"},
        ...         {"from": "B", "to": "C"}
        ...     ]
        ... }
        >>> layers = compute_andos_layers(entities, "A", graph_config)
        >>> # Returns: [[EntityC], [EntityB], [EntityA]]
        >>> # Training order: C first (periphery), then B, then A (core)
    """
    # Step 1: Build directed graph from interaction config
    G = build_interaction_graph(interaction_graph)

    # Step 2: Validate graph is acyclic (DAG property required)
    if not nx.is_directed_acyclic_graph(G):
        cycles = list(nx.simple_cycles(G))

        # Format cycle paths for error message
        cycle_paths = []
        for cycle in cycles:
            path = " → ".join(cycle + [cycle[0]])
            cycle_paths.append(path)

        raise ValueError(
            f"Interaction graph contains {len(cycles)} cycle(s). "
            f"ANDOS requires acyclic graph (DAG).\n\n"
            f"Cycles found:\n" +
            "\n".join(f"  - {path}" for path in cycle_paths) +
            "\n\nPlease fix template configuration to remove cycles."
        )

    # Step 3: Compute distances from target entity
    try:
        distances = compute_entity_distances(G, target_entity_id)
    except nx.NodeNotFound as e:
        # Target not in graph - use heuristic (all entities at distance 1)
        print(f"WARNING: {e}")
        print(f"Using fallback: all entities at distance 1 from virtual target")

        # Create single layer with all entities
        return [entities]

    # Step 4: Create entity lookup map
    entity_map = {e.entity_id: e for e in entities}

    # Step 5: Group entity IDs by distance
    entity_ids = list(entity_map.keys())
    layer_id_groups = group_by_distance(entity_ids, distances)

    # Step 6: Convert ID groups back to Entity objects
    layers = []
    for id_group in layer_id_groups:
        entity_layer = [entity_map[eid] for eid in id_group if eid in entity_map]
        if entity_layer:
            layers.append(entity_layer)

    return layers


def validate_andos_layers(
    layers: List[List[Any]],
    interaction_graph: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validate ANDOS layers satisfy dependency constraints.

    Checks that for each interaction (A → B), entity A appears in an earlier
    layer than entity B (lower layer index), ensuring A's tensor is available
    when B needs it for dialog synthesis.

    Args:
        layers: List of entity lists from compute_andos_layers()
        interaction_graph: Original interaction graph configuration

    Returns:
        Tuple of (is_valid: bool, violations: List[str])

    Example:
        >>> layers = [[EntityC], [EntityB], [EntityA]]
        >>> graph = {"interactions": [{"from": "A", "to": "B"}]}
        >>> valid, violations = validate_andos_layers(layers, graph)
        >>> valid
        True
    """
    violations = []

    # Build entity → layer index map
    entity_layer_map = {}
    for layer_idx, layer in enumerate(layers):
        for entity in layer:
            entity_layer_map[entity.entity_id] = layer_idx

    # Check each interaction
    interactions = interaction_graph.get('interactions', [])

    for interaction in interactions:
        source = interaction['from']
        targets = interaction['to']

        # Handle both single target and list
        if isinstance(targets, str):
            targets = [targets]

        source_layer = entity_layer_map.get(source)

        for target in targets:
            target_layer = entity_layer_map.get(target)

            # Source should be in later layer than target (higher index)
            # This ensures target trains first and has tensor ready
            if source_layer is not None and target_layer is not None:
                if source_layer <= target_layer:
                    violations.append(
                        f"{source} (layer {source_layer}) should be in later layer than "
                        f"{target} (layer {target_layer}) because {source} talks to {target}"
                    )

    return (len(violations) == 0, violations)


def print_andos_layers(
    layers: List[List[Any]],
    title: str = "ANDOS Training Layers"
) -> None:
    """
    Pretty-print ANDOS layer structure for debugging.

    Args:
        layers: List of entity lists from compute_andos_layers()
        title: Optional title for output
    """
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Total layers: {len(layers)}")
    print(f"Total entities: {sum(len(layer) for layer in layers)}")
    print()

    for idx, layer in enumerate(layers):
        entity_ids = [e.entity_id for e in layer]
        print(f"Layer {idx} ({len(layer)} entities): {entity_ids}")

    print(f"{'='*60}\n")
