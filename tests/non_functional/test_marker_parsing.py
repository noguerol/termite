"""Non-functional tests for Phase 2 - Marker Integration."""

import time
from pathlib import Path

import pytest

from termite.pipeline.marker_parser import MarkerParser


class TestParsingPerformance:
    """Performance tests for document parsing."""

    @pytest.mark.timeout(30)
    def test_parse_small_text_file(self, tmp_path):
        """Text file < 10KB should parse in < 30s."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("This is a small test file.\n" * 100)

        parser = MarkerParser()
        start = time.time()
        doc = parser.parse(test_file)
        duration = time.time() - start

        assert duration < 30
        assert len(doc.chunks) >= 1

    @pytest.mark.timeout(60)
    def test_parse_medium_text_file(self, tmp_path):
        """Text file < 100KB should parse in < 60s."""
        test_file = tmp_path / "medium.txt"
        test_file.write_text("This is test content. " * 1000)

        parser = MarkerParser()
        start = time.time()
        doc = parser.parse(test_file)
        duration = time.time() - start

        assert duration < 60
        assert len(doc.chunks) >= 1


class TestReliability:
    """Reliability tests."""

    def test_missing_file_handling(self):
        """System should raise a clear error for missing files."""
        parser = MarkerParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("nonexistent_file.pdf"))

    def test_empty_file_handling(self, tmp_path):
        """System should handle empty files."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        parser = MarkerParser()
        doc = parser.parse(test_file)

        assert doc is not None
        assert len(doc.chunks) >= 1
