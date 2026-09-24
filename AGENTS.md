# Trader Assist / Trade OS — Agent Router VNext

This file is the repository entry map only. It is not a second constitution.

GitHub is the canonical engineering source of truth. Chat history, copied prompts,
old PR narratives, remembered SHAs, and stale local state are not canonical.

Resolve governance in this order:

```text
AGENTS.md
-> governance/ACTIVE_GOVERNANCE_MANIFEST.json
-> governance/PROJECT_RULES_INDEX.md
-> active constitution selected by the manifest
```

Do not hard-code historical governance versions. The manifest selects the active
constitution. Historical documents are reference only.

## Role routing

```text
Engineering Control
  requirements / architecture / package freeze / escalation

Writer
  executes only frozen scope

Codex
  package execution surface for coherent coding tasks

Independent Reviewer
  fresh read-only evidence validation

Human
  retained protected gates
```

## Default execution principle

Use the cheapest capable route:

```text
mechanical
 -> deterministic tools

small semantic
 -> appropriate lightweight model

large coherent coding
 -> Codex package

unclear architecture/security/authority
 -> Engineering Control
```

## Handoff requirement

Every workflow stop must provide:

```text
DECISION
NEXT_DESTINATION
NEXT_ACTION
COPY_PASTE_COMMAND_OR_PROMPT
```

Do not leave routing decisions to the user when governance already determines
the next node.

## Boundary

Load detailed procedures only when their trigger applies. Do not duplicate
procedures here.
