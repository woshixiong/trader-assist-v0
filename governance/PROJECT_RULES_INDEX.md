# Trader Assist / Trade OS — Project Rules Index

This is the canonical navigation index. It is intentionally an index, not a duplicate engineering constitution. Live GitHub/code/exact artifacts override stale chat or historical PR narrative.

## 1. Mandatory Engineering Control read path

Before material project work, Engineering Control reads:

1. `AGENTS.md`
2. this file
3. `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`
4. `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`
5. `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
6. `governance/GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md`
7. `governance/PROJECT_STATE.json`
8. `governance/V0_FAST_LAUNCH_PROGRAM.json`
9. current accepted Product / Strategy / Operations / Security authority for the bounded task
10. current live GitHub main/issue/PR/exact-head/CI state.

For material Writer work require `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS` and `ENGINEERING_PREFLIGHT_GATE=PASS`. Research/route decisions use independent analysis -> external/mature evidence -> synthesis/decision.

For every nontrivial human-executed Terminal/shell/launcher command, including otherwise mechanical work, also require the generated-command reliability rule. Local environment incompatibility, Linux validation fallback, file-backed execution, command repair budget, one-shot boundaries, and evidence-egress proof are governed there.

## 2. Tooling / model Router

After independent acceptance and merge, task-level routing is governed by `governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md`.

Candidate execution paths: `CODEX_CLI`, `OPENCODE`, `TRAE`, `DEEPSEEK_HARNESS`. Hermes is a separate operator/transport/orchestration layer, not L1 or a Reviewer.

Permanent rules: user manual override retained; no silent substitution; one primary Writer per coherent shared-authority stage; quality first; quota/points/free availability and human relay are routing inputs; OpenCode Opus 4.6, Trae GLM-5.3 and Trae DeepSeek V4 Pro are real Writer candidates according to task fit; Writer self-check is not independent acceptance.

Router V2 applies to every project model-backed invocation, including future executors/providers/models, model-backed operators/evidence providers and T4 model/surface selection where applicable. Every model-backed launch must freeze the requested route and collect actual executor/provider/model/reasoning/tool/session identity where exposed. Requested-vs-actual mismatch, silent fallback/substitution, unauthorized retry/resume, ignored user override or an unprovable required identity is a `ROUTER_INCIDENT`: Engineering fails closed, prohibits automatic rerun, proactively notifies the user and emits one complete Tooling Control escalation packet. Deterministic non-model tools stay under onboarding/authority rather than model selection.

## 3. Codex selected

Read:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md`
- `governance/CODEX_CURRENT_MODEL_PROFILE.md`
- repo `.codex/config.toml`
- relevant repo skills under `.agents/skills/`
- frozen Task Packet.

Engineering Control must freeze the exact Codex model, reasoning effort and `CODEX_WEB_SEARCH_REQUIRED=YES|NO` before prompt/launch generation. If Web Search is needed, also freeze a verified current Codex mode; if not needed, keep it disabled. Model/reasoning/Web-Search shape must not be silently changed by Writer/Hermes.

Efficiency rules include compact AGENTS map; task-local model/reasoning/sandbox/approval; stable model/reasoning/CWD/sandbox/approval/tool shape inside one coherent stage; stable prefix + mutable tail; exact-session resume; `codex exec --json`; bounded logs; progressive skill loading; no unrelated web/MCP/subagent surface by default. `CODEX.md` is retired historical state and is not instruction fallback.

## 4. OpenCode / Trae / DSH selected

OpenCode: read `governance/OPENCODE_ENGINEERING_USAGE_PROFILE_V1_2026-08-23.md`. Opus 4.6 is default free OpenCode model when available; Sonnet 4.6 fallback/task-specific; V4 Flash mainly Scout/triage/high-volume mechanics.

For a Router-selected local OpenCode stage compatible with the accepted Local Task Runner V0, also read:

- `governance/LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`
- `governance/LOCAL_TASK_RUNNER_V0_OPERATOR_OBSERVABILITY_GUIDE_V1_2026-08-24.md`
- `.agents/skills/trade-os-local-task-runner/SKILL.md`

Engineering Control owns the complete Runner lifecycle visible to the user: generate one complete Terminal paste block; create/hash the frozen Runner Task Packet; verify exact runner/Git/OpenCode identity; call `validate`; call `run` exactly once; collect result/evidence/telemetry; then, after the user pastes the complete Terminal output once back into the same Engineering window, review **both** the normal code/task outcome and Runner workflow health. The user does not manually author Runner JSON/hashes, search the Terminal transcript for Runner status fields, classify red flags, or compose tooling escalation reports.

