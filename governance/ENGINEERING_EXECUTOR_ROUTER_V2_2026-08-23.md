# Trader Assist / Trade OS — Engineering Executor Router V2

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
ROUTER_SELECTION_CLASS=DETERMINISTIC|BOUNDED_SEMANTIC|HIGH_COMPLEXITY_SEMANTIC|INDEPENDENT_REVIEW
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

- OpenCode Opus 4.6, Sonnet 4.6 and DeepSeek V4 Flash have zero marginal quota cost.
- OpenCode default free Writer is **Claude Opus 4.6** when available.
- Sonnet 4.6 is a valid fallback/task-specific alternative, not the default merely to save free tokens.
- DeepSeek V4 Flash is mainly Scout/triage/high-volume mechanical work.
- Ox Alpha and other temporary free models are opportunistic only and do not become durable routing dependencies.
- Trae GLM-5.3 and Trae DeepSeek V4 Pro consume points, but points are a secondary tie-breaker when a material quality difference is expected.

## 4. Surface-first routing and task classes

Router selection is **surface-first**, then model-fit. Quota health never promotes a task to Codex.

Default priority:

```text
1 AUTHORITATIVE GITHUB / PROVIDER-NATIVE / DETERMINISTIC TOOL
2 ENGINEERING CONTROL DIRECT ACTION WHEN NO CODING AGENT IS NEEDED
3 ACCEPTED NON-CODEX MODEL WRITER WHEN SEMANTIC MUTATION NEEDS AN AGENT
4 CODEX ONLY WHEN THE REMAINING SEMANTIC IMPLEMENTATION MATERIALLY NEEDS CODEX CAPABILITY
```

No prose proof of Codex necessity is required. Engineering Control classifies the task and applies this order.

### T0 — MECHANICAL / OPERATOR

Examples: repo search, GitHub state, log extraction, tests, CI, status/diff/evidence, deterministic formatting, artifact handling, already-authorized publication mechanics.

```text
DEFAULT=GITHUB_CONNECTOR_OR_GITHUB_ACTIONS_OR_DETERMINISTIC_TOOL
MODEL_WRITER_REQUIRED=NO
CODEX=NO
```

Use OpenCode/another model only when the operation itself genuinely needs model interpretation; do not invoke a model merely to run commands.

### T1 — LOW-RISK BOUNDED CODING

Frozen scope, simple logic, decisive validation, low blast radius.

Preferred routes:
- Engineering Control direct GitHub edit only for governance/docs, Issue/PR metadata, workflow metadata or mechanical configuration whose semantics are already frozen and deterministically checkable;
- application/source semantic logic requires an accepted semantic Writer by default;
- otherwise use OpenCode Opus 4.6 or a fit Trae writer.

```text
CODEX_DEFAULT=NO
```

### T2 — MATERIAL NORMAL ENGINEERING

Normal feature implementation, meaningful bug fix, bounded multi-file implementation or nontrivial refactor.

First use GitHub/Engineering Control for all control-plane discovery, exact-state work and validation setup. If a semantic Writer is required, select among accepted non-Codex Writers by task fit. Codex is eligible only when Engineering Control determines that the remaining semantic implementation materially benefits from Codex-level coding/agentic capability.

Known non-Codex fits remain:
- Opus 4.6: large-codebase comprehension, debugging and refactoring;
- GLM-5.3: highly constrained complete packets and long implement/test loops;
- DeepSeek V4 Pro: broad repo investigation and larger-context root-cause work.

```text
HEALTHY_CODEX_QUOTA_ALONE_DOES_NOT_SELECT_CODEX=YES
```

### T3 — COMPLEX / HIGH-CONSEQUENCE ENGINEERING

State machines, recovery, concurrency, durable authority, cross-layer semantics, difficult root cause or production-critical logic.

Use the strongest appropriate accepted semantic Writer for the exact task. Codex Sol is a first-class option when its capability is materially needed, but is **not** the default merely because quota remains. Opus 4.6, GLM-5.3 and DeepSeek V4 Pro remain first-class alternatives when their task fit is sufficient.

If the task can be decomposed into deterministic control-plane work plus one narrow semantic core, perform the deterministic work outside Codex and send only that core plus compact authority to the selected Writer.

### T4 — INDEPENDENT REVIEW / ADJUDICATION

Default final adjudicator:

```text
SURFACE=SEPARATE ORDINARY CHATGPT REVIEW WINDOW
MODEL=STRONGEST APPROPRIATE AVAILABLE
REASONING=HIGHEST APPROPRIATE
```

If exact GitHub artifacts/diffs and exact-head CI are sufficient, review them directly. Do not spend Codex quota to reproduce a GitHub-only review.

## 5. Quota-state behavior

Quota state constrains availability; it does not define task class.

### CODEX_QUOTA_STATE=HEALTHY

```text
T0 -> deterministic/GitHub
T1 -> Engineering Control or accepted non-Codex Writer
T2 -> accepted fit Writer; Codex only if selected for the semantic core
T3 -> strongest fit Writer; Codex eligible when materially needed
T4 -> strongest independent ChatGPT
```

### CODEX_QUOTA_STATE=CONSTRAINED

```text
NEW_NONESSENTIAL_CODEX_DISPATCH=HOLD
T0/T1=NO_CODEX
T2=NORMALLY_NON_CODEX
T3=CODEX_ONLY_FOR_IRREDUCIBLE_HIGH_VALUE_SEMANTIC_CORE
T4=INDEPENDENT_CHATGPT
```

### CODEX_QUOTA_STATE=EXHAUSTED

Use GitHub/deterministic surfaces and accepted non-Codex Writers. T4 remains strongest independent ChatGPT.

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
OPENCODE_OPUS_DEFAULT_FREE_MODEL=YES
GLM_5_3_FIRST_CLASS_ADVANCED_WRITER=YES
DEEPSEEK_V4_PRO_FIRST_CLASS_ADVANCED_WRITER=YES
NO_UNIVERSAL_OPUS_VS_GLM_VS_V4PRO_RANKING=YES
USER_OVERRIDE_PRESERVED=YES
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
T4_FINAL_REVIEW_STRONGEST_CHATGPT_DEFAULT=YES
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
