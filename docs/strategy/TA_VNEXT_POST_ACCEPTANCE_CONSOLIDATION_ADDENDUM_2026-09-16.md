# TA_VNEXT Post-Acceptance Consolidation Addendum — 2026-09-16

Status: PUBLICATION-CLEAN CONSOLIDATION CANDIDATE / NON-EXECUTABLE
Date: 2026-09-16
Source accepted artifact: PR #168 exact HEAD `5fb311de457aa8a449c7c6fa2028630c2f4a36be`
Current publication base: `main` after PR #180 merge
Parent authorities: #161, #150, #85, #163, #174

This addendum publishes the current accepted status and bounded post-acceptance contract/validation/stage-placement deltas without reopening Strategy economics.

It does not create a new Setup, Strategy family, Entry/Exit/Re-entry/Winner policy, numeric threshold, Nautilus dependency/version, Product UI, execution permission or trading authority.

## 0. Precedence and scope

Read order:

```text
accepted Sep-11 base files
-> TA_VNEXT_PRE_E4_REPAIR1_CONTRACT_ADDENDUM_2026-09-11.md
-> THIS Sep-16 post-acceptance consolidation addendum
```

Repair 1 continues to override only conflicting clauses for:

```text
R1 BBO validity / continuity
R2 >=60s precursor BBO + TradeTick prebuffer and incomplete-prehistory semantics
R3 order-active causal fill reference
R4 U21 / U23 / U25 governance dispositions
N1 timestamp terminology / ts_init semantics
N2 adaptive multi-Challenger Forward selection contamination
```

This addendum has precedence only for:

- current publication/status pointers;
- accepted post-Repair-1 execution-realism contract additions;
- Independent Validation workstream responsibility/method gates;
- Product stage placement after E4 scope minimization;
- current next-stage sequencing.

All non-conflicting accepted September 11 Strategy/Data/Validation economics and semantics remain unchanged.

## 1. Terminal Repair-1 acceptance and current status

Canonical terminal acceptance:

- PR #168 comment `5631267991` — `THIRD_PARTY_PRE_E4_DELTA_REVIEW=PASS`;
- #161 comment `5631264789` — Strategy acceptance;
- PR #168 comment `5631565108` — accepted-head preservation / publication housekeeping;
- #163 comment `5631266751` — Engineering handoff release.

Current identity remains:

```text
STRATEGY_VERSION=TA_VNEXT_E4_C1_2026-09-11
POLICY_VERSION=TA_FRICTION_POSITION_POLICY_V0_1
PARAMETER_VERSION=TA_PRE_E4_GRID_V0_1
DERIVATION_VERSION=TA_MICROSTRUCTURE_DERIV_V0_1
CURRENT_THREE_SETUP_AUTHORITY=UNCHANGED
THIRD_PARTY_PRE_E4_DELTA_REVIEW=PASS
STRATEGY_DATA_VALIDATION_CLOSED_LOOP_ACCEPTED=YES
LIVE_STRATEGY_CHANGE=NO
```

No later accepted authority identified before this publication changed those four VNext version identities.

Historical file-local phrases such as:

```text
REPAIR_APPLIED_PENDING_DELTA_REVIEW
ENGINEERING19_HANDOFF_ALLOWED=NO_PENDING_DELTA_REVIEW
E4_HARD_HOLD=ACTIVE
E4_HARD_HOLD=ACTIVE_UNTIL_ENGINEERING19_INDEPENDENT_ACCEPTANCE
```

are retained inside the byte-preserved source files as historical stage-state evidence. They no longer represent the current project hold state.

The common Nautilus E4 public-data/causal-evidence foundation has since received exact-head/provider independent acceptance and was merged via PR #177. This publication does not claim that ordinary Strategy calibration/G4 or E5 promotion is therefore complete.

## 2. Strategy economics remain frozen

This addendum does not modify:

