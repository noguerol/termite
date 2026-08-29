"""Non-functional tests for Phase 1."""

import time

import pytest

from termite.config import load_config


class TestPerformance:
    """Performance tests."""

    @pytest.mark.timeout(1)
    def test_config_load_time(self):
        """Config should load in under 100ms."""
        start = time.time()
        for _ in range(100):
            load_config("config.yaml")
        duration = (time.time() - start) / 100

        assert duration < 0.1, f"Config loading took {duration:.3f}s (expected < 0.1s)"


class TestReliability:
    """Reliability tests."""

    def test_invalid_config_handling(self):
        """System should handle invalid config gracefully."""
        from termite.config import load_config

        # Should not raise, should return defaults
        config = load_config("nonexistent_file.yaml")
        assert config is not None
