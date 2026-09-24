# Codex Runtime Policy VNext Draft

Status: DRAFT — migration preparation only

## Purpose

Consolidate Codex execution rules that are currently distributed across model profiles, CLI notes, and workflow procedures.

This is not a second constitution. The active manifest selects the effective route.

## Core principles

1. Use Codex quota for semantic work, not deterministic bookkeeping.
2. Prefer the lowest-cost capable execution route.
3. Keep one primary Writer by default.
4. Use subagents only when runtime identity is verifiable and the expected benefit exceeds context and quota cost.
5. Do not use model reasoning for CI waiting, status polling, SHA checks, or mechanical routing.

## Routing

```text
Deterministic/mechanical
-> zero-model deterministic tools

Small bounded semantic
-> appropriate lightweight model

Large coherent implementation
-> Codex package

Architecture/security/authority ambiguity
-> Engineering Control
```

## Lifecycle

```text
Plan-only
-> Pre-code Review
-> Implementation
-> Focused validation
-> CI
-> Bounded repair
-> Final Review handoff
```

## Model policy

The active manifest/controller selects exact model and reasoning values.

Do not hard-code temporary model preferences into procedures or prompts.

## Agent policy

Default:

```text
subagents = disabled
```

Enable only when:

- work is genuinely separable;
- runtime identity is verified;
- additional context cost is justified;
- outputs have deterministic reconciliation.

Recursive delegation is prohibited unless explicitly qualified by active governance.

## Recovery

Quota exhaustion, network failure, UI interruption, CI transport failure, or evidence egress failure is a checkpoint recovery event, not semantic failure.

Resume from durable GitHub/controller state. Do not restart semantic work merely because execution output was interrupted.

## Activation

This document remains inactive until referenced by the active manifest after validation.
