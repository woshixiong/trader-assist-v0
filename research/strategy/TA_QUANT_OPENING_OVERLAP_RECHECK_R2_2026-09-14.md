# Trade OS — Quant Opening Overlap Recheck R2

**Status:** RESEARCH DECISION ADDENDUM / NON-EXECUTABLE / BRANCH-ONLY / NO PR  
**Date:** 2026-09-14  
**Repository:** `woshixiong/trader-assist-v0`  
**Branch:** `research/quant-opening-event-r1-20260914`  
**Parent research:** `TA_QUANT_OPENING_EVENT_RESEARCH_R1_2026-09-14.md`

This addendum rechecks whether the proposed post-open research is economically distinct from the existing Three Setup + VNext Entry Activation / TAKE-WAIT-PASS architecture. It supersedes the R1 terminal disposition only for the question of whether a separate local opening strategy/overlay deserves continued research.

It grants no production Strategy change, E4 Writer dispatch, merge, deployment, private/account API, exchange write, or real-capital authority.

## 1. Evidence rechecked

Project-side comparison used:

- current Three Setup Strategy Kernel on live main;
- Issue #82 intraday time/opening research freeze;
- Issue #161 Strategy Research Master Plan;
- Draft PR #168 VNext E4 C1 Strategy candidate;
- R1 Opening Event candidate.

External/mature evidence was rechecked for opening-range breakout, call-auction price discovery, cash/futures lead-lag, Nasdaq Opening Cross / NOII, and KRX opening call-auction mechanics.

## 2. Mechanical overlap result

| Opening R1 concept | Existing Trade OS equivalent | Overlap |
| --- | --- | --- |
| `OPEN_DIRECTIONAL_ACCEPTANCE` | `BREAKOUT_RETEST` plus VNext `EA1 DIRECT_REACCEL_PRICE`, `EA2 RETEST_REACCEL_PRICE`, optionally `EA3` flow acceptance | HIGH |
| `OPEN_FAILED_IMPULSE_RECLAIM` | `SWEEP_RECLAIM` / failed-breakout-to-reclaim structure | HIGH |
| opening-range edge rejection | `RANGE_EDGE_REJECTION` when the relevant boundary/range is causally valid | HIGH |
| `OPEN_TWO_WAY_CHAOS -> WAIT` | existing `TAKE / WAIT / PASS`, `WAIT_FOR_OPENING_CHAOS_RESOLUTION`, no-followthrough / friction logic | HIGH |
| local BBO/trades flow confirmation | VNext `EA3 SIMPLE_FLOW_PRICE_RESPONSE_ACCEPTANCE` | DIRECT DUPLICATION |
| `OPEN_NORMALIZED` | retirement of opening context; normal Strategy resumes | NOT A STRATEGY |
| fixed +15m no-entry | time/risk permission rule | NOT ALPHA |
| cash opening auction / NOII / expected-match / cash-perp-oracle lead-lag | no direct current Three Setup equivalent | POTENTIALLY UNIQUE |

The R1 local O1/O2 architecture therefore does not establish a new economic mechanism. It mostly renames existing structural and activation states inside a scheduled time window.

## 3. Revised interpretation

The opening itself is a **regime/event boundary**, not sufficient alpha authority.

For the current quant architecture:

```text
OPENING TIME
-> CONTEXT / ATTRIBUTION TAG

THREE_SETUP
-> WHAT / WHERE / SIDE

VNEXT ACTIVATION + MICROSTRUCTURE
-> WHEN / SHORT-HORIZON ACCEPTANCE

FRICTION / EXECUTION GATES
-> WHETHER TRADEABLE
```

Therefore a local-only `Opening Strategy` is unnecessary unless future evidence proves an effect that cannot be expressed by those existing layers.

## 4. Fixed 15-minute rule

Issue #82 already freezes the principle that time-of-day alone must not veto a valid Three Setup. Issue #161 likewise treats fixed wait seconds as research checkpoints, not the preferred policy architecture.

Research disposition:

```text
FIXED_15M_HARD_TIME_VETO_AS_QUANT_POLICY=CANDIDATE_REMOVE
REMOVE_NORMAL_THREE_SETUP_OR_EXECUTION_GATES=NO
BLIND_TRADE_FROM_OPEN=NO
OPENING_CONTEXT_TAG=KEEP
```

