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
CONFLICT_STATE: OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED
SUPERSESSION_STATE: EFFECTIVE_VARIANT_UNDETERMINED
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

The query-free rate-limit page was freshly retrieved at `2026-07-12T14:34:55Z` and, with no-cache/no-store headers, at `2026-07-12T14:35:06Z`. Both reads returned HTTP 200 and the same Variant A body semantics. The supporting query-free Info page returned HTTP 200 at `2026-07-12T14:35:14Z` and confirmed operation identities without resolving the primary-page conflict. External R3 review had already confirmed a conflicting Variant B at the same canonical location. No independently confirmable version, effective marker, or supersession statement selects either variant. The public UI exposed only relative observations, so `publication_or_last_updated_marker` remains `None`; retrieval times are observation metadata, and the legacy source-catalog verification date remains `2026-07-07`.

The repository does not preserve or claim to authenticate complete remote GitBook HTML. Each source instead carries a reproducible evidence hash and byte length over canonical structured observation material stored in the contract: source identity, independently confirmable marker or `None`, semantic locator, bound fact IDs, bound unknown IDs, and normalized semantic observations. Fresh retrieval UTC is kept as frozen observation metadata but is excluded from evidence, source, and authority hash material. Remote wrapper, script, content length, tracking URL, or wrapper-byte changes do not by themselves establish official semantic drift.

The 25 conflict-safe common-subset facts cover the documented aggregate REST/IP budget; exchange, Info, explorer and response-item weights; WebSocket subscriptions, users, messages and inflight posts; EVM JSON-RPC; address volume allowance, initial buffer, limited fallback, cancel and open-order formulas; the common 2x maker-share percentage multiplier; and IP/address batch accounting. Every fact binds exact transport, endpoint class, operation allowlist, scope, value/unit, applicable window, response divisor/formula, sources, and a domain-separated fact hash.

Neither 10 nor 100 simultaneous WebSocket connections is an authenticated fact, and no 30-per-minute connection fact is retained. The maker-share fact is only `2 × maker share percentage`; it contains no reference period or computation/update cadence. The authority records `OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED` and `EFFECTIVE_VARIANT_UNDETERMINED` rather than selecting either observed variant.

The 14 mandatory unresolved fields retain the original ten—burst semantics, window algorithm, window alignment, partial response-bucket rounding, HTTP 429 behavior, error body, response headers, `Retry-After`, exact older-block weighting, and the high-congestion trigger—and add simultaneous WebSocket connection limit, new-connection/reconnection rate, maker-share reference period, and maker-share computation/update cadence. Every item is mandatory and blocking. A future candidate requires explicit official resolution or supersession plus separate bounded authorization.

A4 rejects third-party, community, remembered, inferred, blog, forum, Discord, StackOverflow, or model-memory authority metadata, as well as stale/altered sources, duplicate or conflicting facts, source mismatch, injected facts, omitted unknowns, and coherently rehashed alterations. Even a later complete resolved authority would not by itself authorize live transport.

`OfficialRateLimitAuthorityV0` and its nested Pydantic models are untrusted structural, serialization, and Schema containers. Builders and helpers return candidates, not authenticated authority, and low-level Pydantic APIs may construct counterfeit instances. Final authenticity never follows from Python instance identity. The sole public authority input is `authenticate_official_rate_limit_authority_json` with exact raw `str` or `bytes`; there is no public mapping-validation alias. Strict UTF-8 decoding, duplicate-key rejection at every depth, exact primitive typing, exact membership/order, semantic checks, and all hashes are reauthenticated. Every production consumer continues to follow private primitive builder → private mapping authenticator → immutable non-Pydantic authentication result. `rate_limit_authority_document` and `rate_limit_entry_gate` expose `conflict_state` and `supersession_state`. `validate_public_readonly_transport_preflight` reauthenticates the authority and returns `rate_limit_status = UNRESOLVED_OFFICIAL_LIMIT` with `live_transport_authorized = false`, but does not currently return those two structured state fields. `assert_rate_limit_allows_live_transport` reauthenticates the authority and raises a fail-closed unresolved-limit exception rather than returning a structured state payload.

The authentication result records what one authentication call proved; it is not an unforgeable capability, is never accepted again as authority input, and persisted or cross-process material must be reauthenticated from raw JSON. The private mapping path cannot recover duplicate keys already lost by an external parser and therefore is not a wire boundary. The generated JSON Schema remains structural only: a schema-valid counterfeit may exist and must be rejected by both authentication boundaries.

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
