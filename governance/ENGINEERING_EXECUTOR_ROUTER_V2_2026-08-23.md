# Trader Assist / Trade OS — Engineering Executor Router V2

> **HISTORICAL / SUPERSEDED BY V4.** This file is preserved as routing
> rationale only. Active routing is owned by
> `governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md`.

**Status:** HOLISTIC-CONVERGENCE GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-23  
**Repository:** `woshixiong/trader-assist-v0`

This file supersedes the routing logic in `ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md` after independent acceptance and merge. It changes tooling only. It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission/cancellation or trading authority.

## 1. Objective

Select the execution path that maximizes accepted engineering progress while minimizing rework, user relay, quota consumption and unnecessary context.

```text
ROUTING_OBJECTIVE =
  QUALITY / CORRECTNESS
  + TASK_MODEL_FIT
  + AGENTIC_COMPLETION_ABILITY
  + VALIDATION_CLOSURE
  + HUMAN_RELAY_REDUCTION
  + WALL_CLOCK_EFFICIENCY
  + QUOTA_EFFICIENCY
  - REWORK_RISK
  - CONTEXT_BLOAT
  - TOOL_SWITCHING_COST
```

Free token price never overrides a real quality requirement. Paid/quota resources are not consumed merely because they exist.

## 2. Permanent user override

```text
USER_MANUAL_OVERRIDE=ALWAYS_AVAILABLE
SILENT_MODEL_OR_EXECUTOR_SUBSTITUTION=PROHIBITED
```

If the user explicitly selects a model/executor, Engineering uses it for that bounded task/stage unless the path lacks a mandatory capability or violates a safety/authority gate. In that case return `SAFE_STOP` and explain the capability gap; do not silently substitute.

### 2.1 Universal model-invocation coverage

Router V2 governs **every project model-backed invocation**, not only the currently enumerated Writer candidates. This includes:

```text
CODEX_CLI
OPENCODE
TRAE
DEEPSEEK_HARNESS
FUTURE_EXECUTORS_PROVIDERS_MODELS
MODEL_BACKED_BROWSER_OR_COMPUTER_OPERATORS
LOCAL_MODEL_BACKED_EVIDENCE_PROVIDERS
T4_MODEL_AND_SURFACE_SELECTION_WHERE_APPLICABLE
```

Deterministic non-model tools do not require model selection, but they remain subject to tool onboarding, authority, evidence and publication rules.

The existence of a specialized profile does not create a routing exception. Specialized profiles constrain execution **after** Router V2 selects the route.

### 2.2 Mandatory route freeze and requested-vs-actual attestation

Before every model-backed launch, Engineering Control freezes the requested route:

```text
ROUTER_ROLE=
ROUTER_EXECUTOR_SURFACE=
ROUTER_PROVIDER=
ROUTER_MODEL=
ROUTER_REASONING_OR_EQUIVALENT=
ROUTER_WEB_SEARCH_OR_TOOL_STATE=
ROUTER_SESSION_POLICY=
ROUTER_RESOURCE_STATE=
EXECUTION_CLASS=
  DETERMINISTIC_MECHANICAL
  | FROZEN_BOUNDED_SEMANTIC
  | OPEN_MATERIAL_SEMANTIC
  | HIGH_CONSEQUENCE_AMBIGUOUS
USER_MANUAL_OVERRIDE_APPLIED=YES|NO
```

Where the execution surface exposes the information, collect the actual launch/runtime identity without asking the user to inspect raw logs:

```text
ACTUAL_EXECUTOR_SURFACE=
ACTUAL_PROVIDER=
ACTUAL_MODEL=
ACTUAL_REASONING_OR_EQUIVALENT=
ACTUAL_WEB_SEARCH_OR_TOOL_STATE=
ACTUAL_SESSION_ID=
```

Use `NOT_EXPOSED` only when the surface genuinely does not expose an optional field. If an identity is required by the frozen task/authority contract and cannot be proven, fail closed rather than guessing. Absence of observed Web Search/tool calls proves only that no use was observed; it does not prove a disabled configuration unless the execution surface exposes that configuration state.

