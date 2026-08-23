---
name: trade-os-writer-preflight
description: Verify a frozen Trader Assist Writer Task Packet, exact Git/worktree identity, scope, authority attestations and stop conditions before any local coding-agent mutation.
---

# Trade OS Writer Preflight

Use this skill at the start of a Trader Assist Writer stage.

1. Read the frozen Task Packet exactly as supplied.
2. Verify selected executor/model/reasoning, repository/worktree, branch/detached state, exact base/expected HEAD and clean/declared worktree state.
3. Require `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`; for material work also require `ENGINEERING_PREFLIGHT_GATE=PASS`.
4. Verify allowed paths, prohibited scope, invariants, exact validation plan, repair stage, SAFE_STOP conditions and retained user gates.
5. Read only the narrow task authorities explicitly referenced unless a real conflict requires escalation.
6. Record preflight facts before mutation.

Return `L1_DECISION_REQUIRED` without implementation for stale/ambiguous packet, identity drift, capability/permission mismatch, allowlist expansion, new dependency/provider, new material design decision, authority conflict or unapproved gate crossing. Never solve a preflight failure by silently changing model/executor/scope.