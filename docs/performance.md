# Performance and Scaling

## Complexity summary

| Stage | Complexity | Notes |
|---|---|---|
| Discovery | O(files) | Symlink-safe scan; skips oversize files by `stat()` only. |
| Parsing | O(input bytes) | Dominated by marker models when installed (GPU recommended). |
| Exact dedup | O(total bytes) | One SHA-256 pass over normalized text per document. |
| Near-dedup pair pass | O(n² × set-ops) with precomputed sets | See scaling notes below. |
| Cross-references | O(Σ m_e²) worst case | Inverted index; Σ m_e² over entities, where m_e = docs containing entity e. |
| Compression | O(total tokens) | Linear; regex + per-token operations. |
| Output | O(output bytes) | Atomic writes. |

## Scaling notes

- **Corpora up to ~5 000 documents** run comfortably on a laptop; the
  full test suite (≈250 tests) runs in well under a second on a modern
  CPU (excluding heavy optional parsers).
- **Near-dedup is quadratic** in document count by design (it is
  exhaustive, deterministic). For very large corpora:
  - Partition the corpus by domain and run separate pipelines.
  - Raise `similarity_threshold` to prune candidates early.
  - Pre-hash/dedupe identical files at the filesystem level first.
- **Cross-reference graph**: a single boilerplate entity present in every
  document makes the inverted index expansion quadratic. Mitigation:
  raise `min_common_entities`, or remove over-common entities via a
  custom `EntityExtractor` whitelist.
- **Memory**: bounded by the largest document × number of parsed
  documents held in memory. `max_file_size_mb` caps the first factor.
  For very large corpora, partition the input directory and run
  multiple sequential invocations.

## Benchmarks (reference machine, CPU-only)

Indicative numbers from the non-functional test suite and smoke runs;
re-measure in your environment before capacity planning.

| Workload | Volume | Wall clock |
|---|---|---|
| Discovery | 1 000 files | < 0.1 s |
| Exact dedup | 1 000 docs | < 0.5 s |
| Near-dedup (trigrams, 100 docs) | 100 docs | < 1 s |
| Cross-refs | 200 docs | < 1 s |
| Compression | 100 KB mixed EN/ES | < 0.2 s |
| Full pipeline (text inputs, 10 docs) | ~2 KB docs | ≈ 50 ms |

PDF parsing with marker+torch dominates runtime by orders of magnitude
(GPU recommended for > 100 PDFs).

## Typical compression results

Termite targets **30–40% token reduction** on prose-heavy corpora with
`remove_stopwords` + `smart_merge`. Results vary by content:

- Repetitive/template corpora: 40–70% (deduplication dominates).
- Technical prose (EN/ES): 25–40%.
- Code-dense or already-compressed inputs: ~0% (code is protected).

The reported `compression_ratio` covers the **entire pipeline**
(deduplication + lexical compression measured against the pre-dedup
baseline).

## Tuning checklist

1. Choose the parser tier first (marker vs pypdf); it dominates cost.
2. `max_file_size_mb` — set slightly above your real maximum.
3. `similarity_threshold` — raise for speed, lower for recall.
4. `min_common_entities` — raise if cross-refs are too noisy.
5. Use `--log-level DEBUG` and the statistics block to find the
   expensive stage before optimizing.
