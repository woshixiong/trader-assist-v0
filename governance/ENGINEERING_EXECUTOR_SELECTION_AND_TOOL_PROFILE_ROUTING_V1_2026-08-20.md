# Trader Assist / Trade OS — Engineering Executor Selection and Tool-Profile Routing V1

**Status:** SPECIALIZED GOVERNANCE PROPOSAL  
**Effective date:** 2026-08-20  
**Repository:** `woshixiong/trader-assist-v0`  
**Scope:** execution-class routing, task-level selection/switching among approved L2 coding executors/models, and automatic routing to the selected tool's GitHub-resident usage profile.

This file is the stable routing layer. It must not absorb model-version-specific tuning. Current model details belong in refreshable model profiles. It does not change product/strategy/runtime semantics and grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission, cancellation or trading authority.

---

## 1. First route the execution class — do not use a coding Agent unnecessarily

Before selecting Codex, Trae or DeepSeek Harness, Engineering Control determines whether a coding executor is needed at all.

Preferred routing order:

```text
TASK / COHERENT STAGE
→ CAN ENGINEERING CONTROL COMPLETE IT DIRECTLY WITH CONNECTORS / READ-ONLY REASONING?
   YES → GPT_CONTROL_DIRECT
   NO
→ CAN IT BE COMPLETED BY A DETERMINISTIC LOCAL TERMINAL/GIT COMMAND BUNDLE
  WITHOUT CODE/ARCHITECTURE JUDGMENT?
   YES → GPT_CONTROL_DETERMINISTIC_TERMINAL
   NO
→ LOCAL CODE SEMANTIC INSPECTION / MUTATION / DEBUG / REPAIR LOOP REQUIRED
   YES → L2_CODING_EXECUTOR
          → USER/L1 SELECTS CODEX_CLI | TRAE | DEEPSEEK_HARNESS + MODEL
   NO → CAPABILITY_MISMATCH / SAFE_STOP / EXPLICIT ROUTE DECISION
```

This is a **capability and cost routing rule**, not a fourth coding executor.

```text
ORDINARY_GPT_CONTROL_WINDOW_IS_FOURTH_L2_EXECUTOR=NO
L2_CODING_AGENT_FOR_NONCODING_MECHANICAL_WORK=NO_BY_DEFAULT
```

### `GPT_CONTROL_DIRECT`

Prefer the ordinary Engineering/Review GPT window when its connected capabilities are sufficient, including as applicable:

- live GitHub state/Issue/PR/CI inspection;
- research, architecture/product/strategy/operations reasoning at L1;
- independent review that can be completed from exact GitHub artifacts/diffs without local execution;
- governance/document-only GitHub changes allowed by canonical rules;
- create/update Draft PR after the branch is already pushed;
- GitHub comments/labels/review metadata/CI observation;
- Mark Ready or merge **only after separate current user authorization**.

Do not launch a code model merely to call GitHub APIs or restate an already accepted publication decision.

### `GPT_CONTROL_DETERMINISTIC_TERMINAL`

If local state is required but model code judgment is not, Engineering Control generates the normal single contiguous Terminal block. Examples include an already-accepted exact artifact requiring:

- `git status` / branch / SHA / dirty-fingerprint proof;
- deterministic file/hash verification;
- exact pre-authorized test/check command execution where no repair is permitted inside the stage;
- commit/push of an already independently accepted exact artifact when that publication stage is authorized;
- other bounded shell/Git mechanics whose commands and failure behavior are fully known.

The ordinary GPT window does **not** claim to execute the user's local Terminal itself; it owns the deterministic script and the user performs the single paste unless another approved transport exists.

If a deterministic stage fails and fixing it requires semantic code judgment, stop. Reclassify the new work as a bounded L2 coding task rather than quietly turning publication/mechanics into implementation.

### `L2_CODING_EXECUTOR`

Use a peer coding executor when the stage genuinely needs local agentic code work, including:

- semantic codebase inspection that drives implementation;
- source/test mutation;
- debugging with code corrections;
- refactor/migration requiring local reasoning;
- implementation-test-repair loops;
- generated/local artifacts that require code-aware correction.

This routing preference does not override an explicit current user decision to use a particular approved L2 executor, but Engineering should not recommend a coding executor when direct GPT/connector or deterministic Terminal work is sufficient.

