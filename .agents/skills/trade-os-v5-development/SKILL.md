---
name: trade-os-v5-development
description: Execute a frozen V5 development package through Plan-only, Pre-code Review, same-thread implementation, focused validation, bounded repair, and publication handoff.
---

# Trade OS V5 Development

Thin adapter only; do not duplicate the constitution.

~~~text
MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT
SHARED_OUTER_LAUNCHER_STDIN=PROHIBITED
~~~

Before local publication containing `.github/workflows/**`, require current
human-backed `GH_WORKFLOW_SCOPE_VERIFIED=YES`; do not silently refresh OAuth.

1. Bootstrap exact package/base/runtime identity first.
2. Run Plan-only with no product-source mutation.
3. Persist the Plan and emit the complete fresh Pre-code Review prompt.
4. Review PASS and PLAN_REVISE must resume the exact same primary Codex
   thread/worktree. If exact resume is unavailable or unverifiable, preserve the
   checkpoint and return PAUSED_CAPABILITY to Engineering Control; never
   silently substitute a new semantic Codex thread. CONTROL_REPLAN returns to
   Engineering Control. The user does not select the route.

~~~text
PRE_CODE_PASS_SAME_THREAD_RESUME_REQUIRED=YES
PLAN_REVISE_SAME_THREAD_RESUME_REQUIRED=YES
EXACT_RESUME_UNAVAILABLE_OR_UNVERIFIABLE=>PAUSED_CAPABILITY/ENGINEERING_CONTROL
SILENT_NEW_SEMANTIC_THREAD_SUBSTITUTION=PROHIBITED
~~~
5. Default subagents=0. At most one optional bounded child may run when actual
   child identity is verifiable; otherwise skip it with no fallback.
6. Implement -> smallest decisive validation -> observe -> bounded in-scope
   repair.
7. Semantic budget is initial + Repair1 + Repair2; third semantic failure or a
   new root/scope/architecture/security/authority issue returns to Control.
8. After publication, hand exact head to the deterministic CI stage. Do not
   model-poll CI.
9. V5-A does not supply the controller; use this skill as candidate procedure
   only until V5-B is implemented and qualified.
