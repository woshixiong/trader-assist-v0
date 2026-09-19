# Trader Assist / Trade OS — Mandatory Engineering Preflight and Convergence Checklist V1

**Status:** ACTIVE CHECKLIST CANDIDATE  
**Effective date:** 2026-08-17  
**Last material amendment candidate:** 2026-09-17  
**Normative owner:** `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`

This file is an **execution checklist and record schema**, not a second engineering constitution. If this checklist and Unified V2 conflict, Unified V2 governs.

Use the full checklist for every MATERIAL engineering task before Writer dispatch. Mechanical exact-state work may use a shortened form; if it exposes a material decision, reclassify immediately.

No material Writer dispatch without:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

Engineering Control completes this checklist from live GitHub and canonical authority. A downstream Writer receives the resulting attestation in its frozen Task Packet and **does not reread this entire checklist or the entire governance corpus by default**.

Record the execution surface and bound Writer attestation at control time:

```text
EXECUTION_SURFACE_CLASS=
  GITHUB_DETERMINISTIC
  | ENGINEERING_CONTROL_DIRECT
  | NON_CODEX_MODEL_WRITER
  | CODEX_SEMANTIC_WRITER
  | LOCAL_DETERMINISTIC
  | TARGET_HOST
MODEL_WRITER_REQUIRED=YES|NO
CODEX_SELECTED=YES|NO
TASK_PACKET_HASH=
GOVERNANCE_ATTESTATION_MAIN_OR_BASE_SHA=
AUTHORITY_PROVENANCE_LOCATORS=
WRITER_CONTEXT_MODE=COMPACT_PACKET|EXPLICIT_EXCEPTION
FULL_GOVERNANCE_CORPUS_REQUIRED=NO|YES

ACTIVE_STAGE_CHECKPOINT_REF=
WINDOW_SCOPE=
ROTATION_TRIGGER=
CONTEXT_COMPLETENESS_GATE=PASS|FAIL
SUCCESSOR_WINDOW_REQUIRED=YES|NO
```

The Task Packet must contain the normalized authority assertions needed by the Writer; provenance locators bind those assertions to canonical GitHub/files. A stale main/base binding, Task Packet hash mismatch or material authority drift invalidates the attestation and returns control to Engineering Control.

For Engineering Control itself, the active checkpoint is the durable starting state. Before material work, the context-completeness gate verifies current stage/identity, active authority, accepted/superseded decisions, unresolved blockers, scope, acceptance criteria, next action and provenance. A missing material field triggers targeted canonical retrieval; unresolved uncertainty means `CONTEXT_COMPLETENESS_GATE=FAIL`.

`FULL_GOVERNANCE_CORPUS_REQUIRED=YES` is exceptional and requires a governance-maintenance task whose object is the relevant corpus or a concrete unresolved governance conflict. Quota availability alone never selects Codex.

---

## 1. Required live identity

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS|FAIL
ENGINEERING_PREFLIGHT_GATE=PASS|FAIL
ROLE=
TASK_CLASS=MATERIAL|MECHANICAL
LIVE_REPO=
LIVE_MAIN_SHA=
ACTIVE_ISSUE_OR_PR=
EXACT_START_HEAD=
CURRENT_AUTHORITY_SOURCES=
APPLICABLE_SPECIALIZED_CONTRACTS=
USER_AUTHORITY_REQUIRED_NOW=YES|NO
```

Fresh GitHub/code/exact artifacts control over stale chat or old prompt state.

### 1A. Human-executed command pre-delivery hard gate

Whenever the bounded task will deliver a nontrivial human-executed Terminal/shell/launcher command, the specialized procedure in:

- `governance/GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md`

is applicable **before the command is shown to the user**.

Record at minimum:

```text
GENERATED_COMMAND_RELIABILITY_GATE=PASS|FAIL|NOT_APPLICABLE
KNOWN_COMMAND_INCIDENT_CLASSES_REVIEWED=YES|NO|NOT_APPLICABLE
KNOWN_INCIDENT_NONREGRESSION_GATE=PASS|FAIL|NOT_APPLICABLE
SCRIPT_TRANSPORT=FILE_BACKED|SHORT_INLINE|HEREDOC_EXCEPTION|NOT_APPLICABLE
CLI_INVOCATION_CONTRACT_PROOF=PASS|FAIL|NOT_APPLICABLE
SAFE_STOP_GATES_BOUND_TO_REAL_INVARIANTS=YES|NO|NOT_APPLICABLE
SIDE_EFFECT_FREE_PREFLIGHT_COMPLETE_BEFORE_ONE_SHOT=YES|NO|NOT_APPLICABLE
COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION|NOT_APPLICABLE
```

Hard enforcement:

```text
ENGINEERING_PREFLIGHT_GATE=PASS
!=
GENERATED_COMMAND_RELIABILITY_GATE=PASS

NONTRIVIAL_HUMAN_EXECUTED_COMMAND_APPLICABLE
AND GENERATED_COMMAND_RELIABILITY_GATE != PASS
=> COMMAND_DELIVERY=PROHIBITED

NONTRIVIAL_HUMAN_EXECUTED_COMMAND_APPLICABLE
AND KNOWN_INCIDENT_NONREGRESSION_GATE != PASS
=> COMMAND_DELIVERY=PROHIBITED