---

## 2. Peer L2 executor decision

When execution class is `L2_CODING_EXECUTOR`, the project has three peer paths:

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

If the user has selected an executor/model for the current coherent coding stage, Engineering uses that selection until the user changes it or a real capability/safety blocker forces `SAFE_STOP` and a new route decision.

If the user has not selected one, Engineering may recommend the capability/quality/cost/speed fit. It must not silently override an explicit user choice or treat an old sequencing snapshot as current authority.

A user selection changes executor/model routing only. It does not supersede technical acceptance criteria, authority invariants, repair budget, allowed scope, tests, exact-artifact review, CI, independent Review or retained user gates.

---

## 3. Switching semantics

"Free switching" means the user may select any approved peer executor for each bounded coding task or coherent coding stage. It does not mean competing Writers may mutate the same authority concurrently.

```text
ONE_PRIMARY_WRITER_PER_COHERENT_SHARED_AUTHORITY_STAGE=YES
COMPETING_WRITERS_ON_SAME_ARTIFACT=NO
```

If switching between coherent stages:

```text
FREEZE EXACT CURRENT ARTIFACT / HEAD / DIRTY HASH
→ CLOSE OR PAUSE OLD WRITER CONTEXT
→ RE-RUN NORMAL L1 PREFLIGHT FOR NEXT STAGE
→ RECLASSIFY EXECUTION CLASS
→ IF L2 STILL REQUIRED: SELECT NEW EXECUTOR + MODEL
→ LOAD SELECTED TOOL CORE + CURRENT MODEL PROFILE
→ ISSUE ONE COMPLETE TASK PACKET
→ NEW EXECUTOR ACKNOWLEDGES EXACT WORKTREE / ARTIFACT / AUTHORITY
→ EXECUTE
```

If a switch is requested mid-mutation stage, Engineering first establishes a safe handoff boundary. Never leave two Writers active on the same worktree/branch or make the user manually reconstruct authoritative state.

A session may be reused only where the selected tool profile permits it and role, coherent stage, worktree/artifact, authority, objective and required independence remain compatible.

---

## 4. Automatic profile routing

After an L2 executor/model is selected, Engineering Control automatically reads the corresponding GitHub profile before generating the downstream command/prompt.

### 4.1 DeepSeek Harness selected

Read and apply:

- `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`;
- `governance/DEEPSEEK_HARNESS_NATIVE_HEADLESS_ONE_PASTE_WORKFLOW_V1_2026-08-20.md`.

Default bounded operator UX remains the merged one-paste native-headless route when applicable.

### 4.2 Trae + GLM selected

Read and apply:

- `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` — stable version-independent family/tool core;
- `governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md` — refreshable current GLM model snapshot/delta;
- relevant Unified Governance sections;
- current task-specific Product/Strategy/Operations/Security authority.

```text
EXECUTOR=TRAE
MODEL=GLM-family model explicitly selected by the user/L1
```

GLM is a model, not a fourth executor authority.

### 4.3 Codex selected

