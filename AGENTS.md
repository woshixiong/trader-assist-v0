# Trader Assist / Trade OS — Agent Operating Map

This file is a **compact entry map**, not the project encyclopedia. GitHub is the engineering source of truth.

## 1. Authority loading — controller resolves, Writer consumes a compact packet

Engineering Control resolves live GitHub state and applicable governance under the Project Rules Index / Unified V2, completes material preflight when applicable, then freezes one exact Task Packet.

Required controller gates remain:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

A semantic Writer normally receives only the auto-loaded root map, exact Task Packet/hash, a governance/preflight attestation bound to the packet's live-main/base identity, normalized task-required authority assertions with exact provenance locators, affected code/tests, and the selected executor profile when model-backed.

The Writer does not reread full Unified V2, full preflight, full Issue/PR history or broad governance/docs by default. A concrete conflict, missing material fact or identity drift triggers the minimum targeted canonical read or returns control to Engineering Control.

Canonical rules remain full-strength authority; progressive disclosure changes model context, not governance.

### 1.1 Durable control plane and Control Capsule

Chat history is an ephemeral reasoning surface, not canonical engineering state. GitHub owns durable workflow state.

Default architecture:

```text
GITHUB = DURABLE CONTROL PLANE / STATE MACHINE
CHATGPT = MATERIAL DECISION / EXCEPTION / ADJUDICATION SERVICE
CODEX OR OTHER ACCEPTED WRITER = SEMANTIC IMPLEMENTATION SERVICE
GITHUB ACTIONS / DETERMINISTIC TOOLS = VERIFICATION AND ROUTINE TRANSITIONS
```

Each active material task maintains one compact canonical **Control Capsule**:

```text
TASK_ID
GOVERNANCE_EPOCH
EXACT_MAIN
EXACT_TARGET_HEAD_OR_TREE
TASK_PACKET_HASH
RISK_CLASS
CURRENT_STATE
CURRENT_BLOCKER
NEXT_ALLOWED_ACTION
RUNNING_AGENT_THREAD_OR_WORKSPACE_ID
CURRENT_PR
CI_STATE_LOCATOR
COMPLETED_WORK_LEDGER
RETAINED_USER_GATES
AUTHORITY_ATTESTATION_LOCATORS
PREFLIGHT_BINDING_KEY
```

Full technical evidence, historical failures and superseded routes stay behind exact GitHub locators. Active model context contains only the capsule, current packet/manifest and the minimum facts required for the current decision.

```text
CHAT_HISTORY_IS_NOT_ENGINEERING_STATE=YES
NO_CRITICAL_ENGINEERING_STATE_ONLY_IN_CHAT=YES
ACTIVE_STATE_MINIMALITY_GATE=REQUIRED
COMPLETED_WORK_LEDGER=REQUIRED
FULL_ISSUE_PR_HISTORY_RELOAD_BY_DEFAULT=NO
RAW_LONG_LOG_IN_MODEL_CONTEXT=NO_BY_DEFAULT
QUALITY_AND_CORRECTNESS_GT_CONTEXT_ECONOMY=YES
```

### 1.2 Governance epoch, reusable preflight and context lifecycle

A governance epoch is the exact set/hash of applicable canonical authority file SHAs used to produce the current governance attestation.

```text
FULL_CORE_RULE_READ=
  FIRST MATERIAL ACTION IN A FRESH CONTROL CONTEXT
  OR GOVERNANCE_EPOCH DRIFT
  OR CONCRETE AUTHORITY CONFLICT

UNCHANGED_GOVERNANCE_EPOCH
=> REUSE BOUND GOVERNANCE ATTESTATION
=> TARGETED CANONICAL READS ONLY
```

Material preflight is reusable when its binding key is unchanged:

```text
PREFLIGHT_BINDING_KEY =
  GOVERNANCE_EPOCH
  + TASK_PACKET_HASH
  + EXACT_BASE_OR_HEAD
  + EXECUTION_SURFACE
```

Fresh live repository/main/Issue/PR/head/CI identity checks remain mandatory. Attestation reuse is memoization of exact proven authority, never permission to ignore drift.

