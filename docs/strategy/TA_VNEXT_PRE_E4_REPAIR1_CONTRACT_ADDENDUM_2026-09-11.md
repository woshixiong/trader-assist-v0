# TA_VNEXT PRE-E4 Repair 1 Contract Addendum

Status: ACTIVE REPAIR CANDIDATE / NON-EXECUTABLE / PENDING INDEPENDENT DELTA RE-REVIEW
Date: 2026-09-11
Parent: Draft PR #168
Third-party review basis: independent `THIRD_PARTY_PRE_E4_REVIEW=REPAIR`

This addendum is a bounded causal/data-contract repair. It does not create a new Strategy family, Entry hypothesis, Exit family, data platform or execution authority.

## 0. Precedence and scope

Within PR #168, this addendum **overrides only conflicting clauses** in:

- `TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11.md`;
- `TA_VNEXT_ENGINEERING19_PRE_E4_HANDOFF_2026-09-11.md`;
- `TA_VNEXT_VALIDATION_BACKTEST_SHADOW_AND_PROMOTION_STANDARD_V1_2026-09-11.md`;
- `TA_VNEXT_OPEN_QUESTIONS_AND_HYPOTHESIS_LEDGER_V1_2026-09-11.md`.

All non-conflicting clauses remain unchanged.

No Engineering implementation may rely on a conflicting older sentence after this addendum. If an ambiguity remains between this addendum and an older clause, this addendum controls for PRE-E4 review purposes until the files are later consolidated after independent acceptance.

```text
REPAIR_SCOPE=BOUNDED_CONTRACT_CLOSURE
NEW_SETUP=NO
NEW_ENTRY_FAMILY=NO
NEW_EXIT_FAMILY=NO
FULL_L2_FIRST_STAGE_EXPANSION=NO
ML_EXPANSION=NO
CUSTOM_MARKET_DATA_PLATFORM=NO
E4_WRITER_DISPATCH=NO
ENGINEERING19_HANDOFF_ALLOWED=NO_PENDING_DELTA_REVIEW
MARK_READY=NO
MERGE=NO
EXCHANGE_WRITE=NO
REAL_CAPITAL_AUTHORITY=NO
```

## 1. Repair R1 — BBO freshness is state validity, not quote-change age

### 1.1 Problem closed

Hyperliquid `WsBbo` is change-driven: a new BBO message is sent only when the BBO changes on a block. Therefore:

```text
NO_NEW_BBO_CHANGE_EVENT_FOR_2S
!=
BBO_STATE_STALE
```

The prior C1 rule `BBO age <=2s or BLOCKED/NOT_EVALUABLE` is superseded as a hard validity rule.

### 1.2 Required BBO evidence fields

Retain or deterministically derive:

```text
bbo_bid_px
bbo_bid_size
bbo_ask_px
bbo_ask_size
bbo_provider_event_ts
bbo_adapter_ts_init
bbo_true_receive_ts_if_observable
bbo_admission_ts
bbo_last_change_ts
bbo_event_age_ms                 # diagnostic only
bbo_stream_health
bbo_continuity_epoch
bbo_snapshot_or_state_validated_ts
bbo_gap_or_reconnect_state
```

`bbo_event_age_ms` is a diagnostic describing time since the last value-changing event. It is **not** by itself a stale-data gate.

### 1.3 C1 BBO validity rule

A BBO-dependent new-risk decision is evaluable only when:

```text
BBO_STATE_VALID=YES
AND BBO_STREAM_HEALTH=HEALTHY
AND BBO_CONTINUITY_AMBIGUITY=NO
AND REQUIRED_INSTRUMENT_IDENTITY_VALID=YES
```

A previously admitted BBO remains the current BBO while the provider subscription is healthy and continuity is known, even when no BBO change event has arrived recently.

`BLOCKED/NOT_EVALUABLE` is required when continuity is not defensible, including an unresolved disconnect, reconnect gap, subscription ambiguity, instrument-state conflict or missing current state validation.

### 1.4 Reconnect / promotion behavior

At Actionable promotion and after reconnect, use accepted provider-native / Nautilus subscription, snapshot/state and reconnect capability to establish current BBO state and continuity.

Do not create a second project-owned generic market-data/reconnect platform.

After a reconnect with unresolved continuity, historical decisions are not rewritten. The affected candidate remains `GAPPED/NOT_EVALUABLE` for the ambiguous interval and may resume only after current state is re-established.

