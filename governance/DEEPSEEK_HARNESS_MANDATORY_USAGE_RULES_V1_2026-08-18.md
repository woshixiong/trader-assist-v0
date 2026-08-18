# Trader Assist / Trade OS — DeepSeek Harness Mandatory Usage Rules V1

**Status:** DRAFT SPECIALIZED GOVERNANCE FOR QUALIFICATION  
**Effective date:** 2026-08-18  
**Repository:** `woshixiong/trader-assist-v0`  
**Parent profile:** `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`  
**Scope:** mandatory prompt, session, cache, model, skill, permission, cost-scheduling and qualification rules whenever Trader Assist / Trade OS uses a DeepSeek model or DeepSeek Harness as an engineering coding executor.

This file is a specialized companion, not a second general engineering constitution. The canonical Unified Engineering Governance, Mandatory Engineering Preflight, Project Research/Evidence/Decision Method, parent executor profile and all explicit user authority gates remain controlling.

It grants no Mark Ready, merge, deployment, production/runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission or trading authority.

---

## 1. Mandatory applicability

Whenever an Engineering/Operations ChatGPT window generates a DeepSeek Writer prompt, configures a DeepSeek Harness session, assigns `DEEPSEEK_HARNESS`, or deliberately routes another harness to a DeepSeek API model, it MUST apply this file before dispatch.

Required record:

```text
DEEPSEEK_USAGE_RULES_LOADED=YES
DEEPSEEK_EXECUTION_ROUTE=
DEEPSEEK_PROVIDER=
DEEPSEEK_MODEL=
DEEPSEEK_REASONING_EFFORT=
DEEPSEEK_SESSION_MODE=NEW/RESUME_EXACT
DEEPSEEK_PERMISSION_PRESET=
DEEPSEEK_AGENT_PRESET=
DEEPSEEK_PRICE_WINDOW=PEAK/OFF_PEAK
DEEPSEEK_CACHE_DISCIPLINE=PASS
```

Missing or ambiguous material routing fields are fail-closed. The DeepSeek model, Harness, Hermes, or coding Writer may not invent them.

---

## 2. Frozen route decision: native Harness first, Codex compatibility lane second

For normal DeepSeek coding work, the preferred route is:

```text
DEEPSEEK_PRIMARY_HARNESS=DEEPSEEK_HARNESS
DEEPSEEK_PRIMARY_PROVIDER=deepseek-official
```

Rationale:

- DeepSeek Harness is first-party and exposes provider-native DeepSeek semantics;
- it supports the project's intended DeepSeek Flash and Pro routes through its native adapter;
- its Code Mode, project skills, token meter, tool-result pruning, compaction, permission presets and future headless mode form one coherent replaceable executor seam;
- retaining DSH as a peer executor preserves the project's three-tool coding pool rather than collapsing DeepSeek into the Codex harness.

Codex with a DeepSeek custom provider is an **optional compatibility / benchmark lane**, not the default DeepSeek route. Current Codex custom model providers use the Responses API wire contract. Therefore a Codex→DeepSeek route must not be assumed compatible with a DeepSeek model unless the current official DeepSeek API documentation confirms Responses API support for that exact model and the route passes qualification.

As of this rule freeze, official DeepSeek pricing/model documentation confirms Responses API support for `deepseek-v4-flash` and still states `deepseek-v4-pro` is not yet supported there. Therefore:

```text
CODEX_DEEPSEEK_FLASH=OPTIONAL_QUALIFICATION_LANE
CODEX_DEEPSEEK_PRO=DO_NOT_ASSUME_SUPPORTED
```

If official provider support changes later, re-verify before changing this routing policy. Do not infer future support from an old roadmap date.

---

## 3. Ten mandatory DeepSeek operating rules

### Rule 1 — Code Mode first for coding

After DSH qualification, coding sessions default to the shipped `code` agent preset rather than `standard` unless the task explicitly needs a different preset.

The Code Mode design presents the tool registry through a generated SDK and `run_code`, allowing multiple deterministic tool operations to be composed into one model round trip. Use that mechanism to reduce repeated tool-call turns when the operations and return shapes are already known.

Use Standard/Plan behavior only when exploration or explicit planning requires it. Do not switch presets or tool composition mid-stage merely for convenience; a session's agent preset is fixed at session creation.

### Rule 2 — Canonical repository instructions, not repasted history

`AGENTS.md` and the mandatory GitHub governance path are the stable project instruction baseline. DeepSeek prompts should reference canonical repository authority instead of repasting long chat histories or duplicate governance text.

Keep the stable repository instruction chain bounded and specific. Use nested `AGENTS.md` only when a real directory-specific rule exists. Do not duplicate byte-equivalent instructions across `AGENTS.md`, `CLAUDE.md`, Task Packets and skills.

