
# ============================================================================
# graph.py - NetworkX graph operations and fixtures
# ============================================================================
import warnings
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict
import numpy as np

def create_test_graph(n_entities: int = 10, seed: int = 42) -> nx.Graph:
    """Create deterministic test graph"""
    np.random.seed(seed)
    G = nx.Graph()
    
    for i in range(n_entities):
        G.add_node(f"entity_{i}", 
                   entity_type="person",
                   age=np.random.randint(20, 80),
                   training_count=0,
                   query_count=0)
    
    # Add edges with relationship types
    for i in range(n_entities - 1):
        for j in range(i + 1, min(i + 4, n_entities)):
            if np.random.random() > 0.5:
                G.add_edge(f"entity_{i}", f"entity_{j}", 
                          relationship="knows",
                          strength=np.random.random())
    
    return G

def create_timeline_graph(start_date: datetime, end_date: datetime, resolution: str = "day") -> nx.DiGraph:
    """Create temporal graph with variable resolution"""
    G = nx.DiGraph()
    current = start_date
    delta = timedelta(days=1) if resolution == "day" else timedelta(hours=1)
    
    while current <= end_date:
        timepoint_id = current.isoformat()
        G.add_node(timepoint_id,
                   timestamp=current,
                   resolution=resolution,
                   training_status="untrained")
        
        # Connect to previous timepoint
        if current > start_date:
            prev = (current - delta).isoformat()
            if prev in G:
                G.add_edge(prev, timepoint_id, causality="temporal_succession")
        
        current += delta
    
    return G

def compute_centralities(G: nx.Graph) -> Dict[str, Dict[str, float]]:
    """Compute all centrality metrics"""
    # Suppress RuntimeWarning for small graphs
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=RuntimeWarning)
        return {
            "eigenvector": nx.eigenvector_centrality(G),
            "betweenness": nx.betweenness_centrality(G),
            "pagerank": nx.pagerank(G),
            "degree": dict(G.degree())
        }

def export_graph_data(graph: nx.Graph, filename: str):
    """Export graph in multiple formats for visualization"""
    import json
    from pathlib import Path

    # Create directory if it doesn't exist
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    # Node-link format for D3.js
    data = nx.node_link_data(graph)

    with open(filename + '.json', 'w') as f:
        json.dump(data, f, indent=2)

    # GraphML for Gephi/Cytoscape
    nx.write_graphml(graph, filename + '.graphml')

    print(f"Graph exported: {filename}.json, {filename}.graphml")

def print_graph_summary(graph: nx.Graph):
    """Print ASCII summary of graph structure"""
    print(f"\nGraph Summary:")
    print(f"  Nodes: {graph.number_of_nodes()}")
    print(f"  Edges: {graph.number_of_edges()}")
    print(f"  Density: {nx.density(graph):.4f}")
    print(f"  Connected: {nx.is_connected(graph)}")

    if graph.number_of_nodes() > 0:
        degrees = dict(graph.degree())
        avg_degree = sum(degrees.values()) / len(degrees)
        max_degree_node = max(degrees, key=degrees.get)

        print(f"  Average degree: {avg_degree:.2f}")
        print(f"  Most connected: {max_degree_node} ({degrees[max_degree_node]} connections)")
