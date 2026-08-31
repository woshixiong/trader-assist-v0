# Trader Assist / Trade OS — Agent Operating Map

This file is a **compact entry map**, not the project encyclopedia. GitHub is the engineering source of truth.

## 1. Mandatory engineering path

Before material engineering work read:

1. `governance/PROJECT_RULES_INDEX.md`
2. `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`
3. current Product / Strategy / Operations / Security authority for the bounded task
4. current live GitHub main / issue / PR / exact-head / CI state.

For a material task, complete the checklist in:

- `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`

No material Writer dispatch without:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

## 2. Load specialized procedures only when applicable

Do **not** read every tool/profile file for every task.

- material direction-setting research -> `PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
- nontrivial human-executed command/launcher -> `GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md`
- model-backed executor selection -> `ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md` + only the selected executor/model profile
- new/materially changed engineering tool -> `ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`
- Local Task Runner -> its accepted Runner profile/skill only when selected and compatible
- Hermes -> Hermes contract/profile only when selected
- target-host deployment/qualification through FinalShell -> `FINALSHELL_TARGET_HOST_DEPLOYMENT_WORKFLOW_V1_2026-08-26.md` + current Operations authority.

The Unified V2 standard owns project-wide engineering policy. Specialized files may be stricter in their narrow domain but are not competing constitutions.

## 3. Universal execution invariants

```text
GITHUB_CANONICAL_SOURCE=YES
ONE_PROJECT_WIDE_ENGINEERING_CONSTITUTION=YES
INDEPENDENT_ANALYSIS_BEFORE_EXTERNAL_CONCLUSIONS=YES_FOR_MATERIAL_DIRECTION_SETTING
MATURE_SOLUTION_FIRST=YES
GLOBAL_ROOT_CAUSE_BEFORE_LOCAL_PATCH_LOOPS=YES
STABLE_NARROW_SEAMS_AND_CONTINUITY=REQUIRED
DEVELOPMENT_AND_VERIFICATION_DESIGNED_TOGETHER=YES
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=YES
VALIDATION_ENVIRONMENT_MUST_MATCH_CLAIM=YES
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
COMPLETE_TASK_PACKET_BEFORE_EXECUTION=YES
WRITER_PASS_NE_INDEPENDENT_ACCEPTANCE=YES
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
ACTIVE_TASK_OWNERSHIP_UNTIL_TERMINAL_DISPOSITION=YES
NO_SILENT_MODEL_EXECUTOR_FALLBACK=YES
NO_HIDDEN_SEMANTIC_RETRY=YES
FALSE_SAFE_STOP_GATE=PROHIBITED
CHECKPOINT_RESUME_INSTEAD_OF_REDO=YES
EXACT_ARTIFACT_EXACT_HEAD_CI_INDEPENDENT_REVIEW=WHEN_APPLICABLE
```

## 4. Repository and authority safety

- no direct commit to `main` for normal engineering work;
- no force-push/shared-history rewrite after review begins;
- no secrets, credentials, wallets, raw private/account data, production DB/log/cache or real account identifiers in commits;
- simulated/default market/account data is never real evidence;
- scope expansion, new material architecture/authority/provider/dependency decision or exhausted repair budget -> `SAFE_STOP` / `L1_DECISION_REQUIRED`;
- Mark Ready, merge, deployment, runtime/cloud mutation, service start/restart/enable/reboot, credentials/private API, wallet/signing, exchange write/order submission/cancellation and autonomous trading always require separate current user authority.

## 5. Review and task ownership

Final independent adjudication defaults to a **new ordinary ChatGPT review window using the strongest appropriate available model and highest appropriate reasoning**.

If GitHub evidence is sufficient, review exact GitHub head/diff + exact-head CI directly. If local evidence is needed, prefer deterministic hash-manifested evidence/review bundles rather than downgrading the final Reviewer to a weaker local coding model.

The current control/orchestration role retains task ownership through intermediate CI/review/publication gates, executes every safe authorized next action, and stops only at the specific external or user-retained authority boundary.

## 6. Stale / historical files

`CODEX.md` and superseded governance are historical evidence only. Do not use them as fallback instruction authority when current indexed governance exists.