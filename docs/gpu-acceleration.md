# GPU Acceleration (CUDA / ROCm)

Termite uses GPU acceleration for **local parsing only** (marker-pdf and
its PyTorch models). Deduplication, entity processing and compression are
CPU-bound and unaffected by GPU configuration.

## Device selection

`MarkerParser` auto-detects the best device at construction time:

1. `torch.cuda.is_available()` → `cuda` (NVIDIA **or** AMD ROCm, which
   exposes GPUs through the CUDA-compatible API).
2. `torch.version.hip` set (ROCm build of PyTorch) with devices → `cuda`.
3. Otherwise → `cpu`.

Force CPU with `MarkerParser(force_cpu=True)` or by installing a CPU-only
PyTorch build. Environment variables (`CUDA_VISIBLE_DEVICES`,
`GPU_DEVICE_ORDINAL`) are honoured and **never overwritten** if already
set by the operator.

## NVIDIA

Install a CUDA-enabled PyTorch matching your driver:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## AMD (ROCm)

ROCm must be installed on the system first (`rocm-smi` to verify).
Then install ROCm-enabled PyTorch wheels, e.g.:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.2
```

Verify:

```python
import torch
print(torch.__version__)              # e.g. 2.9.1+rocm6.2
print(torch.cuda.is_available())     # True
print(torch.cuda.get_device_name(0))
```

Tested configurations (community reports):

| ROCm | PyTorch | GPU | Status |
|---|---|---|---|
| 6.2 | 2.9+rocm | ✅ |
| 7.x | 2.9+rocm | ✅ |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `torch.cuda.is_available() == False` | Driver/ROCm missing or version mismatch; reinstall the matching PyTorch wheel. |
| `hipErrorNoBinaryForGpu` | PyTorch ROCm build does not include kernels for your GPU; use the ROCm release matching your GPU family, or set `HSA_OVERRIDE_GFX_VERSION` (e.g. `11.0.0` for gfx1100). |
| OOM during parsing | Termite sets `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512`; for very large PDFs lower it or fall back to `pypdf` (uninstall/remove `marker-pdf` from the environment). |
| `No module named 'torchvision'` | `pip install torchvision --index-url ...` (must match torch build). |

## Notes

- GPU parsing loads models **once per process** and reuses them across
  documents; memory footprint stays stable.
- In `cloud` mode no GPU is required (parsing happens upstream).
- If marker is not installed at all, Termite falls back to
  CPU-only parsers (`pypdf`, built-in EPUB reader) regardless of GPU
  availability.
