# VNext Qualification Failure Closure Matrix

## Purpose
Define deterministic failure handling during VNext qualification.

## Failure Routes

| Failure | Destination | Rule |
|---|---|---|
| Plan rejected | Codex revise | Preserve scope and regenerate bounded plan |
| Scope or architecture conflict | Engineering Control | Re-plan before implementation |
| Implementation failure | Original execution route | Bounded repair only |
| CI failure | Same implementation route | Use deterministic CI evidence |
| Final review failure | Engineering Control | No direct reviewer modification |
| Interrupted execution | Existing checkpoint | Resume, do not restart |

## Required Output
Every transition must provide:

- Current State
- Decision
- Next Destination
- Exact Next Action
- Required Authority
