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

Use the V5-B deterministic waiter/controller once qualified. The preferred
local exact-head wait surface is `scripts/control/v5_ci_waiter.py`. When Remote
Desktop Commander is the execution relay, launch this waiter as one long-running
local process rather than repeatedly polling process/status output through
Remote Desktop Commander. Preserve the existing `gh run watch` path as the
immediate fallback if the waiter is unavailable or returns a fail-closed
transport/query result.

Verify PR head before waiting and at terminal readback. Head drift invalidates
old CI/review.

Classify a failed result before retry/mutation as transient/known flake,
deterministic mechanical, semantic, infrastructure/transport, or unresolved.
Collect only the minimum decisive failure evidence.

Known transient: at most one same-head rerun. Semantic: consume the frozen
repair budget and route through package-state. Unresolved/new-root: Engineering
Control.

All-green routes HIGH/governance to required Final Review; LOW/MEDIUM may
advance to protected closeout after verified tier binding and exact-head CI.
MEDIUM promotion additionally needs phase-level behavioral evidence. Never
silently Mark Ready, merge, deploy or cross another protected gate.

## Transient network outage recovery (candidate)

Network transport failure must preserve exact head/run/checkpoint, distinct from
failing semantic tests. Prefer native GitHub workflow/job rerun for **failed
transient jobs only**, never blindly rerun full CI on every network hiccup.
Use a 10s/20-attempt bounded quick reconnect envelope where client-managed
reads are required; after that only a durable existing native scheduler/service
may retry at a 5-15min jittered cadence until recovery or cancellation.
Read exact CI run status before retry. GitHub native rerun limits apply; an
exhausted job rerun budget must enter a tracked paused state, not loop.
No RDC polling storm, credential reissue, untrusted proof injection or duplicate
deployment on ambiguous success.
