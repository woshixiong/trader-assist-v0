---
name: trade-os-v4-development
description: Execute one frozen V4 development package through Plan-only, Goal-preserving implementation, focused validation, bounded repair, and publication checkpoint.
---

# Trade OS V4 Development

Use after V4 bootstrap passes.

1. **Plan-only:** inspect the repository and select implementation order and
   mechanics without mutation. The plan cannot change scope, product behavior,
   architecture authority, protected actions, or acceptance criteria.
2. Record `PLAN_BOUNDARY_CHECK=PASS` and continue automatically when compliant.
   Otherwise return one exact blocker to Engineering Control.
3. Preserve one package-scoped Goal, thread, worktree, Writer, and checkpoint.
4. Iterate edit -> smallest decisive focused test -> observe -> bounded in-scope
   repair. Use the frozen validation plan; never turn an unrun gate into PASS.
5. Stop and return to Control for a new root cause, architecture/provider/
   dependency choice, scope/allowlist expansion, security/authority issue, or
   exhausted repair budget.
6. Run a fresh read-only Codex Code Review for large packages. It may identify
   findings but cannot edit or provide final independent acceptance.
7. Repair ordinary in-scope findings with the same Writer, rerun decisive
   gates, then commit, push, and open a Draft PR when authorized.
8. Checkpoint the exact published head at `CI_PENDING`. Do not semantically poll
   CI; hand the exact head to the V4 CI skill.

Perform every safe authorized action available. Do not request routine user
confirmation or use the user as a transport bus.
