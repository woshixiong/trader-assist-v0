---
name: trade-os-v4-ci
description: Wait for exact-head Trader Assist CI with zero model use and emit only a compact terminal projection plus bounded decisive failure evidence.
---

# Trade OS V4 CI

Required inputs:

```text
REPOSITORY
PR_NUMBER
EXPECTED_EXACT_HEAD
REQUIRED_CHECKS_OR_WORKFLOWS
```

This phase is `M0_DETERMINISTIC_MECHANICAL`:

```text
MODEL_REQUIRED=NO
MODEL_MEDIATED_CI_POLLING=PROHIBITED
RAW_SUCCESS_LOG_INGESTION=PROHIBITED
```

Use a provider-native blocking waiter such as `gh pr checks --watch` or an
equivalent deterministic API waiter. Verify the PR head equals the expected
head before waiting and at terminal readback. Identity drift wakes Engineering
Control and invalidates old-head CI.

Emit only PR/head/tree, terminal state/result, required checks, exact run/job
locators, failed-step locator when any, artifact metadata, and next event.
All-green advances mechanically to `REVIEW_NEEDED` and wakes one fresh final
Independent Reviewer. Do not read success logs.

On failure, collect the exact failed run/job/step and minimum decisive excerpt,
then classify it before rerun or mutation. A known transient gets at most one
same-head rerun when currently authorized. Semantic/new-root/ambiguous failure
wakes Engineering Control. Never Mark Ready, merge, deploy, or cross another
retained gate.
