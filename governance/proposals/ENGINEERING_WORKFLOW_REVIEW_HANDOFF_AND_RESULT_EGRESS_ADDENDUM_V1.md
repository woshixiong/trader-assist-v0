# ENGINEERING_WORKFLOW_REVIEW_HANDOFF_AND_RESULT_EGRESS_ADDENDUM_V1

## Purpose

Extend the workflow continuity proposal with a strict Review handoff lifecycle.

## Review Handoff Lifecycle

When Engineering Control reaches an Independent Review boundary:

1. Canonical preparation must complete first.

GitHub must contain:
- review target;
- exact PR/head identity;
- scope/evidence locations;
- acceptance criteria;
- required review constraints.

2. Reviewer launcher generation is mandatory.

The Engineering Control window must directly provide a short launcher prompt.

The launcher must not duplicate canonical GitHub content.

It only provides:
- repository;
- PR or artifact locator;
- reviewer role;
- review objective;
- output requirement.

3. Review result egress requirement.

The reviewer launcher must require:

- review result written to GitHub;
- APPROVE / REQUEST_CHANGES / COMMENT state;
- evidence-backed findings.

Chat-only review results are not canonical.

4. Review result reconciliation.

After the user reports that review execution is complete, Engineering Control must independently read GitHub.

It must verify:
- review exists;
- reviewer result exists;
- timestamp/state is current;
- result belongs to the expected PR/head.

The user is not required to copy review output back into chat.

## State Model

```text
REVIEW_PREPARATION_COMPLETE
        |
        v
REVIEW_LAUNCHER_ISSUED
        |
        v
WAITING_FOR_REVIEW_RESULT
        |
        v
REVIEW_RESULT_MATERIALIZED_IN_GITHUB
        |
        v
NEXT_STAGE_ROUTING
```

No transition may rely only on chat confirmation.

## Failure Closed Conditions

If GitHub contains no review result after claimed completion:

state remains:

WAITING_FOR_REVIEW_RESULT

Do not infer completion from conversation state.
