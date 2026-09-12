# Trader Assist / Trade OS — Execution Latency, Slippage and Trading Terminal UX Research Freeze

**Date:** 2026-09-12  
**Status:** RESEARCH / PRODUCT-ARCHITECTURE DECISION RECORD ONLY  
**Repository:** `woshixiong/trader-assist-v0`  
**Research base main:** `41e72737a09d45583df8c6473150c4500ffbf239`  
**Research branch:** `research/execution-latency-terminal-ux-20260912`  
**Predecessor research:** `research/frontend-v0-product-architecture-20260911` / `docs/research/FRONTEND_V0_PRODUCT_ARCHITECTURE_RESEARCH_2026-09-11.md`  
**Authority effect:** NONE until separately reviewed/accepted under project governance  
**Implementation authority:** NO  
**Deployment/runtime authority:** NO  
**Credential/private API/wallet/signing/exchange-write authority:** NO  
**Mark Ready / merge authority:** NO

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS_FOR_PRODUCT_RESEARCH_FREEZE_ONLY
PRODUCT_WRITER_DISPATCH=NO
IMPLEMENTATION_PACKET=NO
EXECUTION_PLAN=NO
```

This file is additive. It does not modify the previous frontend research record, current Product/Strategy/Operations/Governance authority, or production code. It records the next independent research round focused on execution latency, price slippage, order-entry protection and the minimal operator-terminal UX required to make those costs visible and controllable.

---

## 1. Research question

The user observes that manually clicking a Hyperliquid market order can produce an average fill roughly USD 0.5-1.0 away from the price perceived at decision/click time on SKHX. The practical concern is not institutional/HFT latency competition. The product goal is:

```text
MINIMIZE CONTROLLABLE EXECUTION DELAY
+ MAKE UNCONTROLLABLE MARKET COST VISIBLE
+ HARD-LIMIT UNACCEPTABLE PRICE CHASE
+ PRESERVE SIMPLE HUMAN APPROVAL
+ PRESERVE SYSTEM SAFETY / RECONCILIATION
```

The research must answer:

1. Does inserting the Trader Assist dashboard and an AWS-hosted approval service create material click-to-fill latency?
2. Which part of observed price difference is spread, book impact, price drift/latency, mark-price display difference, fees or other execution mechanics?
3. Can the future Nautilus route materially reduce avoidable execution loss without becoming a custom HFT infrastructure project?
4. Which execution facts should be shown on the minimal desktop/mobile terminal before approval?
5. Which latency/slippage evidence must be recorded so later Engineering can optimize from measurements rather than assumptions?

---

## 2. Current project authority reviewed

Fresh internal review used:

- `AGENTS.md`;
- `governance/PROJECT_RULES_INDEX.md`;
- `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`;
- `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`;
- `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`;
- `governance/EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md`;
- Issue #18 Product amendment comment `5581144976`;
- Issue #139 Nautilus-centered V0 risk ladder comment `5580843025`;
- Issue #161 Strategy Research Master Plan;
- Issue #163 Nautilus Transition Master Plan;
- current Nautilus/approval contracts on main;
- predecessor frontend research record.

Frozen project facts remain:

```text
TERMINAL_V0_INTERACTION=
SYSTEM PRODUCES EXACT ORDER PACKAGE
-> HUMAN REVIEWS
-> HUMAN EXPLICITLY APPROVES
-> MATURE INFRASTRUCTURE EXECUTES

HUMAN_APPROVAL_PER_NEW_RISK_PACKAGE=REQUIRED
AUTONOMOUS_NEW_RISK=NO
SHADOW_BEFORE_EXECUTION=REQUIRED
ZERO_WRITE_APPROVAL_BEFORE_TESTNET=REQUIRED
TESTNET_BEFORE_MAINNET=REQUIRED
```

The browser remains a presentation/approval-request surface, not an execution/order/position authority.

---

## 3. Phase 1 — independent analysis before external research

### 3.1 Price difference is not one variable

The observed difference between a visible/reference price and actual average fill should be decomposed before attempting optimization.

For a buy, conceptually:

```text
DECISION / DISPLAY REFERENCE PRICE
-> CROSS HALF-SPREAD TO BEST ASK
-> CONSUME AVAILABLE ASK DEPTH
-> MARKET MAY MOVE DURING HUMAN + NETWORK + VENUE LATENCY
-> ACTUAL AVERAGE FILL
-> MARK-TO-MARKET AGAINST CURRENT MARK / MID
-> FEES / FUNDING SEPARATELY
```

Potential components:

```text
A. REFERENCE-PRICE SEMANTICS
   mark vs mid vs last vs best ask/bid

B. QUOTED SPREAD
   buy executes against ask, sell against bid

C. BOOK IMPACT
   order consumes one or multiple levels

