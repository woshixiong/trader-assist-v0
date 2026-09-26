# Trader Assist / Trade OS — Agent Router

This is the repository bootstrap/router. It is not the engineering constitution.

## Resolve authority

GitHub is the canonical engineering control plane. Chat history, copied prompts,
remembered SHAs, old PR descriptions, and stale local state are not authority.

For material engineering work, resolve the exact checked-out/ref state in this order:

~~~text
AGENTS.md
-> governance/ACTIVE_GOVERNANCE_MANIFEST.json
-> manifest-selected sole project-wide constitution
-> exact current package-state / Issue / PR
-> governance/PROJECT_RULES_INDEX.md when navigation is needed
-> only the narrow subordinate procedure triggered by the task
~~~

The manifest on the exact ref decides which constitution and skills apply.
This router cannot activate a candidate governance version by itself.

## Bootstrap invariants

Before mutation, fresh-resolve repository, main/base/head/tree, task identity,
role, route, scope, authority boundary, acceptance criteria, execution surface,
and retained gates. Never silently change role, executor, model, reasoning,
surface, scope, acceptance, or authority.

Use progressive disclosure. Do not load broad governance history, old chats, or
unrelated backlog by default.

Every actor works to its safe authorized ability boundary. Routine continuation,
SHA/CI/log relay, and long review-result relay through the user are prohibited.

At every expected stop emit:

~~~text
DECISION=
CANONICAL_GITHUB_REF=
NEXT_DESTINATION=
NEXT_ACTION=
COPY_PASTE_COMMAND_OR_PROMPT=
~~~

## Protected actions

The manifest/constitution may never imply current authority for Mark Ready,
merge, branch deletion, deployment, production/runtime/cloud mutation, service
control, credential/private-API mutation, wallet/signing, exchange/order writes,
autonomous trading, or real-capital action. Each requires explicit current human
authorization.

Load the manifest-selected phase skill only when that phase actually applies.
