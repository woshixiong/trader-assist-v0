# Trader Assist V0 — First Launch Signal-First Product Baseline

**Baseline ID:** `TA-FIRST-LAUNCH-SIGNAL-FIRST-BASELINE-2026-07-19-R1`  
**Date:** 2026-07-19  
**Repository:** `woshixiong/trader-assist-v0`  
**Status:** Product direction frozen by user; documentation-only GitHub synchronization pending review/merge  
**Authority boundary:** This document defines product scope and priority. It does not itself authorize runtime activation, account access, wallet/signing, Testnet/Mainnet exchange write, order submission, cancellation, or automatic SL/TP.

---

## 1. Product objective

First Launch is not a complete trading platform or infrastructure-completion milestone. Its three ordered objectives are:

1. **Assist the user in real trading as quickly as possible.**
2. **Validate whether this signal-assisted workflow is practically useful.**
3. **Only after usefulness is demonstrated, expand data capture, strategy validation, shadow orders, outcome analysis, and the broader V0/mainline foundation.**

The release is therefore defined as a **signal-viability pilot**, not a general-purpose data platform.

---

## 2. Frozen product priority

### P0 — First Launch public-data signal pilot

Deliver the minimum end-to-end loop:

```text
Hyperliquid public ETH data
→ validated market-data snapshot
→ volatility-regime safety layer
→ existing deterministic base strategies
→ OI/Funding contextual evidence
→ complete TradePlan
→ immediate notification
→ human review and manual execution
```

### P1 — Immediately after First Launch

Two product lanes have equal strategic priority:

1. **Add strategies for additional market conditions.**
2. **Build “signal → user review → one-click order preview/submission”.**

### P2 — After assisted order execution exists

Then continue:

- signal / decision / fill closure;
- shadow and real execution matching;
- outcome, MFE/MAE and strategy evaluation;
- selected V0 and mainline foundation work;
- broader persistence, reporting and product surfaces.

Engineering-foundation completeness must not replace trading assistance as the primary product objective. However, safety controls directly required to protect real funds remain mandatory before exchange-write activation.

---

## 3. Current completed capability baseline

The repository already contains:

- deterministic ETH `SWEEP_RECLAIM` and `BREAKOUT_RETEST`;
- LONG and SHORT;
- FAST and STANDARD paths;
- WAIT / WATCH / PREPARE / EXPIRED / INVALIDATED lifecycle;
- deterministic TradePlan generation;
- entry zone, chase limit, stop, TP1, TP2 and quantity calculation;
- public market-data parsing and fail-closed quality states;
- public runtime frame protocol and in-memory lifecycle;
- offline operator cards, NOT_SUBMITTED shadow records and decision journal;
- offline plan-to-outcome replay and pilot review modules.

The remaining First Launch work is primarily real public-network integration, product composition, notification, minimal persistence/de-duplication, deployment, and the product changes frozen below.

---

## 4. First Launch asset and authority boundary

### Included

- Asset: `ETH_ONLY`
- Venue data: Hyperliquid public endpoints only
- Runtime mode: restricted public `LIVE_SHADOW`
- Execution: human manual execution
- Deployment: one AWS instance
- Notification: one immediate, reliable user channel
- Strategy authority: deterministic reviewed code only

### Excluded from First Launch

- account reading;
- balances, positions, orders or fills;
- private keys, wallet signing or nonce authority;
- Testnet/Mainnet exchange write;
- automatic order submission;
- automatic cancellation;
- automatic SL/TP;
- BTC and ETHBTC;
- multi-strategy automatic selection;
- full dashboard;
- complete L2/OFI/CVD microstructure engine;
- online AI in the authoritative signal path;
- automatic optimization or production rule mutation.

---

## 5. Required market data

### 5.1 Closed ETH candles

Collect and validate:

- ETH 5m closed OHLCV;
- ETH 15m closed OHLCV.

Warm-up requirements:

- **5m: 64 closed, continuous candles**
- **15m: at least 20 closed, continuous candles**

Open candles have no signal authority. Data gaps, conflicts, stale observations or disconnection must fail closed.

### 5.2 Rolling composite windows

Using only closed, continuous 5m candles, deterministically construct:

- `3 × 5m` → rolling 15m composite;
- `6 × 5m` → rolling 30m composite;
- `12 × 5m` → rolling 60m composite.

These are rolling windows ending at the current closed 5m boundary. They must not depend on after-the-fact window selection or use future candles.

### 5.3 Volatility regime

Minimum First Launch classifier:

```text
atr5 = Wilder ATR(14) on closed 5m candles
atr_ratio = current ATR14 / median(previous 48 ATR14 values)
```

Regimes:

| Regime | ATR ratio | First Launch behavior |
|---|---:|---|
| LOW | `< 0.75` | Rolling 30m primary, rolling 60m backup; a 5m candidate cannot directly remain FAST |
| NORMAL | `0.75–1.50` | Existing 5m trigger and 15m bias remain primary; 30m is backup context |
| HIGH | `1.50–2.25` | Fast structure may remain eligible; label high volatility, tighten chase discipline, suggested risk cap `0.75x` |
| EXTREME | `> 2.25` | No normal actionable trigger; observation/alert only until recovery or additional closed confirmation |

The volatility layer is a **one-way safety overlay**:

- it may confirm;
- it may downgrade;
- it may veto;
- it may not create an independent trade when the base strategy returns WAIT/WATCH.

A complete DCBR scoring model, boundary registry and production overlay are not required for First Launch.

### 5.4 ActiveAssetContext and short context series

Collect:

- mark price;
- mid price;
- open interest;
- funding;
- source/receive timestamp.

Add a short rolling context series:

- receive or sample every 5–15 seconds;
- retain at least 60–120 minutes.

Compute and show:

- OI delta and percentage delta over 5m and 15m;
- current funding and recent change;
- mark–mid basis in bps;
- simple price × OI context:
  - `PRICE_UP_OI_UP`
  - `PRICE_UP_OI_DOWN`
  - `PRICE_DOWN_OI_UP`
  - `PRICE_DOWN_OI_DOWN`

For First Launch these values are:

- collected;
- logged;
- displayed to the user;
- retained as contextual/shadow evidence.

They are **not yet unvalidated hard signal gates**. Funding z-score and longer-history derivatives models are deferred until enough history exists.

### 5.5 Metadata

Collect ETH metadata required for price and quantity precision, including `szDecimals`.

---

## 6. Order-book boundary

The current First Launch signal strategy does not require:

- BBO;
- trades;
- L2 depth;
- OFI;
- CVD;
- wall detection.

Full order-book ingestion must not block the public signal pilot.

Before one-click order preview or exchange submission, the system must add at least:

- best bid;
- best ask;
- spread;
- current executable/reference price;
- basic depth/slippage check.

Full L2 behavior, trades, OFI, CVD, persistence/refill/cancel scoring and microstructure strategies are later strategy-specific extensions.

Static displayed walls must never be treated as reliable support/resistance without behavioral evidence.

---

## 7. Runtime user settings

The following must be external runtime configuration rather than code constants:

- `ACCOUNT_EQUITY_USD`
- `RISK_PER_TRADE_PCT`
- optional `MAX_NOTIONAL_USD`

### Requirements

- The user does not need frequent changes, but must have a documented way to change them.
- A configuration file plus safe reload or service restart is sufficient.
- No source-code modification or redeployment should be required.
- Decimal representation and units must be unambiguous.
- Values must be validated against safe allowed ranges.
- Every generated TradePlan must bind:
  - exact equity;
  - exact risk percentage/risk budget;
  - optional max notional;
  - configuration version.
- Existing TradePlans remain immutable after a configuration change.
- The current hard-coded `0.25%` risk budget must be removed as the only possible value.
- A volatility/overlay risk multiplier may only reduce the configured base risk, never exceed it.

---

## 8. Required First Launch output

An actionable notification must contain at least:

- ETH;
- LONG or SHORT;
- FAST or STANDARD;
- setup family;
- volatility regime and selected composite span;
- signal and market-data timestamps;
- entry range and planned entry;
- chase limit;
- stop;
- TP1 and TP2;
- quantity and notional;
- configured account equity and planned risk;
- expiry and invalidation conditions;
- OI/Funding/basis context;
- stable setup/signal/plan identifiers.

