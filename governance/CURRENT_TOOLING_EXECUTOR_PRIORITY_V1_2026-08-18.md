# Trader Assist / Trade OS — Current Tooling Executor Priority V1

**Status:** HISTORICAL SEQUENCING SNAPSHOT — SUPERSEDED FOR TASK-LEVEL EXECUTOR ROUTING  
**Original effective date:** 2026-08-18  
**Superseding routing proposal:** `governance/ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md`  
**Repository:** `woshixiong/trader-assist-v0`

## Current interpretation after the 2026-08-20 routing change

This file previously recorded a temporary tooling sequence in which the next real bounded task was expected to use DeepSeek Harness. That sequence was useful as a dated planning snapshot, but it must not be treated as permanent executor authority.

Current durable routing is:

```text
APPROVED_L2_EXECUTORS=CODEX_CLI | TRAE / TRAE_COMPUTER_USE | DEEPSEEK_HARNESS
USER/L1_SELECTS_EXACT_EXECUTOR_MODEL_PER_BOUNDED_TASK_OR_COHERENT_STAGE=YES
GLOBAL_FIXED_PRIMARY_WRITER=NO
STALE_SEQUENCING_SNAPSHOT_BINDS_NEW_TASK=NO
SELECTED_TOOL_PROFILE_AUTO_LOAD=YES
```

The user may switch among approved peer executors from one bounded task/coherent stage to another. One primary Writer still owns each shared-authority stage; executor switching does not permit competing Writers on the same artifact. A current user selection supersedes only stale executor/model routing, never technical acceptance criteria, authority invariants, repair budget, tests, review, CI or retained user gates.

Deferred tooling work is tracked in GitHub Issue #115:

- DeepSeek Harness rc.8 real-task seam/capability validation;
- DeepSeek Harness token/cache/progressive-skill evidence during a future real DSH task;
- Codex settings/execution/token-efficiency profile work;
- Hermes installation/configuration.

For the ongoing Issue #112 workflow, the current user-selected executor/model is `TRAE + GLM-5.3` until the user changes it. The live Issue #112 coordination note is the task-level routing authority; Issue #112's technical acceptance matrix remains unchanged.

No rule in this file grants Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission/cancellation or trading authority.

---

## Historical 2026-08-18 snapshot

The original sequencing decision was:

```text
NOW=FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK
CODEX_CONFIGURATION_AND_EFFICIENCY_PROFILE=DEFERRED_UNTIL_USER_RESUMES
DEEPSEEK_HARNESS_SEPARATE_SYNTHETIC_CODING_QUALIFICATION=NOT_REQUIRED
DEEPSEEK_HARNESS_SEPARATE_PRETASK_SETUP_STAGE=NOT_REQUIRED
DEEPSEEK_HARNESS_LIGHTWEIGHT_PRESET_SKILL_CACHE_VERIFICATION=COLLECT_DURING_FIRST_REAL_TASK
HERMES_CONFIGURATION=AFTER_CURRENT_DEEPSEEK_WORK_OR_WHEN_USER_NEXT_PRIORITIZES
```

That historical record remains useful for provenance of PR #108/DeepSeek Harness setup timing, especially the decision to avoid a separate paid synthetic coding qualification and to collect lightweight setup/cache evidence during a real task. It is **not** a current universal Primary-Writer assignment.

The underlying permanent DeepSeek safety/usage rules remain in:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`.

The permanent first-real-task evidence principle also remains: no standalone synthetic paid qualification is required; when DeepSeek Harness is next selected for a real bounded task, perform the then-current required pre-mutation execution-seam checks and collect token/cache/skill evidence naturally during that task.
