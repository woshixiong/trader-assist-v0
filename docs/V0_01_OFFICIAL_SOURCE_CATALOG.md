# V0-01 Official Public Source Catalog

Catalog version: `hyperliquid-public-mainnet.0.1.0`

Fixed source catalog hash: `0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7`

Catalog-entry hash domain: `trader-assist-v0/source-catalog-entry/v1`

Officially verified: `2026-07-07`

The single executable catalog authority is `src/trader_assist_v0/contracts/source_catalog.py`. It depends only on the standard library and `contracts/common.py`, so `RawEventV0` can validate catalog authority without a contracts-to-data import cycle. `src/trader_assist_v0/data/source_catalog.py` is a compatibility re-export and does not define a second catalog.

A0 records public interface facts only and does not connect to any endpoint. A1 freezes public transport-entry contracts only and still does not connect to any endpoint. A2 uses those contracts for caller-supplied public observation bytes and still does not connect to any endpoint. A3 freezes future public read-only transport preflight checks and still does not connect to any endpoint. A4 completed the official-only rate-limit authority freeze and still does not connect to any endpoint. A5 consumes only caller-supplied exact bytes already bound to `RawEventV0`; it also does not connect to any endpoint.

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

A0, A1, A2, A3, and A4 do not parse raw payload fields. `source_event_time`, `source_publish_time`, `revision_time`, `source_native_id`, and `source_native_cursor` remain `None` in RawEvent authority. A5 extracts candle fields into a separate typed result and does not modify or rebind RawEvent.

## Frozen semantics

- `l2Book`: `FULL_SNAPSHOT_NOT_DELTA`.
- `trades`: batched stream, no documented source sequence.
- `bbo`: change-only stream; timestamp availability is `FIELD_TIME` in milliseconds; no documented source sequence.
- `activeAssetCtx`: current observation, no documented source timestamp.
- `allMids`: current map observation, no documented source timestamp.
- `candle`: mutable current bar; logical key is coin, interval, and open time.

## A3 public read-only transport preflight

A3 freezes only future public read-only collector configuration preflight. It accepts only the frozen source, environment, operation class, endpoint/operation allowlist, coin/interval rules, and capture-mode match already recorded by the catalog. `runtime_enabled` must be absent or false, `live_transport_authorized` remains false, and the kill switch must fail closed.

A3 rejects credentials, wallet/signing/nonce/account material, private/user/account endpoints, `/exchange`, order/update/fill/funding user classes, Testnet/Mainnet execution wording, unsupported coins, unsupported intervals, unsupported capture modes, and capture-mode mismatch.

A3 is not a runtime collector, not an HTTP client, not a WebSocket client, not a reconnect/heartbeat/backfill/health loop, not a payload parser, not a Silver normalizer, not a strategy/risk/AI layer, and not an execution path.

## A4 official rate-limit authority — completed

A4 froze the official-only rate-limit authority contract required before any future public read-only live transport runtime. FLP1B0A re-read the current official pages and amended A4 with a versioned, deterministic `OfficialRateLimitAuthorityV0`. It records exact source-bound numeric facts without treating incomplete operational semantics as resolved transition authority.

Recognized status states:

```text
UNRESOLVED_OFFICIAL_LIMIT
OFFICIAL_NUMERIC_LIMIT_RESOLVED
```

