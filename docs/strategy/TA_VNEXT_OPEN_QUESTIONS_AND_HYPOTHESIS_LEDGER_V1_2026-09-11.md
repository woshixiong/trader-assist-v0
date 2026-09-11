# TA_VNEXT Open Questions / Hypothesis Ledger V1

Status: ACTIVE RESEARCH LEDGER CANDIDATE / NON-EXECUTABLE
Date: 2026-09-11
Purpose: ensure every material unknown is explicitly recorded, mapped to future evidence, and never silently turned into a production default.

Legend:

- `HARD_BLOCKER` — cannot make the stated next claim without evidence.
- `MATERIAL_OPTIMIZATION` — current candidate can proceed to Shadow; decision belongs to causal/OOS/Forward evidence.
- `OPTIONAL` — useful only if cheap or if a reopen trigger fires.
- dispositions: `ACQUIRE_BEFORE_NEXT_GATE`, `CAPTURE_CHEAP_OPTIONALITY`, `PROCEED_WITH_CURRENT_BEST_AND_DEFER`, `PARK_OR_REJECT`.

## U01 — EA1 Direct vs EA2 Retest vs EA3 price+flow

Question: which Activation mode maximizes after-cost Thesis expectancy while controlling false activation and missed runaway winners?

Evidence: same-Opportunity paired E4/E5 causal replay using BBO/trades and identical Thesis state.

Metrics: detection delay, executable entry price, false activation, missed-winner value, net first-passage, net R.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.
Reject EA3 if it adds no stable OOS/Forward value over price-only modes.

## U02 — 15s flow window / sign-only EA3 acceptance

Question: is 15s sign-only flow×price-response sufficient, or do 5s/30s/magnitude thresholds add value?

Evidence: prospective derived-feature variants only after C1 baseline.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.
No magnitude threshold is authorized from historical fishing.

## U03 — microprice / top-level imbalance incremental value

Question: do BBO microprice/imbalance improve EA3 beyond price+TradeTick response?

Evidence: paired incremental E4/E5 ablation.

Criticality: OPTIONAL/MATERIAL_OPTIMIZATION only if simple baseline plateaus.
Disposition: CAPTURE_CHEAP_OPTIONALITY for BBO-derived fields; policy use deferred.

## U04 — AP1/AP2/AP3/AP4 Attempt policy

Question: fixed bps, vol-normalized, time/no-followthrough or price+time hybrid?

Evidence: causal Attempt first-passage and recovery curves after exact Activation.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U05 — exact Stop / time threshold

Question: which threshold best separates failed timing from ordinary micro-noise?

Evidence: Forward Attempt MAE/MFE, time-to-progress, recovery after adverse thresholds, false-scratch value.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U06 — Re-entry: none vs one fresh activation

Question: does one fresh Re-entry recover enough missed winners to justify extra friction?

Evidence: same-Thesis paired R0 no-Reentry vs R1 one-fresh-Reentry.

Metrics: total Thesis net R, cumulative scratch cost, eventual winner probability, marginal EV Attempt 2.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U07 — Attempt 3+

Question: is there any positive marginal after-cost value after two total Attempts?

Evidence/reopen trigger: Attempt 2 must first show material positive incremental Forward value and a specific causal hypothesis must justify Attempt 3.

Criticality: OPTIONAL.
Disposition: PARK_OR_REJECT until trigger.

## U08 — Winner Confirmation WC0/WC1/WC2/WC3

Question: when should control transfer from Probe failure logic to slower Winner logic?

Evidence: Forward comparison of favorable progress, persistence, fresh structure, then flow acceptance only if incremental.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U09 — Exit X0/X1/X2/X3

Question: fixed-R, structural full exit, MFE giveback, or structural+giveback?

Evidence: identical Entry/Attempt/Winner paths with Exit only changed.

Metrics: net R, right-tail capture, MFE capture, giveback, profit-to-loss flip, drawdown, holding time, re-entry friction.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U10 — MFE giveback threshold 1/3 vs 1/2 vs 2/3

