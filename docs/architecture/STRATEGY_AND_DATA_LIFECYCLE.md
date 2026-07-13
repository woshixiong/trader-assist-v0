# Strategy and Data Lifecycle

## StrategyManifest

Every strategy version declares:

- strategy ID and version;
- supported assets and timeframes;
- required and optional data products;
- minimum lookback;
- configuration schema;
- signal-output version;
- risk profile;
- replay compatibility;
- enabled state.

Promotion is independent development, deterministic tests, replay, shadow,
independent review, registry admission, and explicit configuration enablement.

Disabling a strategy sets `enabled = false`. It does not delete historical
versions, decisions, outcomes, or replay capability. These are future R1
lifecycle requirements. R0 has no strategy, StrategyManifest, registry, or
enable/disable requirement.

After the Capture Now T1 amendment, active R0 is `CAPTURE_ONLY` with
`active_strategy_count = 0`. It authorizes no strategy runtime, signal
recommendation, risk sizing, or TradePlan. The ETH-LDAR Operator Assist
semantics move to future R1 and remain not implemented or authorized in T1.
The release authority is `R1: ETH_OPERATOR_ASSIST`,
`T1: CONTRACT_SCHEMA_GOVERNANCE_ONLY`, and
`T2: SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME`. R1 remains
`FUTURE_NOT_IMPLEMENTED_NOT_AUTHORIZED`.

Future R1 may enable only `ETH-LDAR-v0.1` or a separately approved future ETH
strategy. Deferred families include BRK-AR, TRD-PB,
BAL-RV, LQS-FR/ETH-LDAR, MACRO-RP, ETHBTC relative strength, liquidation
cascade, turtle/cross-day trend, grid/market making, cross-venue arbitrage,
automatic regime routing, and AI discretionary strategy.

## DataProductManifest

The fixed dependency chain is:

```text
Source Adapter
-> Raw Observation
-> Validation
-> Normalized Data Product
-> Feature Provider
-> StrategyInput
```

A manifest declares product ID, version, semantic definition, source adapter,
asset, timeframe, freshness rule, quality states, replay format, retention
policy, and enabled state.

A strategy cannot read raw exchange JSON directly. It must declare required and
optional products. A new product cannot automatically influence an existing
strategy.

A product may be retired only when there is no active strategy, risk, or system
state dependency; historical decoding and replay remain available; and migration
is complete.

R0 enables no live data product runtime. Future R1 may enable only products
required by `ETH-LDAR-v0.1` or a separately approved future ETH strategy after a
separate gate.

## Change control

Any strategy or data-product change that may affect a signal, risk calculation,
TradePlan, operator decision, or outcome matching requires a new version,
deterministic tests, replay, shadow evaluation, independent review, and explicit
release.

`RAW_PUBLIC_EVIDENCE_PLANE` and `CAPTURE_AUTHORITY_PLANE` remain separate in T1.
Capture contracts may reference evidence IDs and hashes, but T1 does not connect
Capture records to RawEvent, Bronze, ingress, replay runtime, normalized data,
strategy, AI, risk, dashboard, account observation, Testnet/Mainnet execution,
or exchange writes.
