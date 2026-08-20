# Trader Assist / Trade OS — Engineering Executor Selection and Tool-Profile Routing V1

**Status:** SPECIALIZED GOVERNANCE PROPOSAL  
**Effective date:** 2026-08-20  
**Repository:** `woshixiong/trader-assist-v0`  
**Scope:** task-level selection and switching among approved L2 coding executors/models, plus automatic routing to the selected tool's GitHub-resident usage profile.

This file is a narrow execution companion to the canonical Unified Engineering Governance, Mandatory Engineering Preflight, Research/Evidence/Decision Method and existing executor-specific profiles. It does not change product/strategy/runtime semantics and grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission, cancellation or trading authority.

---

## 1. Core decision

The project has three peer L2 coding-executor paths:

```text
CODEX_CLI
TRAE / TRAE_COMPUTER_USE
DEEPSEEK_HARNESS
```

No current issue, backlog item, old tooling-priority file, historical PR body or prior chat permanently assigns all future engineering work to one of them.

The binding selection rule is:

```text
USER_CURRENT_SELECTION = FINAL TASK-LEVEL EXECUTOR/MODEL CHOICE
ENGINEERING_CONTROL = MAY RECOMMEND, MUST FREEZE AND ENCODE THE USER'S CURRENT CHOICE
GLOBAL_FIXED_PRIMARY_WRITER = NO
STALE_EXECUTOR_SEQUENCING_SNAPSHOT = NON_BINDING FOR A NEW TASK
```

If the user has already selected an executor/model for the current coherent task/stage, Engineering must use that selection until the user changes it or a real capability/safety blocker forces `SAFE_STOP` and a new route decision.

If the user has not yet selected an executor/model for a material Writer stage, Engineering may recommend the capability/cost/quality fit, but it must not silently override an explicit user choice or treat an old sequencing snapshot as current authority.

A current user selection may supersede only the executor/model-routing field of an older task snapshot. It does **not** supersede technical acceptance criteria, authority invariants, repair budget, allowed scope, tests, exact-artifact review, CI, independent Review or retained user gates.

---

## 2. Switching semantics

"Free switching" means the user may select any approved peer executor for each bounded task or coherent stage. It does **not** mean competing Writers may mutate the same authority concurrently.

Preserve:

```text
ONE_PRIMARY_WRITER_PER_COHERENT_SHARED_AUTHORITY_STAGE=YES
COMPETING_WRITERS_ON_SAME_ARTIFACT=NO
```

If the user switches executor/model between coherent stages:

```text
FREEZE EXACT CURRENT ARTIFACT / HEAD / DIRTY HASH
→ CLOSE OR PAUSE THE OLD WRITER CONTEXT
→ RE-RUN NORMAL L1 PREFLIGHT FOR THE NEXT STAGE
→ SELECT THE NEW TOOL PROFILE
→ ISSUE ONE COMPLETE TASK PACKET FOR THE NEW EXECUTOR
→ NEW EXECUTOR ACKNOWLEDGES EXACT WORKTREE / ARTIFACT / AUTHORITY
→ EXECUTE
```

If the user requests a switch in the middle of a shared-authority mutation stage, Engineering must first choose a safe handoff boundary. Do not leave two Writers live against the same worktree/branch or make the user manually reconstruct state.

A Writer may be reused in the same session only where that tool's accepted profile permits it and all of the following remain unchanged:

- role;
- coherent stage;
- worktree/artifact;
- authority;
- task objective;
- independence is not required.

A new session is required when independence is required or when task/role/worktree/authority/material stage changes materially.

---

## 3. Automatic tool-profile routing

After the user/existing stage selects the executor/model, Engineering Control must automatically read the corresponding GitHub profile before writing the downstream command/prompt.

### 3.1 DeepSeek Harness selected

Read and apply:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`.

Default operator UX remains the merged one-paste native-headless route when applicable.

### 3.2 Trae + GLM selected

Read and apply:

- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`;
- the canonical high-constraint GLM baseline in `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md` section 29;
- current task-specific Product/Strategy/Operations/Security authority.

In the current workflow:

```text
EXECUTOR=TRAE
MODEL=GLM-family model explicitly selected by the user, currently GLM-5.3 where available in the user's Trae surface
```

GLM is a model, not a fourth executor authority.

### 3.3 Codex selected

Until a later Codex-specific profile is independently accepted and merged, use the canonical Codex/session/token rules already present in the Unified Engineering Governance and the normal one-paste Terminal rule.

Draft PR #111 is a research/proposal input only and is **not** canonical authority while it remains unmerged. When Codex work resumes, reconcile/retarget that work against live `main` before any later acceptance/merge.

---

## 4. No stale "current tooling priority" can pin a task

`governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` is a historical sequencing snapshot and must no longer be interpreted as a universal current Primary-Writer rule.

