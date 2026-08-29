"""Unit tests for compression module - Multi-language support."""

from termite.config import CompressionConfig
from termite.pipeline.compression import SPANISH_STOPWORDS, LanguageDetector, LexicalCompressor


class TestLanguageDetector:
    """Tests for language detection."""

    def test_detect_spanish(self):
        """Test Spanish detection."""
        detector = LanguageDetector()
        text = "El proceso de construcción de ruedas requiere atención cuidadosa al detalle."
        assert detector.detect(text) == "es"

    def test_detect_english(self):
        """Test English detection."""
        detector = LanguageDetector()
        text = "The wheelbuilding process requires careful attention to detail."
        assert detector.detect(text) == "en"

    def test_detect_spanish_chars(self):
        """Test Spanish characters detection."""
        detector = LanguageDetector()
        text = "niñoños äl"
        assert detector.detect(text) == "es"

    def test_detect_english_words(self):
        """Test English words detection."""
        detector = LanguageDetector()
        text = "the and is are was were"
        assert detector.detect(text) == "en"


class TestSpanishStopwords:
    """Tests for Spanish stopwords."""

    def test_spanish_stopwords_exist(self):
        """Test that Spanish stopwords are defined."""
        assert len(SPANISH_STOPWORDS) > 100
        assert "el" in SPANISH_STOPWORDS
        assert "la" in SPANISH_STOPWORDS
        assert "de" in SPANISH_STOPWORDS
        assert "que" in SPANISH_STOPWORDS
        assert "en" in SPANISH_STOPWORDS

    def test_spanish_articles(self):
        """Test Spanish articles are stopwords."""
        assert "el" in SPANISH_STOPWORDS
        assert "la" in SPANISH_STOPWORDS
        assert "los" in SPANISH_STOPWORDS
        assert "las" in SPANISH_STOPWORDS
        assert "un" in SPANISH_STOPWORDS
        assert "una" in SPANISH_STOPWORDS

    def test_spanish_prepositions(self):
        """Test Spanish prepositions are stopwords."""
        assert "de" in SPANISH_STOPWORDS
        assert "en" in SPANISH_STOPWORDS
        assert "a" in SPANISH_STOPWORDS
        assert "con" in SPANISH_STOPWORDS
        assert "por" in SPANISH_STOPWORDS
        assert "para" in SPANISH_STOPWORDS


class TestRemoveConsecutiveDuplicates:
    """Tests for remove_consecutive_duplicates method."""

    def test_no_duplicates(self):
        """Test that text without duplicates is unchanged."""
        compressor = LexicalCompressor()
        text = "The cat sat on the mat."
        result = compressor.remove_consecutive_duplicates(text)
        assert result == "The cat sat on the mat."

    def test_consecutive_duplicates_removed(self):
        """Test that consecutive duplicate words are removed."""
        compressor = LexicalCompressor()
        text = "the the cat sat on the the mat"
        result = compressor.remove_consecutive_duplicates(text)
        assert "the the" not in result
        assert "the" in result

    def test_case_insensitive(self):
        """Test that duplicate detection is case insensitive."""
        compressor = LexicalCompressor()
        text = "Hello Hello world"
        result = compressor.remove_consecutive_duplicates(text)
        assert result == "Hello world"

    def test_empty_text(self):
        """Test handling of empty text."""
        compressor = LexicalCompressor()
        assert compressor.remove_consecutive_duplicates("") == ""

    def test_spanish_duplicates(self):
        """Test Spanish consecutive duplicate removal."""
        compressor = LexicalCompressor()
        text = "el el gato esta en en la casa"
        result = compressor.remove_consecutive_duplicates(text)
        assert "el el" not in result
        assert "en en" not in result


class TestRemoveStopwords:
    """Tests for remove_stopwords method."""

    def test_english_stopwords_filtered(self):
        """Test that English stopwords are removed."""
        compressor = LexicalCompressor()
        text = "The quick brown fox"
        result = compressor.filter_stopwords(text, lang="en")
        assert "the" not in result.lower()

    def test_spanish_stopwords_filtered(self):
        """Test that Spanish stopwords are removed."""
        compressor = LexicalCompressor()
        text = "El proceso de construcción de ruedas"
        result = compressor.filter_stopwords(text, lang="es")
        # After removal: "proceso construcción ruedas"
        assert "el" not in result.lower()
        assert "de" not in result.lower()
        assert "proceso" in result.lower()

    def test_filter_stopwords_preserved(self):
        """Test that whitelisted terms are preserved."""
        compressor = LexicalCompressor()
        text = "the python code"
        result = compressor.filter_stopwords(text, lang="en", whitelist={"python"})
        assert "python" in result

    def test_code_blocks_preserved(self):
        """Test that code blocks are preserved."""
        compressor = LexicalCompressor()
        text = "The code is here: `the print statement`"
        result = compressor.filter_stopwords(text, lang="en")
        assert "`the print statement`" in result

    def test_spanish_whitelist(self):
        """Test Spanish whitelist works."""
        compressor = LexicalCompressor()
        text = "el rueda bicicleta"
        result = compressor.filter_stopwords(text, lang="es", whitelist={"rueda"})
        assert "rueda" in result.lower()


