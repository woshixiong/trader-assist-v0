# Trader Assist / Trade OS — Local Task Runner V0 Operator Observability Guide V1

**Status:** GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-24 after independent acceptance and merge  
**Issue:** #121  
**Scope:** Engineering-window post-run triage, user handoff, first-real-task observation, and tooling escalation

This guide is an operator-facing companion to `LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`. It changes no Runner code, model routing, Task Packet authority, retry policy, publication authority or product/runtime semantics.

Its purpose is to ensure the user does **not** become a manual telemetry collector, Runner diagnostician, or routine bridge between Engineering Control and tooling control.

## 1. Permanent user experience

For every Local Task Runner invocation, Engineering Control must generate the complete one-paste Terminal block. After it finishes, the user's normal action is simply:

```text
RUN THE ONE ENGINEERING-GENERATED TERMINAL BLOCK
-> COPY THE COMPLETE TERMINAL OUTPUT ONCE
-> PASTE IT BACK INTO THE SAME ENGINEERING WINDOW
-> ENGINEERING WINDOW TRIAGES BOTH THE CODE RESULT AND THE RUNNER WORKFLOW HEALTH
```

The user is **not** expected to search the Terminal output for Runner status fields or personally classify the four Runner states.

The user must not be asked to manually:

- locate and interpret individual Runner JSON fields;
- search for the status sentinel inside a long Terminal transcript;
- calculate hashes;
- inspect raw OpenCode logs;
- count retries;
- compare changed paths against the allowlist;
- reconstruct Git identity;
- decide whether a failure belongs to application engineering or tooling;
- compose a tooling-control escalation prompt.

Engineering Control owns those deterministic observations after receiving the Terminal output.

## 2. Mandatory machine-readable final sentinel

Every Engineering-generated Runner Terminal block must still end by printing exactly one compact machine-readable sentinel containing at least:

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

**This sentinel is primarily an Engineering-Control parsing surface, not a user inspection burden.** The Engineering window must read it from the pasted Terminal transcript. The user should not need to find or interpret it during ordinary work.

If the sentinel is absent, malformed, contradictory or inconsistent with other pasted evidence, Engineering Control must treat that fact itself as a workflow warning and classify it before any rerun.

## 3. Mandatory Engineering-window post-run triage

After the user pastes the complete Terminal output back into the same Engineering window, Engineering Control must perform **two reviews in the same response**:

```text
A. NORMAL ENGINEERING OUTCOME
   - did the implementation satisfy the frozen task?
   - did local checks/tests pass?
   - what normal repair/review/CI action follows?

B. RUNNER WORKFLOW HEALTH
   - was accepted Runner identity preserved?
   - was exact task/model/Git identity preserved?
   - was exactly one Runner/OpenCode attempt executed?
   - were changed-path and deterministic-check gates coherent?
   - did result/evidence remain readable and mutually consistent?
   - was retry/fallback/resume policy preserved?
```

The user must not perform review B manually.

Engineering Control must explicitly classify the Runner workflow as one of:

