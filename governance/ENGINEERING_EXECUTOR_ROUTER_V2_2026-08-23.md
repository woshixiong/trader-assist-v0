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

## 4. Task classes and candidate set

### T0 — MECHANICAL / OPERATOR

Examples: repo search, grep, log extraction, bounded tests, status/diff/evidence, deterministic formatting, already-authorized commit/push, repetitive file operations.

Default:

```text
OPENCODE + OPUS_4_6
```

Optional fast/high-volume Scout:

```text
OPENCODE + DEEPSEEK_V4_FLASH
```

Trae GLM-5.3 and DeepSeek V4 Pro are capable but normally unnecessary for T0 unless the user overrides or the task unexpectedly requires their specific harness.

### T1 — LOW-RISK BOUNDED CODING

Characteristics: frozen scope, simple logic, strong deterministic validation, low blast radius.

Default candidate:

```text
OPENCODE + OPUS_4_6
```

Also valid:

```text
TRAE + GLM_5_3
TRAE + DEEPSEEK_V4_PRO
```

Use Trae here when the user chooses it, the task shape specifically favors it, or OpenCode is unavailable. Do not consume Codex quota by default for work that a free strong model plus decisive tests can reliably close.

### T2 — MATERIAL NORMAL ENGINEERING

Examples: normal feature implementation, meaningful bug fix, bounded multi-file implementation, nontrivial refactor.

If Codex quota is healthy:

```text
DEFAULT = CODEX_CLI + GPT_5_6_TERRA
UPGRADE = CODEX_CLI + GPT_5_6_SOL when complexity/consequence warrants
```

Alternative first-class Writers, especially when Codex is constrained/exhausted or the user overrides:

```text
OPENCODE + OPUS_4_6
TRAE + GLM_5_3
TRAE + DEEPSEEK_V4_PRO
```

Known task-fit guidance:

- **GLM-5.3:** highly constrained complete Task Packet; frozen scope/invariants; long coherent agentic implementation; terminal-heavy implement→test→repair loop.
- **Opus 4.6:** large-codebase comprehension; debugging; refactoring; deep code-context reasoning; tasks where flexible interpretation across existing code is valuable.
- **DeepSeek V4 Pro:** broad repo investigation; repo-wide/full-stack implementation; larger-context root-cause discovery; clean alternative route when another Writer stalls.

When these fits do not distinguish the candidates, prefer free Opus 4.6 as the tie-breaker while available. The user may override.

### T3 — COMPLEX / HIGH-CONSEQUENCE ENGINEERING

Examples: state machines, recovery, idempotency, concurrency, durable authority, cross-layer semantics, hard root cause, production-critical logic.

If Codex quota is healthy:

```text
DEFAULT = CODEX_CLI + GPT_5_6_SOL
```

If Codex is unavailable/constrained enough to preserve remaining quota, or the user overrides, all three are first-class candidates:

```text
OPENCODE + OPUS_4_6
TRAE + GLM_5_3
TRAE + DEEPSEEK_V4_PRO
```

Choose by the known task-fit guidance above. Do not manufacture a universal ranking among these three without representative Trader Assist evidence.

### T4 — INDEPENDENT REVIEW / ADJUDICATION

Default final adjudicator:

```text
SURFACE = SEPARATE ORDINARY CHATGPT REVIEW WINDOW
MODEL = strongest appropriate available model
REASONING = highest appropriate level
```

If exact GitHub artifacts/diffs plus exact-head CI are sufficient, review directly through GitHub/connectors. Do not spend a coding-agent turn merely to reproduce a GitHub-only independent review.

If local execution/inspection evidence is required, the preferred route is **not** to downgrade the final Reviewer to a weaker local coding model. Prefer:

```text
DETERMINISTIC TERMINAL / LOCAL TOOLING
-> exact hash-manifested review bundle
-> upload bundle to a NEW independent strongest-ChatGPT review window
-> strongest ChatGPT performs final review/adjudication
```

