# Trader Assist / Trade OS — Codex Current Model Profile

**Status:** REFRESHABLE MODEL-SPECIFIC GOVERNANCE CANDIDATE  
**Last verified:** 2026-08-23  
**Locally verified Codex CLI:** `0.149.0`

This file is refreshable current-state guidance. Durable workflow rules live in `CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md`.

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
-> verify exact model/reasoning/service-tier controls in the installed surface
-> compare with recent accepted Trader Assist evidence
-> update THIS FILE by default
```

Do not rewrite Router V2 or the stable Codex V2 core merely because a model/version label changed.