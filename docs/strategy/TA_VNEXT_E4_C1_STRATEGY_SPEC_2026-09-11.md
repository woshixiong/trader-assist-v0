# TA_VNEXT_E4_C1 — bounded Strategy candidate for causal Shadow

Status: PRE-E4 CANDIDATE / NON-EXECUTABLE
Date: 2026-09-11
Parent authorities: #161, #150, #85
Engineering handoff: #163 comment `5613066757`

```text
STRATEGY_PRE_E4_HANDOFF=READY
STRATEGY_VERSION=TA_VNEXT_E4_C1_2026-09-11
POLICY_VERSION=TA_FRICTION_POSITION_POLICY_V0_1
PARAMETER_VERSION=TA_PRE_E4_GRID_V0_1
DERIVATION_VERSION=TA_MICROSTRUCTURE_DERIV_V0_1
CURRENT_THREE_SETUP_AUTHORITY=UNCHANGED
LIVE_STRATEGY_CHANGE=NO
E4_HARD_HOLD=ACTIVE_UNTIL_ENGINEERING_INDEPENDENT_ACCEPTANCE
EXCHANGE_WRITE=NO
REAL_CAPITAL_AUTHORITY=NO
AUTONOMOUS_TRADING=NO
```

## 1. Core architecture

Three Setup remains the only directional structural authority:

- `SWEEP_RECLAIM`
- `BREAKOUT_RETEST` (`MICRO_FAST` / `STANDARD`)
- `RANGE_EDGE_REJECTION`

Layer separation:

```text
THREE_SETUP / STRUCTURE
= WHAT + WHERE + SIDE

PRICE + ORDER FLOW / MICROSTRUCTURE
= WHEN + SHORT-HORIZON QUALITY / ACCEPTANCE

EXECUTION / FRICTION
= WHETHER THE OPPORTUNITY IS ECONOMICALLY TRADEABLE

WINNER MANAGEMENT
= SLOWER RIGHT-TAIL CONTROL AFTER PROBE SUCCESS
```

Raw CVD, displayed walls or venue-local order flow are not a fourth Setup and cannot independently choose side.

## 2. Anti-HFT / turnover boundary

```text
HIGH_FREQUENCY_DATA_NE_HIGH_FREQUENCY_TRADING=YES
LATENCY_ARBITRAGE_AS_PROJECT_EDGE=REJECTED
LOW_FRICTION_NE_OVERTRADING_LICENSE=YES
FRESH_CAUSAL_INFORMATION_REQUIRED_FOR_NEW_ATTEMPT=YES
```

Fast data is used for timing, executable-state evidence and failure detection. Trading frequency is an output of qualified Opportunities, never the optimization target.

## 3. Lifecycle

```text
CONTEXT
-> THESIS
-> ELIGIBILITY
-> ARMED
-> ACTIVATION
-> ENTRY_PROPOSAL
-> PROBE_UNCONFIRMED
-> ATTEMPT_FAILED | WINNER_CONFIRMED

ATTEMPT_FAILED + THESIS_VALID
-> WAIT_FOR_FRESH_TRIGGER
-> optional one fresh Re-entry in C1

WINNER_CONFIRMED
-> HOLD
-> PROTECT / STRUCTURAL_RATCHET
-> GIVEBACK / STRUCTURAL_DETERIORATION / THESIS_INVALIDATION EXIT
```

Permanent distinction:

`ATTEMPT_FAILURE != THESIS_INVALIDATION`.

## 4. Entry Activation family

First bounded comparison:

```text
EA0 = current Formal-time entry control
EA1 = DIRECT_REACCEL_PRICE
EA2 = RETEST_REACCEL_PRICE
EA3 = EA1/EA2 + SIMPLE_FLOW_PRICE_RESPONSE_ACCEPTANCE
EA4 = richer/full-L2 activation — DEFERRED
```

### 4.1 Causal 1m restart pivot

A pivot high at completed 1m bar `j` becomes knowable only after `j+1` has completed:

```text
high[j] > high[j-1]
AND high[j] >= high[j+1]
```

Pivot low:

```text
low[j] < low[j-1]
AND low[j] <= low[j+1]
```

Decision timestamp is the admission of completed bar `j+1`; no retroactive use at bar `j`.

Long restart reference = latest causally confirmed post-reset pivot high.
Short restart reference = latest causally confirmed post-reset pivot low.

`EA1` fires on first thesis-direction price activation across the restart reference using causally admitted event data and current executable BBO.

`EA2` requires a causal retest before a fresh reacceleration activation. Retest is an Entry mode, not a global prerequisite.

### 4.2 EA3 simple flow × price response

Primary flow window: `15s`.

```text
AGGR_NOTIONAL_IMBALANCE_15S
= side_sign * (buy_aggressive_notional - sell_aggressive_notional)
  / (total_aggressive_notional + epsilon)
```

