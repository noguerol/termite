# Troubleshooting

## Installation

### `ModuleNotFoundError: No module named 'termite'`

```bash
pip install -e .        # from a source checkout
# or
pip install termite
```

### `termite: command not found`

The scripts directory is not on `PATH`. Run `python -m termite ...` or
add your Python bin directory to `PATH`
(`python -m site --user-base`).

### PDF parsing quality is poor

Termite uses `marker-pdf` when installed; without it, PDFs fall back to
`pypdf` (no layout detection, no OCR). For scanned/image-only PDFs you
need OCR-capable parsing — install marker or use cloud mode.

## Pipeline runs

### `Documents parsed: 0`

- Input directory missing or empty — check the path (`--input`).
- Files are oversized: oversized files are **skipped with a warning**;
  raise `pipeline.max_file_size_mb` or shrink the input.
- Parse failures are logged per file; run with `--log-level DEBUG` to
  see each failure reason.

### `DATALAB_API_KEY is required for cloud mode`

Cloud mode requires the environment variable (never hardcode keys):

```bash
export DATALAB_API_KEY=...
```

### Compression did nothing (`compression_ratio ≈ 0`)

Lexical compression is **opt-in**: enable `remove_stopwords` and/or
`apply_stemming` in `config.yaml`. Stemming additionally requires
`pip install "termite[stemming]"`; without NLTK a warning is logged and
stemming is skipped.

### Spanish not being compressed as expected

Automatic detection may classify very short or mixed-language texts as
English. Force the language: `compression.language: "es"`.

### Dedup removed documents you expected to keep

Near-duplicate merging depends on `similarity_threshold`. Inspect with
`--log-level DEBUG`; lower `min_common_entities`/threshold, or use
strategy `keep_first` to see raw grouping.

### Cross-references look noisy

Raise `cross_reference.min_common_entities` (e.g. 3–4) and cap
`max_refs_per_doc`.

## GPU

See [gpu-acceleration.md](gpu-acceleration.md) for CUDA/ROCm issues
(device not detected, `hipErrorNoBinaryForGpu`, OOM, model loading).

## Getting more information

```bash
termite --input ... --output ... --log-level DEBUG -v
```

Log lines are prefixed with the module name
(`termite.pipeline.deduplication`, etc.), so you can isolate the stage.

## Reporting issues

Open an issue with:

1. Termite version (`termite --version`), Python version, OS.
2. Input formats and sizes (anonymized).
3. The statistics block and DEBUG log excerpt.
4. A minimal reproducer file if possible.