- the Three Setup directional authority;
- EA0-EA4 research family definitions;
- AP0-AP5 Attempt/Stop research family definitions;
- C1 attempt budget;
- WC0-WC3 Winner Confirmation families;
- A0 no-add baseline;
- X0-X3 Winner Exit comparison;
- partial-scale-out deferral;
- room-to-cost diagnostic grid;
- stop/time/volatility diagnostic grids;
- giveback diagnostic grid;
- market/universe Strategy economics;
- any production threshold.

Any future material change to Strategy/Policy/Parameter/Derivation semantics requires a new immutable version and the normal trial/OOS/Forward reset discipline.

## 3. Accepted execution-realism and approval-data contract

Canonical source: #161 comment `5661968053`.

The following are minimum evidence/contract requirements because they may materially change the claim `does the Strategy retain deployable after-cost edge?`.

### 3.1 Causal executable Entry checkpoints

Retain or deterministically derive, when applicable:

```text
armed_ts
activation_ts / signal_ts
signal_reference_price
signal_bid_px / signal_ask_px / signal_executable_px

human_approval_ts
approval_bid_px / approval_ask_px / approval_executable_px
approval_evidence_role=OBSERVED|SIMULATED|NOT_APPLICABLE

guard_eval_ts
guard_result=PASS|NO_SUBMIT
guard_reason_codes

order_submit_intent_ts
order_active_ts
order_active_bid_px / order_active_ask_px / order_active_executable_px

fill_market_state_ts
fill_ts
fill_vwap_or_modeled_fill_px
fill_quantity
fee
execution_model_version
execution_model_limited
```

Do not create a second tick store or generic TCA platform. Reuse the accepted causal BBO/TradeTick/Nautilus evidence surfaces.

### 3.2 Implementation-shortfall attribution

The report/research layer should support side-adjusted adverse-bps decomposition including:

```text
REFERENCE_TO_SIGNAL_EXEC_BASIS_BPS
SIGNAL_TO_APPROVAL_DRIFT_BPS
APPROVAL_TO_ORDER_ACTIVE_DRIFT_BPS
ORDER_ACTIVE_TO_FILL_IMPACT_BPS
SIGNAL_TO_FILL_SHORTFALL_BPS
EXPLICIT_FEES_BPS
FUNDING_BPS_WHEN_RELEVANT
ALL_IN_IMPLEMENTATION_SHORTFALL_BPS
```

Economic views include:

```text
STRATEGY_IMMEDIATE_EXECUTABLE_NET_EDGE
DEPLOYED_WORKFLOW_NET_EDGE
EDGE_LOST_TO_HUMAN_DELAY
EDGE_LOST_TO_SYSTEM_DELAY
EDGE_LOST_TO_MARKET_EXECUTION
```

These are derived evidence/report requirements, not a separate TCA service.

### 3.3 EntryExecutionGuard and NO_SUBMIT

E4/E5 require deterministic zero-write guard semantics and reason-coded counterfactual `NO_SUBMIT`; actual Human approval runtime/UI is deferred to E6.

A guard failure is terminal for that exact package + Activation and does not silently remain armed:

```text
ACTIVATION
-> APPROVAL/REVALIDATION
-> GUARD_FAIL
-> NO_SUBMIT_TERMINAL_FOR_THIS_PACKAGE_AND_THIS_ACTIVATION

IF THESIS_INVALID:
   THESIS_TERMINAL
ELSE:
   WAIT_FOR_FRESH_TRIGGER
   -> fresh causal Activation
   -> new exact package / new Human approval when Human stage applies
```

```text
NO_SUBMIT != ATTEMPT_FAILED
```

because no new-risk Attempt/fill occurred.

Bounded reason identities may include:

```text
PRICE_MOVED_TOO_FAR
SPREAD_OR_FRICTION_TOO_HIGH
ROOM_TO_COST_FAIL
SIZE_DEPTH_FAIL
DATA_HEALTH_FAIL
PACKAGE_EXPIRED
THESIS_INVALID
ACTIVATION_INVALID
```

