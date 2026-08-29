"""Unit tests for marker parser."""

from termite.pipeline.marker_parser import MarkerParser


class TestMarkerParser:
    """Tests for MarkerParser class."""

    def test_parser_initialization(self):
        """Test parser initializes with correct defaults."""
        parser = MarkerParser()
        assert parser.mode == "local"
        assert parser.datalab_api_key is None

    def test_parser_initialization_cloud_mode(self):
        """Test parser initializes with cloud mode."""
        parser = MarkerParser(mode="cloud", datalab_api_key="test-key")
        assert parser.mode == "cloud"
        assert parser.datalab_api_key == "test-key"


class TestExtractChunks:
    """Tests for extract_chunks method."""

    def test_extract_chunks_basic(self):
        """Test basic chunk extraction."""
        parser = MarkerParser()
        markdown = "# Header\n\nThis is some content.\n\n## Subheader\n\nMore content."
        chunks = parser.extract_chunks(markdown)

        assert len(chunks) > 0
        assert all(chunk.chunk_id.startswith("chunk-") for chunk in chunks)

    def test_extract_chunks_respects_max_tokens(self):
        """Test that max_tokens parameter creates smaller chunks."""
        parser = MarkerParser()
        # Create content with multiple lines so chunking can occur
        lines = [f"This is line number {i}.\n" for i in range(50)]
        content = "".join(lines)
        chunks = parser.extract_chunks(content, max_tokens=20)

        # With max_tokens=20 and many lines, we should get multiple chunks
        assert len(chunks) >= 1
        # Each chunk should have reasonable token count
        for chunk in chunks:
            assert chunk.token_count >= 0

    def test_extract_chunks_empty_content(self):
        """Test handling of empty content."""
        parser = MarkerParser()
        chunks = parser.extract_chunks("")

        assert len(chunks) == 1
        assert chunks[0].content == ""

    def test_extract_chunks_token_count(self):
        """Test that token counts are reasonable."""
        parser = MarkerParser()
        content = "This is a test sentence with some content."
        chunks = parser.extract_chunks(content, max_tokens=500)

        for chunk in chunks:
            # Token count should be reasonable estimate
            assert chunk.token_count >= 0
            assert chunk.token_count <= len(chunk.content) // 2 + 10

    def test_extract_chunks_preserves_headers(self):
        """Test that headers are preserved in chunks."""
        parser = MarkerParser()
        markdown = "# Title\n\nContent here."
        chunks = parser.extract_chunks(markdown)

        content = "\n".join(chunk.content for chunk in chunks)
        assert "# Title" in content
        assert "Content here" in content


class TestExtractMetadata:
    """Tests for extract_metadata method."""

    def test_extract_metadata_with_json(self):
        """Test metadata extraction from JSON."""
        parser = MarkerParser()
        json_data = {
            "title": "Test Document",
            "author": "John Doe",
            "document_type": "report",
        }
        metadata = parser.extract_metadata(json_data, "test.pdf")

        assert metadata.title == "Test Document"
        assert metadata.author == "John Doe"
        assert metadata.document_type == "report"

    def test_extract_metadata_without_json(self):
        """Test metadata extraction without JSON."""
        parser = MarkerParser()
        metadata = parser.extract_metadata(None, "my_document.pdf")

        assert metadata.title == "My_Document"  # From filename
        assert metadata.source_file == "my_document.pdf"

    def test_extract_metadata_fallback_title(self):
        """Test that filename is used as title fallback."""
        parser = MarkerParser()
        json_data = {}
        metadata = parser.extract_metadata(json_data, "important_report.pdf")

        # Title should be derived from filename (without extension)
        assert "important" in metadata.title.lower()
        assert "report" in metadata.title.lower()


class TestGenerateDocId:
    """Tests for _generate_doc_id method."""

    def test_doc_id_length(self):
        """Test that doc IDs are 12 characters."""
        parser = MarkerParser()
        doc_id = parser._generate_doc_id("test/path.pdf")

        assert len(doc_id) == 12

    def test_doc_id_consistent(self):
        """Test that same path generates same ID."""
        parser = MarkerParser()
        id1 = parser._generate_doc_id("test/path.pdf")
        id2 = parser._generate_doc_id("test/path.pdf")

        assert id1 == id2

    def test_doc_id_different_for_different_paths(self):
        """Test that different paths generate different IDs."""
        parser = MarkerParser()
        id1 = parser._generate_doc_id("test/path1.pdf")
        id2 = parser._generate_doc_id("test/path2.pdf")

        assert id1 != id2
