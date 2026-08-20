# Project Rules Index

## Mandatory successor-window read order

Every successor window / Agent reads this order before acting:

1. `AGENTS.md`
2. `governance/PROJECT_RULES_INDEX.md`
3. `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`
4. `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`
5. `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
6. `governance/PROJECT_STATE.json`
7. `governance/V0_FAST_LAUNCH_PROGRAM.json`
8. `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`
9. `governance/FIRST_LAUNCH_MINIMUM_RECOVERY_READINESS_V1.md`
10. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`
11. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`
12. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_AUTOMATION_ABANDONMENT_RULING_V1.md`
13. `governance/ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md` for execution-class routing, current task-level executor/model selection and automatic tool-profile routing.
14. current live GitHub objects and exact-head CI state.

When the role is `HERMES_EXECUTION_OPERATOR`, additionally read:

- `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`;
- `schemas/control/lossless-task-packet-v1.schema.json`;
- and, for `TRAE_COMPUTER_USE`, `governance/HERMES_TRAE_COMPUTER_USE_PROFILE_V1_2026-08-16.md`.

When DeepSeek Harness is selected as the L2 coding executor, additionally read:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`.

`governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` is historical sequencing provenance only. It must not pin a new task to DeepSeek Harness.

When Trae + a GLM-family model is selected, additionally read:

- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` — stable version-independent Trae+GLM family/tool core;
- `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md` — refreshable current GLM model snapshot/delta;
- relevant Unified Governance sections;
- the active task's current Product / Strategy / Operations / Security authority.

The exact GLM model is selected per task and is not permanent architecture. A newer GLM version should update only `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md` by default after a narrow current-Trae-surface + first-party Z.AI/Trae verification. Keep the version-independent Trae+GLM core and execution-class/three-executor routing unchanged unless the new model/tool actually changes durable workflow or authority semantics.

When Codex is selected, additionally read:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` — stable version-independent Codex CLI core;
- `governance/CODEX_CURRENT_MODEL_PROFILE.md` — refreshable current Codex model/reasoning/service-tier snapshot;
- the Unified Engineering Governance Codex session/prompt/token-efficiency and one-paste rules;
- the active task's current Product / Strategy / Operations / Security authority.

A newer Codex/OpenAI model should update only `governance/CODEX_CURRENT_MODEL_PROFILE.md` by default after a narrow current-Codex-surface + first-party OpenAI verification. Draft PR #111 is historical/salvage input and not a competing canonical Codex profile.

Live GitHub objects override stale chat snapshots and stale PR-body snapshots. Future windows must resolve live GitHub state before relying on historical text.

No governance file independently grants host, deployment, runtime, smoke, credential, account, signing or exchange-write authority.

---

## Canonical engineering-process authority

`governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md` is the canonical future engineering-process entry point.

Before **any** project work, every participant must compare the task against that ruleset and record:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
```

or safe-stop.

For material Writer work, the unified rule additionally requires:

```text
ENGINEERING_PREFLIGHT_GATE=PASS
```

under `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md` before dispatch.

The unified standard consolidates the durable project-wide rules covering:

- independent analysis → external evidence/mature-solution research → synthesis;
- mature/provider-native solution first;
- proprietary strategy/value focus;
- simplicity by total lifecycle/operator/review cost;
- cumulative small-step delivery and real-evidence iteration;
- code continuity, stable narrow seams and replaceable implementation policy;
- root-cause/global-authority reasoning before local repair loops;
- external-contract evidence and realistic fixtures;
- scale/provider/freshness budgets and realistic-size tests;
- capability-matched task allocation;
- coherent continuous execution without using the user as a routine message bus;
- GPT-control/direct/deterministic execution before coding Agents when coding capability is unnecessary;
- one primary Writer for shared authority plus independent review;
- exact artifact / exact-head CI / delta-first review;
- one normal repair + at most one exceptional repair, then holistic convergence;
- complete task packets and prohibition on architecture-critical prompt addenda;
- high-constraint complete task packets for GLM-family and DeepSeek-family models when used inside approved L2 coding-executor paths, including explicit worktree, scope, validation, SAFE_STOP and lossless prompt-delivery boundaries;
- lossless handoff for authority-bearing tasks;
- one-paste macOS Terminal delivery;
- Codex session/prompt/token-efficiency rules;
- automation/toil and third-party service rules;
- explicit user-retained release/runtime/account/exchange authority gates.

