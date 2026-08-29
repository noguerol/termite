"""Integration tests for entity extraction and cross-referencing."""

from termite.config import CrossReferenceConfig
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.pipeline.entity_extractor import EntityExtractor
from termite.pipeline.entity_graph import EntityGraph


class TestEntityExtractionWorkflow:
    """Integration tests for entity extraction workflow."""

    def test_extract_entities_from_multiple_documents(self):
        """Test extracting entities from multiple documents."""
        extractor = EntityExtractor()

        docs = [
            self._make_doc("doc1", "Python and Docker are essential tools."),
            self._make_doc("doc2", "Kubernetes manages Docker containers."),
            self._make_doc("doc3", "JavaScript runs in browsers."),
        ]

        all_entities = []
        for doc in docs:
            entities = extractor.extract_from_document(doc)
            all_entities.extend(entities)

        # Should have extracted entities
        assert len(all_entities) > 0

        # Check frequency calculation
        freq = extractor.get_entity_frequency(all_entities)
        assert len(freq) > 0

    def test_entity_extraction_with_custom_technical_terms(self):
        """Test extraction with custom technical terms."""
        custom_terms = {"tensorflow", "pytorch", "keras"}
        extractor = EntityExtractor(technical_terms=custom_terms)

        text = "TensorFlow and PyTorch are deep learning frameworks."
        entities = extractor.extract_entities(text)

        tech_entities = [e for e in entities if e.label == "TECHNICAL"]
        texts_lower = [e.text.lower() for e in tech_entities]

        assert "tensorflow" in texts_lower
        assert "pytorch" in texts_lower

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
        )


class TestCrossReferenceWorkflow:
    """Integration tests for cross-reference workflow."""

    def test_full_cross_reference_workflow(self):
        """Test complete cross-reference building workflow."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))

        docs = [
            self._make_doc("doc1", "Python is a great programming language."),
            self._make_doc("doc2", "Python and Docker work well together."),
            self._make_doc("doc3", "Java is different from Python."),
        ]

        graph.build_graph(docs)

        # Check statistics
        stats = graph.get_statistics()
        assert stats["total_documents"] == 3

        # Check cross-references
        refs = graph.find_cross_references("doc1")
        # doc1 and doc2 share "python"
        assert len(refs) > 0

    def test_cross_reference_injection_workflow(self):
        """Test injecting cross-references into documents."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))
        extractor = EntityExtractor()

        docs = [
            self._make_doc("doc1", "Python is essential."),
            self._make_doc("doc2", "Python and Docker are used together."),
        ]

        graph.build_graph(docs, extractor)
        title_map = {"doc2": "Docker Guide"}

        # Inject references into doc1
        doc1 = docs[0]
        result = graph.inject_cross_references(doc1, title_map)

        # Verify cross-reference was injected
        assert len(result.chunks) > 0
        content = result.chunks[0].content
        assert "CROSS-REF" in content
        assert "Docker Guide" in content

    def test_cross_reference_limit(self):
        """Test that max_refs_per_doc limit is respected."""
        config = CrossReferenceConfig(
            min_common_entities=1,
            max_refs_per_doc=2,
        )
        graph = EntityGraph(config)

        # Create many documents with overlapping entities
        docs = []
        for i in range(10):
            docs.append(self._make_doc(f"doc{i}", "Python and Docker are essential tools."))

        graph.build_graph(docs)

        # Check that no document has more than max_refs_per_doc references
        for doc_id in graph._doc_entities:
            refs = graph.find_cross_references(doc_id)
            assert len(refs) <= config.max_refs_per_doc

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


class TestGraphClear:
    """Integration tests for graph clearing."""

    def test_clear_graph(self):
        """Test that graph can be cleared."""
        graph = EntityGraph()

        docs = [
            self._make_doc("doc1", "Python"),
            self._make_doc("doc2", "Python"),
        ]

        graph.build_graph(docs)
        assert len(graph._doc_entities) == 2

        graph.clear()
        assert len(graph._doc_entities) == 0
        assert len(graph._cross_refs) == 0

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
        )
