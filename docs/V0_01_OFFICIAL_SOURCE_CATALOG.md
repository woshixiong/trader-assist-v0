# V0-01 Official Public Source Catalog

Catalog version: `hyperliquid-public-mainnet.0.1.0`

Catalog hash: `0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7`

Officially verified: `2026-07-07`

The executable catalog is `src/trader_assist_v0/data/source_catalog.py`. This document records public interface facts only; A0 does not connect to any endpoint.

## Coverage

Coins: `ETH`, `BTC`.

WebSocket definitions: `trades`, `l2Book`, `bbo`, `activeAssetCtx`, `allMids`, `candle`.

Info definitions: `meta`, `metaAndAssetCtxs`, `allMids`, `l2Book`, `candleSnapshot`, `fundingHistory`, `predictedFundings`.

Runtime candle interval allowlist: `1m`, `3m`, `5m`, `15m`, `1h`.

## Frozen semantics

- `l2Book`: `FULL_SNAPSHOT_NOT_DELTA`.
- `trades`: batched stream, no documented source sequence.
- `bbo`: change-only stream, no documented source sequence.
- `activeAssetCtx`: current observation, no documented source timestamp.
- `allMids`: current map observation, no documented source timestamp.
- `candle`: mutable current bar; logical key is coin, interval, and open time.

The official candle subscription table and type definition use inconsistent singular/array descriptions. The catalog therefore records `Candle or Candle[]; official documentation differs` with `AMBIGUOUS_DOCUMENTATION`; A1 must freeze the actual envelope using a separately authorized fixture or read-only observation.

The official rate-limit page was not readable during verification. Numeric limits are recorded as `UNRESOLVED_OFFICIAL_LIMIT`; no remembered or third-party value is substituted. This is an A1 entry gate, not an A0 blocker.

## Official locations

- WebSocket: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket`
- WebSocket subscriptions: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions`
- Timeouts and heartbeats: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/timeouts-and-heartbeats`
- Info endpoint: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint`
- Tick and lot size: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/tick-and-lot-size`
- Asset IDs: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids`
- Rate limits and user limits: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits`
