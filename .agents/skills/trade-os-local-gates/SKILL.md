---
name: trade-os-local-gates
description: Run only the frozen Trader Assist local tests, static checks and bounded validation commands, keeping passing output concise and failing closed on scope expansion.
---

# Trade OS Local Gates

Use the Task Packet's exact validation plan as authority.

- Run the smallest decisive focused gate first, then the required relevant regression/static checks.
- Keep passing output bounded; preserve exit status and decisive failure lines rather than flooding model context.
- Do not invent a broader test plan, install dependencies or change configuration unless authorized.
- Repair an in-scope implementation defect only when the frozen stage allows it.
- New root cause, new dependency/provider, allowlist expansion, architecture/authority change or exhausted repair budget => `L1_DECISION_REQUIRED`.
- Never convert an unrun check into PASS.