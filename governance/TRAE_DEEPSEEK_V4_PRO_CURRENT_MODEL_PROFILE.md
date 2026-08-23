# Trader Assist / Trade OS — Trae + DeepSeek V4 Pro Current Model Profile

**Status:** REFRESHABLE MODEL-SPECIFIC GOVERNANCE CANDIDATE  
**Current user-available Trae model:** `DeepSeek V4 Pro`  
**Last verified:** 2026-08-23

DeepSeek V4 Pro inside Trae is a model selection under the Trae executor path, not a new project authority. Router V2 selects it per bounded task/stage.

## Best-use guidance

DeepSeek V4 Pro is a first-class advanced Writer. Prefer it when the task has a strong fit for:

- broad repository investigation and codebase mapping;
- repo-wide/full-stack implementation;
- larger-context root-cause discovery;
- a clean alternative Writer route after another model stalls or overfits a local hypothesis;
- bounded complex implementation where a different model family is useful.

Do not encode a universal ranking against GLM-5.3 or Claude Opus 4.6. Use current task fit and real Trader Assist evidence. The user retains manual override.

## Task packet discipline

For material work use the same high-constraint complete Task Packet principles:

```text
EXACT WORKTREE / ARTIFACT
FROZEN GOAL / SCOPE / INVARIANTS
ALLOWED + PROHIBITED PATHS
NEGATIVE / ATTACK CASES
EXACT VALIDATION
SAFE_STOP CONDITIONS
OUTPUT / EVIDENCE CONTRACT
```

Prefer one coherent bounded stage over one-file microtasks. If inspection exposes a new material route/authority/allowlist decision, stop and return to Engineering Control.

## Evidence

Passively collect real-task evidence where Trae exposes it:

```text
MODEL
TASK_CLASS
FIRST_PASS_RESULT
TEST/CI_RESULT
REPAIR_COUNT
HUMAN_INTERVENTION_COUNT
ELAPSED_TIME
POINTS/TOKENS WHERE EXPOSED
INDEPENDENT_REVIEW_BLOCKERS
```

Do not spend points on synthetic model-ranking work.

## Refresh rule

A future DeepSeek model change normally updates this file only after verifying the exact Trae-visible label/surface and current first-party DeepSeek evidence. Change Router/core workflow only if durable executor semantics change.