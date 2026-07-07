# Executor Instructions

## Current bounded task

`V0-01A0 — Bronze authority and offline replay foundation`

## Allowed

- governance updates for the V0-01A0 ceiling;
- versioned public-source catalog definitions;
- strict raw-observation, manifest-entry, and replay-report contracts;
- exact fixture/application payload hashing;
- local content-addressed immutable payload storage;
- append-only hash-linked manifests;
- deterministic offline replay and corruption/path-boundary tests;
- generated JSON schemas for the three A0 contracts.

## Forbidden

- HTTP or WebSocket clients and any live endpoint connection;
- new runtime or development dependencies;
- credentials, public account addresses, wallets, signing, exchange writes, order mutation, Testnet/Mainnet execution configuration;
- strategy candidates, AI recommendations, risk sizing, health/reconnect/backfill runtime, dashboards, databases, cloud storage, soak operation, or later V0 slices;
- modifications to `woshixiong/trade-os` or Issue #47 files.

## Required checks

```text
python -m compileall -q src scripts tests
python scripts/export_schemas.py --check
python scripts/scan_secrets.py .
ruff check .
mypy src scripts
pytest -q
git diff --check
```

Never report a check as passed unless it was executed and observed.
