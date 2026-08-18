---
name: trade-os-local-gates
description: Run only the frozen Trader Assist local tests, static checks and bounded validation commands from the Task Packet, with concise outputs and fail-closed scope discipline.
whenToUse: Load when a DeepSeek Harness task reaches focused tests, relevant regression, Ruff, Mypy, compile or other explicitly authorized local gates.
user-invocable: true
disable-model-invocation: false
---

# Trade OS Local Gates

Use the Task Packet's exact test/gate plan as authority.

Rules:

- Do not invent a broader test plan, install dependencies or change configuration unless the packet authorizes it.
- Prefer the smallest decisive gate first, then the broader relevant regression required by the packet.
- Keep command output bounded. Capture exit status and decisive failure lines; do not flood model context with entire passing logs.
- If a test failure is caused by an in-scope implementation defect, repair only when the packet/repair stage authorizes ordinary in-scope correction.
- If a failure reveals a new root cause, new dependency, allowlist expansion, architecture/authority change or exhausted repair budget, stop with `L1_DECISION_REQUIRED`.
- Never convert an unrun check into PASS.

When applicable, report exact observed status for focused tests, relevant regression, Ruff, Mypy, compile/compileall, schema/diff/scope/secret checks or other packet-specified gates.
