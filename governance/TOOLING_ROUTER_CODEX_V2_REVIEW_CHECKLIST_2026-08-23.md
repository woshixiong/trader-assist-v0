# Tooling Router + Codex V2 — Independent Review Checklist

This file defines review scope only; it does not declare PASS.

The independent reviewer must read live GitHub and inspect the exact candidate HEAD rather than trusting Writer claims.

## Required decisions

### R1 — Router correctness

Verify:

- T0–T4 include the intended Codex/OpenCode/Trae/DSH candidate paths;
- Opus 4.6, GLM-5.3 and DeepSeek V4 Pro are treated as first-class task-fit candidates without an invented universal rank;
- Codex healthy/constrained/exhausted states behave as intended;
- user manual override and no-silent-substitution are preserved;
- one primary Writer and independent-review semantics remain intact.

### R2 — Codex token/context/cache efficiency

Verify:

- root `AGENTS.md` is materially slimmer/clearer as a map and does not omit critical authority gates;
- `CODEX.md` stale task state cannot become instruction authority;
- repo `.codex/config.toml` contains only stable low-noise defaults and does not pin task-local model/reasoning/sandbox/approval;
- stable stage model/reasoning/CWD/sandbox/approval/tool-shape rule is explicit;
- stable-prefix/mutable-tail, exact-session resume, bounded logs and JSONL telemetry are correct;
- global config recommendations do not overwrite unrelated user settings.

### R3 — Skills design

Verify the four `.agents/skills` are small, executor-neutral and suitable for progressive disclosure; ensure they do not silently inherit DeepSeek-specific authority or create a second acceptance system.

### R4 — Governance continuity

Verify `AGENTS.md` + `PROJECT_RULES_INDEX.md` still preserve the canonical Unified Governance, Mandatory Preflight, research method, repair budget, exact artifact/CI/review and user-retained authority gates.

Check whether any V2 wording conflicts with the Unified Governance's requirement that project participants compare the task with canonical rules. A bounded Writer may rely on a frozen preflight attestation only to the extent the canonical rules permit; no token optimization may weaken an authority gate.

### R5 — Hermes insertion

Verify Hermes remains transport/operator/orchestration only; it may carry frozen packets and deterministic mechanics without becoming Router/L1/Reviewer or adding a duplicate semantic reasoning layer.

### R6 — Scope / exact-head CI

Candidate must be governance/tooling/config/skills only. No runtime/product/strategy semantics. Verify exact-head CI and changed-file scope.

## Final disposition

Return one of:

```text
PASS
REPAIR
REPLAN
SAFE_STOP
```

If PASS, report the exact reviewed HEAD SHA and exact-head CI run/result. PASS does not grant Mark Ready or merge; those remain separate user authorities.