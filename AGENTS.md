# Trader Assist / Trade OS — Agent Operating Map

This file is a compact entry map, not the project encyclopedia. GitHub is the engineering source of truth. Detailed authority lives in the indexed governance files and the current frozen Task Packet.

## 1. Mandatory control-plane path

Before material research, routing, architecture or Writer dispatch, Engineering Control reads and applies:

1. `governance/PROJECT_RULES_INDEX.md`
2. `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`
3. `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`
4. `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
5. current product/strategy/operations/security authority and live GitHub/CI state.

Material route decisions use independent analysis -> external/mature evidence -> synthesis. No material Writer dispatch without `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS` and `ENGINEERING_PREFLIGHT_GATE=PASS`.

## 2. Task-level execution routing

After independent acceptance and merge, task/model routing is governed by `governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md`.

Permanent rules:

- user retains manual executor/model override;
- no silent substitution;
- one primary Writer per coherent shared-authority stage;
- free/cheap never overrides quality;
- human relay/time is part of total engineering cost;
- Writer self-check is not independent acceptance.

Load only the selected tool/model profile needed for the current stage.

## 3. Codex selected

Read:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md`
- `governance/CODEX_CURRENT_MODEL_PROFILE.md`

Engineering Control must freeze before prompt/launch generation:

```text
CODEX_MODEL=
CODEX_REASONING_EFFORT=
CODEX_WEB_SEARCH_REQUIRED=YES|NO
CODEX_WEB_SEARCH_MODE=disabled|cached|indexed|live
```

Use only a Web Search mode verified in the installed Codex surface. If current external evidence is genuinely needed inside the Writer stage, explicitly enable the required mode; otherwise keep Web Search disabled. Writer/Hermes must not silently change model/reasoning/Web-Search state.

Core efficiency invariants:

```text
codex exec for bounded Writer automation
material/resumable work -> --json telemetry
root AGENTS = map, not full manual
stable control prefix + mutable evidence tail
small repo-scoped skills loaded on demand
exact-session resume only inside the same trusted stage
```

Within one coherent Codex stage keep stable unless deliberately opening a new stage: model, reasoning, service tier, CWD/worktree, sandbox, approval policy, enabled tool/MCP/plugin shape, Web Search mode, control prefix and output-contract shape.

Use repo Skills only when their phase applies:

- `$trade-os-writer-preflight`
- `$trade-os-local-gates`
- `$trade-os-evidence`
- `$trade-os-result-packet`
- `$trade-os-independent-review-bundle` for T4 local-evidence packaging only.

Do not enable unrelated web/MCP/plugins/subagents merely because they are available.

## 4. OpenCode / Trae / DSH

OpenCode: read `governance/OPENCODE_ENGINEERING_USAGE_PROFILE_V1_2026-08-23.md`. Opus 4.6 is current default free model when available; Sonnet 4.6 fallback/task-specific; DeepSeek V4 Flash mainly Scout/triage/high-volume mechanics.

When Router V2 has already selected a local `OPENCODE` stage and the frozen task is compatible with the independently accepted Local Task Runner V0, also read:

- `governance/LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`
- `governance/LOCAL_TASK_RUNNER_V0_OPERATOR_OBSERVABILITY_GUIDE_V1_2026-08-24.md`
- `.agents/skills/trade-os-local-task-runner/SKILL.md`

Engineering Control generates the complete one-paste Terminal block, including Runner identity preflight, Task Packet creation/hash, one `validate`, exactly one `run`, result/evidence capture and telemetry. After the user pastes the complete Terminal output back into the same Engineering window, Engineering Control must review **both** the normal code/task outcome and Runner workflow health. The user must not manually search the Terminal transcript for Runner states or red flags.

If a genuine Runner/workflow defect is detected, Engineering Control must explicitly tell the user to return to tooling control, prohibit automatic rerun, and generate one complete ready-to-copy `TOOLING_CONTROL_ESCALATION_PROMPT_BEGIN ... END` prompt in a fenced code block. For the first real Runner project use only, Engineering Control also generates the one-time `LOCAL_TASK_RUNNER_OBSERVATION_PACKET` prompt regardless of PASS/FAIL. Do not ask the user to hand-author Runner JSON/hashes, do not manufacture a synthetic first-real-task benchmark, and do not route normal application-code/test failures to the tooling window.

Trae GLM-5.3: read `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` and `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`.

Trae DeepSeek V4 Pro: read `governance/TRAE_DEEPSEEK_V4_PRO_CURRENT_MODEL_PROFILE.md`.

DeepSeek Harness: read its accepted harness/mandatory-usage/native-headless profiles. Do not encode an unsupported universal ranking among Opus 4.6 / GLM-5.3 / V4 Pro.

## 5. T4 independent review

Default final adjudication is a **new ordinary ChatGPT review window using the strongest appropriate available model and highest appropriate reasoning**.

- If GitHub/connectors are sufficient: review exact GitHub artifacts + exact-head CI directly.
- If local evidence is required: prefer deterministic Terminal/tooling -> hash-manifested review bundle -> exact upload to the new strongest-ChatGPT review window.
- A weaker local coding model is not the default final Reviewer merely because it can execute locally.
- Local Codex/Opus/GLM/V4 Pro may supply otherwise unobtainable evidence under a frozen route; final adjudication normally returns to strongest ChatGPT.
- After Hermes qualification, Hermes may automate deterministic bundle generation/verification/upload/prompt transport, never the judgment.

## 6. Hermes operator selected

Read:

- `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`
- `governance/HERMES_TOOLING_V2_INSERTION_PLAN_2026-08-23.md`
- `schemas/control/lossless-task-packet-v1.schema.json`
- the frozen Task Packet.

Hermes is transport/operator/orchestration infrastructure. It must not choose route/model/reasoning/Web Search, reinterpret authority, conduct independent review, weaken validation or infer missing authority.

Every multi-step Hermes workflow must be checkpointed and human-recoverable: exact phase, input/output hashes, action result, retry count, stop reason and resume point must be available. Hidden semantic retries are prohibited.

The existing V1 Hermes schema does not automatically authorize direct OpenCode/DSH H2 dispatch or ChatGPT review-browser transport. Required extensions belong to the Hermes configuration stage and must be independently accepted before use.

## 7. Tool onboarding

Before first project use of a new engineering executor/operator/orchestrator, or after a material configuration/permission/session/routing change, apply `governance/ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md` and obtain separate independent ChatGPT acceptance of the exact configuration/evidence.

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

No Task Packet, Writer, operator, CI result or review implicitly grants Mark Ready, merge, branch deletion, production deploy/runtime/cloud mutation, service start/restart/enable/reboot, credentials/private API, wallet/signing/nonce, exchange write, order submission/cancellation or autonomous trading. These require explicit current user authority.

## 10. Stale/special files

`CODEX.md` is historical stale task state and is not a Codex instruction authority. Do not add it to instruction fallback discovery. Current rules are this map + `PROJECT_RULES_INDEX.md` + the selected profile + the frozen Task Packet.
