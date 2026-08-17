# ChatGPT Project Governance Bridge V1

**Effective:** 2026-08-17  
**Scope:** Trader Assist / Trade OS ChatGPT Project behavior  
**Purpose:** provide a short second-layer ChatGPT instruction that always routes engineering work back to the live GitHub canonical rules without creating a second mutable copy of the full ruleset.

## 1. Governing architecture

Use two layers:

```text
PRIMARY / CANONICAL
GitHub repository governance + live code/PR/CI state

SECONDARY / ENFORCEMENT BRIDGE
ChatGPT Project Instructions requiring live GitHub rule intake and preflight
```

Do **not** duplicate the complete engineering rules into ChatGPT memory or global Custom Instructions. The detailed rules evolve in GitHub and must have one auditable source of truth.

ChatGPT memory may retain a short pointer such as "Trader Assist engineering governance is canonical in GitHub and must be re-read before material work", but memory is not an authority source.

## 2. Recommended ChatGPT Project Instructions block

Place the following block in the ChatGPT Project Instructions for the Trader Assist / Trade OS project:

```text
TRADER ASSIST / TRADE OS PROJECT GOVERNANCE BRIDGE

For every project task, GitHub is the canonical source of engineering truth. Do not treat ChatGPT memory, prior chat summaries, stale PR bodies, or copied prompts as higher authority than live GitHub.

Before any engineering, research, architecture, product/strategy route, implementation, review, handoff, automation, operations-engineering, or technical-direction work:

1. Use the GitHub connector to resolve the live repository/main SHA, active issue/PR/head and relevant exact-head CI state.
2. Read the current live versions of:
   - AGENTS.md
   - governance/PROJECT_RULES_INDEX.md
   - governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md
   - governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md when material
   - governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md when material
   - any narrower current Product / Strategy / Operations / Security authority named by the active task.
3. Compare the task against the canonical engineering rules before beginning and record PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS or SAFE_STOP.
4. For material Writer work, do not dispatch implementation until ENGINEERING_PREFLIGHT_GATE=PASS.
5. For material direction-setting work, preserve the exact sequence: independent analysis first; external primary/mature-solution research second; synthesis and final route third.
6. Prefer mature/provider-native solutions, the simplest safe route, stable narrow interfaces, code continuity and replaceable implementation seams. Do not repeatedly patch the same failed design; obey the repair budget and holistic-convergence stop condition.
7. Do not use the user as a routine message bus when exact task/evidence transport can be automated or carried directly.
8. User-operated macOS engineering delivery defaults to one contiguous ordinary-Terminal paste that performs routing/preflight/Codex invocation internally. Do not require a second prompt paste unless technically unavoidable or required by an explicit authority/security gate.
9. Writer self-reported PASS is not independent acceptance. Bind review and CI to exact artifacts/exact heads and use delta review after an accepted baseline.
10. Never infer Mark Ready, merge, deploy, runtime/cloud mutation, credentials/private API, signing/wallet, exchange-write, order submission or trading authority from a previous stage.

If ChatGPT memory or a prior conversation conflicts with live GitHub governance, live GitHub controls. If the required live GitHub intake cannot be completed, state that the engineering rules are not verified and SAFE_STOP rather than silently working from memory.
```

## 3. Saved Memory recommendation

If personal Saved Memory is used, save only a short stable pointer, not the full ruleset:

```text
For Trader Assist / Trade OS, live GitHub governance is canonical. Before material project work, verify the current GitHub engineering rules and preflight; do not rely on saved memory as the rule source.
```

This is optional. The Project Instructions bridge is the preferred ChatGPT-side enforcement layer.

## 4. Global Custom Instructions recommendation

Do not paste the full Trader Assist engineering rules into global Custom Instructions because they apply outside the project and may become stale.

If Trader Assist work is sometimes performed outside the ChatGPT Project, an optional minimal global pointer is:

```text
When a request concerns Trader Assist / Trade OS, treat its live GitHub governance as canonical and verify the current project rules before material engineering work.
```

## 5. Project-memory caveat

Project memory is useful for continuity and prior project context, but it is not a versioned governance store. In project-only memory mode, outside Saved Memories are not referenced. Therefore the ruleset must remain discoverable and enforceable through Project Instructions + live GitHub rather than depending on personal memory state.

## 6. Change control

When the canonical GitHub engineering filename/version changes, update this bridge and the ChatGPT Project Instructions pointer in the same governance maintenance cycle.

Do not create a second independent rule copy. Keep the Project Instructions short enough that the authoritative detail always remains in GitHub.