COMMAND_IS_WRITER_LAUNCH_PATH
AND COMMAND_DELIVERY=PROHIBITED
=> WRITER_DISPATCH=PROHIBITED
```

A command may not recreate a known avoidable incident class merely by changing wrapper language, encoding, transport or exact text. Fresh authoritative GitHub/control-plane identity must not be converted into redundant lower-reliability local proof unless the additional proof protects a distinct real invariant.

For Writer launch paths also record:

```text
SEMANTIC_READINESS=PASS|FAIL
SEMANTIC_START_PREREQUISITES=
PUBLICATION_READINESS=PASS|FAIL|NOT_APPLICABLE_YET
PUBLICATION_PREREQUISITES=
PRE_SEMANTIC_GATE_NECESSITY_PROOF=PASS|FAIL
LAUNCH_ARTIFACT_DELIVERY_CONFIRMED=YES|NO|NOT_APPLICABLE
```

A publication-only prerequisite may not set `SEMANTIC_READINESS=FAIL`. GitHub auth/API/push/PR/result-egress checks belong after the semantic checkpoint unless they are truly required to acquire/verify the semantic source or protect another distinct pre-mutation invariant. A launcher artifact may not be represented as executable by the user until its actual delivery/availability on the operator surface is confirmed.

After any command failure, complete the Generated Command failure classification/checkpoint fields and repair-stage disposition before another command is issued. A pre-semantic command failure does not consume the application semantic repair budget, but it does consume the applicable command-repair progression. The second avoidable defect in one launcher family terminates that family and prohibits another incremental correction.

### 1B. User-local Git publication transport hard gate

Whenever the bounded task will deliver or execute a user-local Git publication command for this repository, also load:

- `governance/GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md`

before the publication command is shown or executed. Record:

```text
LOCAL_GIT_TRANSPORT_APPLICABLE=YES|NO
LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED=YES|NO|NOT_APPLICABLE
LOCAL_GIT_TRANSPORT_GATE=PASS|FAIL|NOT_APPLICABLE
LOCAL_TRANSPORT_HEALTH_PREFLIGHT=PASS|FAIL|NOT_APPLICABLE
KNOWN_TRANSPORT_INCIDENT_NONREGRESSION=PASS|FAIL|NOT_APPLICABLE
AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED=YES|NO|NOT_APPLICABLE
SEMANTIC_CHECKPOINT_ALREADY_COMPLETE=YES|NO|NOT_APPLICABLE
```

For an applicable user-local publication command, `LOCAL_GIT_TRANSPORT_GATE=PASS` is derived only when every required transport input is resolved:

```text
USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED = YES
AND LOCAL_TRANSPORT_HEALTH_PREFLIGHT = PASS
AND KNOWN_TRANSPORT_INCIDENT_NONREGRESSION = PASS
AND AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED = YES
=> LOCAL_GIT_TRANSPORT_GATE=PASS

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_TRANSPORT_HEALTH_PREFLIGHT != PASS
=> LOCAL_GIT_TRANSPORT_GATE=FAIL

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED != YES
=> LOCAL_GIT_TRANSPORT_GATE=FAIL

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND KNOWN_TRANSPORT_INCIDENT_NONREGRESSION != PASS
=> LOCAL_GIT_TRANSPORT_GATE=FAIL

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED != YES
=> LOCAL_GIT_TRANSPORT_GATE=FAIL
```

`AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED=YES` means the routing check has been resolved; it does not assert that a remote write surface exists. If an equal-or-higher-fidelity authoritative remote publication surface is available, apply Unified V2's remote-execution preference before selecting another user-local publication attempt. A proven-unhealthy local route cannot receive `LOCAL_GIT_TRANSPORT_GATE=PASS` merely because HTTPS remains the project default.

Hard enforcement:

```text
USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED != YES
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_GATE != PASS
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_TRANSPORT_HEALTH_PREFLIGHT != PASS
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED != YES
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND KNOWN_TRANSPORT_INCIDENT_NONREGRESSION != PASS
=> COMMAND_DELIVERY=PROHIBITED
```

If an exact semantic checkpoint already exists and the local GitHub TLS/API route is proven unreliable, do not rerun the semantic action or loop local publication retries. Preserve the checkpoint and follow the specialized procedure's authoritative remote/offline-artifact fallback ladder. A previously successful local read/authentication probe is not by itself proof that the later mutation path remains healthy.

### 1C. Engineering-window rotation hard gate

At each material Engineering Control stage entry:

```text
WINDOW_SCOPE=REQUIRED
ROTATION_TRIGGER=REQUIRED
ACTIVE_STAGE_CHECKPOINT_REF=REQUIRED
```

If a rotation trigger fires, the current window must freeze and verify the durable GitHub checkpoint and produce the successor-window prompt before another material stage begins. The successor window must read the checkpoint and fresh live identity; it must not rely on the predecessor transcript as canonical state.

```text
ROTATION_TRIGGER_FIRED=YES
AND CHECKPOINT_VERIFIED != YES
=> NEXT_MATERIAL_STAGE=PROHIBITED

