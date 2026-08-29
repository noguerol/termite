"""Unit tests for data models."""

import pytest
from pydantic import ValidationError

from termite.models import (
    CompressionResult,
    DeduplicationResult,
    DocumentChunk,
    DocumentMetadata,
    EntityCrossReference,
    ParsedDocument,
)


class TestDocumentMetadata:
    """Tests for DocumentMetadata model."""

    def test_empty_metadata(self):
        """Test creating empty metadata."""
        metadata = DocumentMetadata()
        assert metadata.title is None
        assert metadata.author is None

    def test_with_values(self):
        """Test creating metadata with values."""
        metadata = DocumentMetadata(
            title="Test Document",
            author="John Doe",
            document_type="report",
        )
        assert metadata.title == "Test Document"
        assert metadata.author == "John Doe"


class TestDocumentChunk:
    """Tests for DocumentChunk model."""

    def test_create_chunk(self):
        """Test creating a document chunk."""
        chunk = DocumentChunk(
            chunk_id="chunk-001",
            content="# Hello World",
            token_count=5,
        )
        assert chunk.chunk_id == "chunk-001"
        assert chunk.token_count == 5

    def test_default_metadata(self):
        """Test that metadata defaults to empty dict."""
        chunk = DocumentChunk(chunk_id="test", content="test")
        assert chunk.metadata == {}


class TestParsedDocument:
    """Tests for ParsedDocument model."""

    def test_create_document(self):
        """Test creating a parsed document."""
        doc = ParsedDocument(
            doc_id="doc-001",
            source_file="test.pdf",
            chunks=[
                DocumentChunk(chunk_id="c1", content="Chunk 1", token_count=10),
                DocumentChunk(chunk_id="c2", content="Chunk 2", token_count=20),
            ],
        )

        assert doc.doc_id == "doc-001"
        assert len(doc.chunks) == 2

    def test_total_tokens(self):
        """Test total_tokens calculation."""
        doc = ParsedDocument(
            doc_id="doc-001",
            source_file="test.pdf",
            chunks=[
                DocumentChunk(chunk_id="c1", content="Chunk 1", token_count=10),
                DocumentChunk(chunk_id="c2", content="Chunk 2", token_count=20),
            ],
        )

        assert doc.total_tokens() == 30

    def test_total_chars(self):
        """Test total_chars calculation."""
        doc = ParsedDocument(
            doc_id="doc-001",
            source_file="test.pdf",
            chunks=[
                DocumentChunk(chunk_id="c1", content="Hello", token_count=2),
                DocumentChunk(chunk_id="c2", content="World", token_count=2),
            ],
        )

        assert doc.total_chars() == 10


class TestDeduplicationResult:
    """Tests for DeduplicationResult model."""

    def test_create_result(self):
        """Test creating deduplication result."""
        result = DeduplicationResult(
            original_count=100,
            deduplicated_count=75,
            duplicates_removed=25,
            compression_ratio=0.25,
        )

        assert result.original_count == 100
        assert result.duplicates_removed == 25


class TestEntityCrossReference:
    """Tests for EntityCrossReference model."""

    def test_create_reference(self):
        """Test creating entity cross-reference."""
        ref = EntityCrossReference(
            source_doc_id="doc-001",
            target_doc_id="doc-002",
            common_entities=["Python", "ML"],
            reference_strength=0.8,
        )

        assert ref.source_doc_id == "doc-001"
        assert len(ref.common_entities) == 2
        assert ref.reference_strength == 0.8

    def test_reference_strength_bounds(self):
        """Test that reference strength is bounded."""
        with pytest.raises(ValidationError):
            EntityCrossReference(
                source_doc_id="doc-001",
                target_doc_id="doc-002",
                reference_strength=1.5,
            )


class TestCompressionResult:
    """Tests for CompressionResult model."""

    def test_create_result(self):
        """Test creating compression result."""
        result = CompressionResult(
            original_tokens=1000,
            compressed_tokens=700,
            compression_ratio=0.3,
        )

        assert result.original_tokens == 1000
        assert result.compressed_tokens == 700
        assert result.compression_ratio == 0.3
