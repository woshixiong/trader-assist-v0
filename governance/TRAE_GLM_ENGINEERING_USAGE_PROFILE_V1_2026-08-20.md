# Trader Assist / Trade OS — Trae + GLM Engineering Usage Profile V1

**Status:** SPECIALIZED GOVERNANCE PROPOSAL  
**Effective date:** 2026-08-20  
**Repository:** `woshixiong/trader-assist-v0`  
**Executor:** `TRAE` / `TRAE_COMPUTER_USE`  
**Model family:** GLM, with the exact current model selected per task by the user/L1.

This file is the **version-independent Trae+GLM workflow core**. The current model-specific snapshot lives at the stable path:

`governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md`

When the user changes to a newer GLM model, update that current-model file only by default. Do not rewrite this family core or the three-executor switching architecture merely because the model name changed.

This profile complements the canonical Unified Engineering Governance and the task-level executor-routing rule. It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission, cancellation or trading authority.

---

## 1. Stable architecture — family core separate from current model

```text
LAYER A — EXECUTOR ROUTING
ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING...
stable three-peer-executor switching architecture

LAYER B — VERSION-INDEPENDENT TRAE+GLM CORE
THIS FILE
stable task sizing, prompt structure, context discipline, session rules,
validation, authority boundaries and token-efficiency principles

LAYER C — CURRENT GLM MODEL SNAPSHOT / DELTA
TRAE_GLM_CURRENT_MODEL_PROFILE.md
current Trae-visible model label plus only verified model-specific controls/limits
```

The exact GLM model is task-level state, not architecture.

Before a material Trae+GLM Writer stage, Engineering freezes:

```text
CURRENT_USER_SELECTED_EXECUTOR=TRAE
CURRENT_USER_SELECTED_MODEL=
CURRENT_TRAE_VISIBLE_MODEL_LABEL=
CURRENT_MODEL_PROFILE_PATH=governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md
MODEL_PROFILE_LAST_VERIFIED_AT=
MODEL_SPECIFIC_CONTROLS_VERIFIED=
MODEL_SPECIFIC_ASSUMPTIONS=NONE_UNLESS_VERIFIED
```

A new model version alone does not change executor switching, review independence, worktree rules, user-retained gates or the high-constraint Task Packet contract.

---

## 2. Independent position

The project needs GLM to be strong at real engineering without giving it unnecessary freedom to invent route, scope or authority. The two main risks are:

1. underspecification — the Writer guesses route, allowlist, acceptance or authority; and
2. context bloat — repeated governance/history consumes tokens and makes critical constraints less salient.

The durable solution is:

```text
SMALL STABLE GLOBAL RULE SURFACE
+ VERSION-INDEPENDENT TOOL PROFILE
+ REFRESHABLE CURRENT-MODEL SNAPSHOT
+ ONE COMPLETE HIGH-CONSTRAINT TASK PACKET
+ EXACT TASK-RELEVANT CONTEXT
+ ONE COHERENT BOUNDED SESSION/STAGE
+ DETERMINISTIC COMMANDS FOR MECHANICAL PROOF
+ NEW SESSION AT MATERIAL / AUTHORITY / INDEPENDENCE BOUNDARIES
```

Optimize for accepted useful work per total token/rework/review/human-relay cost, not minimum prompt length.

---

## 3. External first-party evidence

External research was performed after the independent pass.

### Z.AI

Checked:

- `https://docs.z.ai/devpack/resources/best-practice`
- `https://docs.z.ai/devpack/resources/memory-mechanism`
- `https://docs.z.ai/guides/capabilities/cache`
- `https://docs.z.ai/guides/capabilities/thinking-mode`
- `https://docs.z.ai/guides/llm/glm-5`
- `https://docs.z.ai/guides/llm/glm-5.1`
- `https://docs.z.ai/release-notes/new-released`
- `https://docs.z.ai/api-reference/llm/chat-completion`

Relevant first-party guidance supports:

- explicit **Goal / Context / Constraints / Done when** task structure;
- planning before execution for complex tasks;
- long-lived rules in stable project-level configuration rather than repeated prompts;
- layered instruction/project/session memory;
- modular/on-demand rules instead of one oversized always-loaded memory file;
- deliberate session management and separate sessions for unrelated tasks;
- full implementation → tests → checks → diff review development loops;
- automatic repeated-context caching on supported provider surfaces;
- thinking/interleaved thinking/preserved thinking on supported GLM Coding Plan/API surfaces.

