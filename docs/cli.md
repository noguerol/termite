# CLI Reference

```text
termite [options]
```

## Options

| Flag | Type | Description |
|---|---|---|
| `--input DIR` | directory | Input directory containing source documents. |
| `--output DIR` | directory | Output directory for the compressed corpus. |
| `--config FILE` | path | Configuration file (default `./config.yaml`). |
| `--mode {local,cloud}` | choice | Override parsing mode. `cloud` requires `DATALAB_API_KEY`. |
| `--stats` | flag | Print a statistics block after processing. |
| `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}` | choice | Library log level. Default `WARNING`; `--verbose` implies `INFO`. |
| `-v, --verbose` | flag | Human-readable progress output (implies INFO logging). |
| `--version` | flag | Print version and exit. |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | Processing error, or no documents were found to process. |
| `130` | Interrupted by user (`Ctrl-C`). |

## Examples

```bash
# Typical run
termite --input ./raw_docs --output ./output --stats -v

# Custom config
termite --config prod-config.yaml --stats

# Cloud mode (reads DATALAB_API_KEY)
export DATALAB_API_KEY=...
termite --input ./raw_docs --output ./output --mode cloud

# Debugging a single problematic file set
termite --input ./debug-in --output ./debug-out --log-level DEBUG -v
```

## Output files

| File | Description |
|---|---|
| `compressed_docs.md` | Unified corpus: one `# Title` section per document, `---` separated. |
| `compressed_index.md` | Statistics (documents, chunks, tokens, ratios, cross-refs) + document index. |

All output is written atomically (temp file + rename); readers never
observe partial files.