The exact numeric production entry guard and provider execution collar remain unproven; Nautilus adapter defaults are not project Strategy thresholds.

### 3.4 ARMED / approval-timing evidence

`PREAUTHORIZED_ARMED` remains a preferred policy hypothesis for later zero-write Human evaluation, not a proven production winner.

E4/E5 preserve counterfactual state/evidence, including:

```text
ARMED_TO_ACTIVATION_LEAD_TIME_MS
approval_timing_mode=POST_ACTIVATION|PREAUTHORIZED_ARMED
```

E6 later measures observed Human approval timing, including preapproval coverage, approval-before-Activation, expiry and post-approval guard-fail rates.

### 3.5 Stop execution realism

Do not retune AP0-AP5 merely from this addendum. Retain the execution path evidence needed to prevent idealized stop PnL:

```text
stop_decision_ts
stop_trigger_ts
stop_order_active_ts
stop_executable_reference
stop_fill_ts
stop_fill_vwap
stop_trigger_to_fill_shortfall_bps
used_stop_execution_collar_bps
```

### 3.6 Explicitly deferred/rejected expansion

This publication preserves the accepted diminishing-return decisions:

```text
FULL_L2_FIRST=REJECT
L3_L4=REJECT_OR_PARK
GENERIC_TCA_PLATFORM=REJECT
NEW_LATENCY_SERVICE=REJECT
CUSTOM_NETWORK_TRACING_PLATFORM=REJECT
AWS_LOCATION_MICRO_OPTIMIZATION=PARK
LARGE_PRICE_GUARD_GRID=REJECT
AUTO_TUNING_OR_SELF_MODIFYING_GUARD=REJECT
MULTI_ACTIVATION_REUSE_OF_ONE_APPROVAL=PARK
COMPLEX_STOP_OPTIMIZER=PARK
```

Conditional richer depth remains available only if the accepted size-feasibility trigger fires.

## 4. Independent Validation responsibility freeze

Canonical sources:

- #85 comment `5662126687` — Independent Validation charter and hardening freeze;
- #161 comment `5662129799` — Strategy / Validation / Engineering responsibility separation.

Responsibilities are distinct:

```text
STRATEGY_WORKSTREAM
= propose/derive economic hypotheses
+ freeze Strategy/Policy/Parameter/Derivation semantics
+ preregister bounded candidate families and claim intent
+ define Strategy-owned metric meaning
+ respond to validation findings

ENGINEERING_WORKSTREAM
= implement accepted causal evidence/replay/Shadow/report surfaces
+ prove technical correctness
+ not invent Strategy/statistical policy

INDEPENDENT_VALIDATION_WORKSTREAM
= execute/adjudicate formal backtest / paired replay / chronological OOS
+ execute/adjudicate G4 Shadow and E5 Forward evidence
+ audit causal/data/execution realism
+ apply anti-overfit/dependence/multiplicity controls
+ determine supported claim scope
```

```text
STRATEGY_SELF_VALIDATION_AS_FINAL_PROMOTION_AUTHORITY=NO
ENGINEERING_SELF_VALIDATION_OF_STRATEGY_EDGE=NO
```

A material Strategy change after inspecting formal validation evidence triggers the normal version/OOS/Forward reset rules; the same evidence is not silently reclassified as pristine confirmation.

## 5. Validation hardening V1-V6

These are correctness/validity requirements, not new Strategy economics.

### V1 — TradeTick identity / dedup / order / reconnect

Before flow-derived evidence is trusted:

```text
DUPLICATE_TRADE_CANNOT_CHANGE_FLOW_FEATURE=YES
RECONNECT_REPLAY_CANNOT_DOUBLE_COUNT=YES
OUT_OF_ORDER_POLICY=DETERMINISTIC
AGGRESSOR_SIDE_MAPPING_TESTED=YES
```

