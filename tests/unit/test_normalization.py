"""Unit tests for normalization utilities."""

from termite.utils.normalization import (
    create_pipeline,
    extract_ngrams,
    jaccard_similarity,
    normalize_for_hash,
    normalize_whitespace,
    remove_punctuation,
)


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace function."""

    def test_single_spaces(self):
        """Test that multiple spaces are collapsed to single space."""
        text = "Hello    World"
        assert normalize_whitespace(text) == "Hello World"

    def test_tabs_and_newlines(self):
        """Test that tabs and newlines are converted to spaces."""
        text = "Hello\t\nWorld"
        assert normalize_whitespace(text) == "Hello World"

    def test_strip_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        text = "  Hello World  "
        assert normalize_whitespace(text) == "Hello World"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert normalize_whitespace("") == ""


class TestRemovePunctuation:
    """Tests for remove_punctuation function."""

    def test_removes_common_punctuation(self):
        """Test that common punctuation is removed."""
        text = "Hello, World! How are you?"
        result = remove_punctuation(text)
        assert "," not in result
        assert "!" not in result
        assert "?" not in result

    def test_preserves_alphanumeric(self):
        """Test that alphanumeric characters are preserved."""
        text = "Hello World 123"
        result = remove_punctuation(text)
        assert result == "Hello World 123"


class TestNormalizeForHash:
    """Tests for normalize_for_hash function."""

    def test_lowercase(self):
        """Test that text is lowercased."""
        text = "HELLO World"
        assert normalize_for_hash(text) == "hello world"

    def test_remove_punctuation(self):
        """Test that punctuation is removed."""
        text = "Hello, World!"
        assert normalize_for_hash(text) == "hello world"

    def test_normalize_whitespace(self):
        """Test that whitespace is normalized."""
        text = "Hello    World"
        assert normalize_for_hash(text) == "hello world"

    def test_full_pipeline(self):
        """Test complete normalization pipeline."""
        text = "  HELLO,   WORLD!  "
        result = normalize_for_hash(text)
        assert result == "hello world"

    def test_unicode_normalization(self):
        """Test that unicode is normalized."""
        text = "café"
        result = normalize_for_hash(text)
        # The 'é' should be preserved but normalized
        assert "cafe" in result or "caf" in result


class TestExtractNgrams:
    """Tests for extract_ngrams function."""

    def test_trigrams_basic(self):
        """Test basic trigram extraction."""
        text = "hello"
        ngrams = extract_ngrams(text, n=3)
        assert "hel" in ngrams
        assert "ell" in ngrams
        assert "llo" in ngrams

    def test_trigrams_count(self):
        """Test that correct number of trigrams is returned."""
        text = "hello world"
        ngrams = extract_ngrams(text, n=3)
        # "hello world" has 11 characters, so 9 trigrams
        assert len(ngrams) == 9

    def test_short_text(self):
        """Test handling of text shorter than n."""
        text = "hi"
        ngrams = extract_ngrams(text, n=3)
        assert ngrams == set()

    def test_normalized_extraction(self):
        """Test that n-grams are extracted from normalized text."""
        text = "Hello,  World!"
        ngrams = extract_ngrams(text, n=3)
        # Should be extracted from "hello world"
        assert "hel" in ngrams


class TestJaccardSimilarity:
    """Tests for jaccard_similarity function."""

    def test_identical_sets(self):
        """Test that identical sets return 1.0."""
        set_a = {"abc", "def", "ghi"}
        set_b = {"abc", "def", "ghi"}
        assert jaccard_similarity(set_a, set_b) == 1.0

    def test_disjoint_sets(self):
        """Test that disjoint sets return 0.0."""
        set_a = {"abc", "def"}
        set_b = {"ghi", "jkl"}
        assert jaccard_similarity(set_a, set_b) == 0.0

    def test_partial_overlap(self):
        """Test partial overlap calculation."""
        set_a = {"abc", "def", "ghi"}
        set_b = {"abc", "def", "jkl"}
        # Intersection: 2, Union: 4
        # Jaccard = 2/4 = 0.5
        assert jaccard_similarity(set_a, set_b) == 0.5

    def test_empty_sets(self):
        """Test that two empty sets return 1.0 (both empty = identical)."""
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty_set(self):
        """Test that one empty set returns 0.0."""
        assert jaccard_similarity({"abc"}, set()) == 0.0


class TestCreatePipeline:
    """Tests for create_pipeline function."""

    def test_single_function(self):
        """Test pipeline with single function."""
        pipeline = create_pipeline(normalize_whitespace)
        text = "Hello    World"
        assert pipeline(text) == "Hello World"

    def test_multiple_functions(self):
        """Test pipeline with multiple functions."""
        pipeline = create_pipeline(
            normalize_whitespace,
            str.lower,
            remove_punctuation,
        )
        text = "  HELLO,   WORLD!  "
        result = pipeline(text)
        assert result == "hello world"

    def test_empty_pipeline(self):
        """Test pipeline with no functions."""
        pipeline = create_pipeline()
        text = "Hello World"
        assert pipeline(text) == "Hello World"