Current frozen status:

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
TRANSITION_ELIGIBLE: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
```

The accepted official source identities are:

```text
source_kind: official
official_source_title: Rate limits and user limits
official_source_location: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
supporting_source_title: Info endpoint
supporting_source_location: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
```

The query-free rate-limit page was independently retrieved at `2026-07-12T07:49:50Z` and, with no-cache headers, at `2026-07-12T07:49:51Z`. Both reads returned the same normalized body semantics and official last-updated marker `2026-04-28T02:43:32.166Z`. The supporting Info page was retrieved at `2026-07-12T07:50:44Z` with marker `2026-06-11T08:02:46.893Z`. These retrieval times are observation metadata; the legacy source-catalog verification date remains separately frozen at `2026-07-07`.

The repository does not preserve or claim to authenticate complete remote GitBook HTML. Each source instead carries a reproducible evidence hash and byte length over the same canonical structured observation material stored in the contract: source identity, official marker, semantic locator, bound fact IDs, bound unknown IDs, and normalized semantic observations. Remote wrapper, script, or tracking-byte changes do not by themselves establish official semantic drift.

The 27 frozen facts cover the documented aggregate REST/IP budget; exchange, Info, explorer and response-item weights; WebSocket connections, subscriptions, users, messages and inflight posts; EVM JSON-RPC; address volume allowance, initial buffer, limited fallback, cancel and open-order formulas; high-congestion maker-share multiplier; and IP/address batch accounting. Every fact binds exact transport, endpoint class, operation allowlist, scope, value/unit, applicable window, response divisor/formula, sources, and a domain-separated fact hash.

The current reconciled WebSocket facts are exactly 10 simultaneous connections and 30 new connections per minute. The current maker-share fact retains the official previous-day reference and once-per-UTC-date computation wording. These values came from the two matching current official reads, not prior planning or tests.

The mandatory unresolved fields are burst semantics, window algorithm, window alignment, partial response-bucket rounding, HTTP 429 behavior, error body, response headers, `Retry-After`, exact older-block weighting, and the high-congestion trigger. A future resolved candidate requires exact official resolution of every mandatory field and a separate bounded authorization; recomputing hashes or omitting unknowns cannot make this authority transition-eligible.

A4 rejects third-party, community, remembered, inferred, blog, forum, Discord, StackOverflow, or model-memory authority metadata, as well as stale/altered sources, duplicate or conflicting facts, source mismatch, injected facts, omitted unknowns, subclass/model construction/copy bypasses, and coherently rehashed alterations. Even a later complete resolved authority would not by itself authorize live transport.

All Python and JSON validation entry points are permanently strict and forbid extras; string-validation, attribute extraction, model construction, and model copying cannot act as alternate authority paths. The generated JSON Schema requires every serialized root and nested field and forbids additional properties, but it remains structural only. Schema validity does not authenticate official sources, exact fact/unknown membership or ordering, duplicate/conflict rules, semantic evidence, hashes, or transition authority; executable `OfficialRateLimitAuthorityV0` validation is mandatory.

## A1 candle WebSocket envelope contract

A1 freezes the public-source envelope authority for Hyperliquid candle data.

Accepted public envelope policy:

```text
data: Candle
data: Candle[]
```

The contract accepts both shapes because the official candle subscription table and type definition have historically differed between singular and array descriptions. A1 records accepted policy only; it is not live subscription code.

The internal evidence model remains exact `RawEventV0` application-payload bytes. A1 does not parse candle values into strategy signals, normalize them into Silver, infer direction, create AI recommendations, or size risk.

## A2 no-network public observation ingress

A2 accepts only exact bytes supplied by its caller. It does not acquire bytes by HTTP, WebSocket, DNS, socket, polling, reconnect, heartbeat, health, backfill, async runtime, or any other live transport runtime.

A2 validates each selection through the frozen A1 read-only transport entry contract and binds exact bytes into `RawEventV0` authority. Optional payload persistence and manifest append use existing A0 authority; A2 creates no second persistence authority.

## A5 offline candle payload extraction

A5 supports only:

```text
hl-ws-mainnet-public / candle / WS_TEXT_UTF8_APPLICATION_PAYLOAD
hl-info-mainnet-public / candleSnapshot / HTTP_RESPONSE_BODY
```

A5 accepts only exact caller-supplied bytes whose length and SHA-256 match an exact `RawEventV0`. It does not read `payload_ref` or any other file.

Frozen candle fields are exactly:

```text
t  open time in milliseconds
T  close time in milliseconds
s  coin
i  interval
o  open price
c  close price
h  high price
l  low price
v  base-unit volume
n  trade count
```

A5 rejects missing/extra fields, duplicate JSON keys, invalid UTF-8, BOM, malformed JSON, NaN/Infinity, booleans in integer positions, strings in numeric positions, negative timestamps/volume/trade count, nonpositive OHLC, inconsistent high/low ranges, unsupported selections, and coin/interval mismatch.

A5 produces `CandlePayloadExtractionV0` with domain-separated logical candle keys and an extraction hash. The logical key binds source ID, coin, interval, and open time and deliberately excludes endpoint. A5 does not decide finality, revision ordering, latest-wins behavior, WebSocket/Info reconciliation, gaps, backfill, normalization, or Silver promotion.

## A1/A2/A3/A4/A5 rate-limit entry gate

Documented numeric facts are frozen, but the authority remains `UNRESOLVED_OFFICIAL_LIMIT` because mandatory operational semantics remain unknown. No remembered, inferred, third-party, community, blog, StackOverflow, Discord, or model-memory value is substituted.

When numeric limits are unresolved, live polling, WebSocket reconnect, backfill, health runtime, and any public transport runtime remain prohibited. A5 is offline and does not weaken this gate.

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

A1/A2/A3/A4/A5 reject private endpoints, user/account endpoints, wallet/signing material, nonces, order mutation, `/exchange`, Testnet/Mainnet execution enablement, strategy/risk logic, and AI recommendation logic.

`mainnet public read-only` is a public source identity / environment label only. It is not Mainnet execution enablement.

## A1 fixture admission policy

Allowed fixtures are synthetic documentation-derived fixtures, minimal redacted examples, and fixtures with explicit provenance and no operational secrets. Forbidden fixtures include raw operational payloads, real market/account logs, private/user/account data, wallet addresses, API keys, signatures, nonces, credentials, databases, caches, and unredacted observations. A5 adds no payload fixture.

## A1-to-A2 gate

A1 completion did not authorize A2 automatically. A2 could only be considered after A1 PR merge, external exact-head review PASS, the explicit rate-limit entry gate, the frozen public source envelope contract, and a new exact-head project-control lease. This historical authority chain remains part of the completed A1/A2 governance record and is not weakened by A5.

## A5 next gate

A5 completion does not authorize live public transport, health, backfill, reconnect, revision reconciliation, Silver, strategy, AI recommendation, risk sizing, dashboard, Testnet/Mainnet execution, or exchange writes. Each later slice requires a new exact-head scope freeze, write lease, CI run, external independent review, and finalization authorization.

## Official locations

- WebSocket: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket`
- WebSocket subscriptions: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions`
- Timeouts and heartbeats: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/timeouts-and-heartbeats`
- Info endpoint: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint`
- Tick and lot size: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/tick-and-lot-size`
- Asset IDs: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids`
- Rate limits and user limits: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits`
