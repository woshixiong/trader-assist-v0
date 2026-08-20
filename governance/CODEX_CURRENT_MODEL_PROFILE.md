# Trader Assist / Trade OS — Codex Current Model Profile

**Status:** REFRESHABLE SPECIALIZED GOVERNANCE PROPOSAL  
**Last first-party verification:** 2026-08-20  
**Stable path:** `governance/CODEX_CURRENT_MODEL_PROFILE.md`  
**Scope:** current Codex-visible model/reasoning/service-tier facts and project task-to-model guidance only.

This is **Layer C** of the Codex governance design. It is intentionally replaceable in place.

A future model release should update this file by default without changing:

- `governance/ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md`;
- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`;
- the three peer L2 executor architecture;
- one-primary-Writer semantics;
- independent review;
- worktree/Task-Packet rules;
- user-retained authority gates.

Change the Layer B Codex CLI core only if the CLI/session/permission/context/evidence workflow actually changes. Change Layer A only if execution-class routing or the executor/authority model itself changes.

---

## 1. Current first-party model baseline

Fresh OpenAI first-party verification on 2026-08-20 establishes the current GPT-5.6 family:

```text
FRONTIER_COMPLEX_MODEL=gpt-5.6-sol
BALANCED_MODEL=gpt-5.6-terra
COST_SENSITIVE_MODEL=gpt-5.6-luna
UNSUFFIXED_GPT_5_6_ALIAS=gpt-5.6 -> gpt-5.6-sol
```

Current OpenAI guidance describes:

- GPT-5.6 Sol as the frontier choice for complex professional work, reasoning and coding;
- GPT-5.6 Terra as the balance of intelligence and cost for everyday work;
- GPT-5.6 Luna as the fastest/lowest-cost member for cost-sensitive, high-volume work.

Current Codex availability material says Sol, Terra and Luna are available in Codex on eligible paid plans, with Terra also available on Free/Go. Exact local/account availability must still be verified at dispatch rather than inferred from this document.

Current OpenAI help material requires Codex CLI `0.144.0` or later for GPT-5.6 access. This is a **current compatibility floor**, not a permanently pinned project CLI version. Before a real Codex task, mechanically verify the installed CLI and the selected model surface; do not create a synthetic paid task only to prove availability.

---

## 2. Current model contract facts

Current public GPT-5.6 model documentation reports for Sol/Terra/Luna:

```text
CONTEXT_WINDOW=1,050,000
MAX_OUTPUT=128,000
KNOWLEDGE_CUTOFF=2026-02-16
```

Current provider model guidance exposes reasoning values including:

```text
none | low | medium | high | xhigh | max
```

Current Codex config-reference text explicitly documents:

```text
model_reasoning_effort=minimal | low | medium | high | xhigh
```

The first-party Codex source/client model type also contains newer effort values, but a provider/API capability is not automatically a safe task-local CLI contract.

Therefore the project uses the intersection that is unambiguous on the current documented CLI surface by default:

```text
DEFAULT_ALLOWED_TASK_EFFORTS=low|medium|high|xhigh
MAX=PROVIDER_MODEL_SUPPORTED_BUT_VERIFY_CURRENT_CODEX_CLI_SURFACE_BEFORE_USE
ULTRA=DO_NOT_ASSUME_FROM_ADJACENT_SURFACES; VERIFY_CURRENT_CODEX_SURFACE_BEFORE_USE
```

Do not invent or cargo-cult an effort value merely because another OpenAI surface exposes it.

---

## 3. Current project model-selection matrix

The first routing question is always whether Codex is needed at all. Noncoding/GitHub-only/deterministic work should normally stay in Engineering Control under the execution-class rule.

When `CODEX_CLI` is genuinely selected, use this current starting matrix:

### GPT-5.6 Luna

Use only when the task is highly bounded, mechanically checkable and low in semantic ambiguity, for example:

- repetitive narrow code transformations with strong tests;
- low-risk fixture/test-data maintenance;
- mechanical generated-code adjustment where deterministic validation dominates judgment.

Starting effort:

```text
LUNA=medium
LUNA_LOW=allowed when the task is exceptionally clear and cheap validation is decisive
```

If the task is so mechanical that no code judgment is required, do not use Luna merely because it is cheap; route to deterministic Terminal/Git tooling instead.

### GPT-5.6 Terra

Project default for **ordinary well-bounded coding Writer work** where the route is frozen and the task requires real local code understanding:

- normal bounded feature implementation;
- ordinary bug fix;
- contained refactor;
- test implementation plus in-scope correction;
- straightforward multi-file change with explicit invariants.

Starting effort:

```text
TERRA=medium
TERRA_HIGH=for materially harder bounded implementation when Sol is not yet justified
```

### GPT-5.6 Sol

Use when capability/reliability dominates model cost:

- difficult root-cause debugging;
- cross-layer implementation with important invariants;
- unfamiliar or complex code paths;
- security/authority/execution boundary work;
- hard independent code adjudication when Codex is explicitly selected for review;
- release-critical code acceptance where local semantic inspection is necessary.

Starting effort:

```text
SOL=medium or high
SOL_XHIGH=exceptional difficult tasks where extra depth is justified
```

OpenAI's current general guidance says that when model choice is genuinely uncertain, start with Sol rather than guessing that a smaller model will be sufficient. The project therefore uses Terra as the everyday default only when the bounded task is clearly within Terra's intended balanced-workload class; otherwise choose Sol up front to reduce rework.

### Max / Ultra / subagent-heavy modes

```text
MAX_DEFAULT=OFF
ULTRA_DEFAULT=OFF
SUBAGENT_HEAVY_DEFAULT=OFF
```

Use only when:

1. the current Codex surface explicitly supports the selected setting;
2. L1 records why lower effort is not the best one-pass choice for this bounded task;
3. the extra exploration/parallelism does not violate one-primary-Writer/shared-authority rules;
4. expected quality gain justifies token/credit/latency cost.

Do not use them as prestige defaults.

---

## 4. Reasoning-effort rule

Current durable selection heuristic:

```text
LOW     = narrow, obvious, quickly validated
MEDIUM  = normal bounded coding default
HIGH    = hard multi-step implementation/debugging
XHIGH   = exceptional high-consequence or unusually difficult work
MAX     = current-surface-verified exceptional case only
```

Choose the **lowest effort likely to succeed correctly in one pass**, not the lowest effort that can begin the task.

A cheap failed attempt followed by escalation can cost more tokens and review time than choosing the correct tier initially. Conversely, using XHigh/Max on deterministic work is waste.

Reasoning selection is frozen before the Writer starts. Do not silently raise/lower it mid-stage.

---

## 5. Standard vs Fast service tier

Current Codex first-party speed documentation reports:

```text
FAST_MODE_SPEED≈1.5x
GPT_5_6_FAST_CHATGPT_CREDIT_RATE=2.5x_STANDARD
GPT_5_6_API_PRIORITY_RATE=2x_STANDARD_API_TOKEN_RATE
```

Therefore:

```text
CODEX_SERVICE_TIER_DEFAULT=STANDARD
FAST_MODE_DEFAULT=OFF
```

Enable Fast only for a genuinely time-critical bounded stage where wall-clock latency is worth the current extra usage/credit cost. Fast mode is not a quality upgrade and must not be enabled merely because the task is material.

If the current pricing/speed contract changes, refresh this Layer C file rather than Layer A/B.

---

## 6. Current Codex credit/cache facts

The current OpenAI Codex rate material reports relative token-credit rates where cached input is substantially cheaper than uncached input. The currently published GPT-5.6 Codex rates are:

```text
MODEL              INPUT    CACHED_INPUT    OUTPUT
GPT-5.6 Sol         125      12.5            750
GPT-5.6 Terra       50       5               300
GPT-5.6 Luna        5        0.5             30
```

These are current rate-card values and must be refreshed when OpenAI changes them; they are not durable architecture.

Current Codex rate material also says Codex does not charge ChatGPT Codex credits for cache writes. By contrast, direct GPT-5.6 API prompt caching currently bills cache writes at `1.25x` uncached input rate and reports them separately. Authentication/product surface therefore matters.

Project rule:

```text
DO_NOT_TRANSFER_API_CACHE_BILLING_SEMANTICS_TO_CHATGPT_CODEX=YES
DO_NOT_TRANSFER_CHATGPT_CODEX_CREDIT_SEMANTICS_TO_API_KEY_USE=YES
```

The normal local user-operated Codex route should use the user's already-authenticated Codex CLI and must not ask for or expose API keys merely to optimize caching.

---

## 7. Cache optimization on the current CLI surface

OpenAI's underlying GPT-5.6 API now supports explicit cache breakpoints and cache keys, but the current Codex CLI contract checked for this profile does **not** establish task-level `prompt_cache_key` / explicit breakpoint flags.

Therefore:

```text
EXPLICIT_API_CACHE_BREAKPOINTS_IN_CODEX_CLI=NOT_ASSUMED
PROMPT_CACHE_KEY_IN_CODEX_CLI=NOT_ASSUMED
```

Use the provider-supported optimization that is actually observable in Codex today:

```text
SMALL_STABLE_AGENTS
+ STABLE TOOL/PERMISSION/MODEL SHAPE WITHIN A STAGE
+ STABLE CONTROL PREFIX
+ MUTABLE TASK/EVIDENCE TAIL
+ EXACT SESSION RESUME ONLY WHEN SEMANTICALLY VALID
+ PASSIVE cached_input_tokens MEASUREMENT
```

Current `codex exec --json` emits `turn.completed.usage` including:

```text
input_tokens
cached_input_tokens
output_tokens
reasoning_output_tokens
```

Capture those fields without extra model turns.

A cache miss is not a correctness failure. Do not create synthetic requests to improve a metric.

---

## 8. Context-size economics and discipline

The model family has a very large context window; that is capacity, not permission to fill it.

Current OpenAI model pricing material applies a long-context premium above `272K` input tokens on the GPT-5.6 API surface. Product/plan accounting can differ, but the engineering conclusion is stable:

```text
DO_NOT_USE_LARGE_CONTEXT_JUST_BECAUSE_AVAILABLE=YES
TARGET_TASK_CONTEXT=SMALLEST_COMPLETE_AUTHORITY_AND_CODE_CONTEXT
```

Use repository-local inspection, exact paths and accepted fingerprints instead of copying whole histories/files into the Task Packet.

If a long-running Codex session accumulates stale/unrelated context, start a new clean session at the next valid boundary rather than retaining it solely for cache reuse.

---

## 9. Current CLI/task-local control facts

Current Codex CLI documentation verifies task-local controls including:

```text
--model / -m
--cd / -C
--sandbox / -s
--ask-for-approval / -a
--config / -c key=value
--json
--ephemeral
--ignore-user-config
--strict-config
--add-dir
```

Current config documentation verifies explicit launch model/reasoning overrides take precedence over managed new-thread defaults.

Project implication:

```text
L1_FROZEN_MODEL_REASONING_MUST_BE_ENCODED_PER_INVOCATION=YES
DO_NOT_RELY_ON_REMEMBERED_GLOBAL_MODEL_DEFAULT=YES
```

Use only flags needed by the current task. More flags are not automatically safer.

---

## 10. Current model-profile refresh procedure

When the user changes to a newer Codex/OpenAI model, or OpenAI materially changes current Codex model/service behavior:

```text
VERIFY CURRENT LOCAL CODEX MODEL/VERSION SURFACE
→ CHECK CURRENT FIRST-PARTY CODEX MODEL + CLI + CONFIG DOCS
→ CHECK CURRENT AVAILABILITY / RATE / SPEED DOCS WHERE RELEVANT
→ VERIFY ONLY ACTUALLY EXPOSED CONTROLS
→ COMPARE WITH RECENT REAL TRADER ASSIST CODEX EVIDENCE
→ UPDATE THIS FILE IN PLACE
```

Default change scope:

```text
ONLY governance/CODEX_CURRENT_MODEL_PROFILE.md
```

Escalate to Layer B only if durable CLI/session/context/permission/evidence semantics changed. Escalate to Layer A only if executor or execution-class authority/routing changed.

Do not create `CODEX_GPT_5_7_RULES.md`, `CODEX_GPT_6_RULES.md`, etc. for routine model upgrades.

---

## 11. Real-task observability

During real Codex tasks, collect naturally available evidence:

```text
CODEX_VERSION
MODEL
REASONING_EFFORT
SERVICE_TIER
SESSION_ID / NEW_OR_RESUME_EXACT
INPUT_TOKENS
CACHED_INPUT_TOKENS
OUTPUT_TOKENS
REASONING_OUTPUT_TOKENS
ELAPSED_TIME
MODEL_RETRY_COUNT
ENGINEERING_REPAIR_REWORK_COUNT
FINAL_TASK_ACCEPTANCE
```

Use this evidence to tune future model selection. Do not manufacture paid benchmark tasks.

No arbitrary cache-hit percentage or token target is an acceptance gate.

---

## 12. Current frozen snapshot

```text
PROFILE_LAST_VERIFIED=2026-08-20
CURRENT_CODEX_MODEL_FAMILY=GPT-5.6
CURRENT_SOL=gpt-5.6-sol
CURRENT_TERRA=gpt-5.6-terra
CURRENT_LUNA=gpt-5.6-luna
CURRENT_EVERYDAY_CODEX_WRITER_START=TERRA_MEDIUM_WHEN_CLEARLY_SUFFICIENT
UNCERTAIN_MODEL_FIT_START=SOL_MEDIUM
HARD_COMPLEX_START=SOL_HIGH
XHIGH=EXCEPTIONAL
MAX=VERIFY_CURRENT_CODEX_CLI_SURFACE_BEFORE_USE
ULTRA=VERIFY_CURRENT_CODEX_SURFACE_BEFORE_USE
FAST_MODE_DEFAULT=OFF
CACHE_METRIC=PASSIVE_CACHED_INPUT_TOKENS
EXPLICIT_API_CACHE_BREAKPOINT_IN_CLI=NOT_ASSUMED
MODEL_UPGRADE_DEFAULT_CHANGE_SCOPE=THIS_FILE_ONLY
```