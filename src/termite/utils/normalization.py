"""Text normalization utilities for Termite."""

import re
import unicodedata
from collections.abc import Callable
from functools import reduce


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    Replaces multiple spaces with single space and strips leading/trailing whitespace.

    Args:
        text: Input text.

    Returns:
        Text with normalized whitespace.
    """
    return re.sub(r"\s+", " ", text).strip()


def remove_punctuation(text: str) -> str:
    """Remove punctuation from text.

    Args:
        text: Input text.

    Returns:
        Text with punctuation removed.
    """
    # Keep alphanumeric and spaces
    return re.sub(r"[^\w\s]", "", text)


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters to their canonical form.

    Args:
        text: Input text.

    Returns:
        Text with normalized unicode.
    """
    return unicodedata.normalize("NFKC", text)


def normalize_for_hash(text: str) -> str:
    """Normalize text for hash computation.

    This function:
    1. Lowercases the text
    2. Removes punctuation
    3. Normalizes whitespace
    4. Normalizes unicode

    Args:
        text: Input text.

    Returns:
        Normalized text ready for hashing.
    """
    # Apply normalization pipeline
    text = text.lower()
    text = normalize_unicode(text)
    text = remove_punctuation(text)
    text = normalize_whitespace(text)
    return text


def create_pipeline(*functions: Callable[[str], str]) -> Callable[[str], str]:
    """Create a normalization pipeline from multiple functions.

    Args:
        functions: Variable number of transformation functions.

    Returns:
        A single function that applies all transformations in order.
    """

    def pipeline(text: str) -> str:
        return reduce(lambda acc, fn: fn(acc), functions, text)

    return pipeline


def extract_ngrams(text: str, n: int = 3) -> set[str]:
    """Extract character n-grams from text.

    Args:
        text: Input text.
        n: Size of n-grams (default 3 for trigrams).

    Returns:
        Set of character n-grams.
    """
    text = normalize_for_hash(text)
    if len(text) < n:
        return set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Calculate Jaccard similarity between two sets.

    Args:
        set_a: First set.
        set_b: Second set.

    Returns:
        Jaccard similarity coefficient (0.0 to 1.0).
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union > 0 else 0.0
