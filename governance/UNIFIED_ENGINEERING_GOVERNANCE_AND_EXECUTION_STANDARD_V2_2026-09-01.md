# Trader Assist / Trade OS — Unified Engineering Governance and Execution Standard V2

**Status:** CANONICAL GOVERNANCE CANDIDATE  
**Effective date:** 2026-09-01  
**Repository:** `woshixiong/trader-assist-v0`  
**Authority intent:** on independent acceptance and merge, this file becomes the **single project-wide normative engineering ruleset**. Task-specific Product / Strategy / Operations / Security authority and narrow executor/tool/deployment contracts may be stricter in their own domain, but they must not become competing engineering constitutions.

This document consolidates the durable engineering rules previously spread across the Unified V1 standard, the mandatory preflight rule, the research/evidence method, Issue #139 holistic verification work, generated-command reliability incidents, tool-onboarding lessons and accepted workflow practice.

It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, wallet/signing, exchange-write, order-submission or autonomous-trading authority.

---

## 1. Governance architecture and precedence

### 1.1 One normative engineering constitution

Project-wide engineering rules have one normative owner: this document.

The documentation architecture is:

```text
AGENTS.md
= compact entry map

PROJECT_RULES_INDEX.md
= navigation / active-authority index

UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md
= sole project-wide normative engineering constitution

MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md
= executable checklist / record derived from this constitution

PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md
= task-conditional research procedure / examples; no competing authority

GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md
= task-conditional operator-command procedure / incident catalogue; no competing authority

executor / model / tool / FinalShell / Hermes profiles
= narrow task-conditional contracts after route selection
```

Maps and checklists point to rules; they do not redefine them. A specialized contract may add stricter requirements for its exact executor, deployment surface or safety domain, but cannot weaken this file without an explicit governance change.

### 1.2 Source of truth

GitHub is the canonical engineering source of truth.

Before material work, resolve from live GitHub as applicable:

```text
LIVE_REPOSITORY
LIVE_MAIN_SHA
ACTIVE_ISSUE_OR_PR
EXACT_BASE / EXACT_HEAD
EXACT_CHANGED_PATHS
EXACT_HEAD_CI
CURRENT_PRODUCT_STRATEGY_OPERATIONS_SECURITY_AUTHORITY
```

Actual code, exact diffs, accepted artifacts and current GitHub objects override stale chat summaries, old prompts, old PR bodies and remembered SHAs.

### 1.3 Precedence

When rules appear to conflict, use:

1. explicit current user authority and safety boundary;
2. current accepted Product / Strategy / Security / Operations authority for the narrow domain;
3. this Unified Engineering Governance V2;
4. the current material-task preflight record and frozen Task Packet;
5. applicable narrow executor/tool/deployment contracts;
6. historical governance, superseded ADR-like decisions and chat narrative as rationale only.

A less strict rule never weakens a stricter authority or safety requirement.

---

## 2. Universal engineering objective

Optimize for **validated useful progress per unit of total engineering effort**.

Order of preference:

```text
REAL SAFETY / AUTHORITY CORRECTNESS
-> ROOT-CAUSE CORRECTNESS
-> PRODUCT / TRADING / DATA USEFULNESS
-> SIMPLE MATURE REUSABLE ROUTE
-> CONTINUITY / REPLACEABILITY
-> VALIDATION QUALITY
-> LOW HUMAN RELAY / LOW REWORK
-> TOKEN / QUOTA / WALL-CLOCK EFFICIENCY
-> OPTIONAL SOPHISTICATION
```

Free, cheap, fashionable or technically interesting solutions never override correctness or fit.

Total engineering burden includes implementation, tests, independent review, CI/release, operator actions, model/token cost, debugging/evidence, maintenance, recovery, migration and future replacement cost.

---

## 3. Mandatory end-to-end workflow

For material engineering work use this sequence:

```text
LOAD LIVE STATE + CANONICAL RULES
-> CLASSIFY TASK / AUTHORITY / CAPABILITY
-> INDEPENDENT ANALYSIS
-> EXTERNAL / MATURE-SOLUTION EVIDENCE WHEN DIRECTION-SETTING
-> SYNTHESIS / ROUTE DECISION
-> GLOBAL ARCHITECTURE + CONTRACT + CONTINUITY PREFLIGHT
-> SCALE / PROVIDER / FRESHNESS PREFLIGHT WHEN APPLICABLE
-> VERIFICATION + VALIDATION-ENVIRONMENT PLAN
-> FREEZE ATTACK MATRIX / REPAIR BUDGET / TASK PACKET
-> ONE COHERENT WRITER STAGE
-> CHEAPEST DECISIVE VALIDATION OUTWARD
-> EXACT ARTIFACT / EXACT HEAD
-> AUTHORITATIVE CI / ENVIRONMENT-SPECIFIC PROOF
-> INDEPENDENT REVIEW
-> BOUNDED REPAIR OR REPLAN
-> SEPARATE USER PUBLICATION / DEPLOYMENT / RUNTIME GATES
-> INCIDENT / LESSON CAPTURE
```

