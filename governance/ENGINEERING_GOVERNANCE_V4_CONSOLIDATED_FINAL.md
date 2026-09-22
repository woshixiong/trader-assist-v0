# ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL

## Status

Canonical governance consolidation proposal implementation.

## Purpose

Unify V2 routing rules and V4 workflow architecture into one engineering governance model.

## Canonical Principles

- GitHub is the engineering source of truth.
- Chat history is not canonical state.
- Roles and authority boundaries must remain explicit.
- Agents continue until a real gate requires human action.

## Roles

Engineering Control:
- planning
- routing
- authority checks
- handoff generation

Writer:
- implementation only

Reviewer:
- independent validation only

Human Gate:
- authorization decisions

## Stage Routing

Semantic stages:
- architecture
- complex reasoning
- implementation decisions

Use high capability reasoning.

Mechanical stages:
- CI checks
- deterministic status queries
- evidence collection

Prefer tools or lightweight execution.

Reporting stages:
- summaries
- formatting
- evidence packaging

Prefer lightweight execution.

## Continuation Rule

Completion of one stage must produce the next valid handoff artifact.

Agents stop only when:
- human authorization is required;
- permissions are insufficient;
- safety or governance conflict exists.

## Handoff Requirement

Authority-bearing launchers must include required capability initialization.

Examples:
- GitHub tasks require GitHub capability activation.

Handoffs should use structured artifacts instead of large chat transfer.

## Bootstrap Enforcement

Before execution, every authority-bearing window confirms:
- role;
- authority boundary;
- canonical source;
- required capabilities.

## Codex Optimization

- Reserve Codex for coding and reasoning-heavy tasks.
- Prefer session continuation.
- Avoid repeated context loading.
- Keep mechanical work outside expensive reasoning paths.

## Resume Rule

After interruption, recover from:
- existing session state;
- GitHub state;
- stored artifacts.

Avoid unnecessary restarts.

## Escalation Rule

Escalate when:
- scope expands;
- architecture changes;
- authority changes;
- production impact appears;
- governance conflict exists.

## Forbidden

- silent role switching;
- silent model switching;
- hidden authority expansion;
- human used as message relay.

## Migration

V2 routing becomes historical reference.
V4 becomes the single canonical governance direction after review and merge.