Real-task telemetry is evidence for later Router refinement; it does not silently rewrite the current routing policy or create a universal benchmark ranking.

### 2.3 Executor/model-agnostic Router incident contract

Any of the following is a Router incident:

- requested-vs-actual executor/provider/model/reasoning/tool-state mismatch outside an explicitly accepted equivalence;
- silent fallback or substitution;
- unauthorized retry, rerun or resume;
- dynamic downstream model/executor selection outside the accepted contract;
- ignored user manual override;
- inability to prove an identity that the frozen task requires.

On detection:

```text
ROUTER_INCIDENT=YES
SAFE_STOP_CURRENT_STAGE=YES
AUTOMATIC_RERUN=PROHIBITED
SILENT_ALTERNATIVE=PROHIBITED
PROACTIVE_USER_NOTIFICATION=REQUIRED
TOOLING_CONTROL_ESCALATION=REQUIRED
```

Engineering Control owns incident discovery and classification. The user must not be asked to manually diagnose raw executor logs or compose the escalation record.

Engineering Control must emit one complete ready-to-copy Tooling Control escalation packet containing the frozen requested route, observed actual route/evidence, exact task/session/artifact identity where available, mismatch or uncertainty, current mutation state, and the required stop condition. A new run requires a new explicit Engineering-Control disposition and applicable authority.

## 3. Resource state

Engineering records, when relevant:

```text
CODEX_QUOTA_STATE=HEALTHY|CONSTRAINED|EXHAUSTED
TRAE_POINTS_STATE=AVAILABLE|LOW|EXHAUSTED
OPENCODE_FREE_STATE=AVAILABLE|DEGRADED|UNAVAILABLE
```

Current user policy until explicitly changed:

- GitHub/provider-native/deterministic surfaces remain first for deterministic/mechanical control-plane work; no semantic model is required.
- A **frozen bounded semantic** task uses a fresh ordinary ChatGPT Writer as the routine first-class default when all bounded-semantic predicates in §4 pass. This route no longer requires routine per-task fallback approval merely because Codex quota exists.
- An **open/material semantic** task uses Codex by default when Codex is available and allowed by the current task/authority contract.
- A **high-consequence/ambiguous** task uses the strongest appropriate accepted route; strongest/max reasoning is still selected for actual consequence/difficulty rather than by habit.
- User manual override remains always available. A current explicit user selection is honored unless it lacks a mandatory capability or violates safety/authority.
- Codex quota/capacity state constrains Codex availability but never changes the task's execution class and never silently authorizes a different non-default route.
- Accepted alternatives such as the user's GLM/GRM 5.3, DeepSeek V4 Pro, Trae/OpenCode or later approved routes remain task-specific selections/exceptions, not silent replacements.
- Unexpected Codex capacity/quota interruption after dispatch preserves the exact checkpoint/evidence and is an expected capacity pause, not a semantic failure. Resume the exact session/thread when recoverable; otherwise continue from the durable checkpoint. Do not restart the original semantic task from scratch and do not silently switch executor.
- Temporary free/discounted models are opportunistic only and do not become durable routing dependencies.

## 4. Surface-first routing and universal execution classes

Router selection is **surface-first**, then semantic-open-ness/consequence, then model fit. File count and quota state do not define the class.

Engineering Control must freeze exactly one class and the reason **before Writer dispatch**:

```text
DETERMINISTIC_MECHANICAL
-> MODEL_REQUIRED=NO
-> GitHub / Actions / provider-native deterministic tooling

FROZEN_BOUNDED_SEMANTIC
-> ROUTINE_DEFAULT=FRESH_ORDINARY_CHATGPT_WRITER
-> ROOT_CAUSE_OR_DIRECTION_FROZEN=YES
-> IMPLEMENTATION_SEMANTICS_EFFECTIVELY_BOUNDED=YES
-> NARROW_EXPLICIT_WRITE_ALLOWLIST=YES
-> NEW_ARCHITECTURE_PROVIDER_DEPENDENCY_CHOICE=NO
-> DECISIVE_ACCEPTANCE_TESTS_ALREADY_SPECIFIED=YES
-> NEW_ROOT_CAUSE_OR_SCOPE_EXPANSION=>STOP_AND_RETURN_TO_ENGINEERING_CONTROL

OPEN_MATERIAL_SEMANTIC
-> CODEX_DEFAULT_WHEN_AVAILABLE_AND_ALLOWED

HIGH_CONSEQUENCE_AMBIGUOUS
-> STRONGEST_APPROPRIATE_ACCEPTED_ROUTE
```

