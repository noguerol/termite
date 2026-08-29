<p align="center">
  <img src="assets/termite-banner.png" alt="Termite — a dragon devouring documents" width="100%" />
</p>

# Termite

**High-performance document compression and structuring for LLM ingestion.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/noguerol/termite/actions/workflows/ci.yml/badge.svg)](https://github.com/noguerol/termite/actions)

Termite converts raw documents (PDF, EPUB, DOCX, TXT, HTML, MD) into a
**compressed, deduplicated, cross-referenced Markdown corpus** that is
optimized for LLM ingestion — without semantic loss.

The goal is **direct RAG without a vector database**: the pipeline
produces a single, token-efficient, cross-referenced Markdown corpus that
can be placed directly in an LLM context window (or chunked cheaply),
while preserving technical terminology, entities, and cross-document
references.

---

## Why Termite

| | Traditional RAG | Termite |
|---|---|---|
| Indexing | Embedding models + vector DB | No embeddings, no DB |
| Infrastructure | Vector store, sync jobs | One Markdown file |
| Cross-document links | Manual / retrieval-approximate | Automatic entity graph |
| Token cost | Raw or naively chunked text | ~30–40% reduction, semantics preserved |
| Multi-language | Pipeline-specific plugins | Built-in English + Spanish |

Termite achieves this through **lossless-by-design lexical compression**
(redundancy removal, not summarization) plus deduplication and an
entity-based cross-reference graph.

## What it looks like

A short passage from a real Termite run (input is prose with stopwords;
output keeps every technical term, number, and entity):

**Input**

> Apache Kafka has become the de facto standard for event streaming in
> modern microservice architectures. However, operating a Kafka cluster
> in production requires a thorough understanding of its internal
> metrics, consumer group behavior, and the many failure modes that can
> affect end-to-end data delivery.

**Output (compressed)** — verbatim from the run:

```text
apach kafka becom de facto standard event stream modern microservic architectur. oper kafka cluster product requir thorough understand intern metric, consum group behavior, mani failur mode affect end-to-end data deliveri. document provid practic guid monitor kafka cluster, focus latenc, throughput, data integr.
```

No facts, numbers, or terminology are lost — only function words and
stemmed endings. Compression is tuned for LLM ingestion, not human
reading; keep the original corpus if you need verbatim text.

## What gets compressed (and what does not)

Compression operates on the **extracted text** — the prose Termite
parses out of each container — not on the binary file. What you save
depends on the *content*, not the format:

| Format | What Termite extracts | Compression potential |
|---|---|---|
| `.md`, `.txt` | Plain text, verbatim | Prose-heavy: ~30–35% |
| `.pdf` | Text layer (via marker / pypdf) | Prose: ~30%; image-heavy or scanned pages: little to none |
| `.epub` | Spine text, XML markup stripped | Prose: ~30%; the XML overhead disappears entirely |
| `.docx` | Text via marker, XML markup stripped | Prose: ~30% |
| `.html` | Text with tags stripped | Mixed prose/code: ~25–30% |

Caveats worth knowing:

- **Scanned PDFs** have no text layer — they are images. Termite needs
  text-based PDFs; scanned documents require OCR *before* ingestion.
- **A PDF's file size tells you nothing about its text**: a 10 MB PDF
  can hold a few paragraphs plus embedded fonts/images, while a 500 KB
  one can hold 30 pages of dense prose. Only the extracted text
  matters for tokens.
- **EPUB/DOCX/HTML wrap their content in markup**; that markup is
  stripped during parsing, so you never pay tokens for XML tags.

## Sizing and savings

Token counts are estimates (≈4 chars/token) for typical English
technical content, and refer to *extracted text* (not file size):

| Content type | Format | Raw tokens | Compressed | Saved |
|---|---|---|---|---|
| Blog / engineering article (prose) | `.md` | ~1,400 | ~950 | ~30% |
| White paper, prose (~10 pages) | `.pdf` | ~6,000 | ~4,100 | ~30% |
| Technical book, prose (~300 pp.) | `.epub` | ~90,000 | ~62,000 | ~30% |
| Meeting notes | `.txt` | ~400 | ~280 | ~30% |
| API reference (mixed prose/code) | `.html` | ~5,000 | ~3,600 | ~28% |
| Spec sheet, tables, figures | `.pdf` | varies | minimal | ~0–10% |

**What that means for a corpus of hundreds or thousands of documents**
(token savings are content-dependent; these assume prose-heavy docs):

| Corpus | Raw tokens | With Termite | Saved | 1M-token context windows |
|---|---|---|---|---|
| 100 typical docs | ~800 K | ~560 K | ~240 K | 1 window, with room |
| 1,000 typical docs | ~8 M | ~5.6 M | ~2.4 M | 8 → 6 windows |
| 10,000 typical docs | ~80 M | ~56 M | ~24 M | 80 → 56 windows |

In practice this means a corpus that previously needed several
context-window-sized passes now fits in fewer, or needs ~30% fewer
retrieval chunks — with cross-document links and duplicate removal
built in.

## Key features

- **Multi-format ingestion** — PDF, EPUB, MOBI, DOCX, TXT, HTML, MD; recursive scanning with a configurable size budget.
- **High-fidelity parsing** — [marker](https://github.com/datalab-to/marker) with GPU acceleration (NVIDIA CUDA and AMD ROCm), with lightweight fallbacks (`pypdf`, built-in EPUB/HTML readers).
- **Deduplication** — SHA-256 exact signatures and Jaccard similarity over character trigrams; merge strategies (`keep_first`, `keep_latest`, `smart_merge`).
- **Entity cross-referencing** — spaCy NER when available plus a technical-term whitelist; documents sharing entities are linked in-place with machine-readable comments.
- **Lexical compression** — language-aware stopword removal (EN/ES, with phrase-level Spanish stopwords), Snowball stemming, header normalization. Code spans are never altered.
- **Document cleaning** — removal of unusable artifacts (image/figure references, internal links, attributions, page references).
- **Enterprise hardening** — input-size guards, EPUB decompression-bomb limits, symlink-safe scanning, atomic output writes, no shell execution, `defusedxml`-based XML parsing, full logging support, strict CLI exit codes.
- **GPU acceleration** — NVIDIA CUDA and AMD ROCm device auto-detection for local parsing.

## Installation

```bash
# From GitHub (recommended; package not yet on PyPI)
pip install git+https://github.com/noguerol/termite.git

# From a source checkout
pip install -e .

# With local PDF parsing (marker-pdf)
pip install -e ".[marker]"

# With stemming support (NLTK Snowball stemmers)
pip install -e ".[stemming]"

# Everything (dev + marker + spaCy NER + stemming)
pip install -e ".[all]"
```

Requirements: Python ≥ 3.10. Optional heavy components (marker, spaCy,
Datalab cloud) are optional extras; Termite core is pure Python and
installs quickly.

## Quickstart

```bash
termite --input ./raw_docs --output ./output --stats -v
```

Output:

```text
output/
├── compressed_docs.md    # unified, compressed corpus
└── compressed_index.md   # statistics + document index
```

Python API:

```python
from termite import run_pipeline

stats = run_pipeline(
    input_dir="./raw_docs",
    output_dir="./output",
    verbose=True,
)
print(stats["compression_ratio"])
```

## Supported formats

| Format | Extensions | Parser | Recursive scan |
|--------|-----------|--------|----------------|
| Markdown | `.md` | Native | ✅ |
| PDF | `.pdf` | marker / pypdf fallback | ✅ |
| EPUB | `.epub` | Built-in (OPF spine) | ✅ |
| MOBI | `.mobi` | Built-in | ✅ |
| DOCX | `.docx` | marker | ✅ |
| Plain text | `.txt` | Native | ✅ |
| HTML | `.html`, `.htm` | marker | ✅ |

## Configuration

`config.yaml` (all keys optional — sensible defaults):

```yaml
pipeline:
  input_dir: "./raw_docs"
  output_dir: "./output"
  mode: "local"           # local | cloud
  max_file_size_mb: 256   # oversized inputs are skipped, not ingested

deduplication:
  similarity_threshold: 0.85   # Jaccard threshold for near-duplicates
  strategy: "smart_merge" # keep_first | keep_latest | smart_merge

cross_reference:
  enabled: true
  min_common_entities: 2
  max_refs_per_doc: 5

compression:
  remove_stopwords: true
  apply_stemming: true
  normalize_headers: true
  language: "auto"       # auto | en | es

marker:
  use_llm_extraction: true
  extract_metadata: true
```

Full reference: [docs/configuration.md](docs/configuration.md).

## How it works

```
Input documents
      │
      ▼
┌──────────────┐   ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
│  Ingestion   │──▶│   Parsing   │──▶│ Deduplication│──▶│ Entity graph │
│ size guards  │   │ marker/pdf │   │ SHA-256 +    │   │ + cross-ref  │
│ symlink-safe │   │ EPUB/HTML  │   │ Jaccard      │   │ injection    │
└──────────────┘   └─────────────┘   └──────────────┘   └──────┬───────┘
                                                               │
                                                               ▼
                       ┌──────────────────────────────────────────────┐
                       │ Cleaning: images/figures/links/attributions │
                       │ Compression: stopwords, stemming, headers   │
                       └───────────────────────┬──────────────────────┘
                                               ▼
                                  Atomic output: corpus + index
```

Details and design decisions: [docs/architecture.md](docs/architecture.md).

## Command-line interface

```text
termite [options]

  --input DIR       Input directory (required)
  --output DIR      Output directory
  --config FILE     Configuration file (default: config.yaml)
  --mode            local | cloud
  --stats           Print pipeline statistics
  --log-level       DEBUG | INFO | WARNING | ERROR | CRITICAL
  -v, --verbose     Verbose progress output
```

Exit codes: `0` success · `1` processing error / no documents found ·
`130` user interrupt. CLI reference: [docs/cli.md](docs/cli.md).

## Security and privacy

- **Local by default.** Processing happens on your machine.
- **Cloud mode is opt-in.** `--mode cloud` uploads document content to the
  Datalab API; consult your data-handling policy before enabling it. The
  API key is read from the `DATALAB_API_KEY` environment variable and is
  never stored in configuration files or code.
- **Hostile-input guards.** Recursive scanning never follows symlinks;
  oversized inputs and decompression-bomb EPUBs are rejected; EPUB member
  paths from the OPF spine are normalized and confined to the archive;
  XML is parsed with `defusedxml` when available.
- **No execution of document content.** Termite never executes code from
  ingested documents; output is plain Markdown written atomically.

Report vulnerabilities privately via
[SECURITY.md](SECURITY.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [CLI reference](docs/cli.md)
- [Python API](docs/python-api.md)
- [GPU acceleration (CUDA / ROCm)](docs/gpu-acceleration.md)
- [Performance and scaling](docs/performance.md)
- [RAG integration guide](docs/rag-integration.md)
- [Troubleshooting](docs/troubleshooting.md)

## Development

```bash
pip install -e ".[dev]"
pytest              # run the full suite (247 tests)
ruff check src tests
black --check src tests
```

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
