# Executor Instructions

## Repository state

```text
LAST_COMPLETED_SLICE: V0-01A5-OFFLINE-CANDLE-PAYLOAD-EXTRACTION-CONTRACT
ACTIVE_IMPLEMENTATION_SLICE: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
ACTIVE_IMPLEMENTATION_WRITE_LEASE: BOUNDED
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
```

## Current bounded task

`V0-01A6 — OFFLINE_CANDLE_CROSS_SOURCE_RECONCILIATION_CONTRACT`

A6 accepts only independently revalidated exact A5 WebSocket and Info candle extraction authorities. It creates a deterministic typed pairwise comparison report over the union of A5 logical candle keys. It is not a collector, transport, Bronze writer, normalizer, Silver task, finality or revision engine, strategy task, or execution path.

## Allowed files

- `README.md`;
- `CODEX.md`;
- `docs/V0_01_SCOPE.md`;
- `docs/architecture/V0_01_DATA_PLANE.md`;
- `src/trader_assist_v0/contracts/candle_reconciliation.py`;
- `src/trader_assist_v0/contracts/__init__.py`;
- `src/trader_assist_v0/data/candle_reconciler.py`;
- `scripts/export_schemas.py`;
- `schemas/v0/CandleCrossSourceReconciliationV0.schema.json`;
- `tests/test_v0_01a6_offline_candle_cross_source_reconciliation_contract.py`.

## Required behavior

- require exact `CandlePayloadExtractionV0` inputs with frozen WS and Info roles;
- independently revalidate both A5 extraction hashes, nested candle authorities, endpoint, operation, and envelope shape;
- require identical source, coin, and interval identities;
- use each A5 `candle_logical_key` as the sole cross-source identity;
- compare the logical-key union in `(open_time_ms, candle_logical_key)` order;
- compare only close time, OHLC, base volume, and trade count in the frozen field order;
- embed both complete A5 extraction authorities while retaining matching scalar event/hash authority;
- derive comparisons, source authority, counts, identity, and the report hash only from those two exact extractions through one deterministic contract-layer authority;
- reconstruct the complete logical-key union during every report validation and reject coherently rehashed omissions, injections, substitutions, or membership changes;
- emit only `MATCH`, `CONFLICT`, `WS_ONLY`, and `INFO_ONLY` with exact counts and a domain-separated report hash covering both complete extractions;
- support `AuthorityClass.model_validate_json(...)` as the sole A6 raw JSON authority entrypoint and require its input bytes to equal `canonical_json_bytes(authority)` exactly;
- reject duplicate object keys at every depth, `-0`, float/exponent/non-finite tokens, non-UTF-8/BOM input, alternate encodings, truncation, trailing material, and every other noncanonical raw representation before Pydantic validation;
- support decoded Python `model_validate`, base-class `model_validate`, `TypeAdapter.validate_python`, and core `validate_python` paths as authentication of the current decoded representation only, without claiming raw-wire provenance;
- fail closed on inherited/core JSON, string, and partial-validation paths; they are not alternative raw authority entrypoints;
- keep generated Schema root WS/Info extraction roles, comparison role/status, required embedded A5 fields, integer-difference value kinds, and portable absolute-end patterns in parity with runtime;
- keep Schema validation structural and JSON-Schema-expressible only; runtime remains authoritative for hashes, exact A5 authority, membership, ordering, counts, differences, and complete logical-key union proof;
- allow empty/empty inputs without sentinel/default evidence;
- keep tolerance, source priority, latest-wins, finality, revisions, canonical winner, normalization, and Silver promotion out of scope.

## Forbidden

- modifications to A5 contracts/extractor, source catalog code/documentation, `events.py`, `ingress.py`, `bronze.py`, or `replay.py`;
- modifications to existing tests, existing schemas, fixtures, dependencies, lockfiles, `pyproject.toml`, or CI workflows;
- HTTP or WebSocket clients, sockets, DNS, async runtime, event loop, live endpoint connection, polling, reconnect, heartbeat, health, backfill, REST request execution, or soak runtime;
- payload parsing or reading payload bytes from `payload_ref` or any filesystem path;
- Bronze or manifest writes, database or cloud storage;
- numeric rate-limit values or a transition away from `UNRESOLVED_OFFICIAL_LIMIT`;
- credentials, account addresses, wallets, signing, nonces, exchange writes, order mutation, Testnet/Mainnet execution configuration;
- tolerance, latest-wins, revision ordering, finality inference, source priority, or canonical winner selection;
- `NormalizedEventV0` emission, Silver normalization/persistence, strategy candidates, AI recommendations, risk sizing, dashboards, or later V0 slices;
- raw operational payloads, logs, caches, databases, source archives, private/user/account data, secrets, or unredacted live observations in Git;
- modifications to `woshixiong/trade-os`.

## Required checks

```text
python -m compileall -q src scripts tests
python scripts/export_schemas.py
python scripts/export_schemas.py --check
python scripts/scan_secrets.py .
ruff check .
mypy src scripts
pytest -q tests/test_v0_01a6_offline_candle_cross_source_reconciliation_contract.py
pytest -q tests/test_v0_01a5_candle_payload_extractor_contract.py
pytest -q
git diff --check
```

The PR must remain Draft until exact-head CI succeeds and external independent review passes. Mark Ready and merge require separate project-control authorization. Never report a check as passed unless it was executed and observed.