Normal application-code/test/task/model-provider issues stay with Engineering Control/Router. If Engineering Control identifies a genuine Runner identity/schema/state/evidence/policy/preflight/retry/substitution defect, it must explicitly tell the user that tooling control is required, prohibit automatic rerun, and generate one complete ready-to-copy `TOOLING_CONTROL_ESCALATION_PROMPT_BEGIN ... END` prompt in a fenced code block using exact evidence. For the first real Runner project task only, Engineering Control must also generate the one-time `LOCAL_TASK_RUNNER_OBSERVATION_PACKET` prompt regardless of PASS/FAIL so tooling control can validate the live workflow once.

Do not manufacture a synthetic first-real-task benchmark or force OpenCode merely to exercise the Runner.

Trae GLM-5.3: read `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` + `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`.

Trae DeepSeek V4 Pro: read `governance/TRAE_DEEPSEEK_V4_PRO_CURRENT_MODEL_PROFILE.md`.

DeepSeek Harness: read `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`, `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`, and `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`.

All use the Router and exact frozen Task Packet. Do not invent a universal ranking among Opus 4.6 / GLM-5.3 / V4 Pro.

## 5. T4 independent review

Final adjudication defaults to a **separate ordinary ChatGPT window using the strongest appropriate available model and highest appropriate reasoning**.

If GitHub/connectors are sufficient, review directly. If local execution/inspection is needed, prefer deterministic local evidence generation -> hash-manifested review bundle -> upload exact bundle to a new strongest-ChatGPT review window. Use `.agents/skills/trade-os-independent-review-bundle` when applicable.

A weaker local coding model is not the default final Reviewer merely because it can execute locally. Local Codex/Opus/GLM/V4 Pro may supply otherwise unobtainable evidence under an explicitly frozen independent route; final adjudication normally returns to strongest ChatGPT.

After Hermes qualification, Hermes may automate bundle generation/verification/upload/prompt transport, but never the independent judgment.

## 6. Hermes selected / future insertion

Read:

- `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`
- `schemas/control/lossless-task-packet-v1.schema.json`
- `governance/HERMES_TOOLING_V2_INSERTION_PLAN_2026-08-23.md`
- for Trae computer use, `governance/HERMES_TRAE_COMPUTER_USE_PROFILE_V1_2026-08-16.md`
- frozen Task Packet.

Hermes executes/transports frozen authority. It may remove copy/paste, launch/wait/status, deterministic terminal/browser/file mechanics, evidence collection and qualified review-bundle transport. It may not select route/model/reasoning/Web Search, paraphrase authority, make independent review/approval decisions, infer missing fields or hide retries/failures.

Every multi-step Hermes run must be checkpointed and recoverable with exact phase, input/output hashes, action result, retry count, stop reason and resume point. The current V1 H2/review-transport schema does not automatically authorize OpenCode/DSH or ChatGPT review-browser transport; required extensions belong to the Hermes configuration stage and require independent acceptance.

## 7. Tool onboarding / material configuration changes

Read `governance/ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`.

Every new engineering executor/operator/orchestrator and every material tool configuration change must receive separate independent ChatGPT acceptance before first project use. The actual installed Hermes configuration and any schema/contract extension therefore require acceptance after configuration and before activation.

Before custom commodity tooling/orchestration development, the same rule requires a hard mature-solution/build-vs-buy gate: reuse accepted project capability -> provider-native -> standard/official -> mature maintained external -> thin adapter -> small project-specific logic -> custom commodity infrastructure only as documented last resort. Target-host fit and total burden must be compared. A fitting mature solution prohibits custom development; sunk cost, repeated repair and high relay/maintenance burden trigger holistic convergence and mature-replacement search rather than continued patching. Project-specific trading/domain semantics are not commodity tooling.

Local Task Runner V0 has completed its separate tool onboarding and first-real-project-use activation gate; its exact accepted identity, usage boundary, post-run Engineering triage, tooling escalation UX, failure routing and telemetry requirements are recorded in:

- `governance/LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`
- `governance/LOCAL_TASK_RUNNER_V0_OPERATOR_OBSERVABILITY_GUIDE_V1_2026-08-24.md`

Material Runner changes still require re-acceptance.

## 8. Shared repo skills

Cross-executor procedural skills:

```text
.agents/skills/trade-os-writer-preflight
.agents/skills/trade-os-local-gates
.agents/skills/trade-os-evidence
.agents/skills/trade-os-result-packet
.agents/skills/trade-os-independent-review-bundle
.agents/skills/trade-os-local-task-runner
```

They provide progressive on-demand procedural context. Existing `.dsh/skills` remain DSH-specific.

## 9. Core engineering invariants

Unified Engineering Governance remains the general engineering constitution. Durable requirements include mature/provider-native solutions first; simplicity by total burden; stable narrow interfaces; root-cause/global authority before repeated repairs; one complete Task Packet per coherent stage; exact artifact/exact-head CI/independent review; one normal + at most one exceptional repair then holistic convergence; and do not use the user as the routine Writer/CI/Reviewer message bus when safe exact automation can carry evidence.

An active bounded task remains owned by the current control/orchestration role until an explicit task-level terminal disposition or an explicit acknowledged handoff. Intermediate CI, independent review, publication/activation authorization, Mark Ready and similar gates are not completion by themselves. At such a gate, execute all currently authorized/capability-available next actions, prepare the minimum blocked next step, and stop only the specific unauthorized/external action while retaining task ownership.

## 10. Historical / superseded tooling

- `ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md` becomes historical/salvage after Router V2 acceptance.
- Draft PR #117 is salvage/history input, not final tooling constitution.
- `CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` is historical sequencing only.
- `CODEX.md` is a historical compatibility pointer only.

## 11. User-retained authority gates

No governance file, Agent, Task Packet, implementation result, CI result or review implicitly authorizes Mark Ready, merge, branch deletion, deployment, production runtime/cloud mutation, service start/restart/enable/reboot, credentials/private keys/account API, wallet/signing/nonce, exchange write, order submission/cancellation or autonomous trading. These require explicit current user authority.

## 12. Deferred tooling backlog

Issue #115 is the canonical non-release-blocking tooling backlog for first-real-task Codex/Router telemetry, the first naturally occurring Local Task Runner observation after Router selects an OpenCode-compatible task, Hermes follow-up and future DSH/alternative-executor evidence. Issue #121 was completed by PR #122 and is not the remaining Runner-observation authority.

## 13. Generated command reliability / operator efficiency

`governance/GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md` is the mandatory authority for project-generated human-executed commands and launchers.

It requires:

- target OS/shell/tool/deployment environment as evidence, not assumption;
- Linux validation fallback when local macOS is unsuitable, using the narrowest safe surface: existing GitHub Actions Ubuntu where fit, then an isolated authorized Lightsail Linux environment where host-like behavior is required; the current production Lightsail host is not a generic development sandbox;
- file-backed execution by default for long, critical or one-shot scripts;
- target-shell syntax checking and mature ShellCheck/static analysis when applicable and available;
- every `SAFE_STOP` gate to map to a real authority/safety/state invariant;
- all side-effect-free preflight before one-shot semantic consumption;
- exact checkpoint/resume rather than redoing completed expensive work;
- generated-command repair budget: one bounded correction, then holistic regeneration instead of CONT patch chains;
- evidence egress as a two-sided contract: server-side file/hash/readability proof plus actual FinalShell/SFTP client visibility/download before acceptance where evidence return is required;
- human relay/waiting as engineering cost.

This rule does not grant cloud/deployment/runtime authority. Creating, stopping or deleting a Lightsail validation instance, mutating the production target host, or beginning any production qualification still requires the applicable current explicit user authority.

## 14. Target-host deployment / FinalShell workflow

For any target-host deployment, redeployment, real-host qualification or release-installation task where the user operates the Linux host through FinalShell, also read:

- `governance/FINALSHELL_TARGET_HOST_DEPLOYMENT_WORKFLOW_V1_2026-08-26.md`;
- the current accepted Operations deployment runbook;
- Issue #93 and the current release/task authority.

The default operator path is:

```text
ONE MACOS LOCAL EXACT-ARTIFACT GENERATION BLOCK
-> ONE FINALSHELL FILE-MANAGER/SFTP FOLDER UPLOAD
-> ONE CONTIGUOUS BLOCK IN THE ALREADY-CONNECTED FINALSHELL SERVER TERMINAL
-> EVIDENCE RETURN
```

FinalShell is the current default operator surface over standard SSH/SFTP. It does not grant deployment/runtime authority, does not replace exact GitHub release identity, and must not silently be substituted with a newly designed Mac-direct-SSH or deployment-framework workflow. Equivalent mature SSH/SFTP transport is allowed only through a visible route change that preserves the same exact-artifact/hash/authority/secret/evidence boundaries.
