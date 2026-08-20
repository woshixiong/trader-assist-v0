# Trader Assist / Trade OS — Trae + GLM Current Model Profile

**Status:** REFRESHABLE MODEL-SPECIFIC GOVERNANCE PROPOSAL  
**Repository:** `woshixiong/trader-assist-v0`  
**Executor:** `TRAE` / `TRAE_COMPUTER_USE`  
**Model family:** GLM  
**Current model label:** `GLM-5.3`  
**Last verified:** 2026-08-20  
**Update policy:** replace this file in place when the user selects a newer GLM model; do not change executor-routing or the version-independent Trae+GLM core unless new evidence requires a real workflow change.

This file contains only the **current model snapshot/delta**. The durable Trae+GLM workflow is `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`. The task-level executor/model switching architecture is `governance/ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING_V1_2026-08-20.md`.

It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission, cancellation or trading authority.

---

## 1. Current model identity and evidence status

```text
CURRENT_USER_SELECTED_MODEL=GLM-5.3
CURRENT_TRAE_VISIBLE_MODEL_LABEL=GLM-5.3
MODEL_LABEL_SOURCE=USER-CONFIRMED_CURRENT_TRAE_SURFACE
MODEL_PROFILE_LAST_VERIFIED_AT=2026-08-20
```

A fresh first-party public-source check on 2026-08-20 found:

- Z.AI release notes record `GLM-5.2` as released on 2026-06-16, and the current first-party GLM-5.2 page identifies it as a flagship foundation model;
- the public Z.AI Chat Completion model enumeration exposes `glm-5.2`, `glm-5.1`, `glm-5-turbo`, `glm-5` and older models, but not `glm-5.3`;
- no first-party public Z.AI model page for `GLM-5.3` was found;
- no first-party public Trae changelog/model page for `GLM-5.3` was found in the checked current public material.

Therefore:

```text
PUBLIC_ZAI_CURRENT_PUBLIC_FLAGSHIP_BASELINE=GLM-5.2
PUBLIC_ZAI_GLM_5_2_RELEASE_DATE=2026-06-16
GLM_5_2_PUBLIC_API_MODEL_ID=glm-5.2
GLM_5_3_PUBLIC_FIRST_PARTY_MODEL_SPEC=NOT_FOUND
GLM_5_3_PUBLIC_API_MODEL_ID=NOT_VERIFIED
GLM_5_3_CONTEXT_LIMIT=NOT_VERIFIED
GLM_5_3_MAX_OUTPUT=NOT_VERIFIED
GLM_5_3_PRICING=NOT_VERIFIED
GLM_5_3_REASONING_FLAGS=NOT_VERIFIED
GLM_5_3_PRESERVED_THINKING_IN_TRAE=NOT_VERIFIED
GLM_5_3_CACHE_TELEMETRY_IN_TRAE=NOT_VERIFIED
GLM_5_3_MAX_MODE_COMPATIBILITY=NOT_VERIFIED
MODEL_SPECIFIC_ASSUMPTIONS=NONE_UNLESS_CURRENT_SURFACE_OR_FIRST_PARTY_SOURCE_PROVES_THEM
```

`GLM-5.3` is accepted here as the user's current **Trae-visible model label**, not as a claim that the public Z.AI API exposes an identically named model.

---

## 2. Best-use rule for the current GLM-5.3 Trae surface

Because no first-party public GLM-5.3 specification was found, the safest high-value profile is:

```text
CURRENT_GLM_5_3_BEST_USE=
    VERSION-INDEPENDENT_TRAE_GLM_CORE
    + CURRENT_TRAE_VISIBLE_CONTROLS_ONLY
    + NO_UNDOCUMENTED_MODEL-SPECIFIC_TUNING
```

For current work:

1. Use one **coherent bounded engineering stage** per Writer session rather than one-file microtasks or unrelated long-running task mixtures.
2. Give one complete high-constraint Task Packet with explicit **Goal / Context / Constraints / Done when**, exact worktree/artifact identity, write allowlist, prohibited scope, attack cases, exact validation commands and SAFE_STOP conditions.
3. For complex implementation, let the Writer form a short local execution plan before mutation; do not ask it to redo L1 architecture/research already frozen by Engineering Control.
4. Prefer exact file/function/artifact context before `#Folder` and `#Workspace`; use broad workspace retrieval only when the bounded problem genuinely requires discovery.
5. Keep long-lived project rules in repository authority (`AGENTS.md` and specialized governance); do not repaste full governance/history into every GLM prompt and do not create a second giant Trae constitution.
6. Use deterministic shell/Git/test commands for hashes, diffs, tests and identity evidence before spending model reasoning tokens on those facts.
7. Keep a stable control prefix and place SHA/branch/log/CI/timestamp facts in the mutable tail to improve repeated-context cacheability where the provider path supports it.
8. Reuse a Trae/GLM session only while Writer role, coherent stage, worktree/artifact, authority and objective remain the same and independence is not required. Start a new session for materially new stages, publication authority changes, unrelated exploration, security/authority review or independent acceptance.
9. Do not assume hidden thinking, context-window, cache, API or pricing semantics from public `GLM-5`, `GLM-5.1` or `GLM-5.2` documentation apply identically to the Trae-visible `GLM-5.3` label.
10. Record model/token/cache/time evidence only where Trae/provider naturally exposes it; do not create synthetic paid calls solely to prove a cache ratio.

---

## 3. Trae mode selection for GLM-5.3

Trae first-party guidance describes regular modes as sufficient for ordinary day-to-day coding and Max Mode as a higher-token/higher-tool-call option for genuinely complex long-context work. Current Trae releases also expose worktree, nested `AGENTS.md` rules, context controls and sandbox-related capabilities.

For this project:

```text
REGULAR_MODE=DEFAULT_WHEN_SUFFICIENT
MAX_MODE=NOT_A_DEFAULT
MAX_MODE_MAY_BE_SELECTED_ONLY_IF=
    CURRENT_TRAE_SURFACE_SHOWS_IT_FOR_GLM-5.3
    AND THE_BOUNDED_TASK_NEEDS_THE_EXTRA_CONTEXT_OR_TOOL_CALL_BUDGET
MAX_MODE_AVAILABILITY_FOR_GLM-5.3=VERIFY_IN_CURRENT_SURFACE_BEFORE_USE
AUTO_ACCEPT_OR_BROAD_PERMISSION_ESCALATION=NOT_IMPLIED_BY_MODEL_CHOICE
```

Do not select Max Mode merely because it exists or because the task is material. Use it only when the current bounded stage would otherwise be constrained by context/tool-call limits and the current UI actually exposes it for the selected model.

---

## 4. Thinking / reasoning semantics

Z.AI publicly documents thinking, interleaved thinking and preserved thinking for supported GLM Coding Plan/API models. It also states that preserved thinking can improve coding continuity and cache reuse on supported surfaces.

That does **not** prove the user's Trae-visible `GLM-5.3` surface exposes the same controls.

Current rule:

```text
USE_ONLY_VERIFIED_TRAE_VISIBLE_REASONING_CONTROL=YES
TASK_PACKET_PROSE_CANNOT_INVENT_A_HIDDEN_REASONING_FLAG=YES
PRESERVED_THINKING_ASSUMED_FOR_TRAE_GLM_5_3=NO
INTERLEAVED_THINKING_ASSUMED_FOR_TRAE_GLM_5_3=NO
```

If a later Trae release visibly exposes a reasoning/deep-thinking control for `GLM-5.3`, Engineering may freeze that visible control per task after verifying its semantics. Until then, rely on task structure and context discipline rather than undocumented tuning.

---

## 5. Token/cache rule

Z.AI publicly documents automatic context caching for supported API models and reports cached tokens on supported API responses. Trae also exposes token-based usage in some modes such as Max Mode.

For the current Trae-visible `GLM-5.3` route, do not assume provider/API cache counters are exposed unless observed in the current UI/session.

