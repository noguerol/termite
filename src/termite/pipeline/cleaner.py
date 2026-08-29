"""Document cleaner module for Termite.

Cleans up extracted documents by removing:
- Broken image references
- Non-existent figure references
- Internal document links
- Malformed markdown links
"""

import re
from typing import TypedDict


class CleanerConfig(TypedDict):
    """Configuration for document cleaning."""

    remove_image_refs: bool
    remove_figure_refs: bool
    remove_internal_links: bool
    remove_broken_links: bool


class DocumentCleaner:
    """Cleans extracted documents of unusable references."""

    def __init__(self, config: CleanerConfig | None = None):
        """Initialize the cleaner."""
        if config is None:
            config = CleanerConfig(
                remove_image_refs=True,
                remove_figure_refs=True,
                remove_internal_links=True,
                remove_broken_links=True,
            )
        self.config = config

    def clean(self, text: str) -> str:
        """Clean a document text."""
        if self.config.get("remove_image_refs", True):
            text = self._remove_image_references(text)

        if self.config.get("remove_figure_refs", True):
            text = self._remove_figure_references(text)

        if self.config.get("remove_internal_links", True):
            text = self._remove_internal_links(text)

        if self.config.get("remove_broken_links", True):
            text = self._remove_broken_links(text)

        text = self._normalize_whitespace(text)
        return text

    def _remove_image_references(self, text: str) -> str:
        """Remove references to images that don't exist."""
        # Markdown images: ![alt](path)
        text = re.sub(
            r"!\[([^\]]*)\]\([^)]+\.(jpg|jpeg|png|gif|webp|svg)([^)]*)\)",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # HTML image tags
        text = re.sub(r"<img[^>]+>", "", text, flags=re.IGNORECASE)

        # Image file refs in parentheses
        text = re.sub(r"\([^)]*\.(jpg|jpeg|png|gif|webp|svg)\)", "", text, flags=re.IGNORECASE)

        # Image directory references
        text = re.sub(r"\(images/[^\)]+\)", "", text)
        text = re.sub(r"\[images/[^\]]+\]", "", text)

        # Relative image paths
        text = re.sub(r'\.\./(?:raw/)?images/[^\s\)"\'\]]+', "", text)
        text = re.sub(r'(?:raw/)?images/[^\s\)"\'\]]+', "", text)

        return text

    def _remove_figure_references(self, text: str) -> str:
        """Remove references to non-existent figures."""
        # (fig. X.X), (figure X.X), (Fig X.X)
        text = re.sub(
            r"\((?:fig|figure|Fig|FIGURE)\.?\s*\d+[\.\d]*[a-z]?\)",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # (see fig. X.X), (see figure X.X)
        text = re.sub(
            r"\(see\s+(?:fig|figure|Fig|FIGURE)\.?\s*\d+[\.\d]*[a-z]?\)",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Standalone figur X.X, figure X.X
        text = re.sub(r"\s+(?:figur|figure)\s+\d+[\.\d]*[a-z]?", "", text, flags=re.IGNORECASE)

        # (photograph by ...), (photo ...), (graph ...)
        text = re.sub(r"\((?:phot|photograph)[^)]+\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\((?:courtesy|source)[^)]+\)", "", text, flags=re.IGNORECASE)

        # (IMG_XXXX.JPG)
        text = re.sub(r"\(IMG_\d+\.[A-Z]{3,4}\)", "", text, flags=re.IGNORECASE)

        return text

    def _remove_internal_links(self, text: str) -> str:
        """Remove references to internal document links."""
        # Markdown links to .md files
        text = re.sub(r"\[([^\]]+)\]\([^)]*\.md(?:#[^)]*)?\)", r"\1", text)

        # Markdown links with ../
        text = re.sub(r"\[([^\]]+)\]\([^)]*\.\./[^)]*\.md(?:#[^)]*)?\)", r"\1", text)

        # Raw doc refs in parentheses
        text = re.sub(r"\([^)]*\.md#[^)]+\)", "", text)

        # (page 123) refs
        text = re.sub(r"\(page\s*\d+\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\(see\s+page\s*\d+\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+page\s+\d+\s*$", "", text, flags=re.IGNORECASE)

        return text

    def _remove_broken_links(self, text: str) -> str:
        """Remove broken or empty links."""
        # Empty markdown links
        text = re.sub(r"\[([^\]]+)\]\(\s*\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\(\s+\)", r"\1", text)
        text = re.sub(r"\[\s*\]", "", text)
        text = re.sub(r"\[([^\]]*)\]\(#+\)", r"\1", text)
        text = re.sub(r"\(\s*\)", "", text)

        # Cleanup punctuation
        text = re.sub(r"\.\.\.", ".", text)
        text = re.sub(r"\.\.", ".", text)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n\n+", "\n\n", text)
        text = re.sub(r" +([.,;:!?])", r"\1", text)
        text = re.sub(r"\[ +", "[", text)
        text = re.sub(r" +\](?=[^)])", "]", text)
        text = re.sub(r"\( +", "(", text)
        text = re.sub(r" +\)(?=[^)])", ")", text)
        return text.strip()


def clean_document(text: str) -> str:
    """Convenience function to clean a document."""
    cleaner = DocumentCleaner()
    return cleaner.clean(text)