Engineering Control is event-driven. Routine provider/GitHub-proven transitions do not require a model turn merely to restate state. Wake control for a new material direction, semantic blocker/new root cause, material CI failure requiring reasoning, scope/authority/identity drift, material Review finding, user-retained gate, or context-integrity risk.

Window rotation protects context capacity/trust; it is not a stage ceremony.

```text
ONE_MATERIAL_STAGE_PER_WINDOW=NO_DEFAULT
MULTIPLE_ROUTINE_STAGES_PER_WINDOW=ALLOWED_WHEN_CONTEXT_REMAINS_COMPACT
PREEMPTIVE_ROTATION=REQUIRED_WHEN_NEXT_HEAVY_PHASE_LACKS_TRUSTED_HEADROOM
```

On rotation, freeze/verify the Control Capsule and any running session/workspace identity, then start the successor from that durable state. The user is not responsible for detecting context pressure or reconstructing the authority chain.

### 1.3 Token-sustainable mechanical-state routing

Mechanical repository/control-plane work is **zero-model by default**. Do not keep Codex, ChatGPT or another semantic model active merely to wait for or restate provider state.

```text
M0_MECHANICAL_STATE
= GitHub / provider-native / deterministic tool
= ZERO MODEL

M1_LIGHTWEIGHT_NONAUTHORITATIVE_TRANSFORM
= lowest sufficient model only when deterministic tooling cannot express the transform
= output remains machine-verifiable and non-authoritative

M2_SEMANTIC_WRITER
= task-adaptive capable model + reasoning
= semantic implementation / repair only

M3_AUTHORITY_REVIEW
= fresh ordinary ChatGPT independent reviewer by routine default
= high / highest appropriate reasoning
```

Before every Writer dispatch, Engineering Control / Router freezes exactly one execution class:

```text
DETERMINISTIC_MECHANICAL
-> MODEL_REQUIRED=NO
-> GitHub / Actions / provider-native deterministic tooling

FROZEN_BOUNDED_SEMANTIC
-> fresh ordinary ChatGPT Writer by routine default
-> root cause / direction frozen
-> implementation semantics effectively bounded
-> narrow explicit write allowlist
-> no new architecture / provider / dependency choice
-> decisive acceptance tests already specified
-> new root cause / scope expansion => STOP and return to Engineering Control

OPEN_MATERIAL_SEMANTIC
-> Codex default when available and allowed by the current Router

HIGH_CONSEQUENCE_AMBIGUOUS
-> strongest appropriate accepted route

USER_MANUAL_OVERRIDE
-> always preserved; no silent substitution
```

This classification selects only the execution surface. It does not alter the engineering state machine, Task Packet semantics, exact-head CI, independent Review, or retained user gates. A Review FAIL creates a new bounded development task which is classified through this same universal rule; there is no separate repair-routing taxonomy.

M0 owns routine reads and waits including live-main SHA, PR state/Draft/base/head/tree, changed paths, mergeability metadata, CI run/job state and conclusions, artifact IDs/names/digests, hashes, allowlists and typed terminal-result extraction.

For exact-head PR CI waiting/terminal projection, use `.agents/skills/trade-os-ci-terminal-wait/SKILL.md` when that execution surface is available.

```text
MODEL_MEDIATED_CI_POLLING=PROHIBITED
CI_WAIT_OWNER=GITHUB_OR_DETERMINISTIC_TOOL
RAW_SUCCESS_LOG_INGESTION=PROHIBITED_BY_DEFAULT
FAILURE_LOG_READ=BOUNDED_FAILED_STEP_EVIDENCE_ONLY
EXACT_ITEM_ENDPOINT_BEFORE_COLLECTION_ENDPOINT=YES
KNOWN_LARGE_FILE_FULL_READ=NO_BY_DEFAULT
NEW_CHAT_NE_NEW_CONTROL_CONTEXT=YES
```

After a Writer publishes an exact head, checkpoint at `CI_PENDING` and stop semantic polling. A healthy all-green terminal transition may mechanically advance to `REVIEW_NEEDED`; wake one fresh M3 Reviewer directly. Wake Engineering Control only for a material decision/exception such as a new root cause, semantic or ambiguous CI failure, non-mechanical identity/scope/authority drift, repair-budget exhaustion, material Review finding, retained user gate or context-integrity risk.