Manual override is orthogonal to execution classification, remains always preserved, never creates a fifth execution class, and never permits silent model/executor substitution.

This classifier changes only executor routing. It does not change Task freeze -> Writer -> CI -> independent Review -> retained user gate, Task Packet semantics, exact-head CI, Review independence, runtime/deployment/trading authority or any other state-machine gate.

A Review FAIL does not enter a special repair router. Engineering Control first creates a **new bounded development task** from the finding, freezes its scope/root cause/acceptance contract as applicable, and then runs this same universal classifier.

Codex quota never creates work and never moves deterministic or frozen-bounded work into Codex merely because capacity is available.

### 4.0A Codex Desktop / managed-worktree pre-model deterministic gate

For any Codex Desktop/local managed-worktree semantic launch, the deterministic controller/runner must complete this gate **before model invocation**:

```text
1 FRESHEN_OR_VERIFY origin/main (or the frozen canonical remote-tracking ref)
2 REQUIRE remote-tracking ref == frozen exact base
3 REQUIRE frozen exact tree == canonical expected tree when bound
4 CREATE_OR_REALIGN a CLEAN managed worktree from the exact frozen commit
5 REQUIRE managed-worktree HEAD == frozen exact base
6 REQUIRE managed worktree clean
7 ONLY THEN launch the semantic model
```

A stale local branch label is never proof of canonical main. Clean exact-base realignment before semantic start is execution-surface recovery, not semantic repair and does not consume semantic repair budget. Dirty/ambiguous worktrees fail closed; no silent reset. This must be enforced by the controller/runner prelaunch surface, not merely written into the Writer prompt.

### 4.0B Terminal result egress freshness

Before any Writer / Reviewer / executor writes a terminal result or blocker:

```text
FRESH_READ_CURRENT_GITHUB_TASK_PR_STATE=REQUIRED

IF_CANONICAL_STATE_ALREADY_ADVANCED_EXTERNALLY
-> WRITE_IDEMPOTENT_RECONCILIATION
-> DO_NOT_WRITE_STALE_BLOCKER_OR_STALE_TERMINAL_STATE
```

A local executor checkpoint is not proof of the current canonical GitHub state.

### 4.1 Provider-native asynchronous semantic route

When an accepted provider-native coding-agent surface can bind a task to an isolated workspace, preserve exact task identity, produce a reviewable result, expose sufficient session/result state and respect the frozen authority boundary, prefer that route over serial chat supervision.

```text
ISSUE_OR_CONTROL_CAPSULE
-> ACCEPTED_ASYNC_AGENT
-> ISOLATED_WORKSPACE
-> REVIEWABLE_RESULT
-> CI
-> INDEPENDENT_REVIEW
```

This is a surface preference, not blanket authorization. If observability, recovery, exact identity, permission or safety fidelity is weaker than the proven fallback, use the accepted fallback instead. Do not build a custom multi-agent orchestrator merely to imitate provider-native capability.

### T0 — MECHANICAL / OPERATOR

Examples: repo search, GitHub state, log extraction, tests, CI, status/diff/evidence, deterministic formatting, artifact handling, already-authorized publication mechanics.

```text
DEFAULT=GITHUB_CONNECTOR_OR_GITHUB_ACTIONS_OR_DETERMINISTIC_TOOL
MODEL_WRITER_REQUIRED=NO
CODEX=NO
```

Use OpenCode/another model only when the operation itself genuinely needs model interpretation; do not invoke a model merely to run commands.

### T1 — LOW-RISK / FROZEN BOUNDED CODING

Frozen scope, frozen root cause/direction, effectively bounded implementation semantics, decisive validation and low blast radius normally map to `FROZEN_BOUNDED_SEMANTIC`.

