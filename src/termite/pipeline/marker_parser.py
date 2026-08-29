"""Marker parser integration for Termite."""

from __future__ import annotations

import hashlib
import logging
import os
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any, Literal

from termite.models import (
    DocumentChunk,
    DocumentMetadata,
    ParsedDocument,
)
from termite.utils.metrics import estimate_tokens
from termite.utils.normalization import normalize_whitespace

logger = logging.getLogger(__name__)

#: Guards against decompression-bomb style archives.
MAX_EPUB_MEMBER_BYTES = 64 * 1024 * 1024  # 64 MB per archive member
MAX_EPUB_TOTAL_BYTES = 256 * 1024 * 1024  # 256 MB extracted per archive


def _element_tree_module():
    """Return the XML ElementTree module to use for untrusted input.

    Prefers ``defusedxml`` (protects against entity-expansion, external
    entity and other XML attacks); falls back to the standard library
    when defusedxml is not installed, in which case the EPUB size
    enforced limits remain as the compensating control.
    """
    try:
        import defusedxml.ElementTree as _ET

        return _ET
    except ImportError:  # pragma: no cover - defusedxml ships in base deps
        from xml.etree import ElementTree as _ET

        return _ET


class DocumentParseError(Exception):
    """Raised when a document cannot be parsed."""


def get_device() -> str:
    """Detect the best available device for PyTorch.

    Priority: CUDA (NVIDIA) > ROCm (AMD) > CPU

    Returns:
        Device string: 'cuda', 'cuda:0', 'hip:0', or 'cpu'
    """
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"

        # torch.version.hip is set when PyTorch is compiled with ROCm
        # support; ROCm exposes its GPUs through the CUDA-compatible API.
        if getattr(torch.version, "hip", None):
            return "cuda" if torch.cuda.device_count() > 0 else "cpu"

        return "cpu"

    except ImportError:
        return "cpu"


def configure_marker_for_gpu() -> None:
    """Configure environment variables for GPU acceleration.

    Only called when GPU usage is actually enabled. Existing environment
    variables are preserved (they are only defaulted, never overwritten),
    so user-supplied device configuration always wins.
    """
    if os.environ.get("CUDA_VISIBLE_DEVICES"):
        # The user already configured device visibility; leave it alone.
        return

    try:
        import torch
    except ImportError:
        return

    if get_device() == "cpu":
        return

    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:512")

    if getattr(torch.version, "hip", None):
        # Additional defaults for AMD ROCm stacks.
        os.environ.setdefault("GPU_DEVICE_ORDINAL", "0")


