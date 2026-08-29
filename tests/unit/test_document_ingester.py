"""Unit tests for document ingester."""

from pathlib import Path

from termite.pipeline.document_ingester import DocumentIngester


class TestDocumentIngester:
    """Tests for DocumentIngester class."""

    def test_initialization(self):
        """Test ingester initialization."""
        ingester = DocumentIngester(Path("./test_dir"))
        assert ingester.input_dir == Path("./test_dir")
        assert ingester.mode == "local"

    def test_supported_extensions(self):
        """Test supported file extensions."""
        ingester = DocumentIngester(Path("./test_dir"))
        assert ".pdf" in ingester.SUPPORTED_EXTENSIONS
        assert ".docx" in ingester.SUPPORTED_EXTENSIONS
        assert ".txt" in ingester.SUPPORTED_EXTENSIONS
        assert ".html" in ingester.SUPPORTED_EXTENSIONS

    def test_initialization_cloud_mode(self):
        """Test ingester initializes with cloud mode."""
        ingester = DocumentIngester(Path("./test_dir"), mode="cloud", datalab_api_key="key")
        assert ingester.mode == "cloud"
        assert ingester.datalab_api_key == "key"


class TestDiscoverDocuments:
    """Tests for discover_documents method."""

    def test_discover_nonexistent_directory(self, tmp_path):
        """Test discovering in non-existent directory."""
        ingester = DocumentIngester(tmp_path / "nonexistent")
        documents = ingester.discover_documents()
        assert documents == []

    def test_discover_no_documents(self, tmp_path):
        """Test discovering when no documents exist."""
        ingester = DocumentIngester(tmp_path)
        documents = ingester.discover_documents()
        assert documents == []

    def test_discover_pdf_files(self, tmp_path):
        """Test discovering PDF files."""
        (tmp_path / "doc1.pdf").touch()
        (tmp_path / "doc2.pdf").touch()
        (tmp_path / "other.txt").touch()

        ingester = DocumentIngester(tmp_path)
        documents = ingester.discover_documents()

        # Should find at least the 2 PDFs (other.txt might also be found)
        pdf_docs = [d for d in documents if d.suffix.lower() == ".pdf"]
        assert len(pdf_docs) == 2
        assert all(p.suffix.lower() == ".pdf" for p in pdf_docs)

    def test_discover_multiple_formats(self, tmp_path):
        """Test discovering multiple file formats."""
        (tmp_path / "doc1.pdf").touch()
        (tmp_path / "doc2.docx").touch()
        (tmp_path / "doc3.txt").touch()
        (tmp_path / "doc4.html").touch()

        ingester = DocumentIngester(tmp_path)
        documents = ingester.discover_documents()

        assert len(documents) == 4

    def test_discover_case_insensitive(self, tmp_path):
        """Test that discovery is case-insensitive."""
        (tmp_path / "doc1.PDF").touch()
        (tmp_path / "doc2.pdf").touch()

        ingester = DocumentIngester(tmp_path)
        documents = ingester.discover_documents()

        assert len(documents) == 2


class TestGenerateDocId:
    """Tests for generate_doc_id method."""

    def test_doc_id_length(self):
        """Test that generated IDs are 12 characters."""
        ingester = DocumentIngester(Path("./test"))
        doc_id = ingester.generate_doc_id(Path("test.pdf"))

        assert len(doc_id) == 12

    def test_doc_id_consistent(self):
        """Test that same file generates same ID."""
        ingester = DocumentIngester(Path("./test"))
        path = Path("test.pdf")
        id1 = ingester.generate_doc_id(path)
        id2 = ingester.generate_doc_id(path)

        assert id1 == id2

    def test_doc_id_different_for_different_files(self):
        """Test that different files generate different IDs."""
        ingester = DocumentIngester(Path("./test"))
        id1 = ingester.generate_doc_id(Path("file1.pdf"))
        id2 = ingester.generate_doc_id(Path("file2.pdf"))

        assert id1 != id2
