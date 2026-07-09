# Executor Instructions

## Current bounded task

`V0-01A2 — no-network public observation ingress contract`

## Allowed

- governance and documentation updates for the V0-01A2 ceiling;
- a pure no-network public observation ingress/helper layer;
- caller-supplied exact public observation bytes only;
- A1 `validate_read_only_transport_entry()` checks for every accepted selection;
- `RawEventV0` authority binding using exact payload bytes, injected timestamps, injected monotonic time, connection ID, subscription ID, and receive sequence;
- optional Bronze payload persistence and manifest append through existing A0 `BronzeStore` / `ManifestWriter` authority only;
- deterministic A2 tests proving byte-exact identity, fail-closed public-only selection, unresolved rate-limit live-transport blocking, and absence of network/async transport capability.

## Forbidden

- HTTP or WebSocket clients, sockets, DNS, async runtime, live endpoint connection, polling, reconnect, heartbeat, health, backfill, or soak runtime;
- new runtime or development dependencies;
- resolving official numeric rate limits while `RATE_LIMIT_STATUS` remains `UNRESOLVED_OFFICIAL_LIMIT`;
- credentials, public account addresses, wallets, signing, nonces, exchange writes, order mutation, Testnet/Mainnet execution configuration;
- strategy candidates, AI recommendations, risk sizing, Silver normalization, dashboards, databases, cloud storage, or later V0 slices;
- raw operational payloads, logs, caches, databases, source archives, private/user/account data, secrets, or unredacted live observations in Git;
- modifications to `woshixiong/trade-os`.

## Required checks

```text
python -m compileall -q src scripts tests
python scripts/export_schemas.py --check
python scripts/scan_secrets.py .
ruff check .
mypy src scripts
pytest -q
pytest -q tests/test_v0_01a2_*.py
pytest -q tests/test_v0_01a1_transport_entry_gate.py tests/test_v0_01a1_source_envelope_contract.py tests/test_v0_01a1_fixture_admission.py
git diff --check
```

Never report a check as passed unless it was executed and observed.