Do not create a second overlapping general engineering constitution for a new lesson when the unified file can be amended cleanly.

---

## Mandatory research / evidence / decision method

For every applicable material research, planning, strategy, product, engineering, architecture, technology, framework, provider or route decision, use:

`governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`

in this exact order:

1. independent analysis and preliminary position;
2. broad external research, including mature solutions, validated cases, counterexamples and disconfirming evidence;
3. explicit synthesis showing what external evidence confirms, modifies, rejects or leaves uncertain before final recommendation.

Purely mechanical execution and exact state verification are exempt unless they expose a new material design choice.

---

## Mandatory engineering preflight / convergence gate

For every material engineering route, architecture decision, runtime/persistence/provider design, cross-layer repair, technical selection, Writer task package or implementation prompt, apply:

`governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`.

No material Writer prompt may be issued unless the gate covers and passes:

- live GitHub authority;
- independent analysis;
- external mature-solution research where applicable;
- synthesis;
- root cause and affected authorities;
- cross-layer invariants;
- future continuity and replaceability;
- scale/provider/freshness where applicable;
- attack matrix;
- repair stage and stop condition.

After one normal repair plus one exceptional repair, or earlier when a blocker proves a global/cross-layer responsibility error, stop coding and enter `HOLISTIC_CONVERGENCE_GATE`.

If a new architecture-critical requirement is discovered after a Writer prompt is issued but before execution, void the old prompt and regenerate one complete replacement prompt. Do not make the user assemble critical addenda.

---

## Execution-class routing — ordinary GPT control before coding Agents

Before selecting an L2 coding executor, Engineering Control applies:

```text
GPT_CONTROL_DIRECT
→ GPT_CONTROL_DETERMINISTIC_TERMINAL
→ L2_CODING_EXECUTOR only when local agentic coding is required
```

`GPT_CONTROL_DIRECT` covers work the ordinary Engineering/Review GPT window can perform with current connectors/reasoning, such as GitHub state/PR/CI operations, material L1 research/decision work, connector-sufficient independent review, and GitHub-side publication after the branch is already pushed.

`GPT_CONTROL_DETERMINISTIC_TERMINAL` covers local shell/Git mechanics where the exact operation is already frozen and no code/architecture judgment is required. The GPT window generates one fail-closed Terminal block; the user pastes it once. This is the preferred route for deterministic commit/push of an already independently accepted local artifact.

`L2_CODING_EXECUTOR` is reserved for local semantic code inspection, mutation, debugging, refactoring or implementation/test/repair loops. The ordinary GPT window is not a fourth L2 executor.

If a deterministic/publication stage discovers a problem requiring code judgment, stop and create a new bounded coding task. Do not silently turn publication into implementation.

Having a GitHub connector or ability to generate Terminal commands is capability only; it never bypasses the explicit user gates for Mark Ready, merge, deployment, runtime/cloud, credentials, signing or exchange write.

---

## Operator delivery rule — current ruling

The current default for user-operated macOS engineering work is **one contiguous ordinary-Terminal paste** when local Terminal execution is actually required and the selected transport can support it safely.

Engineering owns the routing inside the block. The user should not have to separately `cd`, launch a CLI executor, choose shell-vs-agent text, paste a second authoritative prompt, manually select the branch/worktree, or create a transport file when those steps can safely be encoded.

When no local execution is needed and the GPT control window has a sufficient connector, prefer direct connector execution rather than generating a Terminal block merely for ritual consistency.

When `DEEPSEEK_HARNESS` is selected, the first-party native headless seam is the default bounded Writer route: Engineering generates one contiguous Terminal block that resolves the exact repo/worktree/preflight/frozen Task Packet and launches `dsh --profile headless`. The Web UI is optional for interactive/manual use.