### Trae

Checked:

- `https://www.trae.ai/blog/trae_tutorial_0825?v=1`
- `https://www.trae.ai/blog/product_thought_0609?v=1`
- `https://www.trae.ai/blog/trae_update_0902?v=1`
- `https://www.trae.ai/changelog`

Relevant first-party guidance supports:

- stable user/project Rules rather than repeated prompt boilerplate;
- explicit rule priority and avoidance of conflicting rules;
- exact `#Code` / `#File` / `#Folder` context before broad `#Workspace` when the scope is known;
- Ignore Files for irrelevant/high-volume/sensitive context;
- starting a fresh conversation when chat history conflicts with active rules;
- nested Rules including `AGENTS.md`;
- isolated Worktree support;
- regular modes for ordinary work and Max Mode for genuinely deeper/longer context/tool-call workflows, with higher token/usage cost;
- current sandbox/tool-execution controls that should be verified on the actual current surface before being relied on.

---

## 4. Synthesis

External evidence confirms the high-constraint/context-layering route but rejects two extremes.

### Reject over-splitting

"Make every GLM task tiny" is too crude. One file or one command per prompt can increase bootstrap context, token use, human relay and review fragmentation.

Default unit:

```text
ONE_GLM_WRITER_SESSION = ONE_COHERENT_BOUNDED_ENGINEERING_STAGE
```

A stage may include implementation plus its in-scope local validation when all authority/scope remains coherent.

### Reject oversized persistent context

Do not copy the full Trader Assist governance corpus into Trae Rules or every prompt. Repository authority already provides small stable routing plus specialized files.

### Preserve model-version replaceability

Model-specific context limits, reasoning controls, pricing, cache exposure and mode support must come from the current model snapshot/current tool surface, not from adjacent GLM generations.

---

## 5. High-constraint Task Packet architecture

For material coding work, use one complete packet in this semantic order:

```text
A. STABLE CONTROL PREFIX
   ROLE / MODE
   PROJECT
   EXECUTOR=TRAE
   MODEL=<user-selected current GLM model>
   canonical GitHub authority pointers
   Writer != Reviewer
   DO NOT INFER / REDESIGN / EXPAND SCOPE
   retained user authority boundary
   output/evidence contract shape

B. CURRENT TASK CONTRACT
   TASK_ID
   exact repository/worktree/branch
   live main/base/head/artifact identities
   exact Goal
   exact Context
   exact Constraints
   exact Done-when / acceptance
   accepted baseline/root cause
   what must NOT be reopened
   write allowlist
   prohibited files/systems/actions
   must-preserve semantics/authorities
   attack/negative cases
   exact validation commands
   SAFE_STOP conditions
   repair stage/budget

C. MUTABLE EVIDENCE TAIL
   current hashes
   current CI/run IDs
   one-off log/artifact paths
   timestamps/current blocker IDs
```

Keep stable headings/order/text identical where practical. Put volatile facts late.

Prompt brevity never justifies removing scope, allowlists, negative cases, exact tests, stop conditions, exact identities or authority gates.

For current Trae direct paste, preserve the canonical 20,000-character ceiling unless a later verified interface limit supersedes it. Above that boundary, use the lossless Terminal/file/task-packet route. Never truncate or ask the user to reconstruct critical fragments.

---

## 6. Correct task size

Good coherent stages include:

- one bounded implementation plus in-scope tests/local validation;
- one exact evidence-packet freeze from a finished artifact;
- one narrow accepted-blocker repair;
- one separately authorized publication stage: accepted exact artifact → commit → push → Draft PR → exact-head CI observation.

Bad over-splitting includes:

- one prompt per changed file;
- one prompt per lint/test command;
- separate prompts for commit, push and Draft PR when one publication stage already authorizes them;
- using the user as the routine Writer/CI message bus.

Bad over-expansion includes:

- implementation + unrelated refactor + future optimization + publication + deployment;
- current repair plus architecture redesign not frozen by L1;
- Writer self-declaring independent acceptance.

