# TA_VNEXT Validation / Backtest / Shadow / Promotion Standard V1

Status: DRAFT CANDIDATE / NON-EXECUTABLE
Date: 2026-09-11
Applies to: `TA_VNEXT_E4_C1_2026-09-11` and successor immutable versions unless superseded.

## 1. Purpose

The Strategy, its backtest, E4 live Shadow, E5 Forward evidence and later real-capital monitoring must form one causal system. A candidate is not considered validated because it produced a high backtest PnL. Promotion requires evidence that survives costs, causal replay, version freeze, chronological/Forward testing, execution-model sensitivity and independent review.

Primary principle:

```text
ONE_STRATEGY_SEMANTIC_MODEL
-> SAME VERSIONED FEATURE/STATE DEFINITIONS
-> SAME ORDER-INTENT SEMANTICS
-> BACKTEST / REPLAY
-> LIVE SHADOW
-> FORWARD SHADOW
-> LATER ACTUAL EXECUTION COMPARISON
```

Prefer Nautilus `BacktestNode`/catalog-backed workflows and the same Strategy/Actor/ExecutionAlgorithm boundaries that can carry forward to `LiveNode`, rather than a separate project-owned toy backtester.

No backtest or Shadow result authorizes exchange writes or real capital.

## 2. Evidence hierarchy

Strongest-to-weakest for a production edge claim:

1. fresh immutable Forward Shadow on the exact candidate version;
2. chronological untouched OOS replay with causal executable data;
3. deterministic retrospective replay on exact compatible data;
4. coarse mechanism/fee stress tests;
5. literature/theory only.

Historical and literature evidence may justify a candidate entering Shadow. They cannot by themselves promote it to real capital.

## 3. Required validation gates

### G0 — specification / version integrity

PASS only if all of the following are frozen:

- `strategy_version`;
- `policy_version`;
- `parameter_version`;
- `derivation_version`;
- data contract version;
- execution/fill model version;
- fee profile/version;
- exact candidate manifest;
- trial/adaptivity ledger identity.

A material semantic or parameter change creates a new immutable version. No in-place mutation of an observed Forward candidate.

### G1 — deterministic causal replay integrity

Hard PASS requirements:

```text
SAME_INPUT_MANIFEST => SAME_DECISIONS_AND_ORDER_INTENTS=100%
LOOKAHEAD_VIOLATIONS=0
RETROACTIVE_LATE_EVENT_REWRITES=0
UNDECLARED_FALLBACK_OR_DATA_SUBSTITUTION=0
MISSING_STALE_GAP_CONFLICT_STATES_EXPLICIT=100%
VERSION/MANIFEST/HASH_BINDING_COMPLETE=100%
```

Bars are usable only after causal close/admission. Tick/BBO/trade events may affect a decision only after their admitted receive/init timestamp. A late event can improve future state but cannot rewrite a past decision.

If deterministic replay fails, performance evidence is invalid regardless of PnL.

### G2 — retrospective backtest / paired policy replay

Run Champion and every frozen Challenger on the same Opportunity/path wherever causal reconstruction permits.

Primary comparison unit:

`Thesis / MarketEvent`, not individual fills.

All variants must share the same causal input stream, fee state and execution-model assumptions except for the exact component being tested.

Required first-pass ablation order:

```text
Champion
-> Thesis attribution
-> Entry mode
-> price context
-> BBO increment
-> trades increment
-> flow-response/reference increment
-> execution primitive
-> Attempt policy
-> Winner Confirmation
-> Re-entry
-> Exit
```

Do not jointly tune Entry + Stop + Re-entry + Exit to maximize one historical PnL and then attribute the result to a single component.

Retrospective results can reject a candidate. They cannot alone promote it.

### G3 — chronological OOS / walk-forward

Random K-fold is prohibited for the promotion claim.

Use chronological train/development -> validation -> OOS blocks. Where labels/Theses overlap in time, purge training observations whose outcome window overlaps the OOS window and apply an embargo at least as large as the maximum declared outcome/label horizon used by the experiment.

Once an OOS segment has been inspected and used to change the Strategy, that segment is no longer pristine. It becomes development history and the next promotion claim requires a new untouched segment or fresh Forward evidence.

`LEGACY_OOS_NOT_PRISTINE` is an accepted historical state, not a reason to fabricate independence.

### G4 — E4 live causal Shadow

Purpose: prove the exact candidate can consume live causal market data and produce stable hypothetical decisions/orders/outcomes with no exchange write.

Requirements:

- all orders are `NOT_SUBMITTED`;
- every eligible Opportunity is retained, including `TAKE`, `WAIT`, `PASS` and `BLOCKED`;
- every frozen candidate variant is evaluated prospectively on the same live path where inputs permit;
- no selective logging of only winning/taken Opportunities;
- all version identities and raw/derived data-quality states are retained;
- hypothetical fill/execution assumptions are explicit;
- Shadow must survive reconnect/restart without duplicate Strategy authority or retroactive decisions.

E4 is allowed to calibrate and reject. Any material change creates a new version and resets that version's Forward evidence clock.

### G5 — E5 fresh Forward promotion evidence

E5 is the first stage allowed to support an edge-promotion claim for an immutable candidate.

Minimum pragmatic sample floors before a positive broad claim:

```text
COMPLETED_FORWARD_THESES >= 100 overall
COMPLETED_FORWARD_THESES_PER_CLAIMED_FRICTION_REGIME >= 30
COMPLETED_FORWARD_THESES_PER_SPECIFIC_SUBGROUP_CLAIM >= 30
```

These are floors, not sufficient conditions. If dependence/correlation makes effective sample size materially smaller, continue collecting evidence.

Do not make a market/setup/session-specific claim when its subgroup has fewer than 30 completed Theses.

#### Absolute viability gate

For the exact frozen candidate:

- mean `THESIS_NET_R_AFTER_COST > 0`;
- total net PnL after modeled/observed fees, spread/slippage and relevant funding > 0;
- no safety/data-integrity hard-gate breach;
- risk/drawdown remains inside the separately approved risk envelope;
- one-sided cluster/bootstrap confidence on mean after-cost Thesis expectancy is reported.

Default threshold for **Challenger advancement** from Forward research:

`one-sided 90% lower confidence bound > 0`.

Default threshold for **real-capital Strategy promotion**:

`one-sided 95% lower confidence bound > 0` on a fresh, immutable Forward evidence set.

Clusters should reflect causal dependence, such as same macro event/session/theme or correlated simultaneous market episode; do not bootstrap obviously correlated storage-stock signals as independent observations.

If sample structure makes the stated confidence calculation indefensible, status remains `UNPROVEN`; do not replace it with a weaker statistic without a new reviewed standard.

#### Relative Challenger gate

Primary path is superiority to the Champion/reference on paired same-Opportunity evidence:

- `DELTA_NET_R_AFTER_COST > 0`;
- report paired cluster-bootstrap confidence interval;
- default Challenger-advancement threshold: one-sided 90% lower bound > 0;
- default real-capital Strategy-promotion threshold: one-sided 95% lower bound > 0.

A future risk-improvement/non-inferiority path may be added only with a pre-registered non-inferiority margin before opening the evidence. No post-hoc margin is allowed.

### G6 — zero-write approval / Testnet execution qualification

These stages validate operational execution semantics, not alpha.

Required comparisons include:

- Strategy decision -> hypothetical order intent -> operator approval -> submitted Testnet order;
- fill/partial fill/cancel/replace/stop/TP lifecycle;
- idempotency/reconciliation/restart behavior;
- observed vs modeled fees/slippage/latency.

A profitable Testnet sample does not validate Strategy edge because Testnet market microstructure may not represent Mainnet.

### G7 — tiny Mainnet human-approved canary

Requires separate explicit authority.

Canary purpose is to measure model-to-reality error, not to re-optimize the Strategy live.

Compare:

- predicted vs realized fill price;
- predicted vs realized fee;
- predicted vs realized slippage/impact;
- Shadow decision vs actual approved execution;
- order lifecycle/reconciliation;
- actual Thesis/Attempt/Winner/Exit result.

A material execution-model miss creates a new execution-model version and reopens affected evidence claims.

## 4. Order / fill simulation standard

### 4.1 Marketable/taker baseline

For a hypothetical Long Entry, executable reference begins from Best Ask; for a Short Entry, Best Bid. Immediate Long Exit uses Best Bid; Short Exit uses Best Ask.

When size is within credible L1 capacity, L1 can be the first fill approximation. If size exceeds credible top-level capacity, the observation must use top-10/L2 size-aware VWAP where available or be labeled `EXECUTION_MODEL_LIMITED`.

Never assume trigger price equals fill price.

### 4.2 Maker/passive candidate

Maker execution is an execution challenger, not a free fee discount.

Without defensible queue-position evidence, a maker order may not be counted as filled merely because market price touched the limit. Conservative replay must model non-fill / partial-fill / missed-winner risk. A maker policy cannot be promoted from fee savings alone.

### 4.3 Latency sensitivity

Backtests must separate market-event time, local admission time, decision time and hypothetical order-active time.

