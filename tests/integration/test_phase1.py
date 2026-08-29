"""Integration tests for Phase 1 components."""

from termite.config import TermiteConfig, load_config, save_config
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.utils.metrics import CompressionMetrics


class TestConfigWorkflow:
    """Integration tests for configuration workflow."""

    def test_save_load_workflow(self, tmp_path):
        """Test complete save and load workflow."""
        config = TermiteConfig()
        config.pipeline.mode = "cloud"

        config_file = tmp_path / "test_config.yaml"
        save_config(config, config_file)

        loaded = load_config(config_file)
        assert loaded.pipeline.mode == "cloud"


class TestDocumentWorkflow:
    """Integration tests for document processing workflow."""

    def test_document_creation_and_metrics(self):
        """Test creating documents and computing metrics."""
        doc = ParsedDocument(
            doc_id="test-doc",
            source_file="test.txt",
            chunks=[
                DocumentChunk(chunk_id="c1", content="First chunk", token_count=2),
                DocumentChunk(chunk_id="c2", content="Second chunk", token_count=3),
            ],
            metadata=DocumentMetadata(title="Test"),
        )

        # Calculate metrics
        metrics = CompressionMetrics.from_documents(
            original_tokens=doc.total_tokens(),
            compressed_tokens=doc.total_tokens() - 2,  # Simulate compression
            original_chars=doc.total_chars(),
            compressed_chars=doc.total_chars() - 5,
        )

        assert metrics.original_tokens == 5
        assert metrics.compression_ratio > 0