Every bounded task ends in an explicit disposition:

```text
PROCEED
PASS_TO_PUBLICATION
REPAIR
REPLAN
DEFER
REPLACE
MERGED
SAFE_STOP
CANCELLED
```

An intermediate test, CI or Reviewer PASS is not task completion unless the active task contract explicitly defines it as terminal.

---

## 4. Task classification and mandatory preflight

### 4.1 Material vs mechanical

A task is MATERIAL when it creates or changes a substantive decision involving architecture, authority, provider, persistence, lifecycle, concurrency, recovery, scale, security, release semantics, model/tool route, cross-layer contract or meaningful product/strategy behavior.

Purely mechanical exact-state work may use a shortened preflight. If mechanical work exposes a new material choice, reclassify immediately.

### 4.2 Required gates

No material Writer implementation begins until:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

The preflight must establish, where applicable:

```text
LIVE_REPO / MAIN / ISSUE_OR_PR / START_HEAD
ROLE / TASK_CLASS / USER_AUTHORITY_REQUIRED_NOW
ROOT_CAUSE_LEVEL
AFFECTED_AUTHORITIES
FROZEN_INVARIANTS
CURRENT_ROUTE
MATURE_ALTERNATIVES
CURRENT_NEED / NEXT_EXPECTED_STAGE
STABLE_INTERFACES / STABLE_AUTHORITIES
REPLACEABLE_IMPLEMENTATION_SEAMS
PROVIDER_SCALE_FRESHNESS_BUDGET
ATTACK_MATRIX
CANONICAL_VALIDATION_COMMANDS
VALIDATION_PLATFORM_CLASS
AUTHORITATIVE_VALIDATION_ENVIRONMENT
KNOWN_ENVIRONMENT_MISMATCHES
FALLBACK_VALIDATION_SURFACE
EXACT_RELEASE_VERIFICATION_PLAN
EVIDENCE_CHECKPOINT_PLAN
WRITER_SCOPE / PROHIBITED_SCOPE
REPAIR_STAGE / STOP_CONDITION
```

`NOT_APPLICABLE` is explicit; unresolved applicable fields prohibit Writer dispatch.

---

## 5. Research, evidence and decision method

Material direction-setting work uses a strict three-stage method.

### Phase 1 — independent analysis first

Before reading external conclusions, establish from project facts and first principles:

- exact problem and user objective;
- facts, assumptions and unknowns;
- causal/mechanical model;
- decision criteria and constraints;
- candidate routes;
- expected benefits, failure modes and trade-offs;
- evidence that could confirm, weaken or falsify the preliminary view.

Preserve a short pre-research position for material decisions.

### Phase 2 — external evidence and mature solutions

Then consult the strongest relevant evidence, prioritizing:

1. official specifications, provider docs, first-party source repositories;
2. primary research, inspectable data and reproducible benchmarks;
3. mature maintained frameworks and validated production cases/postmortems;
4. high-quality independent technical analysis;
5. community anecdotes only as supplemental evidence.

Search for competing approaches, limitations, negative cases and disconfirming evidence. Check freshness when it matters.

### Phase 3 — synthesis and route freeze

Explicitly record:

```text
WHAT_EXTERNAL_EVIDENCE_CONFIRMS
WHAT_IT_MODIFIES
WHAT_IT_REJECTS
RESIDUAL_UNCERTAINTY
REJECTED_ROUTES_AND_WHY
SELECTED_ROUTE_AND_PROJECT_FIT
VALIDATION_OR_EXPERIMENT_REQUIRED
```

Research must converge to a decision. Endless research around the same failed design is prohibited.

---

## 6. Mature-solution-first, simplicity and build-vs-buy

For nontrivial commodity capability use this order:

```text
REUSE_ACCEPTED_PROJECT_CAPABILITY
-> PROVIDER_NATIVE
-> STANDARD / OFFICIAL
-> MATURE MAINTAINED EXTERNAL
-> THIN PROJECT ADAPTER
-> SMALL PROJECT-SPECIFIC LOGIC
-> CUSTOM COMMODITY INFRASTRUCTURE LAST RESORT
```

Commodity infrastructure includes generic orchestration, scheduling, transport, deployment, observability, persistence tooling and workflow plumbing. Project-specific trading/domain semantics remain valid project-owned engineering value.

A fitting mature solution prohibits an unnecessary custom build. Custom infrastructure requires concrete blocking fit gaps and a positive total-value case. Sunk cost is never justification.

Prefer the simplest route that preserves safety, authority, correctness, recovery and continuity. Do not build institution-grade infrastructure for a rare bounded task.

---

