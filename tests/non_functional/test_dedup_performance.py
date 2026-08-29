"""Non-functional tests for deduplication."""

import time

import pytest

from termite.config import DeduplicationConfig
from termite.models import DocumentChunk, ParsedDocument
from termite.pipeline.deduplication import Deduplicator


class TestDeduplicationPerformance:
    """Performance tests for deduplication."""

    @pytest.mark.timeout(30)
    def test_deduplicate_many_documents(self):
        """100 documents should deduplicate in < 30s."""
        dedup = Deduplicator(DeduplicationConfig())

        # Create 100 documents (mix of unique and duplicates)
        docs = []
        for i in range(100):
            content = "Duplicate content" if i % 3 == 0 else f"Unique content {i}"
            docs.append(
                ParsedDocument(
                    doc_id=f"doc{i}",
                    source_file=f"doc{i}.txt",
                    chunks=[
                        DocumentChunk(
                            chunk_id=f"doc{i}-1",
                            content=content,
                            token_count=10,
                        )
                    ],
                )
            )

        start = time.time()
        result_docs, _ = dedup.deduplicate(docs)
        duration = time.time() - start

        assert duration < 30, f"Deduplication took {duration:.2f}s (expected < 30s)"
        assert len(result_docs) < len(docs)

    @pytest.mark.timeout(60)
    def test_signature_computation_performance(self):
        """1000 signature computations should complete quickly."""
        dedup = Deduplicator()

        texts = [f"Document content number {i}" for i in range(1000)]

        start = time.time()
        signatures = [dedup.compute_signature(text) for text in texts]
        duration = time.time() - start

        assert duration < 5, f"Signature computation took {duration:.2f}s (expected < 5s)"
        assert len(signatures) == 1000

    @pytest.mark.timeout(30)
    def test_near_duplicate_performance(self):
        """Near duplicate detection on 50 documents should be < 30s."""
        dedup = Deduplicator(DeduplicationConfig(similarity_threshold=0.8))

        docs = []
        for i in range(50):
            docs.append(
                ParsedDocument(
                    doc_id=f"doc{i}",
                    source_file=f"doc{i}.txt",
                    chunks=[
                        DocumentChunk(
                            chunk_id=f"doc{i}-1",
                            content=f"Content for document {i} with some text",
                            token_count=20,
                        )
                    ],
                )
            )

        start = time.time()
        near_dups = dedup.find_near_duplicates(docs)
        duration = time.time() - start

        assert isinstance(near_dups, list)
        assert duration < 30, f"Near duplicate detection took {duration:.2f}s"


class TestDeduplicationReliability:
    """Reliability tests for deduplication."""

    def test_empty_document_list(self):
        """System handles empty document list."""
        dedup = Deduplicator()
        result_docs, result_stats = dedup.deduplicate([])

        assert result_docs == []
        assert result_stats.original_count == 0
        assert result_stats.duplicates_removed == 0

    def test_single_document(self):
        """Single document is returned unchanged."""
        dedup = Deduplicator()
        doc = ParsedDocument(
            doc_id="doc1",
            source_file="doc1.txt",
            chunks=[DocumentChunk(chunk_id="c1", content="Content", token_count=2)],
        )

        result_docs, result_stats = dedup.deduplicate([doc])

        assert len(result_docs) == 1
        assert result_stats.duplicates_removed == 0

    def test_all_identical_documents(self):
        """All identical documents are deduplicated to one."""
        dedup = Deduplicator(DeduplicationConfig(strategy="keep_first"))

        docs = [
            ParsedDocument(
                doc_id=f"doc{i}",
                source_file=f"doc{i}.txt",
                chunks=[DocumentChunk(chunk_id=f"doc{i}-1", content="Same", token_count=1)],
            )
            for i in range(10)
        ]

        result_docs, result_stats = dedup.deduplicate(docs)

        assert len(result_docs) == 1
        assert result_stats.duplicates_removed == 9
