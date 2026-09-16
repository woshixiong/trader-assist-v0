# Strategy Research Decision Archive — through 2026-09-11

Status: HISTORICAL / NON-AUTHORITATIVE EXCEPT AS RATIONALE
Purpose: preserve traceability for decisions that were previously used, researched, narrowed, superseded, deferred or rejected. Current authority remains the latest accepted Product/Strategy/Engineering GitHub state.

This file does not duplicate every historical Issue comment. It indexes the material historical conclusions and points to their canonical GitHub discussion homes so future reviewers can reconstruct why the project changed direction.

## Canonical historical homes

- #161 — Strategy Research Master Plan / Selective Participation / Meta-Gate / WAIT / Entry research.
- #150 — Machine Position Strategy / Attempt / Re-entry / Winner / position management.
- #85 — detailed Shadow/Forward and Exit research matrix.
- #163 — Nautilus transition / capability and Engineering handoff.
- #18 — Product baseline and later user-approved Strategy-source amendment.
- #93 — Operations sequencing and safety triggers.

## A01 — ETH-only First Launch as terminal product route

Historical conclusion: original First Launch focused on ETH-only manual execution and legacy custom runtime.

Current status: SUPERSEDED AS TERMINAL ROUTE.

Replacement: #18 comment `5581144976`, #93 comment `5581148643`, #163 mature Nautilus-based sequence. Historical rationale remains useful; current route is Shadow -> zero-write approval -> separately authorized Testnet -> Strategy/Nautilus gates -> tiny Mainnet canary -> human-approved V0.

## A02 — exact historical five-strategy Full-V0 binding

Historical conclusion: `LQS-FR`, `BRK-AR`, `TRD-PB`, `BAL-RV`, `MACRO-RP` were frozen as exact future Strategy families.

Current status: SUPERSEDED.

Replacement: #18 comment `5581144976`: current stable base is Three Setup and future execution uses the latest evidence-promoted frozen Strategy/Policy/Parameter version.

## A03 — Target-12 as permanent universe cap

Historical conclusion: launch/qualification planning used a 12-market hard cap.

Current status: RETIRED.

Replacement: #163 capability audit / Strategy handoff. Universe is Strategy-value driven and Engineering separately qualifies scale/freshness.

## A04 — Target-20 as a permanent cap

Historical conclusion: 20 markets appeared as a later qualification/reference population.

Current status: RETIRED AS CAP; retained only as current research seed/preferred first E4 breadth.

Replacement: dynamic Discovery universe + Actionable subset; no permanent Strategy count before marginal-value evidence.

## A05 — K-line / 1m bars sufficient for final machine Entry/Stop research

Historical conclusion: bar evidence could answer most short-horizon machine-position questions.

Current status: RETIRED.

Replacement: bars remain structural authority; causal BBO and TradeTick are required for executable short-horizon Entry/Attempt evidence. Full L2 is not first-stage mandatory.

## A06 — raw order flow / CVD / book walls as an independent directional Setup

Historical/research idea: raw flow could become a separate Setup/directional authority.

Current status: REJECTED.

Replacement: Three Setup supplies side/location; order flow/microstructure supplies timing/quality/acceptance/execution evidence only.

## A07 — fixed WAIT seconds as production policy

Historical idea: use fixed 30/60/120/300-second delays as WAIT policy.

Current status: REJECTED AS POLICY.

Replacement: WAIT is state/event-driven. Fixed times remain diagnostic/counterfactual checkpoints.

## A08 — blind immediate Re-entry

Historical idea/control: immediately re-enter after a scratch while Thesis remains valid.

Current status: REJECTED AS PREFERRED POLICY; retained as negative control.

Replacement: fresh causal Activation required. C1 first comparison is no-Reentry vs one fresh-Activation Re-entry.

## A09 — `PnL < 0 => EXIT` / any red PnL as machine Stop

Historical/manual heuristic: immediately close whenever the position becomes slightly negative.

Current status: REJECTED AS FINAL MACHINE RULE.

Replacement: separate price failure, time/no-followthrough, state failure, hard protective Stop and slower Thesis invalidation; exact threshold remains empirical.

## A10 — calibrating machine Stop from old Formal-time fills

Historical risk: infer new Attempt Stop from the distribution created by the previous Entry timing.

Current status: REJECTED.

Replacement: Entry Activation and Attempt policy are jointly causal. Stop calibration occurs only after exact candidate Activation identity exists.

## A11 — one universal fee assumption / asset-name fee class

Historical simplification: treat BTC/ETH as high-fee and RWA as low-fee fixed classes.

Current status: REJECTED.

Replacement: versioned effective fee/execution profile; Growth Mode, account tier, maker/taker path, deployer fee, spread/slippage and funding determine current friction.

## A12 — high fee => do not trade

Historical simplification: avoid BTC/ETH because fees are higher.

Current status: REJECTED.

Replacement: same structural Strategy with friction-conditioned participation/retry/winner-exit economics; viability remains a Forward hypothesis.

## A13 — high fee => automatically widen losing Stop

Historical possible inference from cost amortization.

Current status: REJECTED.

Replacement: friction changes participation, retry and voluntary churn thresholds; it never overrides hard protective Stop or structural invalidation.

## A14 — low fees license frequent retry/churn

Historical risk from cheap RWA execution.

Current status: REJECTED.