D. LATENCY / ADVERSE PRICE DRIFT
   book moves after observation/click and before matching

E. VENUE / CONSENSUS PROCESSING
   request must reach API server/node/HyperBFT execution

F. ORDER-PROTECTION POLICY
   allowed aggressive limit / slippage ceiling

G. DISPLAY / ACCOUNTING
   unrealized PnL may be marked against a price different from fill

H. EXPLICIT FEES
   economically real but should not be mislabeled as price slippage
```

Without click-time BBO/depth, order quantity, send/accept/fill timestamps and fill data, a USD 0.5-1.0 gap cannot be attributed correctly.

### 3.2 Dashboard latency model

A human-approved Trader Assist path cannot eliminate the human network hop because execution authority is released only after the approval request reaches the server.

Current direct-web conceptual path:

```text
HUMAN
-> HYPERLIQUID FRONTEND ACTION
-> HYPERLIQUID API / NODE / CONSENSUS
-> FILL
```

Trader Assist conceptual path:

```text
HUMAN
-> TRADER ASSIST SERVER
-> LOCAL AUTHORITATIVE REVALIDATION
-> NAUTILUS EXECUTION CLIENT
-> HYPERLIQUID API / NODE / CONSENSUS
-> FILL
```

Therefore:

```text
TRADER_ASSIST_CLICK_TO_VENUE_LATENCY
IS_NOT_GUARANTEED_TO_BE_LOWER_THAN
DIRECT_HYPERLIQUID_CLICK_TO_VENUE_LATENCY
```

However, total **signal-to-order** latency can be materially lower because Trader Assist removes workflow steps such as switching interfaces, manually reading/copying prices, entering quantity/order type/protection parameters and re-checking the plan. A small additional network hop may be dominated by seconds of eliminated human workflow.

The correct product objective is therefore two separate measures:

```text
A. DECISION/SIGNAL_TO_SUBMISSION_LATENCY
B. APPROVE_CLICK_TO_SUBMISSION/FILL_LATENCY
```

Do not conflate them.

### 3.3 Preliminary independent route

Before external research, the smallest plausible route was:

- keep UI server and execution runtime on the same host or same very-low-latency local network when practical;
- precompute exact order package before approval;
- keep live BBO/depth/account/execution state warm in memory;
- on approval, perform only mandatory local safety/authority revalidation before dispatch;
- keep analytics, AI explanation, rendering work and non-safety reporting out of the order critical path;
- use a venue-supported price-protected aggressive order rather than an unbounded chase;
- measure every latency segment and every execution-cost component;
- do not build a low-latency node/co-location stack unless actual evidence later proves ordinary API access is a material bottleneck.

External research was then used to confirm, modify or reject this view.

---

## 4. Phase 2 — external primary / mature evidence

### 4.1 Hyperliquid matching and API path

Hyperliquid states that HyperCore uses a fully on-chain central limit order book with price-time priority. API servers maintain blockchain state, forward user transactions to a connected node, and return the execution response after the action is included in a committed L1 block.

Primary sources:

- https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/order-book
- https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/api-servers
- https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/overview

Consequence: even a perfectly fast local UI cannot remove venue/network/consensus latency or the book state changes occurring during that interval.

### 4.2 Official latency claim and uncertainty

Hyperliquid documents end-to-end latency as the duration from sending a request to receiving a committed response. For a geographically co-located client it reports approximately:

```text
MEDIAN = 0.2 seconds
P99 = 0.9 seconds
```

Source:
- https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/overview

Hyperliquid also advises automated strategies to operate geographically near an API server and provides a separate advanced latency guide for users requiring lower latency.

Sources:
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/nonces-and-api-wallets
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/optimizing-latency

Important limitation: the official documentation reviewed does not provide a stable public region map proving that AWS Tokyo is the globally optimal location for `api.hyperliquid.xyz` order submission.

A third-party continuous-latency site reported a March 2026 sample of 120 real market-order requests from AWS Tokyo with roughly 884 ms median order-to-fill response and a 695-1634 ms observed range. This is not canonical Hyperliquid evidence, but it materially contradicts the assumption that Tokyo must automatically equal the official co-located benchmark.

Supplemental source:
- https://latency.glassnode.com/hyperliquid/fill-latency

Disposition:

```text
AWS_TOKYO_CURRENT_CANDIDATE=YES
AWS_TOKYO_PROVEN_OPTIMAL=NO
REGION_SELECTION_MUST_BE_MEASURED=YES
```

### 4.3 Hyperliquid market order is price-protected execution, not infinite-price chasing

The official Python SDK implements `market_open` as an aggressive IOC limit order. It derives an aggressive limit price from a reference mid and a slippage allowance. The official SDK default maximum slippage is 5%.

Primary source:
- https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/exchange.py

Relevant implementation semantics:

```text
DEFAULT_SLIPPAGE = 0.05
MARKET ORDER = AGGRESSIVE LIMIT ORDER IOC
```

The venue exchange API itself exposes IOC limit semantics and optional client order IDs.

Source:
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint

This means the project can and should define an explicit maximum executable price rather than treating a market action as economically unbounded.

### 4.4 Nautilus Hyperliquid adapter gives a tighter native seam

Current NautilusTrader Hyperliquid documentation states:

- `MARKET` orders are sent as IOC limits;
- buy price is derived from cached best ask, sell price from cached best bid;
- default `market_order_slippage_bps` is 50 bps;
- the slippage value can be overridden per order;
- market orders are denied when the required quote is unavailable rather than guessing a price;
- standard perps and HIP-3 builder perps share the same order capability;
- partial fills are preserved and only the IOC remainder is canceled.

Primary source:
- https://nautilustrader.io/docs/latest/integrations/hyperliquid/

Disposition:

```text
NAUTILUS_DEFAULT_50_BPS_AS_PROJECT_POLICY=REJECT
PER_ORDER_PROJECT_SLIPPAGE_POLICY=REQUIRED
```

The 50 bps adapter default is a transport/runtime default, not evidence that 50 bps is economically acceptable for SKHX, MU, crypto or any other instrument.

### 4.5 Market depth is available before approval

NautilusTrader's Hyperliquid adapter supports:

- `QuoteTick` best bid/offer;
- full-depth L2 book snapshots;
- `OrderBookDepth10` top-ten levels;
- live trades;
- mark/index prices.

The adapter shares the same venue-side `l2Book` stream across relevant subscribers and maintains books per instrument.

Sources:
- https://nautilustrader.io/docs/latest/integrations/hyperliquid/
- https://nautilustrader.io/docs/latest/concepts/order_book/

Consequence: an active proposal can display and record an estimated executable VWAP / book impact for its exact quantity before the trader approves it. This does not require building a private market-data engine.

### 4.6 Spread, depth and mark price explain immediate negative PnL without any network bug

Hyperliquid documents that:

- order books match at bid/ask levels;
- mark price is a robust reference derived from oracle/order-book/external data;
- mark price is used to compute unrealized PnL;
- mark and trade price are distinct.

Sources:
- https://hyperliquid.gitbook.io/hyperliquid-docs/trading/order-book
- https://hyperliquid.gitbook.io/hyperliquid-docs/trading/robust-price-indices

For a buy, an immediate taker fill normally crosses from the reference mid/mark toward the ask and potentially deeper asks. Therefore a newly opened position can show negative unrealized PnL immediately even with negligible transport latency.

Hyperliquid's own support documentation explicitly warns that low liquidity and volatility can create large slippage and recommends checking the order book, using price-limited execution when exact price matters, and breaking large positions into smaller chunks when appropriate.

Source:
- https://hyperliquid.gitbook.io/hyperliquid-docs/support/faq/trade-outcome-looks-incorrect/my-tp-sl-did-not-execute-correctly

### 4.7 Low-latency market data should use persistent streaming

Hyperliquid states that WebSocket should be used for lowest-latency real-time data and that API WebSocket connections support real-time subscriptions and request sending.

Sources:
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits

Nautilus's adapter already owns REST/WebSocket connectivity in Rust and exposes quote/book streams and execution connectivity.

Sources:
- https://nautilustrader.io/docs/latest/integrations/hyperliquid/
- https://nautilustrader.io/docs/latest/concepts/adapters/

Consequence: Trade OS should consume these mature persistent transports. It should not add a second custom low-latency transport stack.

### 4.8 Hyperliquid's advanced node path exists but is not justified now

Hyperliquid's latency guide recommends, for latency-sensitive traders, running a non-validating node near a reliable peer, using high machine specifications, disabling output buffering and building exchange state locally from node output. The same guide recommends at least 32 logical cores and 500 MB/s disk throughput for that route.

Source:
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/optimizing-latency

This is a mature provider-native escalation route, but it is materially more complex than current needs.

Disposition:

```text
NON_VALIDATING_NODE_NOW=REJECT
LOCAL_ORDER_BOOK_SERVER_NOW=REJECT
REOPEN_ONLY_IF_MEASURED_API_LATENCY_IS_MATERIAL_AND_ECONOMICALLY_RELEVANT
```

The project is not an HFT/latency-arbitrage system and should not absorb this operational burden preemptively.

### 4.9 Market microstructure research supports a cost decomposition, not a universal order type

Cont and Kukanov's order-placement work shows that optimal use of market versus limit orders depends jointly on order-book state, queue/depth, fees and execution risk rather than one universally best order type.

Sources:
- https://arxiv.org/abs/1210.1625
- https://ora.ox.ac.uk/objects/uuid:0ab2bc82-2098-406b-b962-c6134402a0a4

Modern liquidity literature distinguishes quoted spread, effective spread, price impact and implementation shortfall. Implementation shortfall includes both direct execution cost and opportunity cost from delay/non-execution.

Source:
- https://academic.oup.com/book/55158/chapter-abstract/424078167

Recent crypto latency research on Bybit/Binance also emphasizes that the observed order book is already stale by the time a taker order reaches the matching engine, and latency can contribute to failure-to-fill and adverse selection.

Source:
- https://www.tandfonline.com/doi/full/10.1080/14697688.2025.2515933

Project consequence:

```text
MINIMIZE_SLIPPAGE_AT_ALL_COSTS=WRONG_OBJECTIVE
MINIMIZE_TOTAL_IMPLEMENTATION_SHORTFALL_SUBJECT_TO_STRATEGY_URGENCY_AND_RISK=CORRECT_OBJECTIVE
```

A tight price cap can reduce slippage but increase partial/no-fill and missed-move cost. The strategy's urgency and remaining edge must decide which trade-off is acceptable.

---

## 5. Phase 3 — synthesis

### 5.1 What external evidence confirms

External evidence confirms:

1. spread/depth and reference-price semantics are likely to explain a meaningful portion of immediate negative entry PnL;
2. latency is economically real but must be measured separately from book impact;
3. market orders on Hyperliquid/Nautilus are already implemented through price-limited IOC semantics, giving the project a mature price-protection seam;
4. Nautilus already provides the BBO/L2 data required to preview expected execution cost;
5. WebSocket/persistent mature transport should be reused rather than rebuilt;
6. a non-validating-node/co-location stack is a legitimate later escalation but not justified now;
7. server region choice should be evidence-driven rather than assumed.

### 5.2 What external evidence modifies

Earlier assumption:

```text
AWS TOKYO SERVER => AUTOMATICALLY FASTEST EXECUTION
```

Modified conclusion:

```text
AWS TOKYO MAY BE GOOD FOR THE CURRENT JAPAN-BASED OPERATOR
BUT HYPERLIQUID WRITE-LATENCY OPTIMALITY IS NOT PROVEN
```

Earlier product emphasis:

```text
PRICE + ORDER PACKAGE + APPROVE
```

Modified product emphasis:

```text
EXECUTABLE PRICE + EXPECTED FILL + WORST ALLOWED FILL
+ SPREAD/DEPTH/SLIPPAGE
+ ORDER PACKAGE + APPROVE
```

This makes execution cost visible before approval rather than discovering it only after fill.

### 5.3 What external evidence rejects

Reject now:

- assuming every immediate negative PnL is network latency;
- selecting AWS region from intuition alone;
- using Nautilus's 50 bps default as universal project slippage policy;
- submitting a market order without current quote/depth awareness;
- building custom low-latency transport;
- running a Hyperliquid node/local book before measurements justify it;
- adding a complex execution-algorithm UI to solve a problem that can first be handled with exact order packages and price protection.

---

## 6. Product decision — will the dashboard create significant delay?

The defensible answer is:

```text
SIGNIFICANT_DELAY_NOT_INHERENT_TO_DASHBOARD=YES
ZERO_ADDITIONAL_DELAY_GUARANTEE=NO
FASTER_THAN_DIRECT_HYPERLIQUID_CLICK_GUARANTEE=NO
FASTER_SIGNAL_TO_ORDER_WORKFLOW_EXPECTED=YES
MEASUREMENT_REQUIRED_BEFORE_EXECUTION_CLAIM=YES
```

A minimal same-origin approval UI does not need to perform expensive browser computation, AI inference, REST market-data fetches or additional order construction after the click. If the exact proposal is already prepared and authoritative state is warm, the application-specific work after approval can be kept narrow.

But the human approval request still has to travel:

```text
OPERATOR DEVICE -> TRADER ASSIST SERVER
```

before the server is legally/product-authorized to submit new risk. Therefore the user-device network remains part of Human-approved V0 latency.

### 6.1 Critical-path principle

The product-critical path is frozen conceptually as:

```text
APPROVE CLICK
-> SERVER RECEIVES EXACT APPROVAL IDENTITY
-> SERVER RE-READS WARM AUTHORITATIVE STATE
-> MANDATORY REVALIDATION ONLY
-> AUTHORITATIVE APPROVAL/PERMIT TRANSITION
-> NAUTILUS SUBMIT
-> VENUE
```

The following must not be required before submission:

```text
AI EXPLANATION
CHART RENDERING
RESEARCH REPORT GENERATION
NON-SAFETY ANALYTICS
EXTERNAL MARKET-DATA REST REFRESH
DASHBOARD FULL-PAGE RERENDER
THIRD-PARTY ANALYTICS
```

Safety/durability/reconciliation requirements may not be removed merely to save milliseconds.

---

## 7. Execution-price protection product contract

The new route should not expose a generic `market_order_slippage_bps=50` setting directly to the trader as if it were strategy policy.

For each proposed order, the project should derive and display an exact **worst allowed execution boundary** from accepted Strategy/Risk/Execution policy.

Conceptually for a buy:

```text
CURRENT_BEST_ASK
ESTIMATED_VWAP_FOR_EXACT_QTY
STRATEGY_CHASE_LIMIT
EXECUTION_SLIPPAGE_LIMIT
ROUNDING / VENUE CONSTRAINTS
        |
        v
