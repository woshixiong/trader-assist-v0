---
name: trade-os-v5-handoff
description: Emit a zero-decision, GitHub-anchored handoff at every expected stop without using the user as a state or review-result relay.
---

# Trade OS V5 Handoff

Every stop requiring a human or new model context emits (routine automated
continuation stays in GitHub without human relay):

~~~text
DECISION=
CANONICAL_GITHUB_REF=
NEXT_DESTINATION=
NEXT_ACTION=
COPY_PASTE_COMMAND_OR_PROMPT=
~~~

~~~text
MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT
SHARED_OUTER_LAUNCHER_STDIN=PROHIBITED
~~~

Remote Desktop relay loss preserves the checkpoint and emits one exact manual
Terminal command or blocks; it never changes authority or consumes repair.

Before emitting a terminal result or blocker, fresh-read the canonical task/PR
state and reconcile any already-advanced state idempotently.

The GitHub locator contains the durable detail. Chat remains compact. The
copy-paste command/prompt must be complete and must carry the exact role, target,
identity, scope/authority boundary, required next operation, and exact canonical
object locators for package state, plan/review result, CI, and next evidence when
available. Never replace a known exact object locator with a generic instruction
to read an Issue/PR history.

~~~text
EXACT_CANONICAL_LOCATOR_AVAILABLE=>HANDOFF_MUST_CARRY_EXACT_OBJECT
GENERIC_ISSUE_OR_PR_HISTORY_INSTRUCTION_WHEN_EXACT_LOCATOR_KNOWN=PROHIBITED
~~~

For a required HIGH Pre-code PASS or PLAN_REVISE handoff, target the exact same
Codex thread/worktree. LOW/MEDIUM use recorded GitHub checkpoint recovery on
lost sessions, never rerunning completed work. If exact resume is unavailable or unverifiable, emit
PAUSED_CAPABILITY to Engineering Control; never substitute a fresh semantic
thread.

~~~text
PRE_CODE_PASS_SAME_THREAD_RESUME_REQUIRED=YES
PLAN_REVISE_SAME_THREAD_RESUME_REQUIRED=YES
EXACT_RESUME_UNAVAILABLE_OR_UNVERIFIABLE=>PAUSED_CAPABILITY/ENGINEERING_CONTROL
SILENT_NEW_SEMANTIC_THREAD_SUBSTITUTION=PROHIBITED
~~~

Protected and credential actions are never smuggled through handoffs.
Under this candidate's **future activated policy**, ordinary GitHub Mark
Ready/Merge/merged branch deletion become deterministic automatic closeout
actions once trusted CI, phase/independent review and branch protection permit,
not repeated human click prompts. Existing main V5 still governs this Draft PR.
Secrets, credential grants, wallet/signing and real-money exchange writes are
human-only; bounded test-only deployments are allowed only after separate
human setup of an isolated scope.