## 7. Architecture, authority and cross-layer contract rules

### 7.1 Global root cause before local patch loops

Repeated adjacent-layer fixes, growing special cases, mixed-state failures, duplicate authority conflicts or repeated Reviewer discoveries trigger:

```text
STOP LOCAL PATCHING
-> MODEL GLOBAL STATE / AUTHORITY / CONTRACT
-> RE-RUN RESEARCH + SIMPLICITY + CONTINUITY GATES
-> REPLAN OR REPLACE THE FAILED RESPONSIBILITY BOUNDARY
```

When strict immutable authority correctly exposes duplicate/conflicting work, fix the duplicate work; never weaken authority validation merely to silence the conflict.

### 7.2 Cross-layer contract closure

For adjacent authoritative layers:

```text
UPSTREAM_ACCEPTED_DOMAIN ⊆ DOWNSTREAM_SUPPORTED_DOMAIN
```

or the downstream owner must explicitly map legitimate admitted states to a typed semantic result such as:

```text
NO_ACTION
DEFER
UNAVAILABLE
DATA_INVALID
OWNER_LEVEL_BOUNDED_RETRY
```

Incidental arithmetic/parsing/assertion exceptions are not policy.

### 7.3 Admitted-input totality

Every legitimate provider/contract-admitted input must yield a deterministic typed outcome. Truly contradictory, corrupt or authority-invalid input remains fail-closed.

Strict helper functions may retain narrow preconditions when their owning layer correctly maps valid outer-domain cases before invoking them.

### 7.4 Authority model

For material cross-layer work freeze:

- canonical source of truth for each state;
- prohibited second caches/queues/authorities;
- state transitions and precedence;
- restart/replay/reopen semantics;
- idempotency/duplicate behavior;
- freshness/time boundaries;
- supersession/epoch semantics;
- unauthorized/malformed input behavior.

---

## 8. Continuity-first development

Every material implementation must consider both the current bounded need and the next expected stage.

Record:

```text
CURRENT_BOUNDED_NEED
NEXT_EXPECTED_STAGE
STABLE_AUTHORITIES
STABLE_INTERFACES
REPLACEABLE_IMPLEMENTATION_SEAMS
TUNING_PARAMETERS
PERSISTED_REPRESENTATION_VERSIONING
KNOWN_CHANGE_AMPLIFICATION_HOTSPOTS
MIGRATION_OR_LOCKIN_RISK
```

Prefer:

```text
STABLE NARROW CONTRACT
+ ONE CURRENT IMPLEMENTATION
+ REPLACEABLE POLICY
```

Avoid both throwaway shortcuts that force near-term rewrites and speculative generalized platforms for hypothetical future needs.

Do not split modules merely because they are large. A large integration hotspot triggers seam-extraction review when a new unrelated responsibility would otherwise increase change amplification.

Preserve backward-readable/versioned durable state when practical. Migrate incrementally behind stable seams rather than big-bang replacement.

---

## 9. Scale, provider and freshness

Before first release or a material change to market count, history depth, cadence, retry/confirmation count, REST/WS use, concurrency, database workload or cohort size, calculate the relevant order-of-magnitude budget.

At minimum where applicable:

```text
market_count × calls_per_market × provider_weight × cadence
market_count × history_points × database_operations
```

Estimate or measure provider headroom, p50/p95/worst-case completion/freshness latency, CPU/memory/database load, event-loop/shutdown responsiveness and the intended trading/scanner freshness SLA.

Tiny-fixture correctness is insufficient for scale-dependent behavior. Include a realistic-order-of-magnitude acceptance test when production scale materially differs.

Do not respond by building a generic capacity platform unless evidence requires one.

---

## 10. Writer stage, Task Packet and active ownership

### 10.1 One coherent Writer

```text
PARALLELIZE INDEPENDENT WORK
SERIALIZE SHARED AUTHORITY
ONE_PRIMARY_WRITER_PER_COHERENT_SHARED_AUTHORITY_STAGE=YES
```

Do not create competing Writers against the same durable truth or release branch. Split only at real contract, authority, worktree or independence boundaries.

### 10.2 Complete Task Packet

Before execution freeze one complete self-contained packet containing as applicable:

```text
ROLE / MODE / TASK_ID
REPOSITORY / BASE / HEAD / BRANCH / WORKTREE
OBJECTIVE / ROOT_CAUSE
CURRENT_AUTHORITIES / FROZEN_INVARIANTS
ALLOWED_FILES / PROHIBITED_SCOPE
REQUIRED_BEHAVIOR / MUST_REMAIN_BEHAVIOR
CONTINUITY / SCALE REQUIREMENTS
ATTACK_MATRIX
CANONICAL_TEST / LINT / TYPE / COMPILE COMMANDS
VALIDATION_ENVIRONMENT
COMMIT / PUSH AUTHORITY
REVIEW REQUIREMENT
REPAIR_STAGE / SAFE_STOP CONDITIONS
OUTPUT CONTRACT
FINAL_USER_AUTHORITY_BOUNDARY
```

