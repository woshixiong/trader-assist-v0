---
name: trade-os-v5-handoff
description: Emit a zero-decision, GitHub-anchored handoff at every expected stop without using the user as a state or review-result relay.
---

# Trade OS V5 Handoff

Every expected stop emits:

~~~text
DECISION=
CANONICAL_GITHUB_REF=
NEXT_DESTINATION=
NEXT_ACTION=
COPY_PASTE_COMMAND_OR_PROMPT=
~~~

Before emitting a terminal result or blocker, fresh-read the canonical task/PR
state and reconcile any already-advanced state idempotently.

The GitHub locator contains the durable detail. Chat remains compact. The
copy-paste command/prompt must be complete and must carry the exact role, target,
identity, scope/authority boundary, and required next operation so the user does
not reconstruct state or choose a route already determined by evidence.

Protected actions are never smuggled through a handoff; they require explicit
current human authority.
