# Trader Assist / Trade OS — Codex Current Model Profile

**Status:** REFRESHABLE SPECIALIZED GOVERNANCE PROPOSAL  
**Last first-party verification:** 2026-08-20  
**Stable path:** `governance/CODEX_CURRENT_MODEL_PROFILE.md`  
**Scope:** current Codex-visible model/reasoning/service-tier facts and project task-to-model guidance only.

This is **Layer C**. Routine model/version/rate changes update this file in place. They do not change the execution-class routing architecture, three peer L2 executors, version-independent Codex CLI workflow, one-primary-Writer rule, independent review, Task Packet/worktree contract or retained user gates.

Change Layer B only if durable Codex CLI/session/context/permission/evidence semantics change. Change Layer A only if execution-class or executor/authority routing changes.

---

## 1. Current first-party baseline

Fresh OpenAI first-party verification on 2026-08-20 establishes:

```text
FRONTIER_COMPLEX_MODEL=gpt-5.6-sol
BALANCED_MODEL=gpt-5.6-terra
COST_SENSITIVE_MODEL=gpt-5.6-luna
UNSUFFIXED_ALIAS=gpt-5.6 -> gpt-5.6-sol
```

Current OpenAI guidance: Sol is the frontier choice for complex professional work/reasoning/coding; Terra balances intelligence and cost; Luna is the low-cost/high-volume choice. If model fit is genuinely uncertain, current OpenAI model guidance says to start with Sol rather than assume a smaller model is sufficient.

Current Codex availability material says Terra is available in Codex for Free/Go and Sol/Terra/Luna for eligible paid plans. Availability is still mechanically verified at dispatch because account/workspace rollout can differ.

Current minimum Codex CLI version for GPT-5.6 access is `0.144.0`. This is a **current compatibility floor**, not a permanently pinned project version.

Current public Sol/Terra/Luna model pages report:

```text
CONTEXT_WINDOW=1,050,000
MAX_OUTPUT=128,000
KNOWLEDGE_CUTOFF=2026-02-16
```

Large context is capacity, not a target. Project context remains the smallest complete authority/code context needed for the bounded task.

---

## 2. Reasoning controls — use the verified intersection

Current GPT-5.6 provider guidance supports:

```text
none | low | medium | high | xhigh | max
```

Current Codex documentation/source surfaces are evolving and are not assumed to expose every API-only reasoning mode identically. The project default safe task-local set is:

```text
DEFAULT_ALLOWED_TASK_EFFORTS=low|medium|high|xhigh
MAX=VERIFY_CURRENT_CODEX_CLI_SURFACE_BEFORE_USE
ULTRA_OR_PRO_LIKE_MODE=VERIFY_CURRENT_CODEX_SURFACE_BEFORE_USE
```

Do not transfer API-only controls such as persisted reasoning, Pro mode or explicit cache controls into Codex CLI unless the current Codex surface independently exposes them.

Starting heuristic:

```text
LOW    = narrow/obvious/cheaply validated
MEDIUM = normal bounded coding default
HIGH   = hard multi-step implementation/debugging
XHIGH  = exceptional difficult/high-consequence bounded work
MAX    = exceptional + current-surface verified only
```

Choose the lowest effort likely to finish correctly in one pass, not the lowest effort that can merely start. OpenAI's GPT-5.6 migration guidance specifically recommends comparing the existing effort with one level lower on representative work; use real Trader Assist tasks/evidence rather than synthetic paid benchmarks.

Model/reasoning are frozen before the Writer starts. No silent mid-stage changes.

---

## 3. Current project model-selection matrix

First ask whether Codex is needed at all. GitHub-only publication and deterministic local mechanics normally use GPT Control / deterministic Terminal rather than a coding Agent.

When `CODEX_CLI` is genuinely required:

### Luna

Use for highly bounded, low-ambiguity coding with strong deterministic validation, such as repetitive narrow code transformations or low-risk fixture/test maintenance.

```text
LUNA_START=medium
LUNA_LOW=only_when_exceptionally_clear_and_cheaply_validated
```