If a new architecture invariant, provider constraint, authority boundary or major attack case is discovered before execution, regenerate one complete replacement packet. Architecture-critical prompt addenda assembled by the user are prohibited.

### 10.3 Active task ownership

The current control/orchestration role owns the bounded task until terminal disposition or explicit acknowledged handoff.

At intermediate gates it must execute every safe authorized next action, prepare the minimum blocked next step, minimize user relay and stop only the specific unauthorized/external action. A blocked action does not abandon the task.

The user is not the routine Writer/CI/Reviewer information bus when exact evidence can be carried directly.

### 10.4 Lossless authority-bearing handoff

Authoritative handoffs must preserve exact meaning, authority and control fields.

Do not use this as the execution-authority path when the transformation could change scope, permissions, acceptance criteria, stop conditions, route, executor or authority:

```text
AUTHORITATIVE TASK
-> INTERMEDIARY SUMMARY / PARAPHRASE
-> DOWNSTREAM EXECUTOR
```

Prefer a lossless propagation path:

```text
EXACT TASK PACKET OR EXACT IMMUTABLE POINTER
+ INTEGRITY IDENTITY (HASH / EXACT SHA WHEN APPLICABLE)
-> DOWNSTREAM READS THE EXACT AUTHORITATIVE PAYLOAD
-> IDENTITY / AUTHORITY ACKNOWLEDGEMENT
-> EXECUTION
-> RAW EVIDENCE RETURN
```

An intermediary summary may improve readability or navigation, but it is not a substitute downstream execution authority when any authoritative field could be changed, omitted or weakened. The exact packet, immutable pointer and raw evidence remain authoritative over intermediary summaries or paraphrases.

Where a selected specialized operator/handoff contract is stricter, such as a lossless task-packet schema, the stricter contract additionally applies and may not weaken this project-wide rule.

---

## 11. Model/executor/tool routing — general rules

Detailed model capabilities and current model names live in task-conditional Router/profile files; this constitution owns the durable routing principles.

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

Where exposed, record actual executor/provider/model/reasoning/tool/session identity.

Permanent rules:

```text
QUALITY_FIRST=YES
USER_MANUAL_OVERRIDE=ALWAYS_AVAILABLE
SILENT_SUBSTITUTION_OR_FALLBACK=PROHIBITED
UNAUTHORIZED_RETRY_OR_RESUME=PROHIBITED
REQUESTED_VS_ACTUAL_REQUIRED_IDENTITY_MISMATCH=ROUTER_INCIDENT
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
WRITER_SELF_PASS_IS_NOT_INDEPENDENT_ACCEPTANCE
T4_DEFAULT=NEW_INDEPENDENT_STRONGEST_APPROPRIATE_CHATGPT_WINDOW
```

Quota, points, free availability and wall-clock time are routing inputs, never authority to lower required quality.

A Router incident fails closed, prohibits automatic rerun and produces one complete Tooling Control escalation record; the user is not asked to diagnose raw model logs.

### Tool onboarding

A new engineering executor/operator/orchestrator or material tool-configuration change requires:

```text
BOUNDED_CANDIDATE
-> EXACT CONFIG / ARTIFACT IDENTITY
-> REPRESENTATIVE CAPABILITY + SAFETY EVIDENCE
-> SEPARATE INDEPENDENT REVIEW
-> USER ACTIVATION / PUBLICATION AUTHORITY
-> FIRST REAL TASK
```

Installed/free/popular does not equal accepted infrastructure. Multi-step automation must be checkpointed and human-recoverable; hidden semantic retries are prohibited.

---

## 12. Verification architecture — development and testing as one system

Testing is not a downstream ceremony. The implementation route and verification route must be designed together from the same contracts and authority topology.

### 12.1 Production-path fidelity

A test may claim production-path coverage only when it drives the real application composition and authority seams relevant to the claim. A fake substitute that bypasses the boundary under test does not prove that boundary.

### 12.2 Balanced verification portfolio

Use the cheapest decisive layer outward:

```text
G0  PURE_UNIT
G1  CONTRACT_DOMAIN
G2  PROPERTY_BASED
G3  STATEFUL_SEQUENCE
G4  COMPONENT_INTEGRATION
G5  PRODUCTION_COMPOSITION
G6  CANONICAL_INCIDENT_CORPUS
G7  REALISTIC_SCALE
G8  EXACT_RELEASE_ARTIFACT_SYSTEM_TEST
G9  PUBLIC_PROVIDER_FULL_APPLICATION_REHEARSAL
G10 EXACT_HEAD_CI_AND_INDEPENDENT_T4
G11 TARGET_HOST_ENVIRONMENT_QUALIFICATION
G12 BOUNDED_REAL_MARKET_SHADOW_SOAK
```

