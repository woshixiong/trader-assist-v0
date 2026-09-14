# Trade OS — Quant Opening Event Research R1

**Status:** RESEARCH CANDIDATE / NON-EXECUTABLE / BRANCH-ONLY / NO PR  
**Date:** 2026-09-14  
**Repository:** `woshixiong/trader-assist-v0`  
**Live main at research start:** `4c7567a5fa4c6092a9fae0242f3dc27a5defba8c`  
**Research branch:** `research/quant-opening-event-r1-20260914`  
**Primary parent authorities:** Issue #161, Issue #82, Issue #85, Issue #150, Issue #163, Draft PR #168  

This document records a new bounded Strategy research question reopened by explicit user direction while E4 implementation is paused. It does not modify the accepted PRE-E4 candidate documents in Draft PR #168 and does not create production Strategy authority.

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS_FOR_RESEARCH_RECORD_ONLY
TASK_CLASS=MATERIAL_DIRECTION_SETTING_STRATEGY_RESEARCH_AND_DOCUMENTATION
INDEPENDENT_ANALYSIS_DONE=YES
EXTERNAL_RESEARCH_DONE=YES
DISCONFIRMING_EVIDENCE_CHECKED=YES
SYNTHESIS_DONE=YES
CURRENT_THREE_SETUP_AUTHORITY=UNCHANGED
FOURTH_FORMAL_SETUP=NO
LIVE_STRATEGY_CODE_CHANGE=NO
E4_DEVELOPMENT=PAUSED_BY_USER_PENDING_CROSS_TRACK_CONVERGENCE
E4_WRITER_DISPATCH=NO
MARK_READY=NO
MERGE=NO
DEPLOYMENT=NO
PRIVATE_API=NO
EXCHANGE_WRITE=NO
REAL_CAPITAL=NO
AUTONOMOUS_TRADING=NO
```

---

## 1. Exact research question

The current discretionary baseline avoids the first approximately 15 minutes after the relevant underlying cash-market open because opening price discovery often produces violent two-way moves. At the same time, those opening windows visibly contain unusually large opportunity density.

For Trade OS Quant, the question is not:

> Can the system predict the direction of the first opening move?

The bounded question is:

> Can the system replace a fixed opening no-entry interval with a causal, state-driven `WAIT -> TAKE/PASS` release policy that participates earlier only when the opening market state is sufficiently resolved, while preserving after-cost expectancy and controlling false activation, repeated scratch cost and execution risk?

A secondary question is:

> Does synchronized information from the underlying cash market / opening auction add material incremental value beyond Hyperliquid-local price, BBO, trades, mark/index/oracle and current Three Setup context?

The research must distinguish these two questions. Cross-market data is not assumed necessary merely because the traded instruments reference external equities.

---

## 2. Independent pre-research position

Before using external conclusions, the project mechanics imply the following preliminary model.

### 2.1 The relevant “open” is an external information boundary

For HIP-3 equity-like perpetuals, Hyperliquid can already be trading before KRX or U.S. cash-market open. Therefore the underlying stock-market open is not the start of the derivative market. It is a scheduled discontinuity in the information/liquidity process of the reference asset.

A practical causal chain can be:

```text
PRE-OPEN PERP / ORACLE / RELATED-MARKET EXPECTATIONS
-> CASH OPENING AUCTION / FIRST CONTINUOUS PRINTS
-> NEW CASH-MARKET PRICE DISCOVERY
-> ORACLE / REFERENCE UPDATES
-> HYPERLIQUID LOCAL ORDER-BOOK RESPONSE
-> ARBITRAGE / SPECULATIVE REPRICING / BASIS NORMALIZATION
```

The ordering is an empirical question, not a guaranteed sequence. In particular, a continuously traded derivative can lead the cash market when overnight information has already been incorporated before the cash open.

### 2.2 Fixed waiting is a crude information policy

A fixed 15-minute guard implicitly says:

```text
VALUE_OF_ADDITIONAL_INFORMATION_DURING_FIRST_15M
>
VALUE_OF_EARLY_PARTICIPATION
```

for every opening event.

That is unlikely to be universally optimal. It can be a strong safety control in `OPEN_TWO_WAY_CHAOS`, while being costly on clean opening-drive days where most favorable excursion occurs before +15m.

### 2.3 Opening time must not become side authority

The opening boundary can increase information arrival, volatility and liquidity stress, but those facts do not imply `LONG` or `SHORT`.

Current project separation remains:

```text
THREE_SETUP = WHAT / WHERE / SIDE
OPENING STATE = WHETHER TO KEEP WAITING OR RELEASE PARTICIPATION
MICROSTRUCTURE = WHEN / SHORT-HORIZON ACCEPTANCE
EXECUTION / FRICTION = WHETHER THE ATTEMPT IS ECONOMICALLY TRADEABLE
```

The initial expectation is therefore that Opening should remain a participation/context overlay, not a fourth Formal Setup.

### 2.4 Falsifiers

The opening overlay should be rejected or parked if causal local evidence shows that:

- early release increases after-cost false-activation/scratch losses more than it recovers missed early winners;
- positive retrospective results disappear under chronological OOS / Forward Shadow;
- plausible latency/slippage stress destroys the advantage;
- the effect is isolated to one market/day/episode without recurrence;
- external reference data adds no stable incremental value after local state;
- the required data/provider/latency complexity is disproportionate to the incremental value.

---

## 3. External evidence synthesis

### 3.1 Evidence that confirms opening as a special event regime

Tsai et al. (2019), studying index futures with one-minute data, report that futures volume and return fluctuations peak around the open and close of the underlying stock markets and propose a “timely opening range breakout” aligned to the underlying-market open. This is mechanically relevant to 24/7 or extended-hours derivatives around an external cash open, but its exact probe intervals are market/sample-specific and must not be imported as Trade OS thresholds.

Relevant source:
- Yi-Cheng Tsai et al., “Assessing the Profitability of Timely Opening Range Breakout on Index Futures Markets,” IEEE Access 7 (2019), DOI `10.1109/ACCESS.2019.2899177`.

Opening-auction research also confirms that the open is a distinct price-discovery mechanism rather than an ordinary continuous-trading minute. KRX explicitly uses a single-price call auction to determine the opening price; Nasdaq uses the Opening Cross and publishes imbalance information before the cross.

### 3.2 Counterevidence: opening breakout is not a universal edge

A crude-oil futures study found strong full-sample opening-range-breakout profitability, but splitting the sample into subperiods showed that the result was not robust through time and was largely driven by the most recent/high-volatility period.

Relevant source:
- “Assessing the profitability of intraday opening range breakout strategies,” Finance Research Letters (2013), ScienceDirect article `S1544612312000438`.

This is important counterevidence against promoting a direct ORB merely because the opening window is volatile.

### 3.3 Continuation and reversal are both plausible

Research on NYSE opening call auctions finds evidence of opening-trade price reversals, while other markets/samples show continuing information effects after the open. A recent call-auction study also documents opening overvaluation followed by intraday correction under specific market frictions.

The correct project implication is:

```text
OPENING EVENT != CONTINUATION LAW
OPENING EVENT != REVERSAL LAW
```

The system must observe state resolution rather than hard-code one mechanism.

Relevant source:
- “The interaction between opening call auctions and ongoing trade: Evidence from the NYSE,” Review of Financial Economics 13(4), DOI `10.1016/j.rfe.2003.12.003`.

### 3.4 Cross-market leadership is time-varying

Classic stock-index evidence shows strong futures-leading-cash behavior and only weak cash-leading-futures behavior. Other single-stock-futures studies report mixed or time-varying information shares. This rejects the naive assumption that the cash open must always lead a continuously traded derivative.

Relevant source:
- Kalok Chan, “A Further Analysis of the Lead–Lag Relationship Between the Cash Market and Stock Index Futures Market,” Review of Financial Studies 5(1), DOI `10.1093/rfs/5.1.123`.

Therefore, a future `cash -> perp` feature must be learned/validated locally and must preserve true causal admission timing. A lagged data vendor feed can manufacture a false lead-lag relationship.

### 3.5 Microstructure can support short-horizon confirmation, not imported thresholds

Cont, Kukanov and Stoikov show that short-interval price changes are strongly related to order-flow imbalance at the best bid/ask and that the impact slope depends inversely on depth. Queue-imbalance/microprice literature likewise supports top-of-book state as a probabilistic short-horizon signal.

This confirms the existing C1 decision to use simple price × flow-response evidence before deeper L2 complexity. It does not establish a Hyperliquid RWA coefficient or threshold.

Relevant source:
- Rama Cont, Arseniy Kukanov, Sasha Stoikov, “The Price Impact of Order Book Events,” Journal of Financial Econometrics 12(1):47–88; arXiv `1011.6402`.

### 3.6 Nasdaq / KRX pre-open information exists but is not automatically worth buying

Nasdaq officially disseminates Net Order Imbalance Indicator information from 09:25 to the 09:30 Opening Cross. It is subscription data and includes information intended to improve visibility into likely opening prices/liquidity.

KRX officially receives opening-price quotations from 08:30 to 09:00. During the opening call-auction window, after 08:40 it publishes three best bid/offer levels, quantities, and expected matching price/quantity.

These are credible future `O3` inputs. They are not first-stage requirements because provider access, data licensing, historical availability, feed delay and incremental value remain unresolved.

Official references:
- Nasdaq Opening/Closing Cross: `https://www.nasdaqtrader.com/Trader.aspx?id=OpenClose`
- KRX periodic call auction: `https://global.krx.co.kr/contents/GLB/06/0604/0604010100/GLB0604010100T3.jsp`
- KRX quotation information: `https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T6.jsp`

