# Trader Assist / Trade OS — Market and Venue Selection Framework V1

**Status:** SPECIALIZED METHOD CANDIDATE  
**Effective date:** 2026-09-13  
**Normative owner:** `ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md`
**Research ancestry:** Issue #170, including MVSF V1 RC2 and its independent re-review PASS.  

This document is a narrow, reusable method for deciding **what to trade, where to trade it, and whether the route is suitable for Human or Quant use**. It is subordinate to V4 and does not create a competing project-wide engineering constitution.

It grants no production Universe change, venue migration, account/capital action, credential/private-API authority, wallet/signing, exchange write/order authority, deployment, Mark Ready or merge authority.

---

## 1. Objective

MVSF answers one integrated question:

```text
WHAT_TO_TRADE
+
WHERE_TO_TRADE_IT
+
FOR_WHICH_MODE(HUMAN|QUANT)
```

The target is the highest **validated after-cost trading usefulness** subject to execution, risk, data, capital, operational and migration constraints.

MVSF is asset-class neutral and venue-topology neutral. It must not optimize for a single headline metric:

```text
MAX_VOLATILITY_ONLY=NO
MAX_LEVERAGE_ONLY=NO
MAX_VOLUME_ONLY=NO
LOWEST_HEADLINE_FEE_ONLY=NO
MOST_LISTED_MARKETS_ONLY=NO
HIGHEST_SINGLE_WEIGHTED_SCORE_ONLY=NO
FAMILIAR_ASSET_OR_VENUE_BIAS=NO
```

Permanent principles:

```text
ASSET_CLASS_LOCK_IN=PROHIBITED
UNIVERSE_SIZE=EVIDENCE_DRIVEN_NOT_FIXED
MAX_LEVERAGE=CAPITAL_CONSTRAINT_INPUT_NOT_ALPHA
MAX_LEVERAGE=NOT_EXPECTED_RETURN
EXCESS_LEVERAGE_ABOVE_RISK_NEED_AUTOMATIC_BONUS=NO
HARD_P0_FAILURE_CANNOT_BE_SCORED_AWAY=YES
UNKNOWN_IS_NOT_PASS=YES
```

Current or historical focus on BTC, ETH, storage equities, indices, commodities or any other class is evidence/context, not ontology.

---

## 2. Durable responsibility split

Use repository/domain ownership, never a chat-window name.

```text
OWNER_DOMAIN=MARKET_AND_VENUE_SELECTION
```

### 2.1 Strategy Research supplies

```text
VERSIONED_STRATEGY_DEMAND_PROFILE
SETUP / THESIS FAMILIES
TIMEFRAMES / HOLDING HORIZONS
REQUIRED_ORDER_PRIMITIVES
STOP / RISK / ATTEMPT SEMANTICS
STRATEGY-SPECIFIC OPPORTUNITY / OUTCOME EVIDENCE
MATERIAL STRATEGY-CONTRACT CHANGES
```

Strategy Research retains Strategy economics and does not lose ownership of Setup, entry/exit, stop, re-entry, risk, position-management or evidence semantics.

### 2.2 Market & Venue Selection owns

```text
GLOBAL_MARKET_DISCOVERY
UNDERLYING / EXPRESSION QUALIFICATION
OPPORTUNITY / TRADABILITY COMPARISON
RISK-BUDGETED CAPITAL-EFFICIENCY COMPARISON
HUMAN UNIVERSE SELECTION
QUANT UNIVERSE SELECTION
UNDERLYING -> VENUE-EXPRESSION ROUTING
PRIMARY / BACKUP / WATCH / REJECT ROUTE MAP
PERIODIC RESELECTION
EVENT-DRIVEN DEMOTION / CHALLENGER RESEARCH
```

### 2.3 Engineering owns

```text
APPROVED REGISTRY / RUNTIME IMPLEMENTATION
PROVIDER BUDGET
HISTORY / REPLAY AVAILABILITY
TRADING FRESHNESS
REALISTIC-SCALE / CAPACITY QUALIFICATION
ADAPTER / INFRASTRUCTURE QUALIFICATION
OPERATIONS / RECOVERY QUALIFICATION
```

Economic qualification by MVSF never bypasses Engineering implementation gates. In particular, Issue #102 provider-budget, history, Trading-Freshness and realistic-scale authority remains intact.

---

## 3. Decision topology — final Universe comes after venue-expression qualification

Canonical flow:

