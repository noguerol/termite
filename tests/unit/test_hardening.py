"""Tests for security and robustness hardening measures.

Covers behaviour introduced during the security/enterprise review:
size limits, symlink safety, SHA-256 identifiers, EPUB archive guards,
parse-failure semantics, stopword whitelisting and language overrides.
"""

import zipfile

import pytest

from termite.config import CompressionConfig, PipelineConfig
from termite.pipeline import marker_parser as marker_parser_module
from termite.pipeline.compression import LexicalCompressor
from termite.pipeline.document_ingester import DocumentIngester
from termite.pipeline.marker_parser import DocumentParseError, MarkerParser
from termite.pipeline.output_generator import OutputGenerator


class TestFileDiscoverySecurity:
    """Document discovery must be robust against hostile filesystems."""

    def test_symlinked_directories_are_not_followed(self, tmp_path):
        """Files reachable only through symlinked dirs are not ingested."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.md").write_text("# hello")

        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret")

        (input_dir / "linkdir").symlink_to(outside, target_is_directory=True)

        ingester = DocumentIngester(input_dir=input_dir)
        names = [p.name for p in ingester.discover_documents()]

        assert "doc.md" in names
        assert "secret.txt" not in names

    def test_oversized_files_are_skipped(self, tmp_path):
        """Files above ``max_file_size_mb`` are excluded from discovery."""
        big = tmp_path / "big.txt"
        big.write_text("x" * 10_000)

        ingester = DocumentIngester(input_dir=tmp_path, max_file_size_mb=0.0001)
        assert ingester.discover_documents() == []

        unlimited = DocumentIngester(input_dir=tmp_path, max_file_size_mb=None)
        assert big in unlimited.discover_documents()

    def test_document_ids_use_sha256(self, tmp_path):
        """Document IDs are 12 hex chars derived from SHA-256."""
        doc_id = MarkerParser(mode="local")._generate_doc_id(tmp_path / "a.pdf")
        assert len(doc_id) == 12
        assert all(c in "0123456789abcdef" for c in doc_id)


class TestParseFailureSemantics:
    """Parse failures must raise, never silently ingest placeholders."""

    def test_missing_file_raises(self, tmp_path):
        parser = MarkerParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(tmp_path / "missing.pdf")

    def test_epub_without_opf_rejected(self, tmp_path):
        epub_path = tmp_path / "noopf.epub"
        with zipfile.ZipFile(epub_path, "w") as archive:
            archive.writestr("dummy.txt", "hello")

        with pytest.raises(DocumentParseError):
            MarkerParser()._extract_epub_text(epub_path)

    def test_epub_declared_bomb_rejected(self, tmp_path, monkeypatch):
        """A huge declared uncompressed total is rejected up front."""
        monkeypatch.setattr(marker_parser_module, "MAX_EPUB_TOTAL_BYTES", 50)
        epub_path = tmp_path / "bomb.epub"
        with zipfile.ZipFile(epub_path, "w") as archive:
            archive.writestr("package.opf", "x" * 100)

        with pytest.raises(DocumentParseError):
            MarkerParser()._extract_epub_text(epub_path)

    def test_epub_oversized_member_rejected(self, tmp_path, monkeypatch):
        """A member over the per-member limit is rejected."""
        monkeypatch.setattr(marker_parser_module, "MAX_EPUB_MEMBER_BYTES", 20)
        epub_path = tmp_path / "member.epub"
        opf = b"<package/>"
        with zipfile.ZipFile(epub_path, "w") as archive:
            archive.writestr("content.opf", opf * 5)  # 50 bytes > 20

        with pytest.raises(DocumentParseError):
            MarkerParser()._extract_epub_text(epub_path)


class TestStopwordsAndLanguage:
    """Stopword removal and language forcing behave as configured."""

    def test_whitelist_protects_words(self):
        compressor = LexicalCompressor(CompressionConfig(remove_stopwords=True))
        text = "the quick brown fox"
        result = compressor.filter_stopwords(text, lang="en", whitelist=["the"])
        assert "the" in result.split()

    def test_stopwords_removed_without_whitelist(self):
        compressor = LexicalCompressor(CompressionConfig(remove_stopwords=True))
        result = compressor.filter_stopwords("the quick brown fox", lang="en")
        assert "the" not in result.split()

    def test_language_override_forces_english(self):
        """Forced 'en' keeps Spanish content (English rules only)."""
        compressor = LexicalCompressor(CompressionConfig(remove_stopwords=True, language="en"))
        assert compressor._resolve_language("el niño") == "en"
        assert compressor.compress_text("el niño") == "el niño"

    def test_spanish_phrases_removed(self):
        """Multi-word Spanish phrases are removed by the phrase pass."""
        compressor = LexicalCompressor(CompressionConfig(remove_stopwords=True))
        result = compressor.compress_text("el resultado sin embargo fue positivo")
        assert "sin embargo" not in result


class TestConfigValidation:
    """New configuration fields are validated."""

    def test_max_file_size_positive(self):
        with pytest.raises(ValueError):
            PipelineConfig(max_file_size_mb=0)

    def test_language_literal(self):
        with pytest.raises(ValueError):
            CompressionConfig(language="fr")


class TestOutputHardening:

    def test_atomic_write_leaves_no_temp_files(self, tmp_path):
        OutputGenerator._atomic_write(tmp_path / "out.md", "content")
        assert (tmp_path / "out.md").read_text() == "content"
        assert not list(tmp_path.glob("*.tmp"))

    def test_sanitize_filename_blocks_traversal(self):
        gen = OutputGenerator()
        safe = gen._sanitize_filename("../../etc/passwd")
        assert "/" not in safe and ".." not in safe
        assert gen._sanitize_filename("...") != ""
