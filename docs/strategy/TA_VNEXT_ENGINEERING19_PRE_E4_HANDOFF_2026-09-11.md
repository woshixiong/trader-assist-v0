# TA_VNEXT — complete Strategy -> Engineering19 PRE-E4 handoff

Status: STRATEGY REQUIREMENTS HANDOFF CANDIDATE / NO IMPLEMENTATION AUTHORITY
Date: 2026-09-11
Consumes: #163 comment `5613066757` Q1-Q16 plus the new validation/data-loop requirements requested by the user.

```text
STRATEGY_PRE_E4_HANDOFF=READY
STRATEGY_VERSION_OR_CHALLENGER_ID=TA_VNEXT_E4_C1_2026-09-11
POLICY_VERSION=TA_FRICTION_POSITION_POLICY_V0_1
PARAMETER_VERSION=TA_PRE_E4_GRID_V0_1
DERIVATION_VERSION=TA_MICROSTRUCTURE_DERIV_V0_1
E4_HARD_HOLD=ACTIVE_UNTIL_ENGINEERING19_INDEPENDENT_ACCEPTANCE
E4_WRITER_DISPATCH=NO
LIVE_STRATEGY_CHANGE=NO
EXCHANGE_WRITE=NO
```

This handoff is intentionally broader than the earlier Q1-Q16 response. It also requires the data/replay/Shadow/evidence machinery needed to measure Strategy quality after launch and to support future immutable improvement cycles.

## Q1 — Universe

### Discovery

`DISCOVERY_UNIVERSE = all currently eligible Hyperliquid perp/HIP-3 markets with valid identity, finalized cheap bar/context data and minimum tradeability/data-quality state.`

### Actionable

`ACTIONABLE_UNIVERSE = dynamic subset promoted by Scanner WATCH/near-Setup, active Thesis, Attempt or Winner state.`

Discovery and Actionable are intentionally different.

```text
MINIMUM_VIABLE_MARKET_COUNT=8
PREFERRED_INITIAL_E4_RESEARCH_SEED=20
MAXIMUM_USEFUL_MARKET_COUNT=NO_FIXED_STRATEGY_CAP_PRE_E4
```

Initial seed:

`SP500, XYZ100, CL, SILVER, SKHX, SNDK, MU, DRAM, BRENTOIL, SPCX, SKHY, NVDA, AAPL, BTC, ETH, HYPE, ZEC, META, INTC, SOL`.

Rotation candidates remain eligible dynamically.

Reselection:

- Discovery refresh at each finalized 5m boundary;
- Actionable promotion/demotion is state/event driven;
- weekly structural universe review;
- immediate review on listing/delisting, fee/Growth-Mode change, persistent liquidity shift or data-quality/provider change.

Engineering must not hard-code 12 or 20 as permanent product caps.

## Q2 — Cross-sectional synchronization

`SCANNER_SYNCHRONIZATION_REQUIREMENT=HYBRID`.

- cross-sectional Scanner/ranking: `STRICT_SAME_CLOSED_5M_T`;
- after market promotion to Actionable/Thesis: asynchronous per-market point-in-time Entry/Attempt/Winner state.

A missing market cannot silently use T-1 against T cohort. Late data cannot rewrite historical rankings/decisions.

## Q3 — Bars

Required:

- finalized `5m` structural Three Setup / Scanner authority;
- causal `1m` restart/Winner/Exit evidence;
- `15m/30m/60m` deterministic context where the current Strategy uses them.

Keep existing `2304 x 5m` historical warmup for Champion equivalence unless a separate exact equivalence experiment proves a smaller depth preserves outputs.

Nautilus internal aggregation is acceptable for derived higher timeframes only after exact bar-finality/equivalence proof.

## Q4 — BBO / executable quotes

`BBO=MUST_HAVE_FOR_E4_SHADOW`.

Uses:

- executable entry/exit reference;
- spread/tradeability;
- L1 capacity;
- executable MAE/MFE;
- Attempt failure/reentry;
- microprice/top imbalance;
- net executable progress;
- slippage/cost evidence.

Coverage: continuous while Actionable/Thesis-active.

C1 new-risk BBO freshness: `<=2s`; otherwise BBO-dependent variant becomes `BLOCKED/NOT_EVALUABLE`.

EA3 needs `60s` healthy BBO/trade warmup; EA1/EA2 need current executable BBO but not a 60s feature warmup.

## Q5 — Public trades

