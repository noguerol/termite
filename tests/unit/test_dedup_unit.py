"""Unit tests for deduplication module."""

from termite.config import DeduplicationConfig
from termite.models import DocumentChunk, DocumentMetadata, ParsedDocument
from termite.pipeline.deduplication import Deduplicator


class TestComputeSignature:
    """Tests for compute_signature method."""

    def test_signature_deterministic(self):
        """Same text produces same signature."""
        dedup = Deduplicator()
        sig1 = dedup.compute_signature("Hello World")
        sig2 = dedup.compute_signature("Hello World")
        assert sig1 == sig2

    def test_signature_normalizes_text(self):
        """Different formatting produces same signature."""
        dedup = Deduplicator()
        sig1 = dedup.compute_signature("Hello, World!")
        sig2 = dedup.compute_signature("hello world")
        assert sig1 == sig2

    def test_signature_length(self):
        """Signature is 16 characters."""
        dedup = Deduplicator()
        sig = dedup.compute_signature("Test text")
        assert len(sig) == 16

    def test_different_texts_different_signatures(self):
        """Different texts should (usually) produce different signatures."""
        dedup = Deduplicator()
        sig1 = dedup.compute_signature("Hello World")
        sig2 = dedup.compute_signature("Goodbye World")
        # These should be different
        assert sig1 != sig2


class TestFindExactDuplicates:
    """Tests for find_exact_duplicates method."""

    def test_no_duplicates(self):
        """No duplicates returns empty groups."""
        dedup = Deduplicator()
        docs = [
            self._make_doc("doc1", "Content A"),
            self._make_doc("doc2", "Content B"),
        ]

        result = dedup.find_exact_duplicates(docs)

        assert len(result) == 2

    def test_identical_duplicates(self):
        """Identical content returns group with multiple docs."""
        dedup = Deduplicator()
        docs = [
            self._make_doc("doc1", "Same content"),
            self._make_doc("doc2", "Same content"),
        ]

        result = dedup.find_exact_duplicates(docs)

        # Should have one group with 2 documents
        assert len(result) == 1
        for _sig, doc_ids in result.items():
            assert len(doc_ids) == 2
            assert "doc1" in doc_ids
            assert "doc2" in doc_ids

    def test_different_content_no_duplicates(self):
        """Different content doesn't create duplicate groups."""
        dedup = Deduplicator()
        docs = [
            self._make_doc("doc1", "Content A"),
            self._make_doc("doc2", "Content B"),
        ]

        result = dedup.find_exact_duplicates(docs)

        assert len(result) == 2

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[DocumentChunk(chunk_id=f"{doc_id}-1", content=content, token_count=5)],
            metadata=DocumentMetadata(title=doc_id),
        )


class TestFindNearDuplicates:
    """Tests for find_near_duplicates method."""

    def test_no_near_duplicates(self):
        """Completely different content returns no near duplicates."""
        dedup = Deduplicator(DeduplicationConfig(similarity_threshold=0.85))
        docs = [
            self._make_doc("doc1", "Apple banana cherry"),
            self._make_doc("doc2", "Dog elephant frog"),
        ]

        result = dedup.find_near_duplicates(docs)

        assert len(result) == 0

    def test_highly_similar(self):
        """Very similar content returns near duplicates."""
        dedup = Deduplicator(DeduplicationConfig(similarity_threshold=0.5))
        docs = [
            self._make_doc("doc1", "Python is a great programming language"),
            self._make_doc("doc2", "Python is a great programming language and tool"),
        ]

        result = dedup.find_near_duplicates(docs)

        assert len(result) == 1
        assert result[0][2] > 0.5

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[DocumentChunk(chunk_id=f"{doc_id}-1", content=content, token_count=5)],
            metadata=DocumentMetadata(title=doc_id),
        )


class TestDeduplicate:
    """Tests for deduplicate method."""

    def test_no_duplicates_unchanged(self):
        """Documents without duplicates are unchanged."""
        dedup = Deduplicator(DeduplicationConfig(strategy="keep_first"))
        docs = [
            self._make_doc("doc1", "Content A"),
            self._make_doc("doc2", "Content B"),
        ]

        result_docs, result_stats = dedup.deduplicate(docs)

        assert len(result_docs) == 2
        assert result_stats.original_count == 2
        assert result_stats.duplicates_removed == 0

    def test_exact_duplicates_removed(self):
        """Exact duplicates are removed based on strategy."""
        dedup = Deduplicator(DeduplicationConfig(strategy="keep_first"))
        docs = [
            self._make_doc("doc1", "Same content"),
            self._make_doc("doc2", "Same content"),
            self._make_doc("doc3", "Same content"),
        ]

        result_docs, result_stats = dedup.deduplicate(docs)

        assert len(result_docs) == 1
        assert result_stats.duplicates_removed == 2

    def test_keep_latest_strategy(self):
        """Keep latest strategy keeps last document."""
        dedup = Deduplicator(DeduplicationConfig(strategy="keep_latest"))
        docs = [
            self._make_doc("doc1", "Same content"),
            self._make_doc("doc2", "Same content"),
        ]

        result_docs, _ = dedup.deduplicate(docs)

        assert len(result_docs) == 1
        assert result_docs[0].doc_id == "doc2"

    def test_compression_ratio_calculated(self):
        """Compression ratio is calculated correctly."""
        dedup = Deduplicator(DeduplicationConfig(strategy="keep_first"))
        docs = [
            self._make_doc("doc1", "Same content"),
            self._make_doc("doc2", "Same content"),
            self._make_doc("doc3", "Different content"),
        ]

        _, result_stats = dedup.deduplicate(docs)

        # 1 duplicate removed out of 3 = 1/3 ≈ 0.333
        assert abs(result_stats.compression_ratio - 0.333) < 0.01

    @staticmethod
    def _make_doc(doc_id: str, content: str) -> ParsedDocument:
        """Helper to create test documents."""
        return ParsedDocument(
            doc_id=doc_id,
            source_file=f"{doc_id}.txt",
            chunks=[DocumentChunk(chunk_id=f"{doc_id}-1", content=content, token_count=5)],
            metadata=DocumentMetadata(title=doc_id),
        )


class TestDeduplicateChunks:
    """Tests for deduplicate_chunks method."""

    def test_no_duplicate_chunks(self):
        """Chunks without duplicates are unchanged."""
        dedup = Deduplicator()
        chunks = [
            DocumentChunk(chunk_id="c1", content="Content A", token_count=2),
            DocumentChunk(chunk_id="c2", content="Content B", token_count=3),
        ]

        result = dedup.deduplicate_chunks(chunks)

        assert len(result) == 2

    def test_identical_chunks_removed(self):
        """Identical chunks are deduplicated."""
        dedup = Deduplicator()
        chunks = [
            DocumentChunk(chunk_id="c1", content="Same content", token_count=2),
            DocumentChunk(chunk_id="c2", content="Same content", token_count=2),
        ]

        result = dedup.deduplicate_chunks(chunks)

        assert len(result) == 1
