# Trade OS VNext Governance Migration Plan

Status: PREPARATION

Purpose: prepare the governance transition after the current V4 workflow cycle. This document does not activate VNext governance.

## Current canonical state

Current active entry path:

```text
AGENTS.md
-> governance/ACTIVE_GOVERNANCE_MANIFEST.json
-> governance/PROJECT_RULES_INDEX.md
-> governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md
```

Current active governance remains unchanged during preparation.

## Migration classification

### REPLACE / UPDATE

- AGENTS.md: thinner VNext router after activation approval.
- ACTIVE_GOVERNANCE_MANIFEST.json: new active pointer and routing metadata.
- PROJECT_RULES_INDEX.md: updated navigation.
- ChatGPT Project Instruction Bridge: replace after GitHub governance becomes canonical.
- Engineering constitution: add VNext constitution and activate through manifest.

### REVIEW / MERGE INTO NEW STRUCTURE

- Codex routing rules: preserve cost-control principles and simplify around current Codex CLI workflow.
- Review lifecycle: add explicit handoff decision schema.
- Failure routing: deterministic PLAN_REVISE versus CONTROL_REPLAN.
- Closeout flow: preserve human gates with conditional authorization path.
- Token optimization: deterministic-tool-first policy.

### ARCHIVE

Historical rationale documents remain available but cannot override active governance.

## Activation requirements

Before switching active governance:

- new constitution exists;
- manifest points to new constitution;
- AGENTS router matches manifest;
- consistency checks pass;
- simulated success/failure flows pass;
- first migration task is designated as qualification run.

## Non-goals

- no generic multi-agent framework;
- no immediate OpenRouter/free-model integration;
- no unnecessary launcher/controller complexity before validated need;
- no interruption of unfinished engineering work.
