---
name: trade-os-writer-preflight
description: Verify a frozen Trader Assist Writer Task Packet, exact Git/worktree identity, scope, authority attestations and stop conditions before any local coding-agent mutation.
---

# Trade OS Writer Preflight

Use this skill at the start of a Trader Assist Writer stage.

1. Read the frozen Task Packet and verify its packet/hash identity.
2. Verify selected executor/model/reasoning, repository/worktree and exact base/expected HEAD.
3. Require controller-supplied `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`; for material work also require `ENGINEERING_PREFLIGHT_GATE=PASS`.
4. Verify the governance/preflight attestation is bound to the same main/base/worktree identity as the Task Packet and actual workspace. Drift or mismatch => return control.
5. Verify allowed/prohibited paths, invariants, focused validation, repair stage, stop conditions and retained user gates.
6. Consume the packet's normalized required authority assertions and provenance locators. Do not reread full Unified V2, full preflight, full Rules Index, full Issue history or broad governance/docs by default.
7. If a concrete conflict or missing material fact appears, read only the minimum canonical source; unresolved material conflict => return to Engineering Control.
8. When `EXECUTOR=CODEX_CLI`, require exact model, reasoning effort and Web Search state from the launch contract. Do not silently infer or change them.
9. Record concise preflight facts before mutation.

Return `L1_DECISION_REQUIRED` without implementation for stale/ambiguous packet, identity drift, capability/permission mismatch, allowlist expansion, new dependency/provider, new material design decision, authority conflict or unapproved gate crossing. Never solve a preflight failure by silently changing model/executor/reasoning/Web-Search state/scope.