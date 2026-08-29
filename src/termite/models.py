"""Pydantic data models for Termite."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata extracted from a document."""

    title: str | None = None
    author: str | None = None
    date: datetime | None = None
    document_type: str | None = None
    source_file: str | None = None
    page_count: int | None = None


class DocumentChunk(BaseModel):
    """A chunk of content within a document."""

    chunk_id: str = Field(..., description="Unique identifier for this chunk")
    content: str = Field(..., description="The markdown content of the chunk")
    token_count: int = Field(default=0, ge=0, description="Estimated token count")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """A fully parsed document with chunks and metadata."""

    doc_id: str = Field(..., description="Unique document identifier")
    source_file: str = Field(..., description="Original source file path")
    chunks: list[DocumentChunk] = Field(default_factory=list)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def total_tokens(self) -> int:
        """Calculate total token count across all chunks."""
        return sum(chunk.token_count for chunk in self.chunks)

    def total_chars(self) -> int:
        """Calculate total character count."""
        return sum(len(chunk.content) for chunk in self.chunks)


class DeduplicationResult(BaseModel):
    """Result of deduplication operation."""

    original_count: int
    deduplicated_count: int
    duplicates_removed: int
    compression_ratio: float


class EntityCrossReference(BaseModel):
    """A cross-reference between documents."""

    source_doc_id: str
    target_doc_id: str
    common_entities: list[str] = Field(default_factory=list)
    reference_strength: float = Field(default=0.0, ge=0.0, le=1.0)


class CompressionResult(BaseModel):
    """Result of compression operation."""

    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    cross_references: list[EntityCrossReference] = Field(default_factory=list)
    deduplication_result: DeduplicationResult | None = None
