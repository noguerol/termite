# Architecture

This document describes Termite's pipeline architecture, data model,
algorithms and the key design decisions behind them. It is written for
engineers who need to extend, integrate, or operate Termite at scale.

## Design goals

1. **Direct RAG without vector infrastructure.** Produce one canonical,
   compressed Markdown corpus per input set so that retrieval can be
   done by the LLM itself (long-context) or by trivial lexical tools,
   instead of embeddings + vector databases.
2. **Semantics-preserving compression.** Compression must be *lexical*
   (redundancy removal) and never *semantic* (no summarization, no
   paraphrasing). Technical terms, numbers, entities, and code must
   survive byte-for-byte where possible.
3. **Deterministic, auditable output.** Same input + configuration ⇒
   same output. Cross-references are machine-readable comments.
4. **Safe by construction.** Treat every input document as hostile:
   bounded memory, no execution, no path traversal, no shell.
5. **Progressive enhancement.** Core is pure Python with small
   dependencies; parsing/NER/stemming quality can be upgraded with
   optional extras (`marker`, `spacy`, `nltk`, `datalab`).

## Pipeline stages

`TermitePipeline.run()` orchestrates six phases (see
`src/termite/pipeline/pipeline.py`):

```
Discovery → Parsing → Deduplication → Entity graph → Compression → Output
```

### 1. Document discovery (`document_ingester.py`)

- Recursive, deterministic scan (`sorted()`) of the input directory for
  supported extensions.
- **Security controls:**
  - Symlinks are never followed (files or directories); symlink loops and
    out-of-tree ingestion are therefore impossible.
  - Directory identity tracking (resolved-path set) prevents rescanning
    through hardlinked/bind-mounted structures; recursion depth is capped.
  - `pipeline.max_file_size_mb` (default 256 MB) skips oversized files
    before any parsing — the primary memory-exhaustion guard.
- Output: sorted list of paths; duplicates by resolved path are skipped.

### 2. Parsing (`marker_parser.py`)

- **Local mode** (default): uses `marker-pdf` when installed (models
  loaded **once per process** and cached at class level; device selected
  by `get_device()`: CUDA → ROCm → CPU).
- **Fallback parsers** when marker is absent: `pypdf` for PDF, a built-in
  OPF/spine reader for EPUB, direct UTF-8 read for text formats.
- **Cloud mode**: sends documents to the Datalab API (explicit opt-in;
  API key from `DATALAB_API_KEY`, never hardcoded).
- **Error semantics:** parse failures raise
  `FileNotFoundError`/`DocumentParseError` — the pipeline logs and skips
  the file. Placeholder/placeholder-looking content is never ingested.
- Chunking: line-driven, semantically split at markdown headers, target
  `max_tokens=500` per chunk; token estimates at 4 chars/token.
- **EPUB hardening:** per-member size limit (64 MB) and total
  uncompressed-size budget before reading anything (decompression-bomb
  guard); OPF `href` paths are normalized (`posixpath.normpath`) and
  rejected when they escape the archive; XML parsed via `defusedxml`
  when available.
- Document IDs: SHA-256 of the canonical path, first 12 hex chars
  (collision-safe for corpora up to astronomically large sizes; MD5 is
  not used anywhere).

### 3. Deduplication (`deduplication.py`)

- **Exact duplicates**: SHA-256 over normalized text
  (lowercase → NFKC → punctuation removed → whitespace collapsed).
- **Near-duplicates**: Jaccard similarity over character trigrams,
  threshold configurable (`similarity_threshold`, default 0.85).
- Strategies:
  - `keep_first` / `keep_latest` — keep the first/last occurrence.
  - `smart_merge` — groups exact **and** near duplicates transitively by
    grouping pass, then merges unique chunks across each group.
- Performance: signatures and n-gram sets are computed **once per
  document** and reused across all stages of one call. (Previously each
  pair recomputed both documents' features, an O(n³) path; now the pair
  phase is a pure precomputed-set comparison.)

### 4. Entity graph and cross-references (`entity_extractor.py`, `entity_graph.py`)

- Entity extraction: spaCy NER (`ORG, PRODUCT, LAW, GPE, PERSON, NORP,
  FAC, EVENT, WORK_OF_ART, LANGUAGE`) when installed; always available
  technical-term whitelist matched with a **compiled word-boundary regex
  alternation** (no substring false positives like `api` inside
  `rapid`, and O(text) instead of O(terms × text)).
