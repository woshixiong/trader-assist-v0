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

## 1A. Frozen route selection and RDC necessity

The active V5 constitution already defines A = deterministic/mechanical
(provider-native or zero-model), B = small frozen bounded semantic work
(fresh ordinary ChatGPT Writer), C = large coherent multi-step coding
(manifest-selected Codex CLI), and D = unresolved architecture/security/
authority ambiguity (Engineering Control resolves and refreezes).
Engineering Control freezes the route; a user does not routinely choose
Codex versus ordinary ChatGPT once authority and evidence fix it. Route
selection alone is **not** actual-provider/model-identity attestation.
The Codex profile in section 4 applies to Route C, not a global ban on
the frozen ordinary ChatGPT Route B.

AGENTS.md already requires the four-part RDC necessity test: local-only
action/evidence, no native lower-cost equivalent, a decisive call, and
bundled operations. GitHub-native Issue/PR/file/CI evidence requires **zero**
RDC calls and no model-mediated status polling. RDC is a transport, not
an authority or routine CI monitor. These restrictions are unchanged.

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


## 9. Exact-head CI transport and native evidence (P1A only)

The existing deterministic `scripts/control/v5_ci_waiter.py` retains its
**60-second default** normal pending-CI poll. Only a *positively classified*
transient **read** error (HTTP 408/500/502/503/504, TLS/EOF/connection reset)
uses the independent `--transport-retry-seconds` timer (**10 seconds default**),
with a maximum of **20 consecutive transport failures** before
`PAUSED_TRANSPORT`. A complete valid check-runs read resets the count;
a PR-head-only read does not. The overall deadline, pre-wait and terminal
exact-head checks, structured checkpoint, and `gh run watch` fallback remain.
Auth/permission/OAuth/401/403/429, rate limits, quotas, missing CLI executable,
ambiguous queries, writes and semantic failures are **not** rapid-retried.

GitHub's qualified Ubuntu/Python 3.12 CI provides authoritative native test
execution. Exact NautilusTrader **2.0.0rc5** evidence belongs to the
qualified Nautilus GitHub jobs, not to an unqualified local Mac environment.
Required `contracts`, `nautilus-pilot`, `vnext-g4` and `e4-capture` must
have terminal **PASS at the current exact PR HEAD**, with relevant native
steps actually executed; skipped, missing, old-head or unexecuted results
are not PASS. Local macOS absence is not evidence of running Linux/rc5 tests.
CI green is necessary, not independent Final Review or tool activation.

P1A deliberately does **not** implement/fix the original blocked PR #300's
B1/B2/B3 controller and Final Review admission findings or B4 actual-provider
identity-attestation defect. Their evidence and separate closure remain with
Engineering Control. Packet 2's Mac foreground Terminal execution is deferred.
Neither this guide nor a CI success grants Mark Ready, merge, deployment,
runtime, credential, wallet, exchange/order or real-capital authority.
