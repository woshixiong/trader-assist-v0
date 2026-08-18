---
name: trade-os-result-packet
description: Format observed DeepSeek Harness task results into the stable Trader Assist Result Packet contract for lossless downstream review and future Hermes transport.
whenToUse: Load only when producing the final output for a frozen Trader Assist Writer Task Packet.
user-invocable: true
disable-model-invocation: false
---

# Trade OS Result Packet

Return a concise evidence-bearing completion record. Use only observed facts.

Minimum applicable fields:

```text
TASK_ID=
EXECUTOR=DEEPSEEK_HARNESS
DSH_VERSION=
PROVIDER=
MODEL=
REASONING=
SESSION_MODE=
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
RUFF=
MYPY=
COMPILE=
DIFF_SCOPE_CHECK=
SECRET_CHECK=
RAW_EVIDENCE_REFS=
RESIDUAL_RISKS=
BLOCKERS=
REPAIR_STAGE=
L1_DECISION_REQUIRED=YES/NO
MARK_READY_EXECUTED=NO
MERGE_EXECUTED=NO
DEPLOYMENT_EXECUTED=NO
RUNTIME_CLOUD_MUTATION_EXECUTED=NO
ACCOUNT_PRIVATE_API_EXECUTED=NO
EXCHANGE_WRITE_EXECUTED=NO
```

Use `NOT_RUN` or `NOT_APPLICABLE` rather than inventing PASS. Writer PASS is execution evidence only; never label the packet `INDEPENDENT_ACCEPTANCE=PASS` unless an independent reviewer actually supplied that separate fact through an authorized upstream packet.
