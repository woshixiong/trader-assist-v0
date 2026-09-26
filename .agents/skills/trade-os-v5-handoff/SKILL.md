---
name: trade-os-v5-handoff
description: Emit a zero-decision, GitHub-anchored handoff at every expected stop without using the user as a state or review-result relay.
---

# Trade OS V5 Handoff

Every expected stop emits:

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

For Pre-code PASS or PLAN_REVISE handoffs, target the exact same Codex
thread/worktree. If exact resume is unavailable or unverifiable, emit
PAUSED_CAPABILITY to Engineering Control; never substitute a fresh semantic
thread.

~~~text
PRE_CODE_PASS_SAME_THREAD_RESUME_REQUIRED=YES
PLAN_REVISE_SAME_THREAD_RESUME_REQUIRED=YES
EXACT_RESUME_UNAVAILABLE_OR_UNVERIFIABLE=>PAUSED_CAPABILITY/ENGINEERING_CONTROL
SILENT_NEW_SEMANTIC_THREAD_SUBSTITUTION=PROHIBITED
~~~

Protected actions are never smuggled through a handoff; they require explicit
current human authority. Mark Ready and Merge remain distinct protected
actions, while one current user message may conditionally authorize both after
Final Review PASS. Engineering Control must fresh-verify exact reviewed head,
required CI, and no drift before acting. Matching predicates prohibit a second
authorization prompt; changed or unknown predicates fail closed without
consuming the authorization.

~~~text
MARK_READY_AND_MERGE_REMAIN_PROTECTED_ACTIONS=YES
ONE_CURRENT_USER_MESSAGE_MAY_CONDITIONALLY_AUTHORIZE_BOTH=YES
SECOND_AUTHORIZATION_PROMPT_WHEN_FROZEN_PREDICATES_MATCH=PROHIBITED
CHANGED_OR_UNKNOWN_PREDICATE=>FAIL_CLOSED_WITHOUT_CONSUMING_AUTHORIZATION
~~~
