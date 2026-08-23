# Trader Assist / Trade OS — OpenCode Engineering Usage Profile V1

**Status:** SPECIALIZED GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-23

OpenCode is an approved local coding/operator harness after this candidate receives independent acceptance and merge. It does not gain architecture, review, Mark Ready, merge, deployment, runtime/cloud, credential/private-API, signing/wallet, exchange-write or trading authority.

## Current user-qualified / available pool

```text
CLAUDE_OPUS_4_6 = default free OpenCode Writer/operator when available
CLAUDE_SONNET_4_6 = fallback/task-specific alternative
DEEPSEEK_V4_FLASH = Scout/triage/high-volume mechanical route
OX_ALPHA_AND_OTHER_TEMP_FREE = opportunistic only; no durable dependency
```

The user currently treats these OpenCode routes as zero marginal quota cost and will explicitly update the project if that changes.

## Best-use guidance

### Opus 4.6

Prefer for:

- low-risk bounded coding when Codex quota should not be consumed;
- large-codebase comprehension;
- debugging and refactoring;
- deep code-context reasoning;
- free deterministic operator tail after a semantic Writer;
- normal material implementation when Codex is constrained/exhausted and Opus task fit is strong.

### Sonnet 4.6

Use when Opus is unavailable/degraded or representative project evidence shows a task-specific speed/fit advantage. Do not default to Sonnet only to save tokens when both are currently free.

### DeepSeek V4 Flash

Use mainly for:

- repo discovery/search;
- log/test extraction and classification;
- mechanical repetitive edits with decisive validation;
- high-volume preprocessing/Scout work.

Do not use Flash as final authority for high-consequence state/recovery/concurrency/authority logic solely because it is free.

## Writer vs operator roles

OpenCode may act as:

```text
L2_WRITER
```

when Router V2 selects it for semantic code work, or as:

```text
L3_FREE_OPERATOR
```

for already-frozen deterministic mechanics such as status/diff/evidence/commit/push where this reduces user relay.

Operator role must not reinterpret requirements, redesign, widen allowlists, choose another model/route, or declare independent acceptance.

## Task/session discipline

Use one complete high-constraint Task Packet and one coherent bounded stage. Preserve exact worktree/artifact identity. New task, material authority change, independent review or conflicting/stale context => new session.

For current OpenCode v1.x installations, use the permissions/configuration syntax supported by the installed version; do not copy a newer incompatible schema blindly. Explicitly constrain filesystem/Git/external actions for the frozen role.

## Model comparison rule

Do not encode a universal ranking among Opus 4.6, GLM-5.3 and DeepSeek V4 Pro. Router V2 records known task fits and lets current task evidence/user override decide uncertain cases.

## Evidence

For real project tasks retain when available:

```text
MODEL
ROLE=WRITER|OPERATOR
TASK_CLASS
FIRST_PASS_RESULT
TEST/CI_RESULT
REPAIR_COUNT
HUMAN_INTERVENTION_COUNT
ELAPSED_TIME
INDEPENDENT_REVIEW_BLOCKERS
```

Use this evidence to refine Router V2; do not create synthetic work just to rank models.