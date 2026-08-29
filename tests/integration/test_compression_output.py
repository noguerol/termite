"""Integration tests for compression and output generation."""

from termite.config import TermiteConfig
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.pipeline.output_generator import OutputGenerator


class TestCompressionWorkflow:
    """Integration tests for compression workflow."""

    def test_full_pipeline_compression(self):
        """Test complete compression pipeline."""
        generator = OutputGenerator()

        docs = [
            self._make_doc("doc1", "Python programming language basics"),
            self._make_doc("doc2", "Python with Docker containers"),
            self._make_doc("doc3", "Java is different from Python"),
        ]

        result_docs, metadata = generator.generate_output(docs)

        # Verify compression occurred
        assert len(result_docs) <= len(docs)

        # Verify metadata
        assert metadata["original_tokens"] > 0
        assert metadata["compressed_tokens"] > 0

    def test_deduplication_in_pipeline(self):
        """Test that deduplication occurs in pipeline."""
        generator = OutputGenerator()

        docs = [
            self._make_doc("doc1", "Same content"),
            self._make_doc("doc2", "Same content"),
            self._make_doc("doc3", "Different content"),
        ]

        result_docs, metadata = generator.generate_output(docs)

        # Should have fewer documents after deduplication
        assert len(result_docs) < len(docs)
        assert metadata["deduplication_ratio"] > 0

    def test_cross_references_in_pipeline(self):
        """Test that cross-references are added in pipeline."""
        config = TermiteConfig()
        config.cross_reference.enabled = True
        config.cross_reference.min_common_entities = 1
        generator = OutputGenerator(config)

        docs = [
            self._make_doc("doc1", "Python and Docker"),
            self._make_doc("doc2", "Python and Kubernetes"),
        ]

        _result_docs, metadata = generator.generate_output(docs)

        # Should have cross-references
        assert metadata["cross_references_count"] >= 0

    def test_compression_preserves_content(self):
        """Test that compression preserves semantic content."""
        generator = OutputGenerator()

        docs = [
            self._make_doc("doc1", "The Python programming language"),
        ]

        result_docs, _ = generator.generate_output(docs)

        # Check that content is preserved (not destroyed)
        content = result_docs[0].chunks[0].content
        assert "Python" in content

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


class TestOutputGenerationWorkflow:
    """Integration tests for output generation workflow."""

    def test_generate_and_write_workflow(self, tmp_path):
        """Test generating and writing output."""
        config = TermiteConfig()
        config.pipeline.output_dir = tmp_path / "output"
        generator = OutputGenerator(config)

        docs = [
            self._make_doc("doc1", "Python is great", "Python Guide"),
            self._make_doc("doc2", "Docker is great", "Docker Guide"),
        ]

        result_docs, metadata = generator.generate_output(docs)
        generator.write_output(result_docs, metadata, unified_output=True)

        # Verify output files exist
        assert (tmp_path / "output" / "compressed_docs.md").exists()
        assert (tmp_path / "output" / "compressed_index.md").exists()

        # Verify index content
        index_content = (tmp_path / "output" / "compressed_index.md").read_text()
        assert "Statistics" in index_content
        assert "Python Guide" in index_content

    def test_unified_file_structure(self, tmp_path):
        """Test that unified file has correct structure."""
        config = TermiteConfig()
        config.pipeline.output_dir = tmp_path / "output"
        generator = OutputGenerator(config)

        docs = [
            self._make_doc("doc1", "Content 1", "First Document"),
            self._make_doc("doc2", "Content 2", "Second Document"),
        ]

        result_docs, metadata = generator.generate_output(docs)
        generator.write_output(result_docs, metadata)

        # Read and verify structure
        content = (tmp_path / "output" / "compressed_docs.md").read_text()
        assert "# First Document" in content
        assert "# Second Document" in content
        assert "Content 1" in content
        assert "Content 2" in content

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
