# Project Control Workflow Policy

This document defines the default project-control workflow for Trader Assist V0 and, where applicable, the broader Trade OS development line.

## 1. Objectives

All project work must optimize for the following priorities, in order:

1. Quality and safety.
2. Project progress.
3. Codex / agentic quota preservation.
4. Overall operating efficiency.

Efficiency must not override safety, review independence, auditability, or repository authority boundaries.

## 2. Tool roles

### ChatGPT project-control windows

Use ChatGPT project-control windows by default for:

- project management;
- scope freeze;
- bounded task design;
- execution prompt generation;
- external review prompt generation;
- finalization prompt generation;
- review report interpretation;
- state reconciliation;
- risk analysis;
- handoff prompt generation;
- V0 / Trade OS sequence management.

ChatGPT project-control windows are read-only by default and must not be treated as code writers unless explicitly authorized.

### Codex

Use Codex only when repository-level engineering execution is required, including:

- code changes;
- local test execution;
- CI reproduction or repair;
- schema / export regeneration;
- bounded code repair;
- commit / push / PR update under explicit write lease.

Codex must not be the default project controller, final independent reviewer, or unbounded end-to-end executor.

### Trae

Use Trae as a local environment, IDE, and terminal configuration assistant only.

Appropriate Trae tasks include:

- IDE setup;
- terminal / shell / PATH / permission issues;
- Python / Node / npm / uv / venv problems;
- gh CLI / Git local command issues;
- dependency installation conflicts;
- Docker / AWS / database / dashboard / SDK setup;
- local environment troubleshooting.

Trae must not be used as the default code writer, project controller, final reviewer, trading permission authority, or live execution authority.

If Codex quota is exhausted, Trae must not automatically replace Codex for critical code development. Prefer a bounded human-executable patch plan or wait for Codex quota recovery.

## 3. Codex usage policy

Default:

```text
CODEX_REQUIRED: NO
```

Set `CODEX_REQUIRED: YES` only when at least one of the following is true:

1. Repository files must be modified.
2. Local tests must be run.
3. CI must be reproduced or repaired.
4. A bounded code repair is required.
5. Schema / export / tests must be regenerated.
6. A commit / push / PR update is explicitly authorized.
7. A large mechanical repository change is required.

Every Codex task must be short, bounded, and verifiable. It must include:

```text
REPOSITORY:
PR_OR_ISSUE:
TASK_ID:
EXPECTED_BASE_SHA:
EXPECTED_HEAD_SHA:
EXPECTED_BRANCH:
EXPECTED_STATE:
WRITE_LEASE:
AUTHORIZED_SCOPE:
FORBIDDEN_SCOPE:
AUTHORIZED_FILES:
FORBIDDEN_FILES:
ACCEPTANCE_CRITERIA:
EXACT_TESTS:
CI_GATES:
ROLLBACK_RULE:
MARK_READY_ALLOWED:
MERGE_ALLOWED:
STOP_CONDITIONS:
```

Codex must not expand scope, start later phases, mark ready, merge, close PRs, or delete branches unless the project-control prompt explicitly authorizes that exact action.

## 4. Trae usage policy

Default:

```text
TRAE_REQUIRED: NO
```

Set `TRAE_REQUIRED: YES` only when at least one of the following is true:

1. Local environment issues block progress.
2. IDE / terminal / shell / PATH / permissions cannot be quickly resolved.
3. A new phase requires Docker / AWS / database / dashboard / SDK setup.
4. Project-control or Codex provides commands but local execution repeatedly fails for environment reasons.
5. Environment configuration is more complex than the code task itself.

Trae output is operational advice, not a project fact source and not an independent review source.

## 5. Review and execution separation

A writer must not be the final independent reviewer of the same PR.

External independent review is strict read-only by default. Review windows must not:

- modify files;
- commit;
- push;
- rebase;
- reset;
- amend;
- update PR metadata;
- submit GitHub reviews;
- comment on PRs;
- request reviewers;
- mark ready;
- merge;
- close PRs;
- delete branches;
- start later phases.

Review must not accept the following as proof:

- writer reports;
- PR descriptions;
- commit titles;
- test names;
- CI green state alone;
- previous window assertions.

Review must verify current GitHub state, exact base/head SHA, full base-to-head diff, final files, schemas, tests, CI jobs/steps/logs where available, authority preservation, and independent attack analysis.

If expected facts differ from current GitHub facts, stop and report state drift. Do not chase HEAD.

## 6. Standard lifecycle

The default lifecycle for each bounded phase is:

```text
A. ChatGPT Project Control
   - scope freeze
   - bounded task design
   - CODEX_REQUIRED / TRAE_REQUIRED decision

B. Codex Execution
   - only if CODEX_REQUIRED = YES

C. External Independent Review
   - strict read-only
   - exact-head review

D. Bounded Repair
   - only if review returns FAIL_CHANGES_REQUIRED
   - usually Codex

E. Re-review
   - strict read-only
   - exact-head

F. Finalization Prompt
   - generated by project control

G. Finalization Execution
   - only after explicit authorization
   - expected-head Mark Ready / merge where applicable
```

If review passes and no code changes are needed, do not start Codex.