Generic `TradeTick` with price, size/notional, aggressor side and timestamps is sufficient for C1.

Continuous while Actionable/Thesis-active.

Primary flow window: `15s`; `5s` and `30s` diagnostic only unless a new immutable Derivation/Parameter version is opened.

Richer buyer/seller/hash identity: `RESEARCH_ONLY` for C1.

## Q6 — L2 depth

```text
BBO=MUST_HAVE
TOP10=SHOULD_HAVE_IF_L1_CAPACITY_IS_INADEQUATE
FULL_L2=RESEARCH_ONLY
TRUE_L3_L4_MBO=NOT_NEEDED/PARKED
```

Reopen full L2 only if:

1. BBO+TradeTick+flow-response leave a prespecified material OOS/Forward residual question; or
2. intended size cannot be modeled credibly with L1/top10.

No current L3/L4 hypothesis justifies the materially heavier node/order-level route.

## Q7 — Derived features

`MUST_HAVE`:

- spread;
- L1 feasible notional;
- aggressive notional imbalance 15s;
- executable flow-price response 15s;
- net executable progress;
- executable MAE/MFE;
- room-to-cost ratio;
- all-in friction estimate.

`SHOULD_HAVE`:

- microprice;
- top-level imbalance;
- micro-RV 60s;
- directional efficiency 60s;
- trade intensity.

`RESEARCH_ONLY`:

- multi-window persistence;
- CVD variants;
- classical/multi-level OFI;
- resiliency/replenishment;
- imbalance/run bars.

`NOT_NEEDED`:

- actor identity/spoof classifier;
- queue-position/L3-L4 authority;
- wallet clustering.

Exact formulas/gap/warmup semantics are in `TA_VNEXT_E4_C1_STRATEGY_SPEC_2026-09-11.md` and the data contract.

## Q8 — OI / funding / mark / index / basis

- mark: execution/reference input + Thesis/reference validation;
- index/oracle: Thesis/reference validation;
- mark-index basis: slow context;
- funding: slow context + risk/cost input when holding crosses funding event;
- OI: slow context, not sub-second Entry authority in C1.

Approximately one-minute-class sampling is sufficient for OI/funding context unless future evidence promotes them.

Low-burden context capture: `CAPTURE_CHEAP_OPTIONALITY`.

## Q9 — historical order flow

Before first E4:

- historical BBO: Forward-only acceptable;
- deep historical trades: Forward-only acceptable;
- historical full L2: not required;
- historical OI: nice-to-have/Forward acceptable;
- historical structural bars: required under current Strategy semantics.

Do not build a speculative arbitrary-range microstructure backfill platform before E4.

Provider archives may be qualified later for an exact unresolved decision.

## Q10 — Forward retention

Engineering must retain enough data to reproduce and compare all eligible Opportunities, not only fills.

Required durable identities/events:

- MarketEvent/Opportunity;
- Thesis;
- Eligibility/BLOCKED;
- TAKE/WAIT/PASS;
- Reset/Armed/Activation;
- Attempt / failure reasons / reentry;
- Winner Confirmation;
- Hold/protect/ratchet/giveback;
- Exit/Thesis invalidation;
- hypothetical order lifecycle;
- fee/execution model;
- first-passage, MAE/MFE and post-terminal outcomes;
- gap/stale/conflict/completeness state;
- exact Strategy/Policy/Parameter/Derivation versions.

Raw BBO/trades retention:

- at least 60s before first timing-sensitive candidate decision;
- throughout the full active Opportunity/Thesis/Attempt/Winner lifecycle;
- at least 30m after terminal Thesis state;
- low-cost bars/context at least 6h after terminal for broader missed-winner/right-tail diagnostics.

The same retention applies to WAIT/PASS Thesis paths. This is required to prevent selection bias.

## Q11 — timestamps / latency / freshness

Retain where available:

`provider_event_timestamp + local_receive/init/admission_timestamp + decision_timestamp + hypothetical_order_active_timestamp`.

No input may affect a decision before admission.

C1 targets:

- BBO <=2s for new-risk decision;
- mark/index <=5s target;
- OI/funding context <=60s target;
- completed bars only.

Do not impose a microsecond HFT contract.

Latency sensitivity may be reported on a bounded diagnostic grid when exact latency is unknown, but must not be represented as measured latency.

## Q12 — missing/gap semantics

Hard/mandatory input stale/missing/conflicted -> affected candidate `BLOCKED` or `NOT_EVALUABLE`.