```text
RUNNER_FLOW_STATUS=PASS
RUNNER_FLOW_STATUS=ENGINEERING_ACTION_REQUIRED
RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED
RUNNER_FLOW_STATUS=SAFE_STOP
```

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
result/evidence artifacts are readable and internally coherent
```

The exact successful `STOP_REASON` must be interpreted against the accepted Runner contract; do not hard-code `NONE/null` if the accepted success contract uses a named completion reason.

This classification means the **Runner workflow** behaved correctly. It is not independent acceptance of the code and grants no commit/push/Mark Ready/merge/deploy/runtime/trading authority.

### `RUNNER_FLOW_STATUS=ENGINEERING_ACTION_REQUIRED`

Use when the Runner itself behaved correctly but the normal project task needs Engineering Control disposition, including:

- application code/test/check failure;
- implementation did not satisfy the frozen task;
- a legitimate scope change or new technical blocker requires a refrozen Task Packet;
- OpenCode/model/provider unavailable or degraded and Router must decide a new authorized route/run;
- normal repair/convergence rules are required.

Set:

```text
TOOLING_ESCALATION_REQUIRED=NO
```

unless a separate authority/safety condition requires `SAFE_STOP`.

### `RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED`

Use when the defect is in the Runner/workflow envelope rather than the project implementation. Mandatory tooling-escalation triggers include:

```text
LOCAL_TASK_RUNNER_IDENTITY_DRIFT
accepted Runner identity/hash cannot be proven
Runner schema/result corruption
Runner result/evidence is missing, unreadable or internally contradictory
Runner state/evidence artifacts disagree about one run
Runner CLI preflight is wrong or accepts the wrong OpenCode surface
Runner reports success despite a required deterministic check failure
Runner reports success despite non-empty policy violations
Runner changed-path policy is false, inconsistent or fails to detect out-of-allowlist mutation
hidden/duplicate runner.py run execution is observed
RETRY_COUNT > 0 without a separately frozen/authorized new run
silent model/provider/variant substitution is observed
silent worktree/branch/HEAD/authority substitution is observed
mandatory final sentinel is absent/malformed in a way Engineering Control cannot reconcile with authoritative Runner evidence
Runner cannot expose enough authoritative state to classify the run safely
```

Set:

```text
TOOLING_ESCALATION_REQUIRED=YES
ENGINEERING_CONTINUE_ALLOWED=NO
```

Do not attempt an application-code repair as a substitute for resolving a Runner defect.

### `RUNNER_FLOW_STATUS=SAFE_STOP`

Use when exact authority or state is insufficient to continue safely and the failure is not yet classified as normal Engineering or tooling. Engineering Control owns the initial classification. No automatic rerun is allowed.

## 4. Engineering-visible red flags that must be checked automatically

The following are mandatory workflow warnings. They are written into the Engineering workflow so the user does not need to notice them personally:

- the generated command asks the user to manually edit Runner JSON or packet hashes;
- the generated command requires a second manual OpenCode prompt/paste for the same frozen stage;
- the command launches `runner.py run` more than once without a newly frozen Engineering disposition;
- the effective OpenCode model/variant differs from the Router-frozen exact model/variant;
- Runner identity/hash verification is skipped or fails;
- starting Git branch/HEAD does not match the frozen task;
- the worktree is dirty before executor launch without explicit frozen handling;
- changed paths exceed the allowlist;
- `POLICY_VIOLATIONS` is non-empty but the flow still claims PASS;
- a required deterministic check fails but the flow still claims PASS;
- `RETRY_COUNT` is greater than zero without a separately authorized new run;
- `result.json`, evidence or state is missing, unreadable or mutually contradictory;
- the Terminal block silently changes model, provider, variant, worktree, branch, HEAD or authority after a failure;
- the Runner/OpenCode invocation count cannot be established when that fact is required for the current classification;
- the user is told to return to tooling control for an ordinary source-code/test bug;
- the user is asked to manually search the Terminal transcript for Runner health fields instead of letting Engineering Control classify them.

Engineering Control must inspect for these conditions whenever Runner output is returned.

## 5. Mandatory tooling-escalation response contract

When Engineering Control concludes either:

```text
RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED
```

or a `SAFE_STOP` is subsequently classified as a Runner/workflow defect, the Engineering window must do **all** of the following in the same reply:

1. clearly tell the user that this is a Runner/workflow issue and that the tooling-control window is required;
2. tell the user **not to rerun** the Runner automatically;
3. keep normal application-code diagnosis separate;
4. generate one complete ready-to-copy prompt inside a single fenced code block;
5. populate that prompt from the exact pasted Terminal/result evidence; unknown fields must be `UNKNOWN`, never guessed.

The code block must follow this contract:

```text
TOOLING_CONTROL_ESCALATION_PROMPT_BEGIN
PROJECT=Trader Assist / Trade OS
SOURCE_WINDOW=ENGINEERING_CONTROL
REQUEST=Diagnose Local Task Runner V0 workflow/tooling incident. Do not treat this as a normal application-code repair unless the evidence proves that classification was wrong.

