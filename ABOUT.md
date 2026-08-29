# About Termite

**Termite** is an open-source document compression and structuring tool
that turns raw document collections (PDF, EPUB, MOBI, DOCX, TXT, HTML,
MD) into a **token-efficient, deduplicated, cross-referenced Markdown
corpus for LLM ingestion** — enabling direct RAG without vector
databases.

## Why it exists

Retrieval-augmented generation usually means embeddings, vector
databases, sync pipelines and chunking heuristics that break citation
provenance. Termite takes the opposite approach: keep everything in one
readable artifact. Instead of semantic summarization (which destroys
the content RAG needs), Termite removes only *redundancy* — duplicate
documents, boilerplate, stopword noise, dead references — while
preserving every entity, number, and technical term, and adding
machine-readable cross-links between related documents.

The result: a corpus small enough to sit in a long-context window,
cross-linked internally, BM25-friendly, and readable by humans — with
zero vector-database infrastructure.

## What makes it different

- **Direct RAG without a vector DB** — one Markdown corpus, optionally
  loaded whole into a long-context model, or split on document
  boundaries for trivial lexical retrieval.
- **Semantics-preserving compression** — redundancy removal, never
  summarization; code spans untouched; ~30–40% token reduction typical.
- **Entity cross-reference graph** — spaCy NER + curated technical
  whitelist; related documents are linked in-band
  (`<!-- CROSS-REF: … -->`).
- **Enterprise-grade hardening** — hostile-input model: size limits,
  decompression-bomb guards, symlink-safe scanning, atomic writes,
  `defusedxml`, no shell, environment-only credentials.
- **Multi-language** — English and Spanish first-class (language-aware
  stopwords, phrases, stemmers, detection).
- **GPU-ready parsing** — CUDA and AMD ROCm auto-detection for the
  marker-based parser.

## Project facts

| | |
|---|---|
| License | MIT |
| Python | 3.10 – 3.13 |
| Install | `pip install termite` (when published) |
| Modes | Local parsing (default) or opt-in cloud (Datalab) |
| Output | `compressed_docs.md` + `compressed_index.md` |
| Docs | `docs/` — architecture, configuration, CLI, API, GPU, performance, RAG integration |

## Roadmap highlights

- Packaging on PyPI (`termite`) with signed releases.
- Additional language support (DE/FR/PT) with the same hardening bar.
- Pluggable parser backends (Docling, Unstructured).
- Incremental/corporation-scale dedup (prefiltering, optional MinHash
  approximate mode behind an explicit flag).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the code of conduct. Security
vulnerabilities: report privately per [SECURITY.md](SECURITY.md).
