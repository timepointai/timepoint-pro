"""
Embedding index for semantic tensor search.

Uses numpy-based cosine similarity for portability.
Optional FAISS support for improved performance at scale.

Phase 3: Retrieval System
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from pathlib import Path


@dataclass
class EmbeddingIndex:
    """
    Vector index for semantic tensor search.

    Uses numpy-based cosine similarity by default.
    Supports optional FAISS backend for better scalability.

    Attributes:
        embedding_dim: Dimension of embeddings (default 384 for MiniLM)
        use_faiss: Whether to use FAISS backend if available
    """
    embedding_dim: int = 384
    use_faiss: bool = False

    # Internal storage
    _ids: List[str] = field(default_factory=list)
    _embeddings: Optional[np.ndarray] = None
    _id_to_idx: Dict[str, int] = field(default_factory=dict)
    _faiss_index: Optional[object] = None

    def __post_init__(self):
        """Initialize the index."""
        self._ids = []
        self._embeddings = None
        self._id_to_idx = {}
        self._faiss_index = None

        # Try to use FAISS if requested
        if self.use_faiss:
            try:
                import faiss
                self._faiss_index = faiss.IndexFlatIP(self.embedding_dim)
                self._faiss_available = True
            except ImportError:
                self._faiss_available = False
                self.use_faiss = False
        else:
            self._faiss_available = False

    @property
    def size(self) -> int:
        """Number of embeddings in the index."""
        return len(self._ids)

    def add(self, tensor_id: str, embedding: np.ndarray) -> None:
        """
        Add an embedding to the index.

        Args:
            tensor_id: Unique identifier for this tensor
            embedding: Embedding vector (must match embedding_dim)
        """
        # Validate embedding
        embedding = np.asarray(embedding, dtype=np.float32)
        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.embedding_dim}, "
                f"got {embedding.shape[0]}"
            )

        # Normalize for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        # Check if ID already exists
        if tensor_id in self._id_to_idx:
            # Update existing
            idx = self._id_to_idx[tensor_id]
            if self._embeddings is not None:
                self._embeddings[idx] = embedding
            if self._faiss_available and self._faiss_index is not None:
                # FAISS doesn't support in-place update, rebuild needed
                self._rebuild_faiss_index()
            return

        # Add new
        idx = len(self._ids)
        self._ids.append(tensor_id)
        self._id_to_idx[tensor_id] = idx

        # Add to embeddings array
        if self._embeddings is None:
            self._embeddings = embedding.reshape(1, -1)
        else:
            self._embeddings = np.vstack([self._embeddings, embedding])

        # Add to FAISS if available
        if self._faiss_available and self._faiss_index is not None:
            self._faiss_index.add(embedding.reshape(1, -1))

    def remove(self, tensor_id: str) -> bool:
        """
        Remove an embedding from the index.

        Args:
            tensor_id: ID of tensor to remove

        Returns:
            True if removed, False if not found
        """
        if tensor_id not in self._id_to_idx:
            return False

        idx = self._id_to_idx[tensor_id]

        # Remove from arrays
        self._ids.pop(idx)
        del self._id_to_idx[tensor_id]

        # Rebuild index mapping
        self._id_to_idx = {id_: i for i, id_ in enumerate(self._ids)}

        # Remove from embeddings
        if self._embeddings is not None and len(self._embeddings) > 0:
            self._embeddings = np.delete(self._embeddings, idx, axis=0)
            if len(self._embeddings) == 0:
                self._embeddings = None

        # Rebuild FAISS index if needed
        if self._faiss_available:
            self._rebuild_faiss_index()

        return True

    def search(
        self,
        query: np.ndarray,
        k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Search for nearest neighbors.

        Args:
            query: Query embedding vector
            k: Number of results to return

        Returns:
            List of (tensor_id, similarity_score) tuples, sorted by score descending
        """
        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        # Normalize query
        query = np.asarray(query, dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        # Limit k to actual size
        k = min(k, len(self._ids))

        if self._faiss_available and self._faiss_index is not None:
            # Use FAISS
            scores, indices = self._faiss_index.search(query.reshape(1, -1), k)
            results = [
                (self._ids[idx], float(score))
                for idx, score in zip(indices[0], scores[0])
                if idx >= 0 and idx < len(self._ids)
            ]
        else:
            # Use numpy cosine similarity
            similarities = np.dot(self._embeddings, query)
            top_indices = np.argsort(similarities)[::-1][:k]
            results = [
                (self._ids[idx], float(similarities[idx]))
                for idx in top_indices
            ]

        return results

    def get_embedding(self, tensor_id: str) -> Optional[np.ndarray]:
        """
        Get embedding for a tensor ID.

        Args:
            tensor_id: Tensor identifier

        Returns:
            Embedding array or None if not found
        """
        if tensor_id not in self._id_to_idx:
            return None
        idx = self._id_to_idx[tensor_id]
        return self._embeddings[idx] if self._embeddings is not None else None

    def _rebuild_faiss_index(self):
        """Rebuild the FAISS index from scratch."""
        if not self._faiss_available:
            return

        try:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            if self._embeddings is not None and len(self._embeddings) > 0:
                self._faiss_index.add(self._embeddings)
        except ImportError:
            pass

    def save(self, path: Path) -> None:
        """
        Save index to disk.

        Args:
            path: Path to save index (will create .npz file)
        """
        path = Path(path)

        # Save as numpy archive
        np.savez(
            str(path) + ".npz",
            ids=np.array(self._ids, dtype=object),
            embeddings=self._embeddings if self._embeddings is not None else np.array([]),
            embedding_dim=np.array([self.embedding_dim]),
        )

    def load(self, path: Path) -> None:
        """
        Load index from disk.

        Args:
            path: Path to load index from
        """
        path = Path(path)
        npz_path = str(path) + ".npz" if not str(path).endswith(".npz") else str(path)

        data = np.load(npz_path, allow_pickle=True)

        self._ids = list(data["ids"])
        self._id_to_idx = {id_: i for i, id_ in enumerate(self._ids)}

        embeddings = data["embeddings"]
        if len(embeddings) > 0:
            self._embeddings = embeddings
        else:
            self._embeddings = None

        if "embedding_dim" in data:
            self.embedding_dim = int(data["embedding_dim"][0])

        # Rebuild FAISS if needed
        if self._faiss_available:
            self._rebuild_faiss_index()

    def clear(self) -> None:
        """Clear all embeddings from the index."""
        self._ids = []
        self._embeddings = None
        self._id_to_idx = {}
        if self._faiss_available:
            self._rebuild_faiss_index()