ROTATION_TRIGGER_FIRED=YES
AND SUCCESSOR_PROMPT_READY != YES
=> NEXT_MATERIAL_STAGE=PROHIBITED
```

---

## 2. Research / route decision

For material direction-setting work:

```text
INDEPENDENT_ANALYSIS_DONE=YES|NO
PRE_RESEARCH_POSITION=
EXTERNAL_RESEARCH_DONE=YES|NO|NOT_REQUIRED
PRIMARY_OR_MATURE_EVIDENCE=
DISCONFIRMING_EVIDENCE_CHECKED=YES|NO|NOT_REQUIRED
SYNTHESIS_DONE=YES|NO
WHAT_EVIDENCE_CONFIRMS=
WHAT_EVIDENCE_MODIFIES=
WHAT_EVIDENCE_REJECTS=
RESIDUAL_UNCERTAINTY=
SELECTED_ROUTE=
REJECTED_ROUTES=
PRE_WRITER_GO_NO_GO_EXPERIMENT=
```

If the task is not direction-setting, use `NOT_REQUIRED` rather than manufacturing research.

When a material decision selects/rejects/composes/customizes/adopts an external mature solution, or proposes project-owned commodity infrastructure, also load and complete the applicable record from:

- `governance/EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md`

### 2A. Research frontier / investment / complexity gate

Complete this block whenever current evidence is exhausted and the next proposed step requires material new data, data retention, provider/infrastructure work, a larger experiment, further adaptive search on substantially the same historical evidence, or new independent OOS/Forward evidence.

```text
RESEARCH_FRONTIER_REACHED=YES|NO|NOT_APPLICABLE
CURRENT_BEST_CANDIDATE=
CURRENT_CANDIDATE_READINESS=
MISSING_EVIDENCE_OR_DATA=
DECISION_THAT_NEW_INFORMATION_COULD_CHANGE=
DECISION_CRITICALITY=HARD_BLOCKER|MATERIAL_OPTIMIZATION|OPTIONAL|NOT_APPLICABLE
EXPECTED_DECISION_IMPACT=LOW|MEDIUM|HIGH|BOUNDED_ESTIMATE|NOT_APPLICABLE
EXPECTED_UNCERTAINTY_REDUCTION=LOW|MEDIUM|HIGH|BOUNDED_ESTIMATE|NOT_APPLICABLE
TOTAL_RESEARCH_BURDEN=
DIRECT_DATA_OR_PROVIDER_COST=
DELAY_OPPORTUNITY_COST=
COMPLEXITY_OVERFIT_COST=
DATA_PERISHABILITY_OR_RECONSTRUCTABILITY=
NEXT_STAGE_REVERSIBILITY_AND_RISK=
FORWARD_OR_INDEPENDENT_EVIDENCE_VALUE=
FRONTIER_DECOMPOSITION=PASS|NOT_REQUIRED|FAIL|NOT_APPLICABLE
TRIAL_AND_ADAPTIVITY_LEDGER_STATUS=PASS|LEGACY_INCOMPLETE_CONSERVATIVE|FAIL|NOT_APPLICABLE
SIMPLE_BASELINE_AND_INCREMENTAL_VALUE_TEST=PASS|FAIL|NOT_APPLICABLE
RESEARCH_INVESTMENT_DISPOSITION=ACQUIRE_BEFORE_NEXT_GATE|CAPTURE_CHEAP_OPTIONALITY|PROCEED_WITH_CURRENT_BEST_AND_DEFER|PARK_OR_REJECT|NOT_APPLICABLE
REOPEN_TRIGGER_IF_DEFERRED_OR_PARKED=
```

Hard rules:

```text
DATA_BLOCKED_FRONTIER != AUTO_DATA_ENGINEERING

MULTI_DECISION_FRONTIER
=> FRONTIER_DECOMPOSITION=PASS
=> EACH_MATERIAL_FRONTIER_ITEM_HAS_EXACTLY_ONE_DISPOSITION=YES
=> OPTIONAL_ITEM_MUST_NOT_FORCE_ACQUISITION_OF_HARD_BLOCKER_SCOPE=YES
=> HARD_BLOCKER_MUST_NOT_BE_HIDDEN_INSIDE_DEFERRED_OR_OPTIONAL_ITEM=YES

HARD_BLOCKER
=> PROCEED_WITH_CURRENT_BEST_AND_DEFER=PROHIBITED_FOR_THE_BLOCKED_CLAIM
=> PARK_OR_REJECT=PROHIBITED_UNLESS_THE_BLOCKED_CLAIM/ROUTE_ITSELF_IS_ABANDONED

ACQUIRE_BEFORE_NEXT_GATE
=> NEW_RESEARCH_OR_DATA_SCOPE_MUST_MAP_TO_EXACT_UNRESOLVED_DECISION
=> CHEAPEST_DECISIVE_EVIDENCE_ROUTE_REQUIRED

CAPTURE_CHEAP_OPTIONALITY
=> CURRENT_POLICY_USE_FROM_CAPTURE=NO
=> CAPTURED_DATA_NONAUTHORITATIVE_BY_DEFAULT
=> MATERIAL_INFRASTRUCTURE_EXPANSION_PROHIBITED_UNDER_THIS_DISPOSITION

PROCEED_WITH_CURRENT_BEST_AND_DEFER
=> CURRENT_CANDIDATE_MUST_PASS_APPLICABLE_NEXT_STAGE_SAFETY_CORRECTNESS_AUTHORITY_GATES
=> KNOWN_UNKNOWNS_AND_DEFERRED_HYPOTHESES_RECORDED=YES

PARK_OR_REJECT
=> ZOMBIE_TODO_WITHOUT_REOPEN_TRIGGER_OR_EXPLICIT_REJECTION=PROHIBITED

