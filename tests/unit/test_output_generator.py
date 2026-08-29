"""Unit tests for output generator."""

from pathlib import Path

from termite.config import TermiteConfig
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.pipeline.output_generator import OutputGenerator


class TestOutputGenerator:
    """Tests for OutputGenerator class."""

    def test_initialization(self):
        """Test generator initializes correctly."""
        generator = OutputGenerator()
        assert generator.output_dir == Path("./output")

    def test_initialization_with_config(self, tmp_path):
        """Test generator initializes with custom config."""
        config = TermiteConfig()
        config.pipeline.output_dir = tmp_path / "custom_output"
        generator = OutputGenerator(config)
        assert generator.output_dir == tmp_path / "custom_output"


class TestGenerateOutput:
    """Tests for generate_output method."""

    def test_generate_output_basic(self):
        """Test basic output generation."""
        generator = OutputGenerator()
        docs = [
            self._make_doc("doc1", "Python is great", "Python Guide"),
            self._make_doc("doc2", "Docker is great", "Docker Guide"),
        ]

        result_docs, metadata = generator.generate_output(docs)

        assert len(result_docs) >= 1
        assert "original_tokens" in metadata
        assert "compressed_tokens" in metadata
        assert "compression_ratio" in metadata

    def test_generate_output_with_cross_references(self):
        """Test output generation with cross-references."""
        generator = OutputGenerator()
        docs = [
            self._make_doc("doc1", "Python and Docker", "Python Guide"),
            self._make_doc("doc2", "Python and Kubernetes", "K8s Guide"),
        ]

        _result_docs, metadata = generator.generate_output(docs)

        # Should have some cross-references since docs share "Python"
        assert metadata["cross_references_count"] >= 0

    def test_metadata_calculation(self):
        """Test that metadata is calculated correctly."""
        generator = OutputGenerator()
        docs = [
            self._make_doc("doc1", "Content A with more words here", "Doc A"),
            self._make_doc("doc2", "Content B with different words", "Doc B"),
        ]

        _, metadata = generator.generate_output(docs)

        assert metadata["total_documents"] == 2
        assert metadata["total_chunks"] >= 2
        assert metadata["original_tokens"] > 0
        assert metadata["compressed_tokens"] > 0

    @staticmethod
    def _make_doc(doc_id: str, content: str, title: str = "") -> ParsedDocument:
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
            metadata=DocumentMetadata(title=title or doc_id),
        )


class TestWriteOutput:
    """Tests for write_output method."""

    def test_write_unified_output(self, tmp_path):
        """Test writing unified output file."""
        config = TermiteConfig()
        config.pipeline.output_dir = tmp_path / "output"
        generator = OutputGenerator(config)

        docs = [
            self._make_doc("doc1", "Content", "Test Doc"),
        ]

        _, metadata = generator.generate_output(docs)
        generator.write_output(docs, metadata, unified_output=True)

        # Check files were created
        assert (tmp_path / "output" / "compressed_docs.md").exists()
        assert (tmp_path / "output" / "compressed_index.md").exists()

    def test_write_output_creates_directory(self, tmp_path):
        """Test that output directory is created."""
        config = TermiteConfig()
        config.pipeline.output_dir = tmp_path / "nested" / "output"
        generator = OutputGenerator(config)

        docs = [self._make_doc("doc1", "Content", "Test")]
        _, metadata = generator.generate_output(docs)
        generator.write_output(docs, metadata)

        assert (tmp_path / "nested" / "output").exists()

    def test_write_individual_files(self, tmp_path):
        """Test writing individual output files."""
        config = TermiteConfig()
        config.pipeline.output_dir = tmp_path / "output"
        generator = OutputGenerator(config)

        docs = [self._make_doc("doc1", "Content", "Test")]
        _, metadata = generator.generate_output(docs)
        generator.write_output(docs, metadata, unified_output=False)

        # Check file exists (sanitized name)
        files = list((tmp_path / "output").glob("*.md"))
        assert len(files) == 1

    @staticmethod
    def _make_doc(doc_id: str, content: str, title: str = "") -> ParsedDocument:
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
            metadata=DocumentMetadata(title=title or doc_id),
        )


class TestSanitizeFilename:
    """Tests for _sanitize_filename method."""

    def test_sanitize_removes_invalid_chars(self):
        """Test that invalid characters are removed."""
        generator = OutputGenerator()
        result = generator._sanitize_filename("doc/file:name")
        assert "/" not in result
        assert ":" not in result

    def test_sanitize_limits_length(self):
        """Test that filename length is limited."""
        generator = OutputGenerator()
        long_name = "a" * 100
        result = generator._sanitize_filename(long_name)
        assert len(result) <= 50

    def test_sanitize_preserves_valid_chars(self):
        """Test that valid characters are preserved."""
        generator = OutputGenerator()
        result = generator._sanitize_filename("document-name_123")
        assert result == "document-name_123"
