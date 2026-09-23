# Trader Assist / Trade OS — Generated Command Reliability and Operator Procedure V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-08-30  
**Normative owner:** `ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md`

This file operationalizes the V4 rules for project-generated commands, launchers, one-paste Terminal blocks, local automation, target-host execution and evidence-return workflows. It is also the compact incident catalogue for command-generation failures.

It does **not** create a competing project-wide constitution. V4 governs conflicts.

Use this procedure before presenting any nontrivial human-executed engineering command.

---

## 1. Pre-delivery reliability record

```text
GENERATED_COMMAND_RELIABILITY_GATE=PASS|FAIL
TASK=
EXECUTION_SURFACE=MACOS_TERMINAL|GITHUB_ACTIONS_UBUNTU|ISOLATED_LINUX|FINALSHELL_TARGET_HOST|LOCAL_RUNNER|OTHER
TARGET_OS=
TARGET_SHELL=
TARGET_SHELL_VERSION=
PRIVILEGE_MODEL=
CANONICAL_WORKFLOW=
REQUIRED_TOOLS=
REQUIRED_TOOLS_PROVEN=YES|NO

CLI_NAME=
CLI_VERSION=
CLI_INVOCATION_CONTRACT_PROOF=PASS|FAIL|NOT_APPLICABLE
CLI_INPUT_TRANSPORT=
EXACT_INVOCATION_SHAPE=

CANONICAL_VALIDATION_COMMANDS=
VALIDATION_PLATFORM_CLASS=PLATFORM_NEUTRAL|MACOS|LINUX|TARGET_HOST_SPECIFIC|OTHER|NOT_APPLICABLE
AUTHORITATIVE_VALIDATION_ENVIRONMENT=
KNOWN_ENVIRONMENT_MISMATCHES=
LOCAL_ENVIRONMENT_FIT=PASS|FAIL|NOT_APPLICABLE
FALLBACK_VALIDATION_SURFACE=

SCRIPT_TRANSPORT=FILE_BACKED|SHORT_INLINE|HEREDOC_EXCEPTION
KNOWN_INCIDENT_CLASSES_REVIEWED=YES|NO
KNOWN_INCIDENT_NONREGRESSION_GATE=PASS|FAIL
INTERACTIVE_SHELL_PARSE_MODE_PROVEN=PASS|FAIL|NOT_APPLICABLE
TRANSPORT_MONOTONICITY=PASS|FAIL
SYNTAX_CHECK=PASS|FAIL|NOT_AVAILABLE
STATIC_ANALYSIS=PASS|FAIL|NOT_AVAILABLE
SAFE_STOP_GATES_BOUND_TO_REAL_INVARIANTS=YES|NO
ALLOWLIST_SEMANTICS_PROOF=PASS|FAIL|NOT_APPLICABLE
HARNESS_BOUNDARY_CONTRACT_PROOF=PASS|FAIL|NOT_APPLICABLE
HARNESS_OBSERVATION_PHASE_FIDELITY=PASS|FAIL|NOT_APPLICABLE
TEARDOWN_SURVIVING_EVIDENCE_PROOF=PASS|FAIL|NOT_APPLICABLE
PERSISTED_STATE_COPY_SEMANTICS_PROOF=PASS|FAIL|NOT_APPLICABLE

ONE_SHOT_SEMANTIC_BOUNDARY=
SIDE_EFFECT_FREE_PREFLIGHT_COMPLETE_BEFORE_ONE_SHOT=YES|NO|NOT_APPLICABLE
SEMANTIC_START_PREREQUISITES=
PUBLICATION_PREREQUISITES=
PRE_SEMANTIC_GATE_NECESSITY_PROOF=PASS|FAIL|NOT_APPLICABLE
LAUNCH_ARTIFACT_DELIVERY_CONFIRMED=YES|NO|NOT_APPLICABLE
CHECKPOINT_RESUME_PLAN=
POST_SEMANTIC_EVIDENCE_CHECKPOINT_PLAN=

EVIDENCE_OUTPUT_PATH=
EVIDENCE_EGRESS_PLAN=PASS|FAIL|NOT_APPLICABLE
EXPECTED_IRREDUCIBLE_USER_INTERACTIONS=
COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION
```

