# V0-01 Official Public Source Catalog

Catalog version: `hyperliquid-public-mainnet.0.1.0`

Catalog hash: `0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7`

Catalog-entry hash domain: `trader-assist-v0/source-catalog-entry/v1`

Officially verified: `2026-07-07`

The single executable catalog authority is `src/trader_assist_v0/contracts/source_catalog.py`. It depends only on the standard library and `contracts/common.py`, so `RawEventV0` can validate catalog authority without a contracts-to-data import cycle. `src/trader_assist_v0/data/source_catalog.py` is a compatibility re-export and does not define a second catalog.

A0 records public interface facts only and does not connect to any endpoint. A1 freezes public transport-entry contracts only and still does not connect to any endpoint. A2 uses those contracts for caller-supplied public observation bytes and still does not connect to any endpoint. A3 freezes future public read-only transport preflight checks and still does not connect to any endpoint.

## Coverage

Coins: `ETH`, `BTC`.

WebSocket definitions: `trades`, `l2Book`, `bbo`, `activeAssetCtx`, `allMids`, `candle`.

Info definitions: `meta`, `metaAndAssetCtxs`, `allMids`, `l2Book`, `candleSnapshot`, `fundingHistory`, `predictedFundings`.

Runtime candle interval allowlist: `1m`, `3m`, `5m`, `15m`, `1h`.

## RawEvent binding

Each A0/A2 RawEvent binds and revalidates:

- source ID, catalog version, and catalog hash;
- endpoint ID and operation type;
- catalog-entry hash;
- coin and candle interval selection;
- endpoint kind and capture mode;
- connection, subscription, collector-local receive sequence, and payload hash.

WebSocket entries require `WS_TEXT_UTF8_APPLICATION_PAYLOAD`. Info entries require `HTTP_RESPONSE_BODY`. Unknown endpoints or operations, `/exchange`, Testnet, unsupported coins or intervals, missing required coins, and coins supplied to non-coin operations are rejected.

A0, A1, A2, and A3 do not parse raw payload fields. `source_event_time`, `source_publish_time`, `revision_time`, `source_native_id`, and `source_native_cursor` must all be `None` until a later separately reviewed extractor contract exists.

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

## A1 candle WebSocket envelope contract

A1 freezes the public-source envelope authority for Hyperliquid candle data.

Accepted public envelope policy:

```text
data: Candle
data: Candle[]
```

The contract accepts both shapes because the official candle subscription table and type definition use inconsistent singular/array descriptions. A1 records the accepted policy and fixture shape only. It is not a live WebSocket client and does not authorize observation runtime.

The internal evidence model remains exact `RawEventV0` application-payload bytes. A1 does not parse candle values into strategy signals, normalize them into Silver, infer direction, create AI recommendations, or size risk.

## A2 no-network public observation ingress

A2 accepts only exact bytes supplied by its caller. It does not acquire bytes by HTTP, WebSocket, DNS, socket, polling, reconnect, heartbeat, health, backfill, async runtime, or any other live transport runtime.

A2 must validate each accepted selection through the frozen A1 read-only transport entry contract. Private endpoints, user/account endpoints, wallet/signing material, nonces, order mutation, `/exchange`, Testnet/Mainnet execution enablement, strategy/risk logic, and AI recommendation logic remain rejected.

A2 binds exact bytes into `RawEventV0` authority using the catalog-bound payload hash and content-addressed payload reference. Different byte forms, including JSON whitespace or ordering differences, are different evidence.

Optional payload persistence and RawEvent manifest append must use existing A0 `BronzeStore` and `ManifestWriter` authority. A2 does not create a second persistence authority.

## A1/A2/A3 rate-limit entry gate

The official rate-limit page was not readable during A0 verification. Numeric limits remain recorded as `UNRESOLVED_OFFICIAL_LIMIT`; no remembered, inferred, third-party, community, blog, StackOverflow, Discord, or model-memory value is substituted.

When numeric limits are unresolved, live polling, WebSocket reconnect, backfill, health runtime, and any public transport runtime remain prohibited. Only official documented numeric values may replace `UNRESOLVED_OFFICIAL_LIMIT` in a later authorized task.

A3 must not resolve official numeric rate limits unless this exact task is amended by project control after current official docs are readable and cited.

## A1/A3 read-only transport entry contract

Future transport configuration shape is restricted to:

```text
source: hyperliquid-public-mainnet
environment: mainnet public read-only
operation class: public read-only observation only
coins: ETH, BTC
runtime candle intervals: 1m, 3m, 5m, 15m, 1h
capture modes: WS_TEXT_UTF8_APPLICATION_PAYLOAD, HTTP_RESPONSE_BODY
```

A1/A2/A3 must reject private endpoints, user/account endpoints, wallet/signing material, nonces, order mutation, `/exchange`, Testnet/Mainnet execution enablement, strategy/risk logic, and AI recommendation logic.

`mainnet public read-only` is a public source identity / environment label only. It is not Mainnet execution enablement.

## A1 fixture admission policy

Allowed fixtures:

- synthetic documentation-derived fixtures;
- minimal redacted examples;
- fixtures with explicit provenance and no operational secrets.

Forbidden fixtures:

- raw operational payloads;
- real market/account logs;
- private/user/account data;
- wallet addresses;
- API keys;
- signatures;
- nonces;
- credentials;
- database artifacts;
- caches;
- unredacted observations.

If later read-only observation is authorized, only sanitized derived fixtures may be committed. Raw observation artifacts must remain outside Git.

## A1-to-A2 gate

A1 completion does not authorize A2 automatically. A2 may only be considered after A1 PR merge, external exact-head review PASS, explicit rate-limit entry gate, frozen public source envelope contract, and a new exact-head project-control lease.

## Official locations

- WebSocket: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket`
- WebSocket subscriptions: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions`
- Timeouts and heartbeats: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/timeouts-and-heartbeats`
- Info endpoint: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint`
- Tick and lot size: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/tick-and-lot-size`
- Asset IDs: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids`
- Rate limits and user limits: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits`
