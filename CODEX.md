# Executor Instructions

## Current bounded task

`V0-01A3 — public read-only transport preflight contract`

## Allowed

- governance and documentation updates for the V0-01A3 ceiling;
- a pure public read-only transport preflight helper;
- source identity, environment, operation class, endpoint/operation allowlist, coin, interval, and capture-mode checks using the frozen public catalog;
- disabled-runtime default and fail-closed kill-switch semantics;
- credential absence, private/user/account absence, and no-write/no-execution proof;
- unresolved official rate-limit behavior proving live transport remains unauthorized;
- deterministic A3 tests proving public-only preflight acceptance, forbidden material rejection, and absence of network/async capability.

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
pytest -q tests/test_v0_01a3_transport_preflight_contract.py
pytest -q tests/test_v0_01a2_public_observation_ingress.py tests/test_v0_01a1_transport_entry_gate.py
git diff --check
```

Never report a check as passed unless it was executed and observed.