The following old-style fields are therefore not durable executor authority:

```text
NOW=FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK
NEXT_1=...
NEXT_2=...
CURRENT_TOOLING_PRIORITY_SELECTS_<TOOL>
```

For future tasks, replace them with:

```text
CURRENT_USER_SELECTED_EXECUTOR=
CURRENT_USER_SELECTED_MODEL=
SELECTION_SCOPE=THIS_BOUNDED_TASK_OR_COHERENT_STAGE
PROFILE_ROUTING=
```

A task-specific Issue or PR may still record the selected executor/model as an execution snapshot. That snapshot does not prevent the user from selecting a different approved executor for a later bounded task/stage.

---

## 5. Engineering Control generation rule

Before producing a Writer prompt/Terminal block, Engineering Control must:

1. live-verify `main`, active Issue/PR, exact artifact/head and relevant CI;
2. complete `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`;
3. complete `ENGINEERING_PREFLIGHT_GATE=PASS` for material Writer work;
4. freeze the user's current executor/model selection;
5. load the selected tool profile from GitHub;
6. load current task-specific authority;
7. create one complete high-constraint Task Packet;
8. choose the selected tool's operator transport;
9. preserve all retained user gates.

The user must not be asked to manually combine generic project rules with a separate executor addendum when Engineering can produce the complete current packet itself.

The downstream packet must identify at minimum where applicable:

```text
ROLE / MODE
TASK_ID
EXECUTOR
MODEL
REASONING/PRESET IF THE CURRENT TOOL SURFACE ACTUALLY EXPOSES AND L1 FREEZES IT
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

Do not invent model flags, reasoning controls, sandbox semantics, resume commands or provider settings that are not verified on the selected current tool surface.

---

## 6. Capability mismatch does not silently reroute

If the selected tool cannot perform a mandatory task gate:

```text
SAFE_STOP
→ REPORT THE EXACT CAPABILITY GAP
→ ENGINEERING MAY RECOMMEND ANOTHER APPROVED EXECUTOR
→ USER SELECTS / CONFIRMS THE NEW ROUTE
```

Do not silently switch executor, model, worktree, permission scope, provider, reasoning tier or UI/CLI surface merely because execution is inconvenient.

Examples of real capability gaps include:

- no access to the required local worktree;
- inability to run the required test/runtime;
- inability to preserve exact artifact identity;
- missing authorized Git/GitHub action needed by the coherent stage;
- inability to enforce the required write boundary;
- tool/model behavior that repeatedly violates the frozen high-constraint packet after the allowed repair budget.

---

## 7. Review and publication independence

Changing executor does not change acceptance rules.

```text
WRITER_PASS != INDEPENDENT_ACCEPTANCE
```

Independent Review must inspect the actual exact artifact/delta/head and relevant CI. The Reviewer must not simply inherit the Writer's reasoning or use the same session when independence is a control objective.

Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission/cancellation and autonomous trading remain separate explicit current user gates.

---

## 8. Current Issue #112 coordination

Issue #112's technical acceptance matrix remains unchanged.

Its body currently contains an old sequencing sentence that names `DEEPSEEK_HARNESS` as Primary Writer. Under this routing rule that sentence is a stale executor snapshot only.

The user's current task-level selection for the ongoing Issue #112 development flow is:

```text
EXECUTOR=TRAE
MODEL=GLM-5.3
```

until the user changes it. This changes no Issue #112 production semantics, accepted baseline, scope, test authenticity requirement, repair budget, publication gate or host/runtime authority.

A separate live Issue #112 coordination note should point future windows to this interpretation rather than rewriting the technical acceptance matrix merely to change executor routing.

---

## 9. Tooling backlog

Deferred setup work is tracked in GitHub Issue #115:

- two DeepSeek Harness real-task validations;
- Codex settings/profile work;
- Hermes installation/configuration.

DeepSeek Harness installation/configuration and the merged one-paste workflow are complete enough to pause; the two remaining DSH items are evidence to collect during a future real DSH task, not another standalone setup stage.

---

## 10. Decision

```text
DECISION=PROCEED
USER_CONTROLS_TASK_LEVEL_EXECUTOR_MODEL_SELECTION=YES
GLOBAL_FIXED_PRIMARY_WRITER=NO
ENGINEERING_AUTO_LOADS_SELECTED_TOOL_PROFILE=YES
ONE_PRIMARY_WRITER_PER_COHERENT_STAGE=YES
SILENT_EXECUTOR_SUBSTITUTION=NO
STALE_TOOLING_PRIORITY_SNAPSHOT_BINDS_NEW_TASK=NO
ISSUE112_CURRENT_SELECTION=TRAE+GLM-5.3
INDEPENDENT_REVIEW_REQUIRED=YES
```