### 1.5 Status of the old `2s` number

The old `<=2s` BBO event-age threshold is removed as a validity gate.

If retained at all, `2s` may appear only as a diagnostic/reporting threshold until a later immutable Strategy/Data version explicitly promotes an age-based feature with evidence. It must not silently filter quiet but healthy markets.

## 2. Repair R2 — close the 60-second pre-decision capture boundary

### 2.1 Problem closed

The prior files simultaneously required:

- broad Discovery on bars/context only;
- BBO/trades capture after Actionable promotion;
- at least 60s raw BBO/trades before the first timing-sensitive decision;
- EA1/EA2 not to wait for a 60s microstructure warmup.

Those requirements were not jointly satisfiable for a newly promoted market.

### 2.2 Bounded precursor prebuffer

Use a bounded rolling ephemeral BBO/TradeTick prebuffer for markets that enter the existing near-Actionable / WATCH precursor set.

Conceptual topology:

```text
DISCOVERY_ONLY
  -> bars/context only

NEAR_ACTIONABLE_OR_WATCH_PRECURSOR
  -> subscribe/capture BBO + TradeTick into bounded rolling ephemeral prebuffer

ACTIONABLE_OR_THESIS_ACTIVE
  -> flush available prebuffer into durable Opportunity evidence
  -> continue durable raw BBO + TradeTick capture through lifecycle
```

The precursor hook must reuse an existing Scanner/Strategy pre-Actionable state such as WATCH / near-Setup / breakout-near-level semantics. It must not introduce a new directional rule.

### 2.3 Prebuffer requirements

```text
TARGET_PREBUFFER_LENGTH>=60s
PREBUFFER_STORAGE=EPHEMERAL_BOUNDED_BY_DEFAULT
DURABLE_FLUSH_ON_ACTIONABLE_OR_OPPORTUNITY=YES
WHOLE_DISCOVERY_UNIVERSE_DURABLE_TICK_STORAGE=NO
```

The implementation should use the cheapest accepted provider-native/Nautilus route that preserves the evidence contract.

### 2.4 Incomplete prehistory semantics

If a market reaches its first timing-sensitive decision before 60s of valid prebuffer exists:

```text
PRE_DECISION_WINDOW_COMPLETE=NO
EVIDENCE_STATE=PRE_DECISION_WINDOW_INCOMPLETE
```

Do not fabricate or backfill the missing interval after the outcome is known.

This incompleteness does **not** delay or change EA1/EA2 Strategy semantics when their own required causal inputs are present. EA1/EA2 may still be evaluated, but analyses requiring a full 60s microstructure prehistory must treat that observation as incomplete.

EA3 remains stricter:

```text
EA3_REQUIRED_HEALTHY_MICROSTRUCTURE_WARMUP=60s
EA3_IF_WARMUP_INCOMPLETE=NOT_EVALUABLE
NO_SILENT_EA3_TO_EA1_FALLBACK=YES
```

### 2.5 Durable retention after promotion

Once Actionable/Opportunity/Thesis exists, retain raw admitted BBO/trades:

- all available flushed prebuffer;
- through the full active Opportunity/Thesis/Attempt/Winner lifecycle;
- at least 30m after terminal Thesis state;
- low-cost bars/context at least 6h after terminal state.

WAIT/PASS Thesis paths receive the same durable lifecycle/tail treatment once an Opportunity/Thesis exists.

## 3. Repair R3 — fill reference is bound to order-active causal market state

### 3.1 Timestamp chain

For every hypothetical order retain:

```text
market_event_ts
adapter_ts_init
true_receive_ts_if_observable
admission_ts
decision_ts
order_submit_intent_ts
hypothetical_order_active_ts
fill_market_state_ts
hypothetical_fill_ts
execution_model_version
latency_scenario_id
book_state_id_or_equivalent_provenance
```

### 3.2 Normative marketable-fill rule

For a marketable hypothetical order:

```text
MARKETABLE_FILL_REFERENCE
=
FIRST_ELIGIBLE_CAUSALLY_ADMITTED_EXECUTABLE_MARKET_STATE
AT_OR_AFTER
hypothetical_order_active_ts
```

The fill model must never use a decision-time BBO merely because that BBO was visible when Strategy decided, unless that same BBO is still the current valid executable state when the order becomes active.

