# Trader Assist / Trade OS — Holistic Engineering Verification, Continuity and Release Method V1

**Status:** CANONICAL GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-31  
**Repository:** `woshixiong/trader-assist-v0`  
**Authority source:** Issue #139 post-preflight methodology freeze plus the 2026-08-31 generated-command incident convergence.  

This document is the dedicated project-wide method for converting engineering incidents and material changes into verified, continuous, releasable work without repeatedly discovering deeper failures on the target host or through user-operated command retries.

It complements, and does not replace:

- `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`;
- `MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`;
- `PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`;
- `GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md`;
- current Product / Strategy / Operations / Security authority.

It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, wallet/signing, exchange-write, order-submission or trading authority.

---

## 1. Why this method exists

Recent pre-live failures showed a recurring higher-level pattern:

```text
VERIFICATION_TOPOLOGY_DOES_NOT_MATCH_PRODUCTION_AUTHORITY_TOPOLOGY
```

The project already had substantial tests. The problem was not simply test count. Important paths first became real only after an earlier failure was removed, after provider-valid edge states appeared, after true production composition executed, or after a source-level candidate was converted into a release/host shape.

Reusable failure subclasses include:

```text
CROSS_LAYER_CONTRACT_DOMAIN_MISMATCH
PRODUCTION_COMPOSITION_COVERAGE_GAP
SYNTHETIC_FIXTURE_MONOCULTURE
FIRST_FAILURE_MASKING
RELEASE_SEMANTIC_GAP
COMMAND_OR_VALIDATION_TOPOLOGY_MISMATCH
```

Examples include:

- an upstream-valid market input that a downstream indicator could not totalize;
- component tests passing while the real application composition failed later;
- aligned synthetic fixtures hiding valid arbitrary-phase behavior;
- one startup/lifecycle failure preventing later strategy or outcome paths from executing;
- source-level verification succeeding while staged artifact / target-host behavior had different assumptions;
- generated commands validating a CLI, OS or static-analysis topology different from the authoritative execution environment.

The permanent objective is to make cheaper deterministic verification exercise the same semantic and authority path that expensive release, host and Shadow stages will later exercise, while still keeping environment-specific qualification separate.

---

## 2. Project-wide invariants

The following are mandatory for material engineering work when applicable:

```text
CROSS_LAYER_CONTRACT_CLOSURE=REQUIRED
ADMITTED_INPUT_TOTALITY=REQUIRED
PRODUCTION_PATH_FIDELITY=REQUIRED
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=REQUIRED
INCIDENT_TO_INVARIANT_CONVERGENCE=REQUIRED
EXACT_RELEASE_VERIFICATION_BEFORE_TARGET_HOST=REQUIRED_WHEN_SAFE_AND_PRACTICAL
CODE_CONTINUITY_REVIEW_FOR_MATERIAL_CHANGES=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY=REQUIRED
```

### Cross-layer contract closure

For adjacent authoritative layers:

```text
UPSTREAM_ACCEPTED_DOMAIN
⊆
DOWNSTREAM_SUPPORTED_DOMAIN
```

or the downstream layer must explicitly map an admitted state to the correct typed semantic outcome, such as:

```text
NO_ACTION
DEFER
UNAVAILABLE
DATA_INVALID
OWNER_LEVEL_BOUNDED_RETRY
```

Incidental arithmetic, denominator, index, parsing or assertion exceptions are not semantic policy.

### Admitted-input totality

Every legitimate provider/contract-admitted input must produce a deterministic typed outcome. Truly contradictory, corrupt or authority-invalid data still fails closed.

This rule does not require every function to accept every value. Strict helpers may keep narrow preconditions when the owning layer correctly prevents or maps valid outer-domain cases before invoking them.

### Production-path fidelity

A test may claim production-path coverage only when it drives the real application composition and authority seams relevant to the claim. A substitute that bypasses the boundary under test does not prove that boundary.

### Verification-topology match

