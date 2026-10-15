---
name: trade-os-v5-review
description: Enforce fresh Pre-code and Final Independent Review, exact identity binding, canonical GitHub result egress, and COMMENT_ONLY fallback.
---

# Trade OS V5 Review

Thin adapter to the constitution review contract.

## Pre-code Review — HIGH design risk only

Do not require Pre-code Review for LOW/MEDIUM changes or repeated use of an
already accepted HIGH architecture. For materially new HIGH safety architecture,
use fresh ordinary ChatGPT High to inspect Plan, exact scope, contracts and
adversarial scenarios. Record PASS, PLAN_REVISE or CONTROL_REPLAN in GitHub.

## Optional internal Codex review

Use only when genuinely useful and actual child model/reasoning identity is
runtime-verifiable. It is read-only, optional, and never final authority.
Unverifiable identity means skip, not fallback.

## Final Independent Review — HIGH/governance only

Use a fresh ordinary ChatGPT context that did not control or implement the
HIGH/governance candidate. Bind to exact current PR/base/head/tree and exact-head
CI. For LOW/MEDIUM do not fabricate a Final Review; instead require CI and
a separately recorded phase-level product verification for MEDIUM features.
Retrieve HIGH review evidence progressively while preserving complete coverage:

~~~text
PR_BOOTSTRAP=>METADATA_FIRST
PR_SCOPE=>LIST_ALL_CHANGED_FILENAMES_FIRST
FINAL_REVIEW=>REVIEW_EVERY_CHANGED_FILE
PR_PATCH_IO=>FETCH_PER_FILE_OR_BOUNDED_CHUNK
FULL_PR_TIMELINE=>NOT_ROUTINE_REVIEW_INPUT
CI_SUCCESS=>STATUS_AND_LOCATOR_ONLY
RAW_SUCCESS_LOG_INGESTION=PROHIBITED
CI_FAILURE=>MINIMUM_DECISIVE_FAILING_EVIDENCE_ONLY
~~~

Verify every changed path against frozen scope, then semantically review every
changed file. Fetch each patch/file or bounded chunk incrementally; do not skip a
changed file to save context. If a listed patch is unavailable, obtain alternate
exact evidence or the review cannot PASS. Evidence insufficiency, contradiction,
identity drift, or unauthorized paths trigger targeted expansion/fail-closed
Control handling rather than evidence suppression. Write the complete result to
GitHub.

Use native review when the authenticated identity can do so truthfully.
Otherwise use COMMENT_ONLY exact-head evidence. Never misrepresent self-approval
as independent identity.

A changed head requires a new fresh Final Reviewer.

## Stage-based product verification

For MEDIUM milestone checks, independent agents may act as end users and
adversarial testers with *test-only credentials* in an isolated/shadow environment.
Use launch/doctor/drive/evidence/cleanup and 3-5 real feature scenarios. Check
expected and negative behavior; gather logs/output rather than model opinions.
Summarize one deduplicated defect batch with severity, reproduction, owner and
re-test evidence. Muse/Hark Pro output is optional non-authoritative test input:
it never performs production changes or substitutes for required HIGH review.

## Native ownership / global regression checks on required final review

Where a package changes commodity infrastructure, reviewer checks:
`FRAMEWORK_NATIVE_REUSE_REQUIRED` ownership matrix tied to the pinned
version; no project-managed reconnect/OMS/risk/storage/Shadow mechanics when
a fitting native implementation exists. If a claimed native limitation drove
custom code, `OFFICIAL_COMMUNITY_SEARCH_BEFORE_PATCH` must have an exact
reproducer plus relevant official docs/issue/community evidence; lack of a
confirmed upstream fix must be recorded, not invented. Evaluate whether
`ROOT_CAUSE_BEFORE_CODE` was respected and the smallest supported
configuration/adapter chosen. Verify `SYSTEM_WIDE_CAUSAL_VERIFICATION`
of upstream/downstream contracts and GitHub/AWS artifact identity, with
data/Shadow/risk execution negative cases where applicable.

A competing commodity implementation with no demonstrated framework gap is
a review blocker, even if unit tests pass. A behavioral verification that
covers only a single function but claims an end-to-end result is FAIL/BLOCKED.
This is part of the existing final review, not an extra review stage.