Use the exact authoritative provider/native trade identity available for the accepted adapter surface.

### V2 — no implicit optimistic fill defaults

The run manifest must bind the accepted Nautilus/execution-model assumptions as applicable, including fill model, slippage/fill probabilities, liquidity consumption/queue assumptions, book type, random seed and execution-model version.

```text
IMPLICIT_DEFAULT_FILL_ASSUMPTION=NO
```

Passive touch is not promotion-grade proof of fill without defensible queue/fill assumptions.

### V3 — per-candidate simulated execution-state isolation

Paired candidates may share immutable causal market state, but must not mutate each other's simulated orders/fills/positions/consumed liquidity/account state.

### V4 — replay parity through outcomes

For deterministic configuration:

```text
SAME_MANIFEST + SAME_ADMITTED_EVENTS
=> SAME_DECISIONS
=> SAME_ORDER_INTENTS
=> SAME_HYPOTHETICAL_ORDER_LIFECYCLE
=> SAME_FILLS_FEES
=> SAME_THESIS_ATTEMPT_TERMINAL_OUTCOMES
```

If stochastic execution is used, the declared seed must reproduce the run; any intentionally nondeterministic promotional surface requires an explicit reviewed method.

### V5 — point-in-time universe / eligibility

Historical G2/G3 claims must bind point-in-time universe/listing/instrument/venue/fee-state identity as applicable. Today's surviving markets cannot stand in for historical eligibility.

### V6 — NOT_EVALUABLE missingness remains in the denominator

Retain and report incomplete / `NOT_EVALUABLE` observations and typed reasons. If non-evaluability concentrates in the same volatile/high-friction states central to a claimed edge, Independent Validation narrows or withholds the broad claim rather than evaluating only the convenient complete subset.

## 6. PRE-E5 statistical-method freeze

Before any evidence set is opened/used as confirmatory E5 evidence, freeze the applicable method controls from #85 `5662126687`:

### S1 — analysis looks / optional stopping

Predeclare fixed analysis looks or a separately reviewed valid sequential/always-valid method. Do not continuously peek and stop at the first conventional confidence bound that turns favorable.

### S2 — claim hierarchy / multiplicity

Freeze:

```text
PRIMARY_BROAD_CLAIM
SMALL_PRESPECIFIED_SECONDARY_CLAIMS
EXPLORATORY_ONLY_DECOMPOSITIONS
```

Post-hoc best-looking subgroup findings are exploratory until later fresh confirmation.

### S3 — dependence / cluster-resampling

Freeze a versioned cluster construction and resampling method so correlated simultaneous/session/theme/macro opportunities are not treated as independent merely because they have separate Thesis IDs.

### S4 — stochastic-fill seed policy

One seed establishes reproducibility, not robustness. If stochastic FillModel behavior is material to a claim, predeclare the seed-set/sensitivity policy; seed shopping is prohibited.

### S5 — Forward cutoff / unresolved Thesis treatment

Every formal look freezes its evidence cutoff and explicitly accounts for active/unresolved/right-censored Opportunities/Theses. Do not choose a completion rule that waits selectively for favorable resolution or silently drops unresolved adverse-looking cases.

These method controls do not reopen broad Strategy economics.

## 7. PRE-E8 portfolio/capital-contention gate

Before real-capital Strategy promotion, explicitly adjudicate:

```text
CONCURRENT_OPPORTUNITY_RATE
CORRELATED_CLUSTER_CONCURRENCY
CAPITAL_RISK_BUDGET_CONTENTION
POSITION_NOTIONAL_LIMIT_INTERACTION
OPPORTUNITY_SELECTION_WHEN_CAPACITY_FULL
PORTFOLIO_LEVEL_AFTER_COST_EXPECTANCY_OR_CLAIM_SCOPE
```

A positive marginal Thesis expectancy is not, by itself, proof of portfolio/account deployability. Either validate the actual concurrency/capital-allocation policy or narrow the claim to marginal Thesis edge until that policy is validated.