class TestNormalizeHeaders:
    """Tests for normalize_headers method."""

    def test_headers_normalized(self):
        """Test that headers are normalized."""
        compressor = LexicalCompressor()
        markdown = "### Level 3 Header\n\nContent"
        result = compressor.normalize_headers(markdown, max_level=2)
        assert "## Level 3 Header" in result

    def test_headers_unchanged_if_within_limit(self):
        """Test that headers within limit are unchanged."""
        compressor = LexicalCompressor()
        markdown = "## Level 2 Header"
        result = compressor.normalize_headers(markdown, max_level=2)
        assert result == markdown

    def test_multiple_headers_normalized(self):
        """Test that multiple headers are normalized."""
        compressor = LexicalCompressor()
        markdown = "# H1\n##### H5\n## H2"
        result = compressor.normalize_headers(markdown, max_level=2)
        lines = result.split("\n")
        assert lines[0] == "# H1"
        assert lines[1] == "## H5"
        assert lines[2] == "## H2"


class TestCompressText:
    """Tests for compress_text method."""

    def test_compression_removes_duplicates(self):
        """Test that compression removes consecutive duplicates."""
        compressor = LexicalCompressor()
        text = "Hello Hello world"
        result = compressor.compress_text(text)
        assert "Hello Hello" not in result

    def test_compression_preserves_content(self):
        """Test that compression preserves main content."""
        compressor = LexicalCompressor()
        text = "Python is a programming language"
        result = compressor.compress_text(text)
        assert "Python" in result
        assert "language" in result

    def test_spanish_compression(self):
        """Test Spanish text compression."""
        compressor = LexicalCompressor(
            CompressionConfig(remove_stopwords=True, apply_stemming=True)
        )
        text = "El proceso de construcción de ruedas requiere atención cuidadosa"
        result = compressor.compress_text(text)
        # Should remove stopwords and apply stemming
        assert "el" not in result.lower()
        assert "de" not in result.lower()
        # Should preserve content (stemmed)
        assert "proces" in result.lower() or "proceso" in result.lower()

    def test_spanish_stemming(self):
        """Test Spanish stemming is applied."""
        compressor = LexicalCompressor(CompressionConfig(apply_stemming=True))
        # Note: Full test would require stemming verification
        text = "construcción construcciones"
        result = compressor.compress_text(text)
        # Both should be stemmed to similar root
        assert len(result) < len(text)


class TestCompressMarkdown:
    """Tests for compress_markdown method."""

    def test_preserves_code_blocks(self):
        """Test that code blocks are preserved."""
        compressor = LexicalCompressor()
        markdown = "```python\nprint('hello')\n```"
        result = compressor.compress_markdown(markdown)
        assert "```python" in result
        assert "print" in result

    def test_normalizes_headers_in_markdown(self):
        """Test that headers are normalized in markdown."""
        compressor = LexicalCompressor(CompressionConfig(normalize_headers=True))
        markdown = "##### Too Deep"
        result = compressor.compress_markdown(markdown)
        assert "##### Too Deep" not in result

    def test_spanish_markdown_compression(self):
        """Test Spanish markdown compression."""
        compressor = LexicalCompressor(
            CompressionConfig(remove_stopwords=True, apply_stemming=True)
        )
        markdown = "## Construcción de Ruedas\n\nEl proceso requiere atención"
        result = compressor.compress_markdown(markdown)
        assert "el" not in result.lower()
        assert "de" not in result.lower()


class TestCompressChunk:
    """Tests for compress_chunk method."""

    def test_compress_chunk(self):
        """Test compressing a chunk."""
        from termite.models import DocumentChunk

        compressor = LexicalCompressor()
        chunk = DocumentChunk(
            chunk_id="c1",
            content="Hello Hello world",
            token_count=5,
        )
        result = compressor.compress_chunk(chunk)
        assert "Hello Hello" not in result.content

    def test_compress_spanish_chunk(self):
        """Test compressing a Spanish chunk."""
        from termite.models import DocumentChunk

        compressor = LexicalCompressor(
            CompressionConfig(remove_stopwords=True, apply_stemming=True)
        )
        chunk = DocumentChunk(
            chunk_id="c1",
            content="El proceso de construcción requiere atención",
            token_count=8,
        )
        result = compressor.compress_chunk(chunk)
        assert result.content != chunk.content


class TestCompressDocument:
    """Tests for compress_document method."""

    def test_compress_document(self):
        """Test compressing a document."""
        from termite.models import DocumentChunk, ParsedDocument

        compressor = LexicalCompressor()
        doc = ParsedDocument(
            doc_id="doc1",
            source_file="test.txt",
            chunks=[
                DocumentChunk(chunk_id="c1", content="Hello Hello", token_count=3),
                DocumentChunk(chunk_id="c2", content="World World", token_count=3),
            ],
        )
        result = compressor.compress_document(doc)
        assert len(result.chunks) == 2
        assert "Hello Hello" not in result.chunks[0].content


class TestGetStopwords:
    """Tests for get_stopwords method."""

    def test_get_spanish_stopwords(self):
        """Test getting Spanish stopwords."""
        compressor = LexicalCompressor()
        stopwords = compressor.get_stopwords("es")
        assert "el" in stopwords
        assert "la" in stopwords
        assert "de" in stopwords

    def test_get_english_stopwords(self):
        """Test getting English stopwords."""
        compressor = LexicalCompressor()
        stopwords = compressor.get_stopwords("en")
        assert "the" in stopwords
        assert "a" in stopwords
        assert "is" in stopwords
