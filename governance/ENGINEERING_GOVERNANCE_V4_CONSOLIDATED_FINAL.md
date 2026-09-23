# Trader Assist / Trade OS — Engineering Governance V4 Consolidated Final

**Status:** ACTIVE — SOLE PROJECT-WIDE ENGINEERING CONSTITUTION
**Effective date:** 2026-09-23
**Repository:** `woshixiong/trader-assist-v0`

This document is the single active project-wide engineering constitution.
Task-specific Product, Strategy, Operations, Security, executor, deployment,
and operator procedures may be stricter in their narrow domain but may not
weaken or compete with V4.

Unified V2, Router V2, prior executor profiles, prior workflow proposals, and
old skills are historical rationale after this migration. Their still-valid
project-wide invariants are consolidated here.

This constitution grants no Mark Ready, merge, deployment, runtime/cloud
mutation, credential/private-API, wallet/signing, exchange-write, order, or
real-capital authority.

---

## 1. Authority architecture

### 1.1 Canonical path

```text
AGENTS.md
-> ACTIVE_GOVERNANCE_MANIFEST.json
-> PROJECT_RULES_INDEX.md
-> ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md
```

The manifest is the machine-readable active map, the index is human
navigation, and this file owns project-wide rules. Maps and checklists point to
authority; they do not redefine it.

GitHub is the durable source of engineering truth. Before material work,
freshly resolve the applicable repository, main/base/head/tree, Issue or PR,
changed paths, CI, artifacts, and current domain authority. Exact canonical
objects override chat history, remembered conclusions, copied prompts, stale
branches, and old PR descriptions.

### 1.2 Precedence

When authorities conflict, apply:

1. explicit current user authority and safety boundaries;
2. current accepted Product / Strategy / Security / Operations authority for
   its narrow domain;
3. this V4 constitution;
4. the current bound Control Capsule, preflight, and frozen Development Package;
5. applicable subordinate procedures and executor profiles;
6. historical governance and incident records as rationale only.

A less strict source never weakens a stricter safety or authority requirement.
Historical files cannot override V4.

### 1.3 Durable control plane

```text
GITHUB = DURABLE CONTROL PLANE / STATE MACHINE
ORDINARY CHATGPT = MATERIAL CONTROL / EXCEPTION / ADJUDICATION
ACCEPTED WRITER = SEMANTIC IMPLEMENTATION
GITHUB ACTIONS / DETERMINISTIC TOOLS = ROUTINE VERIFICATION / TRANSITIONS
```

Chat history is an ephemeral reasoning surface, not engineering state. No
critical engineering state may exist only in chat.

Every active material task maintains one compact Control Capsule containing:

```text
TASK_ID
GOVERNANCE_EPOCH
EXACT_MAIN
EXACT_TARGET_HEAD_OR_TREE
TASK_PACKET_HASH
RISK_CLASS
CURRENT_STATE
CURRENT_BLOCKER
NEXT_ALLOWED_ACTION
RUNNING_AGENT_THREAD_OR_WORKSPACE_ID
CURRENT_PR
CI_STATE_LOCATOR
COMPLETED_WORK_LEDGER
RETAINED_USER_GATES
AUTHORITY_ATTESTATION_LOCATORS
PREFLIGHT_BINDING_KEY
```

Full evidence and history remain behind exact canonical locators. Before a
named workstream is dispatched, the completed-work ledger must prove it is not
already terminal or ineligible for redispatch.

---

## 2. Universal objective and ability boundary

Optimize validated useful progress per unit of total engineering effort in
this order:

```text
SAFETY / AUTHORITY CORRECTNESS
-> ROOT-CAUSE CORRECTNESS
-> PRODUCT / STRATEGY / DATA USEFULNESS
-> MATURE SIMPLE REUSABLE ROUTE
-> CONTINUITY / REPLACEABILITY
-> VALIDATION QUALITY
-> LOW HUMAN RELAY / REWORK
-> TOKEN / QUOTA / WALL-CLOCK EFFICIENCY
-> OPTIONAL SOPHISTICATION
```

Total burden includes implementation, tests, CI, review, operator work,
recovery, migration, model cost, and future maintenance. Low current cost or
familiarity never overrides correctness or fit.

Every control and implementation context must:

1. perform every safe authorized action available on its current surface;
2. decide routine routing and continuation internally when evidence suffices;
3. continue across routine stages without progress-confirmation turns;
4. avoid using the user as a SHA/log/CI/review message bus;
5. stop only at a capability, authority, security, unresolved-design, or
   retained-human boundary;
6. return the final result or one complete ready-to-use next action.

```text
WORK_TO_ABILITY_BOUNDARY=REQUIRED
ROUTINE_ROUTE_EXPLANATION_TO_USER=NOT_REQUIRED
ROUTINE_CONTINUE_CONFIRMATION=PROHIBITED
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
NEXT_NODE_DIRECT_HANDOFF=REQUIRED
```

This interaction rule never bypasses role separation, safety gates,
independent review, or protected actions.

---

## 3. Roles and execution routing

### 3.1 Role separation

- **Engineering Control:** understands requests; owns architecture, planning,
  decomposition, authority, route selection, Development Package freeze,
  material exceptions, and retained-gate handoffs.
- **Writer:** implements only the frozen package and performs bounded in-scope
  validation/repair.
- **Codex Code Reviewer:** read-only implementation-quality review before
  publication/final handoff; never authority-bearing acceptance.
- **Independent Reviewer:** fresh ordinary ChatGPT context, read-only, exact
  canonical evidence; produces authority-bearing independent review.
- **Human Gate:** authorizes protected actions.

