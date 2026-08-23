# Trader Assist / Trade OS — Trae + GLM Current Model Profile

**Status:** REFRESHABLE MODEL-SPECIFIC GOVERNANCE CANDIDATE  
**Current user-selected Trae model:** `GLM-5.3`  
**Last verified:** 2026-08-23

The stable Trae+GLM workflow remains `governance/TRAE_GLM_ENGINEERING_USAGE_PROFILE_V1_2026-08-20.md`. Task/model selection is governed by `governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md` after acceptance.

## 1. Corrected current evidence

The previous snapshot incorrectly said a first-party public GLM-5.3 specification was not found. Z.AI officially announced GLM-5.3 on 2026-08-14 and published current coding/agentic benchmark and reasoning information.

First-party source:

- `https://z.ai/blog/glm-5.3`

The vendor-reported comparison includes strong long-horizon/agentic coding performance (for example Terminal Bench 2.1 and DeepSWE). Vendor benchmarks are useful evidence, not universal proof that GLM-5.3 dominates another model on Trader Assist tasks.

## 2. Current project best-use

GLM-5.3 is a **first-class advanced Writer**, not a low-cost chore model.

Known strong fit:

```text
HIGH-CONSTRAINT COMPLETE TASK PACKET
+ FROZEN SCOPE / INVARIANTS
+ ONE COHERENT BOUNDED IMPLEMENTATION STAGE
+ TERMINAL-HEAVY IMPLEMENT -> TEST -> REPAIR LOOP
```

This matches the user's real project experience: GLM quality improves materially when Engineering freezes detailed boundaries and acceptance, while excessive microtask splitting increases human relay and should be avoided.

## 3. Comparison policy

Do not encode a universal ordering among:

```text
GLM-5.3
Claude Opus 4.6
DeepSeek V4 Pro
```

Use Router V2 task fit plus current availability/quota state. Trae points are a secondary tie-breaker, not a reason to accept lower expected quality. The user retains manual override.

## 4. Trae controls

Use only controls actually exposed by the current Trae surface. Do not infer API-only or adjacent-model settings.

```text
ONE_COHERENT_STAGE=YES
HIGH_CONSTRAINT_PACKET=YES
EXACT_CONTEXT_BEFORE_WORKSPACE=YES
STABLE_PREFIX_MUTABLE_TAIL=YES
DETERMINISTIC_MECHANICS_BEFORE_REASONING_TOKENS=YES
REGULAR_MODE_DEFAULT_WHEN_SUFFICIENT=YES
MAX_MODE_ONLY_WHEN_EXPOSED_AND_NEEDED=YES
UNDOCUMENTED_HIDDEN_TUNING=NO
```

## 5. Refresh rule

When the user selects a newer GLM model:

```text
VERIFY EXACT TRAE-VISIBLE LABEL
-> CHECK CURRENT FIRST-PARTY Z.AI + TRAE SOURCES
-> VERIFY CURRENT SURFACE CONTROLS
-> COMPARE WITH REAL PROJECT EVIDENCE
-> UPDATE THIS FILE ONLY BY DEFAULT
```

Change the stable Trae family core or Router only when durable workflow/executor semantics actually change.