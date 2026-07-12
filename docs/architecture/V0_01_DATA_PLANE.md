# V0-01 Data Plane

## Preserved A0-A6 evidence plane

```text
official public source catalog
-> exact application-payload bytes
-> RawEventV0
-> immutable Bronze payload and manifest authority
-> deterministic offline replay
-> A5 exact candle extraction
-> A6 exact WebSocket/Info reconciliation
```

The A0-A6 implementations, fixed identities, hashes, canonical validation,
offline-only boundaries, and fail-closed semantics remain unchanged. A6 still
does not select a canonical winner, infer finality, normalize to Silver, run a
strategy, size risk, connect to an endpoint, or execute orders.

## Fast Launch target plane

The frozen target architecture is:

```text
Source Adapter
-> Raw Observation
-> Validation
-> Normalized Data Product
-> Feature Provider
-> StrategyInput
-> ETH-LDAR-v0.1
-> LONG / SHORT / WAIT
-> deterministic risk sizing
-> TradePlan
-> FAST / STANDARD signal card
-> Human Decision
-> manual exchange action
-> read-only account/order/fill observation
-> plan/outcome matching
-> replay and learning findings
```

A strategy must never consume raw exchange JSON directly. A new data product
cannot affect an existing strategy unless the strategy manifest explicitly
declares that dependency and a reviewed version/configuration enables it.

## R0 data products

The first release is bounded to data products required by `ETH-LDAR-v0.1`:

- ETH 5m and 15m candles;
- mark/mid reference;
- ETH open interest;
- Funding;
- timestamps and freshness;
- gap/conflict state;
- heartbeat, reconnect, and bounded backoff state;
- replay-compatible records.

The exact source adapters, normalized semantics, freshness rules, quality states,
retention, and replay formats must be frozen in versioned
`DataProductManifest` records during FLP1 implementation.

## Data quality authority

A signal or TradePlan must fail closed when mandatory data is stale, missing,
conflicting, disconnected, or outside the strategy's declared freshness and
quality contract. Reconnect or backoff must not silently convert unknown data
into live authority.

## Read-only account observation

R0 requires a future read-only path for order/fill observation and plan/outcome
matching. That requirement does not authorize private credentials or runtime
access now.

```text
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
```

FLP1 scope freeze must separately define identity, privacy, matching confidence,
failure states, and CSV/XLSX fallback rules before implementation.

## Execution separation

R0 ends at system assistance and manual exchange execution. No API wallet,
private key, signing, nonce, submit, cancel, SL/TP, transfer, withdrawal, or
position mutation is in the R0 data plane.

R1 may add human-confirmed execution only through a separately reviewed G4
gateway with immutable OrderIntent, idempotency, expiry, revalidation, fill-aware
protection, kill switch, dead-man protection, audit, Testnet, shadow, and
limited-capital canary gates.

## Current gates

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
```

The next gate is `V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE`.