```text
STRATEGY_DEMAND_PROFILE
        |
        v
GLOBAL_MARKET_EXPRESSION_DISCOVERY
        |
        v
NORMALIZE_TO_UNDERLYING_OPPORTUNITY_IDENTITIES
        |
        v
UNDERLYING_COMMON_P0 / CHEAP OPPORTUNITY SCREEN
        |
        v
STRATEGY OPPORTUNITY DENSITY
        |
        v
PRELIMINARY CLUSTER NORMALIZATION
        |
        v
CANDIDATE_UNDERLYING_SHORTLIST          # NON-AUTHORITATIVE / NON-ACTIONABLE
        |
        v
ENUMERATE VENUE-SPECIFIC EXPRESSIONS
        |
        v
EXPRESSION_P0
        |
        v
EXPRESSION EXECUTION / STOP / FEE / MARGIN / LIQUIDATION / CAPITAL ECONOMICS
        |
        +-----------------------+
        |                       |
        v                       v
EXPRESSION_HUMAN_FIT     EXPRESSION_QUANT_FIT
        |                       |
        +-----------+-----------+
                    v
          QUALIFIED_EXPRESSION_SET
                    |
                    v
       FINAL CLUSTER / MARGINAL-VALUE SELECTION
                    |
          +---------+---------+
          |                   |
          v                   v
PROVISIONAL_HUMAN        PROVISIONAL_QUANT
ACTIONABLE_UNIVERSE      ACTIONABLE_UNIVERSE
+ ROUTE_MAP              + ROUTE_MAP
                              |
                              v
                    ENGINEERING PROVIDER / HISTORY /
                    TRADING-FRESHNESS / REALISTIC-SCALE GATE
                              |
                              v
                     IMPLEMENTABLE_QUANT_UNIVERSE
          |                   |
          +---------+---------+
                    v
           SWITCH / ADD / MIGRATE HYSTERESIS
                    |
                    v
          FINAL VERSIONED OPERATING OUTPUT
```

`CANDIDATE_UNDERLYING_SHORTLIST` is explicitly:

```text
NON_AUTHORITATIVE=YES
ACTIONABLE=NO
MAY_NOT_TRIGGER_CAPITAL_OR_RUNTIME_CHANGE=YES
```

There is no final Human or Quant Universe before exact venue expressions have been qualified.

---

## 4. Evaluation identities

### 4.1 Underlying opportunity vs venue expression

Economic opportunity and the tradeable contract are separate identities.

```text
UNDERLYING_OPPORTUNITY
-> VENUE_EXPRESSION_A
-> VENUE_EXPRESSION_B
-> ...
```

Never silently treat different venue derivatives as economically or operationally identical.

### 4.2 Exact expression evaluation unit

Evaluate at least:

```text
UNDERLYING_OPPORTUNITY
x VENUE_CONTRACT
x EXECUTION_TOPOLOGY
x SESSION / LIQUIDITY_REGIME
x ORDER_PRIMITIVE
x TARGET_SIZE
x EFFECTIVE_FEE_PROFILE
x MARGIN_LEVERAGE_PROFILE
x TRADING_MODE(HUMAN|QUANT)
```

Where material also bind:

```text
ACCOUNT_MODE / MARGIN_MODE
COLLATERAL_MODEL
ORACLE / INDEX / MARK MODEL
LIQUIDATION / ADL MODEL
MARKET / RISK-TIER VERSION
VENUE RULE VERSION
ADAPTER VERSION
DATA SEMANTICS VERSION
EXECUTION SEMANTICS VERSION
OBSERVATION WINDOW
SOURCE / OBSERVED_AT TIMESTAMP
```

---

## 5. Evidence hierarchy and qualification state

Use strongest available evidence in this order:

1. valid own execution / fill / latency / order-state telemetry;
2. venue first-party rules, APIs, market data, fee/margin and incident documentation;
3. framework/adapter first-party documentation and exact supported version;
4. regulated/public execution-quality or market-infrastructure evidence where applicable;
5. reputable independent datasets / analytics;
6. aggregators/community evidence only as supplementary discovery or counterevidence.

Every material claim should retain source, timestamp/window and evidence confidence.

P0 state:

```text
PASS | FAIL | UNKNOWN | NOT_APPLICABLE
```

Output qualification state:

```text
QUALIFICATION_STATE=
  QUALIFIED
  | PARTIAL_EVIDENCE
  | NOT_YET_QUALIFIED
  | REJECTED
```

Rules:

```text
ANY_APPLICABLE_P0_FAIL
=> REJECTED

ANY_MATERIAL_APPLICABLE_P0_UNKNOWN
=> NOT_YET_QUALIFIED

PARTIAL_EVIDENCE
=> MAY SUPPORT DISCOVERY / WATCH / RESEARCH PRIORITY ONLY
=> MUST NOT AUTHORIZE FORMAL UNIVERSE PROMOTION OR VENUE MIGRATION
```

---

## 6. Underlying-common screen vs expression-specific P0

### 6.1 Underlying-common screen

Before venue enumeration, use only fields whose semantics are valid at the underlying/opportunity level or are clearly labeled discovery proxies, for example:

```text
REFERENCE / AGGREGATED PRICE PATH
REALIZED MOVEMENT / ATR / STRUCTURE
BROAD ACTIVITY / INTEREST
STRATEGY CANDIDATE / SETUP DENSITY WHEN AVAILABLE
REFERENCE SESSION / EVENT CONTEXT
PRELIMINARY CLUSTER IDENTITY
```

Underlying-common P0 is deliberately narrow:

```text
U_P0_IDENTITY / REFERENCE_INTEGRITY
U_P0_DISCOVERY_DATA_SUFFICIENCY
U_P0_BASE_SESSION / MARKET_EXISTENCE
U_P0_STRATEGY_DOMAIN_COMPATIBILITY
U_P0_MATERIAL_UNDERLYING_EVENT / HALT STATUS
```

### 6.2 Expression-specific fields

The following must not authorize final selection before venue enumeration:

```text
EFFECTIVE FEE
SPREAD / EXECUTABLE IMPACT
STOP / TRIGGER EXECUTION
TARGET-SIZE LIQUIDITY
MARGIN / LEVERAGE / RISK TIER
LIQUIDATION / ADL
VENUE POSITION LIMITS
ACCOUNT / COLLATERAL MODE
ORDER-PRIMITIVE IMPLEMENTATION
DATA / ADAPTER SEMANTICS
```

Expression P0 for exact `UNDERLYING x VENUE_CONTRACT x MODE x SIZE` includes as applicable:

```text
E_P0_ACCESS_AND_LEGAL_USABILITY
E_P0_CONTRACT / VENUE IDENTITY
E_P0_REQUIRED_ORDER_PRIMITIVES
E_P0_TARGET_SIZE_EXECUTABLE_LIQUIDITY
E_P0_EFFECTIVE_FEE_PROFILE_KNOWN_OR_BOUNDED
E_P0_MARGIN / LEVERAGE / RISK-TIER_PROFILE_KNOWN_OR_BOUNDED
E_P0_LIQUIDATION / ADL / POSITION-LIMIT_FEASIBILITY
E_P0_STOP / EXIT_FEASIBILITY_WHEN_STRATEGY_REQUIRES_IT
E_P0_MARK / INDEX / ORACLE_INTEGRITY
E_P0_OPERATIONAL / ORDER-STATE_INTEGRITY
E_P0_CAPITAL / CUSTODY / PROTOCOL_SAFETY
E_P0_DATA / METADATA / ADAPTER_SUFFICIENCY_FOR_MODE
E_P0_MATERIAL_INCIDENT_STATUS
```

CEX/broker and DEX/on-chain evidence may differ, but both converge on the same economic/safety questions. Do not assume `DEX=safe` or `CEX=unsafe`.

---

## 7. Instrument opportunity dimensions

Do not use one giant weighted production score as authority. Use hard gates, interpretable dimensions, reason codes and frontier/Pareto comparison.

```text
I1_OPPORTUNITY_SUPPLY
  realized movement / ATR / volatility / activity / tradable structure

I2_STRATEGY_OPPORTUNITY_DENSITY
  Scanner candidate frequency
  SETUP_READY / Formal conversion
  independent MarketEvent count
  MFE / MAE / Net R / right-tail evidence when valid

I3_EXECUTION_ECONOMICS
  expected all-in execution cost + material funding/carry + repeated-attempt cost

I4_RISK_BUDGETED_CAPITAL_EFFICIENCY
  safe usable leverage
  incremental capital reserve
  liquidation reserve
  risk-sized and liquidity-sized capacity

I5_CAPACITY_AND_MARKET_QUALITY
  target-size depth / executable notional / OI / resiliency / stability

I6_CLUSTER_MARGINAL_VALUE
  redundancy / correlation / Selection Regret / session-regime diversification

I7_HUMAN_ATTENTION_EFFICIENCY
  actionable opportunity value relative to attention / switching / workflow burden

I8_QUANT_INFRA_EFFICIENCY
  actionable opportunity value relative to provider / data / storage / adapter / qualification TCO
```

A composite score may prioritize research/inspection only. It cannot override P0 or independently authorize promotion.

As valid point-in-time Scanner/Shadow/Forward evidence accumulates, it outranks coarse volatility/activity proxies.

---

## 8. Evidence-cost ladder

Use the cheapest decisive evidence first.

```text
STAGE_A_GLOBAL_DISCOVERY
  bars / volume / trade count / OI
  ATR / realized movement / activity
  funding / rough spread
  contract metadata / market hours
  fee + leverage discovery

STAGE_B_SHORTLIST_QUALIFICATION
  BBO / Top-N / topology-equivalent quote curve
  executable VWAP / impact
  exact fee / margin / leverage / risk tier
  oracle / index / session / incident state

STAGE_C_STRATEGY_EVIDENCE
  Scanner / Formal / Shadow
  independent MarketEvent count
  MFE / MAE / Net R
  opportunity density / Selection Regret

STAGE_D_ROUTE_QUALIFICATION
  matched Human task tests
  or Quant order lifecycle / stop behavior
  p50 + tail execution
  reconnect / reconciliation / recovery
```

Do not build a full L2/tick archive or generic distributed market-data platform merely to support daily global discovery.

---

## 9. Execution topology and execution-quality contract

Classify execution topology:

```text
EXECUTION_TOPOLOGY=CLOB|RFQ_OLP|AMM|OTHER
```

Topology-appropriate evidence:

```text
CLOB
-> spread + depth bands + marketable VWAP + fill/latency

RFQ_OLP
-> firm quote curve by size
   + indicative-to-firm drift
   + quote reject/expiry
   + quote-to-fill latency

AMM
-> executable route
   + price impact
   + route failure/revert
   + latency
```

All topologies converge on comparable outputs:

```text
EXECUTION_PRICE_SHORTFALL
EXPECTED_ALL_IN_EXECUTION_COST
EXECUTION_RELIABILITY
```

For target size/order primitive, collect where applicable:

