"""Integration tests for the complete pipeline."""

from termite.config import TermiteConfig
from termite.pipeline.pipeline import TermitePipeline, run_pipeline


class TestPipelineWorkflow:
    """Integration tests for pipeline workflow."""

    def test_pipeline_initialization(self):
        """Test that pipeline initializes correctly."""
        config = TermiteConfig()
        pipeline = TermitePipeline(config)
        assert pipeline.config is not None
        assert pipeline.deduplicator is not None
        assert pipeline.compressor is not None

    def test_pipeline_with_empty_directory(self, tmp_path):
        """Test pipeline with no documents."""
        config = TermiteConfig()
        config.pipeline.input_dir = tmp_path / "empty"
        config.pipeline.output_dir = tmp_path / "output"

        pipeline = TermitePipeline(config)
        stats = pipeline.run()

        assert stats["documents_discovered"] == 0
        assert stats["documents_parsed"] == 0

    def test_pipeline_processes_documents(self, tmp_path):
        """Test pipeline with actual documents."""
        # Create test input directory
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create test documents
        (input_dir / "doc1.txt").write_text("# Document 1\n\nPython content here.")
        (input_dir / "doc2.txt").write_text("# Document 2\n\nDocker content here.")

        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = tmp_path / "output"

        pipeline = TermitePipeline(config)
        stats = pipeline.run()

        assert stats["documents_discovered"] == 2
        assert stats["documents_parsed"] == 2
        assert stats["documents_deduplicated"] >= 1

    def test_pipeline_deduplication(self, tmp_path):
        """Test that deduplication works in pipeline."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create duplicate documents
        (input_dir / "doc1.txt").write_text("Same content in both files")
        (input_dir / "doc2.txt").write_text("Same content in both files")
        (input_dir / "doc3.txt").write_text("Different content")

        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = tmp_path / "output"

        pipeline = TermitePipeline(config)
        stats = pipeline.run()

        # Should have fewer documents after deduplication
        assert stats["documents_deduplicated"] < stats["documents_parsed"]

    def test_pipeline_output_generation(self, tmp_path):
        """Test that output files are generated."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "test.txt").write_text("# Test\n\nContent here.")

        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = tmp_path / "output"

        pipeline = TermitePipeline(config)
        pipeline.run()

        # Check output files exist
        assert (tmp_path / "output" / "compressed_docs.md").exists()
        assert (tmp_path / "output" / "compressed_index.md").exists()


class TestRunPipelineFunction:
    """Tests for run_pipeline convenience function."""

    def test_run_pipeline_empty(self, tmp_path):
        """Test run_pipeline with empty directory."""
        stats = run_pipeline(
            input_dir=tmp_path / "empty",
            output_dir=tmp_path / "output",
        )

        assert stats["documents_discovered"] == 0

    def test_run_pipeline_with_config(self, tmp_path):
        """Test run_pipeline with custom config."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("# Test Document")

        output_dir = tmp_path / "output"

        stats = run_pipeline(
            config_path="nonexistent.yaml",  # Will use defaults
            input_dir=input_dir,
            output_dir=output_dir,
            verbose=False,
        )

        assert stats is not None
        assert "compression_ratio" in stats


class TestPipelineStatistics:
    """Tests for pipeline statistics."""

    def test_statistics_accuracy(self, tmp_path):
        """Test that statistics are accurate."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("Some content for testing.")

        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = tmp_path / "output"

        pipeline = TermitePipeline(config)
        stats = pipeline.run()

        assert stats["documents_discovered"] == 1
        assert stats["documents_parsed"] == 1
        assert stats["original_tokens"] >= 0
        assert stats["compressed_tokens"] >= 0
        assert 0 <= stats["compression_ratio"] <= 1
        assert stats["execution_time_seconds"] >= 0

    def test_statistics_execution_time(self, tmp_path):
        """Test that execution time is recorded."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("Test content")

        config = TermiteConfig()
        config.pipeline.input_dir = input_dir
        config.pipeline.output_dir = tmp_path / "output"

        pipeline = TermitePipeline(config)
        stats = pipeline.run()

        assert "execution_time_seconds" in stats
        assert stats["execution_time_seconds"] < 60  # Should be fast
