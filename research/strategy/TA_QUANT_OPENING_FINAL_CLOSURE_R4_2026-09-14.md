# Trade OS — Quant Opening Research Final Closure R4

**Status:** TERMINAL RESEARCH CLOSURE / NON-EXECUTABLE / BRANCH-ONLY / NO PR  
**Date:** 2026-09-14  
**Repository:** `woshixiong/trader-assist-v0`  
**Branch:** `research/quant-opening-event-r1-20260914`

This record supersedes the R2/R3 disposition only where those branch-only notes could be read as creating a required `A0/A1` validation obligation before E4/E5.

## 1. Fresh canonical recheck

The current canonical quant direction does **not** contain a fixed first-15-minute no-trade veto:

- live-main Three Setup Strategy Kernel is clock-free and contains no session/open-time veto;
- Issue #82 states that time-of-day alone must not veto a valid Three Setup and that future boundary recovery should be dynamic rather than a hard-coded clock rule;
- Issue #161 rejects fixed WAIT seconds as production policy and keeps opening as context rather than a fourth Setup;
- Draft PR #168 `TA_VNEXT_E4_C1` contains no fixed 15-minute opening veto in Strategy, Activation, friction, Attempt, Winner or Exit policy.

Therefore there is no current quant Strategy rule that must be removed before E4/E5.

## 2. A0/A1 disposition

The prior branch-only labels were:

```text
A0 = EXISTING THREE_SETUP + VNEXT ACTIVATION / FRICTION, NO FIXED 15M TIME VETO
A1 = EXACT SAME STRATEGY + FIXED 15M TIME VETO
```

Final interpretation:

```text
A0 = already consistent with the current canonical quant direction
A1 = optional counterfactual / negative-control research variant only
```

Because A1 is not a current or planned mandatory quant rule, proving A0 superior to A1 is **not** a prerequisite for E4 or E5.

The A0/A1 pair may be run later as a cheap diagnostic if data is already available, but it must not block E4/E5, must not be silently promoted to a mandatory test, and must not cause extra product/data/infrastructure scope by itself.

## 3. Review / merge disposition

The opening R1/R2/R3/R4 branch contains research notes only and changes no runtime, Strategy code, PR #168, production policy or execution authority.

Final disposition:

```text
OPENING_RESEARCH_BRANCH_REVIEW_REQUIRED=NO
OPENING_RESEARCH_BRANCH_MERGE_REQUIRED=NO
PR_REQUIRED=NO
MAIN_CHANGE_REQUIRED=NO
PR168_CHANGE_REQUIRED_FOR_15M_RULE=NO
E4_PRECONDITION_CREATED_BY_A0_A1=NO
E5_PRECONDITION_CREATED_BY_A0_A1=NO
```

Do not merge the branch merely to preserve the exploratory opening study. It remains non-canonical research history unless a future independently justified hypothesis reopens it.

## 4. Quant Strategy rule freeze for E4/E5 planning

For the quant system only:

```text
FIXED_FIRST_15M_NO_TRADE_VETO=NO
OPENING_AS_FOURTH_SETUP=NO
OPENING_TIME_AS_DIRECTIONAL_ALPHA=NO
NORMAL_THREE_SETUP_AUTHORITY=YES
VNEXT_ACTIVATION_AND_FRICTION_GATES=YES
OPENING/SESSION_CONTEXT_TAGGING=ALLOWED_AS_CONTEXT
```

A valid Three Setup / VNext Opportunity is not rejected solely because it occurs inside the first 15 minutes after the relevant cash-market open. It must still pass all normal causal data, Activation, participation, friction and execution requirements.

## 5. Terminal research disposition

```text
QUANT_OPENING_RESEARCH=TERMINALLY_CLOSED_FOR_CURRENT_PRE_E4_SCOPE
LOCAL_OPENING_STRATEGY=REJECTED_AS_REDUNDANT
CROSS_MARKET_AUCTION_OR_LEAD_LAG=OPTIONAL_FUTURE_REOPEN_ONLY_ON_NEW_EVIDENCE
NO_PRE_E4_OR_PRE_E5_CHANGE_REQUIRED_FROM_THIS_RESEARCH=YES
```

Reopen only if future E4/E5 evidence identifies a stable opening-specific failure mode that cannot be represented by the existing Three Setup + VNext Activation / participation / friction architecture, or if genuinely exogenous auction/cross-market information shows prespecified incremental causal OOS/Forward value.