Do not deliver a nontrivial command with `GENERATED_COMMAND_RELIABILITY_GATE=FAIL`.

A known prior failure class is a regression test, not merely history. If the planned command or harness recreates a catalogued failure shape without a specific preventive control, then:

```text
KNOWN_INCIDENT_NONREGRESSION_GATE=FAIL
GENERATED_COMMAND_RELIABILITY_GATE=FAIL
```

---

## 2. Target environment and CLI semantics are evidence

Before command generation, establish only the facts that materially affect correctness:

- OS/distribution/version and CPU architecture when relevant;
- shell implementation/version;
- actual CLI/tool version and subcommand;
- privilege/sudo shape;
- filesystem/worktree/deployment shape;
- artifact-vs-Git-checkout model;
- evidence transfer surface.

Do not assume GNU utilities on macOS, BSD behavior on Linux, a Git checkout on an artifact-only target, or CLI argument semantics from flag names.

For versioned material CLIs, prove as applicable:

```text
POSITIONAL_ARGUMENT_SEMANTICS
FILE_ARGUMENT_SEMANTICS
STDIN_SEMANTICS
WORKING_DIRECTORY_SEMANTICS
MODEL_OR_PROVIDER_ID_SEMANTICS
OUTPUT_MODE_SEMANTICS
```

`--help` proving a flag exists is not enough when its argument meaning is ambiguous. Prefer provider-native documentation plus installed-version evidence.

Model-backed executors must never inherit the same stdin stream that contains the running shell/heredoc program. Use file-backed phase separation and an explicit executor stdin source.

Shell parsing behavior is also environment evidence. Interactive commands must not depend on an unset or unproven startup option, alias, comment mode, history mode, quoting mode or shell-emulation mode when that behavior can change parsing or execution. In particular, an ordinary interactive zsh paste must not assume `#` is a comment unless `INTERACTIVE_COMMENTS` has been explicitly established; the simpler default is to omit interactive comment lines entirely.

---

## 3. One-paste and file-backed execution

User-operated macOS engineering work defaults to **one ordinary-Terminal paste** when safe.

The user should not need to manually reconstruct:

- repository/worktree path;
- prompt fragments;
- hashes/JSON;
- executor/model route already frozen by Engineering;
- validation/evidence commands that can be encoded deterministically.

For long, critical, model-launch, deployment or one-shot workflows:

```text
GENERATE FILE-BACKED SCRIPT / TASK PACKET
-> CLOSE INPUT TRANSPORT
-> HASH / MANIFEST WHEN MATERIAL
-> SYNTAX / STATIC VALIDATE
-> SHORT HASH-VERIFY / EXECUTE LAUNCHER
```

Use an interactive heredoc only when short/low-risk or genuinely required by the environment.

### 3.1 Transport monotonicity

`FILE_BACKED` describes a reduction in operator-input complexity, not a filename at the end of an equally fragile transport.

A route does **not** satisfy the file-backed requirement merely by embedding the complete long script or packet inside the same interactive paste as:

- a giant Base64/hex/escaped literal;
- a giant quoted `shell -c` string;
- a long nested heredoc/subshell whose full parse must survive interactive paste;
- another representation whose operator-visible payload is comparable to or more fragile than the original script.

Required invariant:

```text
OPERATOR_VISIBLE_BOOTSTRAP
  MUST_BE_MATERIALLY_SIMPLER_THAN_PAYLOAD
  AND PARSE_COMPLETE_ON_ITS_OWN
```

If this cannot be achieved on the current surface, prefer a robust file/artifact transfer surface, an accepted repository-owned launcher, or an explicitly safe phase split over another encoding layer. Hash verification detects corruption after transport; it does not make an overlong transport reliable.

A self-extracting or embedded-payload artifact may be an acceptable emergency transport only when the payload is already complete, hash-verified, rehearsed and materially simpler for the operator than reconstructing it interactively. It is not a preferred steady-state substitute for a versioned stable runner.

For launcher repair or holistic regeneration, the operator-visible command must not become a self-modifying patch engine. In particular, do not deliver a long interactive `python -c`, `sed`, `perl`, nested shell string or equivalent command whose purpose is to rewrite an existing launcher in-place before execution.

