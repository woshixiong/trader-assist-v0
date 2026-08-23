# Tooling Router + Codex/Hermes V2 — Independent Review Checklist

This file defines review scope only; it does not declare PASS.

The independent reviewer must read live GitHub and inspect the exact candidate HEAD rather than trusting Writer claims.

## Required decisions

### R1 — Router correctness

Verify:

- T0–T4 include the intended Codex/OpenCode/Trae/DSH candidate paths;
- Opus 4.6, GLM-5.3 and DeepSeek V4 Pro are treated as first-class task-fit candidates without an invented universal rank;
- Codex healthy/constrained/exhausted states behave as intended;
- user manual override and no-silent-substitution are preserved;
- one primary Writer and independent-review semantics remain intact;
- T4 final adjudication defaults to a new ordinary ChatGPT window with the strongest appropriate available model/highest appropriate reasoning;
- when local evidence is needed, deterministic hash-manifested review bundle -> strongest ChatGPT is preferred over defaulting final review to a weaker local coding model.

### R2 — Codex token/context/cache efficiency

Verify:

- root `AGENTS.md` is materially slimmer/clearer as a map and does not omit critical authority gates;
- `CODEX.md` stale task state cannot become instruction authority;
- repo `.codex/config.toml` contains only stable low-noise defaults and does not pin task-local model/reasoning/sandbox/approval;
- stable stage model/reasoning/CWD/sandbox/approval/tool/Web-Search shape rule is explicit;
- stable-prefix/mutable-tail, exact-session resume, bounded logs and JSONL telemetry are correct;
- global config recommendations do not overwrite unrelated user settings;
- Engineering Control explicitly chooses model and reasoning for every Codex Writer stage;
- Engineering Control explicitly sets `CODEX_WEB_SEARCH_REQUIRED=YES|NO` and a verified mode when YES; Web Search is neither blindly always-on nor blindly unavailable when needed;
- required mid-stage model/reasoning/Web-Search changes create an appropriate stage/session boundary rather than silently breaking cache/execution shape.

### R3 — Skills design

Verify the five `.agents/skills` are small, single-purpose, executor-neutral where intended and suitable for progressive disclosure:

- `trade-os-writer-preflight`
- `trade-os-local-gates`
- `trade-os-evidence`
- `trade-os-result-packet`
- `trade-os-independent-review-bundle`

Ensure they do not silently inherit DeepSeek-specific authority, create a second acceptance system, or flood initial context. The review-bundle skill must generate evidence only and never declare PASS.

### R4 — Governance continuity / tool onboarding

Verify `AGENTS.md` + `PROJECT_RULES_INDEX.md` preserve canonical Unified Governance, Mandatory Preflight, research method, repair budget, exact artifact/CI/review and user-retained authority gates.

Review `governance/ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md` and verify new executors/operators/orchestrators and material configuration/permission/session/routing changes require separate independent acceptance before first project use, without forcing full harness re-acceptance for harmless model-label refreshes.

### R5 — Hermes insertion and handoff efficiency

Review both:

- accepted/current `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md`;
- candidate `governance/HERMES_TOOLING_V2_INSERTION_PLAN_2026-08-23.md`.

Verify Hermes remains transport/operator/orchestration only; it may carry frozen packets and perform deterministic mechanics without becoming Router/L1/Reviewer or adding a duplicate semantic reasoning layer.

Verify the Codex -> Hermes boundary can actually reduce Codex token/human-relay burden: Codex handles semantic inspect/reason/implement/validation; Hermes may handle authorized deterministic tail work after exact result freeze. Ensure the plan does not force unnecessary handoffs when the tail is trivial.

### R6 — Hermes diagnosability / recoverability

Verify every multi-step Hermes run is checkpointed with enough exact data for human takeover after failure: run ID, phase, packet/artifact hashes, destination/executor/model/reasoning, worktree/HEAD where relevant, result/exit status, retry count, stop reason and resume point.

Verify:

- no hidden semantic retry;
- no inference that UI/tool state succeeded without verification;
- exact resume from verified checkpoints only;
- model/reasoning/Web-Search/route mismatch fails closed;
- unexpected login/update/permission/UI ambiguity fails closed;
- a user can identify exactly where an automated run stopped instead of reconstructing it from prose.

### R7 — Hermes -> strongest ChatGPT review transport feasibility and boundary

Verify the proposed T4 automation is sound:

```text
Terminal/tooling builds exact review bundle
-> manifest/hash verification
-> Hermes binds a fresh ChatGPT review surface
-> verifies exact L1-frozen reviewer model/reasoning UI state
-> uploads exact bundle
-> pastes exact frozen review prompt without paraphrase
-> verifies attachment/prompt state before submit
-> captures result/evidence
```

Check current Hermes upstream capabilities relevant to terminal/process, computer-use/browser state and file-input upload. Confirm the plan does **not** falsely claim the current project V1 Lossless Task Packet/H2 schema already authorizes ChatGPT review-browser transport or direct OpenCode/DSH H2 dispatch. Those extensions must remain a separately reviewed Hermes configuration-stage prerequisite.

### R8 — Scope / exact-head CI

Candidate must remain governance/tooling/config/skills only. No runtime/product/strategy semantics. Verify exact-head CI and changed-file scope.

## Acceptance criteria

Independently disposition A1–A19 in `governance/TOOLING_ROUTER_CODEX_V2_ACCEPTANCE_CRITERIA_2026-08-23.md` as PASS/FAIL with exact evidence.

## Final disposition

Return one of:

```text
PASS
REPAIR
REPLAN
SAFE_STOP
```

If PASS, report the exact reviewed HEAD SHA and exact-head CI run/result. PASS does not grant Mark Ready, merge, Hermes activation, first project use or deployment; those remain separate user authorities.