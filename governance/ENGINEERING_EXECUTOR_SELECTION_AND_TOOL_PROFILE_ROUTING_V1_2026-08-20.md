# Trader Assist / Trade OS — Engineering Executor Selection and Tool-Profile Routing V1

**Status:** SPECIALIZED GOVERNANCE PROPOSAL  
**Effective date:** 2026-08-20  
**Repository:** `woshixiong/trader-assist-v0`  
**Scope:** task-level selection and switching among approved L2 coding executors/models, plus automatic routing to the selected tool's GitHub-resident usage profile.

This file is the stable switching layer. It must not absorb model-version-specific tuning. Current model details belong in the selected executor/model profile. It does not change product/strategy/runtime semantics and grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission, cancellation or trading authority.

---

## 1. Core decision

The project has three peer L2 coding-executor paths:

```text
CODEX_CLI
TRAE / TRAE_COMPUTER_USE
DEEPSEEK_HARNESS
```

No current issue, backlog item, old tooling-priority file, historical PR body or prior chat permanently assigns all future engineering work to one of them.

```text
USER_CURRENT_SELECTION = FINAL TASK-LEVEL EXECUTOR/MODEL CHOICE
ENGINEERING_CONTROL = MAY RECOMMEND, MUST FREEZE AND ENCODE THE USER'S CURRENT CHOICE
GLOBAL_FIXED_PRIMARY_WRITER = NO
STALE_EXECUTOR_SEQUENCING_SNAPSHOT = NON_BINDING FOR A NEW TASK
```

If the user has selected an executor/model for the current coherent task/stage, Engineering uses that selection until the user changes it or a real capability/safety blocker forces `SAFE_STOP` and a new route decision.

If the user has not yet selected one for a material Writer stage, Engineering may recommend the capability/cost/quality fit. It must not silently override an explicit user choice or treat an old sequencing snapshot as current authority.

A current user selection changes only executor/model routing. It does not supersede technical acceptance criteria, authority invariants, repair budget, allowed scope, tests, exact-artifact review, CI, independent Review or retained user gates.

---

## 2. Switching semantics

"Free switching" means the user may select any approved peer executor for each bounded task or coherent stage. It does not mean competing Writers may mutate the same authority concurrently.

```text
ONE_PRIMARY_WRITER_PER_COHERENT_SHARED_AUTHORITY_STAGE=YES
COMPETING_WRITERS_ON_SAME_ARTIFACT=NO
```

If switching between coherent stages:

```text
FREEZE EXACT CURRENT ARTIFACT / HEAD / DIRTY HASH
→ CLOSE OR PAUSE OLD WRITER CONTEXT
→ RE-RUN NORMAL L1 PREFLIGHT FOR NEXT STAGE
→ SELECT NEW EXECUTOR + MODEL
→ LOAD SELECTED TOOL/FAMILY PROFILE + CURRENT MODEL PROFILE
→ ISSUE ONE COMPLETE TASK PACKET
→ NEW EXECUTOR ACKNOWLEDGES EXACT WORKTREE / ARTIFACT / AUTHORITY
→ EXECUTE
```

If a switch is requested mid-mutation stage, Engineering first establishes a safe handoff boundary. Never leave two Writers active on the same worktree/branch or make the user manually reconstruct authoritative state.

A session may be reused only where the selected tool profile permits it and role, coherent stage, worktree/artifact, authority, objective and required independence remain compatible.

---

## 3. Automatic profile routing

After the executor/model is selected, Engineering Control automatically reads the corresponding GitHub profile before generating the downstream command/prompt.

### 3.1 DeepSeek Harness selected

Read and apply:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`.

Default bounded operator UX remains the merged one-paste native-headless route when applicable.

### 3.2 Trae + GLM selected

Read and apply:

- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` — stable version-independent family/tool core;
- `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md` — refreshable current GLM model snapshot/delta;
- section 29 of `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`;
- current task-specific Product/Strategy/Operations/Security authority.

```text
EXECUTOR=TRAE
MODEL=GLM-family model explicitly selected by the user
```

GLM is a model, not a fourth executor authority.

### 3.3 Codex selected

Until a later Codex-specific profile is independently accepted and merged, use the canonical Codex/session/token rules already present in Unified Engineering Governance and the normal one-paste Terminal rule.

Draft PR #111 remains proposal/history input only until reconciled against current `main`, independently accepted and merged.

---

## 4. Model-version refresh rule — switching architecture stays stable

Tool/executor switching is intentionally separated from model-version tuning.

```text
EXECUTOR_SWITCHING_ARCHITECTURE = STABLE BY DEFAULT
VERSION_INDEPENDENT_TOOL_FAMILY_CORE = STABLE BY DEFAULT
CURRENT_MODEL_PROFILE = REFRESHABLE
```

For Trae+GLM specifically, a new GLM version should normally change only:

`governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`

Refresh sequence:

```text
VERIFY CURRENT TOOL-SURFACE MODEL LABEL
→ CHECK CURRENT FIRST-PARTY MODEL/TOOL DOCUMENTATION
→ VERIFY ONLY ACTUALLY EXPOSED CONTROLS/LIMITS
→ COMPARE WITH RECENT REAL PROJECT EVIDENCE
→ UPDATE CURRENT MODEL PROFILE ONLY
```

Change the version-independent Trae+GLM core only if a durable tool/family workflow semantic changes. Change this executor-routing file only if the executor pool or L1/L2 routing/authority model changes.