### 3.7 HIP-3 mechanics strengthen the case for measuring, not assuming, lead-lag

HIP-3 deployers define and publish their own oracle/reference inputs. Hyperliquid’s HIP-3 deployer API specifies bounded oracle/mark update behavior, while local order books and trades can react independently. The mark update can include deployer-supplied mark inputs together with a local mark component based on best bid/best ask/last trade. Therefore cash, deployer oracle/reference, local BBO and local trades are distinct state streams.

Relevant official references:
- HIP-3 overview: `https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals`
- HIP-3 deployer/oracle actions: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/hip-3-deployer-actions`
- Hyperliquid WebSocket subscriptions: `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions`

This creates a plausible opening-specific research edge, but also a data-synchronization trap.

---

## 4. Synthesis / decision

### What external evidence confirms

- underlying cash opens are genuine high-information / high-volatility market boundaries;
- opening auctions contain economically meaningful price-discovery information;
- short-horizon BBO/order-flow state can improve timing/acceptance decisions;
- continuously traded derivatives can react differently from the cash market around an open;
- opening research should be event-time aligned to the underlying market, not to a generic UTC clock.

### What external evidence modifies

The pre-research idea of “cash opens, then perp follows” is too simple. Leadership can run in either direction. The external cash feed should initially be a synchronized reference/diagnostic input, not an assumed leader.

### What external evidence rejects

- one universal opening-range duration;
- one universal `cash leads derivative` assumption;
- importing ORB thresholds from index futures into Hyperliquid RWA;
- creating a new directional Setup merely from the fact that the underlying market opened;
- using volatility alone as proof that the opening window has positive after-cost expectancy.

### Selected route

```text
PRIMARY_ROUTE
= OPENING AS STATE-DRIVEN PARTICIPATION / WAIT OVERLAY