```text
OPERATOR_VISIBLE_SELF_MODIFYING_LAUNCHER_REWRITE=PROHIBITED
HOLISTIC_REGENERATION_DELIVERS_COMPLETE_REPLACEMENT_BYTES=REQUIRED
POST_GENERATION_VALIDATION_RUNS_ON_EXACT_FINAL_BYTES=REQUIRED
```

A holistic regeneration must produce the complete replacement script/bundle **before** operator handoff, validate its exact final bytes, and reduce the user action to a short verify-and-execute bootstrap. A syntax check on the unmodified/original files does not prove that an intended interactive rewrite succeeded.

### 3.1A Dynamic-launcher stop rule

Repeated repair must reduce execution freedom, not create another bespoke program.

```text
TASK_PACKET_IS_DATA_NOT_PROGRAM=YES
PER_TASK_DYNAMIC_EXECUTION_PROGRAM_GENERATION=PROHIBITED_BY_DEFAULT
VERSIONED_STABLE_RUNNER_PREFERRED=YES
```

After a launcher-family termination/holistic regeneration, first ask whether the remaining semantic stage can run through the accepted stable runner with task-specific data only. If yes, generating another task-specific R3/R4/R5-style execution topology is prohibited.

A custom launcher remains exceptional and must show:

```text
STABLE_RUNNER_INSUFFICIENCY_PROVEN=YES
NEW_MECHANIC_IS_TRULY_TASK_SPECIFIC=YES
ADDED_FAILURE_SURFACE_LT_DECISION_VALUE=YES
SEPARATE_REVIEW_REQUIRED=YES
```

Successful emergency recovery mechanisms such as Git-object reconstruction, patch stitching, self-extracting payloads or transport-specific fallbacks remain recovery evidence. They do not automatically become normal launch architecture.

### 3.1B Validated execution-path and failed-path ledgers

Command reliability must preserve successful knowledge as aggressively as failure knowledge.

```text
VALIDATED_EXECUTION_PATH_LEDGER=REQUIRED
FAILED_PATH_RETIREMENT_LEDGER=REQUIRED
```

A validated entry records:
- executor/client family;
- minimum required capabilities;
- known-good invocation shape;
- source-acquisition and workspace-materialization contract;
- checkpoint/egress contract;
- last proven version or capability evidence;
- canonical evidence locator.

When a known-good path fits the frozen task, prefer it. Introduce a new execution shape only when a concrete requirement or capability/environment drift proves the known-good path insufficient.

A failed-path entry records the retired assumption/mechanic and canonical evidence. Known-failed paths are prohibited by default and may reopen only with changed capability/environment evidence plus bounded requalification. Renaming or wrapping the same assumption does not reset retirement.

Current Codex-specific entries live in the applicable Codex profile rather than being duplicated here.

### 3.2 Launch-artifact delivery is a prerequisite to operator execution

A generated ZIP, script, command file or bundle is not available merely because Engineering Control described it or recorded an expected filename/hash.

Before telling the user to execute a local artifact:

```text
ARTIFACT_BYTES_CREATED=YES
ARTIFACT_SHA256_VERIFIED=YES
OPERATOR_DELIVERY_SURFACE=PROVEN
LAUNCH_ARTIFACT_DELIVERY_CONFIRMED=YES
```

If the artifact is expected in a local path such as Downloads, that path must come from actual delivered/operator evidence, not an invented filename. If delivery cannot be proven, use a provider-native artifact/download surface or give a short self-contained bootstrap whose payload source is itself real and verified. Missing-artifact execution is a command-generation defect and consumes command-repair progression.

---

## 4. Canonical validation command and platform fidelity

Do not invent a local validation topology when the repository/CI already defines one.

Use:

```text
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_NONAUTHORITATIVE_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
NO_LOCAL_RETRY_AFTER_PROVEN_PLATFORM_MISMATCH=REQUIRED
```

If a proof depends on `sys.platform`, filesystem permission semantics, Linux APIs/utilities, systemd, kernel behavior or target-host state, run it on the corresponding authoritative platform.

Preferred fallback route:

```text
LOCAL_PLATFORM_WHEN_FIT
-> EXISTING_GITHUB_ACTIONS_UBUNTU
-> ISOLATED_AUTHORIZED_LINUX_ENVIRONMENT_IF_HOST_LIKE_BEHAVIOR_IS_REQUIRED
-> CURRENT_TARGET_HOST_ONLY_FOR_TARGET_HOST_SPECIFIC_PROOF_UNDER_CURRENT_AUTHORITY
```

The production target host is not a generic development sandbox.

When the repository already has an accepted GitHub Actions workflow that supplies locked dependencies and equal-or-higher-fidelity Linux/full-suite proof:

```text
USER_MAC_FULL_REPOSITORY_SUITE=NO_BY_DEFAULT
LOCAL_LAUNCHER_FOCUSED_TESTS_ONLY=YES_WHEN_USEFUL
SEMANTIC_CHECKPOINT_BEFORE_REMOTE_FULL_SUITE=REQUIRED
GITHUB_ACTIONS_FULL_SUITE_AND_LINUX_PROOF=PREFERRED
LOCAL_MISSING_CI_ONLY_DEPENDENCY!=APPLICATION_FAILURE
```

Do not spend user workstation resources installing/reproducing the entire CI environment solely for parity when GitHub is the authoritative proof surface. A genuinely local claim remains local.

A known platform mismatch is a routing input. Do not keep rewriting commands merely to make the wrong platform pass.

---

## 5. No false SAFE_STOP or false exactness

Every fail-closed gate must protect a real authority, identity, safety, state or correctness invariant.

Prohibited patterns:

- checking incidental source formatting instead of the authoritative object/state;
- requiring redundant lower-reliability network proof after fresh authoritative control-plane GitHub identity when it adds no safety value;
- treating a missing convenience tool as safety failure when a proven native/standard alternative gives the same proof;
- requiring a target artifact to be a Git checkout when the canonical deployment is exact-artifact/SFTP;
- interpreting an allowlist as a requirement that every allowed path must change;
- embedding a self-generated expected identity that has not itself been computed or independently checked from the exact object it gates.

Unless the semantic contract explicitly requires named files to change:

```text
CHANGED_PATHS ⊆ ALLOWLIST
```

is the scope proof.

---

## 6. Release-sensitive values and exact artifact consistency

Release-specific values should come from one canonical identity source rather than independent duplicated literals.

When applicable verify:

```text
RELEASE_SHA / TREE
MANIFEST_HASH / ENTRY_COUNT
PACKAGE_IDENTITY
CONFIG / SERVICE / DEPLOYMENT SURFACE
REGISTRY_OR_PROVIDER_IDENTITY
CROSS_ARTIFACT_SEMANTIC_CONSISTENCY
STALE_RELEASE_LITERAL_SCAN
```

Template/generator byte equality proves generation fidelity only; it does not prove every embedded release-specific value was rebound correctly.

Manifest creation from source and staged-artifact verification are separate contracts. A non-Git staged artifact uses retained manifest + explicit expected release identity; do not require `.git` merely because source manifest creation used Git.

---

## 7. One-shot boundary, checkpoint and resume

Before an expensive/irreversible/rate-limited one-shot action, finish all **necessary** side-effect-free proof first. Preflight scope is minimized to prerequisites that protect semantic safety/correctness or are irreducibly required to obtain/verify the semantic source.

```text
SEMANTIC_READINESS != PUBLICATION_READINESS
SEMANTIC_START_DEPENDENCY_MINIMIZATION=REQUIRED
```

Do not place GitHub push/PR/result-egress authentication, publication dry-runs or redundant control-plane identity probes before a semantic Writer merely because the same wrapper intends to publish afterward. When practical, semantic execution must be able to reach a durable local/exact checkpoint even if publication transport is unavailable.

Before an expensive/irreversible/rate-limited one-shot action, finish all side-effect-free proof first.

Suggested phases:

```text
0 READ-ONLY ENVIRONMENT / CAPABILITY PREFLIGHT
1 ARTIFACT / CONFIG PREPARATION
2 SAFE REHEARSAL WHEN PRACTICAL
3 SEMANTIC ONE-SHOT PREFLIGHT
4 ATTEMPT SENTINEL IMMEDIATELY BEFORE SEMANTIC ACTION
5 SEMANTIC ACTION EXACTLY ONCE
6 EVIDENCE / CLEANUP / ADJUDICATION
```