```text
SPREAD_BPS
DEPTH_AT_TARGET_BPS / TOPOLOGY_EQUIVALENT_CAPACITY
L1_FEASIBLE_NOTIONAL
TOP_N_EXECUTABLE_NOTIONAL
MARKETABLE_VWAP_IMPACT_BPS
DECISION_TO_ACK_MS
DECISION_TO_FIRST_FILL_MS
DECISION_TO_COMPLETE_FILL_MS
FILL_RATE
PARTIAL_FILL_RATE
ORDER_REJECT_RATE
CANCEL_ACK_MS
CANCEL_FAILURE_RATE
ADVERSE_SELECTION_AFTER_FILL
OUTAGE / DISCONNECT / DEGRADED_STATE
```

---

## 10. Stop / trigger execution and executable stressed risk

Direct market-order quality and stop/trigger quality are not interchangeable.

Measure separately where applicable:

```text
TRIGGER_SOURCE = LAST | MARK | INDEX | ORACLE | OTHER
TRIGGER_TO_ORDER_ACTIVE_MS
TRIGGER_TO_FIRST_FILL_MS
TRIGGER_TO_COMPLETE_FILL_MS
TRIGGER_TO_FILL_SLIPPAGE_BPS
TRIGGER_MISS / DELAY / REJECT_RATE
```

A stop/trigger line is an activation condition, not a guaranteed executable loss boundary.

### 10.1 Stressed executable loss function

Risk budget is defined against **net executable account loss**, not chart distance alone.

Bind stress identity:

```text
STRESS_MODEL_ID
STRESS_CONFIDENCE_OR_SCENARIO
OBSERVATION_WINDOW
ORDER_PRIMITIVE
SESSION / REGIME
```

No universal p95/p99 threshold is frozen here; it must be calibrated to the Strategy Demand Profile and evidence quality.

For target notional `q`, conceptually define:

```text
P_ENTRY_EXEC(q)
= expected / observed executable entry price

P_STOP_TRIGGER
= Strategy structural / protective trigger reference

P_EXIT_STRESS(q)
= stressed executable exit price after trigger / gap / liquidity state
```

`P_EXIT_STRESS(q)` must capture, where relevant and evidenced:

```text
TRIGGER_SOURCE_BEHAVIOR
TRIGGER_TO_ORDER_ACTIVE_DELAY
TRIGGER_TO_FILL_TAIL_SLIPPAGE
GAP / JUMP_THROUGH_TRIGGER
SIZE-DEPENDENT_MARKET_IMPACT
PARTIAL_FILL / LIQUIDITY_DECAY
ORDER_REJECT / RETRY_PATH
SESSION / UNDERLYING-CLOSED_STATE
TOPOLOGY-SPECIFIC_QUOTE / ROUTE_BEHAVIOR
```

Use mutually exclusive cost components:

```text
STRESSED_NET_LOSS(q)
= PRICE_PNL_LOSS_FROM_ENTRY_EXEC_TO_EXIT_STRESS(q)
+ EXPLICIT_ENTRY_FEES(q)
+ EXPLICIT_EXIT_FEES(q)
+ MATERIAL_UNAVOIDABLE_FUNDING / CARRY(q)
+ OTHER_NON_PRICE_COSTS_NOT_ALREADY_IN_EXECUTION_PRICE
```

Stressed executable prices already embody spread, impact and trigger-fill price effects; do not add those price effects again.

Risk-sized notional:

```text
N_RISK_STRESS
= sup { q : STRESSED_NET_LOSS(q) <= TRADE_RISK_BUDGET }
```

The implicit form is required because executable loss may be nonlinear in size.

### 10.2 Independent entry/exit liquidity caps

```text
N_ENTRY_LIQUIDITY
= max q that can enter within accepted entry execution-quality limits

N_EXIT_STRESS_LIQUIDITY
= max q that can exit under the defined stressed scenario within accepted
  fill / slippage / latency / reject constraints
```

Final expression capacity:

```text
N_EFFECTIVE
= min(
    N_RISK_STRESS,
    N_MARGIN_ACCOUNT_STATE,
    N_ENTRY_LIQUIDITY,
    N_EXIT_STRESS_LIQUIDITY,
    N_VENUE_LIMIT
  )
```

No component receives an automatic ranking bonus merely for being large. A candidate without defensible stop/exit-tail evidence may remain a discovery/watch candidate but cannot claim authoritative risk-budgeted capital efficiency for a stop-dependent Strategy.

---

## 11. Leverage, margin and account-state capital efficiency

Headline max leverage and standalone initial margin are discovery metadata only.

Bind where material:

```text
MAX_LEVERAGE
LEVERAGE_TIER_BY_NOTIONAL
INITIAL_MARGIN_MODEL
MAINTENANCE_MARGIN_MODEL
MARGIN_MODE
LIQUIDATION_MECHANICS
LIQUIDATION_BUFFER
OPEN_INTEREST / POSITION_CAP
SESSION_OR_OVERNIGHT_MARGIN_OR_LEVERAGE_CHANGE
CROSS / ISOLATED_EFFECT
FUNDING / ROLLOVER / CARRY
PROJECT_POLICY_LEVERAGE_CAP
```

Define an account-state-aware reserve function:

```text
INCREMENTAL_CAPITAL_RESERVE(q, ACCOUNT_STATE)
```

