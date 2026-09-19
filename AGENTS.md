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

### 1.1 Project-wide context architecture

Chat history is an ephemeral working surface, not canonical engineering state. Durable current state belongs in GitHub.

Default context layers:

```text
ALWAYS_ON_CORE
-> ACTIVE_STAGE_CHECKPOINT / TASK OR REVIEW PACKET
-> TARGETED_CANONICAL_READ ONLY FOR A CONCRETE UNKNOWN / CONFLICT / DRIFT
-> COLD_HISTORY / RAW_EVIDENCE OUTSIDE MODEL CONTEXT BY DEFAULT
```

Every compact checkpoint must preserve the current stage, exact main/base/head when applicable, active authority, accepted decisions, superseded routes, unresolved blockers, allowed scope, acceptance criteria, next authorized action and exact provenance locators. Context compression may remove repetition, never authority or evidence. A missing material fact, conflicting locator or uncertain supersession state triggers the minimum targeted canonical read; unresolved uncertainty fails closed.

```text
CHAT_HISTORY_IS_NOT_ENGINEERING_STATE=YES
NO_CRITICAL_ENGINEERING_STATE_ONLY_IN_CHAT=YES
QUALITY_AND_CORRECTNESS_GT_CONTEXT_ECONOMY=YES
FULL_ISSUE_PR_HISTORY_RELOAD_BY_DEFAULT=NO
RAW_LONG_LOG_IN_MODEL_CONTEXT=NO_BY_DEFAULT
```

### 1.2 Engineering-window lifecycle

Each Engineering Control conversation/window must establish at entry:

```text
WINDOW_SCOPE=
ROTATION_TRIGGER=
ACTIVE_CHECKPOINT_REF=
```

Rotation is event-driven, not dependent on a user-visible token meter. Material stage completion, material replan/authority change, independent-review boundary, command-family holistic regeneration, context warning or loss of context trust, or repeated transport interruption are default rotation triggers.

When a trigger fires, Engineering Control must first write/verify a durable GitHub checkpoint, then produce a complete successor-window prompt that points to that checkpoint and the minimum canonical locators. The current window must not continue into the next material stage merely because it still has capacity. A successor window verifies the predecessor checkpoint and live identity before material work.

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
FALSE_SAFE_STOP_GATE=PROHIBITED
CHECKPOINT_RESUME_INSTEAD_OF_REDO=YES
SEMANTIC_START_DEPENDENCY_MINIMIZATION=REQUIRED
SEMANTIC_READINESS_NE_PUBLICATION_READINESS=YES
ENGINEERING_WINDOW_ROTATION_POLICY=REQUIRED
TRANSPORT_INTERRUPTION_NE_TASK_FAILURE=YES
FINAL_INDEPENDENT_REVIEW_REQUIRES_NEW_CHAT_CONTEXT=YES
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

Authority-bearing final independent adjudication **requires a new ordinary ChatGPT conversation/window** using the strongest appropriate available model and highest appropriate reasoning. Engineering Control and the semantic Writer may perform self-check/readiness work, but a PASS produced in the same conversation that controlled or implemented the stage is not independent acceptance.

The reviewer receives a compact Review Manifest: exact target identity, exact changed scope/diff, frozen acceptance criteria, required safety boundaries, decisive CI/artifact/source locators, and any explicitly untrusted prior conclusions. If GitHub evidence is sufficient, review exact GitHub head/diff + exact-head CI directly. Do not reload full Issue/PR history or the full governance corpus by default; use targeted canonical reads only for concrete unknowns/conflicts. If local evidence is needed, prefer deterministic hash-manifested evidence/review bundles rather than downgrading the final Reviewer to a weaker local coding model.

For execution/validation, prefer an authoritative GitHub/provider-native remote surface over user-operated local emulation when it provides equal or higher claim fidelity, exact identity/evidence, and lower human relay. This preference never creates credential/private-API authority and never overrides a genuinely local or target-host-specific claim boundary.

The current control/orchestration role retains task ownership through intermediate CI/review/publication gates, executes every safe authorized next action, and stops only at the specific external or user-retained authority boundary.

An independently reviewed PR must reach an explicit terminal disposition under `GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md`: accepted PASS work proceeds through retained Mark Ready / merge authority and live-main verification; REPLAN / REJECT / SUPERSEDED work is explicitly closed or superseded. Do not leave reviewed PRs indefinitely open/draft without an exact recorded blocker.

## 7. Stale / historical files

`CODEX.md` and superseded governance are historical evidence only. Do not use them as fallback instruction authority when current indexed governance exists.
