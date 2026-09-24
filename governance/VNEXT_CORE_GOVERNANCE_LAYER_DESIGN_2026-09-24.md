# VNext Core Governance Layer Design

## Purpose
Define the final separation between governance principles, procedures, and runtime execution.

## Layers

### Governance Constitution
Owns:
- principles;
- authority boundaries;
- role separation;
- protected actions.

Does not own:
- command syntax;
- model selection details;
- transient operational procedures.

### Procedures
Own:
- Codex workflow;
- review workflow;
- failure routing;
- recovery workflow.

### Runtime
Own:
- execution configuration;
- deterministic automation;
- checkpoint handling.

## Migration Rule
VNext remains inactive until qualification validation completes.