MAX_AUTHORIZED_BUY_PRICE
```

For a sell, the direction is reversed.

Hard product invariant:

```text
EXECUTION_MUST_NOT_FILL_BEYOND_THE_EXACT_HUMAN-APPROVED_PRICE_BOUNDARY
```

If available liquidity inside that boundary is insufficient, the result may be partial fill / no fill / new proposal according to later accepted execution policy. The system must not silently widen the price cap simply to guarantee a fill.

Strategy-specific `Chase Limit` and execution slippage are separate concepts but the final order must respect both.

No universal numeric slippage threshold is frozen by this research record.

---

## 8. Required pre-approval execution-cost view

The previous eight-layer terminal information architecture remains valid, but the exact-order layer should be strengthened with an **Execution Cost Preview**.

For the exact proposed quantity, show as applicable:

```text
REFERENCE MARK
REFERENCE MID
BEST BID / BEST ASK
QUOTED SPREAD ($ and bps)
ESTIMATED AVG FILL / VWAP
ESTIMATED BOOK IMPACT ($ and bps)
WORST AUTHORIZED FILL PRICE
MAX SLIPPAGE ($ and bps)
VISIBLE DEPTH INSIDE AUTHORIZED PRICE BOUNDARY
QUOTE / BOOK AGE
CHASE LIMIT
EXPECTED INITIAL MARK-TO-MARKET DRAG
```

Do not imply false precision. If the book snapshot is stale/incomplete or the requested size exceeds the evidence available for the estimate, show `UNKNOWN / INSUFFICIENT DEPTH EVIDENCE` and fail closed when policy requires it.

### 8.1 Why both mark and executable prices matter

A trader deciding from chart/mark/mid can otherwise compare a non-executable reference with the actual fill and perceive the full spread/impact as unexplained latency.

The UI should explicitly distinguish:

```text
FAIR / REFERENCE PRICE
vs
EXECUTABLE PRICE NOW
vs
MAXIMUM PRICE I AM AUTHORIZING
```

This is expected to improve both execution decisions and post-trade trust in the system.

---

## 9. Required execution-quality evidence per real/test fill

Later Testnet/Mainnet evidence should preserve enough timestamps and price states to decompose execution shortfall.

Conceptual fields:

```text
proposal_created_at
proposal_reference_mark
proposal_reference_mid
proposal_best_bid
proposal_best_ask
proposal_estimated_vwap
proposal_worst_authorized_price
proposal_qty
proposal_book_revision / freshness

