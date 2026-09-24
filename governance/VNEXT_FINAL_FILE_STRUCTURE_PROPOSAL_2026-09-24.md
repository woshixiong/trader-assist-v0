# VNext Final Governance File Structure Proposal

## Target Structure

```text
governance/
├── ENGINEERING_GOVERNANCE_VNEXT.md
├── ACTIVE_GOVERNANCE_MANIFEST.json
├── PROJECT_RULES_INDEX.md
├── procedures/
│   ├── CODEX_RUNTIME_POLICY.md
│   ├── REVIEW_FLOW.md
│   ├── FAILURE_ROUTING.md
│   └── RECOVERY.md
└── archive/
    └── historical and research material
```

## Principles

- One constitutional source of truth.
- One active manifest entry point.
- Procedures load only when triggered.
- Historical documents cannot override active rules.
- Runtime configuration stays separate from governance principles.

## Migration Rule

Do not delete historical material before VNext qualification passes.
