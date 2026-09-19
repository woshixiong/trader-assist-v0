---
name: trade-os-result-packet
description: Format observed Trader Assist coding-agent results into a concise stable handoff packet for downstream operators, CI and independent review.
---

# Trade OS Result Packet

Return only observed facts. Minimum applicable fields:

```text
TASK_ID=
EXECUTOR=
MODEL=
REASONING=
SESSION_ID=
WORKTREE=
EXACT_BASE=
FINAL_HEAD=
BRANCH=
PROJECT_ENGINEERING_RULESET_PREFLIGHT=
ENGINEERING_PREFLIGHT_GATE=
IMPLEMENTATION_RESULT=
CHANGED_FILES=
FOCUSED_TESTS=
RELEVANT_REGRESSION=
STATIC_GATES=
DIFF_SCOPE_CHECK=
SECRET_CHECK=
RAW_EVIDENCE_REFS=
INPUT_TOKENS=
CACHED_INPUT_TOKENS=
OUTPUT_TOKENS=
REASONING_OUTPUT_TOKENS=
RESIDUAL_RISKS=
BLOCKERS=
REPAIR_STAGE=
L1_DECISION_REQUIRED=YES/NO

ACTIVE_STAGE_CHECKPOINT_REF=
CURRENT_STAGE=
NEXT_AUTHORIZED_ACTION=
ROTATION_TRIGGER_STATE=NOT_TRIGGERED|TRIGGERED|NOT_APPLICABLE
SUCCESSOR_WINDOW_REQUIRED=YES/NO
SUCCESSOR_WINDOW_PROMPT_REF=
PUBLICATION_READINESS=PASS|FAIL|NOT_APPLICABLE_YET

COMMIT_PUSH_EXECUTED=YES/NO/NOT_AUTHORIZED
MARK_READY_EXECUTED=NO
MERGE_EXECUTED=NO
DEPLOYMENT_EXECUTED=NO
RUNTIME_CLOUD_MUTATION_EXECUTED=NO
ACCOUNT_PRIVATE_API_EXECUTED=NO
EXCHANGE_WRITE_EXECUTED=NO
```

Use `NOT_RUN`, `NOT_EXPOSED` or `NOT_APPLICABLE`; never invent PASS or telemetry. Writer PASS is not independent acceptance.

When a material Engineering Control rotation trigger has fired, downstream control must not proceed to the next material stage until the durable checkpoint is verified and the successor-window prompt is available. These lifecycle fields carry observed control state; they do not authorize the Writer to decide review/merge/deployment gates.