"""Non-functional tests for Phase 6."""

import time

import pytest

from termite.config import TermiteConfig
from termite.pipeline.pipeline import TermitePipeline


class TestPipelinePerformance:
    """Performance tests for complete pipeline."""

    @pytest.mark.timeout(120)
    def test_pipeline_performance_small_corpus(self, tmp_path):
        """Test pipeline with small corpus completes quickly."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create 10 test documents
        for i in range(10):
            (input_dir / f"doc{i}.txt").write_text(
                f"# Document {i}\n\nThis is document number {i} "
                "with some content about Python, Docker, and other topics."
            )

        output_dir = tmp_path / "output"
        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = output_dir

        pipeline = TermitePipeline(config)

        start = time.time()
        stats = pipeline.run()
        duration = time.time() - start

        assert duration < 120
        assert stats["documents_parsed"] == 10

    @pytest.mark.timeout(300)
    def test_pipeline_performance_medium_corpus(self, tmp_path):
        """Test pipeline with medium corpus."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create 50 test documents
        for i in range(50):
            (input_dir / f"doc{i}.txt").write_text(
                f"# Document {i}\n\n"
                f"Content for document {i}. "
                "This includes references to Python, Docker, Kubernetes, "
                "and various technical concepts."
            )

        output_dir = tmp_path / "output"
        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = output_dir

        pipeline = TermitePipeline(config)
        stats = pipeline.run()

        assert stats["documents_parsed"] == 50
        assert stats["documents_deduplicated"] <= 50


class TestPipelineReliability:
    """Reliability tests for pipeline."""

    def test_pipeline_handles_malformed_files(self, tmp_path):
        """Test that pipeline handles various file types."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create various file types
        (input_dir / "valid.txt").write_text("Valid content")
        (input_dir / "empty.txt").write_text("")
        (input_dir / "long.txt").write_text("A" * 10000)  # Large file

        output_dir = tmp_path / "output"
        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = output_dir

        pipeline = TermitePipeline(config)
        stats = pipeline.run()

        # Should process at least some documents
        assert stats["documents_parsed"] >= 1

    def test_pipeline_creates_output_directory(self, tmp_path):
        """Test that pipeline creates output directory."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("Content")

        output_dir = tmp_path / "nested" / "output"
        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = output_dir

        pipeline = TermitePipeline(config)
        pipeline.run()

        assert output_dir.exists()
        assert (output_dir / "compressed_docs.md").exists()
