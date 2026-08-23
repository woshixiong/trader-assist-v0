# Trader Assist / Trade OS — Codex Current Model Profile

**Status:** REFRESHABLE SPECIALIZED GOVERNANCE PROPOSAL  
**Last first-party verification:** 2026-08-23  
**Stable path:** `governance/CODEX_CURRENT_MODEL_PROFILE.md`  
**Scope:** current Codex-visible model/reasoning/service-tier facts and project task-to-model guidance only.

This is **Layer C**. Routine model/version/rate changes update this file in place. They do not change the execution-class routing architecture, three peer L2 executors, version-independent Codex CLI workflow, one-primary-Writer rule, independent review, Task Packet/worktree contract or retained user gates.

Change Layer B only if durable Codex CLI/session/context/permission/evidence semantics change. Change Layer A only if execution-class or executor/authority routing changes.

---

## 1. Current first-party baseline

Fresh OpenAI first-party verification on 2026-08-23 establishes:

```text
FRONTIER_COMPLEX_MODEL=gpt-5.6-sol
BALANCED_MODEL=gpt-5.6-terra
COST_SENSITIVE_MODEL=gpt-5.6-luna
CURRENT_SPECIALIST_AGENTIC_CODING_MODEL=gpt-5.3-codex
UNSUFFIXED_ALIAS=gpt-5.6 -> gpt-5.6-sol
```

Current OpenAI general model guidance says to start with GPT-5.6 Sol for complex reasoning and coding, use Terra to balance intelligence and cost, and use Luna for cost-sensitive/high-volume work. The later GPT-5.6 launch also calls Sol OpenAI's best coding model yet and reports strong coding-agent/terminal results with improved token efficiency.

GPT-5.3-Codex remains a current supported specialist model optimized for agentic coding. Its dedicated model page still describes it as an agentic-coding model and the current Codex rate card still lists it. The same current rate-card material says Codex's built-in code-review feature uses GPT-5.3-Codex. Those facts make it a real current specialist route, but **not** the project's default Writer model: the later GPT-5.6 guidance supersedes the older February 2026 launch claim for general best-model selection.

Current Codex availability material says Terra is available in Codex for Free/Go and Sol/Terra/Luna for eligible paid plans. GPT-5.3-Codex was launched across paid Codex surfaces and remains present in current Codex rate material. Exact local/account/model-picker availability must still be mechanically verified at dispatch.

Current minimum Codex CLI version for GPT-5.6 access is `0.144.0`. This is a **current compatibility floor**, not a permanently pinned project version.

The current public `@openai/codex` npm distribution observed on 2026-08-23 is `0.149.0`. This is a moving distribution fact, not a project pin. A real Writer dispatch must run `codex --version` mechanically and use the actually installed/current surface rather than assuming this snapshot is still latest.

Current public GPT-5.6 Sol/Terra/Luna model pages report:

```text
CONTEXT_WINDOW=1,050,000
MAX_OUTPUT=128,000
KNOWLEDGE_CUTOFF=2026-02-16
```

The current GPT-5.3-Codex model page reports:

```text
CONTEXT_WINDOW=400,000
MAX_OUTPUT=128,000
KNOWLEDGE_CUTOFF=2025-08-31
REASONING=low|medium|high|xhigh
```

Do not inherit GPT-5.6 context/reasoning semantics into GPT-5.3-Codex or vice versa. Large context is capacity, not a target; project context remains the smallest complete authority/code context needed for the bounded task.

---

## 2. Reasoning controls — distinguish product availability from documented CLI invocation controls

Current GPT-5.6 provider guidance supports:

```text
none | low | medium | high | xhigh | max
```

Current OpenAI GPT-5.6 product material also states that GPT-5.6 users in Codex can use `max`, and that `ultra` is available in Codex for eligible Plus-and-higher plans. However, the current public Codex config reference still documents the task/config field `model_reasoning_effort` as:

```text
minimal | low | medium | high | xhigh
```

Therefore product-level availability must not be confused with a stable documented one-paste CLI/config invocation contract.

Project default task-local set for GPT-5.6:

```text
DEFAULT_ALLOWED_TASK_EFFORTS=low|medium|high|xhigh
MAX=PRODUCT_AVAILABLE_BUT_VERIFY_CURRENT_INSTALLED_CODEX_CLI_TASK_LOCAL_SEAM_BEFORE_ENCODING
ULTRA=PRODUCT_AVAILABLE_ON_ELIGIBLE_PLANS_BUT_VERIFY_CURRENT_INSTALLED_CODEX_CLI_TASK_LOCAL_SEAM_BEFORE_ENCODING
PRO_OR_SOL_PRO=DO_NOT_ASSUME_AS_CODEX_CLI_MODEL_ID_OR_TASK_LOCAL_CONTROL_WITHOUT_CURRENT_CODEX_SPECIFIC_EVIDENCE
```

For GPT-5.3-Codex, use only its currently documented `low|medium|high|xhigh` set unless a newer first-party/current installed Codex surface explicitly changes that contract. Do not apply GPT-5.6 `max`/`ultra` semantics to it by inheritance.

Do not transfer API-only controls such as persisted reasoning, Pro model IDs or explicit cache controls into Codex CLI unless the current installed Codex surface independently exposes them.

Starting heuristic:

```text
LOW    = narrow/obvious/cheaply validated
MEDIUM = normal bounded coding default
HIGH   = hard multi-step implementation/debugging
XHIGH  = exceptional difficult/high-consequence bounded work
MAX    = GPT-5.6 exceptional + current installed task-local surface verified
ULTRA  = GPT-5.6 exceptional + current installed task-local surface verified + eligible plan
```

Choose the lowest effort likely to finish correctly in one pass, not the lowest effort that can merely start. OpenAI's GPT-5.6 migration guidance recommends comparing the existing effort with one level lower on representative work; use real Trader Assist tasks/evidence rather than synthetic paid benchmarks.

Model/reasoning are frozen before the Writer starts. No silent mid-stage changes.

---

## 3. Current project model-selection matrix

First ask whether Codex is needed at all. GitHub-only publication and deterministic local mechanics normally use GPT Control / deterministic Terminal rather than a coding Agent.

When `CODEX_CLI` is genuinely required:

### GPT-5.6 Luna

Use for highly bounded, low-ambiguity coding with strong deterministic validation, such as repetitive narrow code transformations or low-risk fixture/test maintenance.

```text
LUNA_START=medium
LUNA_LOW=only_when_exceptionally_clear_and_cheaply_validated
```

If no semantic code judgment is required, route to deterministic Terminal instead of Luna.

### GPT-5.6 Terra

Default starting model for ordinary well-bounded coding when the route/invariants are already frozen:

- normal bounded feature work;
- ordinary bug fixes;
- contained refactors;
- straightforward multi-file implementation with explicit tests.

```text
TERRA_START=medium
TERRA_HARD_BOUND=high_when_still_clearly_in_balanced_model_class
```

### GPT-5.6 Sol

Use when capability/reliability dominates model cost:

- difficult root-cause debugging;
- cross-layer implementation with important invariants;
- unfamiliar/complex code paths;
- security/authority/execution-boundary work;
- hard local semantic adjudication when Codex is explicitly selected;
- model-fit uncertainty where a weak first attempt is likely to cause rework.

```text
SOL_START=medium_or_high
SOL_XHIGH=exceptional
```

### GPT-5.3-Codex — current specialist, not project default

Keep GPT-5.3-Codex as a **specialist/empirical candidate**, not as an automatically preferred Writer merely because it has `Codex` in the model name.

Use/consider it only when at least one is true:

- the user/L1 explicitly selects it and the current local Codex surface exposes it;
- a bounded agentic-coding workload has recent real project evidence showing better accepted-work-per-credit/time than the chosen GPT-5.6 alternative;
- the project deliberately invokes a Codex-native feature whose current first-party contract uses GPT-5.3-Codex, such as the current built-in code-review feature.

Project review policy remains separate: when exact GitHub artifacts/diffs and exact-head CI suffice, a separate ordinary GPT review window using the strongest appropriate reasoning is preferred over spending a Codex review turn. The fact that Codex's own built-in review feature currently uses GPT-5.3-Codex does not override that routing rule.

Do not claim GPT-5.3-Codex is better than GPT-5.6 for current Trader Assist Writer work without representative real evidence. Its February launch called it the most capable agentic coding model at that time; the later July GPT-5.6 launch explicitly calls GPT-5.6 Sol OpenAI's best coding model yet and current general model guidance recommends the GPT-5.6 family.