human_approve_client_time     # diagnostic only, not authority
approval_server_received_at
approval_revalidation_done_at
order_submit_started_at
order_transport_send_at       # when available from mature infrastructure
venue_accepted_at
first_fill_at
last_fill_at
ui_fill_visible_at            # UX diagnostic

bbo_at_approval
bbo_at_submit
mark_at_submit
book_estimate_at_submit

avg_fill_price
filled_qty
fees
funding_if_applicable
```

Derived diagnostics:

```text
USER_TO_SERVER_APPROVAL_DELAY
APPLICATION_REVALIDATION_DELAY
SERVER_TO_VENUE_ACCEPT_DELAY
SERVER_TO_FIRST_FILL_DELAY
CLICK_TO_FIRST_FILL
CLICK_TO_FINAL_FILL
FILL_TO_UI_VISIBLE_DELAY

QUOTED_SPREAD_COST
ESTIMATED_BOOK_IMPACT
REALIZED_SLIPPAGE_VS_BBO
REALIZED_SLIPPAGE_VS_ESTIMATED_VWAP
TOTAL_IMPLEMENTATION_SHORTFALL
```

Clock caveat: cross-system latency is valid only when timestamp origins and clock synchronization semantics support the comparison. Nautilus documents that `ts_event` vs `ts_init` cannot be interpreted as latency without synchronized clocks.

Source:
- https://nautilustrader.io/docs/latest/concepts/data/

These fields are research/observability requirements, not browser authority.

---

## 10. Hosting and network-location decision

### 10.1 Current conclusion

```text
CURRENT_AWS_TOKYO=KEEP_AS_INITIAL_CANDIDATE
MOVE_REGION_NOW=NO
CLAIM_TOKYO_FASTEST=NO
```

Reasons to keep Tokyo as the initial candidate:

- current operator is generally in Japan/APAC;
- current production host already exists there;
- moving now adds operational variables before evidence exists;
- the project does not require HFT-class proximity.

Reasons not to freeze Tokyo permanently:

- official Hyperliquid documents do not prove Tokyo is the nearest/best API-server route;
- venue processing/consensus can dominate pure network RTT;
- routing can change;
- mobile/operator network conditions can dominate the user-to-server leg;
- actual write latency must be measured in the authorized Testnet/realistic environment.

Future region choice should compare measured end-to-end distributions, not ping alone.

### 10.2 Do not optimize the wrong number

A region with a slightly lower TCP/HTTP RTT is not necessarily better if total:

```text
ORDER SUBMIT -> VENUE ACCEPT / FILL
```

is worse or more variable.

Required performance view later:

```text
P50
P95
P99
TAIL / TIMEOUT RATE
```

for both:

```text
OPERATOR -> APP SERVER
APP SERVER -> VENUE ACCEPT/FILL
```

A lower median with poor tails is not automatically preferable for a human-approved trading product.

---

## 11. Order-style product policy — simple, not one-size-fits-all

This research does not freeze a full execution algorithm. It freezes a small policy surface.

### 11.1 Immediate/urgent entry

Candidate mature primitive:

```text
PRICE-PROTECTED IOC / MARKETABLE LIMIT
```

Use when Strategy edge is time-sensitive and missing the trade is materially costly.

Advantages:
- immediate taker attempt;
- hard worst-price boundary;
- no resting remainder under IOC;
- mature Hyperliquid/Nautilus support.

Trade-off:
- partial/no fill when the cap is too tight or liquidity disappears.

### 11.2 Passive/non-urgent entry

Candidate mature primitive:

```text
LIMIT / ALO POST-ONLY
```

Use only when Strategy timing allows waiting and fill uncertainty is acceptable.

Advantages:
- avoids crossing spread when filled as maker;
- no taker book impact at entry.

Trade-off:
- non-fill / missed move / adverse selection / queue uncertainty.

### 11.3 Large order / insufficient depth

Chunking can reduce instantaneous book impact but increases time/execution risk. Hyperliquid supports TWAP, and Nautilus has mature execution-algorithm abstractions, but these are not V1 defaults for the user's small/medium discretionary intraday workflow.

Disposition:

```text
COMPLEX_EXECUTION_ALGO_UI=NO_V1
AUTO_TWAP_DEFAULT=NO
AUTO_SPLIT_DEFAULT=NO
REOPEN_IF_REAL_ORDER_SIZE_VS_DEPTH_EVIDENCE_JUSTIFIES=YES
```

---

## 12. Revised terminal UX freeze

The predecessor eight-layer content contract remains accepted. This research changes information emphasis, not the overall simple frontend route.

### 12.1 Desktop wireframe — conceptual only

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ TESTNET / ZERO-WRITE | READY | DATA FRESH | EXEC CONNECTED | RECONCILED│
│ KILL: OFF | Quote age: 42 ms                                              │
├───────────────────────────────────┬──────────────────────────────────────┤
│ SKHX  LONG                        │ PROPOSAL → CURRENT DIFF              │
│ BREAKOUT_RETEST                   │ Price        +0.18                   │
│ Strategy v...                     │ Spread       0.12 → 0.16            │
│ Expires 00:21                     │ Chase        PASS                    │
│                                   │ Account      UNCHANGED               │
│ EXACT ORDER                       │                                      │
│ Qty        5                      │ EXECUTION COST PREVIEW               │
│ Type       IOC / price-protected  │ Mark         201.40                  │
│ Entry ref  201.42                 │ Best Ask     201.46                  │
│ Stop       200.80                 │ Est Avg Fill 201.50                  │
│ TP...                              │ Worst Allowed201.62                  │
│ Risk       ...                    │ Spread       0.06 / 3.0 bps          │
│                                   │ Est impact   0.04 / 2.0 bps          │
│                                   │ Depth in cap SUFFICIENT              │
├───────────────────────────────────┴──────────────────────────────────────┤
│ ⚠ deterministic warnings / approval blockers only                       │
├──────────────────────────────────────────────────────────────────────────┤
│                     [ REJECT ]   [ APPROVE BUY ]                         │
├──────────────────────────────────────────────────────────────────────────┤
│ After approval: SUBMITTED → ACCEPTED → PARTIAL/FILLED → PROTECTED       │
│ Position: avg fill | qty | stop/TP state | PnL | fees | reconciliation  │
└──────────────────────────────────────────────────────────────────────────┘

[ Evidence / IDs / AI explanation / research detail — collapsed ]
```