class MarkerParser:
    """Wrapper for marker library parsing.

    Parsing models are loaded once per process (lazily) and reused across
    documents; loading marker models per document would dominate runtime
    for small documents.
    """

    #: Process-wide model cache (marker models are large and expensive to
    # load; instantiating several parsers should share them).
    _model_cache: dict[str, Any] | None = None

    def __init__(
        self,
        mode: Literal["local", "cloud"] = "local",
        datalab_api_key: str | None = None,
        force_cpu: bool = False,
    ):
        """Initialize the marker parser.

        Args:
            mode: "local" for marker-pdf, "cloud" for Datalab API.
            datalab_api_key: API key for Datalab cloud mode. When not
                given, the ``DATALAB_API_KEY`` environment variable is
                used. Never hardcode credentials.
            force_cpu: If True, force CPU even if GPU is available.
        """
        self.mode = mode
        self.datalab_api_key = datalab_api_key or os.environ.get("DATALAB_API_KEY")
        self.force_cpu = force_cpu

        if force_cpu:
            self.device = "cpu"
        else:
            self.device = get_device()
            configure_marker_for_gpu()

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document using marker.

        Args:
            file_path: Path to the document file.

        Returns:
            ParsedDocument with extracted content and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            DocumentParseError: If the document cannot be parsed.
        """
        file_path = Path(file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Document not found: {file_path}")

        doc_id = self._generate_doc_id(file_path)

        if self.mode == "cloud":
            return self._parse_cloud(file_path, doc_id)
        return self._parse_local(file_path, doc_id)

    def _parse_local(self, file_path: Path, doc_id: str) -> ParsedDocument:
        """Parse document using local marker-pdf.

        Args:
            file_path: Path to the document file.
            doc_id: Unique document identifier.

        Returns:
            ParsedDocument instance.
        """
        try:
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models
        except ImportError:
            # marker not installed: fall back to lightweight extractors.
            return self._parse_fallback(file_path, doc_id)

        # Load models once per process, then reuse them.
        if MarkerParser._model_cache is None:
            MarkerParser._model_cache = load_all_models()
        models = MarkerParser._model_cache

        # Move models to the selected device (idempotent).
        if self.device != "cpu":
            for model in models.values():
                if hasattr(model, "to"):
                    model.to(self.device)

        try:
            rendering = convert_single_pdf(str(file_path), models)
        except Exception as exc:  # marker internals raise heterogeneous errors
            raise DocumentParseError(f"marker failed to parse {file_path.name}: {exc}") from exc

        markdown = rendering.markdown
        metadata_json = rendering.metadata

        chunks = self.extract_chunks(markdown)
        metadata = self.extract_metadata(metadata_json, str(file_path))

        return ParsedDocument(
            doc_id=doc_id,
            source_file=str(file_path),
            chunks=chunks,
            metadata=metadata,
        )

    def _parse_cloud(self, file_path: Path, doc_id: str) -> ParsedDocument:
        """Parse document using Datalab cloud API.

        Note:
            Cloud mode uploads the document content to a third-party API.
            Ensure this is acceptable for your data classification policy.

        Args:
            file_path: Path to the document file.
            doc_id: Unique document identifier.

        Returns:
            ParsedDocument instance.
        """
        if not self.datalab_api_key:
            raise ValueError("DATALAB_API_KEY is required for cloud mode")

        try:
            from datalab import DocumentParser
        except ImportError:
            raise ImportError(
                "datalab package is required for cloud mode. " "Install with: pip install datalab"
            ) from None

        parser = DocumentParser(api_key=self.datalab_api_key)
        try:
            result = parser.parse(str(file_path))
        except Exception as exc:
            raise DocumentParseError(f"Datalab failed to parse {file_path.name}: {exc}") from exc

        markdown = result.markdown
        metadata_json = result.metadata

        chunks = self.extract_chunks(markdown)
        metadata = self.extract_metadata(metadata_json, str(file_path))

        return ParsedDocument(
            doc_id=doc_id,
            source_file=str(file_path),
            chunks=chunks,
            metadata=metadata,
        )

    def _parse_fallback(self, file_path: Path, doc_id: str) -> ParsedDocument:
        """Fallback parsing when marker is not available.

        For PDFs, uses pypdf if available. For text-like files, reads
        directly.

        Args:
            file_path: Path to the document file.
            doc_id: Unique document identifier.

        Returns:
            ParsedDocument with basic content.

        Raises:
            DocumentParseError: If extraction fails.
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            content = self._extract_pdf_text(file_path)
        elif suffix in {".epub", ".mobi"}:
            content = self._extract_epub_text(file_path)
        else:
            content = file_path.read_text(encoding="utf-8", errors="replace")

        title = file_path.stem.replace("_", " ").replace("-", " ").title()

        chunks = self.extract_chunks(content)

        metadata = DocumentMetadata(
            title=title,
            source_file=str(file_path),
            document_type=suffix.lstrip("."),
        )

        return ParsedDocument(
            doc_id=doc_id,
            source_file=str(file_path),
            chunks=chunks,
            metadata=metadata,
        )

    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF using pypdf.

        Args:
            file_path: Path to PDF file.

        Returns:
            Extracted text content.

        Raises:
            ImportError: If pypdf is not installed.
            DocumentParseError: If the PDF cannot be read.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError(
                f"Cannot parse {file_path.name} without marker-pdf or pypdf. "
                "Install a parser with: pip install 'termite[marker]'"
            ) from None

        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(f"## Page {page_num + 1}\n\n{text}")
        except Exception as exc:
            raise DocumentParseError(
                f"Failed to extract text from {file_path.name}: {exc}"
            ) from exc

        if not text_parts:
            raise DocumentParseError(
                f"No extractable text found in {file_path.name} "
                "(image-only PDF? marker-pdf or OCR would be required)"
            )

        return "\n\n".join(text_parts)

    def _extract_epub_text(self, file_path: Path) -> str:
        """Extract text from EPUB file.

        Enforces extraction-size limits to protect memory from
        decompression-bomb archives.

        Args:
            file_path: Path to EPUB file.

        Returns:
            Extracted text content.

        Raises:
            DocumentParseError: If the archive is invalid, oversized, or
                no text can be extracted.
        """
        # Prefer defusedxml for untrusted archives (EPUBs are untrusted
        # input); fall back to stdlib with enforced size limits.
        ET = _element_tree_module()

        try:
            with zipfile.ZipFile(file_path, "r") as epub:
                infos = {info.filename: info for info in epub.infolist()}

                # Reject archives whose uncompressed size is absurd before
                # reading anything (decompression-bomb guard).
                declared_total = sum(max(info.file_size, 0) for info in infos.values())
                if infos and declared_total > MAX_EPUB_TOTAL_BYTES:
                    raise DocumentParseError(
                        f"{file_path.name}: uncompressed size "
                        f"{declared_total / 1e6:.0f} MB exceeds EPUB limit "
                        f"({MAX_EPUB_TOTAL_BYTES // 1024 // 1024} MB)"
                    )

                content_file = next(
                    (name for name in infos if name.lower().endswith(".opf")),
                    None,
                )
                if not content_file:
                    raise DocumentParseError(f"{file_path.name}: no OPF package document found")

                opf_base = posixpath.dirname(content_file)
                opf_root = ET.fromstring(self._read_zip_text(epub, infos, content_file))

                # Namespace-agnostic manifest/spine parsing
                ns = {"opf": "http://www.idpf.org/2007/opf"}

                manifest: dict[str, str] = {}
                for item in opf_root.findall(".//opf:item", ns):
                    item_id = item.get("id", "")
                    href = item.get("href", "")
                    media_type = item.get("media-type", "")
                    if "html" in media_type or "xml" in media_type:
                        manifest[item_id] = href

                spine_items: list[str] = []
                for itemref in opf_root.findall(".//opf:spine/opf:itemref", ns):
                    idref = itemref.get("idref", "")
                    if idref in manifest:
                        # Normalize the member path; never trust OPF hrefs verbatim.
                        member = posixpath.normpath(posixpath.join(opf_base, manifest[idref]))
                        if member.startswith(("..", "/")):
                            logger.warning("Ignoring out-of-tree EPUB member path %r", href)
                            continue
                        if member in infos:
                            spine_items.append(member)

                text_parts: list[str] = []
                for member in spine_items:
                    if member not in infos:
                        continue
                    try:
                        html_content = self._read_zip_text(epub, infos, member)
                    except DocumentParseError as exc:
                        logger.warning(
                            "EPUB %s: skipping member %s (%s)",
                            file_path.name,
                            member,
                            exc,
                        )
                        continue

                    try:
                        root = ET.fromstring(html_content)
                        text = self._extract_text_from_element(root)
                    except (ET.ParseError, ValueError):
                        # Some EPUBs ship HTML5 that is not strict XML.
                        text = re.sub(r"<[^>]+>", " ", html_content)
                        text = re.sub(r"\s+", " ", text)
                    if text.strip():
                        text_parts.append(text)

        except zipfile.BadZipFile as exc:
            raise DocumentParseError(f"{file_path.name}: corrupt EPUB archive") from exc

        if not text_parts:
            raise DocumentParseError(f"{file_path.name}: no readable text content in EPUB")

        return "\n\n".join(text_parts)

    def _read_zip_text(
        self,
        epub: zipfile.ZipFile,
        infos: dict[str, zipfile.ZipInfo],
        name: str,
    ) -> str:
        """Read one archive member as text with size enforcement.

        Raises:
            DocumentParseError: member too large or missing.
        """
        info = infos.get(name)
        if info is None:
            raise DocumentParseError(f"EPUB member not found: {name}")
        if info.file_size > MAX_EPUB_MEMBER_BYTES:
            raise DocumentParseError(
                f"EPUB member {name} exceeds per-member size limit "
                f"({MAX_EPUB_MEMBER_BYTES // 1024 // 1024} MB)"
            )
        with epub.open(name) as handle:
            raw = handle.read()
        if len(raw) > MAX_EPUB_MEMBER_BYTES:
            # Declared size was honest; enforce on the real bytes as well.
            raise DocumentParseError(f"EPUB member {name} expanded beyond the per-member limit")
        return raw.decode("utf-8", errors="replace")

    def _extract_text_from_element(self, element: Any) -> str:
        """Recursively extract text from XML element."""
        parts: list[str] = []
        if element.text:
            parts.append(element.text)
        for child in element:
            parts.append(self._extract_text_from_element(child))
            if child.tail:
                parts.append(child.tail)
        text = " ".join(part for part in parts if part)
        return re.sub(r"\s+", " ", text).strip()

    def extract_chunks(self, markdown: str, max_tokens: int = 500) -> list[DocumentChunk]:
        """Extract chunks from markdown content.

        Args:
            markdown: Markdown content to chunk.
            max_tokens: Maximum tokens per chunk (default 500).

        Returns:
            List of DocumentChunk instances.
        """
        # Split by headers first for semantic chunking
        lines = markdown.split("\n")
        chunks: list[DocumentChunk] = []
        current_content: list[str] = []
        current_tokens = 0
        chunk_counter = 1

        for line in lines:
            line_tokens = estimate_tokens(line)

            # If adding this line exceeds max_tokens and we have content
            if current_tokens + line_tokens > max_tokens and current_content:
                content = normalize_whitespace("\n".join(current_content))
                if content.strip():
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"chunk-{chunk_counter:04d}",
                            content=content,
                            token_count=current_tokens,
                        )
                    )
                    chunk_counter += 1
                    current_content = []
                    current_tokens = 0

            current_content.append(line)
            current_tokens += line_tokens

        # Don't forget the last chunk
        if current_content:
            content = normalize_whitespace("\n".join(current_content))
            if content.strip():
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"chunk-{chunk_counter:04d}",
                        content=content,
                        token_count=current_tokens,
                    )
                )

        # Ensure at least one chunk
        if not chunks:
            chunks.append(
                DocumentChunk(
                    chunk_id="chunk-0001",
                    content=normalize_whitespace(markdown)[:500] if markdown else "",
                    token_count=estimate_tokens(markdown[:500] if markdown else ""),
                )
            )

        return chunks

    def extract_metadata(
        self, json_data: dict[str, Any] | None, source_file: str
    ) -> DocumentMetadata:
        """Extract metadata from marker JSON output.

        Args:
            json_data: Metadata dictionary from marker.
            source_file: Original source file path.

        Returns:
            DocumentMetadata instance.
        """
        if json_data is None:
            json_data = {}

        title = json_data.get("title") or Path(source_file).stem.title()
        author = json_data.get("author")
        document_type = json_data.get("document_type")

        return DocumentMetadata(
            title=title,
            author=author,
            source_file=source_file,
            document_type=document_type,
        )

    def _generate_doc_id(self, file_path: Path) -> str:
        """Generate a unique document ID.

        Args:
            file_path: Path to the document file.

        Returns:
            12-character document identifier.
        """
        return hashlib.sha256(str(file_path).encode()).hexdigest()[:12]
