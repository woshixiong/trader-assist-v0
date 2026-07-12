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
versions, decisions, outcomes, or replay capability. R0 needs a stable
interface, registry, and enable/disable control, not a dynamic hot-load market.

R0 enables only `ETH-LDAR-v0.1`. Deferred families include BRK-AR, TRD-PB,
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

R0 enables only products required by `ETH-LDAR-v0.1`.

## Change control

Any strategy or data-product change that may affect a signal, risk calculation,
TradePlan, operator decision, or outcome matching requires a new version,
deterministic tests, replay, shadow evaluation, independent review, and explicit
release.