Implementers do not self-approve. Reviewers do not implement. Engineering
Control or Writer readiness conclusions are never independent acceptance.

### 3.2 Final route model

Engineering Control freezes exactly one branch. The user does not choose the
executor and does not choose Plan versus Goal when the evidence is sufficient.

```text
A. DETERMINISTIC / MECHANICAL
   -> zero-model GitHub/provider-native/deterministic tools

B. SMALL / FROZEN / QUICK SEMANTIC
   -> fresh ordinary ChatGPT Writer
   -> one bounded launcher
   -> implementation + focused validation + authorized publication boundary

C. LARGE / COHERENT / MULTI-STEP CODING
   -> Codex
   -> deterministic bootstrap
   -> Plan-only
   -> automatic package-boundary check
   -> one package-scoped Goal
   -> implement / test / bounded repair / read-only Code Review

D. UNRESOLVED ARCHITECTURE / SECURITY / AUTHORITY /
   HIGH-CONSEQUENCE AMBIGUITY
   -> remain with or return to Engineering Control
   -> resolve and refreeze before implementation
```

Manual user override remains available but never permits a silent capability,
model, executor, reasoning, or authority substitution.

### 3.3 Route identity

Before every model-backed launch freeze:

```text
ROLE
EXECUTOR_SURFACE
PROVIDER
MODEL
REASONING_OR_EQUIVALENT
WEB_SEARCH_OR_TOOL_STATE
SESSION_POLICY
RESOURCE_STATE
SELECTION_REASON
```

Record actual identity where exposed. A required requested/actual mismatch or
unprovable required identity is a Router incident: fail closed, preserve state,
do not automatically rerun or silently substitute, and return one complete
Engineering Control escalation.

Concrete model IDs belong in current configuration/profile or a bound package,
not in permanent capability-class rules.

For Codex child agents, the requested profile is never proof of the actual child
runtime identity. A child may be used only when the surface can verify the
actual spawned model and reasoning against the frozen route. If it cannot,
do not spawn that child. Never inherit or fall back to the parent/default
flagship profile merely to preserve a child stage. Internal Code Review may be
skipped when its child identity is unverifiable; final authority-bearing review
still requires a fresh ordinary ChatGPT context.

```text
SUBAGENT_MODEL_REASONING_MUST_BE_RUNTIME_VERIFIABLE=YES
UNVERIFIED_SUBAGENT_MODEL_INHERITANCE=PROHIBITED
FALLBACK_TO_PARENT_SOL_HIGH=PROHIBITED
SILENT_REVIEWER_PROFILE_FALLBACK=PROHIBITED
```

### 3.4 Concurrency

```text
ONE_PRIMARY_WRITER_PER_COHERENT_SHARED_AUTHORITY_STAGE=YES
INDEPENDENT_TASKS + DISJOINT_WRITES + NO_DEPENDENCY => PARALLEL_ALLOWED
SHARED_AUTHORITY_OR_WRITE_SURFACE_OR_DEPENDENCY => SERIALIZE
```

Do not create Planner, CI, Documentation, or generic orchestration agents.
Use a read-only Explorer only for meaningfully separable repository discovery.
CI polling is deterministic and is never an Agent.

---

## 4. Large Codex package lifecycle

One Development Package uses one Codex thread, one worktree, and one Goal.

```text
DEVELOPMENT_PACKAGE_FREEZE
-> M0 DETERMINISTIC BOOTSTRAP
-> PLAN_ONLY (NO MUTATION)
-> PACKAGE_BOUNDARY_CHECK
-> PACKAGE_SCOPED GOAL
-> EDIT / FOCUSED TEST / OBSERVE / REPAIR / REPEAT
-> READ_ONLY CODE REVIEW WHEN CHILD IDENTITY IS RUNTIME-VERIFIED
   (OTHERWISE SKIP INTERNAL CHILD; NO FALLBACK)
-> FINAL LOCAL VALIDATION
-> COMMIT / PUSH / DRAFT PR
-> CI_PENDING
```

Plan-only decides implementation order and mechanics. It cannot redefine
product scope, application behavior, architecture authority, protected
actions, or acceptance criteria. A compliant plan records
`PLAN_BOUNDARY_CHECK=PASS` and continues without routine user approval.

The Goal preserves the package finish line across interruptions. It is retired
at terminal package disposition and cannot leak into a materially different
package.

If the surface cannot autonomously transition Plan to Goal, one-handoff
compatibility mode uses one package-scoped Goal whose first mandatory phase is
Plan-only. A new architecture, provider, dependency, security, scope, or
authority decision stops before mutation and returns to Engineering Control.

---

## 5. Deterministic bootstrap and preflight

