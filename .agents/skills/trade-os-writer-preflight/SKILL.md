---
name: trade-os-writer-preflight
description: Verify a frozen Trader Assist Writer Task Packet, exact Git/worktree identity, scope, authority attestations and stop conditions before any local coding-agent mutation.
---

# Trade OS Writer Preflight

Use this skill at the start of a Trader Assist Writer stage.

1. Read the frozen Task Packet and verify its packet/hash identity.
2. Require a controller/runner-produced **pre-model deterministic base-freshness proof** before semantic work: fresh canonical base ref / remote-tracking ref (when applicable) equals the frozen exact base; bound expected tree matches when supplied; managed-worktree HEAD equals the frozen exact base; worktree is clean. A stale local `main` label is not evidence. Missing/mismatched proof => stop before semantic mutation and return deterministic execution-surface drift to control.
3. Require controller-supplied `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`; for material work also require `ENGINEERING_PREFLIGHT_GATE=PASS`.
4. Verify the governance epoch and preflight binding key are bound to the same Task Packet, exact base/head, execution surface and actual workspace. If unchanged, consume the existing bound attestation; do not recursively reload governance. Drift or mismatch => return control for recomputation.
5. Verify the Control Capsule and completed-work ledger. If this named workstream is already terminal/completed, semantic redispatch is prohibited unless Engineering Control records a new explicit disposition.
6. Verify allowed/prohibited paths, invariants, focused validation, repair stage, stop conditions and retained user gates.
7. Consume the packet's normalized required authority assertions and provenance locators. Do not reread full Unified V2, full preflight, full Rules Index, full Issue history or broad governance/docs by default.
8. If a concrete conflict or missing material fact appears, read only the minimum canonical source; unresolved material conflict => return to Engineering Control.
9. Use exact-item-first retrieval: exact comment/file/run/job/artifact endpoint before a collection endpoint; exact symbol/heading/range before a whole known-large file; failed step/bounded decisive excerpt before raw logs. Expand only for a concrete material unknown.
10. When `EXECUTOR=CODEX_CLI`, require exact model, reasoning effort and Web Search state from the launch contract. Verify the actual installed CLI identity and required capabilities; do not fail solely on a stale patch-version snapshot unless the task proves an exact version dependency.
11. Verify `SEMANTIC_READINESS=PASS`. Do not require publication-only GitHub auth/push/PR/result-egress readiness before semantic mutation unless the packet proves that capability is an irreducible semantic prerequisite.
12. Record concise preflight facts before mutation.

If execution is a continuation after quota/capacity interruption, verify the same task/authority/workspace/checkpoint and exact session/thread when recoverable. Exact continuation is not a new semantic retry; restarting from the original task is prohibited by default.

Return `L1_DECISION_REQUIRED` without implementation for stale/ambiguous packet, identity drift, **semantic** capability/permission mismatch, allowlist expansion, new dependency/provider, new material design decision, authority conflict or unapproved gate crossing. A publication-only transport/auth problem is returned as a later operator/publication boundary and must not be mislabeled as semantic unreadiness. Never solve a preflight failure by silently changing model/executor/reasoning/Web-Search state/scope.

## Token-sustainable start contract

The semantic Writer is not the CI/status watcher. After exact-head publication/checkpoint:

```text
WRITER_CHECKPOINT=CI_PENDING
MODEL_MEDIATED_CI_POLLING=PROHIBITED
CI_WAIT_OWNER=GITHUB_OR_DETERMINISTIC_TOOL
```

Do not repeatedly read PR checks, workflow runs, SHA/tree, changed paths, mergeability or artifact metadata with the semantic model. Those are M0 mechanical-state work. Resume/wake a semantic model only for a material semantic/new-root/ambiguous failure, scope/authority conflict, or an explicitly assigned semantic repair. Fresh authority-bearing Review uses a separate strong independent context.
