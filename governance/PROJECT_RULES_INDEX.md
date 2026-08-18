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
13. current live GitHub objects and exact-head CI state.

When the role is `HERMES_EXECUTION_OPERATOR`, additionally read:

- `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`;
- `schemas/control/lossless-task-packet-v1.schema.json`;
- and, for `TRAE_COMPUTER_USE`, `governance/HERMES_TRAE_COMPUTER_USE_PROFILE_V1_2026-08-16.md`.

When DeepSeek Harness is selected as the L2 coding executor, additionally read:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` for current sequencing and first-real-task setup-verification timing.

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
- one primary Writer for shared authority plus independent review;
- exact artifact / exact-head CI / delta-first review;
- one normal repair + at most one exceptional repair, then holistic convergence;
- complete task packets and prohibition on architecture-critical prompt addenda;
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
3. explicit synthesis showing what the external evidence confirms, modifies, rejects or leaves uncertain before final recommendation.

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

## Operator delivery rule — current ruling

The current default for user-operated macOS engineering work is **one contiguous ordinary-Terminal paste**.

Engineering owns the routing inside the block. The user should not have to separately `cd`, launch Codex, choose shell-vs-agent text, paste a second prompt, manually select the branch/worktree, or create a transport file when those steps can safely be encoded.

The older requirement that every user-facing handoff separately expose `Terminal local command` versus `Terminal -> Codex CLI` is superseded when it adds no safety value. The orchestrator must still know and encode the execution class internally, but it must not turn that distinction into extra user work.

Extra human steps are allowed only when technically unavoidable or required by a security/authority gate, such as MFA, OS credential approval, secret handling, GUI-only action, explicit Mark Ready/merge/deploy/runtime authorization, credentials/private API/signing or exchange-write authority.

For an already-connected FinalShell target-host session, use one contiguous remote-shell block and do not repeat SSH setup.

---

## Specialized Hermes / lossless transport rule

Hermes is execution/transport infrastructure only. It is not a research, engineering-route, architecture, review, repair, approval or trading authority.

A Hermes task must use the merged Lossless Task Packet contract, explicit machine-readable destination/executor/permissions/stop conditions and canonical integrity verification. Hermes must not paraphrase authoritative handoffs, infer missing fields, choose the executor/model/route, independently retry a failed task, or declare engineering PASS.

Raw executor evidence remains authoritative.

---

## Specialized coding-executor pool / DeepSeek Harness rule

Engineering uses three peer L2 coding executors:

```text
CODEX_CLI | TRAE_COMPUTER_USE / TRAE | DEEPSEEK_HARNESS
```

Hermes plus an approved low-cost/free model is a separate L3 routine operator, not a fourth coding or decision authority.

When DeepSeek Harness is selected, the binding specialized files are:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` for current sequencing and setup-verification timing.

DeepSeek API use is fixed to first-party DeepSeek Harness with `deepseek-official`. Normal coding uses PTC/Code Mode, `workspace-write + ask`, stable small repository instructions, project-local progressive skills, stable-prefix/cache discipline, bounded normal provider retries, L1-frozen model/reasoning and official off-peak scheduling where practical.

No separate synthetic coding qualification, Harness-only review, or standalone paid setup-verification stage is required before the first real bounded DeepSeek task.

For the first real task, before Writer file mutation, mechanically verify the execution baseline required for safe use: expected DSH version, `deepseek-official`, PTC/Code, `workspace-write + ask`, root `AGENTS.md` autoload, and discovery of all four project skills. If one of those checks fails, SAFE_STOP before file mutation.

Skill-body progressive loading and cache telemetry/cache reuse are efficiency evidence collected during the real task where naturally observable. They are not prerequisites to start the first real task, no synthetic requests are required, and no arbitrary cache-hit percentage is required. The first actual assigned task supplies real coding capability evidence under that task's normal project validation/review requirements.

Current tooling priority is unambiguous:

```text
1. FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK = NOW
2. CODEX_CONFIGURATION_AND_EFFICIENCY_PROFILE = DEFERRED_UNTIL_USER_RESUMES
3. HERMES_CONFIGURATION = LATER / WHEN USER NEXT PRIORITIZES
```

`governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` is the authoritative current sequencing/timing record and explicitly supersedes stale sequencing or pre-first-task readiness phrases in the two DeepSeek draft technical documents and prior PR-body text. This current priority changes no technical safety rule and grants no retained authority gate.

---

## Governance-source disposition

The unified standard intentionally absorbs the durable project-wide principles from these Draft governance lines:

- PR #101 — continuity / scale-provider gate;
- PR #96 — one-paste Terminal delivery;
- PR #86 — Engineering Workflow V4 efficiency method;
- PR #79 — Codex token-efficiency and prompt rules;
- PR #67 — mature-solution-first and cumulative small-step delivery;
- PR #58 — capability-matched continuous-stage execution;
- PR #51 — simplicity-first and route stop-loss.

After the unified rule is independently accepted and merged, these Drafts are historical/salvage inputs rather than competing active constitutions. Do not resume patching an old governance branch merely because it contains an earlier version of an absorbed rule.

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

No research, implementation, review, CI result, Task Packet, Agent role or governance document implicitly authorizes:

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
