# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities **privately** by opening a
GitHub Security Advisory (private report) on this repository, or by
emailing the maintainer contact listed in the repository's GitHub
"About" section.

**Do not open a public issue for security vulnerabilities.**

We aim to:

- Acknowledge reports within **3 business days**.
- Provide a fix or mitigation plan within **30 days** for confirmed
  vulnerabilities.
- Publish a security advisory and a patched release for anything
  user-impacting.

## Supported versions

| Version | Supported |
|---|---|
| 1.x (latest minor) | ✅ |
| < 1.0 | ❌ (pre-release) |

## Security model

Termite processes documents that may come from **untrusted sources**.
Threat model assumptions and mitigations:

| Threat | Mitigation |
|---|---|
| Path traversal via document content/metadata | Output filenames are allowlist-sanitized; no content-derived paths are used for writing. |
| Symlink loops / out-of-tree ingestion | Discovery never follows symlinks; directory identities tracked. |
| Oversized inputs (memory exhaustion) | `max_file_size_mb` skip policy (default 256 MB). |
| EPUB decompression bombs | Declared and actual per-member and total-extract limits enforced; oversized members are rejected. |
| XML entity attacks (XXE/billion laughs) | EPUB/XML parsed with `defusedxml` when available, stdlib fallback with size limits enforced. |
| Shell injection | No shell is ever invoked; all file handling via Python APIs. |
| Partial output files | Atomic write (temp + rename); failed runs never leave truncated files. |
| Credential leakage | API keys are only read from the environment (`DATALAB_API_KEY`); never stored in config files, code, or logs. |
| Data exfiltration | Local processing by default. Cloud mode (`--mode cloud`) uploads documents to the Datalab API and is strictly opt-in. |

## Hardening expectations for operators

- Run Termite with the least filesystem privileges needed (read-only
  input, write access only to the output directory).
- Keep cloud mode disabled unless a data policy explicitly permits it.
- Pin versions in production (`termite==1.1.*`) and watch the changelog.

## Vulnerability history

See [CHANGELOG.md](CHANGELOG.md) security entries.
