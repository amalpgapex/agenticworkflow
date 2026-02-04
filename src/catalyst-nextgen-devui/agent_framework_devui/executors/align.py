# Copyright (c) Microsoft. All rights reserved.

"""Semantic Alignment Executor for Document Chunks.

This executor uses in-memory vector embeddings and semantic similarity
to align chunks from two documents. It matches each chunk from the first
document with its most similar chunk from the second document.
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from agent_framework import Executor, WorkflowContext, handler

from ..models.comparison_models import AlignmentInput, AlignmentResult

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================


@dataclass
class DocumentChunk:
    """Represents a single chunk of text from a document."""

    text: str
    document_id: str
    chunk_index: int
    metadata: dict[str, Any] | None = None


@dataclass
class ChunkAlignment:
    """Represents an alignment between two document chunks."""

    source_chunk: DocumentChunk
    target_chunk: DocumentChunk
    similarity_score: float


# ============================================================================
# Embedding and Similarity
# ============================================================================


class SimpleEmbedder:
    """Simple in-memory text embedder using basic TF-IDF style embeddings."""

    def __init__(self):
        """Initialize the embedder."""
        self.vocab: dict[str, int] = {}
        self.embeddings: dict[str, np.ndarray] = {}

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase and split on whitespace/punctuation."""
        import re

        text = text.lower()
        # Split on whitespace and punctuation
        tokens = re.findall(r"\w+", text)
        return tokens

    def _build_vocab(self, texts: list[str]) -> None:
        """Build vocabulary from texts."""
        self.vocab = {}
        unique_tokens = set()

        for text in texts:
            tokens = self._tokenize(text)
            unique_tokens.update(tokens)

        # Assign indices to unique tokens
        for idx, token in enumerate(sorted(unique_tokens)):
            self.vocab[token] = idx

    def _text_to_vector(self, text: str) -> np.ndarray:
        """Convert text to a sparse vector using vocabulary."""
        if not self.vocab:
            return np.array([])

        vector = np.zeros(len(self.vocab))
        tokens = self._tokenize(text)

        # Count term frequencies
        for token in tokens:
            if token in self.vocab:
                vector[self.vocab[token]] += 1

        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

    def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for a list of texts."""
        # Build vocabulary from all texts
        self._build_vocab(texts)

        # Generate vectors for each text
        embeddings = []
        for text in texts:
            vector = self._text_to_vector(text)
            embeddings.append(vector)

        return embeddings

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


# ============================================================================
# Alignment Executor
# ============================================================================


class SemanticAlignment(Executor):
    """
    Executor that aligns chunks from two documents using semantic similarity.

    Uses in-memory vector embeddings to compute similarity between chunks
    and finds the best matching chunk from the target document for each
    source chunk.
    """

    embedder: SimpleEmbedder

    def __init__(self, id: str = "Align"):
        """Initialize the alignment executor.

        Args:
            id: Executor ID for workflow tracking
        """
        self.embedder = SimpleEmbedder()
        super().__init__(id=id)

    @staticmethod
    def _dict_to_chunk(chunk_dict: dict[str, Any]) -> DocumentChunk:
        """Convert dictionary to DocumentChunk."""
        return DocumentChunk(
            text=chunk_dict.get("text", ""),
            document_id=chunk_dict.get("document_id", ""),
            chunk_index=chunk_dict.get("chunk_index", -1),
            metadata=chunk_dict.get("metadata", None),
        )

    def _align_chunks(
        self,
        source_chunks: list[DocumentChunk],
        target_chunks: list[DocumentChunk],
        threshold: float = 0.5,
    ) -> tuple[list[ChunkAlignment], list[int]]:
        """Align source chunks with target chunks using semantic similarity.

        Args:
            source_chunks: Chunks from the source document
            target_chunks: Chunks from the target document
            threshold: Minimum similarity score for alignment

        Returns:
            Tuple of (alignments, unaligned_source_indices)
        """
        # Prepare all texts for embedding
        all_texts = [chunk.text for chunk in source_chunks + target_chunks]

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(all_texts)} chunks")
        embeddings = self.embedder.embed_texts(all_texts)

        # Split embeddings
        source_embeddings = embeddings[: len(source_chunks)]
        target_embeddings = embeddings[len(source_chunks) :]

        # Compute similarity matrix
        alignments: list[ChunkAlignment] = []
        unaligned_indices: list[int] = []

        logger.info(f"Computing similarity matrix: {len(source_chunks)} x {len(target_chunks)}")
        for source_idx, (source_chunk, source_emb) in enumerate(zip(source_chunks, source_embeddings)):
            best_match_idx = -1
            best_similarity = -1.0

            # Find the best matching target chunk
            for target_idx, (target_chunk, target_emb) in enumerate(zip(target_chunks, target_embeddings)):
                similarity = self.embedder.cosine_similarity(source_emb, target_emb)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = target_idx

            # Create alignment if above threshold
            if best_similarity >= threshold:
                alignments.append(
                    ChunkAlignment(
                        source_chunk=source_chunk,
                        target_chunk=target_chunks[best_match_idx],
                        similarity_score=best_similarity,
                    )
                )
                logger.debug(
                    f"Aligned chunk {source_idx} with target {best_match_idx}: score={best_similarity:.3f}"
                )
            else:
                unaligned_indices.append(source_idx)
                logger.debug(f"No match for source chunk {source_idx}: best score={best_similarity:.3f}")

        return alignments, unaligned_indices

    @handler
    async def handle_alignment(
        self, input_data: AlignmentInput | dict[str, Any], ctx: WorkflowContext[AlignmentResult, None]
    ) -> None:
        """Handle chunk alignment request.

        Args:
            input_data: Alignment input with source and target chunks
            ctx: Workflow context for yielding output
        """
        # Parse input
        if isinstance(input_data, dict):
            try:
                input_data = AlignmentInput(**input_data)
            except Exception as e:
                logger.error(f"Failed to parse input: {e}")
                await ctx.send_message(
                    AlignmentResult(
                        alignments=[],
                        total_source_chunks=0,
                        total_target_chunks=0,
                        aligned_count=0,
                        unaligned_source_indices=[],
                    )
                )
                return

        # Convert dictionaries to DocumentChunk objects
        source_chunks = [self._dict_to_chunk(chunk) for chunk in input_data.source_chunks]
        target_chunks = [self._dict_to_chunk(chunk) for chunk in input_data.target_chunks]

        logger.info(
            f"Starting alignment: {len(source_chunks)} source chunks, "
            f"{len(target_chunks)} target chunks, threshold={input_data.similarity_threshold}"
        )

        # Perform alignment
        alignments, unaligned_indices = self._align_chunks(
            source_chunks, target_chunks, input_data.similarity_threshold
        )

        # Format results
        alignment_dicts = [
            {
                "source_chunk": {
                    "text": alignment.source_chunk.text,
                    "document_id": alignment.source_chunk.document_id,
                    "chunk_index": alignment.source_chunk.chunk_index,
                },
                "target_chunk": {
                    "text": alignment.target_chunk.text,
                    "document_id": alignment.target_chunk.document_id,
                    "chunk_index": alignment.target_chunk.chunk_index,
                },
                "similarity_score": float(alignment.similarity_score),
            }
            for alignment in alignments
        ]

        result = AlignmentResult(
            alignments=alignment_dicts,
            total_source_chunks=len(source_chunks),
            total_target_chunks=len(target_chunks),
            aligned_count=len(alignments),
            unaligned_source_indices=unaligned_indices,
        )

        logger.info(
            f"Alignment complete: {len(alignments)} alignments found, "
            f"{len(unaligned_indices)} unaligned source chunks"
        )

        # Yield the result
        await ctx.send_message(result)