Question: how much open-profit giveback best preserves right tail without allowing avoidable reversal?

Evidence: preregistered C1 grid in E4/E5.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U11 — partial take-profit / scale-out

Question: can partial realization reduce profit-to-loss flips enough to compensate for surrendered right tail and extra execution complexity?

Evidence/reopen trigger: first X0-X3 must show a material unresolved giveback problem.

Criticality: OPTIONAL.
Disposition: PARK_OR_REJECT for C1; reopen on trigger.

## U12 — maker-on-retest vs marketable/taker Entry

Question: does maker fee savings exceed non-fill, queue/adverse-selection and missed-runaway costs?

Evidence: conservative passive-order replay; later actual fill calibration if separately authorized.

Criticality: MATERIAL_OPTIMIZATION, not E4 data blocker.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U13 — high-friction BTC/ETH viability

Question: can the same structural Strategy become positive after costs by using higher participation hurdle, lower retry churn and longer right-tail capture?

Evidence: friction-conditioned paired Forward results, not generic crypto momentum literature.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.
Reject if after-cost Forward expectancy remains non-positive under realistic execution.

## U14 — dynamic ROOM_TO_COST hurdle k={2,3,4}

Question: does cost-normalized structural room improve participation versus market-blind thresholds?

Evidence: paired same-Opportunity Forward comparison.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U15 — full L2 / multi-level OFI / resiliency

Question: does deeper book evidence add stable incremental value beyond BBO+TradeTick+flow-response, or is it only extra complexity?

Evidence/reopen trigger: simple first-stage features plateau with a prespecified residual question; or L1/top10 cannot model intended size.

Criticality: OPTIONAL.
Disposition: PARK_OR_REJECT for first E4.

## U16 — true L3/L4 / queue position

Question: required only if a material maker-queue hypothesis cannot be answered by L2/top10.

Criticality: OPTIONAL/high burden.
Disposition: PARK_OR_REJECT.

## U17 — OI/funding/basis timing value

Question: are these useful only as slow context or do they add entry-timing value?

Evidence: low-rate Forward capture and later incremental test.

Criticality: OPTIONAL.
Disposition: CAPTURE_CHEAP_OPTIONALITY while burden remains low.

## U18 — external/cross-venue reference value

Question: does Hyperliquid-local price discovery diverge often enough from external spot/futures/reference markets to create material false activations?

Evidence/reopen trigger: observed Shadow failure clusters attributable to venue-local divergence.

Criticality: OPTIONAL.
Disposition: PARK_OR_REJECT until trigger; mark/index remain current reference inputs.

## U19 — final Discovery/Actionable universe breadth

Question: what market count maximizes unique after-cost opportunity value net of correlation, capital contention and data burden?

Evidence: Forward opportunity density, edge, correlation and capacity by market.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.
Current seed 20 is research seed, not cap.

## U20 — current 2304 x 5m warmup necessity

Question: can warmup depth be reduced without changing current Three Setup/Scanner semantics?

Evidence: exact equivalence study against current Champion outputs.

Criticality: OPTIONAL unless Engineering demonstrates material burden.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER; keep existing depth meanwhile.

## U21 — top10 / size-aware execution

Question: when does L1 cease to be a credible fill model for intended notional?

Evidence: compare desired notional with L1 capacity and top10 VWAP when available.

Criticality: HARD_BLOCKER only for observations whose size exceeds credible L1 capacity; otherwise optional.
Disposition: SHOULD_HAVE / ACQUIRE_BEFORE_NEXT_GATE only when the affected size claim requires it.

## U22 — actual vs hypothetical slippage and fee error

Question: how accurately does public-data Shadow predict future actual fills?

Evidence: later separately authorized Testnet and tiny Mainnet human-approved execution.

Criticality: HARD_BLOCKER for real-capital execution-model acceptance, not for E4 Strategy Shadow.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER until execution stage.