### Max / Ultra / Pro-like / subagent-heavy behavior

```text
DEFAULT=OFF
```

Enable only after current installed Codex-surface verification and an explicit L1 reason that the bounded task benefits enough to justify added tokens/credits/latency. Parallel exploration must not create competing mutation authority. Current product availability alone does not authorize Engineering to invent a CLI flag/config value that the current documented/installed surface does not expose.

---

## 4. Standard versus Fast

Current first-party materials establish that Fast is a latency/service-tier feature with a usage premium; it is **not an intelligence upgrade**. Current public surfaces do not present one single universal speed/credit multiplier for every plan/account, so this profile deliberately does not freeze a universal multiplier.

Exact speed/rate for the user's current Codex product/plan must be verified when Fast is actually considered.

```text
CODEX_SERVICE_TIER_DEFAULT=STANDARD
FAST_MODE_DEFAULT=OFF
FAST_ENABLE_ONLY_FOR_REAL_TIME_CRITICAL_NEED=YES
```

Do not pay a latency premium for routine engineering.

---

## 5. Current Codex credit/cache facts

The current OpenAI Codex rate card checked on 2026-08-23 reports these token-based credits per 1M tokens for the relevant current choices:

```text
MODEL              INPUT    CACHED_INPUT    OUTPUT
GPT-5.6 Sol         125      12.5            750
GPT-5.6 Terra       50       5               300
GPT-5.6 Luna        5        0.5             30
GPT-5.3-Codex       43.75    4.375           350
```

The same current rate material states Codex does not charge for cache writes. These values are **refreshable commercial facts**, not architecture; plan/workspace exceptions and future changes must not be inferred from this snapshot.

Cost comparison must use total accepted-work economics rather than input price alone. GPT-5.3-Codex currently has lower input/cached-input credit rates than Terra but a higher output credit rate, while GPT-5.6 has newer capability/efficiency guidance. Do not infer a universal cheaper/better winner without real task evidence.

Direct API economics are a different surface. Current API pages report different dollar prices and cache/write/long-context rules. Therefore:

```text
DO_NOT_TRANSFER_API_BILLING_TO_CHATGPT_CODEX=YES
DO_NOT_TRANSFER_CHATGPT_CODEX_CREDITS_TO_API_KEY_USE=YES
```

The normal local route uses the user's existing authenticated Codex CLI. Never request/expose an API key merely to optimize cache behavior.

---

## 6. Cache/context policy on current Codex CLI

Current Codex JSONL provides passive cached-input usage evidence. The current CLI contract checked for this profile does not establish task-level explicit API-style `prompt_cache_key` or cache-breakpoint controls, so do not invent them.

Use:

```text
SMALL_STABLE_ROOT_AGENTS
+ ENGINEERING_CONTROL_READS_FULL_SPECIALIZED_PROFILES_BEFORE_DISPATCH
+ DOWNSTREAM_CODEX_DOES_NOT_REREAD_FULL_PROFILES_WHEN_FROZEN_PACKET_IS_COMPLETE
+ STABLE_CONTROL_PREFIX
+ MUTABLE_TASK_EVIDENCE_TAIL
+ STABLE_MODEL_TOOL_PERMISSION_SHAPE_WITHIN_ONE_STAGE
+ EXACT_SESSION_RESUME_ONLY_WHEN_SEMANTICALLY_VALID
+ PASSIVE_CACHED_INPUT_MEASUREMENT
```

For a downstream Writer, the preferred compact authority package is:

```text
root AGENTS.md
+ complete frozen Task Packet
+ exact task-specific authority/code
+ additional canonical sections only when explicitly required or needed to resolve genuine ambiguity
```

Do not paste or reread the full project history/governance corpus on every run merely for completeness.

If a session accumulates stale/unrelated history, start a clean session at the next valid boundary rather than retaining it just for cache reuse.

No cache-hit percentage or synthetic paid cache benchmark is an acceptance gate.

---

## 7. Current task-local Codex controls

Current Codex first-party CLI/config material verifies task-local controls for model, working directory, sandbox, approval/config overrides and JSON execution. The version-independent core owns the exact invocation policy.

Project requirement:

```text
L1_FROZEN_MODEL_REASONING_MUST_BE_ENCODED_PER_INVOCATION=YES
DO_NOT_RELY_ON_REMEMBERED_GLOBAL_MODEL_DEFAULT=YES
GLOBAL_~/.codex/config.toml_MUTATION_FOR_ONE_TASK=NO_BY_DEFAULT
```

Before a real task, mechanically verify installed Codex version and effective selected model/reasoning/sandbox surface before mutation. Do not spend a separate model request solely to qualify it.

---

## 8. Model-profile refresh procedure

When a newer Codex/OpenAI model or material rate/service behavior becomes relevant:

```text
VERIFY CURRENT LOCAL CODEX VERSION/MODEL SURFACE
→ CHECK CURRENT FIRST-PARTY MODEL + CODEX CLI/CONFIG DOCS
→ CHECK CURRENT AVAILABILITY/RATE/SPEED DOCS WHERE RELEVANT
→ VERIFY ONLY ACTUALLY EXPOSED CONTROLS
→ COMPARE WITH RECENT REAL TRADER ASSIST CODEX EVIDENCE
→ UPDATE THIS FILE IN PLACE
```

Default change scope:

```text
ONLY governance/CODEX_CURRENT_MODEL_PROFILE.md
```

Do not create a new project switching constitution for each new GPT/Codex model.

---

## 9. Real-task observability

Collect naturally available evidence, without extra model turns:

```text
CODEX_VERSION
MODEL
REASONING_EFFORT
SERVICE_TIER
SESSION_ID / NEW_OR_RESUME_EXACT
INPUT_TOKENS
CACHED_INPUT_TOKENS
OUTPUT_TOKENS
REASONING_OUTPUT_TOKENS where exposed
ELAPSED_TIME
MODEL_RETRY_COUNT
ENGINEERING_REPAIR_REWORK_COUNT
FINAL_TASK_ACCEPTANCE
```

Use accumulated real-task evidence to refine the Luna/Terra/Sol/GPT-5.3-Codex boundary. Token efficiency is judged by accepted useful work per total token/credit/rework/review cost, not by a single cache ratio.

---

## 10. Current frozen snapshot

```text
PROFILE_LAST_VERIFIED=2026-08-23
CURRENT_CODEX_MODEL_FAMILY=GPT-5.6
CURRENT_SOL=gpt-5.6-sol
CURRENT_TERRA=gpt-5.6-terra
CURRENT_LUNA=gpt-5.6-luna
CURRENT_SPECIALIST_AGENTIC_CODING_MODEL=gpt-5.3-codex
GPT_5_3_CODEX_PROJECT_DEFAULT=NO
GPT_5_3_CODEX_BUILTIN_CODE_REVIEW_CURRENT_USE=YES_PER_CURRENT_RATE_CARD
CURRENT_PUBLIC_CODEX_NPM_LATEST_OBSERVED=0.149.0
MIN_GPT_5_6_CODEX_CLI_COMPATIBILITY_FLOOR=0.144.0
EVERYDAY_BOUNDED_CODEX_START=TERRA_MEDIUM_WHEN_CLEARLY_SUFFICIENT
UNCERTAIN_MODEL_FIT_START=SOL_MEDIUM
HARD_COMPLEX_START=SOL_HIGH
LUNA=ONLY_LOW_AMBIGUITY_STRONGLY_VALIDATED_CODE_TASKS
XHIGH=EXCEPTIONAL
MAX=GPT_5_6_PRODUCT_AVAILABLE_BUT_VERIFY_CURRENT_INSTALLED_TASK_LOCAL_CLI_SEAM_BEFORE_USE
ULTRA=GPT_5_6_PRODUCT_AVAILABLE_ON_ELIGIBLE_PLANS_BUT_VERIFY_CURRENT_INSTALLED_TASK_LOCAL_CLI_SEAM_BEFORE_USE
PRO_OR_SOL_PRO=DO_NOT_ASSUME_AS_CLI_MODEL_ID_WITHOUT_CODEX_SPECIFIC_EVIDENCE
FAST_MODE_DEFAULT=OFF
CACHE_METRIC=PASSIVE_CACHED_INPUT_TOKENS
FULL_SPECIALIZED_PROFILE_RELOAD_IN_DOWNSTREAM_WRITER=NO_BY_DEFAULT
MODEL_UPGRADE_DEFAULT_CHANGE_SCOPE=THIS_FILE_ONLY
```