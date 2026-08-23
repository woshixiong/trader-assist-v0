# Tooling Router / Codex-Hermes V2 — Frozen Changeset Scope

This candidate is governance/tooling/config/skills only.

The current frozen expected changed-path set contains exactly 23 paths:

```text
.agents/skills/trade-os-evidence/SKILL.md
.agents/skills/trade-os-independent-review-bundle/SKILL.md
.agents/skills/trade-os-local-gates/SKILL.md
.agents/skills/trade-os-result-packet/SKILL.md
.agents/skills/trade-os-writer-preflight/SKILL.md
.codex/config.toml
AGENTS.md
CODEX.md
governance/CODEX_CLI_ENGINEERING_USAGE_PROFILE_V2_2026-08-23.md
governance/CODEX_CURRENT_MODEL_PROFILE.md
governance/CODEX_LOCAL_SETUP_V2_2026-08-23.md
governance/CODEX_V2_RESEARCH_EVIDENCE_SNAPSHOT_2026-08-23.md
governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md
governance/ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md
governance/HERMES_TOOLING_V2_INSERTION_PLAN_2026-08-23.md
governance/OPENCODE_ENGINEERING_USAGE_PROFILE_V1_2026-08-23.md
governance/PROJECT_RULES_INDEX.md
governance/TOOLING_ROUTER_CODEX_V2_ACCEPTANCE_CRITERIA_2026-08-23.md
governance/TOOLING_ROUTER_CODEX_V2_CHANGESET_2026-08-23.md
governance/TOOLING_ROUTER_CODEX_V2_PREFLIGHT_2026-08-23.md
governance/TOOLING_ROUTER_CODEX_V2_REVIEW_CHECKLIST_2026-08-23.md
governance/TRAE_DEEPSEEK_V4_PRO_CURRENT_MODEL_PROFILE.md
governance/TRAE_GLM_CURRENT_MODEL_PROFILE.md
```

This list is intended to match the actual PR changed-file set exactly before independent acceptance.

No runtime/product/strategy/test/dependency/deploy file is authorized in this changeset.

Any additional path discovered before independent acceptance requires explicit scope review. Runtime/product code addition forces `SAFE_STOP` / replan rather than silent expansion. A governance/tooling/config/skill path added by an explicitly reviewed convergence repair must be added to this frozen list before final acceptance so the list and live PR remain consistent.