TASK_ID=<exact or UNKNOWN>
TASK_CLASS=<exact or UNKNOWN>
RUN_ID=<exact or NONE/UNKNOWN>
RUNNER_VERSION=<exact or UNKNOWN>
RUNNER_CORE_IDENTITY_CHECK=PASS|FAIL|UNKNOWN
OPENCODE_VERSION=<exact or UNKNOWN>
EXECUTOR=OPENCODE|UNKNOWN
MODEL=<exact or UNKNOWN>
VARIANT=<exact/null/UNKNOWN>
INPUT_PACKET_SHA256=<exact or UNKNOWN>
START_HEAD=<exact or UNKNOWN>
START_BRANCH=<exact or UNKNOWN>
START_WORKTREE_CLEAN=YES|NO|UNKNOWN
EXECUTOR_EXIT_STATUS=<integer/NONE/UNKNOWN>
CHANGED_PATHS=<exact compact value or UNKNOWN>
POLICY_VIOLATIONS=<exact compact value or UNKNOWN>
CHECK_RESULTS=<exact compact value or UNKNOWN>
FINAL_STATUS=<exact or UNKNOWN>
STOP_REASON=<exact or UNKNOWN>
RETRY_COUNT=<integer or UNKNOWN>
RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED|SAFE_STOP
TOOLING_ESCALATION_REQUIRED=YES

TOOLING_TRIGGER=<exact trigger(s) observed by Engineering Control>
OBSERVED_WORKFLOW_RED_FLAGS=<exact compact list or NONE>
ENGINEERING_CODE_OUTCOME=<brief factual application-code disposition; do not ask tooling control to solve normal code defects>
AVAILABLE_LOCAL_EVIDENCE=<RUN_ID/result/evidence paths if printed, otherwise UNKNOWN>

USER_ACTION=Paste this entire block into the Tooling Control window. Do not rerun Local Task Runner unless a new Engineering/Tooling disposition explicitly authorizes it.
TOOLING_CONTROL_ESCALATION_PROMPT_END
```

The user must never be asked to manually compose this packet from the Terminal transcript.

## 6. First real Runner task — one-time observation handoff

The first naturally occurring real Trader Assist stage that legitimately uses the Runner is also the first operational workflow observation. No synthetic task is created.

For this **first real use only**, after the user returns the Terminal output, Engineering Control must generate a one-time ready-to-copy tooling-control prompt **regardless of whether the run is PASS, ENGINEERING_ACTION_REQUIRED, TOOLING_ACTION_REQUIRED or SAFE_STOP**.

The generated prompt must contain the exact observation fields below when available:

```text
LOCAL_TASK_RUNNER_OBSERVATION_PACKET_BEGIN
FIRST_REAL_RUNNER_OBSERVATION=YES
TOOL=LOCAL_TASK_RUNNER_V0
RUNNER_VERSION=<version>
RUNNER_CORE_IDENTITY_CHECK=PASS|FAIL|UNKNOWN
OPENCODE_VERSION=<version or UNKNOWN>
ROLE=WRITER|OPERATOR|UNKNOWN
TASK_ID=<task id>
TASK_CLASS=T0|T1|T2|T3|UNKNOWN
EXECUTOR=OPENCODE
MODEL=<exact provider/model>
VARIANT=<exact value or null/UNKNOWN>
INPUT_PACKET_SHA256=<sha256 or UNKNOWN>
RUN_ID=<run id or NONE/UNKNOWN>
START_HEAD=<sha or UNKNOWN>
START_BRANCH=<branch or UNKNOWN>
START_WORKTREE_CLEAN=YES|NO|UNKNOWN
EXECUTOR_EXIT_STATUS=<integer or NONE/UNKNOWN>
CHANGED_PATHS=<compact exact list or UNKNOWN>
POLICY_VIOLATIONS=<compact exact list or UNKNOWN>
CHECK_RESULTS=<compact name:exit list or UNKNOWN>
FINAL_STATUS=<status or UNKNOWN>
STOP_REASON=<reason or NONE/UNKNOWN>
RETRY_COUNT=<integer or UNKNOWN>
ELAPSED_TIME=<seconds if available or NOT_EXPOSED>
FIRST_PASS_RESULT=PASS|FAIL|UNKNOWN
HUMAN_INTERVENTION_COUNT=<integer if known or NOT_EXPOSED>
TOKENS_OR_COST_IF_EXPOSED=<value or NOT_EXPOSED>
LOCAL_TEST_RESULT=<summary or UNKNOWN>
EXACT_HEAD_CI_RESULT_WHEN_APPLICABLE=<value or PENDING/NOT_APPLICABLE>
INDEPENDENT_REVIEW_RESULT=<value or PENDING/NOT_APPLICABLE>
INDEPENDENT_REVIEW_BLOCKERS=<compact value or NONE/PENDING>
RUNNER_FLOW_STATUS=PASS|ENGINEERING_ACTION_REQUIRED|TOOLING_ACTION_REQUIRED|SAFE_STOP
TOOLING_ESCALATION_REQUIRED=YES|NO
LOCAL_TASK_RUNNER_OBSERVATION_PACKET_END
```

Engineering Control must place that complete observation packet inside one fenced code block and explicitly tell the user to paste it once into tooling control for the one-time first-real-run workflow-health review.

If deeper evidence is later required, tooling control may ask for specific existing `RUN_ID` artifacts such as `result.json`, `evidence.md` or bounded executor logs. The user should not proactively collect large raw logs.

The code/task outcome itself remains with Engineering Control. This one-time return is operational Runner validation, not a second semantic code review.

## 7. Normal daily workflow after the first observation

After the first real workflow observation is accepted by tooling control, the user normally never reads Runner status fields personally.

The daily sequence is:

```text
USER RUNS ONE ENGINEERING-GENERATED TERMINAL BLOCK
-> USER PASTES COMPLETE TERMINAL OUTPUT BACK TO THE SAME ENGINEERING WINDOW
-> ENGINEERING WINDOW CLASSIFIES CODE + RUNNER HEALTH
```

Then:

```text
RUNNER_FLOW_STATUS=PASS
TOOLING_ESCALATION_REQUIRED=NO
-> Engineering Control continues normal development. No tooling-window visit.