PREPARE, EXPIRED, INVALIDATED and runtime/data-failure messages must remain distinguishable from actionable signals.

---

## 9. Minimum runtime and persistence

First Launch needs only the persistence required for reliable assistance:

- recent emission/signal de-duplication;
- latest closed 5m/15m identities;
- minimal signal/notification log;
- configuration version;
- runtime session identity;
- restart-safe prevention of duplicate notifications.

A restart may discard an unconfirmed in-memory PREPARE and rebuild from a fresh snapshot, provided:

- no signal is issued before data returns to READY;
- recent notification IDs prevent duplicate alerts;
- the behavior is explicit and tested.

Full audit-grade lifecycle persistence, distributed storage and complete DecisionBundle/Outcome automation do not block launch.

---

## 10. Deployment and acceptance

### Deployment

- one AWS instance;
- default-off explicit restricted `LIVE_SHADOW`;
- single-instance protection;
- bounded reconnect;
- snapshot recovery;
- process restart;
- basic log rotation and health heartbeat;
- protected notification credentials;
- no account or exchange-write credentials.

### Acceptance

The pilot may start after:

- real Hyperliquid HTTP/WS fixtures pass the parser;
- 5m/15m snapshot warm-up reaches READY;
- closed-candle and gap/stale/disconnect fail-closed behavior passes;
- dynamic regime selection and composite construction are deterministic;
- OI/Funding context series produces expected deltas;
- external risk settings generate correct immutable TradePlans;
- notifications and de-duplication work;
- AWS smoke test succeeds.

A longer stability observation may continue during the restricted pilot rather than block all initial user testing.

### Product-value gate

Review after either:

- 7–14 days of operation; or
- 10–20 actionable signals.

Evaluate whether:

- signals are timely and understandable;
- the user can act within validity/chase limits;
- signal frequency is usable;
- signals surface opportunities or reduce monitoring load;
- false/noisy signals are acceptable;
- the user wants to continue relying on the product.

---

## 11. Post-launch development order

### Lane A — Strategy expansion

Add strategies based on observed market gaps. Candidate order:

1. range-edge liquidity sweep and reclaim;
2. second-test / second-failure behavior;
3. failed retest;
4. failed breakout reversal;
5. OI-price trap/unwind;
6. key-wick high-R:R attempt;
7. 1m/5m microstructure confirmation.

For each strategy:

```text
define market condition
→ define exact required data
→ implement only that data extension
→ deterministic strategy
→ shadow/advisory
→ evaluate
→ retain, revise or remove
```

Do not build a universal data platform before a strategy requires it.

### Lane B — Reviewed one-click order workflow

Shortest safe progression:

1. deterministic Order Preview;
2. Testnet user-confirmed submission;
3. Mainnet very-small-risk user-confirmed submission;
4. operator experience improvements.

Before any exchange submission, mandatory controls include:

- exact TradePlan confirmation;
- current READY data state;
- expiry and chase-limit recheck;
- BBO/spread and execution-quality check;
- balance/position/order conflict check;
- quantity/risk/notional caps;
- duplicate-submit prevention and client order identity;
- post-only handling;
- protective stop/TP result verification;
- kill switch.

These controls are not optional “foundation work”; they directly protect funds.

---

## 12. AI roadmap

AI remains valuable but is not on the First Launch critical path.

Later permitted roles:

- signal explanation;
- supporting/opposing evidence summary;
- market-context and macro/news overlay;
- second opinion and caution;
- post-trade review;
- failure-mode discovery;
- strategy research and candidate generation.

AI must not authoritatively change:

- base signal;
- entry/stop/targets;
- account-risk ceiling;
- quantity;
- signing;
- order submission;
- kill switch;
- production strategy configuration.

AI suggestions must pass deterministic implementation, testing, shadow evaluation and review before becoming production rules.

---

## 13. Engineering and governance synchronization

### Product Function and Priority Control owns

- product objective;
- included/deferred functions;
- strategy and data priority;
- release acceptance;
- post-launch product sequence.

### Engineering Optimization owns

