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
CI_WAITER_STARTED=>CURRENT_ENGINEERING_TURN_MUST_REMAIN_ACTIVE_UNTIL_TERMINAL
USER_REPROMPT_FOR_CI_COMPLETION=PROHIBITED
OUTER_TURN_GITHUB_CI_POLLING=PROHIBITED
OUTER_TURN_RESULT_READBACK=SPARSE_ONLY
TURN_CONTINUITY_UNAVAILABLE=>PAUSED_CAPABILITY_WITH_EXPLICIT_HANDOFF
~~~

Use the V5-B deterministic waiter/controller once qualified. The preferred
local exact-head wait surface is `scripts/control/v5_ci_waiter.py`. When Remote
Desktop Commander is the execution relay, launch this waiter as one long-running
local process rather than repeatedly polling process/status output through
Remote Desktop Commander. Preserve the existing `gh run watch` path as the
immediate fallback if the waiter is unavailable or returns a fail-closed
transport/query result.

After launching the local waiter, the CI stage is not an assistant stop point.
The current engineering turn must remain active until the waiter emits a terminal
result or a genuine host/tool capability failure prevents continuation. Do not
send a final response that hands control back to the user merely because CI is
still running, and never require the user to ask whether CI has finished.

The local waiter remains the sole GitHub CI poller. The outer ChatGPT turn may
use a non-GitHub wait primitive plus sparse Remote Desktop Commander process or
result-file readback (normally no more often than every 60-120 seconds unless a
terminal result is expected). Progress notes may be emitted without requiring a
user reply. Sparse readback is transport observation only; it must not duplicate
GitHub CI polling.

Verify PR head before waiting and at terminal readback. Head drift invalidates
old CI/review.

Classify a failed result before retry/mutation as transient/known flake,
deterministic mechanical, semantic, infrastructure/transport, or unresolved.
Collect only the minimum decisive failure evidence.

Known transient: at most one same-head rerun. Semantic: consume the frozen
repair budget and route through package-state. Unresolved/new-root: Engineering
Control.

All-green advances mechanically to Final Review readiness. Never Mark Ready,
merge, deploy, or cross another protected gate.
