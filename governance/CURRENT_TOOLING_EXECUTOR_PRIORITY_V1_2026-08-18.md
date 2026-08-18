# Trader Assist / Trade OS — Current Tooling Executor Priority V1

**Status:** DRAFT SPECIALIZED CURRENT-PRIORITY OVERRIDE  
**Effective date:** 2026-08-18  
**Repository:** `woshixiong/trader-assist-v0`  
**Scope:** current sequencing and first-real-task setup-verification timing only; does not change the frozen executor architecture or any release/runtime/account/trading authority.

This file records the user's latest tooling priority and is the authoritative current sequencing/timing rule for PR #108.

It explicitly supersedes only the stale sequencing or pre-first-task qualification-timing text in:

- `governance/PROJECT_RULES_INDEX.md` specialized coding-executor / DeepSeek Harness section;
- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md` section 7 where it says all lightweight setup checks must finish before the first real task;
- the same profile section 9 tooling-priority order;
- the same profile section 11 field `NEXT_EXPECTED_STAGE`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md` section 6 where it says all remaining setup checks must finish before `READY_FOR_BOUNDED_REAL_TASK`;
- the same mandatory-usage file section 8 tooling-priority order;
- any PR-body or chat text that says Codex configuration or a separate DeepSeek setup-verification stage must precede the next real DeepSeek task.

It does **not** supersede the technical DeepSeek Harness profile, cache/skill mechanisms themselves, safety boundaries, Task Packet rules, Hermes contract, canonical engineering governance, or explicit user gates. It changes only **when** the remaining lightweight setup evidence is collected: inside the first real bounded task rather than as a separate prerequisite stage.

## Current priority

```text
NOW=FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK
CODEX_CONFIGURATION_AND_EFFICIENCY_PROFILE=DEFERRED_UNTIL_USER_RESUMES
DEEPSEEK_HARNESS_SEPARATE_SYNTHETIC_CODING_QUALIFICATION=NOT_REQUIRED
DEEPSEEK_HARNESS_SEPARATE_PRETASK_SETUP_STAGE=NOT_REQUIRED
DEEPSEEK_HARNESS_LIGHTWEIGHT_PRESET_SKILL_CACHE_VERIFICATION=COLLECT_DURING_FIRST_REAL_TASK
HERMES_CONFIGURATION=AFTER_CURRENT_DEEPSEEK_WORK_OR_WHEN_USER_NEXT_PRIORITIZES
```

## First-real-task setup rule

The first real bounded Trader Assist task may select `DEEPSEEK_HARNESS` as the L2 Primary Writer once PR #108 is canonical on `main` and the normal project preflight/task-specific authority is satisfied.

There is no separate paid/synthetic Harness qualification stage before that task.

At the start of the real task, before Writer file mutation, perform only the low-cost mechanical session-baseline checks that are required for safe execution:

```text
EXPECTED_DSH_VERSION_VISIBLE=PASS
DEEPSEEK_OFFICIAL_PROVIDER_VISIBLE=PASS
PTC_CODE_PRESET_VISIBLE=PASS
WORKSPACE_WRITE_PLUS_ASK_VISIBLE=PASS
ROOT_AGENTS_AUTOLOAD=PASS
FOUR_PROJECT_SKILLS_DISCOVERED=PASS
```

If any of those execution-baseline checks fails, SAFE_STOP before file mutation and return to Engineering Control.

The following observability/efficiency evidence is collected during the real task where naturally observable and is **not** a prerequisite to start that task:

```text
FLASH_AND_PRO_CATALOG_VISIBLE
SKILL_BODY_LOADS_ON_DEMAND
SKILL_BODY_NOT_ALWAYS_INJECTED
CACHE_TELEMETRY_VISIBLE
WARM_STABLE_PREFIX_CACHE_HIT_OBSERVED
```

Do not create extra paid requests solely to raise cache metrics, force every skill body to load, or benchmark coding ability. If progressive-skill or cache evidence remains unconfirmed after the task, report it as Harness integration evidence; do not retroactively invalidate otherwise-correct task implementation unless the missing behavior affected correctness or violated the frozen Task Packet.

The real task's normal tests/evidence/review remain the coding capability evidence.

## Canonical interpretation of stale readiness phrases

For PR #108 and successor windows, phrases in the two DeepSeek draft technical documents such as:

```text
After these checks, DeepSeek Harness is ready for a first real task.
DEEPSEEK_HARNESS_SETUP=READY_FOR_BOUNDED_REAL_TASK
```

must be interpreted under this current rule as:

```text
PR108_CANONICAL_ON_MAIN
+ NORMAL_PROJECT_PREFLIGHT/TASK_PACKET=PASS
+ FIRST_REAL_TASK_SESSION_BASELINE_CHECKS=PASS_BEFORE_MUTATION
→ REAL_TASK_MAY_PROCEED
```

Cache-hit and on-demand-skill observability are collected during that task, not before it.

## Permanent boundaries unchanged

This priority record grants no Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission, cancellation, autonomous trading or financial-action authority.
