# Trade OS — Opening A0/A1 Validation Binding R3

**Status:** RESEARCH VALIDATION BINDING / NON-EXECUTABLE / BRANCH-ONLY / NO PR  
**Date:** 2026-09-14  
**Repository:** `woshixiong/trader-assist-v0`  
**Branch:** `research/quant-opening-event-r1-20260914`  
**Parent:** `TA_QUANT_OPENING_OVERLAP_RECHECK_R2_2026-09-14.md`

This record closes one narrow omission discovered during a fresh GitHub recheck: the exact `A0 vs A1` opening-time-veto ablation is defined in R2, while Draft PR #168 provides the generic G2/G3/G4/G5 validation machinery but does not yet name this later research variant explicitly.

This file does not modify main, Draft PR #168, E4 implementation, current production behavior, or any current human trading rule. It creates no exchange-write, real-capital, merge, Mark Ready, or deployment authority.

## 1. Frozen ablation identity

```text
A0 = EXISTING THREE_SETUP + VNEXT ACTIVATION / FRICTION, NO FIXED 15M TIME VETO
A1 = EXACT SAME STRATEGY + FIXED 15M TIME VETO
```

Only the time-veto component may differ. Same market universe, same Three Setup semantics, same Entry Activation family, same friction/execution gates, same data-quality rules, same execution/fill model, same fee profile, and same causal input path.

## 2. Required placement in the existing validation ladder

The ablation must use the already-defined PR #168 validation architecture when the final E4 package is reopened and authorized.

```text
G2 RETROSPECTIVE PAIRED REPLAY
-> evaluate A0 and A1 on the same eligible Opportunity / Thesis paths

G3 CHRONOLOGICAL OOS / WALK-FORWARD
-> exact frozen A0/A1 identities; no post-hoc threshold tuning

G4 E4 LIVE CAUSAL SHADOW
-> prospectively evaluate A0 and A1 on the same live causal path where inputs permit
-> all hypothetical orders remain NOT_SUBMITTED
-> retain TAKE / WAIT / PASS / BLOCKED and counterfactual outcomes

G5 E5 FRESH FORWARD
-> if A0 is selected as the candidate removal policy, collect fresh immutable Forward evidence on A0
-> retain A1 as the paired/reference policy where causally evaluable
-> no production removal claim from retrospective evidence alone
```

A0/A1 therefore is not a separate Opening Strategy program. It is one bounded rule ablation inside the normal Strategy validation ladder.

## 3. Minimum data requirement

No continuous full-opening-window archive is required solely for this ablation when no Three Setup Opportunity exists.

For each eligible Three Setup Opportunity that falls inside or around the relevant underlying-market opening boundary, retain enough causal evidence to reconstruct both variants:

```text
underlying/session/open identity and scheduled open timestamp
opportunity / thesis / setup / side identity
decision timestamp and event-time distance from open
A0 decision + reason
A1 decision + reason, including FIXED_15M_VETO when applicable
BBO / trades / 1m / 5m / mark-index-reference data already required by the applicable VNext candidate
hypothetical order-active timestamp and executable modeled fills
fees / slippage / impact / capacity state
MAE / MFE / missed-winner / scratch / right-tail outcomes
```

The crucial anti-selection-bias requirement is that an Opportunity suppressed by A1 during the first 15 minutes must still remain observable as a counterfactual A0 Opportunity. It must not disappear from the denominator merely because A1 would not trade it.

## 4. Metrics

Primary paired metrics remain:

```text
THESIS_NET_R_AFTER_COST
THESIS_NET_PNL_AFTER_COST
TAIL_MAE / DRAWDOWN
FALSE_ACTIVATION / SCRATCH COST
MISSED_WINNER_VALUE
RIGHT_TAIL_PNL_RETAINED
ENTRY DELAY / CHASE COST
FEES / SLIPPAGE SHARE OF GROSS EDGE
```

Also report by opening/session context where sample permits, with correlated event clustering rather than treating simultaneous storage-stock opportunities as independent observations.

## 5. Decision / promotion rule

```text
IF A0 preserves or improves after-cost expectancy
AND does not cause unacceptable tail / execution deterioration
AND survives the applicable chronological OOS + E4 Shadow + E5 Forward gates
=> fixed 15m veto may be removed from the future quant policy under a separately reviewed Strategy version

IF A0 materially deteriorates specifically in opening windows
=> keep/reopen the protection question and diagnose the exact failure mode before inventing an opening-only strategy
```

Retrospective backtest success alone is insufficient to remove the rule from a promoted quant policy.

## 6. Current rule disposition

```text
REMOVE_15M_RULE_NOW=NO
CURRENT_ACTIVE_CODE_CHANGE=NO
CURRENT_HUMAN_RULE_CHANGE=NO
CURRENT_THREE_SETUP_AUTHORITY_CHANGE=NO
E4_IMPLEMENTATION_NOW=NO
A0_A1_FUTURE_G2_G3_G4_G5_BINDING=YES_AT_RESEARCH_BRANCH_LEVEL
CANONICAL_PR168_INTEGRATION=REQUIRED_BEFORE_E4_RESTART
```

Note: the current live-main Three Setup Strategy Kernel is clock-free and does not itself implement a fixed 15-minute opening veto. Therefore there is no current Strategy-Kernel line to delete now. The relevant future decision is whether a fixed opening-time veto should be added/retained in the future VNext quant participation policy; that decision remains pending the A0/A1 validation above.
