# Trader Assist / Trade OS — Codex Current Model Profile

**Status:** REFRESHABLE MODEL-SPECIFIC GOVERNANCE CANDIDATE  
**Last verified:** 2026-09-19  
**Latest observed local Codex CLI:** `0.155.1`

This file is refreshable current-state guidance. Durable workflow rules live in `CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md`.

The observed CLI version is telemetry, **not an exact-equality launch gate**. A launcher may require a specific version only when a task has a proven version-dependent semantic incompatibility. Otherwise verify the actual installed CLI identity and the exact required command/config capabilities. A newer compatible patch release must not trigger a false SAFE_STOP merely because this profile has not yet been refreshed.

**Scope:** this profile applies only after `ENGINEERING_EXECUTOR_ROUTER_V2` has selected `CODEX_CLI` for a semantic Writer stage. Labels such as `NORMAL_MATERIAL` or `HIGH_CONSEQUENCE` choose the Codex model/reasoning within that route; they do not create semantic work and do not override Router/user executor authority.

## Current family

```text
GPT_5_6_TERRA = normal material Codex Writer / quality-efficiency balance
GPT_5_6_SOL   = difficult, complex, uncertain or high-consequence Codex Writer
GPT_5_6_LUNA  = cost/high-volume specialist; small role in this project because free OpenCode covers many low-risk tasks
GPT_5_3_CODEX = agentic-coding specialist / empirical alternative, not default Writer
```

Current OpenAI guidance describes Sol as the frontier option, Terra as the intelligence/cost balance, and Luna as efficient high-volume. Reasoning effort should be set intentionally rather than maximized by default.

## Reasoning routing

```text
NORMAL_MATERIAL:
  Terra medium

DIFFICULT_BUT_BOUNDED:
  Terra high
  OR Sol medium/high when the quality requirement warrants model upgrade

HIGH_CONSEQUENCE / HARD_ROOT_CAUSE:
  Sol high

EXTREME / ARCHITECTURAL / FRONTIER_DIFFICULTY:
  Sol xhigh

MAX:
  only after an explicit current-surface verification and a task-specific reason;
  never because "material" alone implies maximum reasoning
```

When migrating/tuning, compare the current level with one level lower on representative real tasks; do not assume more reasoning always improves accepted work per quota.

## Task-local Engineering Control decision — mandatory

For every Codex Writer stage, Engineering Control/Router must explicitly decide and freeze before prompt/launch generation:

```text
CODEX_MODEL=
CODEX_REASONING_EFFORT=
CODEX_WEB_SEARCH_REQUIRED=YES|NO
CODEX_WEB_SEARCH_MODE=disabled|cached|indexed|live
```

Rules:

- model and reasoning level are Engineering Control decisions based on task complexity/consequence and current quota state; the Codex Writer does not self-upgrade;
- `CODEX_WEB_SEARCH_REQUIRED=NO` normally means `CODEX_WEB_SEARCH_MODE=disabled`;
- if current external/provider/library facts are genuinely needed inside the Writer stage, Engineering Control may set Web Search to the verified current Codex mode that fits the task and must state this explicitly in the Task Packet/launch contract;
- do not enable Web Search merely because it is available; do not disable it when the frozen task genuinely depends on current external evidence;
- a required mid-stage model/reasoning/Web-Search shape change is normally a stage/session boundary because it changes execution/prefix/tool shape.

The current Codex source exposes top-level `web_search` modes `disabled`, `cached`, `indexed`, and `live`; the current task launcher must use only a mode verified in the installed Codex surface.

## Service tier

```text
DEFAULT_SERVICE_TIER=default
FAST_OR_PRIORITY=OFF_BY_DEFAULT
```

Fast/priority is a latency policy, not a quality upgrade. Enable only for a real time-critical need.

## Current local baseline

User audit on 2026-08-23 showed:

```text
codex-cli 0.149.0
~/.codex/config.toml present
model = gpt-5.6-terra
model_reasoning_effort = high
service_tier = default
~/.codex/AGENTS.md absent
~/.codex/AGENTS.override.md absent
```

V2 recommendation changes the user-level fallback reasoning from `high` to `medium`. Trader Assist task-specific upgrades should be explicit through Router-selected profiles/CLI flags.

## Refresh rule

When the current Codex model family/CLI changes:

```text
VERIFY codex --version
-> check current first-party Codex/model/config docs
-> verify exact model/reasoning/service-tier/Web-Search controls in the installed surface
-> compare with recent accepted Trader Assist evidence
-> update THIS FILE by default
```

Do not rewrite Router V2 or the stable Codex V2 core merely because a model/version label changed.

## Validated local fallback path / retired assumptions — 2026-09-19

This is current execution telemetry, not the preferred future architecture.

```text
ROLE=PROVEN_LOCAL_FILE_BACKED_CLI_FALLBACK_OR_RECOVERY
CANONICAL_EVIDENCE=Issue_163_comment_5740747880
KNOWN_GOOD_INVOCATION_FAMILY=codex config overrides + exec + frozen model/sandbox/json/output/cwd
EXACT_PATCH_VERSION_REQUIRED=NO
UNPROVEN_CONFIG_BYPASS_FLAG_REQUIRED=NO
UNPROVEN_APPROVAL_FLAG_REQUIRED=NO
LOCAL_GITHUB_PUBLICATION_REQUIRED_BEFORE_SEMANTIC_START=NO
LOCAL_CANONICAL_PR_HEAD_OBJECT_REQUIRED_BEFORE_SEMANTIC_START=NO
ONE_SEMANTIC_SESSION=YES
IMMEDIATE_DURABLE_CHECKPOINT=YES
```

Retired unless capability/environment materially changes:

```text
STALE_EXACT_CODEX_PATCH_VERSION_GATE
UNPROVEN_CONFIG_BYPASS_FLAG_REQUIREMENT
UNPROVEN_APPROVAL_FLAG_INVOCATION
LOCAL_CANONICAL_PR_HEAD_OBJECT_PRESENCE_AS_SEMANTIC_PREREQUISITE
LOCAL_GITHUB_PUBLICATION_AS_SEMANTIC_START_PREREQUISITE
DYNAMIC_LAUNCHER_REPAIR_CHAIN_AS_DEFAULT
```

Provider-native asynchronous/issue-centric execution remains the preferred experiment when fidelity, observability and recovery are sufficient. The proven local file-backed route remains fallback/recovery evidence, not a mandate to reproduce custom source-reconstruction mechanics.