FIRST_RESEARCH_LEADERS
= O1_LOCAL_STATE_RELEASE
+ O2_LOCAL_MICRO_RELEASE

HIGH-VALUE CONDITIONAL CHALLENGER
= O3_CROSS_MARKET_SYNC_RELEASE

FOURTH_SETUP_NOW
= NO
```

---

## 5. Bounded candidate ladder

The initial ladder is deliberately simple. Each material variant requires an immutable identity and trial-ledger entry before performance evidence is opened.

### O0 — `FIXED_15M_CONTROL`

Research control only.

```text
UNDERLYING_OPEN -> KEEP ELIGIBLE THREE_SETUP OPPORTUNITIES IN WAIT UNTIL +15M
THEN -> NORMAL CURRENT PARTICIPATION LOGIC
```

The 15-minute value is a control representing the current conservative behavior, not a newly frozen machine parameter or permanent production rule.

Purpose: quantify exactly what the fixed guard saves and what it misses.

### O1 — `LOCAL_STATE_RELEASE`

Use only local Hyperliquid causal state plus existing Three Setup direction.

```text
THREE_SETUP THESIS EXISTS
+ OPENING STATE RESOLVES
+ EXECUTION / FRICTION HARD GATES PASS
=> OPENING WAIT MAY RELEASE EARLY
```

No cross-market cash feed is required.

O1 should use price/executable-state geometry, not a new optimized score.

### O2 — `LOCAL_MICRO_RELEASE`

O1 plus the simple C1 microstructure family already planned by PR #168:

```text
AGGR_NOTIONAL_IMBALANCE_15S
FLOW_PRICE_RESPONSE_15S
MICRO_RV_60S
BBO / SPREAD / L1 FEASIBILITY
```

The opening overlay does not duplicate EA3. It asks whether this existing timing evidence should terminate `WAIT_FOR_OPENING_CHAOS_RESOLUTION` earlier or keep waiting.

A key candidate diagnostic remains:

```text
SAME-DIRECTION AGGRESSIVE FLOW
+ NON-POSITIVE EXECUTABLE PRICE RESPONSE
=> WEAK_RESPONSE / ABSORPTION_CANDIDATE
```

### O3 — `CROSS_MARKET_SYNC_RELEASE`

O2 plus synchronized underlying-market/reference evidence.

First-stage external inputs should be the cheapest causally defensible set:

```text
UNDERLYING OPEN / AUCTION PRICE
UNDERLYING BBO OR EXECUTABLE QUOTES WHEN AVAILABLE
UNDERLYING TRADES WHEN AVAILABLE
HYPERLIQUID MARK / INDEX / ORACLE / LOCAL BBO
```

Optional auction data such as Nasdaq NOII or KRX expected matching price remains a separate incremental feature group.

O3 must never assume `cash leads`. It tests whether cross-market alignment/divergence improves the `TAKE / WAIT / PASS` decision after local state and after costs.

### B0/B1 — offline mechanism benchmarks only

To avoid circularly assuming that Opening can never be an independent source of edge, retain two simple offline benchmark families:

```text
B0_SIMPLE_OPENING_RANGE_CONTINUATION
B1_SIMPLE_OPENING_RANGE_FAILURE_REVERSAL
```

These are research controls, not Shadow order authority and not a fourth Setup.

Reopen “Opening as a distinct Formal Setup” only if a simple causal benchmark demonstrates stable incremental OOS/Forward value that cannot be captured by the Three Setup + Opening overlay architecture.

---

## 6. Opening state model

Do not begin with a large weighted score. Use a small observable state machine.

Candidate research states:

```text
OPEN_UNRESOLVED
OPEN_DIRECTIONAL_ACCEPTANCE
OPEN_FAILED_IMPULSE_RECLAIM
OPEN_TWO_WAY_CHAOS
OPEN_NORMALIZED
```

Separate attributes:

```text
OPEN_STATE_DIRECTION = UP | DOWN | NONE
RELATION_TO_THESIS = WITH | AGAINST | NEUTRAL | NOT_APPLICABLE
```

The classifier may be computed for every opening event, even when no Three Setup exists, to preserve the denominator. It has no order authority by itself.

Example semantic interpretation:

```text
OPEN_UNRESOLVED
=> WAIT remains preferred

