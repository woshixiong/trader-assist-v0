# VNext Activation Validation Matrix

## Validation Scope

The VNext governance migration must be validated before activation.

## Scenarios

| Scenario | Expected Route |
|---|---|
| Normal coding task | Engineering Control → Codex/Writer → CI → Review |
| Plan rejected | Return to Codex plan revision |
| Scope/architecture conflict | Return to Engineering Control |
| CI failure | Deterministic repair loop |
| Final review failure | Engineering Control re-plan |
| Interrupted execution | Resume checkpoint, do not restart |
| Quota interruption | Resume durable state |

## Success Criteria

- Clear next action at every handoff.
- No manual state reconstruction.
- No duplicate governance authority.
- Protected actions remain gated.