TRIAL_AND_ADAPTIVITY_LEDGER_STATUS=LEGACY_INCOMPLETE_CONSERVATIVE
=> EXACT_LEGACY_TRIAL_COUNT_MUST_NOT_BE_FABRICATED
=> BEST_KNOWN_LOWER_BOUND_OR_UNKNOWN_LEGACY_INCOMPLETE_REQUIRED=YES
=> HISTORICAL_AND_REPEATED_OOS_INDEPENDENCE_STRENGTH_MUST_BE_DOWNGRADED=YES
=> LEGACY_INCOMPLETENESS_ALONE_IS_NOT_FORWARD_SHADOW_BLOCK=YES
=> PROSPECTIVE_MATERIAL_VARIANT_LOGGING_REQUIRED=YES

NEW_UNLOGGED_MATERIAL_STRATEGY_VARIANT
=> TRIAL_AND_ADAPTIVITY_LEDGER_STATUS=FAIL
=> AFFECTED_ADAPTIVITY_OR_INDEPENDENCE_CLAIM=FAIL
```

For trading Strategy work where material discretionary economic complexity is proposed, additionally require:

```text
PRESPECIFIED_CAUSAL_HYPOTHESIS=YES|NO|NOT_APPLICABLE
SIMPLE_BASELINE_DEFINED=YES|NO|NOT_APPLICABLE
MATERIAL_INCREMENTAL_OOS_OR_FORWARD_VALUE_REQUIRED_FOR_PROMOTION=YES|NO|NOT_APPLICABLE
MATERIAL_VARIANT_COUNT_OR_SEARCH_HISTORY_RECORDED=YES|LEGACY_LOWER_BOUND_OR_UNKNOWN|NO|NOT_APPLICABLE
FORWARD_VERSION_FREEZE_PLAN=PASS|FAIL|NOT_APPLICABLE
```

Complexity independently required for safety, correctness, authority or causal validity remains governed by those hard gates and does not require an economic-uplift experiment merely to exist.

Do not require fake numerical precision. Qualitative evidence is acceptable; unresolved applicable fields are not.

---

## 3. Architecture / authority / continuity

```text
ROOT_CAUSE_LEVEL=LOCAL|CROSS_LAYER|ARCHITECTURAL|UNKNOWN
AFFECTED_AUTHORITIES=
FROZEN_INVARIANTS=
SECOND_AUTHORITY_CACHE_QUEUE_RISK=PASS|FAIL|NOT_APPLICABLE
CROSS_LAYER_CONTRACT_CLOSURE_PLAN=
ADMITTED_INPUT_TOTALITY_PLAN=
RESTART_REPLAY_IDEMPOTENCY_PLAN=
TIME_FRESHNESS_SUPERSESSION_PLAN=

CURRENT_BOUNDED_NEED=
NEXT_EXPECTED_STAGE=
STABLE_AUTHORITIES=
STABLE_INTERFACES=
REPLACEABLE_IMPLEMENTATION_SEAMS=
PERSISTED_REPRESENTATION_VERSIONING=
KNOWN_CHANGE_AMPLIFICATION_HOTSPOTS=
KNOWN_REWRITE_OR_LOCKIN_RISK=
OVERENGINEERING_CHECK=PASS|FAIL
```

If the route predictably forces a near-term rewrite of stable authority or interfaces, do not pass the gate merely because it is locally small.

---

## 4. Mature-solution / total-burden check

First classify the capability:

```text
CAPABILITY_CLASS=STRATEGY_DIFFERENTIATOR|COMMODITY_INFRASTRUCTURE|THIN_INTEGRATION
STRATEGY_DECISION_ENGINE_RESPONSIBILITY=
TRADING_INFRASTRUCTURE_ENGINE_RESPONSIBILITY=
```

For commodity capability or a reopened legacy custom responsibility:

```text
EXTERNAL_MATURE_SELECTION_RULE_LOADED=YES|NO|NOT_APPLICABLE
STAGE_0_NO_PRODUCT_CODE_AUDIT=PASS|FAIL|NOT_APPLICABLE
P0_REQUIREMENTS_FROZEN=YES|NO|NOT_APPLICABLE
EXISTING_PROJECT_CAPABILITY_CHECKED=YES|NO|NOT_APPLICABLE
PROVIDER_NATIVE_CHECKED=YES|NO|NOT_APPLICABLE
STANDARD_OFFICIAL_CHECKED=YES|NO|NOT_APPLICABLE
MATURE_EXTERNAL_FULL_FRAMEWORK_CHECKED=YES|NO|NOT_APPLICABLE
MATURE_EXTERNAL_MODULAR_COMPONENT_CHECKED=YES|NO|NOT_APPLICABLE
MATURE_COMPOSITION_CHECKED=YES|NO|NOT_APPLICABLE
THIN_ADAPTER_CHECKED=YES|NO|NOT_APPLICABLE
CANDIDATE_AUTHENTICITY_AND_IDENTITY_CHECKED=YES|NO|NOT_APPLICABLE
P0_HARD_GATE_MATRIX=PASS|FAIL|UNRESOLVED|NOT_APPLICABLE
EVIDENCE_CONFIDENCE_RECORDED=YES|NO|NOT_APPLICABLE
TOTAL_BURDEN_COMPARISON=PASS|FAIL|UNRESOLVED|NOT_APPLICABLE
DECISION_STABILITY_CHECK=PASS|LOW|NOT_APPLICABLE
STAGE_0_DISPOSITION=SELECT_MATURE_ROUTE|SELECT_MODULAR_COMPOSITION|ONE_BLOCKER_FEASIBILITY_SPIKE|UNRESOLVED_TRADEOFF|REJECT_CANDIDATE|NO_FITTING_MATURE_ROUTE|SAFE_STOP|NOT_APPLICABLE
ONE_AUTHORITATIVE_OWNER_PER_RESPONSIBILITY=PASS|FAIL|NOT_APPLICABLE
ONE_BLOCKER_TINY_SPIKE=PASS|FAIL|NOT_REQUIRED|NOT_APPLICABLE
TINY_SPIKE_NON_OVERRIDABLE_CONSTRAINTS=PASS|FAIL|NOT_APPLICABLE
TINY_SPIKE_BUDGET_OVERRIDE=NO|BOUNDED_WITH_RATIONALE|FAIL|NOT_APPLICABLE
TINY_SPIKE_OVERRIDE_GATE=PASS|FAIL|NOT_APPLICABLE
LEGACY_KEEP_CUSTOM_DECISION_EXPIRY_CHECK=PASS|FAIL|NOT_APPLICABLE
CUSTOM_COMMODITY_EXCEPTION_USER_AUTHORITY=YES|NO|NOT_APPLICABLE
```

Hard pre-dispatch consequences:

```text
FITTING_MATURE_SOLUTION_EXISTS
=> CUSTOM_FROM_SCRATCH_IMPLEMENTATION=PROHIBITED
=> SECOND_PROJECT_OWNED_IMPLEMENTATION=PROHIBITED

