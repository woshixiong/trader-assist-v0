---
name: trade-os-v4-bootstrap
description: Deterministically bind a Trader Assist V4 task to exact Git identity, governance, preflight, route, and a clean worktree before semantic mutation.
---

# Trade OS V4 Bootstrap

Use before every material Writer stage.

1. Fresh-read the exact canonical task/Control Capsule locators.
2. Freshen or verify the canonical remote-tracking ref and require it equals the
   frozen exact base. Verify a bound tree when supplied.
3. Require managed-worktree HEAD equals the base and the worktree is clean.
   Dirty or ambiguous state fails closed; never silently reset user work.
   Record `PRE_MODEL_DETERMINISTIC_BASE_GATE=PASS` only from observed evidence.
4. Bind Task Packet hash, governance epoch, exact base/head, execution surface,
   and preflight binding key to the same task/workspace.
5. Require controller-supplied
   `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`,
   `ENGINEERING_PREFLIGHT_GATE=PASS`, `SEMANTIC_READINESS=PASS`, and an exact
   `CONTROL_CAPSULE_REF`.
6. Verify requested/actual executor, provider, model, reasoning, web-search,
   session policy, and worktree policy. No silent substitution.
7. Check the completed-work ledger before redispatch. Resume an interrupted
   exact checkpoint; do not restart a completed semantic action.
8. Record concise facts, then enter Plan-only. Publication-only readiness must
   not create a false semantic-start gate.

Use `scripts/control/v4_bootstrap.py` for the deterministic identity/binding
checks. A new scope, architecture, provider, dependency, security, or authority
decision returns to Engineering Control before mutation.
