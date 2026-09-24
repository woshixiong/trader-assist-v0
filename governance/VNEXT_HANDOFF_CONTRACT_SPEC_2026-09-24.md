# VNext Handoff Contract Specification

## Purpose

Define deterministic handoff rules between Engineering Control, Codex, Reviewer, and Human gates.

## Required output at every stopping point

Every workflow stop must provide:

1. Current decision.
2. Exact next destination.
3. Copy-ready command or action.
4. Required evidence/state binding.

## Routes

### Pre-code Review FAIL

Reviewer must classify:

- PLAN_REVISE: return to Codex planning.
- CONTROL_REPLAN: return to Engineering Control.

The reviewer must include the exact next prompt/command.

### Implementation FAIL

Return to the bounded implementation executor unless the failure indicates scope, architecture, security, or authority issues.

### Final Review FAIL

Return to Engineering Control for a new repair cycle.

Do not directly mutate implementation from Reviewer context.

## Human retained gates

Human approval remains required for protected actions:

- MARK_READY
- MERGE
- DEPLOYMENT
- production mutation

## Objective

Reduce human relay work while preserving explicit ownership boundaries.