NO_FITTING_MATURE_ROUTE
AND CUSTOM_COMMODITY_IMPLEMENTATION_PROPOSED
AND CUSTOM_COMMODITY_EXCEPTION_USER_AUTHORITY != YES
=> ENGINEERING_PREFLIGHT_GATE=FAIL
=> WRITER_DISPATCH=PROHIBITED

DECISION_STABILITY_CHECK=LOW
=> STAGE_0_DISPOSITION=UNRESOLVED_TRADEOFF
=> SELECT_MATURE_ROUTE=PROHIBITED
=> SELECT_MODULAR_COMPOSITION=PROHIBITED
=> ADOPTION=PROHIBITED
=> PRODUCT_WRITER_DISPATCH=PROHIBITED
```

`DECISION_STABILITY_CHECK=LOW` is a resolved diagnostic result but a non-promotable route state. It may transition only to `ONE_BLOCKER_FEASIBILITY_SPIKE` when the specialized rule proves exactly one material P0 uncertainty remains and every applicable Tiny Spike eligibility and budget gate passes. It never authorizes product Writer dispatch.

For a Tiny Spike Writer dispatch, all applicable conditions must be resolved before `ENGINEERING_PREFLIGHT_GATE=PASS`:

```text
STAGE_0_DISPOSITION=ONE_BLOCKER_FEASIBILITY_SPIKE
ONE_BLOCKER_TINY_SPIKE=PASS
TINY_SPIKE_NON_OVERRIDABLE_CONSTRAINTS=PASS
TINY_SPIKE_BUDGET_OVERRIDE=NO|BOUNDED_WITH_RATIONALE
TINY_SPIKE_OVERRIDE_GATE=PASS|NOT_APPLICABLE
```

If `TINY_SPIKE_BUDGET_OVERRIDE=BOUNDED_WITH_RATIONALE`, then `TINY_SPIKE_OVERRIDE_GATE=PASS` is mandatory. If any non-overridable constraint fails, the override is `FAIL`, or a second material uncertainty/commodity authority appears:

```text
ENGINEERING_PREFLIGHT_GATE=FAIL
TINY_SPIKE_WRITER_DISPATCH=PROHIBITED
```

A fitting mature route blocks unnecessary custom commodity infrastructure. Sunk cost, existing code, migration inconvenience alone, a preference for no new dependency, launch proximity, architecture familiarity or belief that one more repair may work are not valid blockers.

`NO_NEW_DEPENDENCY` is not a simplicity proof. Total lifecycle engineering burden is the metric.

---

## 5. Scale / provider / freshness

```text
PROVIDER_SCALE_BUDGET=PASS|FAIL|NOT_APPLICABLE
REQUEST_WEIGHT_OR_RATE_BUDGET=
DATABASE_WORKLOAD_BUDGET=
REALISTIC_SCALE_TEST_PLAN=
FRESHNESS_OR_LATENCY_GATE=
RESOURCE_OR_SHUTDOWN_GATE=
```

Use `NOT_APPLICABLE` only when the change is genuinely scale-neutral.

---

## 6. Verification and validation-environment plan

```text
PRODUCTION_PATH_FIDELITY_PLAN=
STAGE_CLAIM_LADDER=
AUTHORITATIVE_PROOF_SURFACE_FOR_EACH_STAGE=
MINIMUM_REPRESENTATIVE_TOPOLOGY=
COMPLEXITY_ESCALATION_ORDER=
DETERMINISTIC_BRANCH_PROOF_PLAN=
REAL_EXTERNAL_BOUNDARY_PROOF_PLAN=
APPLICABLE_G0_TO_G12_GATES=
PROPERTY_BASED_TEST_PLAN=
STATEFUL_TEST_PLAN=
INCIDENT_TO_INVARIANT_PLAN=
REALISTIC_COMPOSITION_PLAN=

