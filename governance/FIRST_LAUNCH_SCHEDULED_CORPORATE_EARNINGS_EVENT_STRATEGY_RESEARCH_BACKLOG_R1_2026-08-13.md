# First Launch Scheduled Corporate Earnings Event Strategy Research Backlog R1

**Record ID:** `TA-FIRST-LAUNCH-SCHEDULED-CORPORATE-EARNINGS-EVENT-RESEARCH-R1-2026-08-13`  
**Date:** `2026-08-13`  
**Repository:** `woshixiong/trader-assist-v0`  
**Related Draft PR:** `#52`  
**Status:** `POST-FIRST-LAUNCH RESEARCH CONTRACT / NON-EXECUTABLE / NON-AUTHORIZING`  
**Parent concept:** shared future `SCHEDULED_INFORMATION_EVENT_ENGINE`; sibling research contract: `FIRST_LAUNCH_SCHEDULED_US_MACRO_EVENT_STRATEGY_RESEARCH_AND_FUTURE_AUTOMATION_BACKLOG_R1_2026-08-12.md`  

---

## 1. Decision

Corporate earnings / company-report events are a high-value future strategy-research direction for Hyperliquid / XYZ equity perpetuals.

This does **not** change the current First Launch release and does not authorize any current-release code.

```text
CURRENT_RELEASE_CHANGE = NO
CURRENT_MACHINE_STRATEGY_CHANGE = NO
NEW_FORMAL_SETUP_NOW = NO
AUTO_TRADE_NOW = NO
FUTURE_RESEARCH = YES
```

The research should share common event infrastructure with scheduled U.S. macro research, but earnings requires a separate interpretation model.

```text
SHARED EVENT ENGINE
  ├─ MACRO_EVENT_INTERPRETER
  └─ CORPORATE_EARNINGS_INTERPRETER
```

Do not force EPS/revenue/guidance into the same semantics as CPI/NFP/PCE.

---

## 2. Why this is distinct from ordinary price-action trading

A scheduled earnings event changes the information set discontinuously and often creates:

```text
PRE-EVENT EXPECTATION / POSITIONING
→ RELEASE-TIME REPRICING
→ MULTI-VARIABLE INTERPRETATION
→ AFTER-HOURS / PRE-MARKET PRICE DISCOVERY
→ CASH-OPEN RECONCILIATION
→ CONTINUATION / FAILURE / NEW BALANCE
```

The event can also be multi-stage:

```text
EARNINGS RELEASE
→ GUIDANCE / SUPPLEMENTAL MATERIALS
→ CONFERENCE CALL / MANAGEMENT TONE
→ Q&A
→ ANALYST REVISIONS
```

Therefore the event should have multiple timestamped sub-events, not one single release timestamp.

---

## 3. Shared architecture with Macro Event Strategy

Reuse the same causal layers where possible:

```text
L0 PRE-EVENT EXPECTATION STATE
L1 RELEASE / SURPRISE INTERPRETATION
L2 BENCHMARK / PEER INTERPRETATION
L3 TRADEABLE MARKET ACCEPTANCE
L4 EXECUTION QUALITY
L5 ENTRY ROUTER / NO_TRADE
```

Shared research primitives:

```text
Point-in-Time event calendar
expectation snapshot
surprise vector
pre-event price state
normalized event move
impact retention
price acceptance
relative event strength
leader / laggard
execution quality
NO_TRADE
second-stage continuation
micro-pause / shallow pullback
full retest
failed first move
bounded event-window high-resolution evidence
```

---

## 4. Earnings-specific interpretation vector

Do not use `EPS beat/miss` as a single trigger.

Minimum generic vector:

```text
EPS actual vs consensus
Revenue actual vs consensus
Forward revenue guidance vs consensus / prior guidance
Forward EPS / profit guidance if relevant
Gross / operating margin surprise
FCF / capex surprise when economically material
prior-period revisions / restatements if relevant
```

Company / sector-specific KPI schema is required for serious research. Examples may include:

```text
cloud growth / backlog / RPO
subscription / customer growth
unit shipments / pricing
memory / NAND / DRAM pricing and margins
AI / data-center revenue
bookings / TCV / ARR
same-store / marketplace / advertising metrics
```

