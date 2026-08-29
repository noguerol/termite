"""Lexical compression module for Termite - Multi-language support."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import Any

from termite.config import CompressionConfig
from termite.models import DocumentChunk, ParsedDocument
from termite.pipeline.cleaner import DocumentCleaner
from termite.utils.metrics import estimate_tokens
from termite.utils.normalization import normalize_whitespace

logger = logging.getLogger(__name__)

# Spanish stopwords (single tokens). Multi-word expressions live in
# SPANISH_STOPWORD_PHRASES and are removed by a dedicated pass.
SPANISH_STOPWORDS = {
    # Articles
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    # Demonstratives
    "este",
    "esta",
    "esto",
    "estos",
    "estas",
    "ese",
    "esa",
    "esos",
    "esas",
    "aquel",
    "aquella",
    "aquello",
    "aquellos",
    "aquellas",
    # Possessives
    "mi",
    "tu",
    "su",
    "mis",
    "tus",
    "sus",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
    "vuestro",
    "vuestra",
    "vuestros",
    "vuestras",
    # Personal pronouns
    "yo",
    "me",
    "mí",
    "conmigo",
    "tú",
    "te",
    "ti",
    "contigo",
    "él",
    "ella",
    "ello",
    "se",
    "sí",
    "consigo",
    "nosotros",
    "nosotras",
    "nos",
    "vosotros",
    "vosotras",
    "os",
    "ellos",
    "ellas",
    "ustedes",
    "usted",
    # Interrogatives / exclamatives
    "qué",
    "quién",
    "cuál",
    "cuáles",
    "dónde",
    "cuándo",
    "cómo",
    "cuánto",
    "cuánta",
    "cuántos",
    "cuántas",
    # Indefinites
    "algo",
    "alguien",
    "algún",
    "alguna",
    "algunos",
    "algunas",
    "nada",
    "nadie",
    "ningún",
    "ninguna",
    "ningunos",
    "ningunas",
    "todo",
    "toda",
    "todos",
    "todas",
    "otro",
    "otra",
    "otros",
    "otras",
    "mismo",
    "misma",
    "mismos",
    "mismas",
    "vario",
    "varios",
    "varias",
    "bastante",
    "bastantes",
    "demás",
    # Conjunctions
    "y",
    "e",
    "o",
    "u",
    "pero",
    "sino",
    "aunque",
    "porque",
    "que",
    "si",
    "como",
    "así",
    "luego",
    "mientras",
    "además",
    "también",
    # Prepositions
    "a",
    "ante",
    "bajo",
    "cabe",
    "con",
    "contra",
    "de",
    "desde",
    "durante",
    "en",
    "entre",
    "hacia",
    "hasta",
    "mediante",
    "para",
    "por",
    "según",
    "sin",
    "sobre",
    "tras",
    # Auxiliary / high-frequency verbs
    "es",
    "son",
    "fue",
    "fueron",
    "era",
    "eran",
    "sido",
    "siendo",
    "está",
    "están",
    "estuvo",
    "estuvieron",
    "estado",
    "estando",
    "ha",
    "han",
    "hay",
    "haber",
    "había",
    "habían",
    "he",
    "has",
    "hemos",
    "sea",
    "sean",
    "fuera",
    "fueran",
    "tenga",
    "tengan",
    "tuve",
    "tuvieron",
    "tenido",
    "teniendo",
    "va",
    "van",
    "ido",
    "yendo",
    # High-frequency adverbs
    "no",
    "tampoco",
    "muy",
    "más",
    "menos",
    "ya",
    "todavía",
    "aún",
    "ahora",
    "antes",
    "después",
    "aquí",
    "ahí",
    "allí",
    "donde",
    "cuando",
    "bien",
    "mal",
    "mejor",
    "peor",
    "siempre",
    "nunca",
    "jamás",
    "acaso",
    "quizá",
    "quizás",
    "probablemente",
    "solamente",
    "solo",
    "sólo",
    "incluso",
    "recién",
    "apenas",
    # Other frequent forms
    "del",
    "al",
    "excepto",
    "ser",
    "estar",
    "tener",
    "hacer",
    "poder",
    "querer",
    "saber",
    "cada",
    "gran",
    "grande",
    "mayor",
    "menor",
    "alguno",
    "ninguno",
    "mucho",
    "poco",
    "tanto",
}

#: Multi-word Spanish expressions. A plain token set cannot match these,
#: so they are removed with a word-boundary regex before token filtering.
SPANISH_STOPWORD_PHRASES = (
    "con nosotros",
    "con vosotros",
    "sin embargo",
    "no obstante",
    "a través de",
    "debido a",
    "gracias a",
    "junto a",
    "lejos de",
    "tal vez",
    "por qué",
    "para qué",
    "a qué",
    "en qué",
)

# English stopwords
ENGLISH_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "nor",
    "for",
    "yet",
    "so",
    "in",
    "on",
    "at",
    "to",
    "from",
    "by",
    "with",
    "about",
    "as",
    "into",
    "of",
    "off",
    "over",
    "under",
    "above",
    "below",
    "between",
    "among",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "ought",
    "need",
    "dare",
    "i",
    "me",
    "my",
    "myself",
    "we",
    "our",
    "ours",
    "ourselves",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "what",
    "which",
    "who",
    "whom",
    "this",
    "that",
    "these",
    "those",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "not",
    "only",
    "same",
    "than",
    "too",
    "very",
    "just",
    "also",
    "now",
    "then",
    "once",
    "always",
    "never",
    "ever",
    "again",
    "already",
    "still",
    "often",
    "sometimes",
    "however",
    "therefore",
    "thus",
    "hence",
}

# Language patterns for detection
LANGUAGE_PATTERNS = {
    "es": [
        # Spanish-specific characters
        r"[áéíóúüñ¿¡]",
        # Common Spanish words not present in English
        r"\b(la|las|los|el|un|una|de|en|que|con|por|para|como|más|pero|este|esta|esto|estos|estas)\b",
    ],
    "en": [
        # Common English function words
        r"\b(the|and|is|are|was|were|have|has|had|that|this|with|from|for|not|you|your)\b",
    ],
}

#: Regex matching fenced and inline code spans; these regions are never
#: altered by stopword removal or stemming.
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```|`[^`]+`")


def _split_code_blocks(text: str) -> list[tuple[str, str]]:
    """Split text into plain and code segments.

    Returns:
        List of (kind, content) tuples where kind is ``"text"`` or
        ``"code"``. Concatenating all parts reproduces the input.
    """
    parts: list[tuple[str, str]] = []
    current_pos = 0
    for match in _CODE_BLOCK_RE.finditer(text):
        if match.start() > current_pos:
            parts.append(("text", text[current_pos : match.start()]))
        parts.append(("code", match.group()))
        current_pos = match.end()
    if current_pos < len(text):
        parts.append(("text", text[current_pos:]))
    return parts


class LanguageDetector:
    """Detects the language of text."""

    @staticmethod
    def detect(text: str) -> str:
        """Detect language of text.

        Args:
            text: Text to analyze.

        Returns:
            Language code: 'es', 'en', or 'unknown'
        """
        lowered = text.lower()

        # Quick check for Spanish-specific characters
        spanish_chars = len(re.findall(r"[áéíóúüñ¿¡]", lowered))

        # Count Spanish words
        spanish_words = len(
            re.findall(
                r"\b(la|las|los|el|un|una|de|en|que|con|por|para|como|más|pero|este|esta|esto|ser|estar|tener|haber|hacer|poder|querer|saber)\b",
                lowered,
            )
        )

        # Count English words
        english_words = len(
            re.findall(
                r"\b(the|and|is|are|was|were|have|has|that|this|with|from|for|not|you|your)\b",
                lowered,
            )
        )

        # Decision
        if spanish_chars > 0 or spanish_words > english_words:
            return "es"
        if english_words > 0:
            return "en"

        # Fallback: check word endings common in each language
        spanish_endings = len(
            re.findall(r"\b\w+(?:ación|imiento|idad|mente|ción|ología|ería)\b", lowered)
        )
        english_endings = len(re.findall(r"\b\w+(?:tion|ness|ment|ology|ing|ed|ly)\b", lowered))

        if spanish_endings > english_endings:
            return "es"
        if english_endings > spanish_endings:
            return "en"

        return "unknown"


class LexicalCompressor:
    """Applies lexical compression to text while preserving semantics.

    Supports multiple languages with automatic detection. The target
    language can be forced via ``CompressionConfig.language``; with the
    default ``"auto"`` the language is detected per text.
    """

    def __init__(self, config: CompressionConfig | None = None):
        """Initialize the compressor.

        Args:
            config: Compression configuration.
        """
        if config is None:
            config = CompressionConfig()

        self.remove_stopwords = config.remove_stopwords
        self.apply_stemming = config.apply_stemming
        self.normalize_headers_enabled = config.normalize_headers
        self.language_mode = config.language
        self.detector = LanguageDetector()

        # Initialize document cleaner
        self.cleaner = DocumentCleaner()

        # Stemmers are created lazily per language on first use.
        self._stemmers: dict[str, Any | None] = {}
        self._stemmer_init_failed = False
        if self.apply_stemming:
            self._init_stemmers()

    def _init_stemmers(self) -> None:
        """Initialize stemmers for supported languages (Snowball via NLTK)."""
        try:
            from nltk.stem import SnowballStemmer

            self._stemmers["es"] = SnowballStemmer("spanish")
            self._stemmers["en"] = SnowballStemmer("english")
        except ImportError:
            try:
                from nltk.stem import PorterStemmer

                # Fallback: English-only stemming.
                self._stemmers["en"] = PorterStemmer()
                self._stemmers["es"] = None
            except ImportError:
                self._stemmer_init_failed = True
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Stemming is enabled but NLTK is not installed; "
                    "stemming will be skipped. Install with: "
                    "pip install 'termite[stemming]'"
                )

    def _resolve_language(self, text: str) -> str:
        """Resolve the language to use for a given text.

        Honors the configured language override (``en``/``es``); with
        ``auto`` falls back to detection, defaulting to English for
        undetermined text.
        """
        if self.language_mode != "auto":
            return self.language_mode
        lang = self.detector.detect(text)
        return "en" if lang == "unknown" else lang

    def compress_text(self, text: str) -> str:
        """Compress text while preserving semantics.

        Args:
            text: Input text to compress.

        Returns:
            Compressed text.
        """
        # Clean up broken references, images, figures first
        text = self.cleaner.clean(text)

        lang = self._resolve_language(text)

        # Remove consecutive duplicate words
        text = self.remove_consecutive_duplicates(text)

        # Apply stopword removal if enabled
        if self.remove_stopwords:
            text = self.filter_stopwords(text, lang)

        # Apply stemming if enabled
        if self.apply_stemming:
            stemmer = self._get_stemmer(lang)
            if stemmer:
                text = self._apply_stemming(text, stemmer)

        # Normalize whitespace
        text = normalize_whitespace(text)

        return text

    def get_stopwords(self, lang: str) -> set[str]:
        """Get stopwords for the specified language."""
        if lang == "es":
            return set(SPANISH_STOPWORDS)
        return set(ENGLISH_STOPWORDS)

    def filter_stopwords(
        self,
        text: str,
        lang: str = "en",
        whitelist: Iterable[str] | None = None,
    ) -> str:
        """Remove stopwords for the given language.

        Args:
            text: Input text.
            lang: Language code (``"es"`` or ``"en"``).
            whitelist: Optional extra words that must never be removed.
                Multi-word phrases in the whitelist are protected as
                phrases.

        Returns:
            Text with stopwords removed (code spans untouched).
        """
        stopwords = self.get_stopwords(lang)
        protected = {w.lower() for w in whitelist} if whitelist else set()

        # Split multi-word whitelist entries out for phrase protection.
        phrase_whitelist = {p for p in protected if " " in p}
        protected_single = protected - phrase_whitelist

        result_parts: list[str] = []
        for kind, content in _split_code_blocks(text):
            if kind == "code":
                result_parts.append(content)
                continue

            if lang == "es":
                content = self._remove_phrases(
                    content, SPANISH_STOPWORD_PHRASES, protected=phrase_whitelist
                )

            words = content.split()
            filtered = []
            for word in words:
                word_lower = word.lower().strip(".,!?;:\"'()[]{}")
                if (
                    word_lower in protected_single
                    or word_lower in protected
                    or word_lower not in stopwords
                ):
                    filtered.append(word)
            result_parts.append(" ".join(filtered))

        return "".join(result_parts)

    @staticmethod
    def _remove_phrases(text: str, phrases: Iterable[str], protected: Iterable[str] = ()) -> str:
        """Remove stopword phrases while protecting whitelist phrases."""
        protected = {p.lower() for p in protected}
        removable = sorted(
            (p for p in phrases if p.lower() not in protected),
            key=len,
            reverse=True,  # longest first so overlapping phrases resolve
        )
        if not removable:
            return text
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(p) for p in removable) + r")\b",
            flags=re.IGNORECASE,
        )
        return pattern.sub(" ", text)

    def _get_stemmer(self, lang: str) -> Any:
        """Return the stemmer for a language, creating it on demand."""
        if self._stemmer_init_failed:
            return None
        if lang not in self._stemmers:
            self._init_stemmers()
        return self._stemmers.get(lang) or self._stemmers.get("en")

    def _apply_stemming(self, text: str, stemmer: Any) -> str:
        """Apply stemming to text (code spans preserved)."""
        result_parts: list[str] = []
        for kind, content in _split_code_blocks(text):
            if kind == "code":
                result_parts.append(content)
            else:
                stemmed = [self._stem_word(word, stemmer) for word in content.split()]
                result_parts.append(" ".join(stemmed))
        return "".join(result_parts)

    def _stem_word(self, word: str, stemmer: Any) -> str:
        """Stem a single word, preserving surrounding punctuation."""
        if not word or len(word) <= 2:
            return word

        # Extract leading punctuation
        prefix = ""
        clean_word = word
        while clean_word and not clean_word[0].isalnum():
            prefix += clean_word[0]
            clean_word = clean_word[1:]

        # Extract trailing punctuation
        suffix = ""
        while clean_word and not clean_word[-1].isalnum():
            suffix = clean_word[-1] + suffix
            clean_word = clean_word[:-1]

        # Apply stemming to alphabetic word
        if clean_word.isalpha() and len(clean_word) > 2:
            try:
                clean_word = stemmer.stem(clean_word.lower())
            except Exception as exc:  # noqa: BLE001 - preserve original word on stemmer failure
                logger.debug("Stemming failed for %r: %s", word, exc)

        return prefix + clean_word + suffix

    def compress_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        """Compress a document chunk."""
        compressed_content = self.compress_text(chunk.content)
        new_token_count = estimate_tokens(compressed_content)

        return chunk.model_copy(
            update={
                "content": compressed_content,
                "token_count": new_token_count,
            }
        )

    def compress_document(self, document: ParsedDocument) -> ParsedDocument:
        """Compress all chunks in a document."""
        compressed_chunks = [self.compress_chunk(c) for c in document.chunks]
        return document.model_copy(update={"chunks": compressed_chunks})

    def remove_consecutive_duplicates(self, text: str) -> str:
        """Remove consecutive duplicate words."""
        words = text.split()
        if not words:
            return text

        result = [words[0]]
        for word in words[1:]:
            if word.lower() != result[-1].lower():
                result.append(word)

        return " ".join(result)

    def normalize_headers(self, markdown: str, max_level: int = 2) -> str:
        """Normalize header levels to max_level or below."""
        lines = markdown.split("\n")
        result_lines = []

        for line in lines:
            header_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if header_match:
                level = min(len(header_match.group(1)), max_level)
                content = header_match.group(2)
                result_lines.append(f"{'#' * level} {content}")
            else:
                result_lines.append(line)

        return "\n".join(result_lines)

    def compress_markdown(self, markdown: str, preserve_code_blocks: bool = True) -> str:
        """Apply all compression to markdown content."""
        if preserve_code_blocks:
            parts = re.split(r"(```[\s\S]*?```)", markdown)
            result_parts = []

            for i, part in enumerate(parts):
                if i % 2 != 1:  # not a fenced code block
                    part = self.compress_text(part)
                if self.normalize_headers_enabled:
                    part = self.normalize_headers(part, max_level=2)
                result_parts.append(part)

            return "".join(result_parts)

        result = self.compress_text(markdown)
        if self.normalize_headers_enabled:
            result = self.normalize_headers(result, max_level=2)
        return result
