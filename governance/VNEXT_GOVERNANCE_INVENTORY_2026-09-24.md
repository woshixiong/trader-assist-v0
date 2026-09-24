# Trader Assist / Trade OS — VNext Governance Inventory

## Purpose

Baseline inventory for the VNext governance migration. This document classifies
existing governance surfaces before activation changes.

## Current active control surfaces

| Surface | Action | Reason |
|---|---|---|
| AGENTS.md | UPDATE | Keep as thin repository entry router only |
| governance/ACTIVE_GOVERNANCE_MANIFEST.json | UPDATE | Remain the machine-readable active authority map |
| governance/PROJECT_RULES_INDEX.md | UPDATE | Navigation and loading rules |
| governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md | REVIEW | Candidate replacement target for VNext constitution |
| governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE_V4* | UPDATE | Align ChatGPT entry behavior |

## Execution layer

| Surface | Action | Reason |
|---|---|---|
| .codex/config.toml | REVIEW | Align model routing and cost controls |
| .codex/agents/* | REVIEW | Validate whether subagents are still useful |
| .codex/hooks/* | REVIEW | Keep only deterministic safety controls |
| scripts/control/* | REVIEW | Avoid duplicated orchestration logic |

## Historical / compatibility layer

Existing historical documents should remain available only as rationale unless
explicitly reactivated by the new governance manifest.

## Design principle

The migration should reduce duplicated rules. The final structure should have:

1. one constitution;
2. one active manifest;
3. thin entry points;
4. conditional procedures loaded only when triggered;
5. deterministic execution controls separated from semantic decisions.

## Not included

- no production deployment changes;
- no application code changes;
- no active governance switch in this preparation stage.