- Graph build uses an **inverted index** (entity → documents): candidate
  pairs are those sharing at least one entity, with shared-entity counts
  accumulated in a counter; only candidates pass the full
  set-intersection strength computation. Typical corpora process near
  linearly; worst case remains quadratic (documented in
  performance.md).
- References above `min_common_entities` are scored
  (`shared / union`), sorted by strength (ties deterministic by document
  order), capped at `max_refs_per_doc`, and injected in-place into each
  document's first chunk as:

  ```markdown
  <!-- CROSS-REF: See also: Deployment Guide (docker, kubernetes) -->
  ```

### 4b. Compression (`compression.py`, `cleaner.py`)

- **Cleaning** (always applied first): removes image/figure references,
  internal `.md` links, page references, photo attributions, and empty
  markdown links. Regex-based, documented in `cleaner.py`.
- **Language resolution**: `compression.language` (`auto` | `en` | `es`);
  `auto` detects per text (character/word/endings heuristics),
  defaulting to English for undetermined text.
- **Stopword removal** (optional): per-language token sets plus
  phrase-level Spanish stopwords (e.g. *sin embargo*, *por qué*) removed
  via a dedicated longest-first regex pass. `filter_stopwords()` accepts
  a `whitelist` to protect terms.
- **Stemming** (optional): Snowball (ES/EN) via NLTK when installed
  (`pip install "termite[stemming]"`); a warning is logged when
  stemming is enabled without NLTK, and the step is skipped instead of
  failing silently.
- **Code preservation**: fenced and inline code spans are split out and
  re-inserted verbatim; code is never compressed.
- Headers normalized to `max_level=2` for uniform document structure.

### 5. Output (`output_generator.py`)

- Unified corpus (`compressed_docs.md`) + index
  (`compressed_index.md`) or per-document files
  (`unified_output=False`).
- **Atomic writes**: temp file + `os.replace()`, so consumers never
  observe partially written output and failures don't leave truncated
  files.
- Per-document filenames are sanitized (allowlist `[A-Za-z0-9_-]`,
  length-capped, traversal-proof).

## Data model (`models.py`)

| Model | Role |
|---|---|
| `ParsedDocument` | doc_id, source_file, chunks, metadata, extraction_timestamp (UTC-aware) |
| `DocumentChunk` | chunk_id, content, token_count, metadata |
| `DeduplicationResult` | counts + ratio of a dedup pass |
| `EntityCrossReference` | source/target doc ids, shared entities, strength ∈ [0,1] |
| `CompressionResult` | token accounting + cross-refs + dedup result |
| `TermiteConfig` (+ sub-configs) | Pydantic-validated configuration; `max_file_size_mb > 0`, thresholds bounded |

## Module map

```
src/termite/
├── cli.py / __main__.py      # CLI entry point, logging setup, exit codes
├── config.py                 # pydantic settings (TermiteConfig)
├── models.py                   # data models
├── pipeline/
│   ├── pipeline.py             # orchestrator (TermitePipeline, run_pipeline)
│   ├── document_ingester.py  # discovery + security scanning
│   ├── marker_parser.py        # parsing (marker/pdf/epub/cloud) + hardening
│   ├── deduplication.py        # exact + near dedup
│   ├── entity_extractor.py     # NER + technical whitelist
│   ├── entity_graph.py         # inverted-index cross-reference graph
│   ├── compression.py          # lexical compression, EN/ES
│   ├── cleaner.py              # reference/artifact cleaning
│   └── output_generator.py     # atomic writers + index
└── utils/
    ├── normalization.py        # whitespace/unicode/n-grams/Jaccard
    └── metrics.py              # token estimation, ratios
```

## Design decisions (FAQ)

- **Why Jaccard trigrams instead of MinHash/LSH?** Deterministic,
  dependency-free, and exact — corpora fit comfortably in RAM; LLM
  corpora are typically thousands of documents, where exact pairwise
  comparison is fast enough and gives reproducible results.
- **Why not summarization?** Summarization destroys precisely the
  content RAG needs. Termite removes only *redundant* signal.
- **Why chunk at ~500 tokens?** Matches typical LLM citation granularity
  and keeps every chunk self-contained; downstream tools can re-chunk
  cheaply.
- **Why entity comments in-band?** Cross-references travel with the
  document and are machine-parseable (`<!-- CROSS-REF: ... -->`) yet
  invisible in rendered Markdown.