This is a wireframe, not a visual-design mandate.

### 12.2 Mobile wireframe — conceptual only

```text
┌────────────────────────────┐
│ ZERO-WRITE | READY         │
│ DATA FRESH | RECONCILED    │
├────────────────────────────┤
│ SKHX  LONG                 │
│ BREAKOUT_RETEST   00:21    │
├────────────────────────────┤
│ DIFF / WARNINGS            │
│ Price +0.18  Chase PASS    │
├────────────────────────────┤
│ EXECUTION NOW              │
│ Mark            201.40     │
│ Best Ask        201.46     │
│ Est Fill        201.50     │
│ Worst Allowed   201.62     │
│ Spread / Impact ...        │
│ Depth           SUFFICIENT │
├────────────────────────────┤
│ ORDER / RISK               │
│ Qty / Stop / TP / Risk     │
├────────────────────────────┤
│ [REJECT] [APPROVE BUY]     │  <- sticky/reachable
├────────────────────────────┤
│ Execution / Position       │
└────────────────────────────┘
```

Mobile remains responsive web, not a native application.

### 12.3 Interaction rule

Keep one explicit approval action. Do not add a routine second confirmation dialog merely to feel safer. Exact package visibility + server-side single-use/idempotent authorization + mandatory revalidation provide the safety model.

