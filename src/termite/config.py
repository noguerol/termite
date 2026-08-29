"""Configuration management for Termite."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    """Pipeline configuration."""

    input_dir: Path = Field(default_factory=lambda: Path("./raw_docs"))
    output_dir: Path = Field(default_factory=lambda: Path("./output"))
    mode: Literal["local", "cloud"] = "local"
    max_file_size_mb: float = Field(
        default=256.0,
        gt=0,
        description="Files larger than this are skipped (guards against "
        "memory exhaustion and zip-bomb style inputs).",
    )


class MarkerConfig(BaseModel):
    """Marker parser configuration."""

    use_llm_extraction: bool = True
    extract_metadata: bool = True


class DeduplicationConfig(BaseModel):
    """Deduplication configuration."""

    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    strategy: Literal["keep_first", "keep_latest", "smart_merge"] = "smart_merge"


class CrossReferenceConfig(BaseModel):
    """Cross-reference configuration."""

    enabled: bool = True
    min_common_entities: int = Field(default=2, ge=1)
    max_refs_per_doc: int = Field(default=5, ge=1)


class CompressionConfig(BaseModel):
    """Compression configuration."""

    remove_stopwords: bool = False
    apply_stemming: bool = False
    normalize_headers: bool = True
    language: Literal["auto", "en", "es"] = "auto"


class TermiteConfig(BaseModel):
    """Root configuration for Termite."""

    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    marker: MarkerConfig = Field(default_factory=MarkerConfig)
    deduplication: DeduplicationConfig = Field(default_factory=DeduplicationConfig)
    cross_reference: CrossReferenceConfig = Field(default_factory=CrossReferenceConfig)
    compression: CompressionConfig = Field(default_factory=CompressionConfig)


def load_config(config_path: str | Path = "config.yaml") -> TermiteConfig:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        TermiteConfig: Loaded and validated configuration.
    """
    path = Path(config_path)
    if not path.exists():
        return TermiteConfig()

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return TermiteConfig(**data)


def _path_representer(dumper: yaml.Dumper, path: Path) -> yaml.Node:
    """Represent a Path as a string."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(path))


def save_config(config: TermiteConfig, config_path: str | Path = "config.yaml") -> None:
    """Save configuration to YAML file.

    Args:
        config: Configuration to save.
        config_path: Path to save the configuration file.
    """
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and handle Path objects
    data = config.model_dump()
    data = _convert_paths_to_strings(data)

    yaml.add_representer(Path, _path_representer)

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def _convert_paths_to_strings(data: Any) -> Any:
    """Recursively convert Path objects to strings."""
    if isinstance(data, Path):
        return str(data)
    if isinstance(data, dict):
        return {k: _convert_paths_to_strings(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_paths_to_strings(item) for item in data]
    return data