RUNNER_FLOW_STATUS=ENGINEERING_ACTION_REQUIRED
TOOLING_ESCALATION_REQUIRED=NO
-> Engineering Control handles code/test/task/model/provider disposition. No tooling-window visit.

RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED
TOOLING_ESCALATION_REQUIRED=YES
-> Engineering Control explicitly tells the user to return to tooling control and provides the complete one-copy escalation prompt.

RUNNER_FLOW_STATUS=SAFE_STOP
-> Engineering Control classifies the stop. No automatic rerun. If it is a Runner/workflow defect, Engineering Control provides the tooling escalation prompt.
```

The user does not need to inspect the Terminal transcript for these states; Engineering Control is responsible for doing so.

## 8. Evidence retention and no hidden rerun

The exact Runner `RUN_ID` is the primary local evidence handle. Engineering Control should preserve or reference normal Runner result/evidence artifacts in the task evidence trail when applicable.

A failed run is evidence. Do not run the same Runner task again merely to obtain a cleaner observation packet or prettier Terminal output. Engineering Control first classifies the cause and freezes any permitted next run under normal repair/routing rules.

## 9. What first-real-task workflow success means

The first operational observation is successful when genuine project work demonstrates that:

1. the user needed only the expected single Terminal paste for the local Runner stage;
2. the user could return the complete Terminal output once without manually mining telemetry;
3. Engineering Control correctly classified both the application-code result and Runner workflow health;
4. exact Runner/task/model/Git identity was preserved;
5. exactly one Runner/OpenCode attempt occurred;
6. deterministic scope/check gates governed success rather than Writer self-report;
7. evidence was readable enough for Engineering and tooling diagnosis;
8. normal application failures stayed with Engineering Control;
9. genuine Runner/workflow defects produced an explicit one-copy tooling escalation prompt.

This operational success does not prove the underlying code is correct; normal CI and independent engineering review remain separate gates.
