"""Deduplication module for Termite."""

import hashlib
import logging

from termite.config import DeduplicationConfig
from termite.models import DeduplicationResult, DocumentChunk, ParsedDocument
from termite.utils.normalization import (
    extract_ngrams,
    jaccard_similarity,
    normalize_for_hash,
)

logger = logging.getLogger(__name__)


class Deduplicator:
    """Deduplicates documents using hash and similarity algorithms.

    Exact duplicates are detected with SHA-256 signatures over normalized
    text; near-duplicates with Jaccard similarity over character n-grams.
    Signatures and n-grams are computed once per document and reused
    across all stages of a single ``deduplicate`` call.
    """

    def __init__(self, config: DeduplicationConfig | None = None):
        """Initialize the deduplicator.

        Args:
            config: Deduplication configuration. Uses defaults if None.
        """
        if config is None:
            config = DeduplicationConfig()

        self.threshold = config.similarity_threshold
        self.strategy = config.strategy

    def compute_signature(self, text: str) -> str:
        """Compute SHA-256 hash signature of normalized text.

        Args:
            text: Input text to hash.

        Returns:
            16-character hex signature.
        """
        normalized = normalize_for_hash(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def compute_chunk_signature(self, chunk: DocumentChunk) -> str:
        """Compute signature for a document chunk.

        Args:
            chunk: Document chunk to hash.

        Returns:
            16-character hex signature.
        """
        return self.compute_signature(chunk.content)

    @staticmethod
    def _combined_content(doc: ParsedDocument) -> str:
        """Concatenate all chunk contents of a document."""
        return "\n".join(c.content for c in doc.chunks)

    def find_exact_duplicates(self, documents: list[ParsedDocument]) -> dict[str, list[str]]:
        """Find documents with identical content.

        Args:
            documents: List of parsed documents.

        Returns:
            Dictionary mapping signatures to lists of document IDs.
        """
        signature_map: dict[str, list[str]] = {}

        for doc in documents:
            sig = self.compute_signature(self._combined_content(doc))
            signature_map.setdefault(sig, []).append(doc.doc_id)

        return signature_map

    def find_near_duplicates(
        self, documents: list[ParsedDocument], chunk_level: bool = False
    ) -> list[tuple[str, str, float]]:
        """Find near-duplicates using Jaccard similarity on n-grams.

        Args:
            documents: List of parsed documents.
            chunk_level: If True, compare at chunk level; otherwise at document level.

        Returns:
            List of tuples (doc_id_1, doc_id_2, similarity_score).
        """
        # Build n-gram sets for all documents
        doc_ngrams: dict[str, set[str]] = {}
        for doc in documents:
            if chunk_level:
                ngrams = set()
                for chunk in doc.chunks:
                    ngrams.update(extract_ngrams(chunk.content, n=3))
                doc_ngrams[doc.doc_id] = ngrams
            else:
                combined = self._combined_content(doc)
                doc_ngrams[doc.doc_id] = extract_ngrams(combined, n=3)

        return self._compare_pairs(doc_ngrams)

    def _compare_pairs(self, doc_ngrams: dict[str, set[str]]) -> list[tuple[str, str, float]]:
        """Compare all document pairs for similarity above threshold."""
        near_duplicates: list[tuple[str, str, float]] = []

        doc_ids = list(doc_ngrams.keys())
        for i, id_a in enumerate(doc_ids):
            set_a = doc_ngrams[id_a]
            for id_b in doc_ids[i + 1 :]:
                similarity = jaccard_similarity(set_a, doc_ngrams[id_b])
                if similarity >= self.threshold:
                    near_duplicates.append((id_a, id_b, similarity))

        return near_duplicates

    def deduplicate(
        self, documents: list[ParsedDocument]
    ) -> tuple[list[ParsedDocument], DeduplicationResult]:
        """Deduplicate a list of documents.

        Args:
            documents: List of documents to deduplicate.

        Returns:
            Tuple of (deduplicated documents, deduplication result).
        """
        original_count = len(documents)

        if original_count == 0:
            result = DeduplicationResult(
                original_count=0,
                deduplicated_count=0,
                duplicates_removed=0,
                compression_ratio=0.0,
            )
            return [], result

        # Compute each document signature once and reuse it everywhere.
        entries = [(doc, self.compute_signature(self._combined_content(doc))) for doc in documents]

        if self.strategy == "keep_first":
            deduplicated = []
            seen_signatures: set[str] = set()
            for doc, sig in entries:
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    deduplicated.append(doc)
        elif self.strategy == "keep_latest":
            seen_by_signature: dict[str, ParsedDocument] = {}
            for doc, sig in entries:
                seen_by_signature[sig] = doc
            deduplicated = list(seen_by_signature.values())
        elif self.strategy == "smart_merge":
            deduplicated = self._smart_merge(documents, entries)
        else:  # pragma: no cover - validated by pydantic
            deduplicated = documents

        duplicates_removed = original_count - len(deduplicated)
        compression_ratio = duplicates_removed / original_count

        logger.debug(
            "Deduplicated %d documents -> %d (%.1f%% removed)",
            original_count,
            len(deduplicated),
            compression_ratio * 100,
        )

        result = DeduplicationResult(
            original_count=original_count,
            deduplicated_count=len(deduplicated),
            duplicates_removed=duplicates_removed,
            compression_ratio=compression_ratio,
        )

        return deduplicated, result

    def _apply_strategy(self, doc_ids: list[str]) -> list[str]:
        """Apply deduplication strategy to a group of duplicate documents.

        Args:
            doc_ids: List of document IDs with identical content.

        Returns:
            List of document IDs to remove.
        """
        if self.strategy == "keep_first":
            return doc_ids[1:]  # Keep first, remove rest
        elif self.strategy == "keep_latest":
            return doc_ids[:-1]  # Keep last, remove rest
        elif self.strategy == "smart_merge":
            return doc_ids[1:]  # Simplified: keep first for now
        return []

    def _smart_merge(
        self,
        documents: list[ParsedDocument],
        entries: list[tuple[ParsedDocument, str]] | None = None,
    ) -> list[ParsedDocument]:
        """Smart merge documents with similar content.

        Exact duplicates are merged first via signature equality; near
        duplicates are merged when Jaccard similarity over character
        trigrams reaches the configured threshold. Signature and n-gram
        sets are computed once per document (previously recomputed per
        pair, quadratic in the worst case).

        Args:
            documents: List of documents to merge.
            entries: Optional precomputed (document, signature) pairs.

        Returns:
            List of merged documents.
        """
        if entries is None:
            entries = [
                (doc, self.compute_signature(self._combined_content(doc))) for doc in documents
            ]

        # Precompute n-gram sets once per document.
        ngrams_by_index = {
            index: extract_ngrams(self._combined_content(doc), n=3)
            for index, (doc, _sig) in enumerate(entries)
        }

        groups: list[list[ParsedDocument]] = []
        assigned: set[int] = set()

        for index, (doc, sig) in enumerate(entries):
            if index in assigned:
                continue

            group = [doc]
            assigned.add(index)
            set_a = ngrams_by_index[index]

            for other_index in range(index + 1, len(entries)):
                if other_index in assigned:
                    continue

                other_doc, other_sig = entries[other_index]

                if sig == other_sig:
                    # Exact duplicate
                    group.append(other_doc)
                    assigned.add(other_index)
                    continue

                # Check for near-duplicates against precomputed sets
                similarity = jaccard_similarity(set_a, ngrams_by_index[other_index])
                if similarity >= self.threshold:
                    group.append(other_doc)
                    assigned.add(other_index)

            groups.append(group)

        # Merge each group
        result: list[ParsedDocument] = []
        for group in groups:
            if len(group) == 1:
                result.append(group[0])
            else:
                merged = self._merge_documents(group)
                result.append(merged)

        return result

    def _merge_documents(self, documents: list[ParsedDocument]) -> ParsedDocument:
        """Merge multiple documents into one.

        Args:
            documents: List of documents to merge.

        Returns:
            Single merged document.
        """
        # Collect all unique chunks
        all_chunks: list[DocumentChunk] = []
        seen_sigs: set[str] = set()

        for doc in documents:
            for chunk in doc.chunks:
                sig = self.compute_chunk_signature(chunk)
                if sig not in seen_sigs:
                    seen_sigs.add(sig)
                    all_chunks.append(chunk)

        # Create merged document (keep metadata from first)
        merged = ParsedDocument(
            doc_id=documents[0].doc_id,
            source_file=documents[0].source_file,
            chunks=all_chunks,
            metadata=documents[0].metadata,
        )

        return merged

    def deduplicate_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Deduplicate chunks within a document.

        Args:
            chunks: List of chunks to deduplicate.

        Returns:
            Deduplicated list of chunks.
        """
        result: list[DocumentChunk] = []
        seen_sigs: set[str] = set()

        for chunk in chunks:
            sig = self.compute_chunk_signature(chunk)
            if sig not in seen_sigs:
                seen_sigs.add(sig)
                result.append(chunk)

        return result