OPEN_DIRECTIONAL_ACCEPTANCE + WITH_THESIS
=> candidate early WAIT release

OPEN_FAILED_IMPULSE_RECLAIM + WITH_THESIS
=> candidate early WAIT release for reclaim-compatible Thesis

OPEN_DIRECTIONAL_ACCEPTANCE + AGAINST_THESIS
=> WAIT / PASS candidate

OPEN_TWO_WAY_CHAOS
=> continue WAIT; repeated attempt churn is explicitly penalized

OPEN_NORMALIZED
=> opening overlay retires; ordinary participation logic resumes
```

No numerical transition threshold is frozen in R1.

---

## 7. Feature families — smallest first

### 7.1 Event / calendar identity — mandatory

Every opening observation must bind:

```text
opening_event_id
underlying_exchange
underlying_instrument_id
perp_instrument_id
scheduled_open_ts
observed_auction_uncross_or_first_regular_trade_ts_if_available
exchange_calendar_version
exchange_timezone
holiday / half-day / special-session state
halt / delayed-open / auction-extension state when observable
underlying_mapping_version
```

Do not hard-code a single UTC time. KRX / U.S. DST / holidays / delayed auctions make that invalid.

### 7.2 Local price / executable-state diagnostics

Candidate derived fields, all normalized in bps / local volatility where appropriate:

```text
PREOPEN_LOCAL_DRIFT
OPEN_DISPLACEMENT_EXEC_BPS
OPEN_DIRECTIONAL_EFFICIENCY
OPEN_ANCHOR_RECROSS_COUNT
OPEN_IMPULSE_RETENTION
OPEN_REVERSAL_FROM_EXTREME
TIME_TO_FIRST_RECLAIM
MICRO_RV_60S
SPREAD_BPS
SPREAD_VS_SAME_MARKET_TOD_BASELINE
L1_FEASIBLE_NOTIONAL
ALL_IN_FRICTION_EST_BPS
```

`OPEN_DIRECTIONAL_EFFICIENCY` should conceptually compare net displacement with total traveled distance. It is useful because a +30 bps net move reached through a +70/-60/+20 path is economically different from a monotonic +30 bps drive.

### 7.3 Local flow / response diagnostics

Reuse the already defined C1 features first:

```text
AGGR_NOTIONAL_IMBALANCE_15S
FLOW_PRICE_RESPONSE_15S
```

Cheap optional diagnostics may include top-level imbalance, microprice offset and trade intensity, but only after the simple baseline is preserved.

### 7.4 Local reference / oracle diagnostics

Retain distinct state rather than collapsing to one “price”:

```text
LOCAL_BBO_MID_OR_EXEC_SIDE
MARK_PRICE
INDEX_PRICE / ORACLE REFERENCE
LOCAL_TO_MARK_BASIS_BPS
LOCAL_TO_ORACLE_BASIS_BPS
ORACLE_LAST_UPDATE_STATE / PROVENANCE
```

For HIP-3 markets, exact deployer/oracle mapping must be versioned. Do not assume all RWA markets use identical oracle semantics.

### 7.5 Cross-market O3 diagnostics

Only after causally synchronized external data exists:

```text
UNDERLYING_OPEN_GAP_BPS
UNDERLYING_RETURN_{1S,5S,15S,30S,60S}
PERP_RETURN_{1S,5S,15S,30S,60S}
CASH_PERP_DIRECTIONAL_CONCORDANCE
PERP_MINUS_CASH_REFERENCE_BASIS_BPS
BASIS_CONVERGENCE_OR_DIVERGENCE
CASH_TO_PERP_RESPONSE_DELAY_DIAGNOSTIC
PERP_TO_CASH_RESPONSE_DELAY_DIAGNOSTIC
```

Lead/lag fields are diagnostics first. A live feature can be promoted only after provider latency and timestamp provenance are defensible.

---

## 8. Causal timing is the key O3 correctness gate

Cross-market opening research is unusually vulnerable to false causality.

A vendor-supplied cash quote can have an exchange timestamp earlier than a Hyperliquid event but reach Trade OS later. If the backtest compares exchange timestamps while the live Strategy could only see the quote after its network/provider delay, the study can manufacture impossible alpha.

Required timing/provenance fields therefore include, where available:

```text
provider_event_ts
true_local_receive_ts_if_observable
adapter_ts_init
admission_ts
decision_ts
hypothetical_order_active_ts
feed_continuity_epoch
source / provider / channel identity
clock_quality_or_sync_state
```

Permanent rule inherited from PRE-E4 Repair 1:

```text
NAUTILUS_TS_INIT != GUARANTEED_NETWORK_RECEIVE_TIME
```

O3 historical studies must distinguish:

```text
EXCHANGE-TIME PRICE-DISCOVERY STUDY
vs
LIVE-REPLAYABLE CAUSAL TRADING STUDY
```

The former can justify mechanism research. Only the latter can support an actionable policy claim.

---

## 9. Required opening denominator — material E4 data-design implication

The existing generic C1 data contract starts durable BBO/trade retention around near-Actionable / Opportunity states. That is correct for generic Entry research, but opening-state research has a distinct denominator problem.

If BBO/trades are captured only when Scanner/Three Setup already identifies an opportunity, the dataset cannot answer:

- how often the open is clean versus chaotic;
- whether early-release rules create or suppress opportunities;
- how many opening drives never generated the current Three Setup in time;
- whether the fixed 15m guard prevented losses on days with no later signal.

Therefore, if the Opening program is included in E4, the first E4 data design should support a **bounded scheduled opening observation window** for the selected opening-research cohort even when no Setup is yet Actionable.

Conceptual topology:

```text
UNDERLYING_OPENING_EVENT_SCHEDULED
-> BOUNDED LOCAL BBO + TRADE CAPTURE AROUND EVENT
-> OPENING STATE / DATA-QUALITY EVIDENCE
-> THREE_SETUP / OPPORTUNITY MAY OR MAY NOT OCCUR
-> TAKE / WAIT / PASS / BLOCKED
-> HYPOTHETICAL ORDER ONLY WHEN NORMAL STRATEGY AUTHORITY PERMITS
```

This is not a continuous full-universe tick archive. It is a scheduled bounded event window.

Candidate design range for capacity assessment only:

```text
PRE-OPEN CONTEXT: order of minutes, not only seconds
POST-OPEN RAW WINDOW: long enough to span early release through the existing +15m control and a short tail
```

A practical assessment candidate is approximately `T-5m` through `T+30m`, but R1 does **not** freeze this as the final retention contract. Provider/storage burden and the product/data decision must be evaluated before E4 implementation.

Low-cost 1m/5m context can be retained for longer horizons through existing project surfaces.

---

## 10. Nautilus fit — reuse mature surfaces

The opening program does not justify a second market-data/backtest framework.

Nautilus already provides built-in data types appropriate to the first-stage design:

```text
QuoteTick
TradeTick
OrderBookDepth10
Bar
MarkPriceUpdate
IndexPriceUpdate
```

Official `BacktestNode` + `ParquetDataCatalog` workflows are designed so Strategy/Actor/ExecutionAlgorithm semantics can carry forward toward `LiveNode`.

For external underlying cash markets:

```text
NORMAL CASH BBO -> QuoteTick when provider mapping supports it
NORMAL CASH TRADE -> TradeTick
REFERENCE PRICE -> built-in reference type where semantically correct
AUCTION-SPECIFIC NOII / EXPECTED-MATCH FIELDS -> versioned CustomData if needed
```

Nautilus CustomData can route and persist application-specific data in the same data engine/catalog. That is preferable to inventing a new side-channel platform for auction imbalance.

Order-book simulation fidelity rule:

```text
L1 DATA CANNOT SYNTHESIZE L2/L3
```

Therefore first-stage opening execution should remain L1/BBO + trades unless intended size or a prespecified residual hypothesis proves deeper book data necessary.

Official references:
- `https://nautilustrader.io/docs/latest/getting_started/backtest_high_level/`
- `https://nautilustrader.io/docs/latest/concepts/data/`
- `https://nautilustrader.io/docs/latest/concepts/custom_data/`
- `https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues/`

