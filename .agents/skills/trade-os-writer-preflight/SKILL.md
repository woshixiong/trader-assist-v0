---
name: trade-os-writer-preflight
description: Verify a frozen Trader Assist Writer Task Packet, exact Git/worktree identity, scope, authority attestations and stop conditions before any local coding-agent mutation.
---

# Trade OS Writer Preflight

Use this skill at the start of a Trader Assist Writer stage.

1. Read the frozen Task Packet and verify its packet/hash identity.
2. Verify selected executor/model/reasoning, repository/worktree and exact base/expected HEAD.
3. Require controller-supplied `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`; for material work also require `ENGINEERING_PREFLIGHT_GATE=PASS`.
4. Verify the governance epoch and preflight binding key are bound to the same Task Packet, exact base/head, execution surface and actual workspace. If unchanged, consume the existing bound attestation; do not recursively reload governance. Drift or mismatch => return control for recomputation.
5. Verify the Control Capsule and completed-work ledger. If this named workstream is already terminal/completed, semantic redispatch is prohibited unless Engineering Control records a new explicit disposition.
6. Verify allowed/prohibited paths, invariants, focused validation, repair stage, stop conditions and retained user gates.
7. Consume the packet's normalized required authority assertions and provenance locators. Do not reread full Unified V2, full preflight, full Rules Index, full Issue history or broad governance/docs by default.
8. If a concrete conflict or missing material fact appears, read only the minimum canonical source; unresolved material conflict => return to Engineering Control.
9. For a known large file, read the exact symbol/heading/range first; load the full file only when whole-file semantics are materially required.
10. When `EXECUTOR=CODEX_CLI`, require exact model, reasoning effort and Web Search state from the launch contract. Verify the actual installed CLI identity and required capabilities; do not fail solely on a stale patch-version snapshot unless the task proves an exact version dependency.
11. Verify `SEMANTIC_READINESS=PASS`. Do not require publication-only GitHub auth/push/PR/result-egress readiness before semantic mutation unless the packet proves that capability is an irreducible semantic prerequisite.
12. Record concise preflight facts before mutation.

If execution is a continuation after quota/capacity interruption, verify the same task/authority/workspace/checkpoint and exact session/thread when recoverable. Exact continuation is not a new semantic retry; restarting from the original task is prohibited by default.

Return `L1_DECISION_REQUIRED` without implementation for stale/ambiguous packet, identity drift, **semantic** capability/permission mismatch, allowlist expansion, new dependency/provider, new material design decision, authority conflict or unapproved gate crossing. A publication-only transport/auth problem is returned as a later operator/publication boundary and must not be mislabeled as semantic unreadiness. Never solve a preflight failure by silently changing model/executor/reasoning/Web-Search state/scope.