# V0-01 Official Public Source Catalog

Catalog version: `hyperliquid-public-mainnet.0.1.0`

Fixed source catalog hash: `0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7`

Catalog-entry hash domain: `trader-assist-v0/source-catalog-entry/v1`

Officially verified: `2026-07-07`

The single executable catalog authority is `src/trader_assist_v0/contracts/source_catalog.py`. It depends only on the standard library and `contracts/common.py`, so `RawEventV0` can validate catalog authority without a contracts-to-data import cycle. `src/trader_assist_v0/data/source_catalog.py` is a compatibility re-export and does not define a second catalog.

A0 records public interface facts only and does not connect to any endpoint. A1 freezes public transport-entry contracts only and still does not connect to any endpoint. A2 uses those contracts for caller-supplied public observation bytes and still does not connect to any endpoint. A3 freezes future public read-only transport preflight checks and still does not connect to any endpoint. A4 completed the official-only rate-limit authority freeze and still does not connect to any endpoint.

## Coverage

Coins: `ETH`, `BTC`.

WebSocket definitions: `trades`, `l2Book`, `bbo`, `activeAssetCtx`, `allMids`, `candle`.

Info definitions: `meta`, `metaAndAssetCtxs`, `allMids`, `l2Book`, `candleSnapshot`, `fundingHistory`, `predictedFundings`.

Runtime candle interval allowlist: `1m`, `3m`, `5m`, `15m`, `1h`.

## RawEvent binding

Each A0/A2 RawEvent binds and revalidates:

- source ID, catalog version, and fixed catalog hash;
- endpoint ID and operation type;
- catalog-entry hash;
- coin and candle interval selection;
- endpoint kind and capture mode;
- connection, subscription, collector-local receive sequence, and payload hash.

WebSocket entries require `WS_TEXT_UTF8_APPLICATION_PAYLOAD`. Info entries require `HTTP_RESPONSE_BODY`. Unknown endpoints or operations, `/exchange`, Testnet, unsupported coins or intervals, missing required coins, and coins supplied to non-coin operations are rejected.

A0, A1, A2, A3, and A4 do not parse raw payload fields. `source_event_time`, `source_publish_time`, `revision_time`, `source_native_id`, and `source_native_cursor` must all be `None` until a later separately reviewed extractor contract exists.

## Frozen semantics

- `l2Book`: `FULL_SNAPSHOT_NOT_DELTA`.
- `trades`: batched stream, no documented source sequence.
- `bbo`: change-only stream, no documented source sequence.
- `activeAssetCtx`: current observation, no documented source timestamp.
- `allMids`: current map observation, no documented source timestamp.
- `candle`: mutable current bar; logical key is coin, interval, and open time.

## A3 public read-only transport preflight

A3 freezes only future public read-only collector configuration preflight. It accepts only the frozen source, environment, operation class, endpoint/operation allowlist, coin/interval rules, and capture-mode match already recorded by the catalog. `runtime_enabled` must be absent or false, `live_transport_authorized` remains false, and the kill switch must fail closed.

A3 rejects credentials, wallet/signing/nonce/account material, private/user/account endpoints, `/exchange`, order/update/fill/funding user classes, Testnet/Mainnet execution wording, unsupported coins, unsupported intervals, unsupported capture modes, and capture-mode mismatch.

A3 is not a runtime collector, not an HTTP client, not a WebSocket client, not a reconnect/heartbeat/backfill/health loop, not a payload parser, not a Silver normalizer, not a strategy/risk/AI layer, and not an execution path.

## A4 official rate-limit authority — completed

A4 froze the only accepted authority identity for rate-limit metadata:

```text
source_kind: official
official_source_title: Rate limits and user limits
official_source_location: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
```

A4 recognizes only:

```text
UNRESOLVED_OFFICIAL_LIMIT
OFFICIAL_NUMERIC_LIMIT_RESOLVED
```

Current frozen status:

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
```

No numeric rate-limit values are encoded. Community, blog, forum, Discord, StackOverflow, inferred, remembered, third-party, and model-memory authority metadata are rejected in unresolved and resolved states.

A future resolved candidate requires readable and independently citable official documentation, complete numeric field names, units, operation scope, and no ambiguous fields. Representing complete resolved metadata still does not authorize live transport; transport requires a later separately authorized exact-head task.

## Fixture and operational-data boundary

Fixtures committed to Git must be synthetic documentation-derived or minimal redacted examples, sanitized, and explicitly provenanced. Real raw observations, real market/account logs, wallet addresses, API keys, signatures, nonces, credentials, database/cache artifacts, and unredacted operational payloads are forbidden.

Raw observation artifacts from any later authorized collector must remain outside Git. Only sanitized derived fixtures may be committed after review.

## Next gate

There is no active implementation slice. A4 completion does not authorize live public transport, health, backfill, reconnect, extractor/normalizer, Silver, strategy, AI recommendation, risk sizing, dashboard, Testnet/Mainnet execution, or exchange writes. Each later slice requires a new exact-head scope freeze, write lease, CI run, and external independent review.
