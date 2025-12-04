"""
Retrieval package for Timepoint-Daedalus tensor RAG.

Phase 3: Retrieval System Implementation

This package provides:
- TensorRAG: Semantic search and resolution for trained tensors
- EmbeddingIndex: Vector index for efficient similarity search
- TensorComposer: Strategies for composing multiple tensors
- SearchResult: Data class for search results

Usage:
    from retrieval import TensorRAG, SearchResult

    rag = TensorRAG(tensor_db)
    results = rag.search("Victorian detective")
    composed = rag.compose(results[:2])
"""

from retrieval.embedding_index import EmbeddingIndex
from retrieval.composition import TensorComposer
from retrieval.tensor_rag import TensorRAG, SearchResult

__all__ = [
    # Main class
    "TensorRAG",
    "SearchResult",
    # Components
    "EmbeddingIndex",
    "TensorComposer",
]
