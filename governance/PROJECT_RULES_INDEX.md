# Trader Assist / Trade OS — Project Rules Index

This file is the **canonical navigation index**, not a duplicate constitution. Live GitHub/code/exact artifacts override stale chat or historical PR narrative.

## 1. Authority loading model

Engineering Control uses this index to resolve the bounded authority graph. For material work it fresh-checks live GitHub identity, applicable Unified V2 sections, current Product / Strategy / Operations / Security authority, the Mandatory Preflight checklist and only specialized procedures that actually apply.

Required material gates:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

After freeze, the downstream Writer consumes the exact Task Packet, its bound preflight/governance attestation, normalized required authority assertions with provenance locators, affected code/tests and the selected executor profile. It does not recursively reload this index, full Unified V2, full preflight or full Issue history unless an actual conflict/unknown requires a targeted canonical read.

The same progressive-disclosure rule applies to Engineering Control and independent review: begin from the current Control Capsule/manifest plus fresh live identity, not from the complete chat transcript or full Issue history. Missing material context triggers targeted canonical retrieval; unresolved uncertainty fails closed. Chat history is not canonical project state.

Engineering Control binds the applicable authority-file SHAs into a governance epoch. A full core-governance read is required on the first material action in a fresh control context, governance-epoch drift or a concrete authority conflict. With an unchanged epoch, reuse the exact bound governance/preflight attestation and read only changed/needed authority. Fresh live repository/main/Issue/PR/head/CI checks remain required.

Unified V2 remains the sole project-wide normative engineering constitution.

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

### 2.1 External mature solution selection / adoption

Whenever a material task selects, rejects, composes, customizes, adopts, upgrades or re-evaluates a provider-native, standard/official or mature maintained external framework, library, SDK, platform, service or infrastructure component, or proposes project-owned commodity infrastructure, also use:

- `governance/EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md`

This specialized procedure operationalizes the Unified V2 `MATURE_CAPABILITY_NO_REBUILD_GATE`. It standardizes capability classification, Stage 0 no-product-code audit, candidate discovery/authentication, P0 hard gates, evidence confidence, quality/total-burden comparison, decision-stability checks, One-Blocker Tiny Spike, modular composition, bounded customization, adoption controls, re-evaluation and the explicit-user-authority gate for any custom commodity exception.

It is subordinate to Unified V2 and does not choose a specific framework by itself.

### 2.2 Recurring discretionary trading behavior / edge review

For weekly or periodic review of the user's manual/discretionary trading behavior, edge, session/regime dependence, execution errors, fees, MAE/MFE, and week-over-week behavioral improvement, use:

- `governance/TRADING_BEHAVIOR_AND_EDGE_REVIEW_PROCEDURE_V1_2026-09-06.md`
- `governance/TRADING_BEHAVIOR_REVIEW_AND_EXPERIMENT_LIFECYCLE_V1_2026-09-13.md`

Short-horizon weekly/stage targets are tracked in one lightweight GitHub record:

- Issue #171 — `Trading Behavior — Weekly Optimization Log`

The lifecycle rule separates durable repository principles from tunable weekly experiments. Routine weekly targets are appended as dated comments to Issue #171 and do **not** require a new governance file / branch / PR / independent review / merge by default. A weekly item moves into repository authority only after the lifecycle promotion gate is satisfied.

The dated week-beginning-2026-09-07 baseline embedded in §13 of the parent procedure is historical experiment evidence after 2026-09-14; it is not the current active weekly target set. Current weekly targets come from the latest applicable Issue #171 comment.

These are narrow task-conditional research/review procedures, not project-wide engineering governance and not trading authority. The parent procedure standardizes UTC+08:00 time normalization, flat-to-flat episode reconstruction, Korea/US opening-regime analysis, Macro × US Open interaction analysis, stop-discipline/rapid-reentry diagnostics, fee/friction analysis, MAE/MFE integration, evidence labels, deduplicated counterfactuals, and week-over-week comparison. Raw private/account trade data remains outside Git history.

### 2.3 Market / instrument and venue selection

For recurring selection of **what to trade, where to trade it, and whether the exact route is suitable for Human or Quant use**, use:

- `governance/MARKET_AND_VENUE_SELECTION_FRAMEWORK_V1_2026-09-13.md`

This narrow specialized method is subordinate to Unified V2. It governs global market discovery, non-authoritative candidate-underlying shortlists, venue-expression qualification, execution/stop/fee/margin/liquidation/capital economics, Human/Quant fit, final Universe/route construction, switching hysteresis and recurring reselection.