Replacement: every new Attempt requires fresh causal information; cumulative friction still counts.

## A15 — unlimited Attempts while Thesis valid

Historical possible interpretation of `Attempt != Thesis`.

Current status: REJECTED FOR C1.

Replacement: initial Attempt + at most one fresh Re-entry in C1. Attempt 3+ parked until Attempt 2 shows material incremental Forward value.

## A16 — microstructure flip remains automatic Exit authority after Winner Confirmation

Historical possible carry-forward from fast Probe logic.

Current status: REJECTED.

Replacement: after Winner Confirmation, control migrates to slower structure / right-tail / giveback policy; short-horizon flow remains supporting evidence only.

## A17 — fixed TP as preferred Winner policy

Historical baseline: fixed TP1/TP2 or fixed-R profit exit as main authority.

Current status: DEMOTED TO CONTROL.

Replacement: first bounded horse race X0 fixed-R control, X1 structural full exit, X2 MFE giveback, X3 structural+giveback.

## A18 — partial scale-out as first-pass default

Historical/manual experiment: realize ~40% during pullback and keep remainder for trend continuation.

Current status: DEFERRED, NOT REJECTED FOREVER.

Replacement: first resolve X0-X3. Reopen only if simple full-exit policies show material profit-to-loss/giveback failure that bounded scale-out can causally improve.

## A19 — full L2 required before first microstructure Strategy test

Historical research pressure: richer book data might be necessary for Entry/Stop research.

Current status: DEFERRED / NOT FIRST-STAGE REQUIREMENT.

Replacement: bars+BBO+TradeTick+flow-response first. Reopen full L2 only for measured incremental value or size-aware execution need.

## A20 — true L3/L4 / actor/spoof attribution needed for first Strategy

Historical possibility from order-book research.

Current status: PARKED/REJECTED FOR C1.

Replacement: no L3/L4, queue-position, actor/wallet/spoof model until a material hypothesis cannot be answered with simpler data.

## A21 — project-owned custom generic market-data/reconnect/backtest stack as default future route

Historical architecture: Trade OS would own large amounts of commodity transport/replay infrastructure.

Current status: SUPERSEDED under Nautilus mature-infrastructure route.

Replacement: mature Nautilus/provider-native transport/backtest/live mechanics + thin Trade OS Strategy/evidence layer.

## A22 — strict whole-universe synchronization for every decision

Historical Scanner inference: every downstream market decision could remain cohort-synchronous.

Current status: NARROWED.

Replacement: strict same-closed-5m boundary for cross-sectional Scanner ranking; asynchronous per-market point-in-time Entry/Attempt/Winner after promotion to Actionable state.

## A23 — discovery universe equals execution-quality universe

Historical architecture pressure: same feeds for every market.

Current status: REJECTED FOR C1.

Replacement: broad cheap Discovery on bars/context; BBO/trades only become mandatory for Actionable/Thesis-active markets.

## A24 — HFT/latency race as possible project edge

Historical/general microstructure possibility.

Current status: REJECTED.

Replacement: fast data improves timing/execution quality; Trade OS does not compete in microsecond latency-arbitrage races.

## A25 — large opaque score / HMM / RL / deep-learning first

Historical/future advanced-model possibility.

Current status: PARKED/REJECTED FOR CURRENT STAGE.

Replacement: empirical curves -> simple rules -> calibrated linear/logistic -> simple tree only if incremental OOS/Forward value. No opaque model before clean data and strong baseline.

## A26 — historical order-flow backfill must precede first E4 Forward Shadow

Historical concern: arbitrary-range BBO/L2/trade history might be necessary before causal Strategy research could proceed.

Current status: REJECTED AS A HARD PRE-E4 REQUIREMENT.

Replacement: current live capability is enough for first E4 causal Shadow. Historical provider archives may be qualified later for exact decisions; speculative backfill platform is not authorized.

## A27 — old OOS remains pristine after repeated inspection

Historical risk across repeated Strategy rounds.

Current status: REJECTED.

Replacement: `LEGACY_OOS_NOT_PRISTINE`; real promotion requires new immutable Forward evidence and prospective trial logging.

## A28 — backtest PnL is sufficient proof of Strategy quality

Historical/general failure mode.

Current status: REJECTED.

Replacement: deterministic causal replay + chronological OOS + E4 Shadow + E5 fresh Forward + after-cost/robustness/selection-bias controls. Testnet validates execution rather than alpha.

## A29 — only taken/fill data is sufficient research evidence

Historical/manual-trading bias risk.

Current status: REJECTED.

Replacement: retain every eligible Opportunity including WAIT/PASS/BLOCKED and counterfactual candidate paths; otherwise participation research is selection-biased.

## A30 — changing a Forward candidate in place

Historical generic workflow risk.

Current status: REJECTED.

Replacement: every material Strategy/Policy/Parameter/Derivation change creates a new immutable version and starts a new Forward evidence clock.

## Archive rule

When a future conclusion is superseded, do not delete its rationale from GitHub. Add an archive entry containing:

```text
OLD_CONCLUSION
SOURCE_POINTER
DATE/RANGE
WHY_SUPERSEDED_OR_REJECTED
REPLACEMENT_AUTHORITY
REOPEN_TRIGGER_IF_ANY
```

Historical evidence remains auditable but never silently regains authority over newer live GitHub decisions.
