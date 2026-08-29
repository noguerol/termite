"""Complete Termite pipeline orchestration."""

import logging
import time
from pathlib import Path
from typing import TypedDict

from termite.config import TermiteConfig, load_config
from termite.models import ParsedDocument
from termite.pipeline.compression import LexicalCompressor
from termite.pipeline.deduplication import Deduplicator
from termite.pipeline.document_ingester import DocumentIngester
from termite.pipeline.entity_extractor import EntityExtractor
from termite.pipeline.entity_graph import EntityGraph
from termite.pipeline.marker_parser import MarkerParser
from termite.pipeline.output_generator import OutputGenerator

logger = logging.getLogger(__name__)


class PipelineStatistics(TypedDict):
    """Pipeline execution statistics."""

    documents_discovered: int
    documents_parsed: int
    documents_deduplicated: int
    chunks_before: int
    chunks_after: int
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    cross_references_created: int
    execution_time_seconds: float


class TermitePipeline:
    """Complete Termite document processing pipeline."""

    def __init__(self, config: TermiteConfig | None = None):
        """Initialize the pipeline.

        Args:
            config: Termite configuration.
        """
        if config is None:
            config = TermiteConfig()

        self.config = config
        self._setup_components()

    def _setup_components(self) -> None:
        """Set up all pipeline components."""
        # Document ingestion
        self.ingester = DocumentIngester(
            input_dir=self.config.pipeline.input_dir,
            mode=self.config.pipeline.mode,
            datalab_api_key=None,  # Will use env var
            max_file_size_mb=self.config.pipeline.max_file_size_mb,
        )

        # Document parsing
        self.parser = MarkerParser(mode=self.config.pipeline.mode)

        # Deduplication
        self.deduplicator = Deduplicator(self.config.deduplication)

        # Entity extraction
        self.extractor = EntityExtractor()

        # Entity graph
        self.graph = EntityGraph(self.config.cross_reference)

        # Compression
        self.compressor = LexicalCompressor(self.config.compression)

        # Output generation
        self.generator = OutputGenerator(self.config)

    def run(self, verbose: bool = False) -> PipelineStatistics:
        """Run the complete pipeline.

        Args:
            verbose: If True, print progress information.

        Returns:
            Pipeline execution statistics.
        """
        start_time = time.time()

        if verbose:
            print("Termite Pipeline Starting...")

        # Step 1: Discover documents
        if verbose:
            print(f"Discovering documents in {self.config.pipeline.input_dir}...")

        doc_paths = self.ingester.discover_documents()
        documents_discovered = len(doc_paths)

        if verbose:
            print(f"Found {documents_discovered} documents")

        if documents_discovered == 0:
            return self._empty_stats(start_time)

        # Step 2: Parse documents
        if verbose:
            print("Parsing documents...")

        parsed_docs: list[ParsedDocument] = []
        for i, path in enumerate(doc_paths):
            if verbose:
                print(f"  Parsing [{i+1}/{documents_discovered}]: {path.name}")

            try:
                doc = self.parser.parse(path)
                parsed_docs.append(doc)
            except Exception as e:  # noqa: BLE001 - keep processing remaining documents
                logger.warning("Failed to parse %s: %s", path, e)
                if verbose:
                    print(f"  Warning: Failed to parse {path}: {e}")

        if verbose:
            print(f"Parsed {len(parsed_docs)} documents")

        # Step 3: Deduplicate
        if verbose:
            print("Deduplicating documents...")

        chunks_before = sum(len(doc.chunks) for doc in parsed_docs)
        # Baseline token count measured BEFORE deduplication removes
        # content, so pipeline statistics reflect the true input size.
        tokens_before_dedup = sum(doc.total_tokens() for doc in parsed_docs)
        deduplicated_docs, dedup_result = self.deduplicator.deduplicate(parsed_docs)
        chunks_after = sum(len(doc.chunks) for doc in deduplicated_docs)

        if verbose:
            print(f"Removed {dedup_result.duplicates_removed} duplicates")

        # Step 4: Build entity graph and inject cross-references
        if self.config.cross_reference.enabled:
            if verbose:
                print("Building entity graph...")

            self.graph.build_graph(deduplicated_docs, self.extractor)

            title_map = {doc.doc_id: doc.metadata.title or doc.doc_id for doc in deduplicated_docs}

            deduplicated_docs = [
                self.graph.inject_cross_references(doc, title_map) for doc in deduplicated_docs
            ]

            if verbose:
                stats = self.graph.get_statistics()
                print(f"Created {stats['total_cross_references']} cross-references")

        # Step 5: Compress documents
        if verbose:
            print("Compressing documents...")

        compressed_docs = [self.compressor.compress_document(doc) for doc in deduplicated_docs]

        # Step 6: Generate output
        if verbose:
            print("Generating output...")

        compressed_docs, output_metadata = self.generator.generate_output(
            compressed_docs,
            inject_cross_references=False,  # Already done above
            deduplicate_input=False,  # Already deduplicated above
        )

        self.generator.write_output(compressed_docs, output_metadata)

        if verbose:
            print(f"Output written to {self.config.pipeline.output_dir}")

        execution_time = time.time() - start_time

        # Cross-references were built by the pipeline graph above; use
        # that graph's statistics (the generator's own graph is empty).
        if self.config.cross_reference.enabled:
            cross_references_created = self.graph.get_statistics()["total_cross_references"]
        else:
            cross_references_created = 0

        stats: PipelineStatistics = {
            "documents_discovered": documents_discovered,
            "documents_parsed": len(parsed_docs),
            "documents_deduplicated": len(compressed_docs),
            "chunks_before": chunks_before,
            "chunks_after": chunks_after,
            "original_tokens": tokens_before_dedup,
            "compressed_tokens": output_metadata["compressed_tokens"],
            "compression_ratio": output_metadata["compression_ratio"],
            "cross_references_created": cross_references_created,
            "execution_time_seconds": execution_time,
        }

        if verbose:
            print("\nPipeline Complete!")
            print(f"  Documents: {stats['documents_parsed']} -> {stats['documents_deduplicated']}")
            print(f"  Chunks: {stats['chunks_before']} -> {stats['chunks_after']}")
            print(f"  Tokens: {stats['original_tokens']} -> {stats['compressed_tokens']}")
            print(f"  Compression: {stats['compression_ratio']:.1%}")
            print(f"  Time: {stats['execution_time_seconds']:.2f}s")

        return stats

    def _empty_stats(self, start_time: float) -> PipelineStatistics:
        """Return empty statistics for no documents."""
        return {
            "documents_discovered": 0,
            "documents_parsed": 0,
            "documents_deduplicated": 0,
            "chunks_before": 0,
            "chunks_after": 0,
            "original_tokens": 0,
            "compressed_tokens": 0,
            "compression_ratio": 0.0,
            "cross_references_created": 0,
            "execution_time_seconds": time.time() - start_time,
        }


def run_pipeline(
    config_path: str | Path = "config.yaml",
    input_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    mode: str | None = None,
    verbose: bool = False,
) -> PipelineStatistics:
    """Run the Termite pipeline with the given configuration.

    Args:
        config_path: Path to configuration file.
        input_dir: Override input directory.
        output_dir: Override output directory.
        mode: Override processing mode.
        verbose: If True, print progress information.

    Returns:
        Pipeline execution statistics.
    """
    config = load_config(config_path)

    if input_dir:
        config.pipeline.input_dir = Path(input_dir)
    if output_dir:
        config.pipeline.output_dir = Path(output_dir)
    if mode:
        config.pipeline.mode = mode

    pipeline = TermitePipeline(config)
    return pipeline.run(verbose=verbose)
