# Contributing

Thanks for contributing to Termite! This document explains how to set up
a development environment and the quality bar we maintain.

## Development environment

```bash
git clone https://github.com/noguerol/termite.git
cd termite
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optional extras: `"marker"` (PDF layout parsing), `"spacy"` (NER),
`"stemming"` (Snowball stemmers), `"cloud"` (Datalab). `"all"` installs
everything.

## Quality gates

Every pull request must pass locally before review:

```bash
pytest                    # full suite (unit/integration/e2e/perf)
ruff check src tests      # lint (explicit rule set in pyproject.toml)
black --check src tests   # formatting
```

- **TDD**: add tests alongside behaviour changes; security-sensitive
  changes need adversarial tests (see `tests/unit/test_hardening.py`).
- Python ≥ 3.10 compatibility; no new mandatory dependencies without
  strong justification.
- Type hints on public functions; docstrings on classes and public
  methods.
- Commits: imperative, present-tense subject ("Add X", not "added X").

## Project layout

```
src/termite/          # library code (never import tests from src)
  pipeline/           # one module per pipeline stage
  utils/              # pure helpers
tests/
  unit/               # fast, single-component
  integration/        # multi-stage
  e2e/                # CLI level
  non_functional/     # performance and reliability budgets
docs/                 # user & integration documentation
```

## Pull request process

1. Fork the repo and branch from `main`.
2. Keep changes focused; one feature/fix per PR.
3. Update docs when behaviour or configuration changes.
4. Update `CHANGELOG.md` under *Unreleased*.
3. CI must be green (lint, multi-version test matrix).
4. A maintainer reviews; expect at least one review before merge.

## Reporting bugs

Use the issue template. Include: Termite version, Python version, OS,
input formats, the statistics block, and a DEBUG log excerpt
(`--log-level DEBUG`). **For security issues, follow
[SECURITY.md](SECURITY.md) instead.**

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