Primary C1 acceptance deliberately uses sign, not an optimized magnitude cutoff:

```text
AGGR_NOTIONAL_IMBALANCE_15S > 0
AND FLOW_PRICE_RESPONSE_15S > 0
```

Executable price response:

```text
FLOW_PRICE_RESPONSE_15S
= side_sign * (E_t - E_t-15s) / E_t-15s * 10,000
```

Long executable exit/reference price = Best Bid.
Short = Best Ask.

Same-side aggressive flow with non-positive executable price response is `WEAK_RESPONSE / ABSORPTION_CANDIDATE`, not continuation confirmation.

## 5. Friction-conditioned participation

Do not hard-code BTC/ETH versus RWA as separate Strategy families.

Use a versioned effective fee/execution profile. Effective friction may include:

- entry fee;
- exit fee;
- modeled slippage/impact;
- funding when the holding horizon makes it material.

Never double-count spread when executable entry/exit prices already encode it.

Define:

```text
ROOM_TO_COST_RATIO
= REMAINING_STRUCTURAL_ROOM_BPS
  / max(ALL_IN_FRICTION_EST_BPS, epsilon)
```

C1 diagnostic hurdle grid:

```text
k = {2, 3, 4}
```

This is a bounded research grid, not a production threshold.

A valid Thesis can be `TAKE` in a low-friction state and `WAIT/PASS` in a high-friction state without changing directional authority.

## 6. TAKE / WAIT / PASS

`BLOCKED` is never merged into economic `PASS`.

```text
TAKE = causal Activation exists and current evidence/economics permit participation
WAIT = Thesis valid but information/economic hurdle can still plausibly improve
PASS = valid/eligible opportunity but after-cost value/remaining room is insufficient
BLOCKED = causal/data/safety/process requirement is not satisfied
```

The economic objective is the expected net value of `TAKE` versus `WAIT` versus `PASS`, after fees, executable price, missed-move cost, false-entry cost and right-tail opportunity value.

## 7. Attempt / Stop family

```text
AP0 = STRUCTURAL_REFERENCE
AP1 = FIXED_BPS_STOP: 4/6/8/10/12/15/20 bps
AP2 = VOL_NORMALIZED_STOP
AP3 = TIME_NO_FOLLOWTHROUGH: 30/60/90/120/180 sec; 300 sec diagnostic
AP4 = PRICE_PLUS_TIME — priority simple challenger
AP5 = PRICE_TIME_PLUS_FLOW_STATE — only if AP4 leaves incremental value
```

`PnL < 0 -> EXIT` remains rejected as the final machine rule.

### 7.1 AP2 volatility normalization

Using valid 1-second sampled BBO mids:

```text
MICRO_RV_60S_BPS
= 10,000 * sqrt(sum(log(mid_i / mid_i-1)^2))
```

Research multiplier grid:

```text
k_rv = {0.5, 1.0, 1.5}
Y = clip(k_rv * MICRO_RV_60S_BPS, 4 bps, 20 bps)
```

Again, this is Shadow research only.

## 8. Re-entry / Attempt budget

C1 allows at most:

```text
INITIAL_ATTEMPT + ONE_FRESH_ACTIVATION_REENTRY
```

Attempt 3+ is parked until Attempt 2 demonstrates material incremental after-cost value.

Fresh Re-entry requires a new causal activation state after the previous Attempt has failed. The old pre-failure restart reference cannot simply fire again without new causal information.

No mandatory fixed cooldown. Blind immediate Re-entry remains a negative control.

Past scratch losses are sunk for the marginal decision to Re-enter. They remain recorded at Thesis level but cannot justify another trade through sunk-cost logic.

## 9. Winner Confirmation

First bounded family:

```text
WC0 = favorable executable progress
WC1 = progress + persistence
WC2 = progress + fresh favorable causal structure
WC3 = progress + simple flow/price-response acceptance
```

Favorable progress diagnostic grid remains:

`3/5/8/10/15/20 bps`.

Persistence windows for C1 research:

`30s / 60s`.

Once `WINNER_CONFIRMED`, very-short-horizon microstructure reversal loses the automatic scratch authority it had during `PROBE_UNCONFIRMED`. Control shifts to slower structure/right-tail protection.

## 10. Winner Add

```text
A0 = NO_ADD
```

Winner pyramiding remains deferred until the base Entry/Attempt/Winner/Exit policy shows a measurable unmet need.

## 11. Exit family

First bounded Winner Exit comparison:

```text
X0 = FIXED_R / TP reference control
X1 = STRUCTURAL_FULL_EXIT
X2 = MFE_GIVEBACK_TRAILING
X3 = STRUCTURAL_RATCHET + MFE_GIVEBACK
```

`X3` is the priority simple combined challenger, not a proven winner.

### 11.1 X1 structural exit

