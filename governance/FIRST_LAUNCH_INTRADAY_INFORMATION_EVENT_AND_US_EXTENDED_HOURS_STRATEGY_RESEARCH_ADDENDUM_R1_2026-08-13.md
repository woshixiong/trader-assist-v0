# First Launch Intraday Information-Event and U.S. Extended-Hours Strategy Research Addendum R1

**Record ID:** `TA-FIRST-LAUNCH-INTRADAY-EVENT-EXTENDED-HOURS-RESEARCH-R1-2026-08-13`  
**Date:** `2026-08-13`  
**Repository:** `woshixiong/trader-assist-v0`  
**Related Draft PR:** `#52`  
**Status:** `POST-FIRST-LAUNCH RESEARCH ADDENDUM / NON-EXECUTABLE / NON-AUTHORIZING`  
**Related contracts:** Scheduled U.S. Macro Event R1; Scheduled Corporate Earnings Event R1; Post-Launch Research/Future Development Inventory R4.

---

## 1. Product-scope clarification: intraday event trading only

The intended future event-driven product scope is **short-horizon intraday trading**, not multi-day trend / PEAD investing.

```text
TARGET_HOLDING_HORIZON ~= 10 minutes to 120 minutes
PRIMARY_OBJECTIVE = capture multiple tradable micro-moves inside a larger information repricing process
MULTI_DAY_PEAD / MULTI_DAY_TREND = RESEARCH_REFERENCE ONLY, NOT PRODUCT TARGET
```

For an after-hours earnings event, an event window may cross a civil-calendar boundary in Asia, but individual strategy positions should still be evaluated as bounded intraday/event-window positions rather than multi-day holdings.

This addendum does not modify the current First Launch.

```text
CURRENT_RELEASE_CHANGE = NO
CURRENT_MACHINE_STRATEGY_CHANGE = NO
NEW_FORMAL_SETUP_NOW = NO
AUTO_TRADE_NOW = NO
```

---

## 2. Shared Scheduled Information Event architecture

Macro and earnings should share infrastructure but keep different interpretation semantics.

```text
SCHEDULED INFORMATION EVENT ENGINE
  ├── MACRO EVENT INTERPRETER
  │    CPI / PPI / NFP / PCE / later FOMC family
  └── CORPORATE EVENT INTERPRETER
       earnings / guidance / call / Q&A
```

Shared causal phases:

```text
PRE-EVENT EXPECTATION / POSITIONING
→ RELEASE / INFORMATION SHOCK
→ INITIAL REPRICING
→ ACCEPTANCE / FAILURE
→ SECOND-STAGE MICRO-MOVES
→ NO_TRADE / NEW BALANCE
```

The system should not assume the first post-release trade is the only opportunity. The research target is the sequence of micro-opportunities inside the broader repricing.

---

## 3. Important distinction: pre-event participation vs holding through release

These are two different strategies and must never be conflated.

### A. `PRE_EVENT_TREND_PARTICIPATION`

Trade an already-observable market trend / expectation positioning before the scheduled release.

Purpose:

```text
FOLLOW OBSERVED PRICE DISCOVERY
NOT PREDICT THE UNRELEASED NUMBER
```

Candidate event-relative windows may include, depending on event and session:

```text
T-6h
T-3h
T-90m
T-30m
T-5m
```

Exact windows are research parameters, not production rules.

### B. `CROSS_EVENT_CARRY`

Enter before the event and deliberately hold through the release timestamp.

This is a separate tail-risk strategy because a scheduled information shock can create discontinuous price gaps, spread expansion, slippage and stop non-executability at the modeled stop price.

Default research posture:

```text
PRE_EVENT_TREND_PARTICIPATION = RESEARCH YES
CROSS_EVENT_CARRY = SEPARATE RESEARCH / NOT DEFAULT
```

Cross-event carry should only be considered after explicit jump-risk / execution-cost evidence and a separately bounded risk budget.

### C. `POST_EVENT_REPRICING`

Trade continuation, micro-pause, shallow pullback, failed first move, or new-balance formation after the release.

The three paths must be compared rather than assuming `POST_EVENT_ONLY` is always superior.

---

## 4. “Buy the expectation, sell the fact” must be modeled, not used as a slogan

A strong pre-event trend followed by post-release reversal is a real research pattern, but it does not imply a universal rule.

