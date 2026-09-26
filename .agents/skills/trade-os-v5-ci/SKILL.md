---
name: trade-os-v5-ci
description: Enforce deterministic exact-head CI waiting, bounded failure evidence, stale-head invalidation, and zero model-mediated polling.
---

# Trade OS V5 CI

Required inputs are repository, PR, expected exact head, required checks, and
current package-state locator.

~~~text
MODEL_MEDIATED_CI_POLLING=PROHIBITED
RAW_SUCCESS_LOG_INGESTION=PROHIBITED_BY_DEFAULT
EXACT_HEAD_BINDING=REQUIRED
~~~

Use the V5-B deterministic waiter/controller once qualified. Verify PR head
before waiting and at terminal readback. Head drift invalidates old CI/review.

Classify a failed result before retry/mutation as transient/known flake,
deterministic mechanical, semantic, infrastructure/transport, or unresolved.
Collect only the minimum decisive failure evidence.

Known transient: at most one same-head rerun. Semantic: consume the frozen
repair budget and route through package-state. Unresolved/new-root: Engineering
Control.

All-green advances mechanically to Final Review readiness. Never Mark Ready,
merge, deploy, or cross another protected gate.