Preferred routes:
- Engineering Control direct GitHub edit only for governance/docs, Issue/PR metadata, workflow metadata or mechanical configuration whose semantics are already frozen and deterministically checkable;
- application/source semantic logic uses a fresh ordinary ChatGPT Writer by routine default when every bounded-semantic predicate is satisfied;
- discovery of a new root cause, architecture/provider/dependency choice or write-surface expansion immediately stops the bounded Writer and returns control.

```text
FROZEN_BOUNDED_SEMANTIC_DEFAULT=FRESH_ORDINARY_CHATGPT_WRITER
```

### T2 — MATERIAL NORMAL ENGINEERING

Normal feature implementation, meaningful bug fix, bounded multi-file implementation or nontrivial refactor is classified by what semantic decisions remain, not by file count.

First use GitHub/Engineering Control for all control-plane discovery, exact-state work and validation setup.

- If root cause/direction and implementation semantics are already frozen enough to satisfy every `FROZEN_BOUNDED_SEMANTIC` predicate, use the ordinary ChatGPT bounded Writer default.
- If the Writer must still decide architecture, root cause, cross-layer semantics, recovery/concurrency/security/authority design, dependency/provider choice or substantial implementation direction/continuity, classify `OPEN_MATERIAL_SEMANTIC` and use Codex by default when available/allowed.
- Accepted alternatives such as GLM/GRM 5.3, DeepSeek V4 Pro, Trae/OpenCode or later approved routes remain valid under a current task-specific selection/exception or user override; no silent substitution.

```text
HEALTHY_CODEX_QUOTA_ALONE_DOES_NOT_CREATE_WORK=YES
OPEN_MATERIAL_SEMANTIC_PLUS_USABLE_ALLOWED_CODEX=>CODEX_DEFAULT=YES
```

### T3 — COMPLEX / HIGH-CONSEQUENCE ENGINEERING

State machines, recovery, concurrency, durable authority, cross-layer semantics, difficult unresolved root cause or production-critical logic normally classify as `HIGH_CONSEQUENCE_AMBIGUOUS` while material ambiguity remains.

Use the strongest appropriate accepted semantic route for the exact task while preserving current user authority and executor constraints. If analysis reduces the work to a genuinely frozen bounded semantic core, Engineering Control may re-freeze that resulting task and classify it normally; consequence is not erased merely by reducing file count.

If the task can be decomposed into deterministic control-plane work plus one narrow semantic core, perform the deterministic work outside the model route and send only that core plus compact authority to the selected Writer.

### T4 — INDEPENDENT REVIEW / ADJUDICATION

Default final adjudicator:

```text
SURFACE=FRESH_ORDINARY_CHATGPT_WINDOW
CONTEXT=FRESH_SEPARATE_FROM_CONTROL_AND_IMPLEMENTATION
PERMISSION=READ_ONLY
MODEL=CURRENT_STRONGEST_APPROPRIATE_ORDINARY_CHATGPT_MODEL
CURRENT_PROFILE=GPT-5.6_SOL
REASONING=HIGH_OR_HIGHEST_APPROPRIATE
ORDINARY_CHATGPT_NEW_WINDOW=ROUTINE_DEFAULT
PROVIDER_NATIVE_OR_CODEX_REVIEWER=EXPLICIT_TASK_SPECIFIC_EXCEPTION_OR_OPT_IN
```

If exact GitHub artifacts/diffs and exact-head CI are sufficient, review them directly from the accepted independent surface. Do not spend model quota to reproduce evidence already canonically available. Automation never permits Writer-context reuse or a weaker-than-appropriate reviewer solely for convenience.

## 5. Quota-state behavior

Quota state constrains availability; it does not define task class.

### CODEX_QUOTA_STATE=HEALTHY

```text
DETERMINISTIC_MECHANICAL -> deterministic/GitHub
FROZEN_BOUNDED_SEMANTIC -> fresh ordinary ChatGPT Writer
OPEN_MATERIAL_SEMANTIC -> Codex default, model/reasoning right-sized
HIGH_CONSEQUENCE_AMBIGUOUS -> strongest appropriate accepted route
T4 -> fresh ordinary ChatGPT independent Reviewer by routine default
```