This is a PRE-E8 gate, not an E4 portfolio-optimizer project.

## 8. Product stage placement

Canonical source: #174 comment `5664411089` and the current Product freeze.

The accepted staged route is:

```text
E4-A = minimum runnable data-first Shadow / semantic capture foundation
E4-B = formal technical + validation hardening
E6   = real zero-write Human approval product
```

E4-A/E4-B require semantic representability and truthful evidence for approval-relevant identities/states but do not require the operator web/UI runtime.

Preserve where applicable:

```text
environment/stage identity
market / venue-expression / point-in-time universe identity
Strategy / Policy / Parameter / Derivation / execution-model identity
Opportunity / Thesis / Eligibility / ARMED / Activation / package identity
lifecycle timestamps
approval_timing_mode
expiry / supersession
data-health / continuity / NOT_EVALUABLE reasons
OBSERVED / MODELLED / SIMULATED / NOT_AVAILABLE / NOT_APPLICABLE provenance
guard identity/result/reasons or deterministic replay inputs
NO_SUBMIT lifecycle
execution_model_limited
point-in-time executable-state checkpoints
```

Do not fabricate observed Human approval in E4/E5.

Product implementation deferred to E6 includes the actual APPROVE/REJECT workflow, operator web runtime, mobile/responsive UI, review forms, current-vs-proposal display, browser approval/session/security surface and observed Human approval interaction.

## 9. Current next-stage use and evidence clocks

The common Nautilus E4 foundation is merged and may be reused. This does not collapse independent Strategy lanes into one promotion clock.

For the ordinary VNext lane:

```text
accepted Strategy/Data/Validation publication
-> Strategy-specific E4-B / G4-equivalent calibration + hardening
-> Independent Validation
-> exact immutable refreeze
-> PRE-E5 method freeze complete
-> open NEW untouched E5 segment
```

Any data inspected for material calibration/selection is development/selection evidence for the changed candidate. A confirmatory E5 clock starts only after the exact immutable version and method controls are frozen.

If multiple material Challengers are adaptively compared on one Forward selection set, that set is selection/development evidence for the chosen winner; the selected winner requires a new later immutable confirmatory Forward set under Repair-1 N2.

Explosive and Session Open research lanes may share common infrastructure/validation machinery but retain separate Strategy identities, calibration boundaries and Forward clocks.

## 10. Explicit out-of-scope boundaries

This publication does not import or modify:

```text
SESSION_OPEN_IMPULSE V0.1
HL_EXPLOSIVE_SHADOW_C1
EXPLOSIVE X1 / X2 / X3
BSC_SOLANA_NATIVE_EXECUTION
NAUTILUS_RC5_ADOPTION
PYPROJECT_OR_LOCKS
WORKFLOWS
APPLICATION_OR_TEST_CODE
PRODUCT_E6_UI_RUNTIME
PRIVATE_ACCOUNT_DATA
```

Those items remain governed by their own current authorities and gates.

## 11. Authority boundary

```text
NON_EXECUTABLE=YES
PRODUCTION_STRATEGY_CHANGE=NO
MARK_READY_AUTHORITY=NO
MERGE_AUTHORITY=NO
DEPLOYMENT_AUTHORITY=NO
RUNTIME_CLOUD_MUTATION_AUTHORITY=NO
CREDENTIAL_PRIVATE_API_AUTHORITY=NO
WALLET_SIGNING_AUTHORITY=NO
EXCHANGE_WRITE_ORDER_AUTHORITY=NO
TESTNET_MAINNET_AUTHORITY=NO
REAL_CAPITAL_AUTHORITY=NO
AUTONOMOUS_TRADING_AUTHORITY=NO
```

This addendum is a publication/consolidation layer only. Its purpose is to make the already accepted VNext Strategy/Data/Validation contract self-contained on current `main` while preserving exact historical source evidence and clear precedence.