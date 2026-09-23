# Trader Assist / Trade OS — Agent Router

This file is the compact repository entry map. It is not the engineering
constitution and does not duplicate detailed procedures.

## Active authority

GitHub is the durable engineering control plane. Chat history, copied prompts,
old PR descriptions, and remembered SHAs are not canonical state.

The active governance path is:

```text
AGENTS.md
-> governance/ACTIVE_GOVERNANCE_MANIFEST.json
-> governance/PROJECT_RULES_INDEX.md
-> governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md
```

`ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md` is the sole active
project-wide engineering constitution. Files classified as historical in the
manifest are rationale only and cannot override V4.

For material work, require controller-bound evidence:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
CONTROL_CAPSULE_REF=<canonical locator>
SEMANTIC_READINESS=PASS
```

The Control Capsule, Task Packet hash, governance epoch, exact base/head,
execution surface, and preflight binding key must describe the same task.
Identity drift fails closed.

## Execution router

Engineering Control freezes one route. The user is not asked to choose the
executor or Plan versus Goal when the evidence already decides it.

```text
A DETERMINISTIC / MECHANICAL
  -> zero-model provider-native or deterministic tools

B SMALL / FROZEN / QUICK SEMANTIC
  -> fresh ordinary ChatGPT Writer

C LARGE / COHERENT / MULTI-STEP CODING
  -> Codex package
  -> deterministic bootstrap
  -> Plan-only
  -> package-boundary check
  -> one package-scoped Goal
  -> implement / test / bounded repair / read-only Code Review

D UNRESOLVED ARCHITECTURE / SECURITY / AUTHORITY / HIGH-CONSEQUENCE AMBIGUITY
  -> Engineering Control resolves and refreezes before implementation
```

One coherent shared-authority stage has one primary Writer. Use subagents only
for necessary, genuinely separable work. CI polling is never an agent role.

## Ability boundary

Every actor performs every safe authorized action available on its current
surface, makes routine routing/continuation decisions internally, and carries
the workflow to the next true boundary.

```text
WORK_TO_ABILITY_BOUNDARY=REQUIRED
ROUTINE_CONTINUE_CONFIRMATION=PROHIBITED
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
NEXT_NODE_DIRECT_HANDOFF=REQUIRED
```

Stop only for a real capability, authority, security, unresolved-design, or
retained-human gate. At a stop, return the final result or one complete next
executable action.

## Active skills

Load only the phase that applies:

- `.agents/skills/trade-os-v4-bootstrap/SKILL.md`
- `.agents/skills/trade-os-v4-development/SKILL.md`
- `.agents/skills/trade-os-v4-ci/SKILL.md`
- `.agents/skills/trade-os-v4-review/SKILL.md`

Older Trade OS skills remain compatibility/history unless an exact current
task explicitly invokes one.

## Conditional procedures

Use the Rules Index to locate the minimum applicable subordinate procedure.
Common triggers include:

- material direction-setting research;
- mature external solution selection or a proposed commodity rebuild;
- nontrivial human-executed commands;
- local Git publication or reviewed-PR closeout;
- tool onboarding/material tool change;
- target-host deployment through FinalShell;
- task-specific Product, Strategy, Operations, or Security authority.

Subordinate procedures may be stricter in their narrow domain but cannot weaken
or compete with V4.

## Verification and review

Development and verification are designed together. Use the cheapest decisive
focused local check first, then the authoritative exact-head CI/environment
proof required by the claim.

After Draft PR publication:

```text
WRITER_CHECKPOINT=CI_PENDING
MODEL_MEDIATED_CI_POLLING=PROHIBITED
CI_WAIT_OWNER=GITHUB_OR_DETERMINISTIC_TOOL
```

Codex Code Review is a read-only implementation-quality gate, not independent
acceptance. Final independent review uses a fresh ordinary ChatGPT context,
read-only exact GitHub evidence, and a result bound to the exact head. If the
authenticated PR owner cannot submit a native approval, use the canonical
`COMMENT_ONLY` evidence mode; do not misrepresent it as a second identity.

## Safety and retained gates

Normal engineering work does not commit directly to `main`, force-push shared
history, or commit secrets, credentials, private/account data, production
state, or real account identifiers.

The following always require separate explicit current user authority:

```text
MARK_READY
MERGE
BRANCH_DELETION
DEPLOYMENT
PRODUCTION_RUNTIME_OR_CLOUD_MUTATION
SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_OR_PRIVATE_API
WALLET_OR_SIGNING
EXCHANGE_WRITE_OR_ORDER_ACTION
AUTONOMOUS_OR_REAL_CAPITAL_TRADING
```

A new material architecture/provider/dependency decision, scope expansion,
security concern, authority conflict, or exhausted repair budget returns to
Engineering Control. Interruption is not failure: resume the exact preserved
thread/worktree/checkpoint rather than silently retrying or switching routes.
