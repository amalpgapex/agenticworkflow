from dataclasses import dataclass
from typing import Any
from pydantic import Field

from openai import BaseModel

@dataclass
class ComparisonAnalysis:
    """Analysis of differences between aligned chunks."""

    alignment_summary: str
    total_alignments: int
    unaligned_count: int
    detailed_comparisons: list[dict[str, Any]]

class AlignmentInput(BaseModel):
    """Input model for alignment executor."""

    source_chunks: list[dict[str, Any]] = Field(
        description="List of chunks from the source document with 'text', 'document_id', 'chunk_index'"
    )
    target_chunks: list[dict[str, Any]] = Field(
        description="List of chunks from the target document with 'text', 'document_id', 'chunk_index'"
    )
    similarity_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum similarity score to consider as match"
    )


class AlignmentResult(BaseModel):
    """Result of chunk alignment."""

    alignments: list[dict[str, Any]] = Field(description="List of chunk alignments with similarity scores")
    total_source_chunks: int = Field(description="Total number of source chunks")
    total_target_chunks: int = Field(description="Total number of target chunks")
    aligned_count: int = Field(description="Number of alignments found above threshold")
    unaligned_source_indices: list[int] = Field(description="Indices of source chunks with no match above threshold")