For any managed Codex Desktop/local worktree, the controller/runner owns a **pre-model deterministic exact-base gate** before semantic tokens are spent: freshen/verify `origin/main` (or the frozen canonical remote-tracking ref), require it to equal the frozen exact base, verify the bound exact tree when supplied, create or deterministically realign a **clean** managed worktree from the exact frozen commit, require worktree HEAD to equal that base and require a clean worktree. A stale local branch label is not proof. Dirty/ambiguous state fails closed. This is prelaunch execution control, not a Writer-prompt reminder.

A new chat/window does not invalidate a still-valid Control Capsule/governance attestation. When the governance epoch, task binding and exact authority identity remain unchanged, fresh-check identity metadata and exact locators only; do not reread full governance/history merely because the conversation surface changed.

## 2. User shorthand for unified-governance changes

When the user says **“往统一规则里增加内容”**, **“把这条加入统一规则”**, **“add this to the unified rules”**, or an equivalent phrase, treat it as a request to start the Unified Engineering Governance change-routing process.

Do **not** mechanically append all supplied text to Unified V2. Classify first:

```text
DURABLE_PROJECT_WIDE_CROSS_TASK_ENGINEERING_INVARIANT
-> update Unified V2

TASK_SPECIFIC_RESEARCH_PROCEDURE_OR_EXAMPLE
-> research procedure/reference
-> update V2 only if a reusable project-wide invariant is discovered

HUMAN_EXECUTED_COMMAND_LAUNCHER_PROCEDURE_OR_INCIDENT_EXAMPLE
-> Generated Command procedure/catalogue
-> update V2 only if a reusable project-wide invariant is discovered

EXECUTOR_MODEL_TOOL_DEPLOYMENT_SPECIFIC_DETAIL
-> narrow applicable profile/contract
-> update V2 only if a reusable project-wide invariant is discovered

ONE_OFF_INCIDENT_OR_HISTORY
-> Issue/incident history unless it yields a reusable invariant
```

Default rules:

```text
NEW_PROJECT_WIDE_GOVERNANCE_AUTHORITY=DISFAVORED
UNIFIED_V2_REMAINS_SINGLE_PROJECT_WIDE_ENGINEERING_CONSTITUTION=YES
```

Create a new specialized procedure/contract only when the domain is genuinely narrow, its detail has a materially independent lifecycle, and putting the detail in V2 would create avoidable bloat. Any such document must be indexed, explicitly subordinate to V2 and non-duplicative.

This shorthand does not itself authorize implementation, Mark Ready, merge, deployment, runtime/cloud mutation or any other user-retained gate.

## 3. Load specialized procedures only when applicable

Do **not** read every tool/profile file for every task.

