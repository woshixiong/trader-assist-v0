# Trader Assist / Trade OS — Trae + GLM Engineering Usage Profile V1

**Status:** SPECIALIZED GOVERNANCE PROPOSAL  
**Effective date:** 2026-08-20  
**Repository:** `woshixiong/trader-assist-v0`  
**Executor:** `TRAE` / `TRAE_COMPUTER_USE`  
**Model family:** GLM, with the exact current model selected per task by the user/L1.

This profile defines the project-specific way to use Trae + GLM for bounded engineering work with high execution reliability and low avoidable token/context cost. It complements the canonical Unified Engineering Governance and the task-level executor-routing rule. It does not create a new executor authority and grants no Mark Ready, merge, deployment, runtime/cloud, credential/private-API, signing/wallet, exchange-write, order-submission, cancellation or trading authority.

---

## 1. Versioning principle — do not hard-code one GLM generation

The durable profile is split into two layers:

```text
LAYER A — VERSION-INDEPENDENT GLM/TRAE WORKFLOW
stable task sizing, prompt structure, context discipline, session rules,
validation, authority boundaries and token-efficiency principles

LAYER B — CURRENT MODEL SNAPSHOT
exact GLM model visible/selected in the user's current Trae surface,
verified model-specific controls/capabilities/limits only
```

The user normally prefers the newest useful GLM model. Therefore no model name such as `GLM-5.3` becomes permanent architecture.

For each new material Trae/GLM stage, Engineering must freeze:

```text
CURRENT_USER_SELECTED_MODEL=
CURRENT_TRAE_VISIBLE_MODEL_LABEL=
MODEL_PROFILE_LAST_VERIFIED_AT=
MODEL_SPECIFIC_CONTROLS_VERIFIED=
MODEL_SPECIFIC_ASSUMPTIONS=NONE_UNLESS_VERIFIED
```

If a newer model is selected later, keep Layer A unless evidence shows a workflow change is needed, and refresh only the model-specific snapshot/overrides. Do not duplicate the entire profile for every model revision.

The user's current Trae surface reports `GLM-5.3` as the model in active use. At the time of this research, first-party public Z.AI documentation indexed publicly did not expose a `GLM-5.3` model page; the newest detailed public flagship documentation found was for the GLM-5/5.1 generation. Therefore this profile accepts `GLM-5.3` as the user's current **Trae-visible model selection**, but does not invent undocumented GLM-5.3 API parameters, reasoning flags, context limits, pricing or cache semantics.

---

## 2. Independent position before external research

Current project execution evidence suggests GLM is more reliable when Engineering Control removes unnecessary degrees of freedom before dispatch: one coherent bounded task, exact worktree, explicit allowlist, exact tests, negative cases, `DO NOT INFER`, and fail-closed stop conditions.

The main risks are:

1. an underspecified prompt that lets the model invent route, scope, authority or acceptance semantics; and
2. an oversized, repetitive always-loaded context that wastes tokens and makes important constraints harder to follow.

The preliminary route is:

```text
SMALL STABLE GLOBAL RULE SURFACE
+ ONE TOOL-SPECIFIC PROFILE
+ ONE COMPLETE HIGH-CONSTRAINT TASK PACKET
+ EXACT TASK-RELEVANT FILE/ARTIFACT CONTEXT
+ ONE COHERENT SESSION/STAGE
+ DETERMINISTIC COMMANDS FOR MECHANICAL PROOF
+ NEW SESSION AT MATERIAL OR INDEPENDENCE BOUNDARIES
```

Optimize for **accepted useful work per total token/rework/review/human-relay cost**, not minimum prompt characters.

---

## 3. External first-party evidence

External research was performed after the independent pass.

### 3.1 Z.AI coding-agent guidance

First-party sources checked:

- `https://docs.z.ai/devpack/resources/best-practice`
- `https://docs.z.ai/devpack/resources/memory-mechanism`
- `https://docs.z.ai/guides/capabilities/cache`
- `https://docs.z.ai/guides/capabilities/thinking-mode`
- `https://docs.z.ai/guides/llm/glm-5`
- `https://docs.z.ai/guides/llm/glm-5.1`

Relevant first-party guidance:

- coding-agent task input should make **Goal / Context / Constraints / Done when** explicit;
- complex tasks benefit from planning before mutation;
- repeated long-lived rules belong in project-level configuration instead of every prompt;
- repeated workflows are candidates for reusable skills/workflows;
- unrelated tasks should not accumulate in one long session;
- instruction memory should be separated from temporary/session learning;
- large always-loaded memory increases context pressure and rule conflict risk;
- automatic context caching can reuse repeated prompt/history and reports cached token usage where the provider surface exposes it;
- preserved thinking is designed for coding/agent continuity and can increase cache reuse on supported Coding Plan/API surfaces.

