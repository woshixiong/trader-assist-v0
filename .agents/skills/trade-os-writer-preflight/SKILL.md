---
name: trade-os-writer-preflight
description: Verify a frozen Trader Assist Writer Task Packet, exact Git/worktree identity, scope, authority attestations and stop conditions before any local coding-agent mutation.
---

# Trade OS Writer Preflight

Use this skill at the start of a Trader Assist Writer stage.

1. Read the frozen Task Packet exactly as supplied and verify its packet/hash identity when provided.
2. Verify selected executor/model/reasoning, repository/worktree, exact base/expected HEAD and declared worktree state.
3. Require the controller-supplied `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`; for material work also require `ENGINEERING_PREFLIGHT_GATE=PASS`.
4. Verify allowed paths, prohibited scope, invariants, exact focused validation plan, repair stage, SAFE_STOP conditions and retained user gates.
5. Treat Engineering Control's preflight attestation as the resolved control-plane authority for the stage. **Do not reread the full Unified V2, full Mandatory Preflight, full Project Rules Index, full Issue history or broad governance/docs corpus by default.**
6. Read only exact task authorities/sections explicitly referenced by the packet. If a concrete conflict or missing material fact appears, read the minimum canonical source; if still material, stop and return to Engineering Control.
7. When `EXECUTOR=CODEX_CLI`, require the exact model, reasoning effort and Web Search state from the launch contract. Do not silently infer or change them.
8. Record concise preflight facts before mutation.

Return `L1_DECISION_REQUIRED` without implementation for stale/ambiguous packet, identity drift, capability/permission mismatch, allowlist expansion, new dependency/provider, new material design decision, authority conflict or unapproved gate crossing. Never solve a preflight failure by silently changing model/executor/reasoning/Web-Search state/scope.