The approval button should communicate the action, e.g. `APPROVE BUY`, rather than a generic `OK`.

---

## 13. Frontend technical route re-review

No evidence from this latency research justifies reversing the 2026-09-11 frontend route.

Keep:

```text
FASTAPI / SERVER-AUTHORITATIVE WEB
JINJA2 SERVER RENDERING
NATIVE HTML FORMS / HTTPS
EVENTSOURCE / SSE FOR SERVER->BROWSER STATUS
MINIMAL VANILLA JS
BOOTSTRAP 5.3 CSS-ONLY RESPONSIVE PRIMITIVES
```

Do not put execution submission on the browser SSE path. Approval remains a direct state-changing HTTPS request. SSE is only for presentation/state updates.

The browser frontend therefore need not sit on the execution critical path after the server has received and accepted the approval request.

No SPA/WebSocket/frontend state-store is required to improve trading latency.

---

## 14. Performance objective — optimize controllable latency, not HFT latency

Permanent product principle from this research:

```text
LOW_LATENCY_WITHOUT_UNSAFE_SHORTCUTS=YES
HFT_RACE=NO
MEASURE_BEFORE_INFRASTRUCTURE_ESCALATION=YES
```

The project should optimize in this order:

```text
1. REMOVE HUMAN WORKFLOW DELAY / MANUAL TRANSCRIPTION
2. USE WARM AUTHORITATIVE MARKET/ACCOUNT STATE
3. KEEP APPROVAL REVALIDATION LOCAL AND MINIMAL
4. REUSE PERSISTENT PROVIDER/NAUTILUS TRANSPORT
5. HARD-LIMIT PRICE CHASE
6. SELECT HOST REGION FROM MEASURED END-TO-END DISTRIBUTIONS
7. ONLY THEN CONSIDER ADVANCED NODE/PEERING/COLOCATION
```