Attempt accounting must distinguish:

```text
PREFLIGHT_FAILURE
VALIDATION_ENVIRONMENT_FAILURE
DEPLOYMENT_FAILURE
WRAPPER_OR_HARNESS_FAILURE
SEMANTIC_ACTION_STARTED
SEMANTIC_ACTION_COMPLETED_PASS
SEMANTIC_ACTION_COMPLETED_FAIL
POST_ACTION_EVIDENCE_OR_CLEANUP_FAILURE
```

After a semantic Writer/action completes and exact mutation identity is provable, checkpoint that evidence **before** non-decisive validation/evidence tails.

Examples:

- semantic Writer complete + later deterministic validation failure -> do not rerun Writer;
- deployment complete + evidence packaging failure -> prove/reuse deployment identity;
- one-shot complete + download failure -> repair only evidence path;
- macOS failure caused by platform mismatch -> move remaining proof to the correct Linux surface.

Hidden reruns/retries are prohibited.

### 7.0 Quota/session capacity interruption

Capacity/quota interruption after semantic start is a lifecycle pause, not automatically a semantic failure or repair-budget event.

```text
QUOTA_BOUNDARY_INTERRUPTION=EXPECTED_CAPACITY_PAUSE
SEMANTIC_FAILURE_FROM_CAPACITY_PAUSE=NO
APPLICATION_REPAIR_BUDGET_CONSUMED=NO
AUTOMATIC_RERUN_FROM_SCRATCH=NO
```

Before or during resumable material model work persist the task/packet identity, exact workspace, session/thread identity when exposed, model/tool shape, last durable worktree checkpoint, current diff/artifact identity, validation state and next pending step.

After capacity returns:
1. verify same task/authority/workspace/model-tool shape and no unexpected drift;
2. resume the exact session/thread when recoverable;
3. otherwise start a fresh continuation bound to the existing durable checkpoint, not the original task from scratch;
4. ambiguous/conflicted state => control reconciliation / SAFE_STOP.

### 7.1 Harness and persisted-state boundary proof

A rehearsal harness, fake, adapter wrapper or test double that remains on the production path must satisfy the exact seam contract it replaces or decorates. Before an external/provider or one-shot proof, verify as applicable:

```text
CALL_SIGNATURE
INPUT_TYPES
OUTPUT_TYPES
ENCODING / SERIALIZATION OWNERSHIP
ERROR / EXCEPTION CONTRACT
STATE / RESOURCE OWNERSHIP
OBSERVATION_PHASE / LIFECYCLE_STATE
TEMPORAL_STATE_VALIDITY
TEARDOWN / RESET SEMANTICS
TEARDOWN_SURVIVING_EVIDENCE
```

A harness that double-decodes, double-encodes, changes bytes into objects, changes exception ownership, observes a transient state outside its authoritative lifecycle phase or otherwise violates the seam invalidates the higher-level proof even when the provider/application itself behaved correctly.

Ephemeral live-state evidence must be captured during the authoritative observation phase. If graceful shutdown, teardown, reconnect cleanup or another reset legitimately clears or normalizes the state under test, preserve proof before that reset using a pre-reset immutable snapshot, monotonic event/counter, durable log/record or equivalent teardown-surviving evidence. Post-teardown normalized state must not be used to retroactively deny a pre-teardown readiness/transition already proven unless the governing contract explicitly defines that semantics.

Persisted-state copy and evidence identity must follow the owning component's durability model rather than filename heuristics. For SQLite WAL mode, the main database and any extant `-wal` file form part of the database's persistent state; `-shm` has different cache/index semantics. Do not blanket-delete or blanket-exclude `-wal` from a checkpoint copy. Prefer an engine-supported consistent snapshot/backup or a controlled quiescent copy that preserves the required durability set.

### 7.2 Completed semantic checkpoint + local Git publication failure

When a semantic action is already complete and exact head/tree/scope evidence exists, local GitHub transport failure is not authority to repeat the semantic action. For this repository also load the GitHub Local Transport / Reviewed-PR Closeout procedure.