Include where material:

```text
INITIAL_MARGIN
MAINTENANCE_MARGIN
CROSS / ISOLATED
PORTFOLIO-MARGIN_OFFSET
EXISTING_POSITIONS / CORRELATION_OFFSET
COLLATERAL_HAIRCUT / LTV
BORROW / INTEREST
CONCENTRATION / STRESS_ADD_ON
POSITION / RISK_TIER
LIQUIDATION_SAFETY_BUFFER
VENUE / BROKER_HOUSE_MARGIN_ABOVE_MINIMUM
SESSION / OVERNIGHT_MARGIN_CHANGE
```

Do not assume portfolio offsets persist in stress unless the venue methodology supports that claim.

Report separate economic outputs instead of one authority score:

```text
EXPECTED_NET_R                         # only with valid Strategy evidence
RETURN_ON_RISK_CAPITAL
RETURN_ON_INCREMENTAL_MARGIN_RESERVE
CAPACITY_ADJUSTED_EXPECTANCY
PEAK_INCREMENTAL_CAPITAL_RESERVE
```

If Strategy expectancy is not defensible, capital metrics remain feasibility/sensitivity diagnostics only.

Permanent leverage interpretation:

```text
MAX_LEVERAGE != ALPHA
MAX_LEVERAGE != EXPECTED_RETURN

IF AVAILABLE_LEVERAGE_ALREADY_SUPPORTS_THE_BINDING_RISK_SIZED_NOTIONAL:
  ADDITIONAL_HEADLINE_LEVERAGE
  GETS_NO_AUTOMATIC_RANKING_BONUS
```

Low-volatility, high-safe-leverage markets may still outrank higher-volatility markets if after-cost, stressed-risk, liquidity and incremental-capital economics support it.

---

## 12. Transaction-cost semantics and exact fee identity

### 12.1 Pre-trade route estimate

```text
EXPECTED_ALL_IN_EXECUTION_COST
= EXPLICIT_FEES
+ EXPECTED_EXECUTION_PRICE_SHORTFALL_EX_FEES
+ MATERIAL_FUNDING / CARRY / ROLLOVER
+ OTHER_COSTS_NOT_ALREADY_IN_PRICE_OR_FEES
```

Component definitions must be mutually exclusive.

### 12.2 Post-trade TCA

Use:

```text
TOTAL_IMPLEMENTATION_SHORTFALL
```

as total explicit + implicit implementation cost relative to the specified decision/arrival benchmark, including delay/execution/opportunity-cost components as applicable.

Permanent anti-double-count rule:

```text
NEVER:
TOTAL_IMPLEMENTATION_SHORTFALL + EXPLICIT_FEES
WHEN TOTAL_IMPLEMENTATION_SHORTFALL ALREADY INCLUDES THOSE FEES
```

Unfilled-order opportunity cost is separate in pre-trade qualification unless the chosen TCA definition explicitly includes it.

### 12.3 Exact effective-fee identity

Bind where material:

```text
ACCOUNT_TIER
MARKET / DEPLOYER_FEE
MAKER / TAKER_PROGRAM
REFERRAL / REBATE / TOKEN_DISCOUNT
TIER_ELIGIBILITY_BASIS
ROLLING_VOLUME_WINDOW
TIER_MEASUREMENT_ENTITY / ACCOUNT
PROMO_START / PROMO_EXPIRY / UNTIL_FURTHER_NOTICE_STATE
ACCOUNT_ENTITY / JURISDICTION
PAYMENT / COLLATERAL_TOKEN_DISCOUNT
PRODUCT / MARKET-SEGMENT_SPECIFIC_PROGRAM
EFFECTIVE_FROM
FEE_OBSERVED_AT
```

If exact eligibility is unknown, publish sensitivity cases and keep any fee-sensitive promotion `NOT_YET_QUALIFIED`.

---

## 13. Human branch

Human fit asks whether an experienced discretionary trader can execute the intended method quickly and correctly without the venue amplifying known behavior errors.

Core dimensions:

```text
H1_SITUATION_AWARENESS
H2_ACTION_EFFICIENCY
H3_USE_ERROR_RESISTANCE
H4_BEHAVIOR_COMPATIBILITY
H5_EXECUTION_TRANSPARENCY
H6_WORKFLOW_CONTINUITY
```

Standard task qualification should include as applicable:

```text
OPEN_LONG / OPEN_SHORT
PLACE_PROTECTIVE_STOP
MODIFY_STOP
REDUCE_ONLY_PARTIAL_OR_FULL_EXIT
EMERGENCY_TIME_TO_FLAT
CANCEL_ALL
VERIFY_POSITION / OPEN_ORDERS / TRIGGER_ORDERS
VERIFY_TRIGGER_SOURCE
DIAGNOSE_NON_FILL / PARTIAL_FILL / STOP_FILL
RECOVER_TRUE_STATE_AFTER_RECONNECT
```

Collect:

```text
TASK_SUCCESS_RATE
MEDIAN / TAIL_COMPLETION_TIME
USE_ERROR_RATE
CRITICAL_ERROR_RATE
TIME_TO_ENTRY
TIME_TO_PROTECT
TIME_TO_FLAT
ORDER_STATE_CLARITY
```