Lower and medium verification gates should exercise the same business/authority path later exercised by release/host gates. Environment-specific validation remains separate and must run on the correct authoritative environment class.

### Incident convergence

A high-stack incident should normally converge through:

```text
OBSERVED INCIDENT
-> LOWEST DECISIVE REPRODUCTION
-> GENERALIZED INVARIANT / PROPERTY
-> RELEVANT PRODUCTION-COMPOSITION SCENARIO
-> CANONICAL INCIDENT RECORD
```

Do not grow an unlimited collection of unrelated incident-specific tests without a stable invariant vocabulary.

---

## 3. Mandatory engineering reasoning path

Material work evaluates all applicable layers, not only the edited function:

```text
CODE / CONTRACT
-> DOMAIN LOGIC
-> AUTHORITY / STATE TRANSITIONS
-> PERSISTENCE / RESTART / REPLAY
-> COMPONENT INTEGRATION
-> REAL PRODUCTION COMPOSITION
-> RELEASE ARTIFACT
-> PROVIDER / NETWORK REHEARSAL
-> TARGET-HOST ENVIRONMENT
-> SHADOW / CANARY OBSERVATION
-> FUTURE CONTINUITY / REPLACEABILITY
```

Before Writer dispatch, the attack matrix must include important applicable cases such as:

- ordinary case;
- zero / empty / flat / degenerate-but-valid data;
- denominator-zero and boundary values;
- missing / stale / out-of-order / conflicting evidence;
- arbitrary valid prefix/alignment phases;
- partial cohort / mixed state;
- duplicate wakeup / retry / idempotency;
- provider delay / error / omission and correct owner-level recovery;
- reconnect;
- restart / store reopen / replay;
- interruption / shutdown;
- supersession / Registry epoch transition;
- realistic scale/freshness pressure;
- release/package identity drift;
- unauthorized inputs/actions.

The exact matrix is task-specific. Do not mechanically add irrelevant cases, and do not omit a relevant failure class merely because current fixtures are tidy.

---

## 4. Balanced verification portfolio

Use a balanced portfolio rather than one giant end-to-end qualification:

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

The labels are conceptual unless a specific task/runbook adopts them. Their responsibilities remain distinct even when names differ.

Rules:

1. cheaper deterministic gates catch semantic defects before expensive host runs;
2. target-host qualification focuses on host/systemd/filesystem/permissions/network/timing/resources and exact-release behavior, not the first execution of core business semantics;
3. public-provider rehearsal uses real public data but no account/private API/wallet/signing/exchange write;
4. canary/Shadow observation supplements deterministic verification and never substitutes for it;
5. a high-stack failure should normally be reproduced at the lowest decisive layer plus the relevant composition layer before repair acceptance;
6. exact-head CI is authoritative for CI-platform validation; local platform mismatches do not override it.

---

## 5. Property-based and stateful testing

Property/stateful testing is dev/test tooling, not runtime authority.

Initial useful property domains include:

- valid OHLC geometry including `high == low`;
- zero volume;
- zero/near-zero derived denominators;
- flat sequences;
- positive-price extremes inside accepted Decimal/domain bounds;
- arbitrary valid UTC alignment/prefix phases;
- causal 5m -> 15m/1h aggregation;
- serialization/restore equivalence where suitable.

Initial useful stateful domains include:

- `WARMING -> HISTORY_READY -> SNAPSHOT_READY -> ACTIVE`;
- reconnect;
- provider delay/recovery;
- duplicate boundary/idempotency;
- Registry successor/epoch transition;
- restart/reopen/reconcile;
- shutdown/interruption.

A meaningful generated/shrunk failure must become a deterministic regression example or fixture. CI correctness must not depend on random rediscovery or one seed.

Stateful testing is for bounded lifecycle/state models. It is not permission to build a second full application framework inside the test suite.

---

## 6. Canonical incident corpus

Maintain a converged incident corpus for material historical failures. At minimum each record carries:

```text
INCIDENT_ID
OBSERVED_HIGH_LEVEL_FAILURE
LOWEST_REPRODUCIBLE_CONTRACT
GENERALIZED_INVARIANT
PRODUCTION_COMPOSITION_SCENARIO
RELEASE_OR_HOST_RELEVANCE
FIXED_REGRESSION_ID
```

The current pre-live corpus includes the reusable lessons from Issues #119, #129, #131, #134, #136 and #138.

The corpus is an evidence/index surface, not a second architecture authority. Product/runtime semantics remain in their canonical code/contracts/governance.

---

## 7. Release Candidate production-composition harness

The repository-owned RC application harness must drive existing production authorities rather than reimplement them:

```text
ThreeSetupProductionApplication
-> MultiAssetProductionBootstrap
-> MultiAssetPublicRuntime
-> MultiAssetShadowCoordinator
-> Scanner
-> Strategy
-> Formal / Planning
-> Outcome
-> Evidence / Outbox
```

Representative deterministic journeys should exercise the real Target-20 order of magnitude and current lifecycle where practical, including:

- warmup/history;
- ACTIVE lifecycle;
- at least two relevant closed-5m boundaries;
- maintenance;
- clean shutdown;
- restart/reopen;
- correct continuation;
- no real notification network.

Reuse accepted providers/transports through deterministic injection seams. Do not duplicate business logic merely to make a test easier.

The RC harness validates application semantics. It is not generalized target-host qualification automation.

---

## 8. Release / provider / deployment topology

Use strict conceptual separation:

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

Current architecture remains:

- single-process asyncio application;
- Python/venv;
- SQLite;
- systemd;
- public-data-only Three Setup Shadow;
- FinalShell SSH/SFTP exact-artifact transport for the current target host.

Do not introduce Docker, Kubernetes, microservices, Kafka, Redis, Celery, Temporal, Terraform, Ansible or a new database merely to solve verification gaps. A new tool requires the existing mature-solution/build-vs-buy gate and must reduce total burden.

---

## 9. Exact-release identity and staged-artifact verification

Release identity must bind the exact source tree plus every release-sensitive surface required by the active deployment contract, including applicable locks, deployment scripts, service/config schema and manifest.

Prefer one canonical release-identity source over duplicated literals.

### Manifest creation

Creating the canonical release manifest from a source candidate may require an exact clean Git HEAD when Git is the candidate identity authority.

### Staged artifact verification

Verification of an already-created staged artifact must match the actual deployment transport.

For the current FinalShell/SFTP artifact model:

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

Do not infer release SHA from a non-Git staged filesystem. Do not require `.git` merely because manifest creation used Git.

A staged exact-artifact verifier must not become a second package manager, deployment framework or runtime authority.

---

## 10. Validation environment fidelity

Validation is only authoritative when the validation command and environment match the contract being claimed.

Before material validation, freeze:

```text
CANONICAL_VALIDATION_COMMANDS=
VALIDATION_PLATFORM_CLASS=PLATFORM_NEUTRAL|MACOS|LINUX|TARGET_HOST_SPECIFIC|OTHER
AUTHORITATIVE_VALIDATION_ENVIRONMENT=
KNOWN_ENVIRONMENT_MISMATCHES=
LOCAL_ENVIRONMENT_FIT=PASS|FAIL|NOT_APPLICABLE
FALLBACK_VALIDATION_SURFACE=
```

Mandatory rules:

```text
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY_GATE=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_NONAUTHORITATIVE_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
NO_LOCAL_RETRY_AFTER_PROVEN_PLATFORM_MISMATCH=REQUIRED
```

Use repository/CI canonical commands where they already exist. Do not invent a stricter or narrower local command and then treat its environment-specific failure as an application blocker.

If validation semantics depend on `sys.platform`, filesystem permissions, Linux utilities, systemd, kernel behavior or another OS-specific capability, run that proof on the authoritative platform class. A macOS result does not replace an Ubuntu CI proof, and an Ubuntu hosted runner does not replace target-host qualification for host-specific behavior.