CANONICAL_VALIDATION_COMMANDS=
VALIDATION_PLATFORM_CLASS=PLATFORM_NEUTRAL|MACOS|LINUX|TARGET_HOST_SPECIFIC|OTHER|NOT_APPLICABLE
AUTHORITATIVE_VALIDATION_ENVIRONMENT=
KNOWN_ENVIRONMENT_MISMATCHES=
LOCAL_ENVIRONMENT_FIT=PASS|FAIL|NOT_APPLICABLE
FALLBACK_VALIDATION_SURFACE=
EXACT_RELEASE_VERIFICATION_PLAN=
EVIDENCE_CHECKPOINT_PLAN=
```

Platform-sensitive proof on a non-authoritative OS cannot make this gate PASS.

---

## 7. Writer / scope / attack matrix

```text
ONE_PRIMARY_WRITER=YES|NO
WRITER_SCOPE=
WRITE_ALLOWLIST=
PROHIBITED_SCOPE=
MUST_REMAIN_BEHAVIOR=
ATTACK_MATRIX_FROZEN=YES|NO
CANONICAL_TEST_LINT_TYPE_COMPILE_COMMANDS=
VALIDATION_ENVIRONMENT_FOR_EACH_GATE=
COMMIT_PUSH_AUTHORITY=
REVIEW_REQUIREMENT=
OUTPUT_CONTRACT=
REVIEW_RESULT_EGRESS_REQUIRED=YES|NO
REVIEW_RESULT_EGRESS_SURFACE=GITHUB_ISSUE_COMMENT|GITHUB_PR_COMMENT|EXACT_ARTIFACT_POINTER|OTHER_DIRECT_EXACT_SURFACE|NOT_APPLICABLE
REVIEW_RESULT_EGRESS_TARGET=
DIRECT_CONTROLLER_READABLE=YES|NO|NOT_APPLICABLE
USER_RELAY_REQUIRED=YES|NO|NOT_APPLICABLE
REVIEW_OUTPUT_CONTRACT_SATISFIABLE=YES|NO|NOT_APPLICABLE
REVIEW_RESULT_EGRESS_PERMISSION_COMPATIBLE=YES|NO|NOT_APPLICABLE
REVIEW_RESULT_EGRESS_GATE=PASS|FAIL|NOT_APPLICABLE
```

A write allowlist means `CHANGED_PATHS ⊆ ALLOWLIST` unless the semantic contract explicitly requires particular files to change.

The Task Packet must be complete before execution. Architecture-critical addenda require one regenerated replacement packet.

`REVIEW_RESULT_EGRESS_REQUIRED=YES` if and only if `REVIEW_REQUIREMENT` requires an authority-bearing independent review whose result is needed downstream. `REVIEW_RESULT_EGRESS_TARGET` is the exact destination or pointer sufficient for direct controller location. `DIRECT_CONTROLLER_READABLE=YES` only when no user transcription is required. When egress is required, `USER_RELAY_REQUIRED=NO` is mandatory. `REVIEW_OUTPUT_CONTRACT_SATISFIABLE=YES` only when completeness, terminal/chat restrictions and egress mechanics are mutually satisfiable. `REVIEW_RESULT_EGRESS_PERMISSION_COMPATIBLE=YES` means the selected permissions/mode suffice for the selected egress; do not overfit the egress to writeback.

Hard gate:

```text
REVIEW_RESULT_EGRESS_REQUIRED=YES
AND (
  REVIEW_RESULT_EGRESS_SURFACE=NOT_APPLICABLE
  OR REVIEW_RESULT_EGRESS_TARGET=EMPTY_OR_NOT_APPLICABLE
  OR DIRECT_CONTROLLER_READABLE != YES
  OR USER_RELAY_REQUIRED != NO
  OR REVIEW_OUTPUT_CONTRACT_SATISFIABLE != YES
  OR REVIEW_RESULT_EGRESS_PERMISSION_COMPATIBLE != YES
)
=> REVIEW_RESULT_EGRESS_GATE=FAIL
=> ENGINEERING_PREFLIGHT_GATE=FAIL

