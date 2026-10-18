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
OUTER_TURN_WAIT=DETERMINISTIC_SLEEP_60_TO_120_SECONDS
OUTER_TURN_RESULT_READBACK=SPARSE_ONLY
REMOTE_RELAY_UNAVAILABLE=>DETERMINISTIC_TOOL_INTERNAL_EXACT_HEAD_WAIT
INTERMEDIATE_CI_STATES=>NOT_RETURNED_TO_MODEL
TERMINAL_RESULT_ONLY=>MODEL_RESUME
NO_COMPLETION_CALLBACK_REQUIRED
WAIT_WINDOW_EXPIRED=>CONTINUE_SAME_TURN_WITH_NEW_DETERMINISTIC_WAIT_WINDOW
WAIT_PRIMITIVE_UNAVAILABLE=>PAUSED_CAPABILITY_WITH_EXPLICIT_HANDOFF
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
result or every deterministic wait/readback capability is genuinely unavailable.
Do not send a final response that hands control back to the user merely because
CI is still running, and never require the user to ask whether CI has finished.

For normal local-waiter operation, keep the outer turn alive with a deterministic
non-GitHub sleep/wait primitive supplied by the current ChatGPT tool runtime.
Prefer 60-120 second windows. There must be no model reasoning or GitHub status
query inside those sleep intervals. After each window, perform one sparse Remote
Desktop Commander process/result-file readback. If the waiter is still
non-terminal, immediately start another deterministic wait window in the same
assistant turn. A tool-runtime maximum-duration boundary is a wait-window
boundary, not a user handoff.

The local waiter remains the sole GitHub CI poller while its relay is reachable.
If the Remote Desktop Commander relay becomes unavailable, preserve turn
continuity by moving the CI wait into one deterministic tool execution that:
1. binds the expected PR HEAD before waiting;
2. queries only the required check names;
3. sleeps 60-120 seconds between reads;
4. performs bounded transport retry;
5. suppresses all non-terminal CI states from model context;
6. verifies the same expected HEAD again at terminal readback; and
7. returns only a terminal SUCCESS/FAILURE/STALE_HEAD/transport-timeout result.
This deterministic tool-internal loop is not model-mediated CI polling because
the model does not observe, classify, or decide on intermediate CI states.

Only when neither the local waiter path nor a deterministic tool-internal wait
primitive is available may the stage enter an explicit capability pause. Never
silently end the turn and make the user rediscover CI completion.

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
