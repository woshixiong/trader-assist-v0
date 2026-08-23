# Trader Assist / Trade OS — Agent Operating Map

This file is a compact entry map, not the project encyclopedia. GitHub is the engineering source of truth. Detailed authority lives in the indexed governance files and the current frozen Task Packet.

## 1. Mandatory control-plane path

Before material research, routing, architecture or Writer dispatch, Engineering Control reads and applies:

1. `governance/PROJECT_RULES_INDEX.md`
2. `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`
3. `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`
4. `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
5. current product/strategy/operations/security authority and live GitHub/CI state.

Material route decisions use: independent analysis -> external/mature evidence -> synthesis. No material Writer dispatch without `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS` and `ENGINEERING_PREFLIGHT_GATE=PASS`.

## 2. Task-level execution routing

After independent acceptance and merge, task/model routing is governed by:

`governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md`

Permanent rules:

- the user retains manual executor/model override;
- no silent substitution;
- one primary Writer per coherent shared-authority stage;
- free/cheap is never a reason to violate a quality requirement;
- human relay/time is part of total engineering cost;
- Writer self-check is not independent acceptance.

Load only the selected tool/model profile needed for the current stage.

## 3. Codex selected

Read:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md`
- `governance/CODEX_CURRENT_MODEL_PROFILE.md`

Core efficiency invariants:

```text
codex exec for bounded Writer automation
material/resumable work -> --json telemetry
root AGENTS = map, not full manual
stable control prefix + mutable evidence tail
small repo-scoped skills loaded on demand
exact-session resume only inside the same trusted stage
```

Within one coherent Codex stage keep stable unless a new stage is deliberately opened:

```text
MODEL
REASONING
SERVICE TIER
CWD / WORKTREE
SANDBOX
APPROVAL POLICY
ENABLED TOOL / MCP / PLUGIN SHAPE
CONTROL PREFIX / OUTPUT CONTRACT SHAPE
```

Do not casually change these mid-stage; a required material change means freeze evidence, return to Router/preflight as applicable, and start a new stage/session. This protects execution semantics and repeated-prefix cache reuse.

Use repo Skills when their stage is reached:

- `$trade-os-writer-preflight`
- `$trade-os-local-gates`
- `$trade-os-evidence`
- `$trade-os-result-packet`

Do not enable unrelated web/MCP/plugins/subagents merely because they are available.

## 4. OpenCode selected

Read:

`governance/OPENCODE_ENGINEERING_USAGE_PROFILE_V1_2026-08-23.md`

Current default free OpenCode model is Opus 4.6 when available. Sonnet 4.6 is fallback/task-specific. DeepSeek V4 Flash is mainly Scout/triage/high-volume mechanical work. OpenCode may be a semantic Writer or a free deterministic operator, but role/authority must be explicit.

## 5. Trae selected

For GLM-5.3 read:

- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`
- `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`

For DeepSeek V4 Pro read:

- `governance/TRAE_DEEPSEEK_V4_PRO_CURRENT_MODEL_PROFILE.md`
- Router V2 and the current complete Task Packet.

Both are first-class advanced Writer candidates. Do not encode an unsupported universal ranking against OpenCode Opus 4.6.

## 6. DeepSeek Harness selected

Read:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`

Its existing `.dsh/skills` remain DSH-specific. Shared cross-executor procedural skills live under `.agents/skills`.

## 7. Hermes operator selected

Read:

- `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`
- `schemas/control/lossless-task-packet-v1.schema.json`
- the exact frozen task authority.

Hermes is transport/operator/orchestration infrastructure. It must not choose technical route/model, reinterpret authoritative handoffs, conduct independent review, weaken validation or infer missing authority. It fails closed on packet/integrity/scope mismatch.

## 8. Universal repository safety / authority

- One bounded issue/branch/worktree at a time for mutation.
- No direct commit to `main`; no force-push after review begins; no shared-history rewrite.
- Do not commit secrets, credentials, wallets, raw private/account data, production databases/logs/caches or real account identifiers.
- AI/strategy/research/context modules never receive exchange credentials or exchange-write authority.
- Uncertain/stale/gapped/conflicted mandatory state means no new risk.
- Never use simulated/default market/account data as real decision evidence.
- Scope expansion, new dependency/provider, new material architecture/authority decision or exhausted repair budget => `SAFE_STOP` / `L1_DECISION_REQUIRED`.
- One normal repair + at most one exceptional repair; otherwise enter `HOLISTIC_CONVERGENCE_GATE`.
- Completion evidence lists exact changed files, observed tests/checks, exact artifact/head, residual risks and retained gates.

## 9. User-retained gates

No Task Packet, Writer, operator, CI result or review implicitly grants:

```text
Mark Ready
merge
branch deletion
production deploy/runtime/cloud mutation
service start/restart/enable/reboot
credentials/private API
wallet/signing/nonce
exchange write
order submission/cancellation
autonomous trading
```

These require explicit current user authority.

## 10. Stale/special files

`CODEX.md` is historical stale task state and is not a Codex instruction authority. Do not add it to instruction fallback discovery. Current rules are this map + `PROJECT_RULES_INDEX.md` + the selected profile + the frozen Task Packet.
