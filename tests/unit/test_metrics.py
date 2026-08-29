"""Unit tests for metrics utilities."""

from termite.utils.metrics import (
    CHARS_PER_TOKEN,
    CompressionMetrics,
    calculate_compression_ratio,
    estimate_tokens,
)


class TestEstimateTokens:
    """Tests for estimate_tokens function."""

    def test_basic_estimation(self):
        """Test basic token estimation."""
        text = "Hello World"  # 10 chars / 4 = 2.5 -> 2 tokens
        assert estimate_tokens(text) == 2

    def test_longer_text(self):
        """Test estimation for longer text."""
        text = "This is a longer piece of text for testing."
        result = estimate_tokens(text)
        assert result == len(text) // CHARS_PER_TOKEN

    def test_empty_string(self):
        """Test that empty string returns 0 tokens."""
        assert estimate_tokens("") == 0


class TestCalculateCompressionRatio:
    """Tests for calculate_compression_ratio function."""

    def test_full_compression(self):
        """Test that compression to 0 returns 1.0."""
        assert calculate_compression_ratio(100, 0) == 1.0

    def test_no_compression(self):
        """Test that unchanged size returns 0.0."""
        assert calculate_compression_ratio(100, 100) == 0.0

    def test_partial_compression(self):
        """Test partial compression."""
        result = calculate_compression_ratio(100, 50)
        assert result == 0.5

    def test_zero_original(self):
        """Test that zero original returns 0.0."""
        assert calculate_compression_ratio(0, 0) == 0.0


class TestCompressionMetrics:
    """Tests for CompressionMetrics dataclass."""

    def test_from_documents_basic(self):
        """Test creating metrics from document counts."""
        metrics = CompressionMetrics.from_documents(
            original_tokens=100,
            compressed_tokens=70,
            original_chars=400,
            compressed_chars=280,
        )

        assert metrics.original_tokens == 100
        assert metrics.compressed_tokens == 70
        assert abs(metrics.compression_ratio - 0.3) < 0.001

    def test_from_documents_no_change(self):
        """Test metrics when no compression occurred."""
        metrics = CompressionMetrics.from_documents(
            original_tokens=100,
            compressed_tokens=100,
            original_chars=400,
            compressed_chars=400,
        )

        assert metrics.compression_ratio == 0.0
        assert metrics.deduplication_ratio == 0.0

    def test_from_documents_full_compression(self):
        """Test metrics with full compression."""
        metrics = CompressionMetrics.from_documents(
            original_tokens=100,
            compressed_tokens=0,
            original_chars=400,
            compressed_chars=0,
        )

        assert metrics.compression_ratio == 1.0
        assert metrics.deduplication_ratio == 1.0

    def test_from_documents_zero_original(self):
        """Test handling of zero original values."""
        metrics = CompressionMetrics.from_documents(
            original_tokens=0,
            compressed_tokens=0,
            original_chars=0,
            compressed_chars=0,
        )

        assert metrics.compression_ratio == 0.0
        assert metrics.deduplication_ratio == 0.0
