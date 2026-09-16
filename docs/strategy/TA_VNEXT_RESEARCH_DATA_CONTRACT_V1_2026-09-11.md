# TA_VNEXT Research Data Contract V1

Status: DRAFT CANDIDATE / NON-EXECUTABLE
Date: 2026-09-11
Purpose: define the minimum causal evidence required to backtest, Shadow, Forward-test, monitor and later improve `TA_VNEXT_E4_C1` without changing Strategy semantics between environments.

## 1. Core rule

Collect the denominator, not just taken trades.

Every eligible Opportunity must remain observable through its outcome path, including:

- `BLOCKED`;
- `TAKE`;
- `WAIT`;
- `PASS`;
- activated and non-activated Thesis states;
- successful and failed Attempts;
- missed winners after WAIT/PASS;
- all frozen Challenger variants evaluated on the same causal path where inputs permit.

Logging only fills or only `TAKE` decisions creates selection bias and is insufficient for future Meta-Gate, WAIT-quality or counterfactual research.

## 2. Identity / provenance

Every retained research object must bind as applicable:

```text
research_run_id
release_sha
strategy_version
policy_version
parameter_version
derivation_version
data_contract_version
execution_model_version
fee_profile_version
trial_ledger_version
registry_version / registry_hash
market_id
provider_coin / dex identity
instrument metadata version
market_event_id
formal_signal_id / strategy_evaluation_id
opportunity_id
thesis_id
activation_id
attempt_id / attempt_index
winner_id
exit_id
hypothetical_order_id
source/provenance/hash/completeness state
```

No private account identifier, credential, wallet secret or raw private fill payload enters Git.

## 3. Time / causal fields

For every timing-sensitive record retain where available:

```text
provider_event_timestamp
local_receive_or_adapter_init_timestamp
admission_timestamp
decision_timestamp
hypothetical_order_active_timestamp
hypothetical_fill_timestamp
state_transition_timestamp
```

Causal rule:

`input.admission_timestamp <= decision_timestamp`.

Late events cannot rewrite a historical decision.

Bars must include exact open/close interval and finalization/admission state.

## 4. Market data required for E4

### Bars

- authoritative/finalized `5m` structural bars;
- causal `1m` bars for restart pivots, Winner structure and Exit;
- deterministic `15m/30m/60m` context where used by current Strategy;
- keep current `2304 x 5m` historical warmup for Champion equivalence until separately disproved by an equivalence study.

### BBO / Quote

Required for all Actionable/active-Thesis markets.

Retain:

```text
best_bid_px / size
best_ask_px / size
provider timestamp
local receive/init timestamp
spread
feed health/gap state
```

C1 new-risk decision requires BBO age `<=2s` or the BBO-dependent variant becomes not evaluable/blocked.

### Public trades

Generic TradeTick is sufficient for C1:

```text
price
size/notional
aggressor side
provider event time
local receive/init time
unique event/trade identity when available
```

Richer buyer/seller/hash identity is research-only for C1.

### Mark / index / reference

Retain current mark/index/oracle/reference values and timestamps while an Opportunity/Thesis is active.

### OI / funding / basis/context

Low-rate context only for C1. One-minute-class sampling is sufficient unless later evidence promotes it to timing-critical input.

Funding state must be retained whenever a hypothetical/actual holding interval crosses a relevant funding time.

### L2

Not an E4 hard requirement. Top-10 SHOULD be available when L1 capacity is inadequate for modeled position size. Full L2 is research-only until its reopen trigger fires.

## 5. Strategy state evidence

Retain every transition, not just terminal trades:

```text
SETUP / side / mode
CONTEXT
ELIGIBILITY_STATE
BLOCKED_REASON
DECISION_STATE = TAKE | WAIT | PASS
WAIT_REASON / start / end / termination
THESIS_CREATED / UPDATED / INVALIDATED / EXPIRED
RESET / ARMED
ACTIVATION_MODE / reference / timestamp
ENTRY_PROPOSAL
PROBE_UNCONFIRMED
ATTEMPT_PRICE_FAILURE
ATTEMPT_TIME_NO_FOLLOWTHROUGH
ATTEMPT_STATE_FAILURE
HARD_PROTECTIVE_STOP
ATTEMPT_FAILED
WAIT_FOR_FRESH_TRIGGER
FRESH_REACTIVATION
WINNER_CONFIRMED / mode
HOLD
STRUCTURAL_RATCHET
MFE/GIVEBACK state
EXIT_REASON / exit state
COMPLETE
```

Each transition records the evidence snapshot/reason codes that were actually available at that decision time.

## 6. Required derived features / outcomes

Minimum derived evidence:

```text
AGGR_NOTIONAL_IMBALANCE_15S
FLOW_PRICE_RESPONSE_15S
NET_EXECUTABLE_PROGRESS_BPS
MFE_EXEC_BBO
MAE_EXEC_BBO
MFE_MARKET
MAE_MARKET
MICRO_RV_60S
ROOM_TO_COST_RATIO
ALL_IN_FRICTION_EST_BPS
L1_FEASIBLE_NOTIONAL
```

SHOULD retain:

```text
MICROPRICE_OFFSET
TOP_LEVEL_IMBALANCE
DIRECTIONAL_EFFICIENCY_60S
TRADE_INTENSITY
TOP10_SIZE_AWARE_EXECUTABLE_PRICE when needed
```

First-passage labels:

```text
time_to_first_favorable_{3,5,8,10,15,20}bps
time_to_first_adverse_{3,5,8,10,12,15,20}bps
neither_touch_by_{30,60,90,120,180,300}s
```

All first-passage outcomes must distinguish market-price from executable-price labels.

## 7. Hypothetical order / fill evidence

Every candidate order intent records:

```text
order_intent_id
side
quantity / notional
order primitive candidate
maker/taker intent
trigger/reference price
order-active time
modeled entry fill price
modeled exit fill price
fill model version
fee profile/version
modeled fee
modeled slippage/impact
L1/top10 capacity state
funding applied
fill completeness / execution-model-limited reason
NOT_SUBMITTED=true for E4/E5 Shadow
```

Do not equate trigger price with fill price.

Passive maker candidates must record non-fill and missed-move outcomes; touch does not guarantee fill without defensible queue evidence.

## 8. Counterfactual candidate matrix

At each eligible Opportunity, evaluate the frozen candidates that have their declared inputs:

```text
EA0 / EA1 / EA2 / EA3
AP0 / AP1 / AP2 / AP3 / AP4 as preregistered
R0 no Re-entry / R1 one fresh Re-entry
WC0 / WC1 / WC2; WC3 only when its stage is opened
X0 / X1 / X2 / X3
```

Each candidate receives its own immutable version/variant identity.

A missing input makes that candidate `NOT_EVALUABLE_DATA_INCOMPLETE`; it must not silently fall back to another candidate and inherit its outcome.

## 9. Retention windows

### Discovery-only market

Bars/context only by default.

### Actionable / Opportunity / Thesis market

Retain raw admitted BBO and public trades from at least `60s` before the first timing-sensitive candidate decision through the full active Thesis/Attempt/Winner lifecycle.

After terminal Thesis state:

- retain raw BBO/trades for at least `30m` as counterfactual tail evidence;
- retain low-cost bars/context for at least `6h` after terminal state for broader missed-winner/right-tail diagnostics.

If a Thesis stays active for hours, raw capture continues while active; do not truncate the winner path merely to satisfy a fixed event window.

The same retention applies to `WAIT` and `PASS` Opportunities while their Thesis remains alive. This prevents selective observation of only taken trades.

If storage burden becomes material, Engineering may propose deterministic compression/normalization, but the result must preserve exact re-derivation of every C1 MUST_HAVE feature and executable outcome. Final feature numbers alone are insufficient.

## 10. Completeness / gap semantics

Every evidence window has one explicit state:

```text
COMPLETE
INCOMPLETE
GAPPED
STALE
CONFLICTED
NOT_EVALUABLE
```

Decision rules:

- mandatory causal input missing/stale/conflicted -> affected candidate `BLOCKED` or `NOT_EVALUABLE`;
- optional feature missing -> optional-feature candidate is not evaluable; simpler candidate remains a separate explicit variant;
- reconnect recovery never backfills a historical decision retroactively;
- conflicting historical windows remain conflict-labelled rather than silently reconciled after outcome is known.

## 11. Trial / adaptivity ledger

Every material variant must be logged before its evidence is opened:

```text
variant_id
parent_version
hypothesis
changed component
parameter grid
reason for test
start timestamp
first evidence timestamp
researcher/authority source
predeclared primary metric
predeclared rejection rule
status = ACTIVE | REJECTED | DEFERRED | PROMOTED | SUPERSEDED
```

Legacy trial count remains `LEGACY_INCOMPLETE_CONSERVATIVE`; do not fabricate it.

Any new unlogged material Strategy variant invalidates the affected adaptivity/independence claim.

## 12. Backtest / Shadow run manifest

Every run records:

```text
run_id
exact Git SHA
Strategy/Policy/Parameter/Derivation/Data/Execution/Fee versions
input catalog identity/hash/range
market universe identity
causal split identity
candidate list
latency/fill/cost assumptions
random seed where any stochastic fill model is used
software/runtime versions
start/end timestamps
result artifact hashes
```

Same manifest + same input data must be replayable deterministically for deterministic components.

## 13. Actual fill evidence — later, separate authority

First E4/E5 does not require private account/fill access.

If later separately authorized, minimum actual-fill research fields are:

```text
research-linked non-secret order identity
strategy/order-intent version identity
venue order/fill timestamps
side
requested / filled quantity
fill price(s)
maker/taker/liquidity role if authoritative
actual fee
actual funding when applicable
cancel/partial-fill/rejection state
observed slippage vs contemporaneous BBO
```

Raw account identifiers and secrets stay in private evidence storage. Git stores schema/contract only.

## 14. Required reports generated from this contract

Engineering should make it possible to derive, without manual reconstruction:

- Opportunity denominator report;
- Thesis/Attempt funnel;
- candidate paired-comparison report;
- first-passage / time-to-event report;
- fee/friction report;
- MAE/MFE report;
- missed-winner / false-scratch report;
- right-tail/giveback report;
- market/setup/session/friction-regime robustness report;
- data-quality completeness report;
- hypothetical-vs-actual execution calibration report once actual fills are separately available;
- trial/adaptivity report.

## 15. External capability fit

NautilusTrader official docs support catalog-backed quote/trade/bar data and common Strategy/backtest/live mechanics. Hyperliquid official WebSocket exposes `bbo`, `trades`, `l2Book`, candles and context subscriptions. Hyperliquid historical S3 archive has limited/incomplete coverage and may contain missing data; therefore the project should retain its own causal Forward research evidence once E4 begins rather than assuming every future question can be reconstructed later.