### CODEX_QUOTA_STATE=CONSTRAINED

Quota does not reclassify the task. `FROZEN_BOUNDED_SEMANTIC` continues to use its ordinary ChatGPT default. For an `OPEN_MATERIAL_SEMANTIC` or Codex-selected high-consequence task, Engineering Control determines whether the frozen Codex route remains viable; otherwise preserve the checkpoint and require a current task-specific alternative selection / user override rather than silently substituting.

```text
DETERMINISTIC_MECHANICAL -> deterministic/GitHub
FROZEN_BOUNDED_SEMANTIC -> fresh ordinary ChatGPT Writer
OPEN_MATERIAL_SEMANTIC -> CODEX if viable; otherwise EXPLICIT_TASK_SPECIFIC_ALTERNATIVE_REQUIRED
HIGH_CONSEQUENCE_AMBIGUOUS -> strongest currently authorized appropriate route; no silent downgrade
T4 -> fresh ordinary ChatGPT independent Reviewer by routine default
```

### CODEX_QUOTA_STATE=EXHAUSTED

Use GitHub/deterministic surfaces for non-semantic work. `FROZEN_BOUNDED_SEMANTIC` remains eligible for its ordinary ChatGPT default because that route is class-based rather than a Codex fallback. An open/material or high-consequence task that was frozen for Codex preserves its checkpoint and requires a current task-specific alternative selection / user override before switching executor. T4 remains the fresh ordinary ChatGPT routine default and is not coupled to Writer quota state.

Resource telemetry informs future routing but never creates work merely to consume remaining quota.

## 6. One coherent stage; no microtask tax

Do not compensate for a weaker/less certain model by splitting one coherent engineering stage into many one-file prompts that force repeated user relay, bootstrap context and review. Prefer:

```text
ONE COMPLETE HIGH-CONSTRAINT TASK PACKET
+ ONE COHERENT BOUNDED WRITER STAGE
+ IN-SCOPE VALIDATION
+ EXACT RESULT PACKET
```

Split only at real architecture, authority, worktree, model/harness or independence boundaries.

## 6A. Safe concurrency

```text
INDEPENDENT_TASKS + DISJOINT_WRITE_SURFACES + NO_DEPENDENCY
=> PARALLEL_EXECUTION_ALLOWED

SAME_WRITE_SURFACE OR SHARED_AUTHORITY OR CROSS_TASK_DEPENDENCY
=> SERIALIZE
```

Start with a small bounded number of parallel semantic tasks and increase only after observed CI/review/worktree stability. Quality and safety gates do not relax to consume quota faster.

## 7. Semantic Writer vs deterministic operator tail

A coding Writer spends reasoning on semantic code work, not routine transport.

Default:

```text
ENGINEERING CONTROL / ROUTER
-> frozen Task Packet
-> selected semantic Writer only when semantic mutation needs one
-> focused in-scope tests/self-check
-> exact artifact/evidence boundary
-> GITHUB CONNECTOR / GITHUB ACTIONS / NONMODEL DETERMINISTIC TOOL
   for already-authorized status/diff/artifact/publication/CI mechanics
-> exact-head CI
-> independent ChatGPT review
```

A model-backed operator is not the default for deterministic mechanics. Use one only when the remaining operation genuinely requires model interpretation that cannot be supplied by Engineering Control or deterministic tooling.

After Hermes is independently qualified, it may serve as a deterministic transport/operator where it reduces burden, but it remains subject to the same rule: it transports frozen authority and does not redesign, select a different model/reasoning state, declare independent PASS, Mark Ready, merge or deploy.

Do not force an operator handoff for a microscopic already-authorized tail if the current semantic Writer can finish it with less total burden, but do not start a fresh model turn merely to run deterministic mechanics.

## 7A. Workflow experiment telemetry

Use real-task evidence to decide `ADOPT | ADOPT_HYBRID | REVISE_AND_CONTINUE | REJECT_AND_RETURN` without precommitting either direction:

