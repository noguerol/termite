"""Unit tests for entity graph."""

from termite.config import CrossReferenceConfig
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.pipeline.entity_graph import EntityGraph


class TestEntityGraph:
    """Tests for EntityGraph class."""

    def test_initialization(self):
        """Test graph initializes with defaults."""
        graph = EntityGraph()
        assert graph.min_common_entities == 2
        assert graph.max_refs_per_doc == 5
        assert graph.enabled is True

    def test_initialization_with_config(self):
        """Test graph initializes with custom config."""
        config = CrossReferenceConfig(
            min_common_entities=3,
            max_refs_per_doc=10,
        )
        graph = EntityGraph(config)
        assert graph.min_common_entities == 3
        assert graph.max_refs_per_doc == 10

    def test_disabled_graph(self):
        """Test that disabled graph doesn't build references."""
        config = CrossReferenceConfig(enabled=False)
        graph = EntityGraph(config)
        graph.build_graph([])
        assert len(graph._cross_refs) == 0


class TestBuildGraph:
    """Tests for build_graph method."""

    def test_build_graph_empty(self):
        """Test building graph with no documents."""
        graph = EntityGraph()
        result = graph.build_graph([])
        assert result is graph
        assert len(graph._doc_entities) == 0

    def test_build_graph_extracts_entities(self):
        """Test that graph extracts entities from documents."""
        graph = EntityGraph()
        doc = self._make_doc("doc1", "Python and Docker are great.")

        graph.build_graph([doc])

        assert "doc1" in graph._doc_entities
        # Should have extracted technical terms
        assert len(graph._doc_entities["doc1"]) > 0

    def test_build_graph_creates_references(self):
        """Test that graph creates cross-references."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))

        doc1 = self._make_doc("doc1", "Python programming")
        doc2 = self._make_doc("doc2", "Python and Docker")

        graph.build_graph([doc1, doc2])

        # Should have created cross-references
        refs = graph.find_cross_references("doc1")
        assert len(refs) > 0

    def test_build_graph_no_references_without_common_entities(self):
        """Test that no references are created without common entities."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=2))

        doc1 = self._make_doc("doc1", "Python programming")
        doc2 = self._make_doc("doc2", "Java programming")

        graph.build_graph([doc1, doc2])

        # Should have no cross-references (Python ≠ Java)
        refs = graph.find_cross_references("doc1")
        assert len(refs) == 0

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[
                DocumentChunk(
                    chunk_id=f"{doc_id}-1",
                    content=content,
                    token_count=5,
                )
            ],
            metadata=DocumentMetadata(title=doc_id),
        )


class TestFindCrossReferences:
    """Tests for find_cross_references method."""

    def test_find_cross_references_empty(self):
        """Test finding references for document with none."""
        graph = EntityGraph()
        refs = graph.find_cross_references("nonexistent")
        assert refs == []

    def test_find_cross_references_returns_references(self):
        """Test that cross-references are returned correctly."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))

        doc1 = self._make_doc("doc1", "Python and Docker")
        doc2 = self._make_doc("doc2", "Python and Kubernetes")

        graph.build_graph([doc1, doc2])

        refs = graph.find_cross_references("doc1")
        assert len(refs) > 0
        assert refs[0].target_doc_id == "doc2"
        assert "python" in [e.lower() for e in refs[0].common_entities]

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[
                DocumentChunk(
                    chunk_id=f"{doc_id}-1",
                    content=content,
                    token_count=5,
                )
            ],
            metadata=DocumentMetadata(title=doc_id),
        )


class TestInjectCrossReferences:
    """Tests for inject_cross_references method."""

    def test_inject_references_into_empty_document(self):
        """Test injecting references into document with no chunks."""
        graph = EntityGraph()
        doc = ParsedDocument(
            doc_id="doc1",
            source_file="test.txt",
            chunks=[],
        )

        result = graph.inject_cross_references(doc)
        assert result == doc  # Unchanged

    def test_inject_references_adds_comment(self):
        """Test that cross-reference comment is added."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))

        doc1 = self._make_doc("doc1", "Python is great")
        doc2 = self._make_doc("doc2", "Python with Docker")

        graph.build_graph([doc1, doc2])

        result = graph.inject_cross_references(doc1)

        # Check first chunk has cross-reference comment
        assert len(result.chunks) > 0
        content = result.chunks[0].content
        assert "CROSS-REF" in content
        assert "doc2" in content

    def test_inject_with_title_map(self):
        """Test that title map is used for display."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))

        doc1 = self._make_doc("doc1", "Python")
        doc2 = self._make_doc("doc2", "Python and Docker")

        graph.build_graph([doc1, doc2])

        title_map = {"doc2": "Docker Guide"}
        result = graph.inject_cross_references(doc1, title_map)

        content = result.chunks[0].content
        assert "Docker Guide" in content

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[
                DocumentChunk(
                    chunk_id=f"{doc_id}-1",
                    content=content,
                    token_count=5,
                )
            ],
            metadata=DocumentMetadata(title=doc_id),
        )


class TestGetStatistics:
    """Tests for get_statistics method."""

    def test_statistics_empty_graph(self):
        """Test statistics for empty graph."""
        graph = EntityGraph()
        stats = graph.get_statistics()

        assert stats["total_documents"] == 0
        assert stats["total_cross_references"] == 0

    def test_statistics_with_documents(self):
        """Test statistics with documents."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))

        doc1 = self._make_doc("doc1", "Python")
        doc2 = self._make_doc("doc2", "Python")

        graph.build_graph([doc1, doc2])
        stats = graph.get_statistics()

        assert stats["total_documents"] == 2
        assert stats["total_cross_references"] >= 0

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[
                DocumentChunk(
                    chunk_id=f"{doc_id}-1",
                    content=content,
                    token_count=5,
                )
            ],
            metadata=DocumentMetadata(title=doc_id),
        )