The GLM-5/5.1 public documentation also describes the generation as optimized for long-horizon agentic engineering, complex backend work, debugging and sustained tool-driven execution. This supports allowing one **coherent bounded stage**, rather than mechanically forcing every GLM assignment into tiny single-file prompts.

### 3.2 Trae first-party guidance

First-party sources checked:

- `https://www.trae.ai/blog/trae_tutorial_0825?v=1`
- `https://www.trae.ai/blog/product_thought_0609`
- `https://www.trae.ai/changelog`

Relevant Trae guidance:

- persistent `user_rules.md` / `project_rules.md` reduce repeated prompt input;
- Trae recommends English custom rules in most cases;
- Rules have a 20,000-byte maximum and conflicting/unclear rules reduce adherence;
- rule priority is `user input > Custom Agent prompt > user_rules.md > project_rules.md`;
- complete project-relative file paths reduce context mistakes;
- if chat history conflicts with Rules, starting a new conversation is the recommended recovery;
- `#Code`, `#File`, `#Folder`, `#Workspace`, Docs and Ignore Files deliberately shape context;
- Ignore Files can reduce irrelevant indexing and secret exposure;
- current Trae releases support nested Rules including `AGENTS.md`;
- Trae also supports isolated Worktree-based task execution, which aligns with this project's existing isolated-worktree boundary.

---

## 4. Synthesis

External evidence confirms the project's high-constraint direction but changes the optimal task granularity and context strategy.

### Confirmed

- explicit goal/context/constraints/completion criteria improve reliability;
- persistent rules should be stable and modular instead of repeatedly pasted;
- large monolithic always-on memory/rules are poor context engineering;
- exact scoped context is preferable to indiscriminate workspace loading;
- one coherent task/session is preferable to mixing unrelated work;
- stable repeated prompt structure is favorable for caching where supported.

### Modified

"Make every GLM task very small" is too crude. Over-splitting creates repeated bootstrap context, extra human relay, extra token cost and more review boundaries. The correct unit is **one coherent bounded engineering stage**, not one file or one command.

A separate giant Trae project-rules corpus should not duplicate repository governance merely because Trae supports Rules. This repository already uses `AGENTS.md` plus GitHub-resident specialized authority. Duplicating the full corpus would create drift and unnecessary always-loaded context.

Session reuse is useful only while role/stage/worktree/artifact/authority remain coherent. Publication, independent review, unrelated exploration or degraded/conflicting history should use a new session.

### Rejected

- giant always-loaded `project_rules.md` containing the full Trader Assist governance;
- vague short prompts that ask GLM to infer scope;
- repeatedly pasting full chat/project history;
- forcing the Writer to re-research architecture already frozen by L1;
- broad `#Workspace` context by default when exact files/artifacts are known;
- inventing version-specific GLM controls that are not verified in the current Trae/model surface.

---

## 5. Frozen GLM/Trae packet architecture

For material coding work, the canonical high-constraint packet remains mandatory.

Use this semantic order:

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
   exact objective
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

Prompt brevity never justifies removing allowlists, negative cases, exact tests, stop conditions, exact identities or authority gates.

For the current Trae direct-paste workflow, preserve the canonical 20,000-character ceiling unless a later verified UI limit supersedes it. If the complete packet would exceed that ceiling, use the project's lossless Terminal/file/task-packet transport rather than truncating or making the user assemble fragments.

---

## 6. Correct task size

Default:

```text
ONE_GLM_SESSION = ONE_COHERENT_BOUNDED_ENGINEERING_STAGE
```

Good examples:

- one bounded implementation plus its in-scope tests/local validation;
- one exact evidence-packet freeze from an already-finished artifact;
- one narrow accepted-blocker repair;
- one separately authorized publication stage: accepted exact artifact → commit → push → Draft PR → exact-head CI observation.

Bad over-splitting:

- one prompt per changed file;
- one prompt per lint/test command;
- separate prompts for commit, push and Draft PR when those belong to one currently authorized publication stage;
- making the user relay routine Writer/CI messages that the coherent stage can carry itself.

Bad over-expansion:

- implementation + unrelated refactor + future optimization + publication + deployment in one stage;
- current repair plus architecture redesign that L1 did not freeze;
- Writer performing its own independent acceptance.

---

## 7. Session reuse and reset

Reuse the current Trae/GLM session only when all are true:

```text
SAME_PRIMARY_WRITER=YES
SAME_COHERENT_STAGE=YES
SAME_WORKTREE_ARTIFACT=YES
SAME_AUTHORITY=YES
CONTEXT_REMAINS_TRUSTWORTHY=YES
INDEPENDENCE_REQUIRED=NO
```

Start a **new** Trae/GLM session when any is true:

- task or material stage changes;
- mutation authority changes materially, such as evidence-only → commit/push/PR publication;
- worktree/branch/artifact changes;
- independent review is required;
- security/authority adjudication is required;
- current session has accumulated unrelated history;
- model behavior shows instruction loss, repeated drift, contradictory context or stale assumptions.

For the current Issue #112 flow, reusing the Stage-C GLM session for a read-only D0A evidence freeze is reasonable; a later D1 publication stage should use a new complete session/packet because stage and authority change.

---

## 8. Planning rule — L1 plans architecture; GLM plans local execution only

For material route/architecture decisions, L1 Engineering Control performs the mandatory independent analysis → external research → synthesis → preflight before Writer dispatch.

GLM must not repeat the architecture study or invent a competing route after receiving a frozen packet.

Before mutation on a complex task, GLM may produce a short local execution plan only to verify its understanding, for example:

```text
1. verify identities and allowed paths
2. inspect exact affected code
3. implement the frozen change
4. run focused tests
5. run required regressions/static gates
6. inspect diff/scope
7. return the Result Packet
```

For a purely mechanical task with exact commands, do not spend a separate model turn generating an obvious plan; execute the frozen sequence directly.

If local inspection exposes a new material decision, missing requirement, allowlist expansion or authority conflict: `SAFE_STOP`. Do not solve it by creative inference.

---

## 9. Static Trae rules — small, stable and non-duplicative

Do **not** copy the full Trader Assist governance corpus into Trae `user_rules.md` or `project_rules.md`.

Repository authority remains:

```text
AGENTS.md
→ PROJECT_RULES_INDEX.md
→ canonical/specialized governance files
→ task-specific authority
```

Trae's Rules/`AGENTS.md` support should be a routing surface, not a second governance database.

Current default:

```text
NEW_GIANT_TRAE_PROJECT_RULES_FILE=NO
DUPLICATE_FULL_GOVERNANCE_IN_TRAE=NO
ROOT_AGENTS_REMAINS_SMALL_STABLE_POINTER=YES
DETAILS_LIVE_IN_SPECIALIZED_GITHUB_FILES=YES
```

If real GLM tasks later prove that Trae does not reliably surface the repository's `AGENTS.md`/specialized pointer path, Engineering may propose a **small pointer-only Trae rule** as a measured repair. Do not add one speculatively merely because the feature exists.

If such a Trae custom Rule is later justified, use English, concrete verifiable statements, exact project-relative paths, minimal overlap with other rule layers, and keep it comfortably below Trae's 20,000-byte maximum.

---

## 10. Context-selection discipline

Prefer exact task context over broad retrieval:

```text
EXACT FILE / FUNCTION / ARTIFACT
→ SMALL RELATED DIRECTORY
→ TASK-SPECIFIC DOC/ISSUE
→ BROADER WORKSPACE SEARCH ONLY WHEN NECESSARY
```

Engineering prompts should give exact project-relative or absolute worktree paths where possible.

Do not use broad `#Workspace`/whole-repo context merely to make the model "understand everything" when the task concerns a known bounded delta.

Where Trae Ignore Files configuration is available, exclude irrelevant high-volume or sensitive material from indexing when it is not needed, such as third-party dependency trees, virtual environments, caches, generated binaries and secret-bearing paths. Do not ignore canonical source/tests/evidence required by the task.

---

## 11. Token and cache efficiency

The target is not "shortest prompt". The target is:

```text
TOTAL_COST = INPUT + OUTPUT + RETRIES + REWORK + REVIEW + HUMAN_RELAY
```

### Stable prefix

Keep stable control sections, labels and ordering identical where practical. Avoid cosmetic rewrites of the same long control prefix from task to task.

Z.AI documents automatic context caching for repeated prompt/history and exposes cached token usage on supported API surfaces. Stable repeated context is therefore cache-friendly where Trae's provider path uses/exposes the same mechanism. Treat cache reuse as an optimization, never as a correctness dependency.

### Mutable tail

Put branch/SHA/hash/current log/CI/timestamp facts late in the packet so durable content remains stable.

### No repeated full history

Do not paste old chats, stale PR bodies, previously accepted thousands of lines or full governance bodies when exact canonical paths/identities suffice.

After independent acceptance use:

```text
ACCEPTED BASELINE
+ EXACT NEW DELTA
+ TARGETED REGRESSION / BYPASS CHECKS
```

### Deterministic mechanics before model tokens

Use shell/Git/test commands for hashes, exact file lists, diff stats, branch/head identity, tests/lint/compile and raw evidence packaging. Do not ask GLM to reason about a value a deterministic command can prove exactly.

### Do not manufacture token tests

If Trae/provider exposes usage/cache metrics naturally, record them. If not, do not add synthetic paid requests or custom instrumentation solely to prove a cache percentage.

Useful evidence where observable:

```text
MODEL
SESSION/STAGE IDENTITY
INPUT / OUTPUT TOKENS
CACHE READ/HIT/MISS TOKENS OR RATIO
ELAPSED TIME
MODEL RETRY COUNT
ENGINEERING REPAIR/REWORK COUNT
```

The decisive metric is whether the profile reduces total rework/context cost while preserving accepted output quality.

---

## 12. Thinking/reasoning controls

Z.AI documents thinking, interleaved thinking and preserved thinking on supported GLM Coding Plan/API surfaces. Preserved thinking is specifically intended to help coding/agent continuity and cache behavior.

However, provider capability must be separated from controls actually exposed by the user's current Trae model surface.

Therefore:

```text
USE_VERIFIED_TRAE_VISIBLE_REASONING_CONTROL_ONLY=YES
INVENT_HIDDEN_MODEL_REASONING_FLAG=NO
```

If the current Trae UI exposes a verified reasoning/deep-thinking/Max-style control for the selected model, L1 may freeze it per task based on complexity. If it does not, do not pretend the Task Packet can control it by prose or undocumented settings.

Do not freeze a permanent GLM reasoning-tier table across model generations. Refresh model-specific guidance when the selected model changes.

---

## 13. Validation and self-check

Within the authorized coherent stage, the GLM Writer should complete its own mechanical validation before stopping:

```text
IMPLEMENT
→ FOCUSED TESTS
→ REQUIRED REGRESSION
→ LINT / TYPE / COMPILE WHERE APPLICABLE
→ DIFF / SCOPE / SECRET CHECK
→ EXACT RESULT PACKET
```

Do not confuse Writer self-check with independent acceptance.

For evidence-only/read-only stages, production mutation is prohibited. If GLM discovers a production defect outside the frozen scope, it must report it and `SAFE_STOP`; discovery does not grant repair authority.

---

## 14. Model-profile refresh trigger

This profile must be revisited narrowly when any occurs:

```text
USER_SELECTS_NEW_GLM_MODEL=YES
TRAE_MODEL_SURFACE_CHANGES_MATERIALLY=YES
TRAE_RULES/CONTEXT/WORKTREE_BEHAVIOR_CHANGES_MATERIALLY=YES
FIRST_PARTY_ZAI_MODEL_GUIDANCE_CHANGES_MATERIALLY=YES
REAL_PROJECT_EVIDENCE_SHOWS_CURRENT_RULE_IS_INEFFICIENT_OR_UNRELIABLE=YES
```

Refresh process:

```text
KEEP VERSION-INDEPENDENT CORE BY DEFAULT
→ VERIFY CURRENT TRAE MODEL LABEL/SURFACE
→ CHECK CURRENT FIRST-PARTY Z.AI + TRAE DOCUMENTATION
→ COMPARE WITH REAL PROJECT EVIDENCE
→ UPDATE ONLY THE MODEL-SPECIFIC OR TOOL-SPECIFIC DELTA
→ INDEPENDENT REVIEW BEFORE MERGE IF GOVERNANCE CHANGES
```

Do not create `GLM-5.3_RULES`, `GLM-5.4_RULES`, `GLM-6_RULES` as separate full constitutions unless a future model genuinely requires incompatible workflow semantics.

---

## 15. Frozen concise profile

```text
EXECUTOR=TRAE
MODEL=USER/L1_SELECTED_CURRENT_GLM_MODEL
CURRENT_USER_TRAE_MODEL_SNAPSHOT=GLM-5.3
MODEL_NAME_NOT_PERMANENT_ARCHITECTURE=YES
VERSION_INDEPENDENT_CORE_PLUS_REFRESHABLE_MODEL_DELTA=YES
MATERIAL_PACKET=HIGH_CONSTRAINT_COMPLETE
TASK_UNIT=ONE_COHERENT_BOUNDED_STAGE
SAME_SESSION_REUSE=SAME_ROLE_STAGE_WORKTREE_ARTIFACT_AUTHORITY_ONLY
NEW_SESSION_ON_MATERIAL_STAGE_OR_AUTHORITY_CHANGE=YES
NEW_SESSION_FOR_INDEPENDENT_REVIEW=YES
L1_ARCHITECTURE_RESEARCH_NOT_REPEATED_BY_WRITER=YES
ROOT_AGENTS_SMALL_STABLE_POINTER=YES
FULL_GOVERNANCE_DUPLICATED_IN_TRAE_RULES=NO
EXACT_CONTEXT_BEFORE_WORKSPACE_CONTEXT=YES
STABLE_PREFIX_MUTABLE_TAIL=YES
DETERMINISTIC_MECHANICS_BEFORE_MODEL_TOKENS=YES
SYNTHETIC_CACHE_BENCHMARK=NO
UNDOCUMENTED_MODEL_SPECIFIC_TUNING=NO
WRITER_PASS_NOT_INDEPENDENT_ACCEPTANCE=YES
```