REVIEW_RESULT_EGRESS_REQUIRED=NO
=> REVIEW_RESULT_EGRESS_GATE=NOT_APPLICABLE
```

Required regression cases:

```text
A DETAILED_RESULT + GITHUB_WRITEBACK_ALLOWED + COMPLETE_DIRECT_RESULT => PASS
B DETAILED_RESULT + ALL_DIRECT_WRITEBACK_FORBIDDEN + TERMINAL_ONLY_CHAT + NO_PREEXISTING_FULL_RESULT => FAIL
C TERMINAL_ONLY_CHAT + COMPLETE_RESULT_AT_EXACT_CONTROLLER_READABLE_POINTER => PASS
D STRICT_READ_ONLY + EXACT_ARTIFACT_POINTER_DIRECT_TO_CONTROLLER + NO_RELAY => PASS
E USER_COPY_PASTE_REQUIRED_WHILE_DIRECT_SURFACE_AVAILABLE => FAIL
F NONREVIEW_TASK => EGRESS_REQUIRED=NO / REVIEW_RESULT_EGRESS_GATE=NOT_APPLICABLE / NO_FALSE_STOP
```

---

## 8. Repair and stop conditions

```text
REPAIR_STAGE=INITIAL|NORMAL_REPAIR|EXCEPTIONAL_REPAIR|HOLISTIC_CONVERGENCE
APPLICATION_REPAIR_BUDGET_REMAINING=
COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION|NOT_APPLICABLE
LEGACY_MATURE_SOLUTION_REOPEN_TRIGGER=YES|NO|NOT_APPLICABLE
STOP_CONDITION=
SAFE_STOP_OR_REPLAN_TRIGGER=
ROLLBACK_OR_RECOVERY_PLAN=
```

Default application/design route budget:

```text
INITIAL
+ ONE NORMAL REPAIR
+ AT MOST ONE EXPLICITLY AUTHORIZED EXCEPTIONAL NARROW REPAIR
```

No routine Repair 3/4/5. A new root cause or authority/layer expansion triggers holistic convergence.

For legacy project-owned commodity infrastructure, a material defect, clean-replacement requirement, repeated provider/qualification failure, material verification burden or exhausted repair budget expires prior `KEEP_CUSTOM` / `DEFER_MIGRATION` decisions before another semantic repair. Reopen the mature-solution gate first.

---

## 9. Pre-dispatch decision

`ENGINEERING_PREFLIGHT_GATE=PASS` only when every applicable field above is resolved and the selected Writer/executor has the capabilities required to perform the frozen task and its mandatory gates. This includes `STAGE_CLAIM_LADDER`, `AUTHORITATIVE_PROOF_SURFACE_FOR_EACH_STAGE`, `MINIMUM_REPRESENTATIVE_TOPOLOGY`, `COMPLEXITY_ESCALATION_ORDER`, `PRE_WRITER_GO_NO_GO_EXPERIMENT`, `DETERMINISTIC_BRANCH_PROOF_PLAN` and `REAL_EXTERNAL_BOUNDARY_PROOF_PLAN` when applicable.

For a material research/data task triggered by a research frontier, `ENGINEERING_PREFLIGHT_GATE=PASS` additionally requires an explicit disposition for each material frontier item after decomposition where needed. No data/research Writer may infer `ACQUIRE_BEFORE_NEXT_GATE` from `DATA_BLOCKED_FRONTIER` alone.

Disposition scope is binding:

```text
ACQUIRE_BEFORE_NEXT_GATE
=> ONLY_THE_CHEAPEST_DECISIVE_APPROVED_EVIDENCE_SCOPE_MAY_DISPATCH

CAPTURE_CHEAP_OPTIONALITY
=> CAPTURE_ONLY_NONAUTHORITATIVE_SCOPE
=> CURRENT_STRATEGY_OR_POLICY_CHANGE_FROM_CAPTURE=PROHIBITED

PROCEED_WITH_CURRENT_BEST_AND_DEFER
=> NEW_DATA_ENGINEERING_FOR_THE_DEFERRED_REQUIREMENT=PROHIBITED

PARK_OR_REJECT
=> NEW_DATA_ENGINEERING_FOR_THE_PARKED_REQUIREMENT=PROHIBITED_UNTIL_REOPEN_TRIGGER
```

`LEGACY_INCOMPLETE_CONSERVATIVE` is a resolved transitional evidence state, not an automatic research or Forward-Shadow blocker. It requires conservative evidence-strength labeling and prospective material-variant logging. `FAIL` for a new knowingly unlogged material variant blocks reliance on the affected adaptivity/independence claim until the missing trial identity is recovered.

For any applicable commodity-capability decision, `ENGINEERING_PREFLIGHT_GATE=PASS` additionally requires the external mature-solution selection rule to have reached a typed disposition. A Writer cannot self-authorize custom commodity infrastructure.

`UNRESOLVED_TRADEOFF` and `DECISION_STABILITY_CHECK=LOW` are not promotable states for selection, adoption or product Writer dispatch. A Tiny Spike is the only Writer exception, and only when the strictly bounded Tiny Spike fields above all pass.

If any applicable architecture, authority, validation-environment, scope, repair-budget, research-investment, mature-solution, Tiny Spike, or user-authority field is unresolved or fails its required promotion gate:

```text
ENGINEERING_PREFLIGHT_GATE=FAIL
WRITER_DISPATCH=PROHIBITED
```

The control role must then `REPLAN`, `DEFER`, `REASSIGN`, `REPLACE`, or `SAFE_STOP` at the actual unresolved boundary.

---

## 10. Post-stage record

After a material stage, report observed facts only:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=
ENGINEERING_PREFLIGHT_GATE=
EXACT_BASE=
FINAL_HEAD_OR_ARTIFACT=
CHANGED_PATHS=
IMPLEMENTATION_CHECKPOINT=
CLAIM_UNDER_TEST=
AUTHORITATIVE_PROOF_SURFACE=
CLAIM_RESULT=PASS|FAIL|UNPROVEN
NEXT_PROMOTION_ALLOWED=YES|NO
FAILED_RESPONSIBILITY_BOUNDARY=
RESIDUAL_UNPROVEN_CLAIMS=
IMPLEMENTATION_RESULT=
FOCUSED_TESTS=
PROPERTY_STATEFUL_OR_COMPOSITION_TESTS=
REALISTIC_SCALE_TEST=
CANONICAL_VALIDATION_COMMANDS_RUN=
VALIDATION_ENVIRONMENT=
RUFF=
MYPY=
COMPILE=
DIFF_SCOPE_SECRET_CHECKS=
EXACT_HEAD_CI=
INDEPENDENT_REVIEW=
REPAIR_STAGE=
RESIDUAL_RISKS=
DEFERRED_WORK=
RESEARCH_FRONTIER_REACHED=
RESEARCH_INVESTMENT_DISPOSITION=
FRONTIER_DECOMPOSITION=
TRIAL_AND_ADAPTIVITY_LEDGER_STATUS=
MATURE_SOLUTION_SELECTION_RESULT=
DECISION_STABILITY_RESULT=
STAGE_0_DISPOSITION=
TINY_SPIKE_BUDGET_OVERRIDE=
CUSTOM_COMMODITY_EXCEPTION_AUTHORITY=
MARK_READY_EXECUTED=YES|NO
MERGE_EXECUTED=YES|NO
DEPLOYMENT_EXECUTED=YES|NO
RUNTIME_ACTIVATION_EXECUTED=YES|NO
ACCOUNT_OR_EXCHANGE_WRITE_EXECUTED=YES|NO
```