Optional feature missing -> richer candidate not evaluable; simpler candidate remains a separate explicit variant. No silent EA3->EA1 mutation.

Evidence quality enum at minimum:

`COMPLETE / INCOMPLETE / GAPPED / STALE / CONFLICTED / NOT_EVALUABLE`.

Reconnect cannot retroactively rewrite prior decisions.

## Q13 — Discovery versus execution-quality data

Yes: broad Discovery can run on bars/context.

BBO/trades become mandatory for shortlisted Actionable/Thesis-active markets.

Ranking does not require continuous full microstructure across the entire eligible universe in C1.

## Q14 — Strategy-state / execution-shape

First Shadow requirement:

```text
partial exits=NO / deferred
winner adds=A0 no-add
trailing/giveback=YES hypothetical X2/X3
native trigger orders=counterfactual only
multiple attempts=YES sequential; max 2 total per Thesis in C1
simultaneous attempts=NO
cancel/replace chains=not first Strategy requirement
maker-vs-taker=versioned execution challenger
size-aware L2=conditional on L1 capacity failure
all orders=NOT_SUBMITTED
```

Strategy-side preliminary execution change class: `S2`, because future repeated Attempt and trailing/ratchet lifecycle changes execution shape. Engineering owns final classification.

## Q15 — actual account/fill evidence

Not required for first E4/E5 Strategy research.

Public data + hypothetical execution is sufficient for initial causal Strategy questions.

Later separately authorized fill data is valuable for model-to-reality calibration, but account/private API authority is independent.

## Q16 — priority classification

### MUST_HAVE_FOR_E4_SHADOW

- finalized 1m/5m/context bars;
- BBO;
- TradeTick aggressor-side data;
- mark/index/reference;
- exact instrument metadata;
- versioned fee/execution model;
- timestamps/gap/freshness;
- Opportunity->Thesis->Activation->Attempt->Winner->Exit identities;
- hypothetical executable fill/order model;
- executable MAE/MFE and first-passage;
- C1 MUST derived features;
- trial/version manifests.

### MUST_HAVE_FOR_E5_FORWARD

All E4 requirements plus:

- durable fresh Forward retention;
- complete Opportunity denominator;
- prospective material-variant/trial ledger;
- after-cost Thesis expectancy;
- Attempt count/cumulative friction;
- missed-winner/right-tail/giveback metrics;
- robustness decompositions;
- funding when horizon-relevant.

### SHOULD_HAVE

microprice, top imbalance, micro-RV, directional efficiency, trade intensity, low-rate OI/funding/context, top10 when needed.

### RESEARCH_ONLY

full L2, multi-level OFI/resiliency, rich trade identity, information bars, optional cross-venue extensions.

### NOT_NEEDED

L3/L4/MBO, actor/wallet/spoof attribution, HMM/RL/deep-learning first-stage models, arbitrary historical full-L2 pre-E4 acquisition, second custom generic market-data/reconnect/backtest platform.

# Q17 — new: common backtest / Shadow / live Strategy topology

Engineering must not implement a second Strategy semantics path for backtests.

Preferred mature route:

- project-owned versioned Strategy/Policy/Derivation definitions;
- Nautilus catalog-backed Backtest/Replay;
- same Strategy/Actor/ExecutionAlgorithm boundaries carried into Shadow/LiveNode where applicable;
- deterministic project evidence layer on top.

Any environment-specific adapter must preserve exact state/decision semantics and be independently equivalence-tested.

# Q18 — new: run manifest / reproducibility

Every backtest/Shadow/Forward run must produce a stable manifest binding:

- exact Git SHA;
- Strategy/Policy/Parameter/Derivation/Data/Execution/Fee versions;
- input catalog identity/hash/time range;
- universe identity;
- split/OOS identity;
- candidate set;
- cost/latency/fill assumptions;
- random seed for stochastic fill model;
- result artifact hashes.

Same deterministic manifest + same data => same deterministic decisions/order intents.

# Q19 — new: Opportunity denominator and candidate matrix

For every eligible Opportunity, persist every declared candidate outcome where its required data exists.

At minimum support paired matrices for:

- EA0/EA1/EA2/EA3;
- AP family opened by C1;
- no-Reentry vs one fresh Re-entry;
- WC0/WC1/WC2;
- X0/X1/X2/X3.

Missing data makes a candidate explicitly not evaluable. It cannot inherit another candidate's result.