Labels are conceptual unless a task/runbook adopts them, but responsibilities remain distinct.

Rules:

- cheap deterministic gates catch semantic defects before expensive host runs;
- target-host qualification must not be the first meaningful execution of core application semantics when a safer rehearsal exists;
- canary/Shadow supplements deterministic tests and never replaces them;
- public-provider rehearsal uses public/read-only data with no account/private API, wallet/signing or exchange write;
- exact-head CI is authoritative for the CI platform; local platform mismatches do not override it.

### 12.3 Property/stateful tests

Use property-based tests for meaningful valid domains such as zero/flat/degenerate-but-valid data, denominator boundaries, numeric extremes inside contract, arbitrary alignment/prefix phases and serialization/restore equivalence.

Use stateful testing for bounded lifecycle models such as startup/activation, reconnect, provider recovery, duplicate/idempotency, successor/epoch transition, restart/reopen/reconcile and shutdown/interruption.

Generated/shrunk failures become deterministic regression examples. Correctness must not depend on random rediscovery or one seed.

Stateful testing is not permission to build a second application inside the test suite.

### 12.4 Canonical incident corpus

For material historical incidents preserve:

```text
INCIDENT_ID
OBSERVED_HIGH_LEVEL_FAILURE
LOWEST_REPRODUCIBLE_CONTRACT
GENERALIZED_INVARIANT
PRODUCTION_COMPOSITION_SCENARIO
RELEASE_OR_HOST_RELEVANCE
FIXED_REGRESSION_ID
```

A high-stack incident should converge:

```text
INCIDENT
-> LOWEST DECISIVE REPRODUCTION
-> GENERALIZED INVARIANT / PROPERTY
-> RELEVANT PRODUCTION-COMPOSITION REGRESSION
-> INCIDENT RECORD
```

The incident corpus is evidence/history, not a second architecture authority.

---

## 13. Verification topology and validation-environment fidelity

Verification is authoritative only when both the **command topology** and **execution environment** match the claim.

Before material validation freeze:

```text
CANONICAL_VALIDATION_COMMANDS
VALIDATION_PLATFORM_CLASS=PLATFORM_NEUTRAL|MACOS|LINUX|TARGET_HOST_SPECIFIC|OTHER
AUTHORITATIVE_VALIDATION_ENVIRONMENT
KNOWN_ENVIRONMENT_MISMATCHES
LOCAL_ENVIRONMENT_FIT
FALLBACK_VALIDATION_SURFACE
```

Permanent invariants:

```text
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_NONAUTHORITATIVE_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
NO_LOCAL_RETRY_AFTER_PROVEN_PLATFORM_MISMATCH=REQUIRED
```

If repository configuration or CI already defines a canonical command, reuse it unless a narrower command is explicitly proven semantically equivalent for the exact claim.

Do not invent a stricter/narrower local command and promote its environment-specific failure into an application blocker.

When semantics depend on `sys.platform`, filesystem permissions, Linux utilities, systemd, kernel behavior or another OS-specific capability, run the proof on the authoritative platform class. macOS cannot replace Ubuntu/Linux CI for Linux-sensitive proof; Ubuntu CI cannot replace target-host qualification for host-specific behavior.

Use the narrowest adequate fallback surface:

```text
LOCAL_PLATFORM_WHEN_FIT
-> EXISTING_GITHUB_ACTIONS_UBUNTU
-> ISOLATED_AUTHORIZED_LINUX_ENVIRONMENT_WHEN_HOST_LIKE_BEHAVIOR_IS_REQUIRED
-> CURRENT_TARGET_HOST_ONLY_FOR_TARGET_HOST_SPECIFIC_PROOF_UNDER_CURRENT_AUTHORITY
```

The production host is not a generic development sandbox.

---

## 14. Exact release, staged artifact and deployment topology

Keep strict separation:

```text
SOURCE + LOCKS
-> BUILD / EXACT RELEASE ARTIFACT
-> STAGED EXACT-ARTIFACT SYSTEM TEST
-> PUBLIC-PROVIDER FULL-APPLICATION REHEARSAL
-> PUBLICATION / EXACT-HEAD CI / INDEPENDENT T4
-> EXACT-RELEASE TARGET-HOST QUALIFICATION
-> BOUNDED REAL-MARKET SHADOW SOAK
-> SEPARATELY AUTHORIZED FIRST LIVE
```

Release identity binds the exact source tree plus every release-sensitive surface required by the active deployment contract. Prefer one canonical release-identity source over duplicated literals.

### Manifest creation vs staged verification

When Git is the candidate identity authority, manifest creation may require a clean exact Git HEAD.

Verification of an already-created staged artifact must match the actual deployment transport. For a non-Git exact-artifact/SFTP deployment:

