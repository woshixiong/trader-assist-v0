# Trader Assist / Trade OS — Project Rules Index

This is the canonical navigation index. It is intentionally an index, not a duplicate engineering constitution. Live GitHub/code/exact artifacts override stale chat or historical PR narrative.

## 1. Mandatory Engineering Control read path

Before material project work, Engineering Control reads:

1. `AGENTS.md`
2. this file
3. `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`
4. `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`
5. `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
6. `governance/PROJECT_STATE.json`
7. `governance/V0_FAST_LAUNCH_PROGRAM.json`
8. current accepted Product / Strategy / Operations / Security authority for the bounded task
9. current live GitHub main/issue/PR/exact-head/CI state.

For material Writer work require:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

Research/route decisions use: independent analysis first -> external/mature evidence second -> synthesis/decision third.

## 2. Tooling / model Router

After independent acceptance and merge, the canonical task-level routing candidate is:

`governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md`

It supersedes `governance/ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md` for new tasks.

Current approved candidate execution paths include:

```text
CODEX_CLI
OPENCODE
TRAE
DEEPSEEK_HARNESS
```

Hermes is a separate operator/transport/orchestration layer, not an L1 engineering/review authority.

Permanent routing rules:

- user manual executor/model override is retained;
- no silent substitution;
- one primary Writer per coherent shared-authority stage;
- quality/correctness first;
- quota/points/free availability and human relay are routing inputs;
- free OpenCode Opus 4.6, Trae GLM-5.3 and Trae DeepSeek V4 Pro are all real Writer candidates according to task fit;
- Writer self-check is not independent acceptance.

## 3. Codex selected

Read:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md`
- `governance/CODEX_CURRENT_MODEL_PROFILE.md`
- repo `.codex/config.toml`
- relevant repo skills under `.agents/skills/`
- the frozen Task Packet.

Codex efficiency rules include: compact root AGENTS map; task-local model/reasoning/sandbox/approval; stable model/reasoning/CWD/sandbox/approval/tool shape inside one coherent stage; stable prefix + mutable tail; exact-session resume; `codex exec --json` telemetry; bounded logs; progressive skill loading; no unrelated web/MCP/subagent surface by default.

`CODEX.md` is retired historical state and must not be used as instruction fallback.

## 4. OpenCode selected

Read:

- `governance/OPENCODE_ENGINEERING_USAGE_PROFILE_V1_2026-08-23.md`
- Router V2
- frozen Task Packet and exact task authorities.

Current user policy: Opus 4.6 is the default free OpenCode model when available; Sonnet 4.6 is fallback/task-specific; DeepSeek V4 Flash is mainly Scout/triage/high-volume mechanical work; temporary free models such as Ox Alpha are opportunistic only.

OpenCode may act as a semantic Writer or free deterministic operator. The role must be frozen explicitly.

## 5. Trae + GLM-5.3 selected

Read:

- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`
- `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`
- Router V2
- frozen Task Packet.

GLM-5.3 is a first-class advanced Writer. Prefer one complete high-constraint coherent stage over repeated one-file microtasks.

## 6. Trae + DeepSeek V4 Pro selected

Read:

- `governance/TRAE_DEEPSEEK_V4_PRO_CURRENT_MODEL_PROFILE.md`
- Router V2
- frozen Task Packet.

DeepSeek V4 Pro is a first-class advanced Writer, especially for broad repo investigation, repo-wide/full-stack work, larger-context root-cause discovery and alternate Writer routes.

## 7. DeepSeek Harness selected

Read:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`
- frozen Task Packet.

The remaining DSH rc.8 seam/capability and token/cache/progressive-skill evidence is collected on the next real DSH task, not a synthetic paid benchmark.

## 8. Hermes selected

Read:

- `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`
- `schemas/control/lossless-task-packet-v1.schema.json`
- for Trae computer use, `governance/HERMES_TRAE_COMPUTER_USE_PROFILE_V1_2026-08-16.md`
- frozen Task Packet.

Hermes executes/transports frozen authority and may perform authorized terminal/browser/file mechanics. It must not select model/technical route, paraphrase authority-bearing packets, make independent review/approval decisions, infer missing fields or weaken gates.

## 9. Shared repo skills

Cross-executor procedural skills live under:

```text
.agents/skills/trade-os-writer-preflight
.agents/skills/trade-os-local-gates
.agents/skills/trade-os-evidence
.agents/skills/trade-os-result-packet
```

They provide progressive, on-demand procedural context. Existing `.dsh/skills` remain DSH-specific until separately reconciled; do not assume identical provider/executor fields.

## 10. First Launch / recovery authority anchors

Where relevant also read:

- `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`
- `governance/FIRST_LAUNCH_MINIMUM_RECOVERY_READINESS_V1.md`
- `governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`
- `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`
- `governance/FIRST_LAUNCH_HOST_QUALIFICATION_AUTOMATION_ABANDONMENT_RULING_V1.md`.

Do not infer deployment/runtime authority from engineering acceptance.

## 11. Core engineering invariants

The Unified Engineering Governance remains the general engineering constitution. Durable requirements include:

- mature/provider-native solution first when fit is adequate;
- simplicity by total implementation/test/review/operator/model/maintenance burden;
- stable narrow interfaces and replaceable implementation policy;
- global/root-cause authority modeling before repeated local repairs;
- realistic external-contract evidence and scale/provider/freshness gates where applicable;
- one complete Task Packet per coherent stage;
- exact artifact / exact-head CI / independent review;
- one normal repair + at most one exceptional repair, then holistic convergence;
- do not use the user as routine Writer/CI/Reviewer message bus when safe automation can carry exact evidence.

## 12. Historical / superseded tooling

- `ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md` becomes historical/salvage input after Router V2 acceptance.
- Draft PR #117 is salvage/history input, not the final tooling constitution.
- `CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` is historical sequencing provenance only and never pins a new task.
- `CODEX.md` is a historical compatibility pointer only.

Do not resume patching stale governance branches merely because they contain an older form of a retained rule.

## 13. User-retained authority gates

No governance file, Agent, Task Packet, implementation result, CI result or review implicitly authorizes:

```text
Mark Ready
merge
branch deletion
deployment
production runtime/cloud mutation
service start/restart/enable/reboot
credentials/private keys/account API
wallet/signing/nonce
exchange write
order submission/cancellation
autonomous trading
```

These require explicit current user authority.

## 14. Deferred tooling backlog

Issue #115 tracks remaining real-task DSH validation, first-real-task Codex telemetry, Hermes setup/qualification and future tooling evidence. Tooling/model snapshots are refreshed when the user changes availability/quota state or current provider/tool facts change.