After Winner Confirmation, use causally confirmed 1m favorable structure.

Long: completed 1m close below latest valid confirmed higher-low reference -> structural Exit candidate.

Short: mirror with latest valid confirmed lower-high reference.

Hard protective Stop and Thesis invalidation always retain authority.

### 11.2 X2 giveback

```text
NET_MFE_BPS(t) = max NET_EXECUTABLE_PROGRESS_BPS since Winner Confirmation
GIVEBACK_BPS = NET_MFE_BPS - current NET_EXECUTABLE_PROGRESS_BPS
GIVEBACK_RATIO = GIVEBACK_BPS / max(NET_MFE_BPS, epsilon)
```

C1 grid:

```text
g = {1/3, 1/2, 2/3}
```

### 11.3 X3

Exit on first of:

- X1 causal structural deterioration;
- X2 selected giveback threshold;
- hard protective Stop;
- structural Thesis invalidation.

## 12. Partial take-profit

`PARTIAL_SCALE_OUT=C1_DEFERRED`.

It is not permanently rejected. It is reopened only if X0-X3 show an unacceptable profit-to-loss flip / giveback problem and a bounded scale-out policy has a specific causal hypothesis for improving after-cost expectancy without destroying right-tail value.

## 13. Quantitative cost self-check

For gross Winner `G`, gross Loss `L`, round-trip friction `C`:

```text
p_break_even = (L + C) / (G + L)
```

Repeated failed Attempts make the required final Winner grow linearly with loss + friction. Therefore an open-ended retry policy is economically inconsistent with the Strategy objective and remains rejected.

## 14. Data priority summary

C1 first-stage `MUST_HAVE`:

- finalized 5m structural bars;
- causal 1m bars;
- BBO / executable quotes;
- generic TradeTick with aggressor side;
- mark/index/reference state;
- exact instrument metadata;
- versioned effective fee/execution model;
- provider/local/decision timestamps;
- explicit stale/gap/conflict state;
- full Opportunity -> Thesis -> Activation -> Attempt -> Winner -> Exit identity chain.

`SHOULD_HAVE`:

- microprice;
- top-level imbalance;
- micro-RV;
- directional efficiency;
- trade intensity;
- low-rate OI/funding/basis context;
- top-10 depth if L1 size feasibility is inadequate.

`RESEARCH_ONLY`:

- full L2;
- multi-level OFI / resiliency;
- richer trade-counterparty identity;
- information bars;
- cross-venue extensions.

`NOT_NEEDED` for C1:

- L3/L4/MBO;
- actor/spoof/wallet attribution;
- HMM/RL/deep-learning Strategy model;
- custom generic market-data/reconnect/backtest platform.

## 15. Current known unknowns

No final winner or final numeric threshold is claimed for:

- EA1 vs EA2 vs EA3;
- AP1/AP2/AP3/AP4;
- the exact Attempt Stop/time budget;
- no-Reentry vs one fresh Re-entry;
- WC0/WC1/WC2/WC3;
- X0/X1/X2/X3;
- giveback threshold;
- partial scale-out;
- maker-vs-taker Entry execution;
- full-L2 incremental value;
- OI/funding timing value;
- final actionable-universe breadth;
- actual slippage/capacity at larger future size.

These are first-class research questions in the hypothesis ledger and must not be silently resolved through implementation defaults.

## 16. External evidence disposition

External research confirms the direction but not project thresholds:

- White (2000), `A Reality Check for Data Snooping`, DOI `10.1111/1468-0262.00152` — repeated reuse of the same historical data creates false discovery risk.
- Bailey et al. (2015), `The Probability of Backtest Overfitting`, SSRN `2326253` — investment backtests need explicit overfit controls beyond a naive holdout.
- Bailey & López de Prado (2014), `The Deflated Sharpe Ratio`, DOI `10.3905/jpm.2014.40.5.094` — performance selection must account for multiple trials and non-normal returns.
- Gârleanu & Pedersen, dynamic trading under transaction costs — trading aggressiveness must reflect predictor persistence and costs.
- Cont/Kukanov/Stoikov, Stoikov microprice, queue-imbalance/order-flow literature — short-horizon BBO/trade features can contain probabilistic information but do not transfer universal thresholds to Hyperliquid.
- Hyperliquid official docs — fees are account/market-state dependent; Growth Mode reduces relevant HIP-3 fees by 90%; public live BBO/trades/L2 feeds exist; provider archive history is incomplete and may be missing.
- NautilusTrader official docs — catalog-backed BacktestNode and live Strategy infrastructure are designed to preserve code/semantic continuity from backtest to live.

Therefore the selected route is:

`INDEPENDENTLY_DERIVED_EXTERNALLY_MODIFIED`.

The next decisive evidence is causal E4/E5 replay/Forward evidence, not another broad theory expansion.