```text
STAGED_ARTIFACT_GIT_CHECKOUT_REQUIRED=NO
RETAINED_CANONICAL_MANIFEST_REQUIRED=YES
EXPLICIT_EXPECTED_RELEASE_SHA_REQUIRED=YES
MANIFEST_SCHEMA_MATCH=REQUIRED
EMBEDDED_RELEASE_SHA_MATCH=REQUIRED
SELECTED_PATH_SET_MATCH=REQUIRED
HASH_AND_SIZE_MATCH=REQUIRED
MISSING_OR_MUTATED_SELECTED_CONTENT=FAIL_CLOSED
```

Do not infer release identity from a non-Git staged filesystem and do not turn the verifier into a second deployment/package authority.

---

## 15. Generated commands and operator efficiency

Human-operated engineering commands are part of the engineering system and must be engineered with the same care as application code.

### 15.1 One-paste default

For user-operated macOS engineering work, default to one contiguous ordinary-Terminal paste when safe. Do not require the user to manually reconstruct paths, prompts, hashes or stage routing when they can be encoded deterministically.

An extra human step is allowed only when technically unavoidable or required by a real authority/security boundary.

Long/critical/model-launch/one-shot workflows default to file-backed scripts with a short hash-verify/execute launcher rather than fragile giant interactive heredocs.

### 15.2 Target environment is evidence

Before delivery establish the actual OS, shell, CLI/tool versions, privilege model, filesystem/deployment shape and evidence-return surface when those facts affect correctness.

Do not assume GNU tools on macOS, Git checkout on an artifact-only target, or a CLI argument meaning merely because a flag exists.

### 15.3 Exact CLI invocation contract proof

For a versioned material CLI freeze as applicable:

```text
CLI_NAME / VERSION / SUBCOMMAND
POSITIONAL_ARGUMENT_SEMANTICS
FILE_ARGUMENT_SEMANTICS
STDIN_SEMANTICS
WORKING_DIRECTORY_SEMANTICS
MODEL_PROVIDER_ID_SEMANTICS
OUTPUT_MODE_SEMANTICS
EXACT_INVOCATION_SHAPE
```

`--help` proving flag existence is insufficient when argument semantics are ambiguous. Prefer provider-native documented invocation plus installed-version evidence.

Model-backed executors must not share stdin with the shell/heredoc program that launched them. Prompt/launcher transport must be explicitly separated.

### 15.4 No false SAFE_STOP

Every fail-closed command gate maps to a real authority, identity, safety, state or correctness invariant.

Prohibited false exactness includes:

- implementation-shape checks unrelated to the real invariant;
- redundant less-reliable network proof after fresh authoritative control-plane identity already exists without added safety value;
- treating missing convenience tooling as safety failure when a validated alternative provides the same proof;
- interpreting an allowlist as requiring every permitted path to change.

Unless the semantic contract explicitly requires specific paths to change:

```text
CHANGED_PATHS ⊆ ALLOWLIST
```

is the scope proof.

### 15.5 Checkpoint before non-decisive tails

After a semantic Writer completes and exact mutation scope/identity is provable, preserve the evidence needed to retain that semantic attempt **before** environment-sensitive lint/type/evidence-packaging tails.

A later wrapper, network, platform or evidence failure does not erase a completed Writer delta and does not authorize a semantic rerun.

### 15.6 Command repair budget

```text
INITIAL_GENERATED_COMMAND
-> AT MOST ONE BOUNDED CORRECTION
-> SECOND AVOIDABLE COMMAND/WRAPPER DEFECT IN SAME STAGE
   => COMMAND_RELIABILITY_HOLISTIC_REGENERATION
```

Holistic regeneration re-reads the actual environment, canonical workflow and prior failure classes, removes stale assumptions and regenerates one complete route. Do not build CONT1/CONT2/CONT3 patch chains.

### 15.7 Evidence egress

Evidence return is part of workflow acceptance. Prove the intended output path/permissions/transfer surface before expensive work when materially uncertain; after generation prove exact file/hash/size/readability and actual client visibility/download when the workflow requires manual transfer.

If evidence egress fails after the semantic action, repair only the evidence path; never repeat the semantic action merely to recreate a downloadable file.

---

## 16. Failure classification, checkpoint/resume and incident learning

Before issuing another command or repair after a failure classify:

```text
FAILURE_CLASS=
SEMANTIC_ACTION_STARTED=YES|NO
SEMANTIC_ACTION_COMPLETED=YES|NO
MUTATION_STATE=
SAFE_STATE_RESTORED=
LAST_ACCEPTED_CHECKPOINT=
RESUME_FROM=
RERUN_SEMANTIC_ACTION=YES|NO
```

Useful failure classes include environment-capability mismatch, wrong validation environment, CLI/shell transport defect, false gate, artifact identity failure, deployment mechanic failure, wrapper/harness failure, application/strategy failure, evidence packaging/egress failure and authority/safety block.

