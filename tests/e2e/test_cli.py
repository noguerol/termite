"""End-to-end tests for Termite CLI."""

import pytest

from termite.__main__ import main


class TestCLI:
    """Tests for CLI functionality."""

    def test_cli_help(self, capsys):
        """Test CLI help output."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_cli_version(self, capsys):
        """Test CLI version output."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_cli_with_nonexistent_input(self, tmp_path):
        """Test CLI with non-existent input directory."""
        output_dir = tmp_path / "output"

        # This should return 1 (no documents found)
        result = main(
            [
                "--input",
                str(tmp_path / "nonexistent"),
                "--output",
                str(output_dir),
            ]
        )

        assert result == 1

    def test_cli_with_empty_directory(self, tmp_path):
        """Test CLI with empty directory."""
        input_dir = tmp_path / "empty"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
            ]
        )

        assert result == 1  # No documents

    def test_cli_with_documents(self, tmp_path):
        """Test CLI with actual documents."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("# Test Document\n\nContent here.")

        output_dir = tmp_path / "output"

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
            ]
        )

        assert result == 0
        assert (output_dir / "compressed_docs.md").exists()
        assert (output_dir / "compressed_index.md").exists()

    def test_cli_with_stats(self, tmp_path):
        """Test CLI with statistics output."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("Test content")

        output_dir = tmp_path / "output"

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--stats",
            ]
        )

        assert result == 0

    def test_cli_verbose_mode(self, tmp_path):
        """Test CLI with verbose output."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("Test content")

        output_dir = tmp_path / "output"

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--verbose",
            ]
        )

        assert result == 0

    def test_cli_mode_override(self, tmp_path):
        """Test CLI with mode override."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("Test")

        output_dir = tmp_path / "output"

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--mode",
                "local",
            ]
        )

        assert result == 0