Unrun checks are never reported as PASS.

For material work, broad `PASS`, `DONE`, `READY`, or equivalent wording may describe only the frozen claim actually proven on its authoritative proof surface. Applicable higher-level claims that were not run or were not representatively tested remain `UNPROVEN` and must appear in `RESIDUAL_UNPROVEN_CLAIMS`.

## 11. Task-completion truth gate / terminal readback

Before reporting whole-task completion, evaluate the current bounded user-request scope and active task contract and record this typed readback:

```text
CURRENT_BOUNDED_TASK_CONTRACT=
USER_REQUEST_SCOPE_TERMINAL_OBJECTIVE_REACHED=YES|NO
ACTIVE_TASK_CONTRACT_TERMINAL_DISPOSITION_REACHED=YES|NO
ALL_REQUIRED_INDEPENDENT_REVIEWS_TERMINAL=PASS|FAIL|NOT_APPLICABLE
LINKED_PR_STATE_READBACK=PASS|FAIL|NOT_APPLICABLE
LIVE_MAIN_READBACK=PASS|FAIL|NOT_APPLICABLE
POST_MERGE_OR_POST_PUBLICATION_VERIFICATION=PASS|FAIL|NOT_APPLICABLE
OPEN_PR_OR_SUPERSEDED_WORK_SWEEP=PASS|FAIL|NOT_APPLICABLE
LINKED_ISSUE_OR_TASK_TERMINALITY_READBACK=PASS|FAIL|NOT_APPLICABLE
USER_RETAINED_GATE_STATUS=COMPLETED|PENDING|NOT_APPLICABLE
NO_REQUIRED_NEXT_GATE_IS_SILENTLY_OMITTED=YES|NO
TASK_COMPLETION_TRUTH_GATE=PASS|FAIL
```

Derive applicability only from the current user-request scope and active bounded-task contract. Record `PASS` only from observed terminal evidence, `FAIL` for an applicable unsatisfied or unproven gate, and `NOT_APPLICABLE` only when the gate is outside that contract. Do not omit an applicable gate, infer `PASS` from an intermediate-stage result, or turn a non-applicable gate into an unconditional failure.

`LINKED_PR_STATE_READBACK` supplies the required PR terminal-disposition check. If a PR is required, it passes only when the PR has reached the terminal disposition required by the active task contract. `LIVE_MAIN_READBACK`, post-merge or post-publication verification, linked-task readback, and the open-PR or superseded-work sweep are independently required only when the contract makes them applicable.

Set `TASK_COMPLETION_TRUTH_GATE=PASS` if and only if both terminal-objective fields are `YES`, every applicable review and readback field is `PASS`, every inapplicable review and readback field is explicitly `NOT_APPLICABLE`, `USER_RETAINED_GATE_STATUS` is `COMPLETED` or `NOT_APPLICABLE`, and `NO_REQUIRED_NEXT_GATE_IS_SILENTLY_OMITTED=YES`. Otherwise set it to `FAIL`.

Apply these mandatory checks:

```text
WRITER_COMPLETE != WHOLE_TASK_COMPLETE
CI_PASS != WHOLE_TASK_COMPLETE
REVIEW_PASS != WHOLE_TASK_COMPLETE

MERGE_IN_ACTIVE_TASK_CONTRACT=YES
AND LIVE_MAIN_READBACK != PASS
=> TASK_COMPLETION_TRUTH_GATE=FAIL

POST_MERGE_VERIFICATION_REQUIRED_BY_ACTIVE_TASK_CONTRACT=YES
AND POST_MERGE_OR_POST_PUBLICATION_VERIFICATION != PASS
=> TASK_COMPLETION_TRUTH_GATE=FAIL

USER_RETAINED_GATE_STATUS=PENDING
=> TASK_COMPLETION_TRUTH_GATE=FAIL

NO_PR_IN_ACTIVE_TASK_CONTRACT
=> LINKED_PR_STATE_READBACK=NOT_APPLICABLE
=> OPEN_PR_OR_SUPERSEDED_WORK_SWEEP=NOT_APPLICABLE
   unless a linked or superseded PR is part of this bounded task

UMBRELLA_ISSUE_CONTINUES_TO_SEPARATE_NEXT_STAGE
AND CURRENT_BOUNDED_TASK_IS_TERMINAL
=> ISSUE_CLOSURE_IS_NOT_A_UNIVERSAL_COMPLETION_PREREQUISITE
```

When `TASK_COMPLETION_TRUTH_GATE=FAIL`, do not use user-facing whole-task words such as `complete`, `done`, or `已完成`. Report the exact stage reached, each failed or pending applicable gate, and the next required gate. This checklist does not authorize Mark Ready, merge, deployment, runtime activation, credential or private-API use, wallet or signing action, exchange action, trading, or capital action.