```text
ACCEPTED_ENGINEERING_OUTPUT
FIRST_PASS_CI_RESULT
INDEPENDENT_REVIEW_RESULT
SEMANTIC_REPAIR_OR_REWORK_COUNT
HUMAN_INTERVENTION_COUNT
HUMAN_COPY_PASTE_COUNT
TASK_START_LATENCY
WAITING_TIME
WALL_CLOCK_PER_ACCEPTED_TASK
CODEX_QUOTA_USED_WHEN_EXPOSED
TRANSPORT_OR_STREAM_INCIDENTS
DUPLICATE_ACTIONS
WORKTREE_CONFLICTS
AUTHORITY_DRIFT
```

Quota consumption by itself is never success.

## 8. Hermes insertion requirements

Hermes is an L3 transport/operator/orchestration layer, not a model-quality, routing or engineering-decision authority.

Its detailed candidate insertion/diagnostic/review-transport rules live in:

`governance/HERMES_TOOLING_V2_INSERTION_PLAN_2026-08-23.md`

Before first project use, the actual installed Hermes configuration and any schema/contract extension must receive independent acceptance under:

`governance/ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`

Hermes must expose checkpointed run state sufficient for human takeover. It must not become a black-box multi-step automation whose failure location cannot be reconstructed.

## 9. Frozen routing invariants

```text
QUALITY_FIRST=YES
HUMAN_RELAY_IS_A_COST=YES
QUOTA_STATE_IS_ROUTING_INPUT=YES
UNIVERSAL_EXECUTION_CLASSIFICATION_BEFORE_WRITER_DISPATCH=YES
DETERMINISTIC_MECHANICAL_MODEL_REQUIRED=NO
FROZEN_BOUNDED_SEMANTIC_DEFAULT_ORDINARY_CHATGPT_WRITER=YES
OPEN_MATERIAL_SEMANTIC_CODEX_DEFAULT_WHEN_AVAILABLE_AND_ALLOWED=YES
HIGH_CONSEQUENCE_AMBIGUOUS_STRONGEST_APPROPRIATE_ROUTE=YES
REVIEW_FAIL_NEW_TASK_THEN_UNIVERSAL_CLASSIFICATION=YES
CODEX_DESKTOP_PRE_MODEL_EXACT_BASE_WORKTREE_GATE=REQUIRED
TERMINAL_RESULT_EGRESS_FRESH_CANONICAL_READ=REQUIRED
GLM_5_3_ACCEPTED_TASK_SPECIFIC_WRITER=YES
DEEPSEEK_V4_PRO_ACCEPTED_TASK_SPECIFIC_WRITER=YES
NO_UNIVERSAL_OPUS_VS_GLM_VS_V4PRO_RANKING=YES
USER_OVERRIDE_PRESERVED=YES
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
T4_FINAL_REVIEW_FRESH_ORDINARY_CHATGPT_DEFAULT=YES
T4_PROVIDER_NATIVE_OR_CODEX_REVIEWER_TASK_SPECIFIC_EXCEPTION=YES
T4_WRITER_OR_CONTROL_CONTEXT_REUSE=PROHIBITED
T4_LOCAL_EVIDENCE_BUNDLE_BEFORE_WEAKER_LOCAL_FINAL_REVIEW=YES
WRITER_PASS_NE_INDEPENDENT_ACCEPTANCE=YES
HERMES_IS_OPERATOR_TRANSPORT_NOT_L1_OR_REVIEWER=YES
HERMES_CHECKPOINTED_RECOVERABLE_AUTOMATION_REQUIRED=YES
ROUTER_COVERAGE_ALL_MODEL_INVOCATIONS=YES
ROUTER_ROUTE_FREEZE_BEFORE_LAUNCH=YES
ROUTER_REQUESTED_ACTUAL_ATTESTATION_WHEN_EXPOSED=YES
ROUTER_INCIDENT_EXECUTOR_MODEL_AGNOSTIC=YES
NO_SILENT_FALLBACK_RETRY_RESUME=YES
ENGINEERING_PROACTIVE_ROUTER_INCIDENT_DISCOVERY=YES
```