---

## 11. Shadow / evidence contract delta for future E4 design

Do not overload `ShadowOrder` with context that belongs to the opportunity/decision layer.

### 11.1 Opening Opportunity / Decision evidence

Add conceptually, if this program is selected for E4:

```text
opening_event_id
opening_policy_variant_id
opening_policy_version
opening_state
opening_state_direction
relation_to_thesis
opening_wait_reason
opening_wait_start_ts
opening_wait_end_ts
opening_wait_termination_reason
opening_release_reason
opening_feature_version
local_reference_snapshot_id / provenance
external_reference_snapshot_id / provenance when O3
cross_market_data_state = COMPLETE | INCOMPLETE | GAPPED | LATENCY_LIMITED | NOT_AVAILABLE
```

Every eligible opening-linked Opportunity must retain `TAKE / WAIT / PASS / BLOCKED`, not only resulting hypothetical orders.

### 11.2 Hypothetical order evidence

Reuse the accepted PRE-E4 execution contract:

```text
hypothetical_order_id
order_intent_id
hypothetical_order_active_ts
first eligible executable state at/after active time
modeled entry/exit fill
fee / slippage / impact model identity
latency scenario
L1/top10 capacity state
NOT_SUBMITTED=true
```

No opening variant may substitute trigger price for executable fill price.

