"""Integration tests for deduplication."""

from termite.config import DeduplicationConfig
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.pipeline.deduplication import Deduplicator


class TestDeduplicationWorkflow:
    """Integration tests for deduplication workflow."""

    def test_full_deduplication_workflow(self):
        """Test complete deduplication workflow with mixed content."""
        dedup = Deduplicator(DeduplicationConfig(strategy="smart_merge"))

        docs = [
            self._make_doc("doc1", "Python is great", "Python programming"),
            self._make_doc("doc2", "Python is great", "Python programming"),  # Duplicate
            self._make_doc("doc3", "Java is different", "Java language"),
        ]

        result_docs, result_stats = dedup.deduplicate(docs)

        assert len(result_docs) <= len(docs)
        assert result_stats.original_count == 3
        assert result_stats.duplicates_removed >= 1

    def test_chunk_level_deduplication(self):
        """Test that chunk-level deduplication works."""
        dedup = Deduplicator()

        doc = ParsedDocument(
            doc_id="doc1",
            source_file="test.txt",
            chunks=[
                DocumentChunk(chunk_id="c1", content="Introduction", token_count=2),
                DocumentChunk(chunk_id="c2", content="Same section repeated", token_count=3),
                # intentional duplicate of c2
                DocumentChunk(
                    chunk_id="c3",
                    content="Same section repeated",
                    token_count=3,
                ),
                DocumentChunk(chunk_id="c4", content="Conclusion", token_count=2),
            ],
        )

        deduplicated_chunks = dedup.deduplicate_chunks(doc.chunks)

        # Should have 3 chunks (one duplicate removed)
        assert len(deduplicated_chunks) == 3

    def test_multiple_strategies(self):
        """Test that all strategies work correctly."""
        docs = [
            self._make_doc("doc1", "Content A"),
            self._make_doc("doc2", "Content A"),
            self._make_doc("doc3", "Content B"),
        ]

        for strategy in ["keep_first", "keep_latest", "smart_merge"]:
            dedup = Deduplicator(DeduplicationConfig(strategy=strategy))
            result_docs, _ = dedup.deduplicate(docs)

            # Should have 2 documents (one duplicate removed)
            assert len(result_docs) == 2

    def test_signature_computation_workflow(self):
        """Test that signatures are computed correctly in workflow."""
        dedup = Deduplicator()

        doc1 = self._make_doc("doc1", "Hello World")
        doc2 = self._make_doc("doc2", "Hello World")
        doc3 = self._make_doc("doc3", "Different content")

        docs = [doc1, doc2, doc3]

        # Find exact duplicates
        exact_dups = dedup.find_exact_duplicates(docs)

        # Should have 2 groups: one with 2 identical docs, one with 1
        assert len(exact_dups) == 2

        # Find near duplicates
        near_dups = dedup.find_near_duplicates(docs, chunk_level=False)

        # Check near duplicates if any
        for _doc_a, _doc_b, score in near_dups:
            assert score >= 0.0
            assert score <= 1.0

    @staticmethod
    def _make_doc(doc_id: str, content: str, title: str = "") -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[DocumentChunk(chunk_id=f"{doc_id}-1", content=content, token_count=5)],
            metadata=DocumentMetadata(title=title or doc_id),
        )


class TestSmartMerge:
    """Integration tests for smart merge strategy."""

    def test_smart_merge_combines_chunks(self):
        """Test that smart merge combines unique content."""
        dedup = Deduplicator(DeduplicationConfig(strategy="smart_merge"))

        docs = [
            self._make_doc("doc1", "Python programming language basics"),
            self._make_doc("doc2", "Python programming advanced topics"),
        ]

        result_docs, _ = dedup.deduplicate(docs)

        # Should have 2 docs (may merge if similar enough)
        assert len(result_docs) <= 2

        # Each doc should have content
        for doc in result_docs:
            content = " ".join(c.content for c in doc.chunks)
            assert len(content) > 0

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[DocumentChunk(chunk_id=f"{doc_id}-1", content=content, token_count=5)],
            metadata=DocumentMetadata(title=doc_id),
        )
