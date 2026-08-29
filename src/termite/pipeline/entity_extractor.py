"""Entity extraction module using spaCy (with fallback)."""

import logging
import re
from dataclasses import dataclass
from typing import ClassVar

from termite.models import ParsedDocument

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """A named entity extracted from text."""

    text: str
    label: str
    doc_id: str | None = None
    chunk_id: str | None = None

    def __hash__(self) -> int:
        return hash((self.text.lower(), self.label))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.text.lower() == other.text.lower() and self.label == other.label


class EntityExtractor:
    """Extracts named entities from text using spaCy or fallback."""

    # Default technical whitelist (can be customized)
    DEFAULT_TECHNICAL_TERMS: ClassVar[set[str]] = {
        "python",
        "javascript",
        "java",
        "golang",
        "rust",
        "typescript",
        "react",
        "angular",
        "vue",
        "django",
        "flask",
        "fastapi",
        "tensorflow",
        "pytorch",
        "keras",
        "sklearn",
        "numpy",
        "pandas",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "elasticsearch",
        "kubernetes",
        "docker",
        "terraform",
        "ansible",
        "jenkins",
        "github",
        "gitlab",
        "bitbucket",
        "aws",
        "azure",
        "gcp",
        "api",
        "rest",
        "graphql",
        "grpc",
        "http",
        "tcp",
        "udp",
        "jwt",
        "oauth",
        "saml",
        "ssl",
        "tls",
        "https",
        "html",
        "css",
        "json",
        "xml",
        "yaml",
        "toml",
        "markdown",
        "pdf",
        "docx",
        "txt",
    }

    def __init__(
        self,
        model: str = "en_core_web_sm",
        technical_terms: set[str] | None = None,
    ):
        """Initialize the entity extractor.

        Args:
            model: spaCy model name to use.
            technical_terms: Custom set of technical terms to extract.
        """
        self.model_name = model
        self.technical_terms = technical_terms or self.DEFAULT_TECHNICAL_TERMS.copy()
        self._nlp = None
        self._spacy_available = None
        # Compiled matcher for technical terms: word-boundary alternation,
        # built once per extractor. Substring matching would both miss
        # boundaries ("api" inside "rapid") and run in O(terms x text).
        self._term_pattern = re.compile(
            r"(?<![-\w])("
            + "|".join(re.escape(t) for t in sorted(self.technical_terms, key=len, reverse=True))
            + r")(?![\w-])",
            re.IGNORECASE,
        )

    def _check_spacy_available(self) -> bool:
        """Check if spaCy is available and working.

        The check performs the actual model load once and caches the
        outcome; the loaded pipeline is reused (no double load).
        """
        if self._spacy_available is not None:
            return self._spacy_available

        try:
            import spacy

            self._nlp = spacy.load(self.model_name)
            self._spacy_available = True
        except Exception as exc:  # noqa: BLE001 - spaCy failure must degrade gracefully
            logger.debug("spaCy model %s unavailable: %s", self.model_name, exc)
            self._nlp = None
            self._spacy_available = False

        return self._spacy_available

    @property
    def nlp(self):
        """Lazy-load spaCy model if available (loaded at most once)."""
        if self._nlp is None and self._check_spacy_available():
            # _check_spacy_available already loaded the model on success.
            pass
        return self._nlp

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract named entities from text.

        Args:
            text: Input text to analyze.

        Returns:
            List of Entity objects.
        """
        entities = []

        # Try spaCy extraction if model is available
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if self._is_relevant_entity_type(ent.label_):
                        entities.append(
                            Entity(
                                text=ent.text,
                                label=ent.label_,
                            )
                        )
            except Exception as exc:  # noqa: BLE001 - fall back to whitelist extraction
                logger.debug("spaCy extraction failed: %s", exc)

        # Extract technical terms (always available)
        entities.extend(self._extract_technical_terms(text))

        # Deduplicate
        return self._deduplicate_entities(entities)

    def extract_from_document(
        self,
        document: ParsedDocument,
        entity_types: list[str] | None = None,
    ) -> list[Entity]:
        """Extract entities from entire document.

        Args:
            document: Parsed document to analyze.
            entity_types: Filter by specific entity types.

        Returns:
            List of Entity objects.
        """
        all_entities: list[Entity] = []

        for chunk in document.chunks:
            chunk_entities = self.extract_entities(chunk.content)
            for ent in chunk_entities:
                ent.doc_id = document.doc_id
                ent.chunk_id = chunk.chunk_id
                all_entities.append(ent)

        # Filter by entity types if specified
        if entity_types:
            all_entities = [
                e for e in all_entities if e.label in entity_types or e.label == "TECHNICAL"
            ]

        return all_entities

    def _is_relevant_entity_type(self, label: str) -> bool:
        """Check if entity type is relevant for extraction.

        Args:
            label: spaCy entity label.

        Returns:
            True if the entity type should be extracted.
        """
        relevant_types = {
            "ORG",  # Organizations
            "PRODUCT",  # Products
            "LAW",  # Laws
            "GPE",  # Geopolitical entities
            "PERSON",  # People
            "NORP",  # Nationalities, religious, political groups
            "FAC",  # Facilities
            "EVENT",  # Events
            "WORK_OF_ART",  # Works of art
            "LANGUAGE",  # Languages
        }
        return label in relevant_types

    def _extract_technical_terms(self, text: str) -> list[Entity]:
        """Extract technical terms from whitelist.

        Args:
            text: Input text.

        Returns:
            List of technical Entity objects.
        """
        entities: list[Entity] = []
        seen: set[str] = set()

        for match in self._term_pattern.finditer(text):
            term = match.group(0)
            key = term.lower()
            if key not in seen:
                seen.add(key)
                entities.append(Entity(text=term, label="TECHNICAL"))

        return entities

    def _deduplicate_entities(self, entities: list[Entity]) -> list[Entity]:
        """Remove duplicate entities.

        Args:
            entities: List of entities.

        Returns:
            Deduplicated list.
        """
        seen: set[tuple[str, str]] = set()
        result = []

        for ent in entities:
            key = (ent.text.lower(), ent.label)
            if key not in seen:
                seen.add(key)
                result.append(ent)

        return result

    def get_entity_frequency(self, entities: list[Entity]) -> dict[str, int]:
        """Calculate entity frequency.

        Args:
            entities: List of entities.

        Returns:
            Dictionary mapping entity text to frequency.
        """
        freq: dict[str, int] = {}
        for ent in entities:
            key = f"{ent.text.lower()}|{ent.label}"
            freq[key] = freq.get(key, 0) + 1
        return freq