No numerical application-latency SLA is frozen before representative measurements. Arbitrary sub-10ms/sub-50ms targets would be false precision at this stage.

---

## 15. Research/evidence feedback loop

Every future Testnet/Mainnet fill should support answering:

1. Was the proposal already expensive to execute before the click?
2. How much cost came from spread?
3. How much came from visible depth/market impact?
4. How much price moved between approval and venue submission?
5. How much additional movement occurred before first/final fill?
6. Did the order hit its authorized price ceiling?
7. Did a tighter ceiling cause partial/no fill and missed opportunity?
8. Was the host/network path a material fraction of total delay?
9. Did the user interface display the same significant transaction data that was actually authorized?
10. Would a different order style have reduced total implementation shortfall after including missed-move risk?

This evidence should guide later tuning. Do not infer universal slippage thresholds from one SKHX incident.

---

## 16. Explicit non-goals for the next terminal version

Do not add merely for latency:

- custom Hyperliquid networking stack;
- custom order matching/OMS;
- custom local full order-book server;
- non-validating Hyperliquid node;
- multi-region active-active execution;
- smart order routing across venues;
- HFT co-location infrastructure;
- sub-millisecond browser targets;
- complex execution algorithm selector;
- depth heatmap / full professional DOM terminal;
- separate native mobile app;
- client-side risk or slippage authority.

Any of these requires a new measured blocker and mature-solution re-evaluation.

---

## 17. Residual uncertainty and future decisive evidence

This research intentionally does not claim:

- exact current user-device -> AWS Tokyo latency;
- exact AWS Tokyo -> Hyperliquid API write latency;
- exact click -> accepted/fill distribution through Nautilus;
- exact SKHX spread/depth/impact distribution at the user's trade times;
- exact optimal per-instrument slippage cap;
- exact value of splitting orders;
- exact best AWS/other region.

These are empirical questions. The research disposition is:

```text
REGION_OPTIMALITY=
ACQUIRE_BEFORE_REAL_EXECUTION_ROUTE_FREEZE_WHEN REPRESENTATIVE MEASUREMENT IS AUTHORIZED

PER_INSTRUMENT_SLIPPAGE_POLICY=
ACQUIRE_FROM SHADOW/TESTNET/EXECUTION-QUALITY EVIDENCE BEFORE MAINNET POLICY FREEZE

ADVANCED_NODE/COLOCATION=
PARK_OR_REJECT UNTIL ORDINARY API PATH IS A MEASURED MATERIAL BOTTLENECK

COMPLEX_EXECUTION_ALGORITHMS=
PARK_OR_REJECT UNTIL ORDER-SIZE/DEPTH/URGENCY EVIDENCE SHOWS MATERIAL VALUE
```

No additional research platform is authorized by this record.

---

## 18. Final product research freeze

```text
RESEARCH_ROUTE=INDEPENDENTLY_DERIVED_EXTERNALLY_MODIFIED

DASHBOARD_ADDS_INHERENT_SIGNIFICANT_LATENCY=NO
DASHBOARD_ADDS_ZERO_LATENCY=NO
DIRECT_HL_CLICK_FASTER_GUARANTEE=NO
SIGNAL_TO_ORDER_WORKFLOW_SPEED_ADVANTAGE=EXPECTED_BUT_MUST_BE_MEASURED

AWS_TOKYO=INITIAL_CANDIDATE_NOT_PROVEN_OPTIMAL
REGION_SELECTION=MEASUREMENT_DRIVEN

PRIMARY_EXECUTION_COST_MODEL=
SPREAD
+ DEPTH / MARKET IMPACT
+ LATENCY / ADVERSE DRIFT
+ FEES
+ MISSED-FILL / OPPORTUNITY COST

NAUTILUS_MARKET_ORDER=
PRICE-PROTECTED_IOC_LIMIT_WITH_CONFIGURABLE_SLIPPAGE

NAUTILUS_DEFAULT_50_BPS_AS_PROJECT_POLICY=NO
PER_ORDER_PRICE_PROTECTION=YES
STRATEGY_CHASE_LIMIT_MUST_BE_RESPECTED=YES

PRE_APPROVAL_EXECUTION_COST_PREVIEW=REQUIRED_PRODUCT_DIRECTION
MARK_VS_EXECUTABLE_PRICE_DISTINCTION=REQUIRED
ESTIMATED_FILL_PRICE=REQUIRED_WHEN_EVIDENCE_SUFFICIENT
WORST_AUTHORIZED_FILL_PRICE=REQUIRED
SPREAD_AND_DEPTH_VISIBILITY=REQUIRED
QUOTE/BOOK_FRESHNESS_VISIBILITY=REQUIRED

FRONTEND_ARCHITECTURE_PREVIOUS_FREEZE=KEEP
RESPONSIVE_MOBILE_WEB=KEEP
APPROVE_REJECT_PRIMARY_ACTIONS=KEEP
ONE_CLICK_EXPLICIT_APPROVAL=KEEP

CUSTOM_LOW_LATENCY_STACK=NO
NON_VALIDATING_NODE_NOW=NO
HFT_COLOCATION_PROJECT=NO

EXECUTION_LATENCY_AND_SHORTFALL_TELEMETRY=REQUIRED_FOR_FUTURE_TESTNET/MAINNET_EVIDENCE

PRODUCT_WRITER_DISPATCH=NO
EXECUTION_PLAN=NO
IMPLEMENTATION_AUTHORITY=NO
MAIN_CHANGE=NO
```

---

## 19. Re-open triggers

Re-open this decision only when one of the following becomes true:

1. representative Testnet/Mainnet measurements show application/server latency is a material part of implementation shortfall;
2. AWS Tokyo is materially worse than an alternative region on sustained p50/p95/p99 order-to-accept/fill evidence;
3. order sizes regularly exceed safe visible liquidity inside the approved price boundary;
4. tight IOC protection creates economically material non-fill/missed-winner cost;
5. Nautilus/Hyperliquid transport changes materially;
6. mobile approval latency or reliability becomes a measured workflow blocker;
7. a mature provider-native low-latency service becomes available with materially lower total lifecycle burden than the current route.

Until then, prefer the simple server-authoritative human-approved terminal and mature Nautilus/Hyperliquid execution path.