If review fails, repair only the blocking findings and preserve the frozen scope.

## 7. Finalization policy

Finalization must be a separate task.

Mark Ready / merge is allowed only when all of the following are true:

- external independent exact-head review passes;
- project control explicitly authorizes finalization;
- PR state matches expectations;
- base SHA matches expectations;
- head SHA matches expectations;
- CI succeeds on the exact head;
- no unresolved blocking findings remain;
- merge uses the expected head SHA when supported.

Do not rebase, reset, amend, force-push, expand scope, change merge method, or delete branches without explicit authorization.

## 8. Window rotation policy

Project-control windows must periodically check whether a new window is needed.

Trigger window rotation when any of the following occurs:

1. The current PR is merged.
2. The current Issue or Epic is completed.
3. The current stage ends and the project is about to enter a new stage.
4. Review plus repair exceeds two rounds.
5. HEAD drift occurs.
6. Writer collision occurs.
7. The write lease is revoked or any permission boundary changes.
8. The window accumulates multiple PRs, multiple stages, or stale states.
9. The user repeatedly needs to ask where the project currently stands.
10. Context becomes long enough that old facts may contaminate current decisions.
11. An old HEAD, old CI result, or old PR state is at risk of being reused.
12. The project switches between Trader Assist V0 and Trade OS.
13. The user explicitly requests a new window.
14. The current window has generated several execution, review, repair, or finalization prompts.

When triggered, output:

```text
WINDOW_ROTATION_REQUIRED: YES

REASON:
<why a new project-control window is required>

CURRENT_SAFE_STOP_POINT:
<the exact repository, PR, stage, permission and review point at which work is safely paused>

NEXT_WINDOW_HANDOFF_PROMPT:
<complete copyable prompt>
```

Do not merely recommend opening a new window. Always generate the complete handoff prompt and identify the current safe stop point.

### Recursive window rotation requirement

Every future project-control handoff must reproduce:

1. the full window-rotation policy;
2. the full rotation trigger set;
3. the required rotation output contract;
4. the `RECURSIVE_WINDOW_ROTATION_REQUIREMENT` itself.

The receiving project-control window must apply the same requirement when it later generates another handoff. This requirement applies to every later handoff generation, not only the first rotation, and must continue recursively across all later project-control windows. A one-time summary or simplified version that cannot propagate the same mechanism must not replace the complete requirement.

## 9. Handoff requirements

Every handoff prompt must include:

```text
PROJECT:
REPOSITORY:
WINDOW_ROLE:
CURRENT_OBJECTIVE:
COMPLETED_SEQUENCE:
CURRENT_AUTHORITY:
CURRENT_MAIN_OR_BASE:
CURRENT_PR_OR_ISSUE:
CURRENT_BASE_SHA:
CURRENT_HEAD_SHA:
CURRENT_BRANCH:
CURRENT_TASK_ID:
CURRENT_STATE:
CURRENT_CI:
ACTIVE_SCOPE:
FORBIDDEN_SCOPE:
CODEX_USAGE_POLICY:
TRAE_USAGE_POLICY:
REVIEW_POLICY:
FINALIZATION_POLICY:
WINDOW_ROTATION_POLICY:
RECURSIVE_WINDOW_ROTATION_REQUIREMENT:
KNOWN_OPEN_ITEMS:
NEXT_RECOMMENDED_ACTION:
STOP_CONDITIONS:
```

The `RECURSIVE_WINDOW_ROTATION_REQUIREMENT:` field must state at minimum:

```text
Every future handoff must again include the complete window-rotation policy, its trigger conditions, the required rotation output format, and this recursive requirement itself.
```

A handoff that omits `RECURSIVE_WINDOW_ROTATION_REQUIREMENT:` is incomplete and must not be treated as a valid project-control handoff.

Every handoff must include this warning:

```text
This handoff is not a substitute for current GitHub verification.
Before any action, verify current GitHub state, exact base/head SHA, PR state, draft/merged status, changed files, and CI.
```

## 10. Standard project-control output

When arranging the next task, project control should output:

```text
TASK_ID:
REPOSITORY:
CURRENT_AUTHORITY:
CURRENT_MAIN:
CURRENT_PR_OR_ISSUE:
CURRENT_HEAD:
TASK_TYPE:
CODEX_REQUIRED: YES / NO
WHY_CODEX_REQUIRED:
TRAE_REQUIRED: YES / NO
WHY_TRAE_REQUIRED:
WRITE_LEASE: YES / NO
ROLE:
AUTHORIZED_SCOPE:
FORBIDDEN_SCOPE:
AUTHORIZED_FILES:
FORBIDDEN_FILES:
ACCEPTANCE_CRITERIA:
EXACT_TESTS:
CI_GATES:
ROLLBACK_RULE:
WINDOW_ROTATION_REQUIRED: YES / NO
NEXT_STEP:
```

## 11. Current policy summary

```text
ChatGPT = project control / review orchestration / prompt generation / status reconciliation
Codex = necessary repository write / tests / CI / bounded repair
Trae = local environment / IDE / terminal configuration
External Review = strict read-only / exact-head / no writer provenance
Finalization = explicit authorization / expected-head guarded merge
```
