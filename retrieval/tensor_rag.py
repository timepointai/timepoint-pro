"""
Tensor RAG (Retrieval Augmented Generation) for semantic tensor search.

Provides semantic search over stored tensors using embeddings,
with composition and resolution capabilities.

Phase 3: Retrieval System
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Union
from pathlib import Path

from schemas import TTMTensor
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor, deserialize_tensor
from retrieval.embedding_index import EmbeddingIndex
from retrieval.composition import TensorComposer


@dataclass
class SearchResult:
    """
    Result from tensor search.

    Attributes:
        tensor_id: ID of the matched tensor
        score: Similarity score (0-1)
        tensor_record: Full tensor record from database
    """
    tensor_id: str
    score: float
    tensor_record: TensorRecord


class TensorRAG:
    """
    Semantic retrieval system for trained tensors.

    Provides:
    - Semantic search using sentence-transformers embeddings
    - Tensor composition from multiple matches
    - Entity tensor resolution for pipeline integration
    """

    def __init__(
        self,
        tensor_db: TensorDatabase,
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_dim: int = 384,
        auto_build_index: bool = True
    ):
        """
        Initialize TensorRAG.

        Args:
            tensor_db: TensorDatabase instance for tensor storage
            embedding_model: Name of sentence-transformers model
            embedding_dim: Dimension of embeddings
            auto_build_index: Whether to build index from database on init
        """
        self.tensor_db = tensor_db
        self.embedding_model_name = embedding_model
        self.embedding_dim = embedding_dim

        # Lazy load embedding model
        self._embedder = None

        # Initialize components
        self.index = EmbeddingIndex(embedding_dim=embedding_dim)
        self.composer = TensorComposer()

        # Build index from existing tensors
        if auto_build_index:
            self._build_index_from_database()

    @property
    def embedder(self):
        """Lazy load the sentence transformer model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self.embedding_model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for TensorRAG. "
                    "Install with: pip install sentence-transformers"
                )
        return self._embedder

    @property
    def index_size(self) -> int:
        """Number of tensors in the index."""
        return self.index.size

    def _build_index_from_database(self) -> None:
        """Build embedding index from all tensors in database."""
        # Get all tensors
        tensors = self.tensor_db.list_tensors()

        for record in tensors:
            # Use cached embedding if available
            if record.embedding_blob is not None:
                embedding = np.frombuffer(record.embedding_blob, dtype=np.float32)
            elif record.description:
                # Generate embedding from description
                embedding = self.generate_embedding(record.description)
                # Cache it
                record.embedding_blob = embedding.tobytes()
                self.tensor_db.save_tensor(record)
            else:
                # No description - skip or use entity_id
                embedding = self.generate_embedding(
                    f"{record.entity_id} {record.world_id or ''}"
                )

            self.index.add(record.tensor_id, embedding)

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding array
        """
        embedding = self.embedder.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)

    def search(
        self,
        query: str,
        n_results: int = 10,
        min_maturity: float = 0.0,
        categories: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Search for tensors matching a query.

        Args:
            query: Natural language search query
            n_results: Maximum number of results
            min_maturity: Minimum maturity threshold
            categories: Optional list of categories to filter

        Returns:
            List of SearchResults sorted by score descending
        """
        if not query:
            # Return all tensors if no query
            tensors = self.tensor_db.list_tensors()
            results = []
            for record in tensors[:n_results]:
                if record.maturity >= min_maturity:
                    if categories is None or (record.category and any(c in record.category for c in categories)):
                        results.append(SearchResult(
                            tensor_id=record.tensor_id,
                            score=1.0,
                            tensor_record=record
                        ))
            return results

        # Generate query embedding
        query_embedding = self.generate_embedding(query)

        # Search index (get more than needed for filtering)
        search_k = n_results * 3
        raw_results = self.index.search(query_embedding, k=search_k)

        # Build results with filtering
        results = []
        for tensor_id, score in raw_results:
            # Get full record
            record = self.tensor_db.get_tensor(tensor_id)
            if record is None:
                continue

            # Apply maturity filter
            if record.maturity < min_maturity:
                continue

            # Apply category filter
            if categories is not None:
                if record.category is None:
                    continue
                if not any(c in record.category for c in categories):
                    continue

            results.append(SearchResult(
                tensor_id=tensor_id,
                score=max(0.0, min(1.0, score)),  # Clamp to [0, 1]
                tensor_record=record
            ))

            if len(results) >= n_results:
                break

        return results

    def compose(
        self,
        results: List[SearchResult],
        weights: Optional[List[float]] = None,
        method: str = "weighted_blend"
    ) -> TTMTensor:
        """
        Compose tensors from search results.

        Args:
            results: List of SearchResults to compose
            weights: Optional weights (defaults to similarity scores)
            method: Composition method

        Returns:
            Composed TTMTensor
        """
        if not results:
            raise ValueError("Cannot compose empty results list")

        # Extract tensors
        tensors = []
        for result in results:
            tensor = deserialize_tensor(result.tensor_record.tensor_blob)
            tensors.append(tensor)

        # Default weights from scores
        if weights is None:
            weights = [r.score for r in results]

        return self.composer.compose_tensors(tensors, method=method, weights=weights)

    def resolve_for_entity(
        self,
        entity_description: str,
        scenario_context: str,
        min_maturity: float = 0.0,
        allow_composition: bool = True,
        composition_threshold: float = 0.7
    ) -> TTMTensor:
        """
        Resolve the best tensor for an entity.

        Args:
            entity_description: Description of the entity
            scenario_context: Context/scenario description
            min_maturity: Minimum maturity for matches
            allow_composition: Whether to compose multiple weak matches
            composition_threshold: Score threshold below which to compose

        Returns:
            Resolved TTMTensor
        """
        # Build combined query
        query = f"{entity_description} in {scenario_context}"

        # Search
        results = self.search(query, n_results=5, min_maturity=min_maturity)

        if not results:
            # No matches - create default tensor
            return self._create_default_tensor()

        # Strong single match
        if results[0].score > 0.9 or not allow_composition:
            tensor = deserialize_tensor(results[0].tensor_record.tensor_blob)
            return tensor

        # Check if top result is strong enough
        if results[0].score > composition_threshold:
            tensor = deserialize_tensor(results[0].tensor_record.tensor_blob)
            return tensor

        # Multiple weak matches - compose top 2-3
        top_results = [r for r in results[:3] if r.score > 0.3]
        if len(top_results) > 1:
            return self.compose(top_results)

        # Fall back to best match
        tensor = deserialize_tensor(results[0].tensor_record.tensor_blob)
        return tensor

    def _create_default_tensor(self) -> TTMTensor:
        """Create a default tensor when no match is found."""
        return TTMTensor.from_arrays(
            context=np.array([0.5] * 8, dtype=np.float32),
            biology=np.array([0.5] * 4, dtype=np.float32),
            behavior=np.array([0.5] * 8, dtype=np.float32),
        )

    def add_tensor(
        self,
        tensor_id: str,
        tensor: TTMTensor,
        description: str,
        maturity: float = 0.0,
        category: Optional[str] = None,
        entity_id: str = "",
        world_id: str = ""
    ) -> None:
        """
        Add a tensor to the index and database.

        Args:
            tensor_id: Unique tensor identifier
            tensor: TTMTensor to add
            description: Natural language description
            maturity: Tensor maturity score
            category: Optional category path
            entity_id: Entity identifier
            world_id: World identifier
        """
        # Generate embedding
        embedding = self.generate_embedding(description)

        # Create record
        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id=entity_id,
            world_id=world_id,
            tensor_blob=serialize_tensor(tensor),
            maturity=maturity,
            training_cycles=0,
            description=description,
            category=category,
            embedding_blob=embedding.tobytes(),
        )

        # Save to database
        self.tensor_db.save_tensor(record)

        # Add to index
        self.index.add(tensor_id, embedding)

    def update_tensor(
        self,
        tensor_id: str,
        tensor: TTMTensor,
        description: Optional[str] = None,
        maturity: Optional[float] = None
    ) -> None:
        """
        Update a tensor in the index and database.

        Args:
            tensor_id: Tensor identifier
            tensor: Updated TTMTensor
            description: New description (regenerates embedding if changed)
            maturity: New maturity score
        """
        # Get existing record
        record = self.tensor_db.get_tensor(tensor_id)
        if record is None:
            raise ValueError(f"Tensor not found: {tensor_id}")

        # Update fields
        record.tensor_blob = serialize_tensor(tensor)

        if maturity is not None:
            record.maturity = maturity

        if description is not None and description != record.description:
            record.description = description
            embedding = self.generate_embedding(description)
            record.embedding_blob = embedding.tobytes()
            self.index.add(tensor_id, embedding)  # Updates existing

        # Save to database
        self.tensor_db.save_tensor(record)

    def save_index(self, path: Union[str, Path]) -> None:
        """
        Save the embedding index to disk.

        Args:
            path: Path to save index
        """
        self.index.save(Path(path))

    def load_index(self, path: Union[str, Path]) -> None:
        """
        Load the embedding index from disk.

        Args:
            path: Path to load index from
        """
        self.index.load(Path(path))

    def rebuild_index(self) -> None:
        """Rebuild the embedding index from database."""
        self.index.clear()
        self._build_index_from_database()