When `CODEX_CLI` is selected, Engineering generates one contiguous Terminal block that performs deterministic identity/preflight, freezes the selected model/reasoning/sandbox/approval settings, and launches provider-native `codex exec` with the complete Task Packet. Interactive TUI is opt-in rather than the normal bounded Writer transport.

When Trae + GLM is selected, Engineering generates the complete Trae+GLM high-constraint packet using the stable family profile plus current model profile. Direct paste remains acceptable while the complete packet fits the current verified interface boundary; if it exceeds the canonical 20,000-character direct-paste ceiling, use the lossless Terminal/file/task-packet route rather than truncating or fragmenting authority-critical instructions.

The older requirement that every user-facing handoff separately expose `Terminal local command` versus `Terminal -> Codex CLI` is superseded when it adds no safety value. The orchestrator still knows and freezes the execution class internally, but must not turn that distinction into extra user work.

Extra human steps are allowed only when technically unavoidable or required by a security/authority gate, such as MFA, OS credential approval, secret handling, GUI-only action, explicit Mark Ready/merge/deploy/runtime authorization, credentials/private API/signing or exchange-write authority.

For an already-connected FinalShell target-host session, use one contiguous remote-shell block and do not repeat SSH setup.

---

## Specialized Hermes / lossless transport rule

Hermes is execution/transport infrastructure only. It is not a research, engineering-route, architecture, review, repair, approval or trading authority.

A Hermes task must use the merged Lossless Task Packet contract, explicit machine-readable destination/executor/permissions/stop conditions and canonical integrity verification. Hermes must not paraphrase authoritative handoffs, infer missing fields, choose the executor/model/route, independently retry a failed task, or declare engineering PASS.

Raw executor evidence remains authoritative.

---

## Specialized coding-executor pool / dynamic routing rule

After execution-class routing establishes that a coding executor is actually required, Engineering uses three peer L2 coding executors:

```text
CODEX_CLI | TRAE_COMPUTER_USE / TRAE | DEEPSEEK_HARNESS
```

GLM-family and DeepSeek-family names identify **models/model families**, not additional L2 executor authorities. Hermes plus an approved low-cost/free model is a separate L3 routine operator, not a fourth coding or decision authority.

For each bounded L2 task or coherent coding stage:

```text
L2 CODING NEED CONFIRMED
→ USER/L1 SELECTS EXECUTOR + MODEL
→ ENGINEERING LOADS SELECTED TOOL CORE + CURRENT MODEL PROFILE
→ ENGINEERING FREEZES COMPLETE TASK PACKET
→ ONE PRIMARY WRITER EXECUTES
→ NORMAL EXACT-ARTIFACT / CI / INDEPENDENT-REVIEW GATES APPLY
```

No tool is the universal Primary Writer. Current user selection is final for task-level L2 routing unless a capability/safety blocker requires `SAFE_STOP` and a new user/L1 route decision. Engineering may recommend based on capability, quality, speed, cost or availability, but may not silently substitute.

Switching tools between coherent stages is allowed and expected. Preserve exact artifact/worktree identity at the handoff; do not leave competing Writers live on the same shared authority.

### DeepSeek Harness selected

Binding specialized files:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`.

DeepSeek API use remains first-party DeepSeek Harness with `deepseek-official`. Normal coding uses the accepted PTC/Code, permission, worktree, cache/skill and fail-closed authority rules in those specialized documents.

DeepSeek Harness installation/configuration and its one-paste workflow are complete enough to pause. The remaining rc.8 execution-seam/capability check and token/cache/progressive-skill evidence are deferred to the next real task in which the user selects DeepSeek Harness; no synthetic paid task is required.

### Trae + GLM selected

Binding specialized files:

- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` — stable version-independent core;
- `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md` — refreshable current model snapshot/delta.

Durable GLM/Trae principles include one coherent bounded stage, high-constraint complete packet, stable control prefix + mutable evidence tail, exact scoped context before broad workspace context, deterministic proof before model tokens, deliberate same-stage session reuse, Regular when sufficient and no undocumented model-specific tuning.