If no semantic code judgment is required, route to deterministic Terminal instead of Luna.

### Terra

Default starting model for ordinary well-bounded coding when the route/invariants are already frozen:

- normal bounded feature work;
- ordinary bug fixes;
- contained refactors;
- straightforward multi-file implementation with explicit tests.

```text
TERRA_START=medium
TERRA_HARD_BOUND=high_when_still_clearly_in_balanced_model_class
```

### Sol

Use when capability/reliability dominates model cost:

- difficult root-cause debugging;
- cross-layer implementation with important invariants;
- unfamiliar/complex code paths;
- security/authority/execution-boundary work;
- hard local semantic adjudication/review when Codex is explicitly selected;
- model-fit uncertainty where a weak first attempt is likely to cause rework.

```text
SOL_START=medium_or_high
SOL_XHIGH=exceptional
```

### Max / Ultra / Pro-like / subagent-heavy behavior

```text
DEFAULT=OFF
```

Enable only after current Codex-surface verification and an explicit L1 reason that the bounded task benefits enough to justify added tokens/credits/latency. Parallel exploration must not create competing mutation authority.

---

## 4. Standard versus Fast

Current first-party materials establish that Fast is a latency/service-tier feature with a usage premium; it is **not an intelligence upgrade**. Current public surfaces do not present one single universal speed/credit multiplier for every plan/account, so this profile deliberately does not freeze a universal multiplier.

Current first-party examples include faster GPT-5.6 inference and current token-based Enterprise material showing a GPT-5.6 Fast premium over Standard. Exact speed/rate for the user's current Codex product/plan must be verified when Fast is actually considered.

```text
CODEX_SERVICE_TIER_DEFAULT=STANDARD
FAST_MODE_DEFAULT=OFF
FAST_ENABLE_ONLY_FOR_REAL_TIME_CRITICAL_NEED=YES
```

Do not pay a latency premium for routine engineering.

---

## 5. Current Codex credit/cache facts

The current OpenAI Codex rate card checked on 2026-08-20 reports these token-based credits per 1M tokens for the current general rate-card path:

```text
MODEL              INPUT    CACHED_INPUT    OUTPUT
GPT-5.6 Sol         125      12.5            750
GPT-5.6 Terra       50       5               300
GPT-5.6 Luna        5        0.5             30
```

The same current rate material states Codex does not charge for cache writes. These values are **refreshable commercial facts**, not architecture; plan/workspace exceptions and future changes must not be inferred from this snapshot.

Direct API economics are a different surface. Current GPT-5.6 API pages report different dollar prices and cache-write/long-context rules. Therefore:

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

Use accumulated real-task evidence to refine the Luna/Terra/Sol boundary. Token efficiency is judged by accepted useful work per total token/credit/rework/review cost, not by a single cache ratio.

---

## 10. Current frozen snapshot

```text
PROFILE_LAST_VERIFIED=2026-08-20
CURRENT_CODEX_MODEL_FAMILY=GPT-5.6
CURRENT_SOL=gpt-5.6-sol
CURRENT_TERRA=gpt-5.6-terra
CURRENT_LUNA=gpt-5.6-luna
EVERYDAY_BOUNDED_CODEX_START=TERRA_MEDIUM_WHEN_CLEARLY_SUFFICIENT
UNCERTAIN_MODEL_FIT_START=SOL_MEDIUM
HARD_COMPLEX_START=SOL_HIGH
LUNA=ONLY_LOW_AMBIGUITY_STRONGLY_VALIDATED_CODE_TASKS
XHIGH=EXCEPTIONAL
MAX=VERIFY_CURRENT_CODEX_CLI_SURFACE_BEFORE_USE
FAST_MODE_DEFAULT=OFF
CACHE_METRIC=PASSIVE_CACHED_INPUT_TOKENS
FULL_SPECIALIZED_PROFILE_RELOAD_IN_DOWNSTREAM_WRITER=NO_BY_DEFAULT
MODEL_UPGRADE_DEFAULT_CHANGE_SCOPE=THIS_FILE_ONLY
```