When exact historical latency is unavailable, report sensitivity rather than claim precision. A bounded diagnostic grid such as `0 / 250ms / 500ms / 1000ms` may be used as a stress test, never as a statement of actual production latency.

### 4.4 Fees and funding

Priority:

1. actual authoritative fill fee when separately available;
2. otherwise versioned configured fee profile tied to the run;
3. spread/slippage modeled through executable prices, not double counted;
4. funding included when the position spans a relevant funding timestamp.

Hyperliquid fee tier, Growth Mode and deployer fee state are dynamic inputs, not fixed asset constants.

## 5. Primary performance metrics

Always report at Thesis level:

- `THESIS_NET_PNL_AFTER_COST`;
- `THESIS_NET_R_AFTER_COST`;
- win/loss/breakeven distribution;
- Attempt count and cumulative scratch cost;
- marginal EV of Attempt 2;
- `MFE_EXEC_BBO` / `MAE_EXEC_BBO`;
- market MFE/MAE separately;
- time to first favorable/adverse barriers;
- false-activation and false-scratch classifications;
- missed-winner value;
- right-tail capture;
- MFE Capture Ratio;
- Profit Giveback;
- Profit->Loss Flip Rate;
- holding time / margin-hours when capital efficiency is evaluated;
- maximum drawdown and tail loss;
- fees/slippage/funding as a share of gross edge.

Do not optimize or promote on win rate alone.

## 6. Robustness / anti-overfit report

Every material comparison report must include:

- chronological block results;
- market and Setup decomposition;
- friction regime decomposition;
- session/open/event-context decomposition where sample permits;
- correlation/cluster handling;
- Top-1/Top-3/Top-5 winner contribution;
- leave-one-top-winner-out and leave-top-3-out sensitivity;
- base execution cost and adverse cost sensitivity;
- trial/adaptivity ledger count/status;
- White-Reality-Check/PBO/Deflated-Sharpe style diagnostics when sample/trial structure makes them defensible.

A candidate that is profitable only because of one market/day/episode or one extreme winner is not automatically rejected, because right-tail capture is an explicit objective, but it receives `TAIL_CONCENTRATION_WARNING` and requires more fresh Forward evidence before real-capital promotion.

Suggested warning threshold:

`TOP_1_WINNER_CONTRIBUTION > 50% of total net PnL` -> mandatory extended Forward evidence / no immediate real-capital promotion.

This is a project risk-control warning, not a universal statistical law.

## 7. Cost / regime stress

At minimum report:

- observed/configured base cost;
- `+25%` all-in execution-friction sensitivity;
- `+50%` all-in execution-friction sensitivity.

These stress cases are diagnostics. If observed real execution routinely reaches the stress band that destroys the edge, promotion fails until the execution model/policy is repaired.

## 8. Rejection / stop rules

Reject or park the candidate rather than add more features when any applies:

- after-cost Forward expectancy remains <=0;
- paired Challenger delta remains <=0 after sufficient Forward evidence;
- positive result exists only under implausibly optimistic fills/fees;
- performance disappears under a small plausible execution-cost change;
- result requires narrow threshold tuning with unstable neighboring parameters;
- edge is isolated to one accidental historical period and does not recur Forward;
- data-quality/causal integrity needed for the claim cannot be established;
- incremental complexity does not produce incremental OOS/Forward value.

Do not keep repairing a failed economic hypothesis indefinitely.

## 9. Monitoring after later production promotion

Even after a separately authorized Strategy reaches real capital, retain a parallel Shadow/reference track.

Monitor rolling and cumulative:

- actual vs Shadow/expected net R;
- fill/slippage/fee model error;
- opportunity coverage;
- false-scratch / missed-winner rates;
- Attempt count/cost;
- right-tail capture/giveback;
- drawdown;
- market/regime concentration;
- data-quality/gap incidents;
- version drift.

Drift triggers a review; it does not authorize automatic self-modification. Any material Strategy change returns through immutable Challenger -> replay/OOS -> Forward Shadow -> promotion.

## 10. External method anchors

- Halbert White (2000), `A Reality Check for Data Snooping`, Econometrica, DOI `10.1111/1468-0262.00152`.
- Bailey, Borwein, López de Prado, Zhu (2015), `The Probability of Backtest Overfitting`, SSRN `2326253`.
- Bailey & López de Prado (2014), `The Deflated Sharpe Ratio`, DOI `10.3905/jpm.2014.40.5.094`.
- NautilusTrader official docs: BacktestNode/BacktestEngine, ParquetDataCatalog, fill models and shared live/backtest component model.

These methods reduce false discovery risk; they do not prove this Strategy profitable.