### Rule 3 — Put detailed reusable mechanical procedures in on-demand skills

After qualification, detailed reusable mechanical instructions should live under:

```text
.dsh/skills/<skill-name>/SKILL.md
```

when a project-local skill is justified.

Good skill candidates: test recipes, deterministic preflight/status collection, diff/scope/secret checks, raw evidence collection, Result Packet formatting and other repeatable mechanical workflows.

Skills MUST NOT decide product/strategy/technical route, architecture, executor/model, repair/replan/simplification, scope expansion, independent acceptance, Mark Ready, merge, deployment, runtime, credential/account/signing/exchange or trading actions.

Keep skill descriptions short and routing-specific; load full skill content only when required.

### Rule 4 — Preserve a stable cache prefix

DeepSeek context caching is prefix-based and automatic. Optimize it by preserving the same stable request prefix across a coherent Writer stage:

```text
stable Harness/preset/tool schema
→ stable role + safety/authority boundary
→ stable AGENTS/governance pointers
→ stable output/acceptance contract
→ mutable task facts last
```

Put volatile branch/head SHA, CI run, timestamps, current blocker IDs, one-off evidence and allowlist deltas late in the task packet.

Do not unnecessarily change provider, model, agent preset, visible plugin/tool composition or stable instruction text during the same stage. Correctness and independence always override cache optimization.

### Rule 5 — Measure provider usage instead of guessing efficiency

For qualification and material DeepSeek stages, capture when available:

```text
uncached_input_tokens
prompt_cache_hit_tokens / cache_read_tokens
prompt_cache_miss_tokens
output_tokens
cache_hit_ratio
provider/model
reasoning_effort
session/task id
elapsed time
price window
repair/rework count
```

Provider-reported usage is billing evidence. DSH token-meter estimates are observability aids where exact provider usage is unavailable; they are not billing authority.

A token-saving change is accepted as an optimization only when the task still passes correctness, evidence and review requirements.

### Rule 6 — Resume only within the same Writer role/stage/worktree

Reuse the exact DeepSeek session when all are true:

- same Writer role;
- same coherent authorized stage;
- same worktree/authority context;
- prior context remains trustworthy;
- independence is not required.

Start a new session for independent Reviewer work, clean-route adjudication, a different role, a materially changed authority boundary or a new task whose inherited context is more risk than value.

Do not sacrifice independent review merely to preserve cache hits.

### Rule 7 — Prune deterministic tool noise before model-backed compaction

Prefer deterministic commands and bounded outputs. When test/log/tool output is large, use the shipped tool-result pruning capability before spending another model call on summarization.

Use compaction only at genuine context pressure or a coherent substage boundary. Do not compact after every few turns. Preserve raw authority-bearing evidence separately from conversational summaries.

### Rule 8 — Model and reasoning economy are explicit L1 choices

Use the least expensive DeepSeek model/reasoning level likely to complete the task correctly in one pass.

Default candidate policy after qualification:

```text
Flash + off/low   = deterministic or narrow mechanical work
Flash + high      = ordinary bounded coding when qualification shows adequate quality
Pro + high        = material implementation / difficult debugging
Pro + max         = exceptional hard quality-first coding where measured benefit justifies cost
```

These are routing defaults, not model-owned choices. L1 freezes the exact model and reasoning effort in the task. DeepSeek/Hermes may not self-upgrade model, reasoning, scope or cost tier.

### Rule 9 — “Everything is a Plugin” means composable seams, not plugin proliferation

Use this order:

```text
SHIPPED DSH CAPABILITY
→ SETTINGS / PERMISSION / AGENT PRESET
→ AGENTS.md
→ PROJECT-LOCAL SKILL
→ THIN CUSTOM PLUGIN ONLY AFTER REPEATED MEASURED NEED
```

DSH is Developer Preview, so project integration should minimize dependency on unstable internal plugin details. Custom plugins require a repeated measured need and a replaceability rationale.

Subagents/workflows/Ralph are opt-in, not default. Ralph must never become an unbounded repair loop or an independent acceptance substitute.

### Rule 10 — Schedule delay-tolerant DeepSeek work for official off-peak windows

Official DeepSeek pricing confirmed by the user from the live DeepSeek platform/pricing pages on 2026-08-18:

```text
TIMEZONE=Asia/Shanghai (Beijing time; no DST)
PEAK_1=09:00-12:00
PEAK_2=14:00-18:00
OFF_PEAK=00:00-09:00,12:00-14:00,18:00-24:00
OFF_PEAK_PRICE_MULTIPLIER=0.5_OF_PEAK
```

Policy:

- delay-tolerant DeepSeek coding/replay/evaluation work should be queued for off-peak where practical;
- urgent, release-critical, incident or user-time-sensitive work must not be delayed solely to save API cost;
- cache-hit optimization remains valuable in both price windows;
- these exact windows remain valid only while the official DeepSeek pricing page says so; official current provider state supersedes this snapshot if DeepSeek changes the schedule.

Hermes may later enforce the window mechanically only after `DEEPSEEK_HARNESS` is added to the Lossless Task Packet/operator schema and that change is independently accepted. Until then, off-peak scheduling is manual/L1-controlled for DSH work.

---

## 4. Mandatory DeepSeek prompt-generation shape

When L1 generates a DeepSeek Writer prompt, prefer this shape:

```text
STABLE PREFIX
ROLE / MODE
PROJECT + SAFETY / AUTHORITY BOUNDARY
READ CANONICAL AGENTS/GOVERNANCE PATH
EXECUTOR + PROVIDER + MODEL + REASONING
AGENT PRESET + PERMISSION PRESET
STABLE OUTPUT / EVIDENCE CONTRACT

MUTABLE TASK TAIL
TASK_ID
LIVE_MAIN / EXACT_BASE / EXPECTED_HEAD
BRANCH / WORKTREE
OBJECTIVE / ROOT CAUSE
CURRENT AUTHORITIES / INVARIANTS
ALLOWED FILES / PROHIBITED SCOPE
REQUIRED BEHAVIOR
TEST PLAN / STOP CONDITIONS
CURRENT BLOCKERS / CI / EVIDENCE
PRICE WINDOW
```

Rules:

- do not prepend volatile timestamps/SHAs before stable instructions;
- do not paste complete historical conversations when GitHub already contains accepted authority;
- do not ask the model to rediscover an L1-frozen route;
- do not let a cost-saving instruction weaken tests, review or authority gates;
- for a material Writer task, the normal `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS` and `ENGINEERING_PREFLIGHT_GATE=PASS` requirements still apply before dispatch.

---

## 5. Mandatory DSH preconfiguration baseline

For normal Trader Assist coding after qualification:

```text
PROVIDER=deepseek-official
AGENT_PRESET=code
PERMISSION_PRESET=workspace-write
APPROVAL_POLICY=ask
DANGER_FULL_ACCESS=NO
PRODUCTION_CREDENTIALS=NO
PROJECT_MAIN_WORKTREE_MUTATION=NO
ISOLATED_WORKTREE=YES_FOR_WRITER_MUTATION
MODEL_AND_REASONING=L1_FROZEN_PER_TASK
```

For the initial qualification, use the same safety defaults but begin with a non-production isolated workspace/worktree and a read-only task. No commit, push, PR mutation, production/runtime action or credential/private API access is implied.

---

## 6. Minimum read-only qualification

Before DSH is promoted to normal Writer routing, the first project-specific qualification must prove at least:

```text
OFFICIAL_PROVIDER_ROUTE=PASS
CODE_PRESET_SELECTED=PASS
WORKSPACE_WRITE_PLUS_ASK=PASS
ISOLATED_WORKSPACE_OR_WORKTREE=PASS
AGENTS_GOVERNANCE_DISCOVERY=PASS
READ_ONLY_REPOSITORY_UNDERSTANDING=PASS
NO_FILE_MUTATION=PASS
NO_GIT_MUTATION=PASS
NO_GITHUB_MUTATION=PASS
TOKEN_USAGE_CAPTURE=PASS
CACHE_USAGE_CAPTURE=PASS
RAW_EVIDENCE_CAPTURE=PASS
```

Only after that read-only pass should a separate bounded isolated-worktree coding qualification be authorized.

---

## 7. Qualification comparison: DSH versus Codex+DeepSeek

Do not decide this from architectural preference alone. Where practical, run the same bounded non-production task through:

```text
A = DeepSeek Harness + DeepSeek model
B = Codex harness + the same DeepSeek model, only if that exact model is officially Responses-compatible
```

Compare:

- correctness / acceptance result;
- wall-clock time;
- input/output tokens;
- cache-hit ratio after warm context;
- API cost in the same price window;
- number/severity of Writer mistakes;
- repair/rework count;
- test execution quality;
- operator burden;
- session continuity and evidence quality.

The primary route remains DSH unless evidence shows the Codex compatibility lane is materially superior without losing provider features, model support, replaceability or the intended independent executor seam.

---

## 8. Permanent boundaries

This specialized rule does not authorize:

- Hermes H2 dispatch to DeepSeek Harness before schema/profile acceptance;
- autonomous executor/model switching;
- autonomous repair/retry;
- Mark Ready or merge;
- deployment/runtime/cloud mutation;
- credential/private API/account access outside the explicit provider API key needed for the DSH model route;
- wallet/signing/exchange write/order/trading actions.

Any such boundary requires the existing explicit current user authorization and project governance path.