Important ownership boundaries:

```text
STRATEGY_RESEARCH
-> owns Strategy Demand Profile + Strategy economics/evidence

MARKET_AND_VENUE_SELECTION
-> owns recurring underlying/expression qualification + Human/Quant Universe + route map

ENGINEERING
-> owns approved Registry/runtime implementation + provider/history/Trading-Freshness/realistic-scale/adapter qualification
```

Economic qualification never bypasses Issue #102 provider-budget, history/replay, Trading-Freshness or realistic-scale gates. The MVSF method grants no production Universe change, venue migration, account/capital action or exchange-write authority.

## 3. Human-executed commands / launchers

For every nontrivial human-executed Terminal/shell/launcher command use:

- `governance/GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md`

It operationalizes V2 command rules: environment evidence, exact CLI invocation contract, canonical validation commands, platform fidelity, false-gate prevention, file-backed execution, checkpoint/resume, command repair budget and evidence egress.

It is a specialized procedure/incident catalogue; Unified V2 owns the project-wide invariant.

### 3.1 GitHub local transport / reviewed-PR closeout

For user-local Git transport for this repository, generated local Git publication commands, or the terminal disposition of an independently reviewed Pull Request, use:

- `governance/GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md`

This narrow procedure is subordinate to Unified V2. It canonizes the accepted project-local HTTPS + GitHub CLI + system credential-store route, deprecates SSH-over-443 as the default local Git path for this project, and operationalizes the existing V2 requirement that reviewed work reach an explicit terminal disposition.

It does not create credential-scope, Mark Ready, merge, deployment/runtime/cloud, exchange-write or trading authority. A reviewed PR that is accepted after final PASS still requires current retained user authority for Mark Ready and merge; a REPLAN / REJECT / SUPERSEDED PR must be explicitly closed or superseded rather than left indefinitely open/draft.

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
SURFACE=FRESH_ACCEPTED_INDEPENDENT_REVIEW_CONTEXT
MODEL=STRONGEST_APPROPRIATE_ACCEPTED_REVIEW_MODEL
REASONING=HIGHEST_APPROPRIATE
WRITER_OR_ENGINEERING_CONTROL_CONTEXT=PROHIBITED_FOR_INDEPENDENT_ACCEPTANCE
ORDINARY_CHATGPT_NEW_WINDOW=ACCEPTED_FALLBACK
PROVIDER_NATIVE_REVIEWER_AGENT=ALLOWED_AFTER_INDEPENDENT_TOOL_ROUTE_ACCEPTANCE
```

The handoff is a compact Review Manifest, not an Engineering-Control conclusion dump. It contains exact target identity, changed scope/diff, frozen acceptance criteria, required safety boundaries, decisive evidence locators and any explicitly untrusted prior conclusions.

If exact GitHub artifacts + exact-head CI are sufficient, the fresh Reviewer reads them directly through the accepted canonical surface. Default reviewer loading is delta/targeted: exact target -> exact diff -> acceptance contract -> decisive CI/artifact -> only necessary upstream/canonical history. Full Issue/PR history and full governance reload are prohibited by default.

If local evidence is required, prefer deterministic evidence generation -> hash-manifested review bundle -> exact delivery to the fresh independent Reviewer. Use `.agents/skills/trade-os-independent-review-bundle` when applicable.

Writer self-review, Supervisor self-review and Engineering-Control self-review never become independent acceptance. A provider-native Reviewer Agent is authority-bearing only when its accepted route enforces fresh context, read-only review authority, direct exact-canonical-evidence access, no inheritance of prior PASS conclusions as facts, and idempotent result egress through an accepted direct or lossless transport surface.

One authority-bearing Review uses one fresh Reviewer context/agent, which retires after result egress. A repaired or materially changed head receives a new fresh Reviewer context. If proof collection threatens context integrity, freeze a bounded evidence-verification checkpoint and adjudicate in a fresh context. Authority-bearing result writeback is idempotent: derive the deterministic Review Result Key, fresh-read before write, and consume an existing matching result instead of duplicating it.

## 6. Tool onboarding / material tool change

For a new engineering executor/operator/orchestrator or a material configuration/permission/session/routing change read:

- `governance/ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`

A tool requires exact identity, representative capability/safety evidence, independent acceptance and separate user activation before first project use. Material tool changes require re-acceptance.

The mature-solution/build-vs-buy gate in Unified V2 and the external mature-solution selection procedure apply before custom commodity tooling.

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