Do not create a new switching constitution for `GLM-5.4`, `GLM-6`, a newer Codex model or a newer DeepSeek model. Do not inherit hidden reasoning/cache/API controls from adjacent model generations.

---

## 5. Stale tooling priority cannot pin a task

`governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` is historical sequencing provenance and no longer a universal Primary-Writer rule.

Old fields such as:

```text
NOW=FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK
NEXT_1=...
NEXT_2=...
CURRENT_TOOLING_PRIORITY_SELECTS_<TOOL>
```

are not durable task-routing authority.

For current tasks record:

```text
CURRENT_USER_SELECTED_EXECUTOR=
CURRENT_USER_SELECTED_MODEL=
SELECTION_SCOPE=THIS_BOUNDED_TASK_OR_COHERENT_STAGE
PROFILE_ROUTING=
MODEL_PROFILE_LAST_VERIFIED_AT=
```

A task-specific Issue/PR may record the current selection as an execution snapshot. That snapshot does not bind a later bounded stage after the user changes the selection.

---

## 6. Engineering Control generation rule

Before producing a Writer prompt/Terminal block, Engineering Control must:

1. live-verify `main`, active Issue/PR, exact artifact/head and relevant CI;
2. complete `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`;
3. complete `ENGINEERING_PREFLIGHT_GATE=PASS` for material Writer work;
4. freeze current executor/model selection;
5. load the selected executor/tool family profile;
6. load the current model profile/snapshot where one exists;
7. if the selected model differs from the current verified snapshot, perform the narrow model-profile refresh before relying on model-specific controls;
8. load current task-specific authority;
9. create one complete high-constraint Task Packet;
10. choose the selected tool's operator transport;
11. preserve all retained user gates.

The downstream packet identifies, where applicable:

```text
ROLE / MODE
TASK_ID
EXECUTOR
MODEL
REASONING/PRESET ONLY IF CURRENT TOOL SURFACE ACTUALLY EXPOSES AND L1 FREEZES IT
REPOSITORY
LIVE_MAIN / EXACT_BASE / EXPECTED_HEAD
BRANCH / WORKTREE
ACCEPTED BASELINE / ROOT CAUSE
ALLOWED FILES
PROHIBITED SCOPE
MUST-PRESERVE AUTHORITIES
ATTACK / NEGATIVE CASES
EXACT TEST / LINT / COMPILE / DIFF COMMANDS
SAFE_STOP CONDITIONS
OUTPUT / EVIDENCE CONTRACT
FINAL USER AUTHORITY BOUNDARY
```

Do not invent model flags, reasoning controls, sandbox semantics, resume commands or provider settings that are not verified on the current selected surface.

---

## 7. Capability mismatch does not silently reroute

If the selected tool cannot perform a mandatory gate:

```text
SAFE_STOP
→ REPORT EXACT CAPABILITY GAP
→ ENGINEERING MAY RECOMMEND ANOTHER APPROVED EXECUTOR
→ USER SELECTS / CONFIRMS NEW ROUTE
```

Do not silently change executor, model, worktree, permission scope, provider, reasoning tier or UI/CLI surface.

Examples include lack of required worktree access, inability to run mandatory tests/runtime, inability to preserve exact artifact identity, missing authorized Git/GitHub capability, inability to enforce write scope, or repeated model/tool behavior violating the frozen packet after the repair budget.

---

## 8. Review and publication independence

Changing executor/model does not change acceptance rules.

```text
WRITER_PASS != INDEPENDENT_ACCEPTANCE
```

Independent Review inspects the exact artifact/delta/head and relevant CI and does not inherit the Writer session when independence matters.

Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission/cancellation and autonomous trading remain separate explicit current user gates.

---

## 9. Current Issue #112 coordination

Issue #112's technical acceptance matrix remains unchanged.

Current task-level selection:

```text
EXECUTOR=TRAE
MODEL=GLM-5.3
```

until the user changes it. This changes no production semantics, accepted baseline, scope, test authenticity requirement, repair budget, publication gate or runtime authority.

The integrity-bound Issue #112 artifact remains rooted at its accepted repair baseline; governance-only `main` movement does not authorize rebase/reset/normalization of that artifact.

---

## 10. Tooling backlog

Issue #115 tracks:

- two future DSH real-task validations;
- Codex settings/profile work;
- Hermes installation/configuration.

DeepSeek Harness installation/configuration and the merged one-paste workflow are complete enough to pause. Remaining DSH checks are collected during a future real DSH task rather than a synthetic paid stage.

---

## 11. Frozen decision

```text
DECISION=PROCEED
USER_CONTROLS_TASK_LEVEL_EXECUTOR_MODEL_SELECTION=YES
APPROVED_PEER_EXECUTORS=CODEX_CLI|TRAE|DEEPSEEK_HARNESS
GLOBAL_FIXED_PRIMARY_WRITER=NO
ENGINEERING_AUTO_LOADS_SELECTED_TOOL_PROFILE=YES
MODEL_PROFILE_SEPARATE_FROM_SWITCHING_ARCHITECTURE=YES
GLM_MODEL_UPGRADE_DEFAULT_CHANGE_SCOPE=TRAE_GLM_CURRENT_MODEL_PROFILE.md_ONLY
ONE_PRIMARY_WRITER_PER_COHERENT_STAGE=YES
SILENT_EXECUTOR_OR_MODEL_SUBSTITUTION=NO
STALE_TOOLING_PRIORITY_SNAPSHOT_BINDS_NEW_TASK=NO
ISSUE112_CURRENT_SELECTION=TRAE+GLM-5.3
INDEPENDENT_REVIEW_REQUIRED=YES
```