- material direction-setting research -> `PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
- material external mature-solution selection/adoption or reopened build-vs-buy -> `EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md`
- nontrivial human-executed command/launcher -> `GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md`
- user-local Git transport or independently reviewed PR publication/closeout -> `GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md`
- model-backed executor selection -> `ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md` + only the selected executor/model profile
- new/materially changed engineering tool -> `ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`
- Local Task Runner -> its accepted Runner profile/skill only when selected and compatible
- Hermes -> Hermes contract/profile only when selected
- target-host deployment/qualification through FinalShell -> `FINALSHELL_TARGET_HOST_DEPLOYMENT_WORKFLOW_V1_2026-08-26.md` + current Operations authority.

The Unified V2 standard owns project-wide engineering policy. Specialized files may be stricter in their narrow domain but are not competing constitutions.

## 4. Universal execution invariants

```text
GITHUB_CANONICAL_SOURCE=YES
ONE_PROJECT_WIDE_ENGINEERING_CONSTITUTION=YES
INDEPENDENT_ANALYSIS_BEFORE_EXTERNAL_CONCLUSIONS=YES_FOR_MATERIAL_DIRECTION_SETTING
MATURE_SOLUTION_FIRST=YES
MATURE_CAPABILITY_NO_REBUILD_GATE=REQUIRED
COMMODITY_INFRASTRUCTURE_CUSTOM_BUILD_DEFAULT=PROHIBITED
ENGINEERING_WINDOW_SELF_AUTHORIZED_CUSTOM_COMMODITY_BUILD=PROHIBITED
STRATEGY_DECISION_ENGINE_PROJECT_OWNED=YES
TRADING_INFRASTRUCTURE_ENGINE_MATURE_EXTERNAL_OWNER_BY_DEFAULT=YES
STAGE_0_NO_PRODUCT_CODE_AUDIT=REQUIRED_WHEN_MATURE_SOLUTION_GATE_APPLIES
ONE_BLOCKER_TINY_SPIKE_ONLY_WHEN_CHEAP_SAFE_DECISIVE=YES
GLOBAL_ROOT_CAUSE_BEFORE_LOCAL_PATCH_LOOPS=YES
STABLE_NARROW_SEAMS_AND_CONTINUITY=REQUIRED
DEVELOPMENT_AND_VERIFICATION_DESIGNED_TOGETHER=YES
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=YES
VALIDATION_ENVIRONMENT_MUST_MATCH_CLAIM=YES
CLAIM_BASED_STAGE_SUCCESS=REQUIRED
PROGRESSIVE_REPRESENTATIVE_PROOF=REQUIRED
PRE_WRITER_GO_NO_GO_EXPERIMENT=WHEN_CHEAP_SAFE_AND_DECISIVE
DETERMINISTIC_AND_REAL_EXTERNAL_PROOF_COMPLEMENT=WHEN_APPLICABLE
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
COMPLETE_TASK_PACKET_BEFORE_EXECUTION=YES
WRITER_PASS_NE_INDEPENDENT_ACCEPTANCE=YES
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
ACTIVE_TASK_OWNERSHIP_UNTIL_TERMINAL_DISPOSITION=YES
REVIEWED_PR_TERMINAL_DISPOSITION_REQUIRED=YES
NO_SILENT_MODEL_EXECUTOR_FALLBACK=YES
NO_HIDDEN_SEMANTIC_RETRY=YES
CI_FAILURE_CLASSIFICATION_BEFORE_REPAIR=REQUIRED
KNOWN_TRANSIENT_SAME_HEAD_RERUN_MAX=1
DETERMINISTIC_MECHANICAL_FAILURE_NE_SEMANTIC_REPAIR=YES
DETERMINISTIC_MECHANICAL_FAILURE_PREFERS_NON_MODEL_REPAIR=YES
TRANSPORT_OR_INFRA_FAILURE_NE_SEMANTIC_RETRY=YES
FALSE_SAFE_STOP_GATE=PROHIBITED
CHECKPOINT_RESUME_INSTEAD_OF_REDO=YES
SEMANTIC_START_DEPENDENCY_MINIMIZATION=REQUIRED
SEMANTIC_READINESS_NE_PUBLICATION_READINESS=YES
PER_TASK_DYNAMIC_EXECUTION_PROGRAM_GENERATION=PROHIBITED_BY_DEFAULT
TASK_PACKET_IS_DATA_NOT_EXECUTION_PROGRAM=YES
VERSIONED_STABLE_SEMANTIC_RUNNER=DEFAULT_WHEN_LOCAL_MODEL_EXECUTION_IS_NEEDED
ENGINEERING_WINDOW_ROTATION_POLICY=CAPACITY_AND_TRUST_BASED
GITHUB_CONTROL_PLANE_STATE_MACHINE=YES
CONTROL_CAPSULE_REQUIRED=YES
GOVERNANCE_EPOCH_ATTESTATION=REQUIRED
BOUND_PREFLIGHT_REUSE_WHEN_BINDING_UNCHANGED=YES
EVENT_DRIVEN_CHATGPT_CONTROL=YES
ACTIVE_STATE_MINIMALITY_GATE=REQUIRED
COMPLETED_WORK_LEDGER=REQUIRED
VALIDATED_EXECUTION_PATH_LEDGER=REQUIRED
FAILED_PATH_RETIREMENT_LEDGER=REQUIRED
QUOTA_BOUNDARY_RESUME_NOT_RETRY=YES
REVIEW_RESULT_EGRESS_IDEMPOTENCY=REQUIRED
TRANSPORT_INTERRUPTION_NE_TASK_FAILURE=YES
FINAL_INDEPENDENT_REVIEW_REQUIRES_FRESH_INDEPENDENT_CONTEXT=YES
EXACT_ARTIFACT_EXACT_HEAD_CI_INDEPENDENT_REVIEW=WHEN_APPLICABLE
AUTHORITATIVE_REMOTE_EXECUTION_PREFERRED_WHEN_EQUAL_OR_HIGHER_FIDELITY=YES
USER_LOCAL_WORKSTATION_NOT_DEFAULT_FOR_CI_OR_LINUX_PROOF=YES
REMOTE_EXECUTION_CREDENTIAL_AUTHORITY_MUST_BE_EXPLICIT=YES
```

## 5. Repository and authority safety

- no direct commit to `main` for normal engineering work;
- no force-push/shared-history rewrite after review begins;
- no secrets, credentials, wallets, raw private/account data, production DB/log/cache or real account identifiers in commits;
- simulated/default market/account data is never real evidence;
- scope expansion, new material architecture/authority/provider/dependency decision or exhausted repair budget -> `SAFE_STOP` / `L1_DECISION_REQUIRED`;
- Mark Ready, merge, deployment, runtime/cloud mutation, service start/restart/enable/reboot, credentials/private API, wallet/signing, exchange write/order submission/cancellation and autonomous trading always require separate current user authority.

## 6. Review and task ownership

Authority-bearing final independent adjudication **requires a fresh independent review context/agent** that did not control or implement the candidate stage. Engineering Control and the semantic Writer may perform self-check/readiness work, but their PASS cannot become independent acceptance. The routine default is a **new ordinary ChatGPT review window** using the current strongest appropriate ordinary ChatGPT model (currently GPT-5.6 Sol) with High / highest appropriate reasoning, read-only authority and direct exact GitHub evidence. A provider-native or Codex reviewer route is an explicit task-specific exception / opt-in only; if selected, it must prove fresh context, read-only review permissions, direct exact-canonical-evidence access, no inheritance of Writer/Supervisor/Engineering-Control conclusions as facts, and idempotent result egress through an accepted direct or lossless transport surface. Independence is a role/context/authority property; a different model vendor is not required by itself.

The reviewer receives a compact Review Manifest: exact target identity, exact changed scope/diff, frozen acceptance criteria, required safety boundaries, decisive CI/artifact/source locators, and any explicitly untrusted prior conclusions. If GitHub evidence is sufficient, review exact GitHub head/diff + exact-head CI directly. Do not reload full Issue/PR history or the full governance corpus by default; use targeted canonical reads only for concrete unknowns/conflicts. If local evidence is needed, prefer deterministic hash-manifested evidence/review bundles rather than downgrading the final Reviewer to a weaker local coding model.

Before any Writer / Reviewer / executor writes a terminal result or blocker, it must fresh-read the current canonical GitHub task/PR state. If another control surface already advanced the state, write only an idempotent reconciliation against that live state; do not emit a stale blocker or stale terminal state from a local checkpoint.

For execution/validation, prefer an authoritative GitHub/provider-native remote surface over user-operated local emulation when it provides equal or higher claim fidelity, exact identity/evidence, and lower human relay. This preference never creates credential/private-API authority and never overrides a genuinely local or target-host-specific claim boundary.

The current control/orchestration role retains task ownership through intermediate CI/review/publication gates, executes every safe authorized next action, and stops only at the specific external or user-retained authority boundary.

An independently reviewed PR must reach an explicit terminal disposition under `GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md`: accepted PASS work proceeds through retained Mark Ready / merge authority and live-main verification; REPLAN / REJECT / SUPERSEDED work is explicitly closed or superseded. Do not leave reviewed PRs indefinitely open/draft without an exact recorded blocker.

## 7. Stale / historical files

`CODEX.md` and superseded governance are historical evidence only. Do not use them as fallback instruction authority when current indexed governance exists.