Resume from the latest exact accepted checkpoint. Hidden retries and silent reruns are prohibited.

Material incidents must become reusable learning:

```text
WHAT_HAPPENED
ROOT_CAUSE / CONTRIBUTING_CAUSES
WHY_EXISTING_GATES_MISSED_IT
LOWEST_DECISIVE_REPRODUCTION
GENERALIZED_INVARIANT
PREVENTIVE_TEST / PROCESS CHANGE
OWNER / FOLLOW_UP
```

Historical incidents are rationale and regression evidence, not competing active rules. Reusable lessons are absorbed into this constitution or a narrow procedure rather than relying on chat memory.

---

## 17. Review, repair budget and convergence

Writer self-PASS is execution evidence only.

Independent Review inspects the actual exact object:

- exact GitHub head; or
- integrity-bound dirty-worktree review packet; or
- exact delta against an independently accepted fingerprint.

Once a baseline is independently accepted, default to delta review:

```text
ACCEPTED_BASELINE
+ EXACT_NEW_DELTA
+ TARGETED_REGRESSION / BYPASS CHECKS
```

Do not repeatedly rereview unchanged accepted thousands of lines without a concrete dependency/regression reason.

Default application/design repair budget:

```text
INITIAL IMPLEMENTATION
+ AT MOST ONE NORMAL CONSOLIDATED REPAIR
+ AT MOST ONE EXPLICITLY AUTHORIZED EXCEPTIONAL NARROW REPAIR
```

No routine Repair 3/4/5. New root cause, expanded authority/layer boundary or exhausted budget triggers `HOLISTIC_CONVERGENCE_GATE` and route-level reanalysis. Sunk cost never authorizes another patch.

---

## 18. Repository, CI and publication discipline

Repository safety:

- no direct commit to `main` for normal engineering work;
- no force-push/shared-history rewrite after review begins;
- one bounded issue/branch/worktree mutation scope unless an explicitly independent disjoint stage is frozen;
- no secrets, credentials, wallets, raw private/account data, production DB/log/cache or real account identifiers committed;
- simulated/default market/account data must never be represented as real evidence.

Acceptance/release identity uses exact base/head/changed paths/artifact/CI run where applicable. CI from another SHA is stale evidence.

GitHub CI verifies exact remote content and the CI platform. It should not be used as the first avoidable downstream test when a faithful cheaper local gate exists, but it **is** the correct authority for environment-specific proof assigned to CI.

Publication order:

```text
EXACT CANDIDATE
-> APPLICABLE LOCAL/SAFE VALIDATION
-> DRAFT PR
-> EXACT-HEAD CI
-> INDEPENDENT REVIEW
-> USER MARK-READY AUTHORITY
-> USER MERGE AUTHORITY
-> POST-MERGE CI / LIVE-MAIN VERIFICATION
```

Mark Ready and merge remain distinct user-retained gates even after technical PASS.

---

## 19. Deployment / runtime / trading authority boundaries

No research, governance, Writer, test, CI, Review or implementation result implicitly authorizes:

```text
MARK_READY
MERGE
BRANCH_DELETION
DEPLOYMENT
PRODUCTION_HOST_OR_CLOUD_MUTATION
SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_OR_PRIVATE_API_ACCESS
REAL_NOTIFICATION_WHEN_SEPARATELY_GATED
WALLET / SIGNING / NONCE
EXCHANGE_WRITE
ORDER_SUBMISSION_OR_CANCELLATION
AUTONOMOUS_TRADING
```

These require explicit current user authority and cannot be inferred from a previous stage.

Uncertain, stale, gapped, disconnected or conflicted mandatory state means no new risk.

---

## 20. Specialized contracts and progressive loading

Do not make every participant read every tool profile.

After the universal preflight, load only the narrow contract required by the selected route, for example:

- `ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md` for model-backed routing;
- Codex/OpenCode/Trae/DeepSeek profiles only when that executor/model is selected;
- `ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md` for new/materially changed tools;
- Local Task Runner profiles only when Runner is selected and compatible;
- Hermes contracts only when Hermes is selected;
- FinalShell target-host workflow only for target-host deployment/qualification;
- current Product / Strategy / Operations / Security authority for the bounded task.

Specialized files contain implementation details and fast-changing profiles. Their general engineering principles are owned here so model/tool churn does not force a new project constitution.

---

## 21. Governance maintenance and decision history

When a new durable lesson appears:

1. determine whether it is project-wide or task-specific;
2. if project-wide, update this single constitution rather than create another overlapping rulebook;
3. preserve detailed incident/decision rationale in Issue/ADR-like history or a narrow procedure;
4. mark superseded decisions explicitly instead of silently editing history into ambiguity;
5. independently review material governance changes before merge;
6. keep `AGENTS.md` and `PROJECT_RULES_INDEX.md` compact and accurate.

