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

## Accepted Local Task Runner V0 execution envelope

When Router V2 has already selected a **local OpenCode stage**, use the independently accepted Local Task Runner V0 as the default local execution/validation/evidence envelope when the frozen task fits its bounded contract.

Read:

- `governance/LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`
- `.agents/skills/trade-os-local-task-runner/SKILL.md`

The Runner does not select OpenCode or choose the model. Engineering Control must freeze the task and exact model first.

For a compatible stage, Engineering Control generates one complete ordinary-Terminal block containing Runner identity preflight, exact Git worktree/branch/HEAD checks, Task Packet creation, packet SHA-256, `validate`, exactly one `run`, result/evidence capture and telemetry. The user is not expected to manually write Runner JSON, calculate hashes or return to a tooling window for routine command generation.

Do not manufacture a synthetic first-real-task benchmark and do not force OpenCode merely to exercise the Runner. The first real Runner task is the first naturally occurring genuine Trader Assist stage for which Router V2 legitimately selects OpenCode and the frozen task is compatible.

Failure ownership remains separated:

```text
normal application-code/test failure -> Engineering Control
scope/authority ambiguity -> Engineering Control / L1 SAFE_STOP
model/provider availability -> Engineering Control / Router; no silent substitution
Runner identity/schema/state/evidence/policy defect -> tooling control
```

Runner V0 has no hidden retry, automatic resume, model fallback or publication primitive. A second run requires an explicit Engineering-Control disposition and newly frozen authority as applicable.

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

When Local Task Runner V0 is used, also retain its profile-required `RUN_ID`, input packet hash, Git identity, changed paths, policy/check result, final status/stop reason and retry count. Use real project evidence to refine Router V2; do not create synthetic work just to rank models or the Runner.