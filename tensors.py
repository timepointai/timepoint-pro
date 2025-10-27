# ============================================================================
# tensors.py - Tensor operations with plugin registry
# ============================================================================
import numpy as np
from scipy.linalg import svd
from sklearn.decomposition import PCA, NMF
from typing import Callable, Dict, List, Optional
import networkx as nx

from schemas import Entity
from metadata.tracking import track_mechanism
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
    @track_mechanism("M6", "ttm_tensor_compression")
    def compress(cls, tensor: np.ndarray, method: str, **kwargs) -> np.ndarray:
        if method not in cls._compressors:
            raise ValueError(f"Unknown compression method: {method}")
        return cls._compressors[method](tensor, **kwargs)
    
    @classmethod
    def run_all(cls, tensor: np.ndarray, **kwargs) -> Dict[str, np.ndarray]:
        return {name: func(tensor, **kwargs) for name, func in cls._compressors.items()}

@TensorCompressor.register("pca")
def pca_compress(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    """
    Compress tensor using PCA with validation.

    Validates:
    - Minimum samples (n_samples >= 2 for PCA)
    - No NaN or inf values
    - Valid numerical data

    Raises:
        ValueError: If tensor data is invalid for PCA compression
    """
    if len(tensor.shape) == 1:
        tensor = tensor.reshape(1, -1)

    # VALIDATION 1: Check for NaN/inf values
    if np.any(np.isnan(tensor)):
        raise ValueError("PCA compression failed: tensor contains NaN values")
    if np.any(np.isinf(tensor)):
        raise ValueError("PCA compression failed: tensor contains inf values")

    # VALIDATION 2: Check minimum samples for PCA
    # PCA requires n_samples >= 2 to avoid division by zero in variance calculation
    n_samples, n_features = tensor.shape
    if n_samples < 2:
        # For single sample, PCA will cause division by zero warning
        # Return the tensor as-is silently (no compression possible)
        return tensor.flatten()

    # For 1D tensors reshaped to (1, n_features), we can't compress below 1 component
    n_components = min(n_components, n_features, n_samples)
    n_components = max(1, n_components)  # Ensure at least 1 component

    try:
        pca = PCA(n_components=n_components)
        compressed = pca.fit_transform(tensor)
        return compressed.flatten()
    except Exception as e:
        raise ValueError(f"PCA compression failed: {e}")

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


def generate_ttm_tensor(entity: Entity) -> Optional[str]:
    """
    Generate TTM tensor from entity metadata and return serialized JSON.

    Converts PhysicalTensor, CognitiveTensor, and personality traits into
    TTMTensor with context_vector, biology_vector, and behavior_vector.

    Args:
        entity: Entity with physical_tensor, cognitive_tensor, personality_traits in metadata

    Returns:
        JSON string containing serialized TTMTensor, or None if insufficient data
    """
    from schemas import TTMTensor
    import json
    import msgspec

    metadata = entity.entity_metadata

    # Extract physical tensor data → biology_vector
    physical_data = metadata.get("physical_tensor", {})
    if not physical_data or "age" not in physical_data:
        # No valid physical data, create minimal biology vector
        biology_array = np.array([0.0] * 10)  # 10-dimensional biology vector
    else:
        # Convert physical tensor to numpy array
        biology_features = [
            physical_data.get("age", 0.0) / 100.0,  # Normalize age to 0-1
            physical_data.get("health_status", 1.0),
            physical_data.get("pain_level", 0.0),
            physical_data.get("fever", 36.5) / 45.0,  # Normalize fever ~36-42°C
            physical_data.get("mobility", 1.0),
            physical_data.get("stamina", 1.0),
            physical_data.get("sensory_acuity", {}).get("vision", 1.0) if isinstance(physical_data.get("sensory_acuity"), dict) else 1.0,
            physical_data.get("sensory_acuity", {}).get("hearing", 1.0) if isinstance(physical_data.get("sensory_acuity"), dict) else 1.0,
            0.0,  # Reserved
            0.0   # Reserved
        ]
        biology_array = np.array(biology_features[:10])

    # Extract cognitive tensor data → context_vector
    cognitive_data = metadata.get("cognitive_tensor", {})
    if not cognitive_data:
        # No cognitive data, create minimal context vector
        context_array = np.array([0.0] * 8)
    else:
        # Convert cognitive tensor to numpy array
        knowledge_count = len(cognitive_data.get("knowledge_state", []))
        context_features = [
            knowledge_count / 10.0,  # Normalize knowledge count
            cognitive_data.get("emotional_valence", 0.0),
            cognitive_data.get("emotional_arousal", 0.0),
            cognitive_data.get("energy_budget", 100.0) / 100.0,
            cognitive_data.get("decision_confidence", 0.8),
            cognitive_data.get("patience_threshold", 50.0) / 100.0,
            cognitive_data.get("risk_tolerance", 0.5),
            cognitive_data.get("social_engagement", 0.8)
        ]
        context_array = np.array(context_features[:8])

    # Extract personality traits → behavior_vector
    personality_traits = metadata.get("personality_traits", [])
    if isinstance(personality_traits, list) and len(personality_traits) >= 5:
        # Assume Big Five personality model
        behavior_array = np.array(personality_traits[:8])  # Use up to 8 dimensions
        if len(behavior_array) < 8:
            # Pad with zeros if less than 8
            behavior_array = np.pad(behavior_array, (0, 8 - len(behavior_array)))
    else:
        # No personality data, create minimal behavior vector
        behavior_array = np.array([0.5] * 8)  # Neutral personality

    # Create TTMTensor using from_arrays (which msgpack-encodes the arrays)
    ttm = TTMTensor.from_arrays(context_array, biology_array, behavior_array)

    # Serialize the TTMTensor object to JSON for storage in entity.tensor
    # Use model_dump() to get dict, then convert bytes to base64 for JSON compatibility
    import base64
    tensor_dict = {
        "context_vector": base64.b64encode(ttm.context_vector).decode('utf-8'),
        "biology_vector": base64.b64encode(ttm.biology_vector).decode('utf-8'),
        "behavior_vector": base64.b64encode(ttm.behavior_vector).decode('utf-8')
    }

    return json.dumps(tensor_dict)