A decision record should preserve context, decision and consequences. Accepted historical decisions remain useful as history even when superseded, but successor windows begin from the current canonical rule, not the entire history stack.

---

## 22. Frozen concise invariants

```text
GITHUB_CANONICAL_SOURCE=YES
ONE_PROJECT_WIDE_ENGINEERING_CONSTITUTION=YES
MATERIAL_WRITER_REQUIRES_PROJECT_RULESET_PREFLIGHT_PASS=YES
MATERIAL_WRITER_REQUIRES_ENGINEERING_PREFLIGHT_PASS=YES
INDEPENDENT_ANALYSIS_BEFORE_EXTERNAL_CONCLUSIONS=YES
EXTERNAL_MATURE_EVIDENCE_FOR_MATERIAL_DIRECTION_SETTING=YES
SYNTHESIS_BEFORE_ROUTE_FREEZE=YES
MATURE_SOLUTION_FIRST=YES
SIMPLICITY_BY_TOTAL_ENGINEERING_BURDEN=YES
GLOBAL_ROOT_CAUSE_BEFORE_LOCAL_PATCH_LOOPS=YES
CROSS_LAYER_CONTRACT_CLOSURE=REQUIRED
ADMITTED_INPUT_TOTALITY=REQUIRED
STABLE_NARROW_SEAMS_AND_CONTINUITY=REQUIRED
PROVIDER_SCALE_FRESHNESS_GATE=WHEN_APPLICABLE
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
COMPLETE_TASK_PACKET_BEFORE_EXECUTION=YES
LOSSLESS_HANDOFF=REQUIRED_FOR_AUTHORITY_BEARING_TASKS
INTERMEDIARY_PARAPHRASE_AS_DOWNSTREAM_AUTHORITY=PROHIBITED
RAW_EVIDENCE_OVERRIDES_INTERMEDIARY_SUMMARY=YES
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
ACTIVE_TASK_OWNERSHIP_UNTIL_TERMINAL_DISPOSITION=YES
NO_SILENT_MODEL_EXECUTOR_FALLBACK=YES
WRITER_PASS_NE_INDEPENDENT_ACCEPTANCE=YES
PRODUCTION_PATH_FIDELITY=REQUIRED
BALANCED_G0_TO_G12_VERIFICATION=REQUIRED_WHEN_APPLICABLE
INCIDENT_TO_INVARIANT_CONVERGENCE=REQUIRED
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=REQUIRED
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_WRONG_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
EXACT_RELEASE_STAGED_ARTIFACT_SEPARATION=REQUIRED
MACOS_OPERATOR_ONE_PASTE_DEFAULT=YES
CLI_INVOCATION_CONTRACT_PROOF=REQUIRED_FOR_MATERIAL_VERSIONED_CLI
MODEL_EXECUTOR_AND_OUTER_LAUNCHER_STDIN_SHARING=PROHIBITED
FALSE_SAFE_STOP_GATE=PROHIBITED
ALLOWLIST_MEANS_CHANGED_PATHS_SUBSET_UNLESS_SEMANTIC_MINIMUM_EXPLICIT=YES
POST_WRITER_EVIDENCE_CHECKPOINT_BEFORE_NONDECISIVE_TAIL=REQUIRED
NO_SEMANTIC_RERUN_AFTER_PRESERVED_COMPLETED_CHECKPOINT=YES
GENERATED_COMMAND_SECOND_AVOIDABLE_DEFECT_TRIGGERS_HOLISTIC_REGENERATION=YES
APPLICATION_NORMAL_REPAIR_LIMIT=1
APPLICATION_EXCEPTIONAL_REPAIR_LIMIT=1
REPAIR_3_PLUS_SAME_ROUTE=PROHIBITED
EXACT_ARTIFACT_AND_EXACT_HEAD_REVIEW=REQUIRED_WHEN_APPLICABLE
T4_FINAL_REVIEW_INDEPENDENT=YES
MARK_READY_MERGE_DEPLOY_RUNTIME_CREDENTIAL_ACCOUNT_EXCHANGE=SEPARATE_CURRENT_USER_AUTHORITY
```

---

## 23. Supersession intent

On independent acceptance and merge of this V2 standard:

- `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md` becomes historical/superseded;
- the project-wide normative portions of `PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md` are incorporated here; that file remains only a task-conditional research procedure/reference;
- the project-wide normative portions of `GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md` are incorporated here; that file remains only a task-conditional operator procedure/incident catalogue;
- the Issue #139 holistic verification methodology is incorporated here and does not require a separate competing governance constitution;
- `MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md` remains a compact executable checklist derived from V2, not a separate source of engineering policy.

Future governance changes should edit V2 or a genuinely narrow specialized contract instead of creating another overlapping project-wide rulebook.