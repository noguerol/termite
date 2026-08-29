"""Integration tests for document ingestion."""

import pytest

from termite.pipeline.document_ingester import DocumentIngester
from termite.pipeline.marker_parser import MarkerParser


class TestDocumentIngestionWorkflow:
    """Integration tests for document ingestion workflow."""

    def test_discover_and_ingest_txt_file(self, tmp_path):
        """Test discovering and ingesting a text file."""
        # Create a test text file
        test_file = tmp_path / "test.txt"
        test_file.write_text("# Test Document\n\nThis is test content.")

        ingester = DocumentIngester(tmp_path)
        documents = ingester.discover_documents()

        assert len(documents) == 1
        assert documents[0].suffix == ".txt"

    def test_parse_txt_file_workflow(self, tmp_path):
        """Test parsing a text file through the pipeline."""
        # Create a test text file
        test_file = tmp_path / "sample.txt"
        test_file.write_text("# Sample Document\n\nThis is sample content for testing.")

        parser = MarkerParser()
        doc = parser.parse(test_file)

        assert doc.doc_id is not None
        assert len(doc.doc_id) == 12
        assert len(doc.chunks) >= 1
        assert doc.metadata.title is not None


class TestMarkerParserIntegration:
    """Integration tests for marker parser."""

    def test_parse_different_modes(self, tmp_path):
        """Test that parser works in different modes."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        # Local mode
        parser_local = MarkerParser(mode="local")
        doc_local = parser_local.parse(test_file)
        assert doc_local.source_file == str(test_file)

        # Cloud mode without API key should raise
        parser_cloud = MarkerParser(mode="cloud")
        with pytest.raises((ValueError, ImportError)):
            parser_cloud.parse(test_file)

    def test_chunk_extraction_preserves_structure(self, tmp_path):
        """Test that chunk extraction preserves document structure."""
        markdown = """# Title

## Section 1

Content of section 1.

## Section 2

Content of section 2.
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(markdown)

        parser = MarkerParser()
        chunks = parser.extract_chunks(markdown)

        # Headers should be preserved
        combined_content = "\n".join(c.content for c in chunks)
        assert "# Title" in combined_content
        assert "## Section" in combined_content