## U23 — latency sensitivity

Question: how much edge decays between causal decision and actionable order arrival?

Evidence: provider/local/decision/order-active timestamps in Shadow; actual execution later.

Criticality: MATERIAL_OPTIMIZATION / later execution blocker.
Disposition: capture required timing now; optimize later.

## U24 — fee-state drift / Growth Mode / deployer fee

Question: how often effective friction changes enough to alter participation decisions?

Evidence: versioned fee profile/state at every Opportunity and later observed actual fee.

Criticality: HARD correctness requirement for after-cost claims.
Disposition: ACQUIRE_BEFORE_NEXT_GATE through current provider/account-configured fee-state evidence; no asset-class hardcode.

## U25 — right-tail concentration

Question: is positive expectancy structurally dependent on one or a few extreme winners?

Evidence: top-winner contribution and leave-top-winner-out sensitivity in E4/E5.

Criticality: MATERIAL promotion risk.
Disposition: ACQUIRE_BEFORE real-capital promotion through Forward sample; concentration is warning, not automatic rejection.

## U26 — Strategy performance by friction regime

Question: does low-friction and high-friction policy overlay remain one coherent Strategy or require future separate policy versions?

Evidence: Forward subgroup results with >=30 completed Theses per claimed regime before regime-specific claims.

Criticality: MATERIAL_OPTIMIZATION.
Disposition: PROCEED_WITH_CURRENT_BEST_AND_DEFER.

## U27 — setup-specific parameterization

Question: should Sweep/Reclaim, Breakout/Retest and Range Edge use different EA/AP/WC/X thresholds?

Evidence/reopen trigger: common-parameter policy must first show stable systematic setup-specific residual errors with enough sample.

Criticality: OPTIONAL/high overfit risk.
Disposition: PARK_OR_REJECT for C1.

## U28 — regime-adaptive Exit

Question: does volatility/regime-specific Exit materially outperform X0-X3 after costs?

Evidence/reopen trigger: simple Exit family plateaus with a clear regime-specific error mode.

Criticality: OPTIONAL.
Disposition: PARK_OR_REJECT for first pass.

## U29 — ML Meta-Gate

Question: can a calibrated statistical model improve TAKE/WAIT/PASS beyond interpretable rules without selection/counterfactual bias?

Prerequisite: clean Opportunity denominator, point-in-time features, strong rule baseline, sufficient sample, defensible counterfactual labels.

Criticality: future OPTIONAL/MATERIAL.
Disposition: PARK_OR_REJECT now; explicit reopen after prerequisite data exists.

## U30 — autonomous trading

Question: whether Strategy quality, execution safety and operational controls ever justify risk-limited autonomous policy.

Prerequisites: separately governed future program after human-approved execution evidence, kill/reconciliation/risk controls and explicit user authority.

Criticality: OUT OF CURRENT SCOPE.
Disposition: PARK_OR_REJECT now.

## Current frontier summary

```text
DATA_BLOCKED_FRONTIER_ITEMS=NONE_FOR_FIRST_E4_SHADOW
E4_CORE_BARS_BBO_TRADES_REFERENCE_COST_IDENTITY=ACQUIRE_BEFORE_NEXT_GATE
LOW_RATE_OI_FUNDING_CONTEXT=CAPTURE_CHEAP_OPTIONALITY
ARBITRARY_HISTORICAL_BBO_L2_OI_DEEP_TRADES=PROCEED_WITH_CURRENT_BEST_AND_DEFER
FULL_L2_L3_L4_RICH_ID_ML=Park_or_reject until exact reopen trigger
FINAL_NUMERIC_EA_AP_WC_X_PARAMETERS=PROCEED_WITH_CURRENT_BEST_AND_DEFER_TO_E4_E5
```

No item may disappear from this ledger merely because implementation chooses a default. A resolved item must record the evidence/version that resolved it; a rejected/deferred item must keep its reopen trigger or explicit terminal rejection.