Baseline side mapping remains:

```text
Long Entry  -> executable Ask side
Short Entry -> executable Bid side
Long Exit   -> executable Bid side
Short Exit  -> executable Ask side
```

### 3.3 Zero-latency control and same-timestamp ordering

`0ms` is a prespecified control scenario, not a claim of production latency.

For Nautilus-backed replay, equal-timestamp semantics must be deterministic and aligned with the accepted engine behavior:

```text
incoming market data updates simulated market state
-> Strategy callback observes that admitted state
-> newly due zero-latency order command settles in that same event/timestamp cycle
```

The exact ordering identity must be bound to the execution-model/runtime version.

### 3.4 Non-zero latency

When a versioned LatencyModel / diagnostic latency scenario produces:

```text
hypothetical_order_active_ts > decision_ts
```

the order is not executable before its active time. It settles only when the accepted engine reaches an eligible venue/market-state settlement point at or after that time.

Never fill a latency-delayed order against a stale earlier quote solely to preserve the original Strategy decision price.

### 3.5 Size / depth

L1 approximation is allowed only when the intended hypothetical size is defensible against current top-of-book capacity.

If size exceeds credible L1 capacity:

```text
TOP10_OR_L2_SIZE_AWARE_EXECUTION_AVAILABLE
-> use versioned size-aware VWAP / matching model

otherwise
-> EXECUTION_MODEL_LIMITED
-> affected size-dependent performance claim cannot promote
```

This condition does not make full L2 a universal first-E4 requirement.

### 3.6 Passive maker orders

Maker/passive replay remains a separate challenger. Touch alone is not a guaranteed fill without defensible queue evidence. Non-fill, partial-fill, adverse-selection and missed-move outcomes remain mandatory.

## 4. Repair R4 — normalize U21 / U23 / U25 to exact governance dispositions

The prior mixed phrasing is superseded by the following decomposed frontier items.

### U21A — intended size is within defensible L1 capacity

```text
DECISION_CRITICALITY=MATERIAL_OPTIMIZATION
RESEARCH_INVESTMENT_DISPOSITION=PROCEED_WITH_CURRENT_BEST_AND_DEFER
CURRENT_ROUTE=L1_EXECUTION_BASELINE
REOPEN_TRIGGER=OBSERVED_OR_PLANNED_SIZE_EXCEEDS_DEFENSIBLE_L1_CAPACITY_OR_L1_MODEL_ERROR_BECOMES_MATERIAL
```

### U21B — intended size exceeds defensible L1 capacity for the affected claim

```text
DECISION_CRITICALITY=HARD_BLOCKER_FOR_THAT_SIZE_DEPENDENT_EXECUTION_CLAIM
RESEARCH_INVESTMENT_DISPOSITION=ACQUIRE_BEFORE_NEXT_GATE
CHEAPEST_DECISIVE_EVIDENCE=TOP10_OR_L2_SIZE_AWARE_EXECUTION_EVIDENCE
SCOPE=ONLY_AFFECTED_MARKETS/SIZES/CLAIMS
```

### U23A — E4 causal timing/provenance capture

```text
DECISION_CRITICALITY=HARD_BLOCKER_FOR_CAUSAL_EXECUTION_REPLAY
RESEARCH_INVESTMENT_DISPOSITION=ACQUIRE_BEFORE_NEXT_GATE
CHEAPEST_DECISIVE_EVIDENCE=EVENT/INIT/ADMISSION/DECISION/ORDER_ACTIVE_TIMESTAMPS_AND_LATENCY_SCENARIO_ID
```

### U23B — actual production execution-latency calibration

```text
DECISION_CRITICALITY=HARD_BLOCKER_FOR_FUTURE_REAL_EXECUTION_MODEL_ACCEPTANCE_NOT_FOR_E4_SHADOW
RESEARCH_INVESTMENT_DISPOSITION=PROCEED_WITH_CURRENT_BEST_AND_DEFER
NEXT_STAGE=SEPARATELY_AUTHORIZED_TESTNET/TINY_MAINNET_EXECUTION_QUALIFICATION
NO_PRIVATE_API_OR_EXCHANGE_WRITE_AUTHORITY_CREATED=YES
```

### U25 — right-tail concentration evidence before real-capital Strategy promotion

