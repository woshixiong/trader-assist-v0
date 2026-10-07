# Trade OS — Codex V5 Operating Guide

**Status:** V5 ACTIVE GUIDE; FIRST REAL CANARY PASSED

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

## 8. Frozen Route B/CI efficiency candidate (Packet 1)

A frozen small Route B package is implemented by a **fresh ordinary ChatGPT
High** Writer through the approved GitHub-native surface, not through Codex or
Remote Desktop Commander. Route A is deterministic/no-model, C retains the
original Codex primary and exact Pre-code thread/worktree resume, and D is
Engineering Control-only. Identity, role, stage, canonical independent Pre-code
PASS, nonduplicate semantic event and exact head must be established before
the admitted entrypoint can execute. A pure controller guard cannot police
provider calls deliberately made outside that entrypoint.

Before validation select the Control-frozen qualified evidence surface: local
focused checks where available; GitHub V0 Ubuntu/Python 3.12 whole-repository
tests; GitHub E4 Linux x86_64/Python 3.12/Nautilus 2.0.0rc5 native tests; or
separately **human-authorized** target-host evidence. Prefer existing qualified
GitHub native CI over emulating its environment on a limited Mac. A missing,
skipped, wrong-head or unexecuted required test is not a PASS.

Use the deterministic waiter for status polling, **60 s by default**. Only
classified transient GitHub *reads* use **10 s retry** (max **20 consecutive**
failures; reset after successful poll), with overall timeout preserved.
401/403/429, rate limit/quota, auth, permission and semantic failure do not
receive fast network retries. Writes with ambiguous outcomes require canonical
readback before any retry. Neither Codex nor RDC is a CI polling agent.

Use a single existing same-head CI run when it meets all frozen requirements;
do not duplicate-dispatch on an existing valid run. Final independent-review
readiness requires exact-head completed PASS on *all* frozen required checks,
plus native proof that their mandatory test steps really executed. Pending,
skipped or missing proof blocks reviewer admission. The fresh Reviewer reads
the GitHub PR/evidence directly and writes the full result back to GitHub;
do not use RDC to relay native evidence. Material tool/session/retry changes
require independent tool acceptance and separate user activation authority.

**Packet 2 is not implemented or qualified here:** macOS foreground Terminal
visibility, provider-native Codex session/transport retry and recovery remain
a separately frozen and reviewed pilot. This candidate does not create a
ChatGPT callback or authorize a new executor, provider, deployment, runtime,
target-host test, credential or trade operation.

## 9. Active governance boundary

The activation merge, V5-B controller/bootstrap/consistency validation, baseline
CLI/GPT-6/permission/auto-review/network qualification, protected-action
nonregression, exact-head CI, fresh Independent Review, version-agnostic Project
Instruction bridge, and first real non-production V5 Development Package canary
have passed.

The manifest-selected lifecycle is now `ACTIVE`. The lifecycle, same-thread
resume, CI, review, protected-action, and transport rules above are unchanged.
V5-C cleanup remains a separate later scope and does not block normal product
development.
