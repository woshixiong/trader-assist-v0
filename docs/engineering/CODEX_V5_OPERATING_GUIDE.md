# Trade OS — Codex V5 Operating Guide

**Status:** V5 CANDIDATE GUIDE; V5-A DOES NOT ACTIVATE THIS WORKFLOW

This guide explains the intended operator experience. It is subordinate to the
manifest-selected constitution and exact Development Package.

## 1. Target human/operator flow

After Engineering Control freezes one Development Package and exact base, the
target is one Terminal launch for the primary Codex thread.

The first Codex phase is Plan-only. It may inspect and design implementation
mechanics but may not mutate product source or alter frozen scope/architecture/
authority/acceptance.

Codex writes a canonical Plan/handoff and emits one complete prompt for a fresh
ordinary ChatGPT Pre-code Review.

## 2. Fresh Pre-code Review

The user opens a fresh ordinary ChatGPT window with the supplied review prompt.

The Reviewer reads only the exact Development Package, Plan, base identity,
frozen architecture/contracts/acceptance/adversarial matrix, and minimal review
authority.

It writes its complete structured result to GitHub before the review is
complete.

Routing is deterministic:

~~~text
PASS
-> command resumes the same Codex thread/worktree for implementation

FAIL / PLAN_REVISE
-> command resumes the same Codex thread for plan revision
-> revised plan receives a new fresh Pre-code Review

FAIL / CONTROL_REPLAN
-> prompt returns directly to Engineering Control
~~~

The user does not choose among these routes.

## 3. Implementation and deterministic middle lifecycle

On PASS, resume the same primary Codex thread/session when supported. Default
subagents=0.

Implementation uses focused validation and the frozen package. After V5-B
exists and is qualified, the deterministic controller owns routine middle
transitions:

~~~text
IMPLEMENT
-> FOCUSED VALIDATE
-> COMMIT/PUSH
-> DRAFT PR
-> EXACT-HEAD CI
-> CLASSIFY FAILURE IF ANY
-> REPAIR 1 IF NEEDED
-> REPAIR 2 / HARD ROOT CAUSE IF NEEDED
-> FINAL REVIEW MANIFEST
~~~

The controller is not an agent. Model-mediated CI polling is prohibited.

V5-A has not implemented this controller/bootstrap/validator. Therefore this
guide is not a runnable activation launcher yet.

## 4. Repair routing

~~~text
INITIAL IMPLEMENTATION
REPAIR 1 = normal frozen primary route
REPAIR 2 = manifest-selected hard-root-cause route
THIRD SEMANTIC FAILURE = Engineering Control replan
~~~

Quota, UI, transport, and CI-transport interruptions do not consume semantic
repair budget. Resume the exact durable checkpoint.

## 5. Optional children

Explorer and internal implementation review are optional and never required.

Use at most one optional child at a time, only for genuinely separable bounded
work, only when actual spawned model/reasoning identity is verifiable.

If identity is unverifiable, skip the child. Do not fall back to the primary
model merely to preserve a child stage. Optional children are never final
authority.

## 6. Final Review handoff

After exact-head CI and the required final manifest, emit one complete prompt
for a fresh ordinary ChatGPT Final Independent Review.

The Reviewer uses exact current PR/base/head/tree/diff, exact-head CI, frozen
acceptance/adversarial matrix, and minimal authority/safety rules. It writes
the complete result to GitHub.

If native self-approval is unavailable, use COMMENT_ONLY evidence. Do not
pretend it is a second identity.

A changed head invalidates the old review.

## 7. Conditional closeout

On Final Review PASS, the review output returns a complete Engineering Control
closeout prompt. Mark Ready and Merge remain separate current-human protected
actions and occur only when the closeout context has valid current authority.

Merge never implies deployment/runtime/trading authority.

## 8. Activation dependency

V5-A supplies governance/config/skills/model maps only.

Still required before V5 activation include V5-B controller/bootstrap/
consistency-validator/hook/tests, runtime CLI/GPT-6/permission qualification,
failure-path simulations, exact-head CI, fresh Independent Review, the accepted
Project Instruction replacement, later cleanup/index reconciliation, and the
frozen non-production end-to-end canary requirement.

Do not describe V5 as active merely because the candidate branch or Draft PR
exists.