No material Writer begins without:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
SEMANTIC_READINESS=PASS
```

The controller-bound packet must establish, as applicable:

- live repository/main/Issue or PR/exact base or head;
- role, task class, execution route, allowed and prohibited scope;
- current authority sources and normalized authority assertions;
- acceptance criteria, attack matrix, repair budget, and stop conditions;
- validation commands, platform, authoritative environment, and evidence plan;
- Task Packet hash, governance epoch, preflight binding key, Control Capsule,
  completed-work ledger, and retained gates.

The preflight binding is:

```text
GOVERNANCE_EPOCH
+ TASK_PACKET_HASH
+ EXACT_BASE_OR_HEAD
+ EXECUTION_SURFACE
```

Reuse is allowed only when the exact binding and authority are unchanged.
Fresh canonical identity checks remain mandatory.

For a managed Codex worktree, before semantic model invocation:

```text
FRESHEN / VERIFY CANONICAL REMOTE-TRACKING REF
-> REQUIRE REF == FROZEN EXACT BASE
-> VERIFY BOUND TREE WHEN SUPPLIED
-> CREATE OR REALIGN A CLEAN WORKTREE FROM EXACT BASE
-> REQUIRE WORKTREE HEAD == EXACT BASE
-> REQUIRE WORKTREE CLEAN
-> ONLY THEN START THE SEMANTIC MODEL
```

A stale branch label is never proof. Dirty or ambiguous state fails closed and
must not be silently reset. Clean exact-base realignment is execution-surface
recovery, not semantic repair.

Publication-only GitHub authentication/push/PR/result-egress readiness does
not falsely block semantic start when exact semantic source identity is already
proven.

---

## 6. Context, cache, checkpoint, and resume

Use stable model/tool/instruction prefixes and preserve one coherent thread.
Keep dynamic task data in the mutable tail. Load only the active map, exact
packet/manifest, affected code/tests, and the minimum applicable procedure.
Large logs and full history stay outside model context; inject only bounded
decisive evidence.

```text
NEW_CHAT_NE_NEW_CONTROL_CONTEXT=YES
UNCHANGED_GOVERNANCE_EPOCH_AND_BINDING=>REUSE_ATTESTATION
FULL_HISTORY_OR_GOVERNANCE_RELOAD_BY_DEFAULT=NO
QUALITY_AND_CORRECTNESS_GT_CONTEXT_ECONOMY=YES
```

Rotate a context only when capacity/trust requires it. Before rotation freeze
and verify the Control Capsule plus the running thread/session/workspace.
The user is not responsible for detecting context pressure.

Interruption, quota pause, UI/network stream loss, transport failure, or
publication failure is not semantic task failure. Read durable state first,
resume from the latest exact checkpoint, and never rerun a completed semantic
action merely because output was interrupted.

```text
NO_SILENT_MODEL_EXECUTOR_FALLBACK=YES
NO_HIDDEN_SEMANTIC_RETRY=YES
QUOTA_BOUNDARY_RESUME_NOT_RETRY=YES
CHECKPOINT_RESUME_INSTEAD_OF_REDO=YES
```

Task packets are data. Reusable execution mechanics belong in versioned stable
scripts/skills, not freshly generated per-task programs.

---

## 7. Research and mature-solution rules

Material direction-setting work follows:

```text
INDEPENDENT ANALYSIS
-> EXTERNAL / MATURE EVIDENCE
-> SYNTHESIS / DECISION
```

Record what evidence confirms, modifies, rejects, residual uncertainty, the
selected and rejected routes, and required validation. Research must converge.

When a material research frontier is reached, select exactly one disposition:

```text
ACQUIRE_BEFORE_NEXT_GATE
CAPTURE_CHEAP_OPTIONALITY
PROCEED_WITH_CURRENT_BEST_AND_DEFER
PARK_OR_REJECT
```

Safety, authority, correctness, data-integrity, or causal blockers cannot be
traded away. Otherwise compare expected decision value of information with
total research, delay, and complexity/overfit burden. A data-blocked frontier
does not automatically authorize data engineering.

For material capability decisions classify:

```text
STRATEGY_DIFFERENTIATOR
COMMODITY_INFRASTRUCTURE
THIN_INTEGRATION
```

Project-specific strategy intelligence remains project-owned. Commodity
trading/runtime infrastructure uses a fitting provider-native, official,
standard, or mature maintained external owner by default.

```text
REUSE ACCEPTED CAPABILITY
-> PROVIDER NATIVE
-> STANDARD / OFFICIAL
-> MATURE FULL FRAMEWORK
-> MATURE MODULAR COMPOSITION
-> CONFIGURATION / OFFICIAL EXTENSION
-> THIN ADAPTER
-> UPSTREAM CONTRIBUTION
-> CUSTOM COMMODITY ONLY WITH EXPLICIT CURRENT USER EXCEPTION
```

A fitting mature capability blocks custom rebuild and a second project-owned
implementation. `NO_NEW_DEPENDENCY`, sunk cost, familiarity, or migration
inconvenience is not a simplicity proof. Stage 0 performs no product coding.
A One-Blocker Tiny Spike is allowed only for one unresolved decisive P0
question, one candidate, one bounded nonproduction Writer stage, and no hidden
product implementation or repair chain.

---

## 8. Architecture, continuity, scale, and authority

Global root cause precedes local patch loops. Repeated adjacent fixes, mixed
state, duplicate authority, or new cross-layer failures trigger route-level
reanalysis rather than weakening validation.

For adjacent authoritative layers:

```text
UPSTREAM_ACCEPTED_DOMAIN ⊆ DOWNSTREAM_SUPPORTED_DOMAIN
```

or downstream must map legitimate inputs to an explicit typed semantic result.
Valid admitted input must have a deterministic outcome; contradictory or
authority-invalid input remains fail closed.

For material cross-layer work freeze canonical ownership, prohibited second
caches/queues, transitions, replay/restart/idempotency, freshness/time,
supersession/epoch, and malformed/unauthorized input behavior. Each durable
responsibility has one authority owner.

Prefer:

```text
STABLE NARROW CONTRACT
+ ONE CURRENT IMPLEMENTATION
+ REPLACEABLE POLICY
```

Preserve backward-readable/versioned durable state where practical. Do not
create throwaway seams that force near-term rewrites or speculative generalized
platforms.

Before scale/provider/freshness changes, estimate calls/weights/cadence,
history/database work, latency/freshness, CPU/memory, lifecycle responsiveness,
and realistic production-order magnitude. Tiny fixtures cannot prove
scale-dependent claims.

---

## 9. Verification architecture

Development and verification are one system. Freeze the exact claim and its
authoritative proof surface before implementation.

Use the cheapest decisive layer outward:

```text
G0 PURE UNIT
G1 CONTRACT / DOMAIN
G2 PROPERTY
G3 STATEFUL SEQUENCE
G4 COMPONENT INTEGRATION
G5 PRODUCTION COMPOSITION
G6 CANONICAL INCIDENT CORPUS
G7 REALISTIC SCALE
G8 EXACT RELEASE ARTIFACT SYSTEM TEST
G9 PUBLIC PROVIDER FULL-APPLICATION REHEARSAL
G10 EXACT-HEAD CI + INDEPENDENT REVIEW
G11 TARGET-HOST QUALIFICATION
G12 BOUNDED REAL-MARKET SHADOW
```

A test claims production-path coverage only when it drives the real composition
and authority seams relevant to the claim. Test doubles must satisfy the exact
contract they replace. Capture transient evidence before teardown when teardown
legitimately clears state.

Property/stateful tests cover meaningful valid domains, lifecycle sequences,
reconnect, replay, idempotency, supersession, restore, and shutdown when
applicable. Shrunk/generated failures become deterministic regressions.

```text
CLAIM_BASED_STAGE_SUCCESS=REQUIRED
PROGRESSIVE_REPRESENTATIVE_PROOF=REQUIRED
DETERMINISTIC_AND_REAL_EXTERNAL_PROOF_COMPLEMENT=WHEN_APPLICABLE
FAILED_CLAIM_BLOCKS_OUTWARD_PROMOTION=YES
```

A smaller topology cannot claim semantics it cannot express. Broad PASS/DONE
language cannot overstate unrun or nonrepresentative proof.

### 9.1 Environment fidelity

Freeze canonical commands, platform class, authoritative environment, known
mismatches, local fit, and fallback. Platform-sensitive proof runs on its
authoritative platform; macOS does not replace Linux CI and CI does not replace
a target host for host-specific claims.

Prefer an accepted authoritative remote/provider-native surface when it offers
equal or higher claim fidelity, exact identity, reproducibility, and less human
relay. This preference creates no credential/private-API authority.

---

## 10. CI and failure classification

After exact Draft PR head publication:

```text
WRITER_CHECKPOINT=CI_PENDING
MODEL_MEDIATED_CI_POLLING=PROHIBITED
CI_WAIT_OWNER=GITHUB_OR_DETERMINISTIC_TOOL
RAW_SUCCESS_LOG_INGESTION=PROHIBITED_BY_DEFAULT
```

The deterministic waiter verifies the PR exact head before and after waiting,
reads only required run/job metadata, and emits a compact terminal projection.
All green advances mechanically to `REVIEW_NEEDED` without a semantic status
turn.

Every failed exact-head CI result is classified before retry or mutation:

```text
TRANSIENT_OR_KNOWN_FLAKE
DETERMINISTIC_MECHANICAL
SEMANTIC
INFRASTRUCTURE_OR_TRANSPORT
UNRESOLVED
```

- A known transient may receive at most one same-head rerun.
- A deterministic mechanical source defect receives a narrow proven
  nonsemantic repair and a new exact-head run, not a blind unchanged rerun.
- A semantic failure consumes the frozen semantic repair budget.
- Infrastructure/transport recovery preserves the semantic checkpoint.
- Unresolved failure collects only bounded decisive evidence and wakes
  Engineering Control.

Success logs are not read by default. Failure evidence is limited to the exact
failed run/job/step and the minimum decisive excerpt.

---

## 11. Review and convergence

### 11.1 Codex Code Review

Large Codex packages use a fresh read-only Code Reviewer before final
publication/handoff only when the actual spawned child model and reasoning are
runtime-verifiable against the frozen internal-review route. If that identity
cannot be proven, skip the Codex child reviewer; do not silently inherit or
fall back to the parent/default Sol/High profile. When used, it reviews exact
diff/head for correctness, regression, scope, authority, safety, and missing
decisive tests. It cannot edit and its PASS is not independent acceptance.
Skipping this internal child never skips final Independent Review.

Ordinary in-scope findings return to the same Writer for the bounded repair.
New architecture, security, scope, dependency, authority, or root cause returns
to Engineering Control.

### 11.2 Final independent review

Authority-bearing final Review requires one fresh ordinary ChatGPT context
that did not control or implement the candidate. It is read-only, uses the
current strongest appropriate ordinary ChatGPT model with High or sufficient
high reasoning, and reads exact GitHub head/diff plus exact-head CI.

Its compact Review Manifest contains exact identity, exact changed scope,
frozen acceptance criteria, safety/authority boundaries, decisive evidence
locators, and explicitly untrusted prior conclusions. Full Issue/PR history or
governance reload is not default input.

A Review Result is bound by:

```text
REVIEW_CLASS + TARGET_IDENTITY + CANDIDATE_IDENTITY + EXACT_HEAD_OR_TREE
```

Read before write and consume an existing matching result instead of
duplicating it. A materially changed head requires a new fresh Reviewer.

Precompute `CAN_SUBMIT_NATIVE_REVIEW`:

- `YES`: use native APPROVE / REQUEST_CHANGES as appropriate.
- `NO`: write canonical exact-head review evidence with
  `REVIEW_SUBMISSION_MODE=COMMENT_ONLY`.

`COMMENT_ONLY` preserves evidence when self-approval is forbidden; it is not a
second GitHub identity and does not weaken the review contract.

### 11.3 Repair budget

Default application/design budget:

```text
INITIAL IMPLEMENTATION
+ AT MOST ONE NORMAL CONSOLIDATED REPAIR
+ AT MOST ONE EXPLICITLY AUTHORIZED EXCEPTIONAL NARROW REPAIR
```

No routine Repair 3/4/5. A new root cause, expanded authority/layer, failed
commodity boundary, or exhausted budget triggers holistic replan/replacement.
A Review FAIL becomes a new bounded development task classified through the
same A-D router; there is no special repair-routing taxonomy.

---

## 12. Repository, publication, and generated-command discipline

Normal engineering work:

- never commits directly to `main`;
- never force-pushes or rewrites shared reviewed history;
- uses one bounded branch/worktree scope;
- never commits secrets, credentials, wallets, raw private/account data,
  production DB/log/cache, or real account identifiers;
- never presents simulated/default market/account data as real evidence.

Publication order:

```text
EXACT CANDIDATE
-> APPLICABLE FOCUSED VALIDATION
-> DRAFT PR
-> EXACT-HEAD CI
-> FRESH INDEPENDENT REVIEW
-> USER MARK-READY AUTHORITY
-> USER MERGE AUTHORITY
-> REQUIRED LIVE-MAIN / POST-MERGE VERIFICATION
```

When user-local Git publication is selected for this repository, the mature
route is HTTPS + GitHub CLI browser OAuth + system credential storage +
`gh auth setup-git`. Manual PATs, plaintext credentials, and
`--insecure-storage` are prohibited. If changed paths include
`.github/workflows/**`, the active OAuth credential must explicitly prove the
`workflow` scope before a real push; successful auth/API/read/dry-run checks do
not prove that scope. If GitHub identity, required OAuth scopes, and the exact
local checkpoint are already proven but a real HTTPS push fails with the known
LibreSSL `SSL_ERROR_SYSCALL` class, classify it as transport instability:
never rerun semantic work or weaken/reauthenticate credentials merely to cure
transport. Preserve the exact checkpoint and keep the same execution route for
a small bounded retry before switching surfaces. Idempotent reads normally get
2-3 attempts. A failed write may be retried on the same route only when
canonical evidence proves the prior attempt did not mutate remote state, or
canonical readback proves the target is unchanged and the exact write is
safe/idempotent. If a write may have succeeded, read back first; if mutation
state remains ambiguous and readback is unavailable, fail closed. Force or
history-rewriting writes remain prohibited unless separately and explicitly
authorized. Switch to connected-provider recovery only after the retry budget
is exhausted or the route is proven persistently unusable, when that recovery
surface is available.

Human-executed commands are engineered artifacts. When a local operator route
is genuinely necessary, prefer one safe contiguous paste or a reviewed
file-backed script with a short hash-verify/execute launcher. Prove actual OS,
shell, CLI semantics, privileges, filesystem shape, and evidence return where
they matter. Do not re-encode a long fragile payload as Base64/heredoc/nested
shell and call it file-backed.

Every fail-closed command gate must protect a real invariant. Publication
readiness must not become a false semantic-start gate. After a semantic
checkpoint, repair transport/evidence tails without rerunning semantics.

One generated-command family receives at most one bounded correction; a second
avoidable defect requires holistic regeneration rather than CONT/R3/R4 chains.

---

## 13. Exact release and runtime boundaries

Keep strict separation:

```text
SOURCE + LOCKS
-> EXACT RELEASE ARTIFACT
-> STAGED ARTIFACT TEST
-> PUBLIC-PROVIDER REHEARSAL
-> EXACT-HEAD CI / REVIEW
-> TARGET-HOST QUALIFICATION
-> BOUNDED SHADOW
-> SEPARATELY AUTHORIZED LIVE ACTION
```

Staged non-Git artifacts retain an exact manifest, expected release identity,
selected path set, hashes, sizes, and schema. Persisted-state copying follows
the owning engine's durability semantics; filename convenience never defines
canonical state.

---

## 14. Failure, checkpoint, and terminal truth

After failure classify semantic start/completion, mutation state, safe state,
last checkpoint, resume point, and whether semantic rerun is authorized.
Transport interruption is a separate fault domain and never proves action
failure.

Before any Writer, Reviewer, or executor writes a terminal result or blocker,
fresh-read current canonical GitHub task/PR state. If another surface already
advanced it, write only an idempotent reconciliation.

Whole-task completion is distinct from Writer, CI, Review, publication, or
merge completion. The active task contract determines applicability. Whole-task
completion requires every applicable terminal objective, independent review,
PR disposition, live-main/post-publication verification, linked-task readback,
open/superseded-work sweep, and retained user gate to be observed PASS or
explicitly not applicable. Unproven or pending gates prohibit the words
complete/done.

An umbrella Issue may stay open for a separate stage when the current bounded
contract is terminal. Conversely, an artifact inside the bounded task cannot
be silently omitted from terminal readback.

---

## 15. Protected human gates

No governance, packet, Writer result, CI, Review, or previous approval implies
authority for:

```text
MARK_READY
MERGE
BRANCH_DELETION
DEPLOYMENT
PRODUCTION_HOST_RUNTIME_OR_CLOUD_MUTATION
SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_OR_PRIVATE_API_ACCESS
REAL_NOTIFICATION_WHEN_SEPARATELY_GATED
WALLET_SIGNING_OR_NONCE
EXCHANGE_WRITE
ORDER_SUBMISSION_OR_CANCELLATION
AUTONOMOUS_TRADING
REAL_CAPITAL_ACTION
```

Each requires explicit current user authority. Merge does not authorize
deployment or runtime mutation. Uncertain, stale, gapped, disconnected, or
conflicted mandatory state means no new risk.

---

## 16. Active subordinate procedures and skills

Load only when applicable. The active manifest and Rules Index own exact paths.
Domains include research evidence, mature-solution adoption, generated-command
reliability, local Git/PR closeout, tool onboarding, target-host deployment,
and current Product/Strategy/Operations/Security authority.

Active progressive-disclosure skills:

1. `trade-os-v4-bootstrap`
2. `trade-os-v4-development`
3. `trade-os-v4-ci`
4. `trade-os-v4-review`

Skills provide procedure, not new authority. Old skills remain compatibility
history and are outside the mandatory route unless an exact current task
explicitly invokes one.

---

## 17. Frozen V4 invariants

```text
GITHUB_CANONICAL_SOURCE=YES
ONE_PROJECT_WIDE_ENGINEERING_CONSTITUTION=YES
V4_SOLE_ACTIVE_CONSTITUTION=YES
CONTROL_CAPSULE_REQUIRED=YES
ACTIVE_STATE_MINIMALITY_GATE=REQUIRED
COMPLETED_WORK_LEDGER=REQUIRED
GOVERNANCE_EPOCH_ATTESTATION=REQUIRED
BOUND_PREFLIGHT_REUSE_ONLY_WHEN_BINDING_UNCHANGED=YES
MATERIAL_WRITER_REQUIRES_BOTH_PREFLIGHT_PASS_VALUES=YES
CODEX_PRE_MODEL_EXACT_BASE_CLEAN_WORKTREE_GATE=REQUIRED
TASK_PACKET_IS_DATA_NOT_EXECUTION_PROGRAM=YES
STABLE_SEMANTIC_RUNNER_DEFAULT=YES
EXECUTION_ROUTE_SET=A_DETERMINISTIC|B_CHATGPT_BOUNDED|C_CODEX_LARGE|D_CONTROL
EXECUTOR_AND_PLAN_GOAL_DECISIONS_ARE_INTERNAL=YES
PLAN_CANNOT_CHANGE_FROZEN_SCOPE_AUTHORITY_ACCEPTANCE=YES
ONE_PACKAGE_ONE_THREAD_ONE_GOAL=YES
ABILITY_BOUNDARY_CONTINUATION=REQUIRED
ROUTINE_USER_CONFIRMATION=PROHIBITED
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
NO_SILENT_MODEL_EXECUTOR_REASONING_SURFACE_CHANGE=YES
SUBAGENT_MODEL_REASONING_MUST_BE_RUNTIME_VERIFIABLE=YES
UNVERIFIED_SUBAGENT_MODEL_INHERITANCE=PROHIBITED
FALLBACK_TO_PARENT_SOL_HIGH=PROHIBITED
SILENT_REVIEWER_PROFILE_FALLBACK=PROHIBITED
NO_HIDDEN_SEMANTIC_RETRY=YES
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
MATERIAL_WRITER_REQUIRES_PROJECT_RULESET_PREFLIGHT_PASS=YES
MATERIAL_WRITER_REQUIRES_ENGINEERING_PREFLIGHT_PASS=YES
INDEPENDENT_ANALYSIS_BEFORE_EXTERNAL_CONCLUSIONS=YES
EXTERNAL_MATURE_EVIDENCE_FOR_MATERIAL_DIRECTION_SETTING=YES
SYNTHESIS_BEFORE_ROUTE_FREEZE=YES
RESEARCH_FRONTIER_REQUIRES_INVESTMENT_DISPOSITION=YES
DATA_BLOCKED_FRONTIER_DOES_NOT_AUTO_AUTHORIZE_ENGINEERING=YES
RESEARCH_INVESTMENT_BY_EXPECTED_DECISION_VALUE_MINUS_TOTAL_BURDEN=YES
SAFETY_CORRECTNESS_CAUSAL_BLOCKERS_OVERRIDE_RESEARCH_ROI_DEFER=YES
RESEARCH_INVESTMENT_DISPOSITIONS=ACQUIRE|CAPTURE_OPTIONALITY|PROCEED_DEFER|PARK_REJECT
SIMPLEST_EFFECTIVE_VALIDATED_STRATEGY_PREFERRED=YES
STRATEGY_DISCRETIONARY_ECONOMIC_COMPLEXITY_REQUIRES_MATERIAL_INCREMENTAL_OOS_OR_FORWARD_VALUE=YES
HISTORICAL_ADAPTIVITY_AND_TRIAL_COUNT_MUST_BE_RECORDED=YES
REPEATED_PRE_FORWARD_RESEARCH_EXPANSION_REQUIRES_FRESH_INVESTMENT_GATE=YES
FREEZE_STRATEGY_VERSION_BEFORE_FORWARD_EVIDENCE=YES
ANY_MATERIAL_STRATEGY_SEMANTIC_OR_EVIDENCE_AFFECTING_CHANGE_RESETS_FORWARD_EVIDENCE_CLOCK=YES
NO_RETROACTIVE_FORWARD_EVIDENCE_CREDIT_AFTER_MATERIAL_VERSION_CHANGE=YES
PRE_WRITER_GO_NO_GO_EXPERIMENT=WHEN_CHEAP_SAFE_AND_DECISIVE
MATURE_SOLUTION_FIRST=YES
MATURE_CAPABILITY_NO_REBUILD_GATE=REQUIRED
CAPABILITY_CLASSIFICATION_BEFORE_COMMODITY_WRITER=REQUIRED
STRATEGY_DECISION_ENGINE_PROJECT_OWNED=YES
TRADING_INFRASTRUCTURE_ENGINE_MATURE_EXTERNAL_OWNER_BY_DEFAULT=YES
FITTING_MATURE_COMMODITY_CAPABILITY_BLOCKS_CUSTOM_REBUILD=YES
SECOND_PROJECT_OWNED_COMMODITY_IMPLEMENTATION=PROHIBITED_WHEN_FITTING_OWNER_EXISTS
ENGINEERING_CONTROL_OR_WRITER_SELF_AUTHORIZED_CUSTOM_COMMODITY_BUILD=PROHIBITED
CUSTOM_COMMODITY_EXCEPTION_REQUIRES_EXPLICIT_CURRENT_USER_AUTHORITY=YES
STAGE_0_NO_PRODUCT_CODE_MATURE_SOLUTION_AUDIT=REQUIRED_WHEN_APPLICABLE
ONE_BLOCKER_TINY_SPIKE_ONLY=YES_WHEN_EXTERNAL_FEASIBILITY_UNRESOLVED
MULTIPLE_FULL_PROTOTYPES_FOR_MATURE_SELECTION=DISFAVORED
INVASIVE_MATURE_FRAMEWORK_FORK=PROHIBITED_BY_DEFAULT
MODULAR_MATURE_COMPOSITION=ALLOWED_WITH_ONE_AUTHORITY_OWNER_PER_RESPONSIBILITY
OVERLAPPING_DURABLE_STATE_OMS_POSITION_RISK_AUTHORITY=PROHIBITED
LEGACY_KEEP_CUSTOM_DECISION_EXPIRY_TRIGGERS=REQUIRED
NO_NEW_DEPENDENCY_IS_NOT_SIMPLICITY_PASS=YES
SIMPLICITY_BY_TOTAL_ENGINEERING_BURDEN=YES
CUSTOM_COMMODITY_BUILD_REQUIRES_EXPLICIT_CURRENT_USER_EXCEPTION=YES
GLOBAL_ROOT_CAUSE_BEFORE_LOCAL_PATCH_LOOPS=YES
CROSS_LAYER_CONTRACT_CLOSURE=REQUIRED
ADMITTED_INPUT_TOTALITY=REQUIRED
STABLE_NARROW_SEAMS_AND_CONTINUITY=REQUIRED
PROVIDER_SCALE_FRESHNESS_GATE=WHEN_APPLICABLE
COMPLETE_TASK_PACKET_BEFORE_EXECUTION=YES
LOSSLESS_HANDOFF=REQUIRED_FOR_AUTHORITY_BEARING_TASKS
INTERMEDIARY_PARAPHRASE_AS_DOWNSTREAM_AUTHORITY=PROHIBITED
RAW_EVIDENCE_OVERRIDES_INTERMEDIARY_SUMMARY=YES
ACTIVE_TASK_OWNERSHIP_UNTIL_TERMINAL_DISPOSITION=YES
EXECUTION_CLASSIFICATION_BEFORE_WRITER_DISPATCH=REQUIRED
SMALL_FROZEN_BOUNDED_SEMANTIC_DEFAULT_ORDINARY_CHATGPT_WRITER=YES
OPEN_MATERIAL_SEMANTIC_CODEX_DEFAULT_WHEN_AVAILABLE_AND_ALLOWED=YES
HIGH_CONSEQUENCE_AMBIGUOUS_STRONGEST_APPROPRIATE_ROUTE=YES
REVIEW_FAIL_CREATES_NEW_TASK_THEN_UNIVERSAL_CLASSIFICATION=YES
CODEX_DESKTOP_PRE_MODEL_EXACT_BASE_WORKTREE_GATE=REQUIRED
TERMINAL_RESULT_EGRESS_FRESH_CANONICAL_READ=REQUIRED
T4_ROUTINE_DEFAULT_FRESH_ORDINARY_CHATGPT=YES
DEVELOPMENT_AND_VERIFICATION_DESIGNED_TOGETHER=YES
CLAIM_BASED_STAGE_SUCCESS=REQUIRED
PROGRESSIVE_REPRESENTATIVE_PROOF=REQUIRED
ONE_MATERIAL_COMPLEXITY_DIMENSION_AT_A_TIME_WHEN_PRACTICAL=YES
FAILED_STAGE_CLAIM_MUST_BE_RERUN_BEFORE_PROMOTION=YES
BROAD_PASS_CANNOT_OVERSTATE_UNPROVEN_CLAIMS=YES
PRODUCTION_PATH_FIDELITY=REQUIRED
HARNESS_BOUNDARY_CONTRACT_FIDELITY=REQUIRED
BALANCED_G0_TO_G12_VERIFICATION=REQUIRED_WHEN_APPLICABLE
INCIDENT_TO_INVARIANT_CONVERGENCE=REQUIRED
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=YES
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY=REQUIRED
VALIDATION_ENVIRONMENT_MUST_MATCH_CLAIM=YES
PLATFORM_SENSITIVE_VALIDATION_ON_WRONG_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
AUTHORITATIVE_REMOTE_EXECUTION_PREFERRED_WHEN_EQUAL_OR_HIGHER_FIDELITY=YES
USER_LOCAL_WORKSTATION_NOT_DEFAULT_FOR_CI_OR_LINUX_PROOF=YES
REMOTE_EXECUTION_CREDENTIAL_AUTHORITY_MUST_BE_EXPLICIT=YES
REMOTE_EXECUTION_PRESERVES_FROZEN_EXECUTOR_MODEL_TOOL_AUTHORITY=REQUIRED
CANONICAL_REMOTE_REF_MUST_NOT_REQUIRE_REDUNDANT_LOCAL_OBJECT_PREEXISTENCE=YES
EXACT_RELEASE_STAGED_ARTIFACT_SEPARATION=REQUIRED
PERSISTED_STATE_COPY_MUST_FOLLOW_COMPONENT_DURABILITY_SEMANTICS=YES
MACOS_OPERATOR_ONE_PASTE_DEFAULT=YES_WHEN_LOCAL_OPERATOR_ROUTE_REQUIRED
KNOWN_COMMAND_INCIDENT_NONREGRESSION_GATE=REQUIRED
LOCAL_GIT_AUTH_ROUTE=HTTPS_GH_BROWSER_OAUTH_SYSTEM_KEYRING_SETUP_GIT
WORKFLOW_PATH_MUTATION_REQUIRES_VERIFIED_WORKFLOW_SCOPE=YES
AUTH_API_READ_DRY_RUN_NE_WORKFLOW_SCOPE_PROOF=YES
TRANSIENT_NETWORK_TLS_HTTP_KEEP_SAME_ROUTE_DEFAULT=YES
IDEMPOTENT_READ_TRANSPORT_RETRY_BUDGET=2_TO_3
SAFE_IDEMPOTENT_WRITE_TRANSPORT_RETRY_REQUIRES_NO_MUTATION_OR_UNCHANGED_READBACK=YES
AMBIGUOUS_MUTATION_WITHOUT_READBACK_FAIL_CLOSED=YES
PREMATURE_EXECUTION_SURFACE_SWITCH_ON_TRANSIENT_TRANSPORT=PROHIBITED
KNOWN_LIBRESSL_PUSH_FAILURE_PRESERVES_CHECKPOINT=YES
KNOWN_LIBRESSL_PUSH_FAILURE_LOCAL_RETRY=BOUNDED_WHEN_MUTATION_STATE_SAFE
KNOWN_LIBRESSL_PUSH_FAILURE_CONNECTED_PROVIDER_RECOVERY=AFTER_RETRY_BUDGET_OR_PERSISTENT_FAILURE_WHEN_AVAILABLE
OPERATOR_TRANSPORT_MUST_REDUCE_COMPLEXITY_NOT_REENCODE_IT=YES
INTERACTIVE_SHELL_PARSE_ASSUMPTIONS_MUST_BE_PROVEN_OR_AVOIDED=YES
CLI_INVOCATION_CONTRACT_PROOF=REQUIRED_FOR_MATERIAL_VERSIONED_CLI
MODEL_EXECUTOR_AND_OUTER_LAUNCHER_STDIN_SHARING=PROHIBITED
ALLOWLIST_MEANS_CHANGED_PATHS_SUBSET_UNLESS_SEMANTIC_MINIMUM_EXPLICIT=YES
POST_WRITER_EVIDENCE_CHECKPOINT_BEFORE_NONDECISIVE_TAIL=REQUIRED
NO_SEMANTIC_RERUN_AFTER_PRESERVED_COMPLETED_CHECKPOINT=YES
GENERATED_COMMAND_SECOND_AVOIDABLE_DEFECT_TRIGGERS_HOLISTIC_REGENERATION=YES
APPLICATION_NORMAL_REPAIR_LIMIT=1
APPLICATION_EXCEPTIONAL_REPAIR_LIMIT=1
REPAIR_3_PLUS_SAME_ROUTE=PROHIBITED
MODEL_MEDIATED_CI_POLLING=PROHIBITED
CI_FAILURE_CLASSIFICATION_BEFORE_REPAIR=REQUIRED
KNOWN_TRANSIENT_SAME_HEAD_RERUN_MAX=1
RAW_SUCCESS_LOG_INGESTION=PROHIBITED_BY_DEFAULT
CODE_REVIEW_READ_ONLY_NOT_AUTHORITY_ACCEPTANCE=YES
FINAL_INDEPENDENT_REVIEW_FRESH_ORDINARY_CHATGPT=YES
COMMENT_ONLY_REVIEW_FALLBACK=REQUIRED_WHEN_NATIVE_SELF_APPROVAL_UNAVAILABLE
REVIEW_RESULT_EGRESS_IDEMPOTENCY=REQUIRED
REPAIRED_HEAD_REQUIRES_NEW_FRESH_INDEPENDENT_REVIEWER=YES
WRITER_PASS_NE_INDEPENDENT_ACCEPTANCE=YES
NO_DIRECT_NORMAL_COMMIT_TO_MAIN=YES
NO_FORCE_PUSH_AFTER_REVIEW=YES
EXACT_ARTIFACT_EXACT_HEAD_CI_INDEPENDENT_REVIEW=WHEN_APPLICABLE
EXACT_ARTIFACT_AND_EXACT_HEAD_REVIEW=REQUIRED_WHEN_APPLICABLE
T4_FINAL_REVIEW_INDEPENDENT=YES
CHECKPOINT_RESUME_INSTEAD_OF_REDO=YES
TRANSPORT_INTERRUPTION_NE_TASK_FAILURE=YES
FALSE_SAFE_STOP_GATE=PROHIBITED
PROTECTED_ACTIONS_REQUIRE_EXPLICIT_CURRENT_USER_AUTHORITY=YES
MARK_READY_MERGE_DEPLOY_RUNTIME_CREDENTIAL_ACCOUNT_EXCHANGE=SEPARATE_CURRENT_USER_AUTHORITY
```

---

## 18. Governance maintenance and supersession

Durable project-wide lessons update this constitution. Task-specific procedure,
deployment mechanics, model/tool details, and incident history remain in their
narrow lifecycle unless they yield a reusable project-wide invariant.

Material V4 changes require independent review before merge. Keep `AGENTS.md`,
the active manifest, and the Rules Index compact and synchronized.

As of V4 activation:

- Unified Engineering Governance V2 is historical/superseded source material;
- Engineering Executor Router V2 is historical/superseded routing rationale;
- old executor/model profiles and workflow proposals are historical or
  task-conditional as classified by the active manifest;
- the Mandatory Engineering Preflight remains an active checklist derived from
  V4, not a competing constitution;
- narrow procedures remain subordinate to V4;
- old skills are outside the mandatory active route.

No historical file may override V4.