```text
STABLE_PREFIX=YES
MUTABLE_TASK_TAIL=YES
REPEAT_FULL_HISTORY=NO
REPEAT_FULL_GOVERNANCE=NO
CACHE_IS_OPTIMIZATION_NOT_CORRECTNESS_AUTHORITY=YES
SYNTHETIC_CACHE_BENCHMARK=NO
ARBITRARY_CACHE_HIT_THRESHOLD=NO
```

If naturally visible, retain:

```text
MODEL_LABEL
SESSION/STAGE_IDENTITY
INPUT/OUTPUT_TOKENS
CACHE_READ/HIT/MISS_OR_RATIO
ELAPSED_TIME
MODEL_RETRY_COUNT
ENGINEERING_REPAIR_REWORK_COUNT
```

The success metric is accepted useful engineering work per total token/rework/review/human-relay cost, not the highest cache percentage.

---

## 6. Current evidence base

First-party sources rechecked 2026-08-20:

### Z.AI

- `https://docs.z.ai/release-notes/new-released`
- `https://docs.z.ai/guides/llm/glm-5.2`
- `https://docs.z.ai/guides/llm/glm-5.1`
- `https://docs.z.ai/api-reference/llm/chat-completion`
- `https://docs.z.ai/devpack/resources/best-practice`
- `https://docs.z.ai/devpack/resources/memory-mechanism`
- `https://docs.z.ai/guides/capabilities/cache`
- `https://docs.z.ai/guides/capabilities/thinking-mode`

### Trae

- `https://www.trae.ai/changelog`
- `https://www.trae.ai/blog/trae_tutorial_0825?v=1`
- `https://www.trae.ai/blog/product_thought_0609?v=1`
- `https://www.trae.ai/blog/trae_update_0902?v=1`

The model snapshot must always distinguish **provider/model-family evidence** from **controls actually exposed by the user's current Trae model surface**.

---

## 7. Refresh procedure when the user changes GLM model

When the user selects a newer GLM version, update **this file only by default**.

```text
USER_SELECTS_NEW_GLM_MODEL
→ VERIFY_EXACT_TRAE_VISIBLE_MODEL_LABEL
→ CHECK_CURRENT_FIRST_PARTY_ZAI_RELEASE/MODEL/API_DOCS
→ CHECK_CURRENT_TRAE_CHANGELOG/RULES/CONTEXT/MODE_SURFACE
→ RECORD_VERIFIED_MODEL_SPECIFIC_CONTROLS_AND_LIMITS
→ COMPARE_WITH_RECENT_REAL_PROJECT_EVIDENCE
→ REPLACE_THIS_CURRENT_MODEL_PROFILE_IN_PLACE
→ KEEP_EXECUTOR_ROUTING_UNCHANGED
→ KEEP_VERSION_INDEPENDENT_TRAE_GLM_CORE_UNCHANGED
```

Escalate to a change in the version-independent family profile or executor-routing governance **only** if the new model/tool version actually changes durable workflow semantics, such as session identity, context/rules loading, permission model, tool execution, worktree support, or acceptance/authority boundaries.

A new model name by itself is not sufficient reason to alter the three-tool switching architecture.

---

## 8. Frozen current snapshot

```text
EXECUTOR=TRAE
MODEL_FAMILY=GLM
CURRENT_MODEL_LABEL=GLM-5.3
CURRENT_MODEL_LABEL_AUTHORITY=USER-CONFIRMED_TRAE_SURFACE
PUBLIC_FIRST_PARTY_GLM_5_3_SPEC=NOT_FOUND_AS_OF_2026-08-20
PUBLIC_ZAI_LATEST_FLAGSHIP_FOUND=GLM-5.2
PUBLIC_ZAI_GLM_5_2_RELEASE_DATE=2026-06-16
MODEL_SPECIFIC_HIDDEN_TUNING=PROHIBITED
VERSION_INDEPENDENT_CORE=TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md
CURRENT_MODEL_PROFILE_UPDATE_PATH=THIS_FILE_ONLY_BY_DEFAULT
EXECUTOR_ROUTING_CHANGE_ON_MODEL_UPGRADE=NO_BY_DEFAULT
```