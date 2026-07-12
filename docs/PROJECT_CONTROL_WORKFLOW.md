# Project Control Workflow Policy

## 1. Authority source

GitHub current state is the project fact source. Prompts, memory, reports, local
checkouts, PR bodies, commit titles, test names, and CI-green summaries do not
replace current GitHub verification.

Before any action, verify repository, default branch, exact base/head SHA, PR
state, draft/merged state, changed files, active write lease, and CI.

## 2. Role separation

Project control freezes scope, grants bounded leases, interprets review, and
authorizes finalization. A writer changes only authorized files. The final
independent reviewer is strict read-only and cannot be the writer. Finalization
is a separate expected-head task.

## 3. Governance

- G0: noncritical documentation and presentation.
- G1: metrics, AI explanation, and backtest presentation.
- G2: live public data, Canonical Market State, and strategy.
- G3: risk, TradePlan, human decision, account/order/fill observation, matching.
- G4: credentials, signing, nonce, exchange write, SL/TP, position mutation.

FLP1 is at least G3. FL4 requires a separate G4 execution and security review.

## 4. Fast Launch route

The pre-launch route has two main PRs:

```text
PR A V0-FLP0-PILOT-AND-LONG-TERM-ROADMAP-AUTHORITY-FREEZE
PR B V0-FLP1-DECISION-TO-OUTCOME-OPERATOR-ASSIST-PILOT
```

PR B is one bounded end-to-end vertical pilot PR. Scope-bounded repairs may
remain in the same execution window. Only the final merge candidate receives the
complete external independent review.

Review findings are `BLOCKER` or `FOLLOW_UP`. Only `BLOCKER` prevents merge.

## 5. Standard lifecycle

```text
project-control scope freeze
-> bounded execution
-> exact-head CI
-> external independent review
-> bounded repair when required
-> exact-head re-review
-> separately authorized finalization
```

No writer may mark ready, merge, delete a branch, or start a later phase unless
the exact action is explicitly authorized.

## 6. Finalization gates

Mark Ready and merge require all of the following:

- external independent exact-head review passes;
- project control explicitly authorizes finalization;
- PR, base, head, draft, and merged state match expectations;
- CI passes on the exact head;
- no unresolved `BLOCKER` remains;
- the expected head guard is used where supported.

Do not rebase, reset, amend, force-push, expand scope, change merge method, or
delete branches without explicit authorization.

## 7. Window rotation policy

Rotate when any of the following occurs:

1. a PR is merged;
2. an Issue, Epic, or phase is completed;
3. the project enters a new stage;
4. review plus repair exceeds two rounds;
5. HEAD drift or writer collision occurs;
6. a write lease or permission boundary changes;
7. the window contains multiple PRs, stages, or stale states;
8. old facts may contaminate current decisions;
9. the user repeatedly asks for status;
10. the project switches between Trader Assist V0 and Trade OS;
11. the user requests rotation;
12. several execution, review, repair, or finalization prompts have accumulated.

Required output:

```text
WINDOW_ROTATION_REQUIRED: YES
REASON: <exact reason>
CURRENT_SAFE_STOP_POINT: <repository, PR, branch, SHA, permission, CI, state>
NEXT_WINDOW_HANDOFF_PROMPT: <complete copyable prompt>
```

## 8. Recursive window rotation requirement

Every future handoff must again include:

- current window role;
- repository;
- exact GitHub SHA;
- PR and branch;
- permission and governance level;
- write lease;
- current CI;
- completed work;
- next action;
- stop conditions;
- the complete rotation policy;
- all rotation triggers;
- the required rotation output;
- this recursive requirement itself.

A handoff omitting the recursive requirement is incomplete. The receiving window
must reproduce it again when rotating.

Every handoff must state:

```text
This handoff is not a substitute for current GitHub verification.
Before any action, verify current GitHub state, exact base/head SHA, PR state,
draft/merged status, changed files, active write lease, and CI.
```

## 9. Fast Launch current safe stop

```text
PROGRAM: V0-FAST-LAUNCH
LAST_COMPLETED_IMPLEMENTATION_PR: 11
LAST_POLICY_STATE_PR: 12
ACTIVE_WRITE_LEASE: NONE
NEXT_WINDOW_ROLE: V0 Fast Launch FLP0 external independent Reviewer
NEXT_WINDOW_PERMISSION: STRICT_READ_ONLY
POST_MERGE_NEXT_GATE: V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE
```
