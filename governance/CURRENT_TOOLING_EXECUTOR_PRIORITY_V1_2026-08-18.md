# Trader Assist / Trade OS — Current Tooling Executor Priority V1

**Status:** DRAFT SPECIALIZED CURRENT-PRIORITY OVERRIDE  
**Effective date:** 2026-08-18  
**Repository:** `woshixiong/trader-assist-v0`  
**Scope:** current sequencing only; does not change the frozen executor architecture or any release/runtime/account/trading authority.

This file records the user's latest tooling priority and supersedes only stale sequencing text in:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md` section 9;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md` section 8;
- any PR-body text that still says Codex configuration must precede the next DeepSeek task.

It does **not** supersede the technical DeepSeek Harness profile, safety boundaries, task-packet rules, cache/skill rules, Hermes contract, canonical engineering governance, or explicit user gates.

## Current priority

```text
NOW=FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK
CODEX_CONFIGURATION_AND_EFFICIENCY_PROFILE=DEFERRED_UNTIL_USER_RESUMES
DEEPSEEK_HARNESS_SEPARATE_SYNTHETIC_CODING_QUALIFICATION=NOT_REQUIRED
DEEPSEEK_HARNESS_LIGHTWEIGHT_PRESET_SKILL_CACHE_VERIFICATION=COLLECT_DURING_FIRST_REAL_TASK_WHERE_NATURAL
HERMES_CONFIGURATION=AFTER_CURRENT_DEEPSEEK_WORK_OR_WHEN_USER_NEXT_PRIORITIZES
```

## DeepSeek first-real-task rule

The next real bounded Trader Assist task may select `DEEPSEEK_HARNESS` as the L2 Primary Writer once this PR is canonical on `main` and the normal project preflight/task-specific authority is satisfied.

Do not create an extra synthetic coding exercise. During the real task, collect only low-burden Harness setup evidence that occurs naturally:

```text
EXPECTED_DSH_VERSION_VISIBLE
DEEPSEEK_OFFICIAL_PROVIDER_VISIBLE
PTC_CODE_PRESET_VISIBLE
WORKSPACE_WRITE_PLUS_ASK_VISIBLE
ROOT_AGENTS_AUTOLOAD
FOUR_PROJECT_SKILLS_DISCOVERED
SKILL_BODY_LOADS_ON_DEMAND_WHERE_OBSERVABLE
CACHE_TELEMETRY_VISIBLE
WARM_STABLE_PREFIX_CACHE_HIT_OBSERVED_WHERE_NATURAL
```

Do not create extra paid requests solely to raise cache metrics, force every skill body to load, or benchmark coding ability. The real task's normal tests/evidence/review remain the capability evidence.

## Permanent boundaries unchanged

This priority record grants no Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission, cancellation, autonomous trading or financial-action authority.
