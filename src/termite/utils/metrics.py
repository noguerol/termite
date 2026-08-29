"""Metrics utilities for Termite."""

from dataclasses import dataclass

# Rough estimate: ~4 characters per token for English text
CHARS_PER_TOKEN = 4


@dataclass
class CompressionMetrics:
    """Metrics for compression results."""

    original_tokens: int
    compressed_tokens: int
    original_chars: int
    compressed_chars: int
    compression_ratio: float
    deduplication_ratio: float

    @classmethod
    def from_documents(
        cls,
        original_tokens: int,
        compressed_tokens: int,
        original_chars: int,
        compressed_chars: int,
    ) -> "CompressionMetrics":
        """Create metrics from document counts.

        Args:
            original_tokens: Token count before compression.
            compressed_tokens: Token count after compression.
            original_chars: Character count before compression.
            compressed_chars: Character count after compression.

        Returns:
            CompressionMetrics instance.
        """
        compression_ratio = (
            1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0.0
        )
        deduplication_ratio = (
            1.0 - (compressed_chars / original_chars) if original_chars > 0 else 0.0
        )

        return cls(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            original_chars=original_chars,
            compressed_chars=compressed_chars,
            compression_ratio=compression_ratio,
            deduplication_ratio=deduplication_ratio,
        )


def estimate_tokens(text: str) -> int:
    """Estimate token count from text.

    Uses a rough heuristic of 4 characters per token.

    Args:
        text: Input text.

    Returns:
        Estimated token count.
    """
    return len(text) // CHARS_PER_TOKEN


def calculate_compression_ratio(original: int, compressed: int) -> float:
    """Calculate compression ratio as percentage reduction.

    Args:
        original: Original size.
        compressed: Compressed size.

    Returns:
        Compression ratio (0.0 to 1.0).
    """
    if original == 0:
        return 0.0
    return 1.0 - (compressed / original)