Once an environment mismatch is proven and the candidate state is preserved, checkpoint and move the remaining proof to the correct environment rather than repeatedly patching local commands.

---

## 11. Generated command / operator topology

For human-executed commands, `GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md` is the detailed authority.

This method adds the following project-wide invariants:

```text
CLI_INVOCATION_CONTRACT_PROOF=REQUIRED
ALLOWLIST_PROOF_IS_SET_MEMBERSHIP_NOT_CHANGE_COUNT=REQUIRED
POST_WRITER_EVIDENCE_CHECKPOINT_BEFORE_NONDECISIVE_TAIL=REQUIRED
```

### CLI invocation contract proof

Before launching a model executor or other versioned CLI through a generated command, prove the exact invocation shape needed by the workflow from the installed/authoritative CLI surface. Merely proving that a flag exists is insufficient when its argument semantics are ambiguous.

Freeze where applicable:

```text
CLI_NAME=
CLI_VERSION=
PROMPT_OR_INPUT_TRANSPORT=
POSITIONAL_ARGUMENT_SEMANTICS=
FILE_ATTACHMENT_SEMANTICS=
STDIN_SEMANTICS=
MODEL_ID=
WORKING_DIRECTORY_SEMANTICS=
OUTPUT_MODE=
```

### Allowlist proof

A write allowlist means:

```text
CHANGED_PATHS ⊆ ALLOWLIST
```

plus any task-specific minimum-change condition actually required by the semantic contract.

It does **not** mean every allowlisted path must change. Do not turn a maximum scope into a false exact-count requirement.

### Post-Writer evidence checkpoint

After a semantic Writer has completed and exact mutation scope/identity can be established, save the evidence needed to preserve that semantic attempt before running non-decisive environment-sensitive validation tails.

A later lint/type/platform/evidence-packaging failure must not erase the exact Writer delta or force a semantic rerun when the delta remains provable.

---

## 12. Code continuity and future development

For material code changes classify relevant paths/responsibilities as:

```text
ACTIVE_CANONICAL
SHARED_COMPATIBILITY
LEGACY_READ_ONLY
FUTURE_DEFERRED
```

Record:

```text
STABLE_AUTHORITIES
STABLE_INTERFACES
REPLACEABLE_IMPLEMENTATION_SEAMS
PERSISTED_REPRESENTATION_VERSIONING
KNOWN_CHANGE_AMPLIFICATION_HOTSPOTS
NEXT_EXPECTED_STAGE
MIGRATION_OR_LOCKIN_RISK
```

Current continuity policy:

- preserve Registry/DataAuthority/Runtime/Evidence/Strategy-continuation authority architecture;
- preserve single-process asyncio, SQLite, systemd and public-provider design;
- do not split files merely because they are large;
- treat large integration/runtime modules as change-amplification hotspots: a future unrelated responsibility should trigger bounded seam-extraction review rather than another arbitrary responsibility;
- preserve backward-readable/versioned durable representations;
- replace gradually behind stable seams when replacement is actually needed;
- do not bulk-delete older lineages until their compatibility role is explicitly classified.

Continuity is not permission to build speculative platforms.

---

## 13. Mature methods and project fit

The route is independently derived and externally confirmed by mature engineering methods, including:

- Google SRE Release Engineering — packaged/reproducible release artifacts and system testing before canary;
- Google SRE Testing for Reliability — deterministic/pre-release testing plus production testing, with canary as structured acceptance rather than a substitute for tests;
- Google SRE Canarying Releases — real traffic/input supplements pre-release confidence;
- Hypothesis — property-based and rule-based stateful testing for broader valid domains and operation sequences;
- Fowler Test Pyramid — many cheap lower-level tests, fewer broad expensive tests;
- Fowler Branch by Abstraction — gradual replacement behind stable seams;
- Twelve-Factor Build/Release/Run — strict separation of build identity, release/config and run;
- AWS deployment guidance — pre-production/one-box/canary-style validation before broad activation.