---

## 7. Session reuse and reset

Reuse the current Trae+GLM Writer session only when all are true:

```text
SAME_PRIMARY_WRITER=YES
SAME_COHERENT_STAGE=YES
SAME_WORKTREE_ARTIFACT=YES
SAME_AUTHORITY=YES
SAME_OBJECTIVE=YES
CONTEXT_REMAINS_TRUSTWORTHY=YES
INDEPENDENCE_REQUIRED=NO
```

Start a new session when any is true:

- task or material stage changes;
- authority changes materially, such as evidence-only → publication;
- worktree/branch/artifact changes;
- independent review or security/authority adjudication is required;
- unrelated history has accumulated;
- current history conflicts with active Rules;
- repeated drift/instruction loss/stale assumptions appear.

Do not reuse a session merely because the same model or Terminal window remains open.

---

## 8. Planning rule

L1 Engineering Control owns architecture/research/route decisions. GLM owns only bounded local execution planning inside the frozen route.

For a complex implementation, a short pre-mutation plan is appropriate:

```text
1. verify identities and allowlist
2. inspect exact affected code
3. implement frozen change
4. run focused tests
5. run required regressions/static gates
6. inspect diff/scope
7. return Result Packet
```

For purely mechanical exact-command work, do not spend a separate model turn restating an obvious plan.

If inspection exposes a new material decision, missing requirement, allowlist expansion or authority conflict: `SAFE_STOP`.

---

## 9. Static Trae rules — small and non-duplicative

Repository authority remains:

```text
AGENTS.md
→ PROJECT_RULES_INDEX.md
→ executor-routing governance
→ THIS VERSION-INDEPENDENT TRAE+GLM CORE
→ TRAE_GLM_CURRENT_MODEL_PROFILE.md
→ current task-specific authority
```

Do not create a giant duplicate `user_rules.md` / `project_rules.md` containing the project governance corpus.

```text
NEW_GIANT_TRAE_PROJECT_RULES_FILE=NO
DUPLICATE_FULL_GOVERNANCE_IN_TRAE=NO
ROOT_AGENTS_REMAINS_SMALL_STABLE_POINTER=YES
DETAILS_LIVE_IN_SPECIALIZED_GITHUB_FILES=YES
```

If real tasks later prove Trae does not reliably surface the repository pointer path, a small pointer-only Rule may be proposed as a measured repair. If created, keep it concrete, consistent and well below Trae's current rule-size boundary.

---

## 10. Context-selection discipline

Prefer:

```text
EXACT FILE / FUNCTION / ARTIFACT
→ SMALL RELATED DIRECTORY
→ TASK-SPECIFIC DOC / ISSUE
→ BROADER WORKSPACE SEARCH ONLY WHEN DISCOVERY IS NECESSARY
```

Do not use `#Workspace` merely to make the model "understand everything" when the task is already bounded.

Where Trae Ignore Files is available, exclude irrelevant dependency trees, virtual environments, caches, generated binaries and secret-bearing paths from indexing when safe. Do not ignore canonical source/tests/evidence required by the task.

---

## 11. Token/cache efficiency

Target:

```text
TOTAL_COST = INPUT + OUTPUT + RETRIES + REWORK + REVIEW + HUMAN_RELAY
```

Rules:

- stable control prefix, mutable evidence tail;
- no repeated full project/chat history;
- no repeated full governance bodies when canonical paths suffice;
- after accepted baseline, use accepted fingerprint + exact delta + targeted regression/bypass checks;
- deterministic shell/Git/test proof before model tokens;
- no synthetic paid cache benchmark;
- no arbitrary cache-hit threshold.

If Trae/provider exposes metrics naturally, retain:

```text
MODEL
SESSION/STAGE IDENTITY
INPUT/OUTPUT TOKENS
CACHE READ/HIT/MISS OR RATIO
ELAPSED TIME
MODEL RETRY COUNT
ENGINEERING REPAIR/REWORK COUNT
```

Cache is an optimization, never correctness or authority.

---

## 12. Trae mode and reasoning controls

### Mode selection

```text
REGULAR_MODE=DEFAULT_WHEN_SUFFICIENT
MAX_MODE=CONDITIONAL_NOT_DEFAULT
```

Use Max Mode only when:

1. the current Trae surface actually exposes it for the user-selected model; and
2. the bounded task genuinely needs additional context/tool-call budget.

Do not select Max merely because the task is material or because the feature exists. It can consume more token-based usage.

### Reasoning/thinking controls

Z.AI provider capability is not identical to controls exposed inside Trae.

```text
USE_VERIFIED_TRAE_VISIBLE_REASONING_CONTROL_ONLY=YES
INVENT_HIDDEN_REASONING_FLAG=NO
INHERIT_ADJACENT_GLM_MODEL_LIMITS=NO
```

Any current-model-specific reasoning/cache/context behavior belongs in `TRAE_GLM_CURRENT_MODEL_PROFILE.md`.

---

## 13. Validation and Writer self-check

Within the authorized coherent stage:

```text
IMPLEMENT
→ FOCUSED TESTS
→ REQUIRED REGRESSION
→ LINT / TYPE / COMPILE WHERE APPLICABLE
→ DIFF / SCOPE / SECRET CHECK
→ EXACT RESULT PACKET
```

Writer self-check is not independent acceptance.

For read-only/evidence stages, production mutation remains prohibited. Discovery of an out-of-scope defect does not grant repair authority.

---

## 14. Model refresh contract

The default refresh target is the stable current-model file only:

```text
USER_SELECTS_NEW_GLM_MODEL
→ VERIFY_CURRENT_TRAE_VISIBLE_LABEL/SURFACE
→ CHECK_CURRENT_FIRST-PARTY_ZAI + TRAE DOCUMENTATION
→ VERIFY_ONLY_ACTUALLY_EXPOSED_CONTROLS/LIMITS
→ COMPARE_WITH_RECENT_REAL_PROJECT_EVIDENCE
→ UPDATE governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md
→ KEEP THIS FAMILY CORE UNCHANGED
→ KEEP EXECUTOR ROUTING UNCHANGED
```

Change this family core only if evidence shows a durable Trae+GLM workflow semantic changed, such as Rules/context loading, session semantics, permission/sandbox behavior, tool execution, worktree support or validation workflow.

Change the executor-routing architecture only if the approved executor pool or L1/L2 authority model itself changes.

A new model name by itself is not enough.

---

## 15. Frozen concise profile

```text
EXECUTOR=TRAE
MODEL=USER/L1_SELECTED_CURRENT_GLM_MODEL
CURRENT_MODEL_PROFILE=governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md
MODEL_NAME_NOT_PERMANENT_ARCHITECTURE=YES
MODEL_UPGRADE_DEFAULT_CHANGE_SCOPE=CURRENT_MODEL_PROFILE_ONLY
EXECUTOR_ROUTING_CHANGE_ON_MODEL_UPGRADE=NO_BY_DEFAULT
VERSION_INDEPENDENT_CORE=THIS_FILE
MATERIAL_PACKET=HIGH_CONSTRAINT_COMPLETE
TASK_UNIT=ONE_COHERENT_BOUNDED_STAGE
SAME_SESSION_REUSE=SAME_ROLE_STAGE_WORKTREE_ARTIFACT_AUTHORITY_OBJECTIVE_ONLY
NEW_SESSION_ON_MATERIAL_STAGE_OR_AUTHORITY_CHANGE=YES
NEW_SESSION_FOR_INDEPENDENT_REVIEW=YES
L1_ARCHITECTURE_RESEARCH_NOT_REPEATED_BY_WRITER=YES
ROOT_AGENTS_SMALL_STABLE_POINTER=YES
FULL_GOVERNANCE_DUPLICATED_IN_TRAE_RULES=NO
EXACT_CONTEXT_BEFORE_WORKSPACE_CONTEXT=YES
STABLE_PREFIX_MUTABLE_TAIL=YES
DETERMINISTIC_MECHANICS_BEFORE_MODEL_TOKENS=YES
REGULAR_MODE_DEFAULT_WHEN_SUFFICIENT=YES
MAX_MODE_CONDITIONAL=YES
SYNTHETIC_CACHE_BENCHMARK=NO
UNDOCUMENTED_MODEL_SPECIFIC_TUNING=NO
WRITER_PASS_NOT_INDEPENDENT_ACCEPTANCE=YES
```