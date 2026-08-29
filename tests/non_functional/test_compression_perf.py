"""Non-functional tests for compression and output generation."""

import time

import pytest

from termite.config import TermiteConfig
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.pipeline.output_generator import OutputGenerator


class TestCompressionPerformance:
    """Performance tests for compression."""

    @pytest.mark.timeout(30)
    def test_compress_many_documents(self):
        """50 documents should compress in < 30s."""
        generator = OutputGenerator()

        docs = []
        for i in range(50):
            docs.append(
                ParsedDocument(
                    doc_id=f"doc{i}",
                    source_file=f"doc{i}.txt",
                    chunks=[
                        DocumentChunk(
                            chunk_id=f"doc{i}-1",
                            content=f"This is document number {i} with some content "
                            "for testing compression performance. The content includes "
                            "various words that will be processed.",
                            token_count=20,
                        )
                    ],
                )
            )

        start = time.time()
        result_docs, metadata = generator.generate_output(docs)
        duration = time.time() - start

        assert duration < 30
        assert len(result_docs) > 0
        assert metadata["compressed_tokens"] > 0

    @pytest.mark.timeout(10)
    def test_compress_single_document_fast(self):
        """Single document compression should be fast."""
        generator = OutputGenerator()

        doc = ParsedDocument(
            doc_id="doc1",
            source_file="doc1.txt",
            chunks=[
                DocumentChunk(
                    chunk_id="c1",
                    content="Word " * 100,
                    token_count=100,
                )
            ],
        )

        start = time.time()
        result_docs, _ = generator.generate_output([doc])
        duration = time.time() - start

        assert duration < 10
        assert len(result_docs) == 1


class TestOutputGenerationPerformance:
    """Performance tests for output generation."""

    @pytest.mark.timeout(60)
    def test_write_many_documents(self, tmp_path):
        """Writing 50 documents should complete in < 60s."""
        config = TermiteConfig()
        config.pipeline.output_dir = tmp_path / "output"
        generator = OutputGenerator(config)

        docs = []
        for i in range(50):
            docs.append(
                ParsedDocument(
                    doc_id=f"doc{i}",
                    source_file=f"doc{i}.txt",
                    chunks=[
                        DocumentChunk(
                            chunk_id=f"doc{i}-1",
                            content=f"Document {i} content for testing.",
                            token_count=10,
                        )
                    ],
                    metadata=DocumentMetadata(title=f"Document {i}"),
                )
            )

        result_docs, metadata = generator.generate_output(docs)

        start = time.time()
        generator.write_output(result_docs, metadata)
        duration = time.time() - start

        assert duration < 60
        assert (tmp_path / "output" / "compressed_docs.md").exists()


class TestCompressionRatio:
    """Tests for compression ratio targets."""

    def test_compression_ratio_calculation(self):
        """Test that compression ratio is calculated correctly."""
        generator = OutputGenerator()

        docs = [
            ParsedDocument(
                doc_id="doc1",
                source_file="doc1.txt",
                chunks=[
                    DocumentChunk(
                        chunk_id="c1",
                        content="This is a test document with some content",
                        token_count=10,
                    )
                ],
            )
        ]

        _, metadata = generator.generate_output(docs)

        # Compression ratio should be between 0 and 1
        assert 0 <= metadata["compression_ratio"] <= 1

    def test_deduplication_ratio_calculation(self):
        """Test that deduplication ratio is calculated correctly."""
        generator = OutputGenerator()

        docs = [
            self._make_doc("doc1", "Same content"),
            self._make_doc("doc2", "Same content"),
            self._make_doc("doc3", "Different content"),
        ]

        _, metadata = generator.generate_output(docs)

        # Should have deduplication ratio > 0
        assert metadata["deduplication_ratio"] > 0
        assert metadata["deduplication_ratio"] <= 1

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[
                DocumentChunk(
                    chunk_id=f"{doc_id}-1",
                    content=content,
                    token_count=len(content) // 4,
                )
            ],
        )


class TestReliability:
    """Reliability tests."""

    def test_empty_document_list(self):
        """System handles empty document list."""
        generator = OutputGenerator()
        result_docs, metadata = generator.generate_output([])

        assert result_docs == []
        assert metadata["total_documents"] == 0
        assert metadata["original_tokens"] == 0

    def test_single_document_compression(self):
        """Single document is processed correctly."""
        generator = OutputGenerator()

        doc = ParsedDocument(
            doc_id="doc1",
            source_file="doc1.txt",
            chunks=[
                DocumentChunk(chunk_id="c1", content="Content", token_count=2),
            ],
        )

        result_docs, metadata = generator.generate_output([doc])

        assert len(result_docs) == 1
        assert metadata["total_documents"] == 1

    def test_special_characters_preserved(self):
        """Special characters are preserved in output."""
        generator = OutputGenerator()

        doc = ParsedDocument(
            doc_id="doc1",
            source_file="doc1.txt",
            chunks=[
                DocumentChunk(
                    chunk_id="c1",
                    content="Code: `print('hello')` and Unicode: 日本語",
                    token_count=20,
                )
            ],
        )

        result_docs, _ = generator.generate_output([doc])

        content = result_docs[0].chunks[0].content
        assert "print" in content
        assert "`" in content
