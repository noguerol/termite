"""Document ingestion module."""

import hashlib
import logging
from pathlib import Path
from typing import ClassVar, Literal

from termite.models import ParsedDocument

logger = logging.getLogger(__name__)


class DocumentIngester:
    """Ingests documents from input directory."""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {
        ".pdf",
        ".docx",
        ".txt",
        ".html",
        ".htm",
        ".md",
        ".epub",
        ".mobi",
    }

    # Hard cap on how many times a single input directory may be expanded
    # through symlinked subdirectories (defence against symlink loops).
    MAX_SCAN_DEPTH = 32

    def __init__(
        self,
        input_dir: Path,
        mode: Literal["local", "cloud"] = "local",
        datalab_api_key: str | None = None,
        max_file_size_mb: float | None = 256.0,
    ):
        """Initialize the document ingester.

        Args:
            input_dir: Directory containing input documents.
            mode: Processing mode - "local" or "cloud".
            datalab_api_key: API key for Datalab cloud mode.
            max_file_size_mb: Skip files larger than this size (MB).
                ``None`` disables the limit.
        """
        self.input_dir = Path(input_dir)
        self.mode = mode
        self.datalab_api_key = datalab_api_key
        self.max_file_size_mb = max_file_size_mb

    def discover_documents(self, recursive: bool = True) -> list[Path]:
        """Discover all supported documents in the input directory.

        Args:
            recursive: If True, search subdirectories as well.

        Returns:
            List of paths to discovered documents (deduplicated).
        """
        if not self.input_dir.exists():
            return []

        seen_paths: set[str] = set()
        visited_dirs: set[str] = set()
        documents: list[Path] = []

        def is_acceptable(doc: Path) -> bool:
            """Apply size policy to a candidate document."""
            if self.max_file_size_mb is None:
                return True
            try:
                size_mb = doc.stat().st_size / (1024 * 1024)
            except OSError:  # unreadable file: skip it
                return False
            if size_mb > self.max_file_size_mb:
                logger.warning(
                    "Skipping oversized file %s (%.1f MB > %.1f MB limit)",
                    doc,
                    size_mb,
                    self.max_file_size_mb,
                )
                return False
            return True

        def scan_directory(directory: Path, depth: int) -> None:
            """Recursively scan directory for documents.

            Symlinks are never followed (neither files nor directories) to
            avoid symlink loops and ingestion of files outside the input
            tree. Visited directory identities prevent re-scanning through
            hardlinked or bind-mounted structures.
            """
            if depth > self.MAX_SCAN_DEPTH:
                logger.warning(
                    "Maximum scan depth reached at %s; stopping recursion",
                    directory,
                )
                return

            dir_key = str(directory.resolve())
            if dir_key in visited_dirs:
                return
            visited_dirs.add(dir_key)

            extensions = set(self.SUPPORTED_EXTENSIONS)
            extensions |= {ext.upper() for ext in self.SUPPORTED_EXTENSIONS}

            try:
                entries = sorted(directory.iterdir())
            except PermissionError:
                logger.warning("No read permission for %s; skipping", directory)
                return

            for entry in entries:
                try:
                    if entry.is_symlink():
                        logger.debug("Skipping symlink %s", entry)
                        continue
                    if entry.is_file():
                        if entry.suffix.lower() not in {e.lower() for e in extensions}:
                            continue
                        normalized = str(entry.resolve()).lower()
                        if normalized in seen_paths:
                            continue
                        if not is_acceptable(entry):
                            continue
                        seen_paths.add(normalized)
                        documents.append(entry)
                    elif recursive and entry.is_dir() and not entry.name.startswith("."):
                        scan_directory(entry, depth + 1)
                except OSError as exc:
                    logger.warning("Error scanning %s: %s", entry, exc)

        scan_directory(self.input_dir, 0)
        return sorted(documents)

    def generate_doc_id(self, file_path: Path) -> str:
        """Generate a unique document ID from file path.

        Args:
            file_path: Path to the document file.

        Returns:
            A unique document identifier.
        """
        return hashlib.sha256(str(file_path).encode()).hexdigest()[:12]

    def ingest(self, file_path: Path) -> ParsedDocument:
        """Ingest a single document.

        Args:
            file_path: Path to the document file.

        Returns:
            ParsedDocument with extracted content and metadata.

        Raises:
            ValueError: If file format is not supported.
        """
        from termite.pipeline.marker_parser import MarkerParser

        parser = MarkerParser(mode=self.mode, datalab_api_key=self.datalab_api_key)
        return parser.parse(file_path)

    def ingest_all(self) -> list[ParsedDocument]:
        """Ingest all discovered documents.

        Returns:
            List of parsed documents.
        """
        documents = self.discover_documents()
        return [self.ingest(doc) for doc in documents]