A future newer GLM model updates the current-model profile only by default. It does not require changing this index, execution-class/executor-routing architecture or family core unless durable workflow semantics actually changed.

### Codex selected

Binding specialized files:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` — stable version-independent CLI core;
- `governance/CODEX_CURRENT_MODEL_PROFILE.md` — refreshable current model/reasoning/service-tier matrix;
- Unified Engineering Governance Codex/session/token and one-paste rules.

Durable Codex principles include provider-native `codex exec`, task-local explicit model/reasoning/sandbox settings, exact-session resume only inside one trusted Writer/stage/worktree/authority, `--json` passive usage/evidence, stable-prefix/mutable-tail prompts, small stable `AGENTS.md`, deterministic mechanics before model tokens, no speculative skills/plugins/MCP, Standard service tier by default and no Max/Ultra/broad-permission default.

A future newer Codex/OpenAI model updates `governance/CODEX_CURRENT_MODEL_PROFILE.md` only by default. It does not require changing execution-class routing, L2 executor architecture or the Codex CLI core unless durable tool semantics actually changed.

Draft PR #111 is historical/salvage input. Do not resume or merge it as a second active Codex constitution once the reconciled current-main profile is accepted.

### Historical sequencing snapshot

`governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` exists for provenance of the earlier DeepSeek-first setup sequence. Its `NOW=FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK` text is not current universal task-routing authority.

Current tooling backlog is tracked in GitHub Issue #115.

---

## Governance-source disposition

The unified standard intentionally absorbs the durable project-wide principles from these Draft governance lines:

- PR #101 — continuity / scale-provider gate;
- PR #96 — one-paste Terminal delivery rule;
- PR #86 — Engineering Workflow V4 efficiency method;
- PR #79 — Codex token-efficiency rules;
- PR #67 — mature-solution-first and cumulative small-step delivery;
- PR #58 — capability-matched continuous-stage execution rules;
- PR #51 — simplicity-first and route stop-loss.

After the unified rule is independently accepted and merged, these Drafts are historical/salvage inputs rather than competing active constitutions. Do not resume patching an old governance branch merely because it contains an earlier version of an absorbed rule.

PR #111 is also now historical/salvage input for the current-main Codex profile route; its useful native `codex exec`, exact-session and JSONL principles are reconciled into the new specialized Codex files rather than making the stale stacked branch authoritative.

PR #35 and PR #44 remain salvage/history inputs, not merged authority. PR #42, PR #43 and PR #45 are superseded. PR #48 is a frozen failed-design/historical research reference and has no further repair authority.

`TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md` remains historical workflow provenance; where it conflicts with the unified future engineering standard, the unified standard governs after merge.

---

## Current First Launch recovery boundary

Deferring PR #48-style automation does not permit deferring all recovery preparation.

Before accepted real operation, retain the minimum recovery-readiness anchors:

- independent cloud-account recovery access;
- external recoverable notification-credential source;
- exact release and non-secret path card;
- approved SQLite-consistent backup and restore method;
- one verified post-qualification SQLite backup;
- explicit provider-snapshot or rebuild-only decision.

Event-specific complete automation may remain deferred.

For immediate low-frequency deployment/qualification work, prefer one fixed host, one exact SHA, existing accepted runbooks/status interfaces and temporary one-paste host-specific command bundles rather than rebuilding the failed PR #48 automation route.

The more complete automated qualification capability remains:

`DEFERRED_LOWEST_PRIORITY__NO_CURRENT_IMPLEMENTATION_AUTHORITY`

until measured need justifies a clean current-main design.

---

## User-retained authority gates

No research, implementation, review, CI result, Task Packet, Agent role, connector availability or governance document implicitly authorizes:

- Mark Ready;
- merge;
- deployment;
- production-host/cloud mutation;
- service start/restart/enable/reboot;
- credentials/private keys;
- account/private API;
- wallet/signing/nonce;
- real notification when separately gated;
- exchange write;
- order submission/cancellation;
- autonomous trading or financial action.

These require explicit current authorization and must never be inferred from an earlier stage.