### 11.3 Missing-data behavior

```text
O3 MISSING EXTERNAL DATA
!=
SILENT FALLBACK TO O2
```

Each variant is independently identified. If O3-required external data is incomplete, O3 is `NOT_EVALUABLE_DATA_INCOMPLETE`; O2 remains a separate candidate with its own identity and outcome.

---

## 12. Product / trading-panel information contract — no UI freeze

The Product window should decide layout and operator interaction later. Strategy research should only state what information becomes decision-relevant.

An opening-aware future panel may need a read-only projection of:

```text
UNDERLYING OPENING EVENT / EXCHANGE / COUNTDOWN OR STATUS
CURRENT OPENING STATE
CURRENT OPENING WAIT REASON
WAIT RELEASED / NOT RELEASED + REASON
LOCAL DATA HEALTH / CONTINUITY
EXTERNAL REFERENCE HEALTH when applicable
THREE_SETUP THESIS + SIDE
LOCAL / EXTERNAL REFERENCE ALIGNMENT OR DIVERGENCE
EXECUTION FRICTION / CAPACITY STATE
SHADOW / NOT_SUBMITTED STATUS
```

This is an information contract only. No panel layout, button, color, workflow or execution authority is frozen here.

---

## 13. Research execution plan

### Stage A — opening path characterization before policy tuning

First characterize the event population without trying to maximize PnL.

For every opening event in the research cohort, report causal path checkpoints such as:

```text
+30s
+60s
+120s
+300s
+900s
```

These are research checkpoints, not live wait timers.

Measure at minimum:

- local executable displacement;
- path directional efficiency / recrosses;
- MFE / MAE from pre-open and open anchors;
- continuation versus reversal path labels;
- spread/friction and micro-RV evolution;
- local mark/oracle/basis evolution;
- data completeness;
- where available, external cash/perp alignment.

Output: descriptive mechanism map + data-quality audit + trial ledger. No Strategy winner selected from Stage A.

### Stage B — freeze a small rule family

Only after Stage A validates that the required observables are causal and measurable, freeze a bounded O1/O2/O3 rule family on a development cut.

Do not choose dozens of feature thresholds. Prefer semantic states and small grids.

### Stage C — deterministic retrospective paired replay

Compare on the same OpeningEvent/Thesis path:

```text
O0 vs O1
O1 vs O2
O2 vs O3 where external evidence exists
```

Also run B0/B1 offline controls.

### Stage D — chronological OOS / walk-forward

- no random K-fold for promotion claims;
- purge/embargo overlapping outcome windows where applicable;
- inspected OOS becomes development history;
- cluster correlated markets/events;
- freeze candidate before untouched OOS/Forward use.

### Stage E — E4 causal Shadow only after the current user hold is explicitly released

All candidate orders remain `NOT_SUBMITTED`.

If O3 data/provider design is not ready, E4 may still begin with O0/O1/O2 only if the final cross-track E4 Task Packet authorizes that scope. Do not let O3 become an artificial blocker to all local opening research.

