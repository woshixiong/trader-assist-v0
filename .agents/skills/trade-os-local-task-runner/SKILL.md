---
name: trade-os-local-task-runner
description: Generate and execute the accepted Local Task Runner V0 one-paste OpenCode workflow for a frozen Trader Assist task, then classify Runner health and produce a ready-to-copy tooling escalation prompt when needed.
---

# Trade OS Local Task Runner

Use only after Engineering Control has completed the mandatory live preflight and Router V2 has already selected `OPENCODE` for the bounded stage.

Read before generating the command:

- `governance/LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`
- `governance/LOCAL_TASK_RUNNER_V0_OPERATOR_OBSERVABILITY_GUIDE_V1_2026-08-24.md`

## Required behavior before and during execution

- Do not manufacture a synthetic first-real-task benchmark. Use the first naturally occurring real OpenCode-compatible project stage.
- Do not use the Runner to override Router V2 or choose a model. Freeze the exact `provider/model` first.
- Resolve `LOCAL_TASK_RUNNER_HOME="${TRADE_OS_LOCAL_RUNNER_HOME:-$HOME/trade-os-local-runner-v0-candidate}"`.
- Verify the accepted Runner version/core identity before execution; drift => `LOCAL_TASK_RUNNER_IDENTITY_DRIFT` and tooling control.
- Use a bounded clean Git worktree with exact start branch/HEAD.
- Generate the complete `local-task-packet-v0` JSON for the user. Never ask the user to hand-edit Runner JSON or calculate its hash.
- Keep `expected_git.required=true`, exact head/branch and the minimum complete `allowed_changed_paths` allowlist.
- Use deterministic argv-based checks from the frozen Task Packet. Do not add shell/Git-mutation validation escape routes.
- Generate **one complete ordinary-Terminal paste block** that performs Runner identity preflight, packet creation, SHA-256 calculation, `validate`, exactly one `run`, RUN_ID/result/evidence capture and compact telemetry.
- `runner.py run` is executed once. No hidden retry, automatic resume or silent model fallback.
- An OpenCode exit code of `0` is not success by itself; final Runner policy/check status governs.
- Do not commit/push, Mark Ready, merge, deploy or access production/private trading authority unless a separate current gate explicitly authorizes that distinct action.
- The Terminal block must finish by printing the mandatory `LOCAL_TASK_RUNNER_STATUS_BEGIN ... END` sentinel defined in the operator observability guide.
- On the first naturally occurring real Runner task, the block must also expose enough exact observation fields for Engineering Control to generate the one-time first-real-run tooling prompt after the user returns the Terminal output.

## Mandatory post-run Engineering behavior

The user's normal post-run action is to paste the **complete Terminal output once** back into the same Engineering window.

The user must not be asked to search the output for Runner fields or decide whether the Runner is healthy.

After receiving the Terminal output, Engineering Control must review two things in the same response:

```text
NORMAL_ENGINEERING_OUTCOME
+ RUNNER_WORKFLOW_HEALTH
```

Engineering Control must derive and state one of:

```text
RUNNER_FLOW_STATUS=PASS
RUNNER_FLOW_STATUS=ENGINEERING_ACTION_REQUIRED
RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED
RUNNER_FLOW_STATUS=SAFE_STOP
```

The exact classification contract and trigger list are defined in the operator observability guide.

### Normal code/task problems stay here

```text
normal application-code or frozen-test failure -> Engineering Control
scope/authority ambiguity -> Engineering Control / L1 SAFE_STOP
model/provider availability/degradation -> Engineering Control / Router; no silent substitution
```

Do not send the user to tooling control for an ordinary code/test bug.

### Runner/workflow problems go to tooling control

Mandatory tooling-escalation triggers include at least:

```text
LOCAL_TASK_RUNNER_IDENTITY_DRIFT
accepted Runner identity/hash cannot be proven
Runner schema/result corruption
result/evidence missing, unreadable or contradictory
Runner state/evidence disagreement
Runner CLI preflight defect or wrong accepted OpenCode surface
false Runner success despite failed deterministic check
false Runner success despite non-empty policy violations
changed-path policy false/inconsistent/out-of-allowlist miss
hidden/duplicate runner.py run
RETRY_COUNT > 0 without separately frozen authority
silent model/provider/variant substitution
silent worktree/branch/HEAD/authority substitution
mandatory final sentinel absent/malformed and not reconcilable
insufficient authoritative Runner state to classify safely
```

Engineering Control must also check these workflow red flags from the returned Terminal transcript:

- user was asked to manually edit Runner JSON or hashes;
- user was asked for a second manual OpenCode prompt/paste in the same frozen stage;
- `runner.py run` executed more than once without a new Engineering disposition;
- effective model/variant differs from the Router-frozen exact values;
- Runner identity verification was skipped or failed;
- start branch/HEAD mismatched the frozen task;
- worktree was dirty before launch without explicit frozen handling;
- changed paths exceeded the allowlist;
- policy violations were non-empty while the flow claimed PASS;
- a required check failed while the flow claimed PASS;
- retry count exceeded zero without a separately authorized new run;
- result/evidence/state was missing or contradictory;
- model/provider/variant/worktree/branch/HEAD/authority changed silently after failure;
- ordinary application-code failure was incorrectly routed to tooling control;
- user was asked to manually mine Runner health fields from the Terminal transcript.

## Mandatory tooling escalation UX

If Engineering Control classifies:

```text
RUNNER_FLOW_STATUS=TOOLING_ACTION_REQUIRED
```

or later determines that a `SAFE_STOP` is a Runner/workflow defect, the Engineering reply must:

1. clearly say that tooling control is required;
2. tell the user not to rerun automatically;
3. keep normal code diagnosis separate;
4. provide **one complete ready-to-copy prompt in a single fenced code block**;
5. populate it from exact returned evidence and use `UNKNOWN` for unknown facts.

Use the `TOOLING_CONTROL_ESCALATION_PROMPT_BEGIN ... END` contract from the operator observability guide. The user must not compose this packet manually.

## First real use — one-time tooling return

For the first naturally occurring real Runner project use only, Engineering Control must generate a ready-to-copy first-real-run observation prompt **regardless of PASS/FAIL classification** after the user returns the Terminal output.

Place the full `LOCAL_TASK_RUNNER_OBSERVATION_PACKET_BEGIN ... END` block from the operator observability guide inside one fenced code block and tell the user to paste it once into tooling control.

This one-time return validates the Runner workflow itself. The application-code outcome remains with Engineering Control.

After tooling control accepts the first-real-run workflow observation, routine successful Runner tasks require no tooling-window visit.

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

For first real use, collect these naturally inside the normal task evidence trail; do not create a separate benchmark task.

The user is not the telemetry collector. Engineering Control extracts/classifies these facts from the returned Terminal/result evidence.

## No hidden rerun

A failed run is evidence. Do not automatically rerun merely to clean up the output or obtain a PASS. Engineering Control must first classify the failure and freeze any permitted new run under the normal repair/routing rules.
