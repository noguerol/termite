# Configuration Reference

Termite reads configuration from a YAML file (default `config.yaml`,
override with `--config`). Every key is optional and falls back to the
documented default. CLI flags override file values. All values are
validated with pydantic at load time — invalid configurations fail fast
with a clear error instead of misbehaving at runtime.

## `pipeline`

| Key | Type | Default | Description |
|---|---|---|---|
| `input_dir` | path | `./raw_docs` | Directory scanned recursively for documents. |
| `output_dir` | path | `./output` | Where the corpus and index are written. |
| `mode` | `local` \| `cloud` | `local` | Parser backend. `cloud` uploads documents to the Datalab API — see security notes. |
| `max_file_size_mb` | float > 0 | `256` | Files larger than this are skipped (logged at WARNING). Guards against memory exhaustion and decompression-bomb archives. |

## `deduplication`

| Key | Type | Default | Description |
|---|---|---|---|
| `similarity_threshold` | float 0.0–1.0 | `0.85` | Jaccard similarity (character trigrams) above which documents are considered near-duplicates. |
| `strategy` | `keep_first` \| `keep_latest` \| `smart_merge` | `smart_merge` | How duplicate groups are resolved. `smart_merge` additionally merges near-duplicate documents, keeping the union of unique chunks. |

Choosing a threshold: `0.9+` catches near-identical documents
(templates, re-exports); `0.7–0.85` catches strong rewrites but risks
merging genuinely distinct documents sharing boilerplate. Defaults are
tuned for technical documentation.

## `cross_reference`

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Build the entity graph and inject cross-reference comments. |
| `min_common_entities` | int ≥ 1 | `2` | Minimum shared entities for two documents to be linked. |
| `max_refs_per_doc` | int ≥ 1 | `5` | Maximum injected references per document. |

## `compression`

| Key | Type | Default | Description |
|---|---|---|---|
| `remove_stopwords` | bool | `false` | Remove language-specific stopwords (EN/ES lists built in; Spanish phrases handled). Code spans are never modified. |
| `apply_stemming` | bool | `false` | Reduce words to stems using Snowball (requires `pip install "termite[stemming]"`; skipped with a warning if NLTK is missing). |
| `normalize_headers` | bool | `true` | Collapse Markdown headers to at most H2. |
| `language` | `auto` \| `en` \| `es` | `auto` | Force the compression language, or detect per text. |

## `marker`

| Key | Type | Default | Description |
|---|---|---|---|
| `use_llm_extraction` | bool | `true` | Passed through to marker (layout extraction quality). |
| `extract_metadata` | bool | `true` | Extract title/author metadata when the parser provides it. |

## Environment variables

| Variable | Purpose |
|---|---|
| `DATALAB_API_KEY` | Credential for `mode: cloud`. Never store it in `config.yaml` or in source control. |

## Precedence

CLI flags (`--input/--output/--mode/--log-level`) override the
configuration file; configuration-file values override defaults. The
effective configuration is logged at DEBUG level.

## Example: aggressive compression

```yaml
pipeline:
  input_dir: ./corpus
  output_dir: ./dist-corpus
  max_file_size_mb: 64

deduplication:
  similarity_threshold: 0.85
  strategy: smart_merge

compression:
  remove_stopwords: true
  apply_stemming: true
  normalize_headers: true
  language: auto

cross_reference:
  enabled: true
  min_common_entities: 3
  max_refs_per_doc: 8
```
