# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/); the
project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-04-26

Security/enterprise hardening release (public release).

### Security

- Document discovery never follows symlinks; recursion depth capped;
  directory-identity tracking prevents re-scans via link structures.
- New `pipeline.max_file_size_mb` limit (default 256 MB): oversized
  files are skipped instead of ingested.
- EPUB extraction hardening: per-member and total uncompressed-size
  limits (decompression-bomb guard), OPF member paths normalized and
  confined to the archive, malformed archives raise `DocumentParseError`.
- XML parsing uses `defusedxml` when available (XXE/entity-attack
  protection) with stdlib fallback under enforced size limits.
- Document identifiers now SHA-256-based (no weak-hash usage).
- Parse failures raise `FileNotFoundError`/`DocumentParseError` instead
  of silently ingesting placeholder text.
- Output writes are atomic (temp file + rename); sanitized output
  filenames cannot traverse directories.
- Cloud API keys read exclusively from `DATALAB_API_KEY`; never stored
  or logged.
- GPU environment variables are only defaulted, never overridden;
  `force_cpu=True` is now honored everywhere.

### Performance

- marker parsing models loaded once per process and reused (previously
  reloaded for every document).
- Deduplication computes signatures and n-grams once per document;
  `smart_merge` no longer recomputes features per pair (was cubic).
- Cross-reference graph built via inverted index candidate discovery
  instead of full pairwise set intersections.
- Technical-term extraction uses compiled word-boundary regex
  alternation (fixes substring false positives, e.g. `api` in `rapid`).
- Removed double deduplication in the pipeline → output-generator path.

### Fixed

- Pipeline statistics now report `original_tokens` measured **before**
  deduplication and correct `cross_references_created` counts.
- `compression.language` configuration option implemented (`auto`/`en`/`es`).
- Stopword whitelist parameter is honored in `filter_stopwords`;
  multi-word Spanish stopword phrases (`sin embargo`, `por qué`, …) are
  removed correctly.
- Spanish stemming now works: NLTK declared via `termite[stemming]` extra
  (previously an undeclared dependency; silent no-op is now a logged
  warning).
- Extraction timestamps are timezone-aware (UTC).
- `py.typed` included so type information ships with the package.

### Quality

- Explicit, deterministic ruff rule set in `pyproject.toml`; source and
  tests pass `ruff check` and `black`.
- Logging (`logging`, module loggers) throughout the library; CLI gains
  `--log-level`.
- 15 new hardening tests (symlink safety, size limits, EPUB bombs,
  whitelists, language forcing, atomic writes).

## [1.1.0-beta] — 2026-04-26

- Multi-language compression (English + Spanish) with automatic
  language detection.
- EPUB/MOBI support; recursive directory scanning.
- `DocumentCleaner` module (removes broken image/figure/image references).
- AMD GPU (ROCm) support; pypdf fallback for PDF parsing.

## [1.0.0] — 2026-04-25

- Initial release: parsing → deduplication → entity graph → lexical
  compression → output pipeline; CLI and YAML configuration.
