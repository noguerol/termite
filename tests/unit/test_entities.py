"""Unit tests for entity extraction."""

from termite.models import DocumentChunk, ParsedDocument
from termite.pipeline.entity_extractor import Entity, EntityExtractor


class TestEntityExtractor:
    """Tests for EntityExtractor class."""

    def test_initialization(self):
        """Test extractor initializes with defaults."""
        extractor = EntityExtractor()
        assert extractor.model_name == "en_core_web_sm"
        assert len(extractor.technical_terms) > 0

    def test_initialization_custom_terms(self):
        """Test extractor initializes with custom technical terms."""
        custom_terms = {"python", "docker", "kubernetes"}
        extractor = EntityExtractor(technical_terms=custom_terms)
        assert extractor.technical_terms == custom_terms

    def test_initialization_custom_model(self):
        """Test extractor initializes with custom model."""
        extractor = EntityExtractor(model="en_core_web_md")
        assert extractor.model_name == "en_core_web_md"


class TestExtractEntities:
    """Tests for extract_entities method."""

    def test_extract_entities_returns_list(self):
        """Test that extract_entities returns a list."""
        extractor = EntityExtractor()
        result = extractor.extract_entities("This is some test text.")
        assert isinstance(result, list)

    def test_extract_technical_terms(self):
        """Test that technical terms are extracted."""
        extractor = EntityExtractor()
        text = "Python is a great language for machine learning."
        entities = extractor.extract_entities(text)

        # Should extract Python (technical term)
        tech_entities = [e for e in entities if e.label == "TECHNICAL"]
        assert any(e.text.lower() == "python" for e in tech_entities)

    def test_extract_multiple_technical_terms(self):
        """Test that multiple technical terms are extracted."""
        extractor = EntityExtractor()
        text = "Use Docker and Kubernetes for deployment."
        entities = extractor.extract_entities(text)

        tech_entities = [e for e in entities if e.label == "TECHNICAL"]
        texts_lower = [e.text.lower() for e in tech_entities]
        assert "docker" in texts_lower or "kubernetes" in texts_lower

    def test_deduplicates_entities(self):
        """Test that duplicate entities are removed."""
        extractor = EntityExtractor()
        text = "Python Python python is great."
        entities = extractor.extract_entities(text)

        # Should have at most one Python entity
        python_entities = [e for e in entities if e.text.lower() == "python"]
        assert len(python_entities) <= 1


class TestExtractFromDocument:
    """Tests for extract_from_document method."""

    def test_extract_from_document(self):
        """Test extracting entities from a document."""
        extractor = EntityExtractor()
        doc = ParsedDocument(
            doc_id="doc1",
            source_file="test.txt",
            chunks=[
                DocumentChunk(
                    chunk_id="c1",
                    content="Python is a programming language.",
                    token_count=5,
                ),
            ],
        )

        entities = extractor.extract_from_document(doc)

        assert len(entities) > 0
        assert all(e.doc_id == "doc1" for e in entities)

    def test_extract_with_entity_type_filter(self):
        """Test filtering by entity type."""
        extractor = EntityExtractor()
        doc = ParsedDocument(
            doc_id="doc1",
            source_file="test.txt",
            chunks=[
                DocumentChunk(
                    chunk_id="c1",
                    content="Python is great. Docker is useful.",
                    token_count=10,
                ),
            ],
        )

        # Filter only technical terms
        entities = extractor.extract_from_document(doc, entity_types=["TECHNICAL"])

        assert all(e.label == "TECHNICAL" for e in entities)

    def test_extract_from_empty_document(self):
        """Test extracting from document with no content."""
        extractor = EntityExtractor()
        doc = ParsedDocument(
            doc_id="doc1",
            source_file="test.txt",
            chunks=[],
        )

        entities = extractor.extract_from_document(doc)
        # Should return empty list without error
        assert isinstance(entities, list)


class TestGetEntityFrequency:
    """Tests for get_entity_frequency method."""

    def test_frequency_calculation(self):
        """Test entity frequency is calculated correctly."""
        extractor = EntityExtractor()
        entities = [
            Entity(text="Python", label="TECHNICAL"),
            Entity(text="Python", label="TECHNICAL"),
            Entity(text="Docker", label="TECHNICAL"),
        ]

        freq = extractor.get_entity_frequency(entities)

        # Keys are lowercase
        assert freq.get("python|TECHNICAL") == 2
        assert freq.get("docker|TECHNICAL") == 1


class TestEntityClass:
    """Tests for Entity dataclass."""

    def test_entity_equality(self):
        """Test that entities are compared by text and label."""
        ent1 = Entity(text="Python", label="TECHNICAL")
        ent2 = Entity(text="Python", label="TECHNICAL")
        ent3 = Entity(text="Python", label="ORG")

        assert ent1 == ent2
        assert ent1 != ent3

    def test_entity_hash(self):
        """Test that entities can be put in sets."""
        ent1 = Entity(text="Python", label="TECHNICAL")
        ent2 = Entity(text="Python", label="TECHNICAL")

        entities_set = {ent1, ent2}
        assert len(entities_set) == 1  # Duplicates removed

    def test_entity_case_insensitive(self):
        """Test that entity comparison is case insensitive."""
        ent1 = Entity(text="PYTHON", label="TECHNICAL")
        ent2 = Entity(text="python", label="TECHNICAL")

        assert ent1 == ent2