Research construct:

```text
PRE_EVENT_POSITIONING
+
RELEASE INFORMATION RELATIVE TO PUBLIC CONSENSUS
+
RELEASE INFORMATION RELATIVE TO MARKET-IMPLIED EXPECTATION
→ EXPECTATION GAP
→ CONTINUATION / SATURATION / REVERSAL
```

Candidate research variables:

```text
pre_event_return_T6h
pre_event_return_T3h
pre_event_return_T90m
pre_event_return_T30m
pre_event_breadth / peer breadth
pre_event_relative_strength
pre_event_rates / DXY path for macro events
pre_event_implied_move / expectation distribution where available
actual standardized surprise vector
initial post-release move
impact retention / giveback
accepted re-entry / failed first move
```

The desired research question is not “Did consensus beat/miss?” but:

```text
HOW MUCH OF THE EVENT OUTCOME WAS ALREADY PRICED?
```

Potential labels (research-only):

```text
EXPECTATION_CONFIRMED
EXPECTATION_UNDERPRICED
EXPECTATION_SATURATED
EXPECTATION_CONTRADICTED
AMBIGUOUS
```

No fixed live thresholds are authorized.

---

## 5. Macro-event asset selection vs earnings-event asset selection

The user-level distinction is retained.

### Macro

Macro information is broad and the best trade expression is not fixed.

```text
MACRO EVENT
→ broad interpretation
→ dynamic EVENT ASSET ROUTER
```

Potential candidates include indices, high-beta sectors/single names and crypto.

### Earnings

The primary information asset is fixed by issuer, but the best **trade expression** can still differ.

```text
EARNINGS EVENT
→ announcing company is primary information asset
→ direct perp / peer / sector / index are bounded candidate trade expressions
```

Therefore earnings needs a narrower corporate-event router, not a full broad-universe macro router.

---

# 6. New independent research direction: U.S. Extended-Hours Session Strategy

TradeXYZ stock perpetuals have 24/5 external equity pricing coverage across U.S. pre-market, regular, post-market and overnight sessions. This creates a product-specific research opportunity.

Research the sessions separately:

```text
POST_MARKET = 16:00-20:00 ET
OVERNIGHT   = 20:00-04:00 ET
PREMARKET   = 04:00-09:30 ET
CASH_OPEN_RECONCILIATION = 09:30 onward
```

Do not assume all extended hours are one regime.

---

## 7. Why extended hours merits separate study

Extended-hours markets generally have lower liquidity and different quote/price-discovery dynamics than regular hours. Earnings announcements often occur after hours and can create substantial quote-based price discovery. Lower liquidity can amplify price impact.

At the same time, generic overnight returns can show continuation in some contexts and reversal in others. Therefore the user's observation that some TradeXYZ markets display smooth, persistent trends is valuable as a venue-specific hypothesis, but it must not be generalized into `overnight trend always continues`.

Primary distinction to research:

```text
INFORMATION-DRIVEN MOVE
vs
LIQUIDITY / INVENTORY-DRIVEN MOVE
```

Hypothesis:

```text
information-driven + retained impact + healthy tracking
→ continuation more plausible

large move + weak information catalyst + poor retention / liquidity distortion
→ reversal or cash-open reconciliation more plausible
```

This is a hypothesis, not a production rule.

---

## 8. Extended-hours candidate strategy families

### A. `EXTENDED_HOURS_TREND_CONTINUATION`

Research whether a stable directional move in post-market / overnight / premarket continues for the next bounded 10-120 minute window.

Candidate evidence:

```text
session
catalyst / no catalyst
normalized trend velocity
impact retention
pullback depth
outside dwell / acceptance
relative strength vs peer / index
spread / depth / slippage
external-oracle-mark-perp basis
```

### B. `EXTENDED_HOURS_REVERSAL / ABSORPTION`

Research when an extended-hours move is largely temporary price pressure and subsequently gives back.

Potential anchors:

```text
prior regular-session extreme move
overnight jump
poor impact retention
widened spread / weak depth
absence of confirming catalyst
peer/index non-confirmation
```

### C. `CASH_OPEN_RECONCILIATION`

Research how overnight/premarket moves behave around the 09:30 ET cash open:

```text
CONTINUE
PARTIAL_GIVEBACK
FULL_REVERSAL
NEW_PRICE_DISCOVERY
```

This connects directly to the already-registered Cash Open / Opening Repricing research direction.

---

## 9. Extended-hours evidence to retain / derive

Prefer raw/reconstructable evidence and offline derivation.

```text
session_type
session_start / event time
last_cash_close
postmarket_return
overnight_return
premarket_return
cash_open_gap
cash_open_30m / 60m result
normalized move / ATR
impact retention / giveback
MFE / MAE
pullback depth
spread / depth / fee / slippage
external price
oracle
mark
perp mid/BBO
tracking basis / lag
peer / index relative strength
news / earnings / macro catalyst tags
```

Do not add a full real-time session strategy to First Launch.

---

## 10. Macro and earnings event windows should be intraday micro-opportunity sequences

Research should explicitly model multiple opportunities around one event:

```text
PRE_EVENT_TREND
→ RELEASE_FIRST_MOVE
→ FAILED_FIRST_MOVE or CONTINUATION
→ MICRO_PULLBACK / MICRO_BALANCE
→ SECOND_STAGE_CONTINUATION
→ CASH_OPEN_RECONCILIATION if relevant
```

Each individual hypothetical trade should be evaluated on a bounded ~10-120 minute horizon.

Do not use multi-day drift as the default objective.

---

## 11. Initial experiment matrix

### EVENT-1 — Pre-event participation

Compare:

```text
NO_PRE_EVENT_TRADE
vs
PRE_EVENT_TREND_PARTICIPATION_EXIT_BEFORE_RELEASE
vs
CROSS_EVENT_CARRY
vs
POST_EVENT_ONLY
```

Metrics must include tail MAE / slippage and not only mean return.

### EVENT-2 — Priced-expectation / sell-the-fact

Condition on pre-event move magnitude and actual/event-implied surprise, then measure:

```text
post-release continuation
post-release reversal
impact retention
failed-first-move rate
```

### EXT-1 — Session continuation/reversal

By POST_MARKET / OVERNIGHT / PREMARKET:

```text
trend continuation probability
reversal probability
MFE / MAE
net expectancy
```

### EXT-2 — Catalyst-conditioned session behavior

Compare:

```text
earnings/news/macro catalyst
vs
no identified catalyst
```

### EXT-3 — Cash-open reconciliation

Condition on premarket/overnight return and measure 09:30-10:30 ET continuation/giveback/reversal.

---

## 12. Research cautions

1. Pre-announcement drift does not prove foreknowledge of the released number. Risk-premium / uncertainty-resolution and informed-positioning explanations can coexist across different samples.
2. `Buy the rumor, sell the fact` is not a universal reversal rule; it must be conditioned on the pre-event move and the information actually delivered relative to public and market-implied expectations.
3. Lower extended-hours liquidity can make trends visually smooth while simultaneously worsening spread, depth and execution quality.
4. TradeXYZ is a perpetual venue referencing external stock prices; venue-specific tracking, mark/oracle mechanics and liquidity must be measured rather than inferred from the underlying stock alone.
5. Extended-hours behavior must be segmented by catalyst and session; a generic overnight momentum rule is not justified by existing evidence.

---

## 13. Research-only maturity sequence

```text
I0 = historical session/event segmentation
I1 = pre-event trend / post-event continuation-reversal event study
I2 = TradeXYZ extended-hours tracking + execution study
I3 = session continuation/reversal and cash-open reconciliation simulation
I4 = live shadow observer
I5 = human-confirmed assisted execution
I6 = bounded automation only after new authority and independent evidence
```

This is not a frozen global priority.

---

## 14. Current non-goals

```text
NO CURRENT PR78 CHANGE
NO CURRENT FIRST-LAUNCH CODE
NO MULTI-DAY PEAD STRATEGY
NO LIVE PRE-EVENT DIRECTIONAL ENGINE NOW
NO DEFAULT CROSS-EVENT HOLDING
NO LIVE EXTENDED-HOURS STRATEGY NOW
NO AUTO TRADE
```

---

## 15. Authority Boundary

This document is research-only. It does not authorize code modification, Engineering dispatch, dependency installation, data-subscription purchase, deployment, restart, production DB mutation, account/private API access, signing, exchange writes, automatic order submission, PR Mark Ready, or Merge.