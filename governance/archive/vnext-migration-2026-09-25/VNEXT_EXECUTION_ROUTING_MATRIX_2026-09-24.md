# VNext Execution Routing Matrix

## Purpose

Define deterministic routing between Engineering Control, ChatGPT, Codex, Reviewer, and human gates.

## Routing

| Situation | Route |
|---|---|
| Deterministic mechanical change | Zero-model tools |
| Small bounded semantic task | Fresh ordinary ChatGPT Writer |
| Large coherent coding package | Codex package |
| Architecture/security/provider decision | Engineering Control |
| Independent validation | Fresh Reviewer |

## Required outputs

Every stage must provide:

- decision;
- destination;
- exact next action;
- copy-ready command when execution is required.

## Failure routing

- Planning failure -> Codex revise or Control re-plan according to scope.
- Implementation failure -> bounded repair route.
- Review failure -> return to Engineering Control unless the issue is a bounded implementation defect.

## Human gates

Human approval remains required for protected actions only.