# Q20 — new: hypothetical order/fill model

Must model:

- marketable Long Entry from Best Ask / Short from Best Bid;
- Long immediate Exit from Best Bid / Short from Best Ask;
- L1 feasibility and top10/L2 escalation when size exceeds credible L1 capacity;
- fee profile/version;
- funding where relevant;
- maker non-fill/missed-move risk;
- trigger != fill price;
- explicit execution-model-limited state.

# Q21 — new: validation gates and reports

Engineering must support the validation sequence in `TA_VNEXT_VALIDATION_BACKTEST_SHADOW_AND_PROMOTION_STANDARD_V1_2026-09-11.md`:

```text
G0 VERSION/SPEC INTEGRITY
G1 DETERMINISTIC CAUSAL REPLAY
G2 RETROSPECTIVE PAIRED BACKTEST
G3 CHRONOLOGICAL OOS / PURGE / EMBARGO
G4 E4 LIVE SHADOW
G5 E5 FRESH FORWARD PROMOTION EVIDENCE
G6 ZERO-WRITE / TESTNET EXECUTION QUALIFICATION
G7 SEPARATELY AUTHORIZED TINY MAINNET CANARY
```

Required automated/derivable reports:

- Opportunity denominator;
- Thesis/Attempt funnel;
- paired candidate comparison;
- first-passage/time-to-event;
- fees/friction;
- market/executable MAE/MFE;
- missed-winner/false-scratch;
- right-tail/giveback;
- market/setup/session/friction-regime robustness;
- data-quality completeness;
- trial/adaptivity;
- hypothetical-vs-actual execution calibration when later authorized.

# Q22 — new: Forward sample/promotion evidence

Engineering should expose metrics needed for the current project promotion standard, not hard-code the thresholds into Strategy infrastructure unless Strategy governance explicitly asks for it.

Current Strategy research standard records pragmatic floors:

- >=100 completed fresh Forward Theses overall before a broad positive promotion claim;
- >=30 per claimed friction regime;
- >=30 per specific subgroup before subgroup claims.

Promotion reporting requires one-sided cluster/bootstrap confidence on after-cost Thesis expectancy and paired Challenger-vs-Champion delta, with correlation/event clusters respected.

The exact policy lives in the Strategy validation standard and may version independently of generic infrastructure.

# Q23 — new: trial/adaptivity ledger

Engineering must make it cheap to log every material variant before evidence is opened:

- variant ID / parent;
- hypothesis;
- changed component;
- parameter grid;
- primary metric;
- start/first-evidence timestamp;
- rejection rule;
- disposition.

Unlogged material variant => affected independence/adaptivity claim invalid.

# Q24 — new: archive / provenance

Do not delete superseded Strategy decisions.

Maintain current authority separately from historical archive. Archived decisions retain:

- old conclusion;
- source pointer;
- why changed;
- replacement authority;
- reopen trigger.

No historical archive can silently regain live authority.

# Engineering-facing current research-investment disposition

```text
E4_CORE_BARS_BBO_TRADES_REFERENCE_COST_IDENTITY=ACQUIRE_BEFORE_NEXT_GATE
LOW_RATE_OI_FUNDING_CONTEXT=CAPTURE_CHEAP_OPTIONALITY_IF_LOW_BURDEN
ARBITRARY_HISTORICAL_BBO_L2_OI_DEEP_TRADES=PROCEED_WITH_CURRENT_BEST_AND_DEFER
FULL_L2_L3_L4_RICH_ID_ML=PARK_OR_REJECT_UNTIL_REOPEN_TRIGGER
FINAL_NUMERIC_EA_AP_WC_X_PARAMETERS=PROCEED_WITH_CURRENT_BEST_AND_DEFER_TO_E4_E5
DATA_BLOCKED_FRONTIER_ITEMS=NONE
```

# Engineering acceptance requested

Engineering19 should independently review this handoff against live main, #163 capability facts, exact Nautilus/provider surfaces and governance, then return one of:

```text
PRE_E4_STRATEGY_HANDOFF_ACCEPTANCE=PASS
PRE_E4_STRATEGY_HANDOFF_ACCEPTANCE=REPAIR
PRE_E4_STRATEGY_HANDOFF_ACCEPTANCE=REPLAN
```

PASS may allow Engineering to generate the bounded E4 Task Packet under its own authority/gates. It does not by itself authorize E4 Writer dispatch, production Strategy change, credentials, exchange writes or trading.