### Stage F — E5 fresh Forward

Use the accepted project promotion standard. A selected winner after adaptive multi-candidate comparison requires a later immutable confirmatory Forward set; do not reuse a selection sample as pristine confirmation.

---

## 14. Primary statistical unit and clustering

Do not treat every second or every state transition as an independent sample.

Primary opening research hierarchy:

```text
OPENING_EVENT
-> MARKET / UNDERLYING EXPRESSION
-> THESIS
-> ATTEMPT(S)
```

For MU and SNDK around the same U.S. open, or multiple storage-theme markets responding to one common event, cluster dependence explicitly. Same-theme simultaneous signals are not independent observations.

Useful reporting levels:

```text
RAW MARKET
OPENING EVENT
THESIS
CROSS-ASSET EVENT CLUSTER
CLUSTER-NORMALIZED
```

---

## 15. Primary metrics

The objective is not win rate and not earliest possible release.

Required paired metrics:

```text
THESIS_NET_R_AFTER_COST
THESIS_NET_PNL_AFTER_COST
MFE_EXEC_BBO
MAE_EXEC_BBO
TAIL_MAE / DRAWDOWN
TIME_FROM_OPEN_TO_RELEASE
EARLY_PARTICIPATION_COVERAGE
FALSE_ACTIVATION / FALSE_SCRATCH
CUMULATIVE_ATTEMPT_COST
MISSED_RUNAWAY_WINNER_VALUE
CHASE_COST_FROM_WAITING
RIGHT_TAIL_PNL_RETAINED
FEES / SLIPPAGE / FUNDING SHARE_OF_GROSS_EDGE
DATA_INCOMPLETE_RATE
```

Opening-specific diagnostics:

```text
VALUE_OF_WAIT
= paired economic outcome of staying in WAIT versus releasing now

OPEN_EDGE_DECAY
= after-cost opportunity value by event-time bucket

O2_MINUS_O1_INCREMENT
= incremental value of flow/microstructure

O3_MINUS_O2_INCREMENT
= incremental value of external cross-market data
```

Always report latency/cost sensitivity. Opening alpha that disappears under a small plausible delay or spread expansion is not promotion-quality.

---

## 16. Research-frontier decomposition and dispositions

### F1 — opening event calendar / exchange-session identity

```text
DECISION_CRITICALITY=HARD_BLOCKER_FOR_CAUSAL_OPENING_CLAIMS
EXPECTED_DECISION_IMPACT=HIGH
RESEARCH_INVESTMENT_DISPOSITION=ACQUIRE_BEFORE_NEXT_GATE
CHEAPEST_ROUTE=EXCHANGE_CALENDAR / PROVIDER-NATIVE SESSION METADATA + VERSIONED PROJECT MAPPING
```

Reason: a wrong open timestamp invalidates every opening label.

### F2 — bounded local Hyperliquid BBO + trades around opening for the research cohort

```text
DECISION_CRITICALITY=HARD_BLOCKER_FOR_O1/O2_SUB-MINUTE_EXECUTABLE_OPENING_CLAIM
EXPECTED_DECISION_IMPACT=HIGH
RESEARCH_INVESTMENT_DISPOSITION=ACQUIRE_BEFORE_NEXT_GATE_IF_OPENING_PROGRAM_ENTERS_E4
IMPLEMENT_NOW=NO_WHILE_E4_USER_HOLD_ACTIVE
```

Use scheduled bounded capture; do not create continuous full-universe archival solely for this program.

### F3 — local full L2

```text
DECISION_CRITICALITY=OPTIONAL_FIRST_PASS
RESEARCH_INVESTMENT_DISPOSITION=PARK_OR_REJECT
REOPEN_TRIGGER=INTENDED_SIZE_EXCEEDS_DEFENSIBLE_L1_CAPACITY_OR_SIMPLE_BBO/TRADES_LEAVES_A_PRESPECIFIED_RESIDUAL_QUESTION
```

### F4 — external underlying open / BBO / trades

Decompose by claim:

```text
FOR_O1/O2
DECISION_CRITICALITY=OPTIONAL
RESEARCH_INVESTMENT_DISPOSITION=PROCEED_WITH_CURRENT_BEST_AND_DEFER

FOR_O3
DECISION_CRITICALITY=HARD_BLOCKER_FOR_O3_ACTIONABLE_CLAIM
RESEARCH_INVESTMENT_DISPOSITION=ACQUIRE_BEFORE_NEXT_GATE_ONLY_IF_O3_IS_SELECTED_FOR_THAT_GATE
```

Do not make a future external-data provider purchase/integration mandatory before local O1/O2 evidence exists unless Product/Data separately selects it for broader value.

### F5 — Nasdaq NOII / KRX expected-match auction fields