Weights must be learned / frozen by company or sector research; do not hard-code one universal weighted earnings score before evidence.

---

## 5. Event stages

At minimum classify:

```text
BMO = before market open
AMC = after market close
IN_SESSION = during regular market
CALL_STAGE = earnings call / Q&A stage
```

The exact release timestamp matters. Scheduled dates can move and should not be assumed immutable.

Future PIT evidence should preserve:

```text
event_id
issuer
underlying
scheduled_date
scheduled_time / time-quality
actual_release_timestamp
event_stage
source
source_version
consensus_snapshot_time
```

---

## 6. Pre-event research

Research, but do not default to a directional pre-earnings bet.

Potential expectation-state features:

```text
pre-event trend / gap state
recent analyst revisions
consensus dispersion
options-implied move / IV where available
pre-event realized volatility
short interest / positioning proxies where available
sector / peer momentum
previous-quarter surprise history
```

Historical earnings-announcement premium / pre-announcement effects are research hypotheses, not automatic live rules. Gap risk and uncertain firm-specific information make `PRE_EVENT_DIRECTIONAL_BET` a default NO until independently justified.

---

## 7. Release-time / first-move research

Do not compete primarily in the first milliseconds/seconds.

Initial research should capture:

```text
headline surprise vector
first impulse direction
normalized event move
impulse retention / giveback
spread / depth / slippage
external-oracle-mark-perp basis
peer / sector response
index response
```

Immediate first move is not authoritative because different line items can conflict and later guidance/call information can reverse the interpretation.

---

## 8. Highest-value first strategy candidates

### A. `EARNINGS_SECOND_STAGE_CONTINUATION`

```text
material surprise / guidance alignment
+ first move accepted
+ impulse retained
+ peer/sector context not severely contradictory
+ execution quality acceptable
→ micro-pause / shallow-pullback / continuation entry research
```

This is the primary initial intraday candidate.

### B. `EARNINGS_FAILED_FIRST_MOVE`

```text
initial headline-driven impulse
→ conflicting details / guidance / call
→ failed acceptance / accepted re-entry
→ reverse-side continuation research
```

Share methodology with `FAILED_FIRST_MOVE` and `FAILED_ACCEPTED_BREAKOUT`, but keep event causality explicit.

### C. `EARNINGS_CALL_REPRICING`

Treat the conference call / Q&A as a second scheduled information event. Research management tone, guidance clarification and Q&A as possible causes of second-stage repricing.

### D. `POST_EARNINGS_DRIFT / SHORT-HORIZON FUNDAMENTAL MOMENTUM`

Research intraday-to-multi-day continuation after standardized surprises, but do not assume classic PEAD is a stable, frictionless production edge. Compare short horizons first and use cost-adjusted / out-of-sample evidence.

### E. `PEER / SECTOR SPILLOVER`

Research whether a bellwether earnings event creates a cleaner or better-cost trade in a peer, sector leader, or index than in the announcing company itself.

---

## 9. Corporate Event Asset Router

Separate interpretation asset from trade asset.

```text
PRIMARY INFORMATION ASSET:
announcing company / underlying external stock price

CONTEXT:
sector ETF / index / direct peers / supplier-customer peers

TRADE CANDIDATES:
announcing XYZ perp
peer XYZ perps
sector-amplifier assets
XYZ100 / SP500 where appropriate
```

Future router features:

```text
EVENT_RELATIVE_STRENGTH
NORMALIZED_EVENT_MOVE
IMPULSE_RETENTION
PRICE_ACCEPTANCE
PEER_CONFIRMATION
SECTOR_CONFIRMATION
SPREAD / DEPTH / SLIPPAGE
FEE
VENUE_TRACKING_BASIS
IDIOSYNCRATIC_SECONDARY_NEWS
```

`STRONGEST MOVE != BEST TRADE` remains mandatory.

---

## 10. TradeXYZ / XYZ venue-specific research

XYZ U.S. single-name stock perps have external pricing coverage across pre-market, cash market, post-market and overnight sessions on weekdays. This makes them especially relevant to BMO / AMC earnings research.

