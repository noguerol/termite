"""Output generation module for Termite."""

from __future__ import annotations

import contextlib
import os
import re
from pathlib import Path
from typing import TypedDict

from termite.config import TermiteConfig
from termite.models import (
    DeduplicationResult,
    ParsedDocument,
)
from termite.pipeline.compression import LexicalCompressor
from termite.pipeline.deduplication import Deduplicator
from termite.pipeline.entity_graph import EntityGraph
from termite.utils.metrics import calculate_compression_ratio


class OutputMetadata(TypedDict):
    """Metadata for the output index."""

    total_documents: int
    total_chunks: int
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    deduplication_ratio: float
    cross_references_count: int


class OutputGenerator:
    """Generates final output files."""

    def __init__(self, config: TermiteConfig | None = None):
        """Initialize the output generator.

        Args:
            config: Termite configuration.
        """
        if config is None:
            config = TermiteConfig()

        self.config = config
        self.output_dir = config.pipeline.output_dir
        self.compressor = LexicalCompressor(config.compression)
        self.deduplicator = Deduplicator(config.deduplication)
        self.entity_graph = EntityGraph(config.cross_reference)

    def generate_output(
        self,
        documents: list[ParsedDocument],
        inject_cross_references: bool = True,
        deduplicate_input: bool = True,
    ) -> tuple[list[ParsedDocument], OutputMetadata]:
        """Generate compressed output from documents.

        Args:
            documents: List of parsed documents.
            inject_cross_references: If True, inject cross-references.
            deduplicate_input: If False, the input is assumed to be
                already deduplicated (e.g. by ``TermitePipeline``) and the
                internal deduplication step is skipped, avoiding a second
                quadratic dedup pass.

        Returns:
            Tuple of (processed documents, output metadata).
        """
        # Step 1: Deduplicate (unless the caller already did it)
        if deduplicate_input:
            dedup_docs, dedup_result = self.deduplicator.deduplicate(documents)
        else:
            dedup_docs = list(documents)
            dedup_result = DeduplicationResult(
                original_count=len(documents),
                deduplicated_count=len(documents),
                duplicates_removed=0,
                compression_ratio=0.0,
            )

        # Step 2: Build entity graph and inject cross-references
        if inject_cross_references and self.config.cross_reference.enabled:
            self.entity_graph.build_graph(dedup_docs)

            # Build title map
            title_map = {doc.doc_id: doc.metadata.title or doc.doc_id for doc in dedup_docs}

            # Inject cross-references
            dedup_docs = [
                self.entity_graph.inject_cross_references(doc, title_map) for doc in dedup_docs
            ]

        # Step 3: Compress documents
        compressed_docs = [self.compressor.compress_document(doc) for doc in dedup_docs]

        # Step 4: Calculate metadata
        original_tokens = sum(doc.total_tokens() for doc in documents)
        compressed_tokens = sum(doc.total_tokens() for doc in compressed_docs)

        metadata: OutputMetadata = {
            "total_documents": len(compressed_docs),
            "total_chunks": sum(len(doc.chunks) for doc in compressed_docs),
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": calculate_compression_ratio(original_tokens, compressed_tokens),
            "deduplication_ratio": dedup_result.compression_ratio,
            "cross_references_count": sum(
                len(self.entity_graph.find_cross_references(doc.doc_id)) for doc in compressed_docs
            ),
        }

        return compressed_docs, metadata

    def write_output(
        self,
        documents: list[ParsedDocument],
        metadata: OutputMetadata,
        unified_output: bool = True,
    ) -> None:
        """Write output files to disk.

        Args:
            documents: Processed documents.
            metadata: Output metadata.
            unified_output: If True, create single unified file.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if unified_output:
            # Write single unified file
            output_path = self.output_dir / "compressed_docs.md"
            self._atomic_write(
                output_path,
                "".join(self._unified_document_parts(documents)),
            )

            # Write index with metadata
            index_path = self.output_dir / "compressed_index.md"
            self._write_index(index_path, documents, metadata)
        else:
            # Write individual files
            for doc in documents:
                safe_name = self._sanitize_filename(doc.doc_id)
                output_path = self.output_dir / f"{safe_name}.md"
                parts = [f"# {doc.metadata.title or doc.doc_id}\n\n"]
                parts.extend(f"{chunk.content}\n\n" for chunk in doc.chunks)
                self._atomic_write(output_path, "".join(parts))

    @staticmethod
    def _unified_document_parts(documents):
        """Yield markdown segments for the unified output file."""
        for doc in documents:
            yield f"# {doc.metadata.title or doc.doc_id}\n\n"
            for chunk in doc.chunks:
                yield f"{chunk.content}\n\n"
            yield "\n---\n\n"

    def _write_index(self, index_path: Path, documents, metadata) -> None:
        """Write the output index atomically."""
        lines = [
            "# Termite Compressed Documents Index\n\n",
            "## Statistics\n\n",
            f"- Total Documents: {metadata['total_documents']}\n",
            f"- Total Chunks: {metadata['total_chunks']}\n",
            f"- Original Tokens: {metadata['original_tokens']}\n",
            f"- Compressed Tokens: {metadata['compressed_tokens']}\n",
            f"- Compression Ratio: {metadata['compression_ratio']:.1%}\n",
            f"- Deduplication Reduction: {metadata['deduplication_ratio']:.1%}\n",
            f"- Cross-References: {metadata['cross_references_count']}\n",
            "\n## Documents\n\n",
        ]
        for doc in documents:
            title = doc.metadata.title or doc.doc_id
            tokens = doc.total_tokens()
            lines.append(f"- [{title}](compressed_docs.md#{doc.doc_id}) " f"({tokens} tokens)\n")
        self._atomic_write(index_path, "".join(lines))

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write content atomically (temp file + rename).

        Prevents consumers from observing partially written output files
        and avoids leaving truncated files behind on failure.
        """
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            # Best-effort cleanup of the partial temp file.
            with contextlib.suppress(OSError):
                tmp_path.unlink(missing_ok=True)
            raise

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            name: Original name.

        Returns:
            Sanitized filename (never empty, never a hidden or traversal
            name).
        """
        safe = re.sub(r"[^\w\-]", "_", name)[:50]
        if not safe or safe.strip("_") == "":
            return "document"
        return safe