Primary references:

- https://sre.google/sre-book/release-engineering/
- https://sre.google/sre-book/testing-reliability/
- https://sre.google/workbook/canarying-releases/
- https://hypothesis.readthedocs.io/en/latest/
- https://hypothesis.readthedocs.io/en/latest/stateful.html
- https://martinfowler.com/bliki/TestPyramid.html
- https://martinfowler.com/bliki/BranchByAbstraction.html
- https://12factor.net/build-release-run
- https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.ads.1-test-deployments-in-pre-production-environments.html

These sources provide method evidence and vocabulary. They do not authorize importing their infrastructure scale into Trader Assist / Trade OS.

---

## 14. Rejected / deferred routes

For the current architecture and verification problem:

```text
PACT_OR_CONTRACT_BROKER=REJECT_FOR_CURRENT_INTERNAL_SINGLE_PROCESS_DOMAIN_CLOSURE
MICROSERVICE_SPLIT=REJECT
DOCKER_REPLATFORM_AS_FIX=REJECT
KUBERNETES=REJECT
GENERIC_WORKFLOW_ENGINE=REJECT
NEW_MESSAGE_BROKER=REJECT
NEW_DATABASE=REJECT
GENERALIZED_HOST_QUALIFICATION_FRAMEWORK=DEFERRED_LOWEST_PRIORITY
BIG_BANG_LEGACY_REWRITE=REJECT
```

Reason: these add authorities and operational burden without solving the root contract/composition/release-topology failure.

---

## 15. Required preflight integration

For material implementation/review/release work under this method, the Engineering Preflight must resolve, when applicable:

```text
CROSS_LAYER_CONTRACT_CLOSURE_PLAN=
ADMITTED_INPUT_TOTALITY_PLAN=
PRODUCTION_PATH_FIDELITY_PLAN=
INCIDENT_TO_INVARIANT_PLAN=
CANONICAL_VALIDATION_COMMANDS=
VALIDATION_PLATFORM_CLASS=
AUTHORITATIVE_VALIDATION_ENVIRONMENT=
KNOWN_ENVIRONMENT_MISMATCHES=
FALLBACK_VALIDATION_SURFACE=
EVIDENCE_CHECKPOINT_PLAN=
EXACT_RELEASE_VERIFICATION_PLAN=
CONTINUITY_CLASSIFICATION=
```

If one is not applicable, record `NOT_APPLICABLE` rather than silently omitting a relevant uncertainty.

---

## 16. Acceptance and authority boundaries

Material implementation acceptance should bind, as applicable, to:

```text
EXACT_BASE
EXACT_CANDIDATE_OR_HEAD
EXACT_CHANGED_PATHS
LOWEST_DECISIVE_REGRESSIONS
PROPERTY_OR_STATEFUL_INVARIANTS
PRODUCTION_COMPOSITION_PROOF
REALISTIC_SCALE_PROOF
EXACT_RELEASE_ARTIFACT_PROOF
PUBLIC_PROVIDER_REHEARSAL
EXACT_HEAD_CI
INDEPENDENT_REVIEW
RESIDUAL_RISKS
```

Writer self-PASS is never independent acceptance.

Mark Ready, merge, deployment, runtime/cloud mutation and First Live remain separate user-retained gates.

A G12/Shadow result for one exact release is not reusable authority to rerun a changed release or to cross a new deployment/runtime gate.

---

## 17. Governance maintenance / successor rule

This file is a mandatory successor-window authority once merged and indexed.

New project-wide verification/continuity/release lessons should normally amend this method or the existing specialized generated-command rule rather than create another overlapping constitution.

Historical Issue comments remain evidence/rationale. They are not a substitute for this merged canonical path.

When a later task narrows or supersedes one implementation technique, preserve the stable invariants here unless a new independently reviewed canonical governance change explicitly changes them.