Use `$trade-os-independent-review-bundle` for this path when available. Before Hermes qualification the user may upload the exact bundle manually. After Hermes is independently qualified, Hermes may automate deterministic bundle generation/verification and exact upload/prompt transport under its checkpointed review-transport profile.

A separate local coding model is an exceptional evidence-acquisition route only when deterministic bundle generation cannot provide the necessary local observation. Eligible local evidence providers include:

```text
CODEX_CLI + appropriate strong Codex model
OPENCODE + OPUS_4_6
TRAE + GLM_5_3
TRAE + DEEPSEEK_V4_PRO
```

Their output is evidence for the independent ChatGPT adjudicator unless L1/user explicitly freezes a different independently accepted review route. Writer self-review never becomes independent acceptance.

## 5. Quota-state behavior

### CODEX_QUOTA_STATE=HEALTHY

```text
T0 -> OpenCode Opus / Flash
T1 -> OpenCode Opus; GLM/V4 Pro valid alternatives
T2 -> Codex Terra/Sol default; Opus/GLM/V4 Pro alternatives
T3 -> Codex Sol default; Opus/GLM/V4 Pro alternatives
T4 -> strongest independent ChatGPT; local evidence bundle when needed
```

### CODEX_QUOTA_STATE=CONSTRAINED

Move T0/T1 entirely off Codex. Move routine T2 to Opus/GLM/V4 Pro unless Codex has a material expected-quality advantage. Preserve Codex Sol preferentially for T3/high-value hard work. T4 remains strongest independent ChatGPT; local evidence generation should normally be deterministic rather than consuming scarce Codex quota.

### CODEX_QUOTA_STATE=EXHAUSTED

Select Opus 4.6 vs GLM-5.3 vs DeepSeek V4 Pro by task fit for local Writer work. Trae points are a secondary factor, not a reason to accept lower expected quality. If quality difference is not decisive and Opus is available free, prefer Opus. T4 final adjudication remains strongest independent ChatGPT and does not depend on Codex quota.

## 6. One coherent stage; no microtask tax

Do not compensate for a weaker/less certain model by splitting one coherent engineering stage into many one-file prompts that force repeated user relay, bootstrap context and review. Prefer:

```text
ONE COMPLETE HIGH-CONSTRAINT TASK PACKET
+ ONE COHERENT BOUNDED WRITER STAGE
+ IN-SCOPE VALIDATION
+ EXACT RESULT PACKET
```

Split only at real architecture, authority, worktree, model/harness or independence boundaries.

## 7. Semantic Writer vs operator tail

A coding Writer should spend reasoning on semantic code work, not routine transport.

Before Hermes is qualified:

```text
ENGINEERING CONTROL / ROUTER
-> frozen Task Packet
-> semantic Writer
-> in-scope tests/self-check
-> exact artifact/evidence boundary
-> optional FREE OPERATOR (normally OpenCode)
   for remaining deterministic commit/push/evidence mechanics when useful
-> exact-head CI
-> independent ChatGPT review
```

After Hermes is independently qualified, Hermes becomes the preferred transport/operator layer when doing so reduces total burden:

```text
ENGINEERING CONTROL / ROUTER
-> frozen lossless Task Packet
-> HERMES
   -> dispatch selected semantic Writer
   -> wait / checkpoint / collect result
   -> perform remaining authorized deterministic mechanics
   -> commit/push/CI observation only when explicitly frozen
   -> build/transport review bundle when T4 needs local evidence
-> strongest independent ChatGPT review
```

Do **not** force an operator handoff when the current Writer can safely finish a tiny already-authorized mechanical tail with less total burden. Conversely, do not spend a fresh Codex reasoning turn on mechanics that a qualified Hermes operator can deterministically perform. The decision criterion is total engineering cost and accepted-work latency, not ceremonial role boundaries.

The operator may execute already-frozen actions; it may not redesign, widen scope, choose a different model/reasoning/Web-Search state, declare independent PASS, Mark Ready, merge or deploy.

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
```