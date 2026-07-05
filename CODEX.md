# Executor Instructions

## Current bounded task

`V0-00 — repository boundary, contracts, provenance, CI, and canonical seed decision`

## Allowed

- governance and security documents;
- strict V0 contracts and JSON schemas;
- contract tests;
- CI, lint, type, compile, schema-drift, and secret-scanning gates;
- provenance manifests and import decisions.

## Forbidden

- exchange network adapters or write clients;
- credentials, wallets, signing, order submission, Testnet/Mainnet configuration;
- strategy signal logic, risk sizing, or automatic trading;
- historical archive copy or broad source import;
- modifications to `woshixiong/trade-os` Issue #47 files.

## Required checks

```text
python -m compileall -q src scripts tests
python scripts/export_schemas.py --check
python scripts/scan_secrets.py .
ruff check .
mypy src scripts
pytest -q
```

Never report a check as passed unless it was executed and observed.
