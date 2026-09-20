---
name: trade-os-result-packet
description: Format observed Trader Assist coding-agent results into a compact stable handoff packet without repeating deterministic or unchanged lifecycle boilerplate.
---

# Trade OS Result Packet

Return observed facts only. Prefer one compact terminal/checkpoint packet over verbose narration.

## Core fields

Emit these when applicable:

```text
TASK_ID=
TASK_PACKET_HASH=
EXECUTOR=
MODEL=
REASONING=
SESSION_ID=
WORKTREE=
EXACT_BASE=
FINAL_HEAD=
FINAL_TREE=
BRANCH=
PROJECT_ENGINEERING_RULESET_PREFLIGHT=
ENGINEERING_PREFLIGHT_GATE=
GOVERNANCE_EPOCH=
PREFLIGHT_BINDING_KEY=
PREFLIGHT_REUSE_STATUS=REUSED|RECOMPUTED|NOT_APPLICABLE

IMPLEMENTATION_RESULT=
CHANGED_FILES=
VALIDATION_SUMMARY=
RAW_EVIDENCE_REFS=
RESIDUAL_RISKS=
L1_DECISION_REQUIRED=YES|NO

CURRENT_STATE=
CURRENT_BLOCKER=
NEXT_ALLOWED_ACTION=
CI_STATE_LOCATOR=
CI_WAIT_OWNER=GITHUB|DETERMINISTIC_TOOL|NOT_APPLICABLE
MODEL_POLLING_LOOP=PROHIBITED|NOT_APPLICABLE
RETAINED_USER_GATE=
SAFETY_BOUNDARY_VIOLATION=NONE_OBSERVED|<exact violation>
```

Use `NOT_RUN`, `NOT_EXPOSED` or `NOT_APPLICABLE`; never invent PASS or telemetry. Writer PASS is not independent acceptance.

## Emit by exception, not boilerplate

Do **not** repeat large unchanged lifecycle/safety blocks at every checkpoint. Emit an extended field only when it is material to the current handoff, changed since the prior durable checkpoint, explicitly required by the frozen Task Packet, or records an exception.

Examples:

```text
FOCUSED_TESTS=
RELEVANT_REGRESSION=
STATIC_GATES=
DIFF_SCOPE_CHECK=
SECRET_CHECK=
INPUT_TOKENS=
CACHED_INPUT_TOKENS=
OUTPUT_TOKENS=
REASONING_OUTPUT_TOKENS=
REPAIR_STAGE=
CONTROL_CAPSULE_REF=
COMPLETED_WORK_LEDGER_REF=
CONTEXT_HEADROOM_STATE=
PUBLICATION_READINESS=
COMMIT_PUSH_EXECUTED=
MARK_READY_EXECUTED=
MERGE_EXECUTED=
DEPLOYMENT_EXECUTED=
RUNTIME_CLOUD_MUTATION_EXECUTED=
ACCOUNT_PRIVATE_API_EXECUTED=
EXCHANGE_WRITE_EXECUTED=
```

When all retained/prohibited boundaries were respected, prefer the single core field:

```text
SAFETY_BOUNDARY_VIOLATION=NONE_OBSERVED
```

instead of repeating many `..._EXECUTED=NO` lines. If an operation is a current retained gate or its state changed, emit that exact field explicitly.

## Mechanical-state economy

SHA/head/tree, PR state, changed paths, mergeability, CI run/job state, conclusions, artifact IDs/names/digests, hashes and typed terminal fields are M0 mechanical data. Their collection belongs to GitHub/provider-native/deterministic tooling, not repeated semantic-model polling.

A quota/capacity pause preserves the same semantic attempt when task, authority and checkpoint identity remain bound. A completed-work ledger entry must be checked before redispatch of a named workstream.
