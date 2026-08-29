# Python API

Termite is importable as a library. The public API is re-exported from
the `termite.pipeline` package (see `__all__`).

## Quickstart

```python
from termite.config import TermiteConfig
from termite.pipeline import TermitePipeline

config = TermiteConfig()
config.pipeline.input_dir = "raw_docs"
config.pipeline.output_dir = "output"
config.compression.remove_stopwords = True

pipeline = TermitePipeline(config)
stats = pipeline.run(verbose=True)
```

## One-shot convenience

```python
from termite import run_pipeline

stats = run_pipeline(
    config_path="config.yaml",   # optional; defaults to ./config.yaml
    input_dir="raw_docs",         # optional overrides
    output_dir="out",
    mode="local",                 # "local" | "cloud"
    verbose=True,
)
```

### `PipelineStatistics` keys

| Key | Description |
|---|---|
| `documents_discovered` | Files found by the scanner. |
| `documents_parsed` | Files parsed successfully. |
| `documents_deduplicated` | Documents after dedup/compression. |
| `chunks_before` / `chunks_after` | Chunk counts across dedup. |
| `original_tokens` | Token estimate **before dedup** (true input baseline). |
| `compressed_tokens` | Token count of final corpus. |
| `compression_ratio` | `1 - compressed/original` over the full pipeline. |
| `cross_references_created` | References injected by the entity graph. |
| `execution_time_seconds` | Wall-clock runtime. |

## Components

Every stage is independently usable:

```python
from termite.pipeline import (
    DocumentIngester, MarkerParser, Deduplicator,
    EntityExtractor, EntityGraph, LexicalCompressor, OutputGenerator,
)

# Discovery (security-scanned)
from pathlib import Path
ingester = DocumentIngester(Path("raw_docs"), max_file_size_mb=128)
paths = ingester.discover_documents()

# Parsing
from termite.pipeline import MarkerParser
parser = MarkerParser(mode="local")          # optional: force_gpu=False
docs = [MarkerParser(mode="local").parse(p) for p in paths[:10]]

# Deduplication
from termite.pipeline import Deduplicator
from termite.config import DeduplicationConfig
dedup = Deduplicator(DeduplicationConfig(similarity_threshold=0.9))
unique, result = dedup.deduplicate(docs)

# Entities and cross-references
extractor = EntityExtractor()   # spaCy used automatically if installed
graph = EntityGraph()
graph.build_graph(unique, extractor)

# Compression
compressor = LexicalCompressor()
compressed = compressor.compress_document(unique[0])

# Output
gen = OutputGenerator(config)
docs_out, metadata = gen.generate_output(unique, inject_cross_references=True)
gen.write_output(docs, metadata)
```

## Errors

| Exception | When |
|---|---|
| `FileNotFoundError` | Parsed file missing. |
| `DocumentParseError` | Archive corrupt, oversized, or no extractable text. |
| `ValueError` | Misconfiguration (e.g. cloud mode without API key); validated config values out of range. |

The pipeline catches stage-level exceptions per document, logs them
(`logging.getLogger("termite")`) and continues with the remaining
documents.

## Logging

Termite logs through the standard `logging` module under the `termite`
logger namespace and does not configure handlers in library use. The CLI
installs a console handler (`--log-level`). Example:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
