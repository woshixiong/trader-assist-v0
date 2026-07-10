# Executor Instructions

## Repository state

```text
LAST_COMPLETED_SLICE: V0-01A4-OFFICIAL-RATE-LIMIT-AUTHORITY-FREEZE
ACTIVE_IMPLEMENTATION_SLICE: V0-01A5-OFFLINE-CANDLE-PAYLOAD-EXTRACTION-CONTRACT
ACTIVE_IMPLEMENTATION_WRITE_LEASE: BOUNDED
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
```

## Current bounded task

`V0-01A5 — OFFLINE_CANDLE_PAYLOAD_EXTRACTION_CONTRACT`

A5 accepts only an exact `RawEventV0` and caller-supplied exact matching candle payload bytes. It creates a deterministic typed extraction result. It is not a collector, transport, Bronze writer, normalizer, Silver task, reconciliation engine, strategy task, or execution path.

## Allowed files

- `README.md`;
- `CODEX.md`;
- `docs/V0_01_SCOPE.md`;
- `docs/V0_01_OFFICIAL_SOURCE_CATALOG.md`;
- `docs/architecture/V0_01_DATA_PLANE.md`;
- `src/trader_assist_v0/contracts/candles.py`;
- `src/trader_assist_v0/contracts/__init__.py`;
- `src/trader_assist_v0/data/candle_extractor.py`;
- `scripts/export_schemas.py`;
- `schemas/v0/CandlePayloadExtractionV0.schema.json`;
- `tests/test_v0_01a5_candle_payload_extractor_contract.py`.

## Required behavior

- support only `hl-ws-mainnet-public/candle` and `hl-info-mainnet-public/candleSnapshot`;
- bind exact payload hash and size to the supplied exact `RawEventV0`;
- accept frozen WebSocket `data:Candle` and `data:Candle[]` shapes plus Info `Candle[]`;
- reject malformed JSON, duplicate keys, invalid UTF-8, BOM, non-finite numbers, missing/extra candle fields, wrong source selection, and coin/interval mismatches;
- parse numeric candle fields without binary-float conversion;
- create deterministic logical candle keys and extraction hashes;
- preserve payload order and allow an empty array without sentinel/default events;
- keep candle finality, revisions, reconciliation, gaps, backfill, normalization, and Silver promotion out of scope.

## Forbidden

- modifications to `events.py`, `source_catalog.py`, `ingress.py`, `bronze.py`, or `replay.py`;
- modifications to existing tests, existing schemas, fixtures, dependencies, lockfiles, `pyproject.toml`, or CI workflows;
- HTTP or WebSocket clients, sockets, DNS, async runtime, event loop, live endpoint connection, polling, reconnect, heartbeat, health, backfill, REST request execution, or soak runtime;
- reading payload bytes from `payload_ref` or any filesystem path;
- Bronze or manifest writes, database or cloud storage;
- numeric rate-limit values or a transition away from `UNRESOLVED_OFFICIAL_LIMIT`;
- credentials, account addresses, wallets, signing, nonces, exchange writes, order mutation, Testnet/Mainnet execution configuration;
- `NormalizedEventV0` emission, Silver normalization, strategy candidates, AI recommendations, risk sizing, dashboards, or later V0 slices;
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
pytest -q tests/test_v0_01a5_candle_payload_extractor_contract.py
pytest -q tests/test_v0_01a0_source_catalog.py tests/test_v0_01a0_bronze_storage.py tests/test_v0_01a1_source_envelope_contract.py tests/test_v0_01a2_public_observation_ingress.py tests/test_v0_01a3_transport_preflight_contract.py tests/test_v0_01a4_rate_limit_authority_contract.py
git diff --check
```

The PR must remain Draft until exact-head CI succeeds and external independent review passes. Mark Ready and merge require separate project-control authorization. Never report a check as passed unless it was executed and observed.
