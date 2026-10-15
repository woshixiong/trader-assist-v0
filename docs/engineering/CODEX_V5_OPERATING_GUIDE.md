# Trade OS — Codex V5 Operating Guide

**Status:** V5 legacy operating guide; new fast-native-reuse/automatic-closeout candidate in PR #339 is NOT ACTIVE until acceptance

This guide explains the intended operator experience. It is subordinate to the
manifest-selected constitution and exact Development Package.

## 1. Target human/operator flow

Remote Desktop Commander is the formal preferred local execution relay when
connected and quota is available. It is execution transport only, never a
correctness dependency or authority. Offline/quota exhaustion preserves the
same checkpoint and yields one exact human Terminal command or a block.

~~~text
REMOTE_DESKTOP_COMMANDER_STATUS=FORMAL_V5_EXECUTION_RELAY
ONE_EXACT_GENERATED_HUMAN_TERMINAL_COMMAND_OR_BLOCK=REQUIRED
MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT
SHARED_OUTER_LAUNCHER_STDIN=PROHIBITED
~~~

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

On PASS, resume the exact same primary Codex thread/worktree. The same
fail-closed rule applies to PLAN_REVISE. Exact resume is required, not
best-effort. If exact resume is unavailable or cannot be verified, preserve the
checkpoint and return PAUSED_CAPABILITY to Engineering Control; never silently
start a new semantic Codex thread.

~~~text
PRE_CODE_PASS_SAME_THREAD_RESUME_REQUIRED=YES
PLAN_REVISE_SAME_THREAD_RESUME_REQUIRED=YES
EXACT_RESUME_UNAVAILABLE_OR_UNVERIFIABLE=>PAUSED_CAPABILITY/ENGINEERING_CONTROL
SILENT_NEW_SEMANTIC_THREAD_SUBSTITUTION=PROHIBITED
~~~

Default subagents=0.

Implementation uses focused validation and the frozen package. The
baseline-qualified V5-B deterministic controller owns routine middle
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

The V5-B controller/bootstrap/validator is implemented and baseline-qualified.
This guide describes the runnable V5 workflow. The first real non-production
end-to-end canary has passed and the manifest-selected lifecycle is `ACTIVE`.

## 4. Repair routing

~~~text
PLAN           = gpt-6.1-sol / medium
IMPLEMENT      = gpt-6.1-sol / medium
REPAIR 1       = gpt-6.1-sol / medium
REPAIR 2       = gpt-6.1-sol / high
GPT-5.6 V5 FALLBACK = PROHIBITED
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
closeout prompt. Mark Ready and Merge remain two distinct current-human
protected actions. One current user message may conditionally authorize both.

Engineering Control must fresh-verify the exact reviewed head, all required CI,
and no drift against the frozen authorization predicates immediately before
acting. If they all match, it must not ask for a second authorization. If any
predicate changed or is unknown, it fails closed without performing either
action and without consuming the conditional authorization.

~~~text
MARK_READY_AND_MERGE_REMAIN_PROTECTED_ACTIONS=YES
ONE_CURRENT_USER_MESSAGE_MAY_CONDITIONALLY_AUTHORIZE_BOTH=YES
SECOND_AUTHORIZATION_PROMPT_WHEN_FROZEN_PREDICATES_MATCH=PROHIBITED
CHANGED_OR_UNKNOWN_PREDICATE=>FAIL_CLOSED_WITHOUT_CONSUMING_AUTHORIZATION
~~~

Merge never implies deployment/runtime/trading authority.

## 8. Active governance boundary

The activation merge, V5-B controller/bootstrap/consistency validation, baseline
CLI/GPT-6/permission/auto-review/network qualification, protected-action
nonregression, exact-head CI, fresh Independent Review, version-agnostic Project
Instruction bridge, and first real non-production V5 Development Package canary
have passed.

The manifest-selected lifecycle is now `ACTIVE`. The lifecycle, same-thread
resume, CI, review, protected-action, and transport rules above are unchanged.
V5-C cleanup remains a separate later scope and does not block normal product
development.

## Candidate successor direction (not an operative instruction until activation)

This legacy guide documents the previously frozen V5 workflow. The proposed
successor in PR #339 replaces per-slice review and human merge clicking
with large pinned NautilusTrader-native capability packages, one continuous
Codex implementation, cheap local checks, one full final-candidate CI and
one package-level strict independent verification. GitHub native branch
protection, not the user, controls automated Ready/Merge on trusted PASS.
Humans exclusively handle passwords, tokens, SSH/IAM credential grants and
wallet/signing. Existing AWS hosts may run SHA-bound, default-OFF isolated
test/Shadow releases through restricted, preconfigured deployment commands.
Real-capital enabling or production mutation is not implied by GitHub Merge.


## Candidate network-continuity change (not active yet)

Local Mac/FinalShell/RDC failures should never abort semantic work already
recorded in GitHub. For transient network errors: official resume/reconnect
first; 10 seconds x up to 20 safe retries; then durable 5-15 minute
provider-native retries with jitter until recovery/cancel. Persist exact head,
CI run, writer checkpoint and AWS operation id. Never duplicate ambiguous
writes, retry credential failures, poll RDC repeatedly, or rerun successful CI
when only its local observer lost connectivity. Long-horizon unattended
recovery needs an actually installed qualified GitHub/systemd runner; a normal
ChatGPT window does not continue itself when closed.