```text
SEMANTIC_CHECKPOINT_ALREADY_COMPLETE
AND LOCAL_GITHUB_TLS_OR_API_PATH_PROVEN_UNRELIABLE
=> RERUN_SEMANTIC_ACTION=NO
=> LOOP_LOCAL_PUBLICATION_RETRIES=NO
=> PRESERVE_EXACT_CHECKPOINT=YES
=> CHECK_AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE=YES
```

If an authoritative connected GitHub write surface is available and provides equal or higher fidelity, prefer exact offline artifact egress plus provider-native remote publication. If it is unavailable, stop at the transport capability boundary; do not weaken credentials, force semantics or exact identity. Earlier successful authentication, `ls-remote`, or read-only API access does not prove the later mutation route is healthy.

---

## 8. Command repair budget

```text
INITIAL_GENERATED_COMMAND
-> AT MOST ONE BOUNDED COMMAND CORRECTION
-> SECOND AVOIDABLE COMMAND/WRAPPER DEFECT IN SAME STAGE
   => CURRENT_LAUNCHER_FAMILY=TERMINATED
   => FURTHER_INCREMENTAL_CORRECTION=PROHIBITED
   => COMMAND_RELIABILITY_HOLISTIC_REGENERATION
```

Renaming/regenerating the ZIP/script without changing the responsibility topology does not reset this counter. The lineage is keyed to the bounded stage + launcher responsibility family, not the filename.

Holistic regeneration requires:

- re-read actual environment and canonical workflow;
- classify every prior command failure;
- compare the replacement against the incident catalogue and prove non-regression controls;
- remove stale assumptions rather than append conditionals;
- reconsider the validation environment;
- prefer existing accepted capability / provider-native / mature tools;
- regenerate one complete replacement;
- repeat this reliability gate.

A pre-semantic command defect does not consume the application's semantic repair budget, but it must be recorded as a tooling/command incident.

---

## 9. Evidence egress

If independent review requires a returned artifact, evidence delivery is part of workflow completion.

Before expensive execution, when the route is materially uncertain, prove:

```text
EVIDENCE_OUTPUT_PATH
OWNER / MODE / DIRECTORY ACCESS
TRANSFER_SURFACE
EXPECTED_DOWNLOAD_OR_FETCH_ROUTE
FALLBACK_PATH
```

After generation prove as applicable:

```text
EXACT_FILE_EXISTS=YES
EXACT_FILE_SHA256=
EXACT_FILE_SIZE=
LOGIN_USER_READABLE=YES
PARENT_DIRECTORY_TRAVERSABLE=YES
CLIENT_VISIBILITY_OR_DOWNLOAD=PASS
```

For FinalShell/SFTP, refresh the file-manager view before inferring that a newly created server file is absent.

If egress fails after the semantic action, repair only egress; do not repeat the semantic action.

---

## 10. Failure classification before another command

Before issuing another command after failure record:

```text
COMMAND_FAILURE_CLASS=
  ENVIRONMENT_CAPABILITY_MISMATCH
  WRONG_VALIDATION_ENVIRONMENT
  CLI_OR_SHELL_TRANSPORT_DEFECT
  FALSE_SAFE_STOP_GATE
  ARTIFACT_IDENTITY_OR_RELEASE_REBIND_FAILURE
  AUTHORITY_OR_SAFETY_BLOCK
  DEPLOYMENT_MECHANIC_FAILURE
  WRAPPER_OR_HARNESS_FAILURE
  APPLICATION_OR_STRATEGY_FAILURE
  EVIDENCE_PACKAGING_OR_EGRESS_FAILURE
  PERSISTED_STATE_COPY_OR_IDENTITY_FAILURE
  UNKNOWN

SEMANTIC_ACTION_STARTED=YES|NO
SEMANTIC_ACTION_COMPLETED=YES|NO
MUTATION_STATE=
LAST_ACCEPTED_CHECKPOINT=
RESUME_FROM=
RERUN_SEMANTIC_ACTION=YES|NO
```

Do not issue the next mutation/retry until the class and resume checkpoint are explicit.

---

## 11. Compact incident catalogue

These incidents are retained as rationale/examples; the normative lessons live in V4.