- Agent/harness routing;
- parallel read-only support;
- Writer/Reviewer workflow;
- automation and evidence transfer;
- reducing manual copying and waiting;
- reliable implementation sequencing.

Engineering Optimization must not change this product baseline. Engineering work must not block the product critical path unless a concrete reliability, permission, routing or execution defect prevents safe delivery.

### Project Control owns

- exact repository/current-main verification;
- task and package activation;
- Write Lease;
- scope/path boundaries;
- evidence and acceptance state;
- finalization sequencing.

Project Control must translate this baseline into bounded implementation packages without adding foundation work that does not directly support First Launch.

---

## 14. Recommended remaining package structure

### Package 3A — Signal-input completion

- 64×5m / 20×15m readiness;
- rolling 15m/30m/60m composites;
- volatility regime;
- short OI/Funding ContextSeries;
- external equity/risk/notional configuration;
- tests and real-response compatibility fixtures.

### Package 3B — Restricted public signal composition

- real HTTP/WS connection;
- snapshot warm-up and reconnect;
- existing strategy + regime overlay;
- TradePlan construction;
- OI/Funding context formatting;
- notification;
- minimal log and de-duplication.

### Package 4 — AWS restricted pilot acceptance

- deployment;
- health and restart;
- failure alerts;
- real-market smoke test;
- restricted user pilot;
- no exchange write.

The exact number of PRs may be changed for efficiency, but the product boundary may not expand.

---

## 15. Canonical ruling

```text
PRODUCT:
FIRST_LAUNCH_SIGNAL_VIABILITY_PILOT

BASELINE_ID:
TA-FIRST-LAUNCH-SIGNAL-FIRST-BASELINE-2026-07-19-R1

PRIMARY_GOAL:
FAST PRACTICAL HUMAN TRADING ASSISTANCE

SECONDARY_GOAL:
VALIDATE PRODUCT AND STRATEGY USEFULNESS

ASSET:
ETH_ONLY

DATA:
HYPERLIQUID PUBLIC
5M/15M CLOSED OHLCV
ROLLING 15M/30M/60M COMPOSITES
VOLATILITY REGIME
SHORT OI/FUNDING/BASIS CONTEXT SERIES
ETH METADATA

STRATEGY:
EXISTING SWEEP_RECLAIM / BREAKOUT_RETEST
FAST / STANDARD / PREPARE
VOLATILITY LAYER MAY CONFIRM, DOWNGRADE OR VETO ONLY

RISK_SETTINGS:
EXTERNAL CHANGEABLE ACCOUNT EQUITY
EXTERNAL CHANGEABLE PER-TRADE RISK
OPTIONAL MAX NOTIONAL
IMMUTABLY BOUND INTO EACH PLAN

ORDER_BOOK:
NOT REQUIRED FOR SIGNAL PILOT
BBO REQUIRED BEFORE ONE-CLICK ORDER EXECUTION
FULL L2/OFI/CVD DEFERRED

OUTPUT:
COMPLETE TRADE PLAN + IMMEDIATE NOTIFICATION

DEPLOYMENT:
SINGLE AWS INSTANCE
RESTRICTED PUBLIC LIVE_SHADOW

EXECUTION:
HUMAN MANUAL

ACCOUNT_ACCESS:
NONE

EXCHANGE_WRITE:
NONE

POST_LAUNCH_PRIORITY:
1. MORE STRATEGIES
2. USER-REVIEWED ONE-CLICK ORDER WORKFLOW
3. OUTCOME/FOUNDATION COMPLETION

AI:
DEFERRED FROM CRITICAL PATH
RETAINED AS NON-AUTHORITATIVE EXPLANATION/CONTEXT/REVIEW/RESEARCH LAYER
```

---

## 16. Change control

Changes to this baseline require an explicit user product decision.

Engineering, Project Control, Writer or Reviewer windows must not infer authority to:

- add product scope;
- restore deferred foundation work as a launch blocker;
- add BTC;
- enable account/exchange write;
- permit AI authority;
- alter risk limits;
- make the volatility overlay independently create trades.

When repository object state and older narrative conflict, the latest explicitly user-approved product baseline controls product intent, while GitHub exact objects control implemented state.
