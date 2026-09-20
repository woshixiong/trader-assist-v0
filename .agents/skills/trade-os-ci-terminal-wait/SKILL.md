---
name: trade-os-ci-terminal-wait
description: Wait for exact-head GitHub CI without model polling, emit a compact terminal projection, and collect only bounded decisive failure evidence.
---

# Trade OS CI Terminal Wait

Use this skill after an exact PR head has been published and semantic Writer work has checkpointed at `CI_PENDING`.

## Inputs

Require:

```text
REPOSITORY
PR_NUMBER
EXPECTED_EXACT_HEAD
REQUIRED_CHECKS_OR_WORKFLOWS (when frozen by the task)
```

Fail closed on missing exact identity.

## Zero-model contract

```text
CLASS=M0_MECHANICAL_STATE
MODEL_REQUIRED=NO
MODEL_MEDIATED_POLLING=PROHIBITED
RAW_SUCCESS_LOG_INGESTION=PROHIBITED
```

A provider-native blocking waiter such as:

```bash
gh pr checks "$PR_NUMBER" --watch --fail-fast
```

or an equivalent GitHub API/check-suite waiter owns the wait. Do not interleave semantic model turns between polls.

## Exact-head guards

Before waiting and again at terminal readback:

1. Read the PR exact head through GitHub.
2. Require it equals `EXPECTED_EXACT_HEAD`.
3. Read only the required check/run metadata.
4. If the head changed, emit `IDENTITY_DRIFT` and wake Engineering Control; do not attach old CI to the new head.

## Terminal projection

Emit one compact deterministic record:

```text
PR_NUMBER=
EXACT_HEAD=
EXACT_TREE=
CI_TERMINAL=YES|NO
CI_RESULT=ALL_GREEN|FAILED|CANCELLED|TIMED_OUT|IDENTITY_DRIFT|INCOMPLETE
REQUIRED_CHECKS=
RUN_JOB_LOCATORS=
FAILED_STEP_LOCATOR=
ARTIFACT_METADATA=
NEXT_EVENT=REVIEW_NEEDED|WAKE_ENGINEERING_CONTROL|WAIT
```

On `ALL_GREEN`, do not read success logs. Mechanically transition to `REVIEW_NEEDED` and wake exactly one fresh authority-bearing Reviewer.

## Failure evidence

On failure:

1. identify the exact failed run/job/step;
2. collect only the minimum decisive failed-step excerpt needed for classification;
3. classify a known deterministic transient/mechanical class only when the active governance/task contract explicitly permits it;
4. otherwise emit `WAKE_ENGINEERING_CONTROL`.

Do not:
- read entire raw logs by default;
- rerun CI before classification;
- redispatch a semantic Writer blindly;
- reuse the prior authority-bearing Reviewer after a material head change;
- Mark Ready, merge, deploy, or cross any retained user gate.

A known same-head transient rerun remains bounded by current governance; this skill does not create retry authority.
