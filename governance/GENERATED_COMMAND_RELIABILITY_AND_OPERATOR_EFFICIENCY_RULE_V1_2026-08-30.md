# Trader Assist / Trade OS — Generated Command Reliability and Operator Procedure V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-08-30  
**Normative owner:** `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`

This file operationalizes the Unified V2 rules for project-generated commands, launchers, one-paste Terminal blocks, local automation, target-host execution and evidence-return workflows. It is also the compact incident catalogue for command-generation failures.

It does **not** create a competing project-wide constitution. Unified V2 governs conflicts.

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
SYNTAX_CHECK=PASS|FAIL|NOT_AVAILABLE
STATIC_ANALYSIS=PASS|FAIL|NOT_AVAILABLE
SAFE_STOP_GATES_BOUND_TO_REAL_INVARIANTS=YES|NO
ALLOWLIST_SEMANTICS_PROOF=PASS|FAIL|NOT_APPLICABLE

ONE_SHOT_SEMANTIC_BOUNDARY=
SIDE_EFFECT_FREE_PREFLIGHT_COMPLETE_BEFORE_ONE_SHOT=YES|NO|NOT_APPLICABLE
CHECKPOINT_RESUME_PLAN=
POST_SEMANTIC_EVIDENCE_CHECKPOINT_PLAN=

EVIDENCE_OUTPUT_PATH=
EVIDENCE_EGRESS_PLAN=PASS|FAIL|NOT_APPLICABLE
EXPECTED_IRREDUCIBLE_USER_INTERACTIONS=
COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION
```

Do not deliver a nontrivial command with `GENERATED_COMMAND_RELIABILITY_GATE=FAIL`.

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

A known platform mismatch is a routing input. Do not keep rewriting commands merely to make the wrong platform pass.

---

## 5. No false SAFE_STOP or false exactness

Every fail-closed gate must protect a real authority, identity, safety, state or correctness invariant.

Prohibited patterns:

- checking incidental source formatting instead of the authoritative object/state;
- requiring redundant lower-reliability network proof after fresh authoritative control-plane GitHub identity when it adds no safety value;
- treating a missing convenience tool as safety failure when a proven native/standard alternative gives the same proof;
- requiring a target artifact to be a Git checkout when the canonical deployment is exact-artifact/SFTP;
- interpreting an allowlist as a requirement that every allowed path must change.

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

---

## 8. Command repair budget

```text
INITIAL_GENERATED_COMMAND
-> AT MOST ONE BOUNDED COMMAND CORRECTION
-> SECOND AVOIDABLE COMMAND/WRAPPER DEFECT IN SAME STAGE
   => COMMAND_RELIABILITY_HOLISTIC_REGENERATION
```

Holistic regeneration requires:

- re-read actual environment and canonical workflow;
- classify every prior command failure;
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

These incidents are retained as rationale/examples; the normative lessons live in Unified V2.

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

A reusable new lesson should update Unified V2 or this narrow procedure rather than relying on chat memory.

---

## 12. Authority boundary

This procedure never grants Mark Ready, merge, deployment, production/cloud mutation, service start/restart/enable/reboot, credential/private API, wallet/signing, exchange write/order submission or trading authority. Those remain separate current user gates.