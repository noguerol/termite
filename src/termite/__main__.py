"""CLI entry point for Termite."""

import argparse
import logging
import sys
from pathlib import Path

from termite import __version__
from termite.pipeline.pipeline import run_pipeline


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="termite",
        description="Document Compressor & Structuring Tool - "
        "Convert raw documents to LLM-friendly formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  termite --input ./raw_docs --output ./output
  termite --input ./docs --output ./compressed --mode cloud
  termite --config custom_config.yaml -v
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"termite {__version__}",
    )

    parser.add_argument(
        "--input",
        type=Path,
        metavar="DIR",
        help="Input directory containing raw documents",
    )

    parser.add_argument(
        "--output",
        type=Path,
        metavar="DIR",
        help="Output directory for compressed documents",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file (default: config.yaml)",
    )

    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        help="Processing mode: local (marker-pdf) or cloud (Datalab API)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print statistics after processing",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Set the library log level (default: WARNING; --verbose implies INFO)",
    )

    return parser


def _configure_logging(log_level: str | None, verbose: bool) -> None:
    """Configure termite's logger without touching third-party loggers."""
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logger = logging.getLogger("termite")
    logger.setLevel(level)
    if not any(getattr(h, "_termite_handler", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
        handler._termite_handler = True
        logger.addHandler(handler)
    logger.propagate = False


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level, args.verbose)

    try:
        # Run the pipeline
        stats = run_pipeline(
            config_path=args.config,
            input_dir=args.input,
            output_dir=args.output,
            mode=args.mode,
            verbose=args.verbose,
        )

        # Print statistics if requested
        if args.stats:
            print("\n=== Pipeline Statistics ===")
            print(f"Documents discovered: {stats['documents_discovered']}")
            print(f"Documents parsed:     {stats['documents_parsed']}")
            print(f"Documents after dedup:{stats['documents_deduplicated']}")
            print(f"Chunks before:        {stats['chunks_before']}")
            print(f"Chunks after:         {stats['chunks_after']}")
            print(f"Original tokens:      {stats['original_tokens']}")
            print(f"Compressed tokens:   {stats['compressed_tokens']}")
            print(f"Compression ratio:    {stats['compression_ratio']:.1%}")
            print(f"Cross-references:     {stats['cross_references_created']}")
            print(f"Execution time:      {stats['execution_time_seconds']:.2f}s")

        if stats["documents_parsed"] == 0:
            print("No documents found to process.", file=sys.stderr)
            return 1

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as e:
        if args.verbose:
            raise
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