| Incident | Failure class | Durable lesson |
| --- | --- | --- |
| macOS command required unavailable GNU `sha256sum` | environment/tool assumption | prove target tools; prefer standard/native cross-platform primitive |
| target-host wrapper required `.git` on exact-artifact/SFTP deployment | deployment-model mismatch | identity proof must match actual deployment transport |
| release script retained stale hard-coded manifest count | duplicated release identity | one canonical release identity + cross-artifact semantic proof |
| long heredoc appeared stuck at continuation prompt | operator input transport fragility | file-backed scripts for long/critical workflows |
| evidence existed server-side but not visible in FinalShell UI | evidence-egress/client-state failure | server proof + client visibility/download are separate |
| Issue #139 launcher hard-required local `git fetch` after fresh connector race-check | redundant false preflight | do not add lower-reliability duplicate proof without real safety value |
| Issue #139 OpenCode `--file`/message construction produced `File not found` | unproven CLI invocation semantics | prove exact CLI input contract before launch |
| Issue #139 used ad-hoc single-script Mypy | validation topology mismatch | reuse repo/CI canonical validation command |
| canonical repo Mypy then ran on macOS and hit `os.listxattr` | wrong validation environment | platform-sensitive proof runs on authoritative OS |
| repair allowlist required both files to change | false exactness | allowlist means changed-path subset unless semantic minimum says otherwise |
| evidence file generated only after fragile validation tails | checkpoint ordered too late | preserve semantic delta/evidence before non-decisive tails |
| S1 resume launcher hard-coded an incorrect self-generated expected SHA and false-stopped before execution | false SAFE_STOP / duplicated identity | an expected identity must be derived or independently checked from the exact object it gates; do not invent duplicate exactness |
| S1 bounded correction pasted comment lines into ordinary interactive zsh without proving `INTERACTIVE_COMMENTS` | shell parse-mode assumption | interactive command syntax must not depend on unproven shell startup options; omit comments or establish parse mode |
| S1 holistic regeneration re-embedded a long file-backed script as one giant Base64 literal and the paste arrived with invalid padding | operator transport fragility | file-backed transport must actually reduce operator-input complexity; giant encoded payloads do not satisfy the rule |
| S1 next regeneration used one giant quoted `zsh -fc` string and the paste truncated inside an unterminated quote | operator transport fragility | a large one-line command is not a safe substitute for a long heredoc; bootstrap must be materially simpler and parse-complete |
| S1 public-provider harness returned an already-decoded list where the production `HttpPost` seam required raw bytes | wrapper/harness contract mismatch | prove exact seam input/output/encoding ownership before external rehearsal |
| S1 checkpoint evidence logic treated SQLite WAL/SHM by filename suffix and a follow-up copy excluded `-wal` | persisted-state copy/identity failure | durable-state manifests/copies follow engine semantics; SQLite WAL may contain committed state and cannot be blanket-excluded |
| S1 attempt #2 sampled `RuntimeHealth` only after graceful teardown had cleared connection/ACK/data-ready state and treated normalized `SHUTDOWN` values as evidence live readiness never occurred | wrapper/harness observation-phase mismatch | ephemeral state evidence must be captured in the authoritative lifecycle phase or preserved by teardown-surviving monotonic evidence; post-teardown normalization cannot negate prior readiness |
| R3 publication local Git HTTPS failed with LibreSSL `SSL_ERROR_SYSCALL`, then authenticated `gh api` failed with EOF after earlier read success | local transport health / checkpoint publication failure | prior connectivity/auth success is not mutation-path health proof; after a completed semantic checkpoint stop local retry loops and prefer exact artifact egress + authoritative remote publication when available |

A reusable new lesson should update V4 or this narrow procedure rather than relying on chat memory.

When a newly observed incident matches an existing row or durable class, explicitly mark it as a **known-class recurrence**. Recurrence is evidence that the preventive gate was not operationally enforced; do not mislabel it as a novel edge case merely because the exact command text differs.

---

## 12. Authority boundary

This procedure never grants Mark Ready, merge, deployment, production/cloud mutation, service start/restart/enable/reboot, credential/private API, wallet/signing, exchange write/order submission or trading authority. Those remain separate current user gates.