Removing the hard time veto means that a valid existing Strategy Opportunity may proceed from the open **only if the same normal causal Setup, Activation, friction, data-integrity and execution gates pass**. It does not create automatic opening participation.

Because removing the veto changes the opportunity set, production promotion still requires a bounded matched comparison. This is a rule ablation, not a new Strategy research program.

## 5. Minimum required validation — one ablation only

Freeze all Strategy economics and compare:

```text
A0 = EXISTING THREE_SETUP + VNEXT ACTIVATION / FRICTION, NO FIXED 15M TIME VETO
A1 = EXACT SAME STRATEGY + FIXED 15M TIME VETO
```

Same markets, same opening events, same causal data, same execution/cost assumptions.

Primary paired metrics:

```text
THESIS_NET_R_AFTER_COST
TAIL_MAE / DRAWDOWN
FALSE_ACTIVATION / SCRATCH COST
MISSED_WINNER_VALUE
RIGHT_TAIL_PNL_RETAINED
ENTRY DELAY / CHASE COST
```

No O1/O2 parameter search is justified before this ablation.

Decision rule:

```text
IF A0 materially preserves/improves after-cost expectancy
AND does not create unacceptable tail/execution deterioration
=> REMOVE FIXED 15M VETO; STOP LOCAL OPENING STRATEGY RESEARCH

IF A0 materially deteriorates specifically during opening events
=> diagnose the exact failure mode before adding any opening-only rule
```

## 6. The only currently plausible unique opening research

The cash-market opening mechanism can expose information not contained in Hyperliquid-local Three Setup state, for example:

```text
OPENING AUCTION CLEARING / INDICATIVE PRICE
ORDER IMBALANCE / EXPECTED MATCH STATE
CASH BBO / TRADES
HYPERLIQUID LOCAL BBO / TRADES
MARK / INDEX / ORACLE
CROSS-MARKET LEAD-LAG / DIVERGENCE
```

This is an exogenous cross-market information hypothesis, not an Opening Range Breakout rewrite.

However, it should remain parked unless one of these triggers occurs:

1. the A0-vs-A1 ablation shows a material opening-specific failure that local existing Strategy state cannot explain;
2. cash/auction data is already available at low burden and can be tested as an incremental feature;
3. a prespecified cross-market divergence/lead-lag hypothesis shows stable incremental OOS/Forward value beyond A0.

Even then, first test it as an incremental context/activation feature. Promote a distinct Opening Setup only if it produces stable causal after-cost OOS/Forward value on opportunities that the existing Three Setup architecture does not capture.

## 7. External evidence synthesis

Opening-range breakout is mechanically a breakout/momentum rule tied to the opening level/range, so it is conceptually close to the existing breakout family rather than evidence of an independent mechanism. Published ORB results also show regime instability across subperiods, which argues against adding a dedicated Strategy merely because the open is volatile.

Opening auctions are nevertheless structurally special price-discovery events. Nasdaq disseminates Opening Cross imbalance information before the cross, and KRX determines the opening price via a call auction. Classic cash/futures evidence also shows that leadership can run from derivatives to cash, so a future cross-market feature must measure lead-lag rather than assume `cash -> perp` causality.

## 8. Revised terminal disposition

```text
DISTINCT_LOCAL_OPENING_STRATEGY_RESEARCH=PARK_OR_REJECT
OPENING_AS_FOURTH_SETUP=NO
R1_O1_LOCAL_STATE_RELEASE=REDUNDANT_WITH_EXISTING_ARCHITECTURE
R1_O2_LOCAL_MICRO_RELEASE=REDUNDANT_WITH_VNEXT_EA3
FIXED_15M_HARD_TIME_VETO=CANDIDATE_REMOVE_FROM_QUANT_POLICY
OPENING_CONTEXT_AND_ATTRIBUTION=KEEP
NEXT_REQUIRED_TEST=A0_VS_A1_MINIMUM_ABLATION_ONLY
CROSS_MARKET_AUCTION_LEAD_LAG=OPTIONAL_UNIQUE_HYPOTHESIS_PARKED_UNTIL_TRIGGER
E4_IMPLEMENTATION_NOW=NO
```

The research frontier is now narrower: do not spend additional Strategy-design effort on a local opening policy unless the minimum ablation or a genuine cross-market information hypothesis creates a decision-changing trigger.