```text
DECISION_CRITICALITY=HARD_BLOCKER_FOR_REAL_CAPITAL_STRATEGY_PROMOTION_CLAIM
RESEARCH_INVESTMENT_DISPOSITION=ACQUIRE_BEFORE_NEXT_GATE
NEXT_GATE=REAL_CAPITAL_STRATEGY_PROMOTION
CHEAPEST_DECISIVE_EVIDENCE=E5_FORWARD_TOP1_TOP3_TOP5_CONTRIBUTION_AND_LEAVE_TOP_WINNER_SENSITIVITY
CURRENT_E4_BLOCKER=NO
```

No additional data platform is authorized by these dispositions.

## 5. Non-blocking repair N1 — timestamp terminology

The combined phrase `local_receive_or_adapter_init_timestamp` is superseded.

Use separate semantics:

```text
provider_event_ts
adapter_ts_init
true_local_receive_ts_if_observable
admission_ts
decision_ts
hypothetical_order_active_ts
```

Nautilus `ts_init` means local object initialization time. It must not be represented as guaranteed network receive time.

`ts_init - ts_event` may be reported as observed clock-to-clock delay only when the relevant clocks are sufficiently synchronized and the provenance supports that interpretation. Otherwise it is not a valid measured network-latency claim.

## 6. Non-blocking repair N2 — multiple E5 Challenger selection

The ordinary one-candidate Forward confidence gate must not be applied to a winner selected adaptively from many Challengers on the same Forward sample as if no model selection occurred.

### 6.1 Simple default rule

If multiple material Challengers are compared on one fresh Forward selection set and the best one is chosen after inspecting those results:

```text
THAT_FORWARD_SET_ROLE=SELECTION/DEVELOPMENT_FOR_THE_CHOSEN_WINNER
REAL_CAPITAL_CONFIRMATORY_CLAIM_FROM_SAME_SET=NO
SELECTED_WINNER_REQUIRES=NEW_LATER_IMMUTABLE_CONFIRMATORY_FORWARD_SET
```

The selected candidate/version must be frozen before the new confirmatory set starts.

### 6.2 Diagnostics

White-Reality-Check / PBO / Deflated-Sharpe-style diagnostics may be used when trial/sample structure makes them defensible, but they do not eliminate the requirement for a later confirmatory Forward set after adaptive multi-candidate selection under the default route.

This rule is intentionally simpler and safer than introducing a large post-selection statistical framework at C1.

## 7. Updated status pending delta re-review

The third-party review accepted the overall Strategy/Data/Validation architecture but found the repaired clauses material enough to block Engineering implementation until re-reviewed.

Therefore current status after applying this addendum is:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
REPAIR_STAGE=NORMAL_REPAIR
STRATEGY_DATA_VALIDATION_CLOSED_LOOP=REPAIR_APPLIED_PENDING_DELTA_REVIEW
STRATEGY_PRE_E4_HANDOFF=REPAIR_APPLIED_PENDING_DELTA_REVIEW
ENGINEERING19_HANDOFF_ALLOWED=NO_PENDING_DELTA_REVIEW
E4_HARD_HOLD=ACTIVE
E4_WRITER_DISPATCH=NO
MARK_READY=NO
MERGE=NO
DEPLOYMENT=NO
PRIVATE_API=NO
EXCHANGE_WRITE=NO
REAL_CAPITAL_AUTHORITY=NO
AUTONOMOUS_TRADING=NO
```

If independent delta re-review passes this exact repair, Strategy Control may restore the handoff disposition to `READY_FOR_ENGINEERING19_ACCEPTANCE` without reopening broad Strategy research.

## 8. External primary/mature evidence anchors for this repair

- Hyperliquid official WebSocket subscription docs: `WsBbo` updates are sent only when BBO changes on a block; BBO event age is therefore not a valid standalone stream-liveness criterion.
- Hyperliquid official WebSocket docs: clients must handle disconnect/reconnect; connection continuity and state recovery are separate from quote-value changes.
- NautilusTrader official Data docs: `ts_event` and `ts_init` have distinct semantics; `ts_init` is initialization time and does not universally mean network receive time.
- NautilusTrader official Backtest Execution Flow: market state is processed before Strategy callbacks; newly due same-timestamp commands settle after callbacks; LatencyModel delays commands until their arrival/settlement time.

These sources validate causal/data mechanics only. They do not establish trading alpha or Strategy thresholds.
