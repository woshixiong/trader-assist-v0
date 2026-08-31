# Trader Assist / Trade OS — Project Rules Index

This file is the **canonical navigation index**, not a duplicate constitution. Live GitHub/code/exact artifacts override stale chat or historical PR narrative.

## 1. Always-read engineering path

For material engineering work read:

1. `AGENTS.md`
2. this index
3. `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`
4. current accepted Product / Strategy / Operations / Security authority for the bounded task
5. current live GitHub main / issue / PR / exact-head / CI state.

For a MATERIAL task also complete:

- `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`

Required gates:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

The Unified V2 standard is the sole project-wide normative engineering constitution. Other files below are task-conditional procedures, executor/tool contracts, operational authority or history.

### 1.1 User phrase “统一规则”

When the user asks to **“往统一规则里增加内容”**, **“把这条加入统一规则”**, **“add this to the unified rules”**, or equivalent, route the request through the governance-maintenance rule in Unified V2 and the shorthand in `AGENTS.md`.

Default destination:

```text
DURABLE_PROJECT_WIDE_ENGINEERING_INVARIANT -> UNIFIED V2
```

Do not mechanically append task-specific procedure, model/tool configuration, deployment mechanics or incident detail to V2. Keep narrow details in the applicable specialized procedure/contract and promote only the reusable project-wide invariant into V2 when needed.

Do not create another project-wide governance authority by default. A genuinely new specialized procedure/contract must be narrow, independently maintainable, indexed here, explicitly subordinate to V2 and non-duplicative.

## 2. Direction-setting research

When the task materially sets or changes research/product/strategy/engineering/architecture/tool/provider direction, use:

- `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`

It operationalizes the V2 three-stage method:

```text
INDEPENDENT ANALYSIS
-> EXTERNAL / MATURE EVIDENCE
-> SYNTHESIS / DECISION
```

It is a procedure/reference; Unified V2 owns the normative rule.

## 3. Human-executed commands / launchers

For every nontrivial human-executed Terminal/shell/launcher command use:

- `governance/GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md`

It operationalizes V2 command rules: environment evidence, exact CLI invocation contract, canonical validation commands, platform fidelity, false-gate prevention, file-backed execution, checkpoint/resume, command repair budget and evidence egress.

It is a specialized procedure/incident catalogue; Unified V2 owns the project-wide invariant.

## 4. Model-backed routing

For any model-backed project invocation read:

- `governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md`

Then load **only the selected route's profile**.

### Codex

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md`
- `governance/CODEX_CURRENT_MODEL_PROFILE.md`
- repo `.codex/config.toml`
- relevant `.agents/skills/` only when their phase applies.

### OpenCode

- `governance/OPENCODE_ENGINEERING_USAGE_PROFILE_V1_2026-08-23.md`

If Local Task Runner V0 is selected and compatible:

- `governance/LOCAL_TASK_RUNNER_V0_ENGINEERING_USAGE_PROFILE_V1_2026-08-24.md`
- `governance/LOCAL_TASK_RUNNER_V0_OPERATOR_OBSERVABILITY_GUIDE_V1_2026-08-24.md`
- `.agents/skills/trade-os-local-task-runner/SKILL.md`

### Trae

GLM:
- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`
- `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`

DeepSeek V4 Pro:
- `governance/TRAE_DEEPSEEK_V4_PRO_CURRENT_MODEL_PROFILE.md`

### DeepSeek Harness

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`

Router V2 freezes requested role/executor/provider/model/reasoning/tool/session/resource state. No silent substitution/fallback/retry/resume. Requested-vs-actual required-identity mismatch is a Router incident.

## 5. Independent T4 review

Default final adjudicator:

```text
SURFACE=NEW ORDINARY CHATGPT WINDOW
MODEL=STRONGEST APPROPRIATE AVAILABLE
REASONING=HIGHEST APPROPRIATE
```

If exact GitHub artifacts + exact-head CI are sufficient, review directly through GitHub/connectors.

If local evidence is required, prefer deterministic evidence generation -> hash-manifested review bundle -> exact upload to the new independent ChatGPT review window. Use `.agents/skills/trade-os-independent-review-bundle` when applicable.

Writer self-review never becomes independent acceptance.

## 6. Tool onboarding / material tool change

For a new engineering executor/operator/orchestrator or a material configuration/permission/session/routing change read:

- `governance/ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`

A tool requires exact identity, representative capability/safety evidence, independent acceptance and separate user activation before first project use. Material tool changes require re-acceptance.

The mature-solution/build-vs-buy gate in Unified V2 applies before custom commodity tooling.

## 7. Hermes

When Hermes is selected read:

- `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`
- `governance/HERMES_TOOLING_V2_INSERTION_PLAN_2026-08-23.md`
- `schemas/control/lossless-task-packet-v1.schema.json`
- route-specific Hermes profile when applicable.

Hermes transports/executes frozen authority; it does not choose architecture/model/reasoning, infer missing authority or perform independent adjudication. Multi-step runs must be checkpointed and human-recoverable.

## 8. Target-host deployment / FinalShell

For deployment, redeployment, release installation or target-host qualification through FinalShell read:

- `governance/FINALSHELL_TARGET_HOST_DEPLOYMENT_WORKFLOW_V1_2026-08-26.md`
- current accepted Operations runbook/authority
- current release/task Issue and exact release identity.

Default operator route remains:

```text
MACOS CREATES ONE EXACT-RELEASE ARTIFACT/FOLDER
-> FINALSHELL SFTP UPLOAD
-> ONE CONTIGUOUS BLOCK IN ALREADY-CONNECTED SERVER TERMINAL
-> EVIDENCE RETURN
```

FinalShell is an operator surface, not deployment/runtime authority.

## 9. Shared procedural skills

Load only when applicable:

```text
.agents/skills/trade-os-writer-preflight
.agents/skills/trade-os-local-gates
.agents/skills/trade-os-evidence
.agents/skills/trade-os-result-packet
.agents/skills/trade-os-independent-review-bundle
.agents/skills/trade-os-local-task-runner
```

Skills provide on-demand procedure, not new authority.

## 10. Project state / product program

`governance/PROJECT_STATE.json` and `governance/V0_FAST_LAUNCH_PROGRAM.json` are state/program snapshots. When stale relative to live GitHub Issue/PR/code/CI, the live evidence and current domain authority govern.

## 11. Historical / superseded engineering governance

After Unified V2 is independently accepted and merged:

- `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md` = historical / superseded;
- the separate Issue #139 Holistic Method proposal = incorporated into V2, not an additional constitution;
- `PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md` = task-conditional procedure/reference, not separate project-wide authority;
- `GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md` = task-conditional procedure/incident catalogue, not separate project-wide authority;
- `ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md` = historical/salvage after Router V2;
- `CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` = historical sequencing only;
- `CODEX.md` = historical compatibility/stale task state, not instruction authority;
- Draft PR #117 = salvage/history input, not a competing constitution.

Historical decisions remain useful rationale but do not enter the mandatory read path unless a current task explicitly needs that history.

## 12. User-retained authority gates

No engineering governance, Task Packet, Writer result, CI result or Review implicitly authorizes:

```text
MARK_READY
MERGE
BRANCH_DELETION
DEPLOYMENT
PRODUCTION_RUNTIME_OR_CLOUD_MUTATION
SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_PRIVATE_API
WALLET_SIGNING_NONCE
EXCHANGE_WRITE
ORDER_SUBMISSION_OR_CANCELLATION
AUTONOMOUS_TRADING
```

These always require explicit current user authority.
