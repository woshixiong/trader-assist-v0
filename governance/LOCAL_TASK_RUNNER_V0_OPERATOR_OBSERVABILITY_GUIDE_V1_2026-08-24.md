# Trader Assist / Trade OS — Local Task Runner V0 Operator Observability Guide V1

**Status:** GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-24 after independent acceptance and merge  
**Issue:** #121  
**Scope:** user-visible first-real-task evidence return and routine Runner health classification

This guide is an operator-facing companion to `LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`. It changes no Runner code, model routing, Task Packet authority, retry policy, publication authority or product/runtime semantics.

Its purpose is to ensure the user does **not** become a manual telemetry collector or the routine bridge between Engineering Control and tooling control.

## 1. Permanent user experience

For every Local Task Runner invocation, Engineering Control must generate the complete one-paste Terminal block so that the block itself reads the Runner artifacts and prints a final machine-readable/user-copyable status section.

The user must not be asked to manually:

- locate and interpret individual Runner JSON fields;
- calculate hashes;
- inspect raw OpenCode logs;
- count retries;
- compare changed paths against the allowlist;
- reconstruct Git identity;
- decide whether a failure belongs to application engineering or tooling.

The generated block performs those deterministic observations and prints the classification.

## 2. Mandatory final sentinel for every Runner use

Every Engineering-generated Runner Terminal block must end by printing exactly one compact final sentinel containing at least:

```text
LOCAL_TASK_RUNNER_STATUS_BEGIN
RUNNER_FLOW_STATUS=PASS|ENGINEERING_ACTION_REQUIRED|TOOLING_ACTION_REQUIRED|SAFE_STOP
TOOLING_ESCALATION_REQUIRED=YES|NO
ENGINEERING_CONTINUE_ALLOWED=YES|NO
TASK_ID=<task id>
RUN_ID=<runner run id or NONE>
MODEL=<exact provider/model or NONE>
FINAL_STATUS=<Runner final status or NONE>
STOP_REASON=<exact stop reason or NONE>
RETRY_COUNT=<integer or UNKNOWN>
LOCAL_TASK_RUNNER_STATUS_END
```

The block must derive these values from exact preflight/result/evidence artifacts, not from Writer prose.

The status sentinel is the user's normal daily health surface. Raw evidence remains available when needed, but the user should not have to read it during ordinary successful work.

## 3. Classification rules

### `RUNNER_FLOW_STATUS=PASS`

Use only when all applicable deterministic conditions are satisfied:

```text
accepted Runner version/core identity = PASS
OpenCode required CLI surface = PASS
start Git branch/HEAD/worktree identity = PASS
start worktree clean = YES
input Task Packet hash = exact
actual executor = OPENCODE
actual model/variant transport = frozen exact values
runner.py run invocation count = 1
RETRY_COUNT = 0
POLICY_VIOLATIONS = []
changed paths are within allowed_changed_paths
required deterministic checks = PASS
FINAL_STATUS = SUCCEEDED
STOP_REASON = NONE/null
result/evidence artifacts are readable and internally coherent
```

This means the **Runner workflow** behaved correctly. It is not independent acceptance of the code, and it does not authorize commit/push/Mark Ready/merge/deploy/runtime/trading actions.

### `RUNNER_FLOW_STATUS=ENGINEERING_ACTION_REQUIRED`

Use when the Runner itself behaved correctly but the normal project task needs Engineering Control disposition, including examples such as:

- application code/test/check failure;
- implementation did not satisfy the frozen task;
- a legitimate scope change or new technical blocker requires a refrozen Task Packet;
- OpenCode/model/provider unavailable or degraded and Router must decide a new authorized route/run;
- normal repair/convergence rules are required.

Set:

```text
TOOLING_ESCALATION_REQUIRED=NO
ENGINEERING_CONTINUE_ALLOWED=YES
```

unless a separate authority/safety condition requires `SAFE_STOP`.

### `RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED`

Use when the defect is in the Runner/workflow envelope rather than the project implementation, including:

```text
LOCAL_TASK_RUNNER_IDENTITY_DRIFT
Runner schema/result corruption
Runner cannot expose or parse authoritative result/evidence
Runner CLI preflight is wrong or accepts the wrong OpenCode surface
Runner reports success despite policy/check failure
Runner changed-path policy is false or inconsistent
Runner state/evidence artifacts disagree about one run
hidden/duplicate Runner execution is observed
retry count is nonzero without newly frozen authority
accepted Runner identity cannot be proven
```

Set:

```text
TOOLING_ESCALATION_REQUIRED=YES
ENGINEERING_CONTINUE_ALLOWED=NO
```

The user returns to tooling control with the final status/observation block. Do not repair application code in the tooling window merely because a Runner incident occurred.

### `RUNNER_FLOW_STATUS=SAFE_STOP`

Use when exact authority or state is insufficient to continue safely and the failure is not yet classified as a normal Engineering or tooling defect. The stop reason must identify the unresolved gate. Engineering Control owns initial classification unless the reason is already a known Runner/tooling defect.

## 4. First real Runner task — mandatory observation packet

The first naturally occurring real Trader Assist stage that legitimately uses the Runner is also the first operational workflow observation. No synthetic task is created.

For that first real use only, the Engineering-generated Terminal block must additionally print a copyable block:

```text
LOCAL_TASK_RUNNER_OBSERVATION_PACKET_BEGIN
FIRST_REAL_RUNNER_OBSERVATION=YES
TOOL=LOCAL_TASK_RUNNER_V0
RUNNER_VERSION=<version>
RUNNER_CORE_IDENTITY_CHECK=PASS|FAIL
OPENCODE_VERSION=<version>
ROLE=WRITER|OPERATOR
TASK_ID=<task id>
TASK_CLASS=T0|T1|T2|T3
EXECUTOR=OPENCODE
MODEL=<exact provider/model>
VARIANT=<exact value or null>
INPUT_PACKET_SHA256=<sha256>
RUN_ID=<run id>
START_HEAD=<sha>
START_BRANCH=<branch>
START_WORKTREE_CLEAN=YES|NO
EXECUTOR_EXIT_STATUS=<integer or NONE>
CHANGED_PATHS=<compact exact list>
POLICY_VIOLATIONS=<compact exact list>
CHECK_RESULTS=<compact name:exit list>
FINAL_STATUS=<status>
STOP_REASON=<reason or NONE>
RETRY_COUNT=<integer>
ELAPSED_TIME=<seconds if available>
FIRST_PASS_RESULT=PASS|FAIL
HUMAN_INTERVENTION_COUNT=<integer>
TOKENS_OR_COST_IF_EXPOSED=<value or NOT_EXPOSED>
LOCAL_TEST_RESULT=<summary>
EXACT_HEAD_CI_RESULT_WHEN_APPLICABLE=<value or PENDING/NOT_APPLICABLE>
INDEPENDENT_REVIEW_RESULT=<value or PENDING/NOT_APPLICABLE>
INDEPENDENT_REVIEW_BLOCKERS=<compact value or NONE/PENDING>
RUNNER_FLOW_STATUS=PASS|ENGINEERING_ACTION_REQUIRED|TOOLING_ACTION_REQUIRED|SAFE_STOP
TOOLING_ESCALATION_REQUIRED=YES|NO
LOCAL_TASK_RUNNER_OBSERVATION_PACKET_END
```

If a field is not exposed at that stage, print a clear `NOT_EXPOSED`, `PENDING` or `NOT_APPLICABLE`; never invent data.

### What the user returns to tooling control after the first real task

The user copies **only the complete `LOCAL_TASK_RUNNER_OBSERVATION_PACKET_BEGIN ... END` block** into the tooling-control window.

That is sufficient for the first-pass workflow-health review in the normal case. If deeper evidence is required, tooling control may then ask for specific existing Runner artifacts, normally from the exact `RUN_ID` directory such as `result.json`, `evidence.md`, or bounded executor logs. The user should not proactively collect or upload large raw logs unless requested.

The code/task outcome itself remains with Engineering Control. The first-real-task return to tooling control is a one-time operational validation of the Runner workflow, not a second code review.

## 5. Normal daily-use guide for the user

After the first real workflow observation is accepted, the user normally checks only the final status sentinel.

```text
RUNNER_FLOW_STATUS=PASS
TOOLING_ESCALATION_REQUIRED=NO
```

=> Runner workflow is normal. Stay in the Engineering window. No tooling-window visit is needed.

```text
RUNNER_FLOW_STATUS=ENGINEERING_ACTION_REQUIRED
TOOLING_ESCALATION_REQUIRED=NO
```

=> Runner worked, but normal code/test/model/task handling is required. Stay in the Engineering window.

```text
RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED
TOOLING_ESCALATION_REQUIRED=YES
```

=> Return to tooling control and paste the complete final status block. Preserve the exact `RUN_ID`; do not rerun automatically.

```text
RUNNER_FLOW_STATUS=SAFE_STOP
```

=> Do not rerun automatically. Let Engineering Control classify the exact stop reason. If it identifies a Runner/tooling defect, return to tooling control with the status block.

## 6. User-visible red flags

Even if the final sentinel is malformed or absent, treat any of the following as a workflow warning and stop before an automatic rerun:

- the generated command asks the user to manually edit Runner JSON or hashes;
- the command launches `runner.py run` more than once without a new Engineering disposition;
- the effective OpenCode model differs from the Router-frozen exact model;
- Runner identity/hash verification is skipped or fails;
- starting Git branch/HEAD does not match the frozen task;
- the worktree is dirty before executor launch without explicit frozen handling;
- changed paths exceed the allowlist;
- `POLICY_VIOLATIONS` is non-empty but the flow still says PASS;
- a required check fails but the flow still says PASS;
- `RETRY_COUNT` is greater than zero without a separately authorized new run;
- `result.json`/evidence is missing, unreadable or internally contradictory;
- the Terminal block silently changes model, provider, worktree or authority after a failure;
- the user is asked to return to tooling control for an ordinary source-code/test bug.

## 7. Evidence retention and no hidden rerun

The exact Runner `RUN_ID` is the primary local evidence handle. Engineering Control should preserve or reference the normal Runner result/evidence artifacts in the task evidence trail when applicable.

A failed run is evidence. Do not run the same Runner task again merely to obtain a cleaner observation packet. Engineering Control first classifies the cause and freezes any permitted next run under normal repair/routing rules.

## 8. What first-real-task success means

The workflow observation is successful when it demonstrates, on genuine project work, that:

1. the user needed only the expected single Terminal paste for the local Runner stage;
2. exact Runner/task/model/Git identity was preserved;
3. exactly one Runner/OpenCode attempt occurred;
4. deterministic scope/check gates governed success rather than Writer self-report;
5. evidence was readable enough for Engineering and tooling diagnosis;
6. normal application failures stayed with Engineering Control;
7. genuine Runner/workflow defects would be clearly escalated to tooling control.

This operational success does not prove the underlying code is correct; normal CI and independent engineering review remain separate gates.
