# Contributing

Eval Ground Truth Lab welcomes focused fixes, validators, adapters, synthetic
datasets, and evidence tooling under Apache-2.0.

## Local setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt -e .
.venv/bin/python -m pytest tests -q --tb=short
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Changes to gates need a positive test and a seeded failure test. Dataset changes
must remain synthetic, preserve provenance metadata, update the semantic hash,
and must not include user data, secrets, production URLs, or credentials.

Do not commit generated live claims. A canonical external-system result needs a
pinned component revision or image digest, the exact command/environment label,
machine-readable output, and a verified evidence manifest.

Pull requests should be small enough to review, update relevant documentation,
and include the commands and outcomes used for verification.
