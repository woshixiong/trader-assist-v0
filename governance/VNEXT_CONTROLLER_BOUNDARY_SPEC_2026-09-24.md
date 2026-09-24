# VNext Controller Boundary Specification

Status: PREPARATION ONLY

## Purpose

Define the smallest deterministic controller responsibility required by VNext.
The controller is not a replacement for Engineering Control, Codex, or Review.

## Controller owns

- durable workflow state;
- exact task/package/base/head/tree binding;
- allowed stage transitions;
- checkpoint resume information;
- deterministic CI/status waiting;
- bounded retry bookkeeping;
- stale-state detection;
- next allowed action generation.

## Controller does not own

- architecture decisions;
- product requirements;
- acceptance interpretation;
- code implementation;
- security decisions;
- final acceptance review;
- protected human approvals.

## State machine target

PREPARED
-> PLAN_ONLY
-> PRE_CODE_REVIEW
-> IMPLEMENTATION
-> VALIDATION
-> CI
-> FINAL_REVIEW
-> CLOSEOUT

Failure routes must preserve the exact failed state and return:

DECISION
NEXT_DESTINATION
NEXT_ACTION
COPY_PASTE_COMMAND_OR_PROMPT

## Design principle

Prefer a thin deterministic controller over a general autonomous agent framework.
Use existing GitHub/Codex capabilities first and add custom automation only when
it removes repeated manual coordination without adding governance complexity.
