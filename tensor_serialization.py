"""
Tensor serialization utilities for TTMTensor persistence.

Provides functions for:
- Binary serialization (msgpack) for efficient storage
- Dict conversion for JSON compatibility
- Roundtrip-safe encoding/decoding

Uses msgspec.msgpack for fast, compact binary encoding.
"""

import base64
from typing import Any

import msgspec
import numpy as np

from schemas import TTMTensor


def serialize_tensor(tensor: TTMTensor) -> bytes:
    """
    Serialize a TTMTensor to compact binary format.

    Uses msgspec.msgpack for efficient encoding of the three vectors.
    The result is a single bytes object suitable for database BLOB storage.

    Args:
        tensor: TTMTensor instance to serialize

    Returns:
        bytes: Compact binary representation

    Example:
        >>> tensor = TTMTensor.from_arrays(ctx, bio, beh)
        >>> blob = serialize_tensor(tensor)
        >>> recovered = deserialize_tensor(blob)
    """
    # Extract arrays from tensor
    context, biology, behavior = tensor.to_arrays()

    # Pack all three vectors into a single structure
    data = {
        "context": context.tolist(),
        "biology": biology.tolist(),
        "behavior": behavior.tolist(),
    }

    return msgspec.msgpack.encode(data)


def deserialize_tensor(blob: bytes) -> TTMTensor:
    """
    Deserialize bytes back to TTMTensor.

    Args:
        blob: Binary data from serialize_tensor()

    Returns:
        TTMTensor: Reconstructed tensor

    Raises:
        msgspec.DecodeError: If blob is malformed
        ValueError: If data structure is invalid
    """
    data = msgspec.msgpack.decode(blob)

    context = np.array(data["context"], dtype=np.float64)
    biology = np.array(data["biology"], dtype=np.float64)
    behavior = np.array(data["behavior"], dtype=np.float64)

    return TTMTensor.from_arrays(context, biology, behavior)


def tensor_to_dict(tensor: TTMTensor) -> dict[str, Any]:
    """
    Convert TTMTensor to JSON-serializable dict.

    Uses base64 encoding for the vector bytes to ensure JSON compatibility.
    This is useful for API responses or config files.

    Args:
        tensor: TTMTensor to convert

    Returns:
        dict: JSON-serializable representation with base64-encoded vectors

    Example:
        >>> d = tensor_to_dict(tensor)
        >>> json.dumps(d)  # Works!
    """
    return {
        "context_vector": base64.b64encode(tensor.context_vector).decode("utf-8"),
        "biology_vector": base64.b64encode(tensor.biology_vector).decode("utf-8"),
        "behavior_vector": base64.b64encode(tensor.behavior_vector).decode("utf-8"),
    }


def dict_to_tensor(d: dict[str, Any]) -> TTMTensor:
    """
    Convert dict back to TTMTensor.

    Args:
        d: Dict from tensor_to_dict()

    Returns:
        TTMTensor: Reconstructed tensor

    Raises:
        KeyError: If required keys are missing
        ValueError: If base64 decoding fails
    """
    return TTMTensor(
        context_vector=base64.b64decode(d["context_vector"]),
        biology_vector=base64.b64decode(d["biology_vector"]),
        behavior_vector=base64.b64decode(d["behavior_vector"]),
    )


def tensor_to_numpy(tensor: TTMTensor) -> np.ndarray:
    """
    Flatten TTMTensor to single 20-dimensional numpy array.

    Order: context (8) + biology (4) + behavior (8) = 20 dimensions

    Args:
        tensor: TTMTensor to flatten

    Returns:
        np.ndarray: Shape (20,) with all values concatenated
    """
    context, biology, behavior = tensor.to_arrays()
    return np.concatenate([context, biology, behavior])


def numpy_to_tensor(arr: np.ndarray) -> TTMTensor:
    """
    Reconstruct TTMTensor from flattened 20-dimensional array.

    Args:
        arr: Shape (20,) array from tensor_to_numpy()

    Returns:
        TTMTensor: Reconstructed tensor

    Raises:
        ValueError: If array shape is not (20,)
    """
    if arr.shape != (20,):
        raise ValueError(f"Expected shape (20,), got {arr.shape}")

    context = arr[:8]
    biology = arr[8:12]
    behavior = arr[12:20]

    return TTMTensor.from_arrays(context, biology, behavior)


def compute_tensor_hash(tensor: TTMTensor) -> str:
    """
    Compute stable hash for tensor content.

    Useful for detecting changes or deduplication.

    Args:
        tensor: TTMTensor to hash

    Returns:
        str: Hex digest of tensor content
    """
    import hashlib

    blob = serialize_tensor(tensor)
    return hashlib.sha256(blob).hexdigest()[:16]


def tensors_equal(t1: TTMTensor, t2: TTMTensor, rtol: float = 1e-5) -> bool:
    """
    Check if two tensors are approximately equal.

    Args:
        t1: First tensor
        t2: Second tensor
        rtol: Relative tolerance for float comparison

    Returns:
        bool: True if all values are within tolerance
    """
    arr1 = tensor_to_numpy(t1)
    arr2 = tensor_to_numpy(t2)
    return np.allclose(arr1, arr2, rtol=rtol)