Venue-specific evidence must retain / compare when available:

```text
external price
oracle price
mark price
perp mid / BBO
spread
basis / tracking lag
funding
open interest
liquidity / depth
session type
```

Large event moves can interact with oracle / mark mechanics and discovery bounds. This is an execution / venue-mechanics research problem, not a reason to create a separate alpha strategy immediately.

Do not assume a traditional equity print and the XYZ perp are identical during violent event windows.

---

## 11. Earnings call / text research

Management tone and Q&A can contain incremental information beyond headline figures.

Long-term candidates:

```text
management tone surprise
guidance language change
uncertainty / vagueness
Q&A sentiment / topic shift
analyst-revision response
```

Text / LLM processing is a later layer. Do not introduce an LLM dependency until numeric + price-acceptance baselines are established.

---

## 12. NO_TRADE conditions

Research at least:

```text
EPS and revenue conflict materially
guidance conflicts with headline beat/miss
company-specific KPI conflict
first move not retained
peer / sector reaction severely contradictory
spread / slippage abnormal
XYZ tracking / oracle / mark state unhealthy
feed / filing latency uncertain
announcement timestamp uncertain
first move excessively extended
call pending and headline interpretation highly incomplete
```

The strategy is not required to trade every earnings release.

---

## 13. Research maturity path

Not a frozen global priority; only an internal evidence sequence:

```text
E0 = PIT earnings calendar + consensus / guidance dataset
E1 = event study: surprise vector + direct stock + peer/sector/index response
E2 = XYZ tracking / execution study
E3 = second-stage continuation / failed-first-move simulation
E4 = conference-call repricing study
E5 = live shadow earnings observer
E6 = human-confirmed assisted execution
E7 = bounded automation only after new authority and independent evidence
```

---

## 14. Initial research metrics

At minimum:

```text
sample size / independent event count
issuer / sector diversity
announcement timing
surprise-vector magnitude / conflict
first move
normalized event move
impact retention
MFE / MAE
first-event continuation / retest / failure
time-to-MFE
spread / slippage / fee
external-oracle-mark-perp basis
peer / sector relative strength
cash-open continuation / reversal
30m / 60m / 120m / next-session outcome
```

Use PIT expectations and avoid final-data hindsight.

---

## 15. Research cautions

- Classic PEAD is historically important but its magnitude / explanation / persistence are contested and may be reduced by modern arbitrage and trading frictions.
- Earnings releases are multi-dimensional; one EPS surprise is insufficient.
- Announcement timing and processing time can change the speed of incorporation.
- Macro-news occurring on the same day can materially change earnings price response and must be recorded.
- Company-specific earnings cannot use a universal fixed metric weighting without evidence.
- High after-hours gross moves can be offset by spread, slippage, fees, funding or XYZ tracking mechanics.

---

## 16. Relationship to current Macro Event research

Recommended architecture:

```text
SCHEDULED_INFORMATION_EVENT_ENGINE
  ├── US_MACRO_EVENT
  │    ├─ CPI
  │    ├─ NFP
  │    ├─ PCE
  │    └─ FOMC (separate multi-stage family)
  │
  └── CORPORATE_EVENT
       └─ EARNINGS
            ├─ RELEASE
            ├─ GUIDANCE
            ├─ CALL
            └─ CASH_OPEN_RECONCILIATION
```

Share data / acceptance / asset-router / execution primitives; keep interpretation semantics separate.

---

## 17. Current non-goals

```text
NO CURRENT PR78 CHANGE
NO CURRENT FIRST-LAUNCH CODE
NO NEW LIVE SETUP
NO LIVE EARNINGS CALENDAR ENGINE NOW
NO AUTOMATIC SEC / IR / TRANSCRIPT TRADING NOW
NO LLM EARNINGS TRADER NOW
NO PRE-EARNINGS DIRECTIONAL BET NOW
NO AUTO TRADE
```

---

## 18. Authority Boundary

This document is research-only. It does not authorize code modification, Engineering dispatch, dependency installation, data-subscription purchase, deployment, restart, production DB mutation, account/private API access, signing, exchange writes, automatic order submission, PR Mark Ready, or Merge.