Read and apply:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md` — stable version-independent Codex CLI core;
- `governance/CODEX_CURRENT_MODEL_PROFILE.md` — refreshable current model/reasoning/service-tier matrix;
- Unified Engineering Governance Codex/session/token and one-paste rules;
- current task-specific Product/Strategy/Operations/Security authority.

```text
EXECUTOR=CODEX_CLI
MODEL=current Codex-supported model explicitly selected by user/L1
```

Draft PR #111 is historical/salvage input for this reconciled current-main profile. It is not independent canonical authority and must not be merged as a competing Codex constitution.

---

## 5. Model-version refresh rule — routing architecture stays stable

Execution-class routing and L2 executor switching are separated from model-version tuning.

```text
EXECUTION_CLASS_ROUTING = STABLE BY DEFAULT
EXECUTOR_SWITCHING_ARCHITECTURE = STABLE BY DEFAULT
VERSION_INDEPENDENT_TOOL_CORE = STABLE BY DEFAULT
CURRENT_MODEL_PROFILE = REFRESHABLE
```

For Trae+GLM, a new model normally changes only:

`governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`

For Codex, a new current OpenAI/Codex model normally changes only:

`governance/CODEX_CURRENT_MODEL_PROFILE.md`

Refresh sequence:

```text
VERIFY CURRENT TOOL-SURFACE MODEL LABEL / AVAILABILITY
→ CHECK CURRENT FIRST-PARTY MODEL/TOOL DOCUMENTATION
→ VERIFY ONLY ACTUALLY EXPOSED CONTROLS/LIMITS
→ COMPARE WITH RECENT REAL PROJECT EVIDENCE
→ UPDATE CURRENT MODEL PROFILE ONLY
```

Change a version-independent tool core only if durable CLI/tool/session/context/permission/evidence semantics change. Change this routing file only if execution-class routing, the executor pool or the L1/L2 authority model changes.

Do not create a new switching constitution for `GLM-5.4`, `GLM-6`, a newer GPT/Codex model or a newer DeepSeek model. Do not inherit hidden reasoning/cache/API controls from adjacent generations.

---

## 6. Stale tooling priority cannot pin a task

`governance/CURRENT_TOOLING_EXECUTOR_PRIORITY_V1_2026-08-18.md` is historical sequencing provenance and no longer a universal Primary-Writer rule.

Old fields such as:

```text
NOW=FIRST_REAL_BOUNDED_DEEPSEEK_HARNESS_TASK
NEXT_1=...
NEXT_2=...
CURRENT_TOOLING_PRIORITY_SELECTS_<TOOL>
```

are not durable task-routing authority.

For current work record as applicable:

```text
EXECUTION_CLASS=GPT_CONTROL_DIRECT|GPT_CONTROL_DETERMINISTIC_TERMINAL|L2_CODING_EXECUTOR
CURRENT_USER_SELECTED_EXECUTOR=
CURRENT_USER_SELECTED_MODEL=
SELECTION_SCOPE=THIS_BOUNDED_TASK_OR_COHERENT_STAGE
PROFILE_ROUTING=
MODEL_PROFILE_LAST_VERIFIED_AT=
```

A task-specific Issue/PR may record the current selection as an execution snapshot. That snapshot does not bind a later bounded stage after the user changes the selection.

---

## 7. Engineering Control generation rule

Before producing an L2 Writer prompt/Terminal block, Engineering Control must:

1. live-verify `main`, active Issue/PR, exact artifact/head and relevant CI;
2. complete `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`;
3. complete `ENGINEERING_PREFLIGHT_GATE=PASS` for material Writer work;
4. classify the execution class and avoid L2 when GPT-direct/deterministic Terminal is sufficient;
5. if L2 is required, freeze current executor/model selection;
6. load the selected executor/tool family core;
7. load the current model profile/snapshot;
8. if the selected model differs materially from the verified snapshot, perform the narrow model-profile refresh before relying on model-specific controls;
9. load current task-specific authority;
10. create one complete high-constraint Task Packet;
11. choose the selected tool's operator transport;
12. preserve all retained user gates.

The downstream L2 packet identifies, where applicable:

```text
ROLE / MODE
TASK_ID
EXECUTION_CLASS=L2_CODING_EXECUTOR
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

For `GPT_CONTROL_DETERMINISTIC_TERMINAL`, do not wrap deterministic shell mechanics in a model prompt. The Terminal block itself is the execution contract and must fail closed on exact identity/gate mismatch.

---

## 8. Capability mismatch does not silently reroute

If the selected route cannot perform a mandatory gate:

```text
SAFE_STOP
→ REPORT EXACT CAPABILITY GAP
→ ENGINEERING MAY RECOMMEND ANOTHER EXECUTION CLASS / APPROVED EXECUTOR
→ USER/L1 SELECTS OR CONFIRMS THE NEW ROUTE WHEN A MATERIAL/EXPLICIT CHOICE IS REQUIRED
```

Do not silently change executor, model, worktree, permission scope, provider, reasoning tier or UI/CLI surface.

Examples include lack of required worktree access, inability to run mandatory tests/runtime, inability to preserve exact artifact identity, missing authorized Git/GitHub capability, inability to enforce write scope, or repeated model/tool behavior violating the frozen packet after the repair budget.

---

## 9. Publication routing

Publication is not inherently coding work.

Default publication route after an exact artifact has been independently accepted:

```text
IS BRANCH/ARTIFACT ALREADY PUSHED?
  YES → GPT_CONTROL_DIRECT handles GitHub-side Draft PR/update/CI/review metadata
  NO
→ IS LOCAL ARTIFACT EXACTLY FROZEN/ACCEPTED AND ONLY COMMIT/PUSH MECHANICS REMAIN?
  YES → GPT_CONTROL_DETERMINISTIC_TERMINAL one-paste
  NO → SAFE_STOP; if code judgment/repair is required, create a new bounded L2 coding task
```

Do not spend Codex/GLM/DeepSeek tokens on publication merely because the preceding implementation used that tool.

Mark Ready, merge, deployment and all other retained gates remain separately user-authorized. A GPT window having a GitHub connector is capability, not authority.

---

## 10. Review independence

Changing execution class/executor/model does not change acceptance rules.

```text
WRITER_PASS != INDEPENDENT_ACCEPTANCE
```

Independent Review inspects the exact artifact/delta/head and relevant CI and does not inherit the Writer session when independence matters.

If exact GitHub artifacts are sufficient, an ordinary independent GPT review window may perform the review directly through the connector. If mandatory local execution or local artifact inspection is required, capability-match the Reviewer environment rather than weakening the gate.

---

## 11. Current Issue #112 coordination

Issue #112's technical acceptance matrix remains unchanged.

Its current task-level L2 selection remains the current Issue snapshot until the user changes it:

```text
EXECUTOR=TRAE
MODEL=GLM-5.3
```

This changes no production semantics, accepted baseline, scope, test authenticity requirement, repair budget, publication gate or runtime authority.

The integrity-bound Issue #112 artifact remains rooted at its accepted repair baseline; governance-only `main` movement does not authorize rebase/reset/normalization of that artifact.

---

## 12. Tooling backlog

Issue #115 tracks:

- two future DSH real-task validations;
- Codex setup/profile work;
- Hermes installation/configuration.

The user has now reprioritized Codex setup/profile work. The current-main Codex governance route is this file plus:

- `governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`;
- `governance/CODEX_CURRENT_MODEL_PROFILE.md`.

Draft PR #111 remains stale proposal/history input and must not compete with the reconciled current-main route.

DeepSeek remaining checks continue to be collected during a future real DSH task rather than a synthetic paid stage.

---

## 13. Frozen decision

```text
DECISION=PROCEED
EXECUTION_CLASS_ROUTING_ORDER=GPT_CONTROL_DIRECT→GPT_CONTROL_DETERMINISTIC_TERMINAL→L2_CODING_EXECUTOR
ORDINARY_GPT_CONTROL_WINDOW_IS_FOURTH_L2_EXECUTOR=NO
CODING_AGENT_REQUIRED_FOR_GITHUB_ONLY_PUBLICATION=NO
CODING_AGENT_REQUIRED_FOR_DETERMINISTIC_COMMIT_PUSH_OF_ACCEPTED_ARTIFACT=NO
USER_CONTROLS_TASK_LEVEL_L2_EXECUTOR_MODEL_SELECTION=YES
APPROVED_PEER_L2_EXECUTORS=CODEX_CLI|TRAE|DEEPSEEK_HARNESS
GLOBAL_FIXED_PRIMARY_WRITER=NO
ENGINEERING_AUTO_LOADS_SELECTED_TOOL_PROFILE=YES
MODEL_PROFILE_SEPARATE_FROM_SWITCHING_ARCHITECTURE=YES
GLM_MODEL_UPGRADE_DEFAULT_CHANGE_SCOPE=TRAE_GLM_CURRENT_MODEL_PROFILE.md_ONLY
CODEX_MODEL_UPGRADE_DEFAULT_CHANGE_SCOPE=CODEX_CURRENT_MODEL_PROFILE.md_ONLY
ONE_PRIMARY_WRITER_PER_COHERENT_STAGE=YES
SILENT_EXECUTOR_OR_MODEL_SUBSTITUTION=NO
STALE_TOOLING_PRIORITY_SNAPSHOT_BINDS_NEW_TASK=NO
INDEPENDENT_REVIEW_REQUIRED=YES
USER_RETAINED_GATES_UNCHANGED=YES
```