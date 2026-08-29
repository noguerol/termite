# RAG Integration Guide

Termite-processed documents follow conventions that retrieval and
generation systems should respect to get the best results. This guide
explains the output format and recommended ingestion patterns.

## Output anatomy

| File | Purpose |
|---|---|
| `compressed_docs.md` | The knowledge base: all documents concatenated, one `# Title` section per source document, `---` separated. |
| `compressed_index.md` | Machine-readable statistics and document index. |

## Conventions in the corpus

1. **Header normalization.** Every source document header becomes at
   most `##` (H2). Chunk boundaries are not marked explicitly; chunks are
   contiguous paragraphs.
2. **Cross-reference comments.** Injected into each document's first
   chunk:

   ```markdown
   <!-- CROSS-REF: See also: Deployment Guide (docker, kubernetes) -->
   ```

   These are HTML comments: invisible when rendered, parseable by tools.
   Retrieval systems can expand context by following them.
3. **Stemming.** When `apply_stemming` is enabled, words appear in
   reduced form (`construction → constru` etc.). Search indexes should
   apply the same stemmer, or disable stemming for exact-match use cases.
4. **Code spans preserved.** Fenced and inline code are never
   compressed — exact-match retrieval of identifiers works.
5. **Removed artifacts.** Broken image/figure references, internal links
   and page references are removed; nothing references a file that does
   not exist in the corpus.

## Recommended ingestion patterns

### Long-context LLM (no vector DB)

Load `compressed_docs.md` directly into a long-context model, or split
on `---` (one chunk per original document) and select documents via
keyword/entity matching. Cross-reference comments tell the model which
documents are related.

### Hybrid lexical retrieval

For corpora that exceed the context window:

1. Split `compressed_docs.md` on `---` (document granularity), or by
   `##` headers.
2. Index with BM25 (or any BM25-compatible engine) — Termite output is
   BM25-friendly: stopwords removed, stems consistent.
3. Expand results through `CROSS-REF` comments (retrieval augmentation
   without embeddings).

### LLM prompt template

When answering from the corpus, tell the model:

> The knowledge base is compressed: function words may be missing,
> stems may be truncated, and `<!-- CROSS-REF -->` comments indicate
> related documents. Interpret stems and fragments accordingly.

## Multi-language corpora

- Automatic detection per text; `compression.language` can force one
  language for the whole corpus when mixed-language detection would be
  unreliable.
- Spanish stopword phrases (`sin embargo`, `por qué`, …) are handled as
  phrases; English/Spanish stopword sets and stemmers are separate.

## Verifying corpus integrity

After a pipeline run, check `compressed_index.md`: `Total Documents`,
`Original/Compressed Tokens`, and `Cross-References` should match
expectations. A large drop in parsed documents vs discovered indicates
inputs failing parsing (check logs at `--log-level DEBUG`).