```text
DECISION_CRITICALITY=OPTIONAL / MATERIAL_OPTIMIZATION_ONLY_AFTER_O3_BASELINE
RESEARCH_INVESTMENT_DISPOSITION=CAPTURE_CHEAP_OPTIONALITY_IF_INCLUDED_IN_ACCEPTED_PROVIDER
OTHERWISE=PARK_OR_REJECT
REOPEN_TRIGGER=O3_BASELINE_SHOWS_MATERIAL_UNRESOLVED_OPENING_AUCTION_ERROR_MODE
```

### F6 — external full L2 / MBO

```text
DECISION_CRITICALITY=OPTIONAL_HIGH_BURDEN
RESEARCH_INVESTMENT_DISPOSITION=PARK_OR_REJECT
```

### F7 — standalone opening directional Setup

```text
DECISION_CRITICALITY=OPTIONAL / HIGH_OVERFIT_AND_AUTHORITY_COST
RESEARCH_INVESTMENT_DISPOSITION=PARK_OR_REJECT
OFFLINE_SIMPLE_BENCHMARK_ALLOWED=YES
REOPEN_TRIGGER=SIMPLE_B0/B1_SHOWS_STABLE_INCREMENTAL_OOS/FORWARD_VALUE_NOT_CAPTURED_BY_THREE_SETUP_OVERLAY
```

### F8 — exact state thresholds

```text
DECISION_CRITICALITY=MATERIAL_OPTIMIZATION
RESEARCH_INVESTMENT_DISPOSITION=PROCEED_WITH_CURRENT_BEST_AND_DEFER_TO_BOUNDED_REPLAY/OOS/FORWARD
LARGE_HISTORICAL_THRESHOLD_SEARCH=PROHIBITED
```

---

## 17. Key open questions for the next cycle

1. What fraction of KRX/U.S. cash opens are `OPEN_TWO_WAY_CHAOS` versus directional acceptance for the actual Trade OS research markets?
2. How much of the eventual +15m MFE is already realized by +30/+60/+120s on successful Three Setup Theses?
3. What is the paired economic cost of O0 waiting versus O1/O2 early release after realistic fills?
4. Does `AGGR_NOTIONAL_IMBALANCE + FLOW_PRICE_RESPONSE` reduce false early release enough to justify its incremental data/logic burden?
5. How often does Hyperliquid local price move first and the underlying cash open merely validate an already-priced direction?
6. How often do external cash and HIP-3 local/oracle states materially diverge during the first minutes?
7. Is O3 incremental value large enough to justify synchronized external market data and auction-data cost?
8. Does opening-specific performance vary enough by KRX versus U.S. open to justify separate future policy versions, or can one normalized state model remain portable?
9. Does the first opening Attempt require a different stop/time-no-followthrough policy, or can the existing AP family remain common after volatility normalization?
10. Are apparent opening profits robust after clustering MU/SNDK/storage-theme events rather than counting each market as independent?

---

## 18. Current R1 terminal disposition

```text
QUANT_OPENING_RESEARCH=CONTINUE
HUMAN_OPENING_STRATEGY_RESEARCH=PAUSED_BY_USER
OPENING_AS_FOURTH_SETUP=NO
OPENING_AS_STATE_DRIVEN_WAIT_OVERLAY=KEEP
FIXED_15M=CONTROL_NOT_FINAL_QUANT_POLICY
PRIMARY_RESEARCH_LEADER=O1_LOCAL_STATE_RELEASE
SECOND_PRIMARY=O2_LOCAL_MICRO_RELEASE
O3_CROSS_MARKET=HIGH_VALUE_CONDITIONAL_CHALLENGER
DIRECT_ORB=OFFLINE_BENCHMARK_ONLY
OPENING_DENOMINATOR_CAPTURE=REQUIRED_IF_PROGRAM_ENTERS_E4
FULL_L2_FIRST_STAGE=NO
AUCTION_IMBALANCE_REQUIRED_FIRST_STAGE=NO
EXTERNAL_PROVIDER_SELECTION_NOW=NO
NUMERIC_OPENING_THRESHOLDS_FROZEN=NO
E4_IMPLEMENTATION_NOW=NO
NEXT=STAGE_A_DATA_AVAILABILITY_AND_CAUSAL_CHARACTERIZATION_DESIGN
```

The main architectural change from the prior generic PRE-E4 plan is not a new Strategy Setup. It is the recognition that an opening-policy study needs a **scheduled event denominator and bounded pre/post-open microstructure window even when no current Setup is yet Actionable**. This requirement should be reconciled with Product, Backtest and E4 data/shadow design before E4 implementation is restarted.

No current authority file or accepted PR #168 artifact is superseded by this branch-only R1 record.
