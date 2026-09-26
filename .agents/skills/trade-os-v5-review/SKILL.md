---
name: trade-os-v5-review
description: Enforce fresh Pre-code and Final Independent Review, exact identity binding, canonical GitHub result egress, and COMMENT_ONLY fallback.
---

# Trade OS V5 Review

Thin adapter to the constitution review contract.

## Pre-code Review

Fresh ordinary ChatGPT / High. Read only the exact package, Plan, base,
architecture/contracts, acceptance/adversarial matrix, and minimal governance.
Write the complete structured result to the package Issue/state record.

Route only to PASS, PLAN_REVISE, or CONTROL_REPLAN as defined by the
constitution. Review is incomplete until GitHub result egress succeeds.

## Optional internal Codex review

Use only when genuinely useful and actual child model/reasoning identity is
runtime-verifiable. It is read-only, optional, and never final authority.
Unverifiable identity means skip, not fallback.

## Final Independent Review

Use a fresh ordinary ChatGPT context that did not control or implement the
candidate. Bind to exact current PR/base/head/tree and exact-head CI. Retrieve
review evidence progressively while preserving complete coverage:

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
