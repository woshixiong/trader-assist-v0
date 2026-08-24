---
name: trade-os-local-task-runner
description: Generate and execute the accepted Local Task Runner V0 one-paste OpenCode workflow for a frozen Trader Assist task, preserving exact Git/task/model identity, deterministic checks and fail-closed evidence.
---

# Trade OS Local Task Runner

Use only after Engineering Control has completed the mandatory live preflight and Router V2 has already selected `OPENCODE` for the bounded stage.

Read `governance/LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md` before generating the command.

## Required behavior

- Do not manufacture a synthetic first-real-task benchmark. Use the first naturally occurring real OpenCode-compatible project stage.
- Do not use the Runner to override Router V2 or choose a model. Freeze the exact `provider/model` first.
- Resolve `LOCAL_TASK_RUNNER_HOME="${TRADE_OS_LOCAL_RUNNER_HOME:-$HOME/trade-os-local-runner-v0-candidate}"`.
- Verify the accepted Runner version/core identity before execution; drift => `LOCAL_TASK_RUNNER_IDENTITY_DRIFT` and tooling control.
- Use a bounded clean Git worktree with exact start branch/HEAD.
- Generate the complete `local-task-packet-v0` JSON for the user. Never ask the user to hand-edit Runner JSON or calculate its hash.
- Keep `expected_git.required=true`, exact head/branch and the minimum complete `allowed_changed_paths` allowlist.
- Use deterministic argv-based checks from the frozen Task Packet. Do not add shell/Git-mutation validation escape routes.
- Generate **one complete ordinary-Terminal paste block** that performs Runner identity preflight, packet creation, SHA-256 calculation, `validate`, exactly one `run`, RUN_ID/result/evidence capture and a compact telemetry summary.
- `runner.py run` is executed once. No hidden retry, automatic resume or silent model fallback.
- An OpenCode exit code of `0` is not success by itself; final Runner policy/check status governs.
- Do not commit/push, Mark Ready, merge, deploy or access production/private trading authority unless a separate current gate explicitly authorizes that distinct action.

## Failure ownership

```text
normal application-code or frozen-test failure -> Engineering Control
scope/authority ambiguity -> Engineering Control / L1 SAFE_STOP
model/provider availability -> Engineering Control / Router; no silent substitution
runner identity/schema/state/evidence/policy defect -> tooling control
```

The user should not be used as the routine bridge between the Engineering and tooling windows. Return to tooling control only for a genuine Runner/workflow problem.

## Required result/telemetry surface

Preserve when available:

```text
RUNNER_VERSION
OPENCODE_VERSION
ROLE
TASK_ID
TASK_CLASS
MODEL
VARIANT
INPUT_PACKET_SHA256
RUN_ID
START_HEAD
START_BRANCH
START_WORKTREE_CLEAN
EXECUTOR_EXIT_STATUS
CHANGED_PATHS
POLICY_VIOLATIONS
CHECK_RESULTS
FINAL_STATUS
STOP_REASON
RETRY_COUNT
ELAPSED_TIME
FIRST_PASS_RESULT
HUMAN_INTERVENTION_COUNT
TOKENS_OR_COST_IF_EXPOSED
LOCAL_TEST_RESULT
EXACT_HEAD_CI_RESULT_WHEN_APPLICABLE
INDEPENDENT_REVIEW_RESULT
INDEPENDENT_REVIEW_BLOCKERS
```

For the first real project use, collect these naturally inside the normal task evidence trail; do not create a separate benchmark task.