Speed is valuable only conditional on correctness.

Review whether the venue amplifies or mitigates known behavior failure modes, including as applicable:

```text
HOLDING_LOSERS
RAPID_REENTRY
ADVERSE_DIRECTION_ADD
OPENING_CHAOS_OVERTRADING
MISREAD_TRIGGER_OR_ORDER_STATE
DELAYED_PROTECTION
ACCIDENTAL_REVERSE / WRONG_SIDE / WRONG_SIZE
```

Human fit is not inferred from Quant/API quality.

---

## 14. Quant branch

Quant fit asks whether the expression can support the Strategy/data/execution contract causally, reproducibly and with bounded lifecycle burden.

Core dimensions:

```text
Q1_LIVE_DATA_COVERAGE
Q2_HISTORICAL_DATA_COVERAGE
Q3_DATA_SEMANTIC_FIDELITY
Q4_REPLAY / BACKTEST_FIDELITY
Q5_EXECUTION_API_FIDELITY
Q6_FRAMEWORK / NAUTILUS_FIT
Q7_OPERATIONS / RECOVERY / OBSERVABILITY
Q8_DATA_AND_INFRASTRUCTURE_TCO
```

### 14.1 Data matrix

Record independently:

```text
LIVE_BARS
LIVE_BBO
LIVE_TRADES
LIVE_TOP_N / L2 / L3
LIVE_MARK / INDEX / ORACLE
LIVE_FUNDING / OI / CONTEXT

HIST_BARS
HIST_TRADES
HIST_BBO
HIST_TOP_N / L2 / L3

FREE_LIVE_DATA
FREE_HISTORICAL_DATA
DATA_LICENSE / RETENTION_RIGHTS
MAX_LOOKBACK
RATE_LIMITS
DATA_GAPS / KNOWN_INCOMPLETENESS
SELF_CAPTURE_REQUIRED
THIRD_PARTY_DATA_REQUIRED
```

Do not require full L2/L3 by default. Escalate data depth only on measured need.

### 14.2 Causal/semantic requirements

As applicable:

```text
PROVIDER_EVENT_TIMESTAMP
LOCAL_INIT / RECEIVE_PROVENANCE
ADMISSION_TIMESTAMP
SEQUENCE / GAP_DETECTION
SNAPSHOT / RECOVERY_SEMANTICS
CHANGE_DRIVEN_VS_PERIODIC_FEED_SEMANTICS
DUPLICATE_HANDLING
BAR_FINALITY
INSTRUMENT_IDENTITY / METADATA_VERSION
HISTORICAL_LIVE_SEMANTIC_CONSISTENCY
```

A field existing is not enough if causal semantics cannot be defended.

### 14.3 Execution API requirements

As applicable:

```text
CLIENT_ORDER_ID
ACK / REJECT
PARTIAL_FILL
CANCEL
AMEND / REPLACE
STOP / TRIGGER
REDUCE_ONLY
POST_ONLY
TIF
ORDER / FILL_STREAM
POSITION / ACCOUNT_RECONCILIATION
IDEMPOTENCY
RESTART / RECONNECT_RECOVERY
TESTNET / SANDBOX
KILL / CANCEL_ALL
RATE_LIMIT_HEADROOM
```

### 14.4 Quant TCO

```text
QUANT_TCO
= TRADING_FRICTION
+ DATA_SUBSCRIPTION / PURCHASE
+ SELF_CAPTURE / STORAGE
+ NORMALIZATION / INTEGRATION
+ ADAPTER / FRAMEWORK_WORK
+ TEST / QUALIFICATION
+ MONITORING / RECOVERY
+ UPGRADE / MAINTENANCE
+ MODEL_UNCERTAINTY_COST
```

Free APIs can still create high TCO.

---

## 15. Cluster, redundancy and Selection Regret

Do not treat raw market count as independent opportunity count.

Preserve where applicable:

```text
RAW_MARKET_LEVEL
SETUP_RESEARCH_CLUSTER
EXPOSURE_CLUSTER
CLUSTER_NORMALIZED
LEADER_ONLY
```

Use preliminary cluster normalization before venue qualification to reduce research burden, but perform final cluster/marginal-value selection only after qualified venue expressions are known.

Selection should account for `SELECTION_REGRET`, best-of-cluster expression quality, shared-risk exposure and marginal session/regime diversification.

---

## 16. Venue Opportunity Surface

A venue may be strategically valuable because it persistently exposes more qualified opportunities even if one overlapping market is only marginally better.

Track without reverting to venue-first ranking:

```text
QUALIFIED_INSTRUMENT_COUNT
QUALIFIED_INSTRUMENT_HOURS
CLUSTER_ADJUSTED_OPPORTUNITY_DENSITY
AFTER_COST_OPPORTUNITY_SUPPLY
SESSION_DIVERSITY
ASSET / REGIME_DIVERSITY
NEW_MARKET_RESPONSIVENESS
```

`NUMBER_OF_LISTED_MARKETS` is discovery metadata, not value by itself.

---

## 17. Versioned output contract

A formal cycle should publish versioned outputs, not one exchange leaderboard:

```text
DISCOVERY_UNIVERSE
  broad discovered/eligible opportunities

CANDIDATE_UNDERLYING_SHORTLIST
  non-authoritative underlyings selected for expression qualification

HUMAN_ACTIONABLE_UNIVERSE
  qualified expressions under bounded human attention/workflow constraints

QUANT_ACTIONABLE_UNIVERSE
  economically/data/adapter-qualified expressions before Engineering production-scale gate

IMPLEMENTABLE_QUANT_UNIVERSE
  Quant expressions that additionally pass applicable provider/history/freshness/realistic-scale Engineering gates

CAPITAL_PRIORITY_VIEW
  risk-budgeted / after-cost priority among currently qualified opportunities

VENUE_ROUTE_MAP
  underlying opportunity
  -> PRIMARY expression
  -> BACKUP expression(s)
  -> WATCH expression(s)
  -> REJECTED / NOT_YET_QUALIFIED expression(s)
```

Every record should retain:

```text
STRATEGY_DEMAND_PROFILE_ID
UNDERLYING_ID
VENUE_CONTRACT_ID
TRADING_MODE
QUALIFICATION_STATE
FEE / MARGIN / RISK-TIER_IDENTITY
DATA / EXECUTION_SEMANTICS_VERSION
SOURCE / OBSERVED_AT
OBSERVATION_WINDOW
REASON_CODES
```

---

## 18. Cadence, persistence and emergency demotion

Separate cheap observation from authoritative changes.

Default cadence candidate:

```text
GLOBAL_DISCOVERY_SCAN
= DAILY

HUMAN_QUANT_PRIORITY_SHORTLIST_REFRESH
= DAILY

FORMAL_UNIVERSE_RESELECTION
= EVERY_2_TO_4_WEEKS_EARLY
= APPROX_MONTHLY_STEADY_STATE

VENUE_ROUTE_DELTA_REVIEW
= MONTHLY_LIGHTWEIGHT + EVENT_DRIVEN

FULL_VENUE_REQUALIFICATION_OR_MIGRATION
= MATERIAL_TRIGGER_ONLY
```

The cadence is a default operating schedule, not a substitute for evidence.

Permanent authority semantics:

```text
DAILY_DISCOVERY=NON_AUTHORITATIVE
DAILY_PRIORITY_SHORTLIST=NON_AUTHORITATIVE
```

Formal promotion/demotion requires versioned persistence/materiality evidence calibrated to the domain; MVSF does not freeze arbitrary K-of-N thresholds without evidence.

Emergency exception:

```text
APPLICABLE_P0_FAIL
=> IMMEDIATE_DEMOTION / SAFE_STOP REVIEW ALLOWED
=> NO PERSISTENCE WAIT REQUIRED
```

Examples include security/capital-access failures, oracle/index integrity failure, halt/delist, execution-integrity failure, liquidity collapse or data-integrity failure.

Material Quant Universe-size change remains subject to provider-budget, history/replay, Trading-Freshness and realistic-scale qualification before production release.

---

## 19. Switching hysteresis, multi-venue routing and migration

Finding a better instrument does not imply changing the entire venue. Prefer per-instrument routing where operationally supportable.

Historical sunk cost/familiarity does not justify keeping a venue. Future switching cost is economically real.

Normal route-add/migration consideration requires:

```text
CANDIDATE_P0=PASS
EVIDENCE_CONFIDENCE=SUFFICIENT
FORWARD_NET_ADVANTAGE_IS_MATERIAL=YES
DECISION_STABLE_UNDER_REASONABLE_SENSITIVITY=YES
```

Conceptual comparison:

```text
FORWARD_NET_ADVANTAGE
≈ EXECUTION_QUALITY_GAIN
 + AFTER_COST_EDGE_GAIN
 + NEW_MARKET / OPPORTUNITY_VALUE
 + RELIABILITY / SAFETY_GAIN
 + DATA / RESEARCH_VALUE
 - INCREMENTAL_RECURRING_TCO
 - CAPITAL_FRAGMENTATION_COST
 - AMORTIZED_MIGRATION_BURDEN
 - UNCERTAINTY_RESERVE
```

Small score differences are insufficient.

A P0 failure cannot be weighted back into acceptance by switching hysteresis.

Migration types:

```text
M1_HUMAN_ONLY_VENUE_CHANGE
M2_QUANT_ONLY_VENUE_CHANGE
M3_DUAL_HUMAN_AND_QUANT_CHANGE
M4_ADD_QUALIFIED_SECONDARY_VENUE
M5_REPLACE_PRIMARY_VENUE
M6_EMERGENCY_EXIT_FROM_P0_FAILURE
```

No in-place blind migration. Material route changes should use bounded parallel qualification, Shadow/Testnet/small-pilot evidence where applicable, rollback and exact version identity.

---

## 20. Venue/framework portability

Preserve three independent version axes:

```text
AXIS_A=STRATEGY_VERSION
AXIS_B=TRADING_INFRASTRUCTURE_VERSION
AXIS_C=VENUE_CONTRACT_VERSION
```

Venue contract binds at minimum:

```text
VENUE_ID
ADAPTER_VERSION
INSTRUMENT_MAPPING_VERSION
MARKET_RULE_VERSION
FEE_PROFILE_VERSION
DATA_SEMANTICS_VERSION
EXECUTION_SEMANTICS_VERSION
```

