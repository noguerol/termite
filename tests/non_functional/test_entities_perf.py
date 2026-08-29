"""Non-functional tests for entity extraction and cross-referencing."""

import time

import pytest

from termite.config import CrossReferenceConfig
from termite.models import DocumentChunk, ParsedDocument
from termite.pipeline.entity_extractor import EntityExtractor
from termite.pipeline.entity_graph import EntityGraph


class TestEntityExtractionPerformance:
    """Performance tests for entity extraction."""

    @pytest.mark.timeout(60)
    def test_extract_many_documents(self):
        """50 documents should extract entities in < 60s."""
        extractor = EntityExtractor()

        docs = []
        for i in range(50):
            docs.append(
                ParsedDocument(
                    doc_id=f"doc{i}",
                    source_file=f"doc{i}.txt",
                    chunks=[
                        DocumentChunk(
                            chunk_id=f"doc{i}-1",
                            content=f"Document {i} about Python and Docker "
                            f"with some content for testing entity extraction. "
                            f"Technical terms include Kubernetes, TensorFlow, "
                            f"and machine learning concepts.",
                            token_count=20,
                        )
                    ],
                )
            )

        start = time.time()
        all_entities = []
        for doc in docs:
            entities = extractor.extract_from_document(doc)
            all_entities.extend(entities)
        duration = time.time() - start

        assert duration < 60
        assert len(all_entities) > 0

    @pytest.mark.timeout(10)
    def test_extract_entities_single_call(self):
        """Single extraction call should be fast."""
        extractor = EntityExtractor()
        text = "Python is great. " * 100

        start = time.time()
        entities = extractor.extract_entities(text)
        duration = time.time() - start

        assert duration < 10
        assert len(entities) > 0


class TestCrossReferencePerformance:
    """Performance tests for cross-reference building."""

    @pytest.mark.timeout(60)
    def test_build_graph_many_documents(self):
        """30 documents should build graph in < 60s."""
        graph = EntityGraph(CrossReferenceConfig(min_common_entities=1))

        docs = []
        for i in range(30):
            docs.append(
                ParsedDocument(
                    doc_id=f"doc{i}",
                    source_file=f"doc{i}.txt",
                    chunks=[
                        DocumentChunk(
                            chunk_id=f"doc{i}-1",
                            content=f"Document {i} with Python and Docker "
                            f"content for testing cross-references.",
                            token_count=20,
                        )
                    ],
                )
            )

        start = time.time()
        graph.build_graph(docs)
        duration = time.time() - start

        assert duration < 60
        assert graph.get_statistics()["total_documents"] == 30

    @pytest.mark.timeout(30)
    def test_find_cross_references_performance(self):
        """Finding references should be fast."""
        graph = EntityGraph(CrossReferenceConfig())

        docs = [
            ParsedDocument(
                doc_id=f"doc{i}",
                source_file=f"doc{i}.txt",
                chunks=[
                    DocumentChunk(
                        chunk_id=f"doc{i}-1",
                        content="Python and Docker content.",
                        token_count=10,
                    )
                ],
            )
            for i in range(100)
        ]

        graph.build_graph(docs)

        start = time.time()
        for doc_id in list(graph._doc_entities.keys())[:10]:
            graph.find_cross_references(doc_id)
        duration = time.time() - start

        assert duration < 30


class TestReliability:
    """Reliability tests."""

    def test_empty_text_handling(self):
        """System handles empty text gracefully."""
        extractor = EntityExtractor()
        entities = extractor.extract_entities("")
        assert isinstance(entities, list)

    def test_empty_document_handling(self):
        """System handles empty document gracefully."""
        graph = EntityGraph()
        doc = ParsedDocument(
            doc_id="empty",
            source_file="empty.txt",
            chunks=[],
        )
        graph.build_graph([doc])

        stats = graph.get_statistics()
        assert stats["total_documents"] == 1
        assert stats["total_cross_references"] == 0

    def test_special_characters_in_text(self):
        """System handles special characters."""
        extractor = EntityExtractor()
        text = "Python 3.9+ @#$%^&*() _special_chars_"
        entities = extractor.extract_entities(text)
        assert isinstance(entities, list)
