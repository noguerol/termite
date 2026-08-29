"""Unit tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from termite.config import (
    DeduplicationConfig,
    TermiteConfig,
    load_config,
    save_config,
)


def test_default_config():
    """Test that default configuration has expected values."""
    config = TermiteConfig()

    assert config.pipeline.input_dir == Path("./raw_docs")
    assert config.pipeline.output_dir == Path("./output")
    assert config.pipeline.mode == "local"
    assert config.deduplication.similarity_threshold == 0.85
    assert config.deduplication.strategy == "smart_merge"


def test_load_config_from_yaml():
    """Test loading configuration from YAML file."""
    config_data = {
        "pipeline": {
            "input_dir": "./input_docs",
            "output_dir": "./output_docs",
            "mode": "cloud",
        },
        "deduplication": {
            "similarity_threshold": 0.9,
            "strategy": "keep_first",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config_data, f)
        temp_path = f.name

    try:
        config = load_config(temp_path)

        assert config.pipeline.input_dir == Path("./input_docs")
        assert config.pipeline.output_dir == Path("./output_docs")
        assert config.pipeline.mode == "cloud"
        assert config.deduplication.similarity_threshold == 0.9
        assert config.deduplication.strategy == "keep_first"
    finally:
        Path(temp_path).unlink()


def test_load_nonexistent_config_returns_default():
    """Test that loading non-existent config returns defaults."""
    config = load_config("nonexistent_config_file.yaml")

    assert isinstance(config, TermiteConfig)
    assert config.pipeline.mode == "local"


def test_save_and_load_config(tmp_path):
    """Test saving and loading configuration."""
    config = TermiteConfig()
    config.pipeline.input_dir = tmp_path / "input"
    config.pipeline.output_dir = tmp_path / "output"
    config.deduplication.similarity_threshold = 0.75

    config_file = tmp_path / "config.yaml"
    save_config(config, config_file)

    loaded_config = load_config(config_file)

    assert loaded_config.pipeline.input_dir == tmp_path / "input"
    assert loaded_config.pipeline.output_dir == tmp_path / "output"
    assert loaded_config.deduplication.similarity_threshold == 0.75


def test_config_validation():
    """Test configuration validation."""
    TermiteConfig()

    # Test threshold bounds (should be 0.0 to 1.0)
    with pytest.raises(ValueError):
        TermiteConfig(deduplication=DeduplicationConfig(similarity_threshold=1.5))

    with pytest.raises(ValueError):
        TermiteConfig(deduplication=DeduplicationConfig(similarity_threshold=-0.1))


def test_config_partial_override():
    """Test that partial config only overrides specified values."""
    config_data = {
        "compression": {
            "remove_stopwords": True,
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config_data, f)
        temp_path = f.name

    try:
        config = load_config(temp_path)

        # Specified value
        assert config.compression.remove_stopwords is True
        # Default values
        assert config.pipeline.mode == "local"
        assert config.deduplication.similarity_threshold == 0.85
    finally:
        Path(temp_path).unlink()