Regression isolation:

```text
CHANGE_VENUE_CONTRACT
=> FREEZE_STRATEGY_ECONOMICS
=> FREEZE_TRADING_INFRASTRUCTURE_VERSION

CHANGE_TRADING_INFRASTRUCTURE_VERSION
=> FREEZE_STRATEGY_ECONOMICS
=> FREEZE_VENUE_CONTRACT_WHERE_PRACTICAL

CHANGE_STRATEGY_VERSION
=> FREEZE_INFRASTRUCTURE
=> FREEZE_VENUE_CONTRACT_WHERE_PRACTICAL
```

Do not combine venue migration, framework migration and Strategy economics change into one acceptance claim.

Project-owned portable assets remain:

```text
VERSIONED_STRATEGY_PACKAGE
PROJECT_CANONICAL_RESEARCH / EVIDENCE DATA + SCHEMA
STABLE MARKET / STRATEGY / ORDER-INTENT DOMAIN CONTRACTS
VERSIONED VENUE_MAPPING / PROVENANCE_MANIFEST
```

Venue/framework-specific code belongs behind a thin replaceable boundary. Do not create a second generic OMS, reconnect stack, portfolio authority or second authoritative state merely to support another venue.

---

## 21. Research and anti-overclaim rules

This framework defines the decision method, not universal market thresholds.

Do not freeze from one calibration window:

```text
UNIVERSAL_MIN_VOLUME
UNIVERSAL_MIN_OI
UNIVERSAL_MAX_SPREAD
UNIVERSAL_MAX_SLIPPAGE
UNIVERSAL_P95 / P99_STOP_THRESHOLD
UNIVERSAL_LEVERAGE_TARGET
UNIVERSAL_K_OF_N_PERSISTENCE_RULE
```

Calibrate thresholds to Strategy Demand Profile, target size, trading mode, evidence quality and operating constraints.

Current-market snapshots are time-bound evidence and must be refreshed when used for an actual decision.

A research/calibration PASS is not production selection authority.

---

## 22. Formal selection lifecycle

For a formal reselection cycle:

```text
1. FREEZE STRATEGY_DEMAND_PROFILE_ID
2. RUN CHEAP GLOBAL DISCOVERY
3. BUILD NON-AUTHORITATIVE CANDIDATE_UNDERLYING_SHORTLIST
4. ENUMERATE MATERIAL VENUE EXPRESSIONS
5. APPLY EXPRESSION P0
6. MEASURE EXECUTION / STOP / FEE / MARGIN / LIQUIDATION / CAPITAL ECONOMICS
7. APPLY HUMAN AND/OR QUANT FIT
8. BUILD QUALIFIED_EXPRESSION_SET
9. APPLY FINAL CLUSTER / MARGINAL-VALUE SELECTION
10. BUILD PROVISIONAL HUMAN / QUANT UNIVERSES + ROUTE MAP
11. FOR QUANT PRODUCTION CHANGES, RUN APPLICABLE ENGINEERING PROVIDER/HISTORY/FRESHNESS/SCALE GATES
12. APPLY PERSISTENCE / MATERIALITY AND SWITCHING HYSTERESIS
13. FREEZE VERSIONED OUTPUT + EVIDENCE MANIFEST + RESIDUAL UNKNOWNS
14. REQUIRE SEPARATE AUTHORITY FOR ANY RUNTIME, CAPITAL, ACCOUNT OR EXECUTION CHANGE
```

---

## 23. Re-open and change control

Re-open MVSF method research when at least one occurs:

```text
NEW_EXECUTION_TOPOLOGY_NOT_REPRESENTABLE_BY_CURRENT_MODEL
NEW_MARGIN / CAPITAL_MODEL_BREAKS_CURRENT_ACCOUNT-STATE_GEOMETRY
REPEATED_REAL_DECISION_FAILURE_TRACEABLE_TO_METHOD_OMISSION
HUMAN_OR_QUANT_ROUTE_CHANGES_CANNOT_BE_EXPLAINED_BY_CURRENT_EVIDENCE_MODEL
MATURE_BEST-EXECUTION / RISK METHOD_MATERIALLY_CHANGES
CURRENT_METHOD_FORCES_DUPLICATED_COMMODITY_INFRASTRUCTURE
OWNERSHIP_CONFLICT_EMERGES_WITH_STRATEGY / ENGINEERING / OPERATIONS
```

A normal change in which asset or venue ranks highest does not require changing the framework.

Any material change to this durable method must follow current V4 research, preflight, exact-artifact, independent-review and publication gates.

---

## 24. Research ancestry / acceptance boundary

Issue #170 contains the non-canonical research/calibration ancestry, including:

```text
ROUND_1_REAL_MARKET_CALIBRATION
ROUND_2_INSTRUMENT / LEVERAGE / CROSS-VENUE_CALIBRATION
MVSF_V1_RC1
RC1_INDEPENDENT_REPLAN
MVSF_V1_RC2
RC2_INDEPENDENT_REREVIEW_PASS
```

Those research comments explain why the method exists but do not themselves authorize production changes.

This file becomes the durable Market & Venue Selection method only after the applicable publication PR is independently accepted and merged under current project authority.
