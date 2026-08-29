# AGENTS.md — AI Agent Guide

> **For AI agents**: this file provides guidance for working on the
> Termite codebase. Keep this file accurate when the architecture changes.

## Project summary

Termite converts raw documents (PDF, EPUB, MOBI, DOCX, TXT, HTML, MD)
into a compressed, deduplicated, cross-referenced Markdown corpus for
direct LLM ingestion (RAG without vector databases).

- Package: `termite` (src-layout, Python ≥ 3.10)
- License: MIT

## Quick commands

```bash
pip install -e ".[dev]"          # dev environment
pytest                           # full suite
pytest tests/unit -q             # unit tests only
ruff check src tests && black --check src tests
python -m termite --input DIR --output DIR --stats -v   # CLI
```

## Architecture (pipeline)

```
Discovery → Parsing → Deduplication → Entity graph → Compression → Output
```

| Stage | Module | Key class |
|---|---|---|
| Discovery | `src/termite/pipeline/document_ingester.py` | `DocumentIngester` |
| Parsing | `src/termite/pipeline/marker_parser.py` | `MarkerParser` |
| Dedup | `src/termite/pipeline/deduplication.py` | `Deduplicator` |
| Entities | `src/termite/pipeline/entity_extractor.py` | `EntityExtractor` |
| Cross-refs | `src/termite/pipeline/entity_graph.py` | `EntityGraph` |
| Compression | `src/termite/pipeline/compression.py`, `cleaner.py` | `LexicalCompressor`, `DocumentCleaner` |
| Output | `src/termite/pipeline/output_generator.py` | `OutputGenerator` |
| Orchestration | `src/termite/pipeline/pipeline.py` | `TermitePipeline`, `run_pipeline` |

Data models live in `src/termite/models.py`; configuration in
`src/termite/config.py` (pydantic, YAML-backed).

## Invariants (do not break)

1. **Never follow symlinks** during discovery (security requirement).
2. **Never ingest placeholder text** for failed parses — raise and skip.
3. Parse errors surface as `FileNotFoundError` / `DocumentParseError`;
   the pipeline logs per-document failures and continues.
4. Archive extraction keeps size limits (EPUB/decompression-bomb guards)
   and never trusts archive-member paths verbatim.
5. API keys come only from the environment (`DATALAB_API_KEY`); never
   hardcode or log credentials.
6. Compression never modifies fenced/inline code spans.
7. Output filenames are allowlist-sanitized; writes are atomic.
8. `compression.language` (`auto|en|es`) and `pipeline.max_file_size_mb`
   are validated configuration; keep bounds enforced.

## Testing expectations

- Every bug fix needs a regression test; security-sensitive changes need
  adversarial tests (`tests/unit/test_hardening.py`).
- Tests are grouped: `unit/`, `integration/`, `e2e/`, `non_functional/`.
- `pytest` must pass; keep lint/format green (`ruff`, `black`).
- Performance budgets exist in `tests/non_functional/` — do not
  introduce quadratic regressions in already-linear stages.

## Style

- black (line-length 100), ruff (explicit rule set in `pyproject.toml`).
- Type hints on public APIs; Google-style docstrings.
- Library code logs via `logging.getLogger(__name__)`; never `print`
  from library code (CLI prints progress).

## Adding features

1. Read the relevant module and `docs/architecture.md`.
2. Add/extend tests first (TDD).
3. Keep changes minimal and focused; update docs + CHANGELOG.
4. Run `pytest`, `ruff check`, `black --check` before proposing changes.

## Security

See [SECURITY.md](SECURITY.md). Report vulnerabilities privately; never
open public security issues.
