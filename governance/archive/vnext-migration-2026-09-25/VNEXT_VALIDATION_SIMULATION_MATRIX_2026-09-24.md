# VNext Governance Validation Simulation Matrix

Status: DRAFT ONLY

Purpose: validate governance transitions before activation.

| Scenario | Expected route |
|---|---|
| Normal Codex package | Plan -> pre-code review -> implementation -> CI -> final review |
| Pre-code review plan defect | Return to Codex PLAN_REVISE with explicit command |
| Pre-code review architecture defect | Return to Engineering Control REPLAN |
| CI mechanical failure | Deterministic repair/retry path |
| Semantic implementation failure | Bounded repair, then escalation if exhausted |
| Final review fail | Engineering Control repair/replan |
| Quota/network interruption | Resume checkpoint, no semantic restart |
| Head drift after review | Invalidate stale evidence and rerun required validation |

Activation requires all scenarios to have deterministic ownership and next-action output.
