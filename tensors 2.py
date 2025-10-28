# ============================================================================
# tensors.py - Tensor operations with plugin registry
# ============================================================================
import numpy as np
from scipy.linalg import svd
from sklearn.decomposition import PCA, NMF
from typing import Callable, Dict, List, Optional
import networkx as nx

from schemas import Entity
class TensorCompressor:
    """Plugin registry for tensor compression algorithms"""
    _compressors = {}
    
    @classmethod
    def register(cls, name: str):
        def decorator(func: Callable):
            cls._compressors[name] = func
            return func
        return decorator
    
    @classmethod
    def compress(cls, tensor: np.ndarray, method: str, **kwargs) -> np.ndarray:
        if method not in cls._compressors:
            raise ValueError(f"Unknown compression method: {method}")
        return cls._compressors[method](tensor, **kwargs)
    
    @classmethod
    def run_all(cls, tensor: np.ndarray, **kwargs) -> Dict[str, np.ndarray]:
        return {name: func(tensor, **kwargs) for name, func in cls._compressors.items()}

@TensorCompressor.register("pca")
def pca_compress(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    if len(tensor.shape) == 1:
        tensor = tensor.reshape(1, -1)
    # For 1D tensors reshaped to (1, n_features), we can't compress below 1 component
    n_components = min(n_components, tensor.shape[1], tensor.shape[0])
    pca = PCA(n_components=max(1, n_components))  # Ensure at least 1 component
    return pca.fit_transform(tensor).flatten()

@TensorCompressor.register("svd")
def svd_compress(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    if len(tensor.shape) == 1:
        tensor = tensor.reshape(1, -1)
    U, S, Vt = svd(tensor, full_matrices=False)
    k = min(n_components, len(S), tensor.shape[0], tensor.shape[1])
    k = max(1, k)  # Ensure at least 1 component
    return (U[:, :k] @ np.diag(S[:k]) @ Vt[:k, :]).flatten()

@TensorCompressor.register("nmf")
def nmf_compress(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    if len(tensor.shape) == 1:
        tensor = tensor.reshape(1, -1)
    tensor = np.abs(tensor)  # NMF requires non-negative
    n_components = min(n_components, tensor.shape[0], tensor.shape[1])
    n_components = max(1, n_components)  # Ensure at least 1 component
    nmf = NMF(n_components=n_components, init='random', random_state=42)
    return nmf.fit_transform(tensor).flatten()

@TensorCompressor.register("decompress")
def decompress_tensor(compressed_data: Dict[str, List[float]], method: str = "pca") -> np.ndarray:
    """Decompress tensor using inverse transformation"""
    # Look for keys that contain the method name
    matching_keys = [k for k in compressed_data.keys() if method in k]
    if not matching_keys:
        raise ValueError(f"No compressed data found for method: {method}")

    # Use the first matching key
    key = matching_keys[0]
    compressed_array = np.array(compressed_data[key])

    if method == "pca":
        # For decompression, we need the original PCA components
        # This is a simplified version - in practice, we'd store/load the PCA model
        # For now, return the compressed data as-is (placeholder)
        return compressed_array
    elif method == "svd":
        return compressed_array
    else:
        return compressed_array

def load_compressed_entity_data(entity: Entity, tensor_type: str = "context") -> Optional[np.ndarray]:
    """Load and decompress entity tensor data from compressed storage"""
    if "compressed" not in entity.entity_metadata:
        return None

    compressed_data = entity.entity_metadata["compressed"]

    # For TENSOR_ONLY entities, we only have compressed data (assumed to be context)
    if entity.resolution_level.value == "tensor_only":
        return decompress_tensor(compressed_data, "pca")  # Default to PCA for context

    # For higher resolution entities, look for tensor-specific compression
    # Try different key patterns for the tensor type
    possible_keys = [
        f"{tensor_type}_pca",    # Specific tensor type with method
        f"{tensor_type}_svd",
        f"{tensor_type}_nmf",
        tensor_type,             # Just the tensor type
        f"{tensor_type}_compressed"  # Legacy format
    ]

    for key in possible_keys:
        if key in compressed_data:
            return decompress_tensor({key: compressed_data[key]}, "pca")

    # Fallback: if no specific tensor found, try to find any compressed data
    # This handles cases where we have general compression but not tensor-specific
    if compressed_data:
        first_key = next(iter(compressed_data.keys()))
        return decompress_tensor({first_key: compressed_data[first_key]}, "pca")

    return None

def compute_ttm_metrics(entity: Entity, graph: nx.Graph) -> Dict[str, float]:
    """Compute Timepoint Tensor Model metrics"""
    if entity.entity_id not in graph:
        return {}

    metrics = {
        "eigenvector_centrality": nx.eigenvector_centrality(graph).get(entity.entity_id, 0.0),
        "betweenness": nx.betweenness_centrality(graph).get(entity.entity_id, 0.0),
        "pagerank": nx.pagerank(graph).get(entity.entity_id, 0.0),
    }
    return metrics
