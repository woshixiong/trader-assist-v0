# Trader Assist / Trade OS — Generated Command Reliability and Operator Efficiency Rule V1

**Status:** CANONICAL GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-30  
**Repository:** `woshixiong/trader-assist-v0`

## 1. Purpose

This rule governs every project-generated command, launcher, one-paste Terminal block, shell script, local automation block, target-host execution block, evidence-collection command, and operator-facing repair/continuation command that a human is expected to execute.

The purpose is to reduce avoidable engineering delay caused by:

- platform or shell assumptions that were never verified;
- forcing work through an unsuitable local macOS environment when a clean Linux validation surface is available;
- versioned CLI argument/input semantics being guessed from flag names rather than proven from the installed/authoritative command surface;
- ad-hoc validation commands that differ from repository/CI canonical validation topology;
- platform-sensitive validation being run on a non-authoritative OS and misclassified as an application defect;
- false `SAFE_STOP` gates that do not protect a real authority/safety invariant;
- allowlist maximum scope being misread as a requirement that every allowlisted path must change;
- long interactive heredocs that are fragile to copy/paste or terminal state;
- repeated CONT1/CONT2/CONT3 patch chains instead of convergence;
- one-shot qualification attempts being consumed by wrapper/deployment defects before the intended semantic action starts;
- rebuilding or rerunning already-completed expensive work after a downstream wrapper/evidence failure;
- failing to checkpoint a completed semantic Writer delta before non-decisive validation/evidence tails;
- incomplete release rebinding or duplicated release-sensitive constants across generated artifacts;
- evidence being generated successfully but not retrievable through the operator's actual transfer surface;
- requiring the user to diagnose raw launcher state or repeatedly relay command fragments.

This rule strengthens, but does not replace:

- `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`;
- `MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`;
- `HOLISTIC_ENGINEERING_VERIFICATION_CONTINUITY_AND_RELEASE_METHOD_V1_2026-08-31.md`;
- `ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`;
- `FINALSHELL_TARGET_HOST_DEPLOYMENT_WORKFLOW_V1_2026-08-26.md`;
- current task-specific Product / Strategy / Operations / Security authority.

It grants no Mark Ready, merge, deployment, runtime/cloud, credential/private-API, wallet/signing, exchange-write, order-submission or trading authority.

---

## 2. Incident evidence that motivated this rule

The 2026-08-30 Issue #131 exact-release requalification workflow and the 2026-08-31 Issue #139 OpenCode/validation continuation exposed several distinct command-generation failure classes. They must not be collapsed into one generic “script failed” label.

| Incident | Observed result | Failure class | Permanent lesson |
| --- | --- | --- | --- |
| Local package verification required literal `G12_FULL_RUN_COUNT=1` in source | `SAFE_STOP: SINGLE_FULL_RUN_PROOF_MISSING` | false static proof / over-constrained validator | runtime-result fields must not be required as literal source text when accepted control-flow/artifact evidence proves the intended invariant |
| macOS continuation required `sha256sum` | `SAFE_STOP: LOCAL_TOOL_MISSING:sha256sum` | unverified platform/tool assumption | target OS/shell/tool capability must be proven before delivery; cross-platform primitives should prefer standard-library implementations or verified native tools |
| target-host wrapper required `/opt/trader-assist-v0/.git` | `SAFE_STOP: CURRENT_DEPLOYMENT_NOT_GIT_CHECKOUT` | deployment-model assumption contradicted by canonical artifact/SFTP workflow | identity proof must match the actual deployment transport; an exact artifact manifest is valid authority when the canonical route does not require a host Git checkout |
| new-release `run_g12.sh` retained a stale hard-coded source-manifest entry count of `287` while the new exact release manifest/identity contained `288` files | `SAFE_STOP: SOURCE_MANIFEST_ENTRY_COUNT_MISMATCH`; deployment was not reached; warmup/full G12 were not reached; `G12_FULL_RUN_COUNT=0` | incomplete release rebinding / duplicated release-sensitive constant / cross-artifact semantic inconsistency | release-sensitive values require one source of truth; mechanical template equality does not prove semantic rebinding completeness; cross-artifact semantic consistency and stale-literal scanning must pass before target-host one-shot execution |
| diagnostic collection paste appeared “stuck” at the heredoc terminator | FinalShell remained at continuation prompt until one final Enter | interactive heredoc/operator-UX fragility | long critical scripts should be file-backed; if a heredoc is unavoidable, termination/newline behavior must be explicit and the user must be told what a continuation prompt means |
| diagnostic archive was created with readable mode but could not be seen/downloaded immediately through the user's FinalShell file-manager view | evidence existed but client visibility/download was not established | evidence-egress path/client-state not proven | evidence delivery is part of workflow acceptance; server-side existence alone is insufficient, and a stale file-manager view must be refreshed before absence is inferred |
| Issue #139 OpenCode launcher required local `git fetch origin main` even after Engineering Control had a fresh authoritative GitHub connector race-check | `SAFE_STOP: FETCH_ORIGIN_MAIN_FAILED` before semantic Writer start | redundant network dependency / false preflight gate | do not add a second less-reliable proof path when the authoritative control-plane identity is already fresh and the local exact HEAD/origin can be verified without network |
| Issue #139 OpenCode launcher used `--file` while also passing a trailing natural-language argument | OpenCode 1.18.18 reported `File not found: Read the attached Task Packet...` before semantic Writer start | unproven CLI invocation/argument contract | prove the exact installed CLI invocation shape and input transport; a flag existing is not proof of its argument semantics |
| Issue #139 validation used `mypy --strict scripts/verify_exact_release.py` rather than the repository/CI command | self-package imports were treated as untyped installed third-party modules | ad-hoc validation topology mismatch | use repository/CI canonical validation commands when they exist; do not invent a stricter/narrower local substitute and call its failure an application blocker |
| Issue #139 then ran canonical `mypy src scripts` on macOS | `os.listxattr` platform typing failure in an unrelated Linux-oriented script | wrong authoritative validation environment | platform-sensitive validation must run on the authoritative platform class; macOS cannot substitute for Ubuntu/Linux CI when the proof depends on `sys.platform`/OS APIs |
| Issue #139 validation tail required both repair-allowlisted files to change | `expected exactly two repair files changed` even though only the implementation file legitimately changed | false scope exactness | an allowlist proves `CHANGED_PATHS ⊆ ALLOWLIST`; it does not require every allowed path to change unless the semantic contract says so |
| Issue #139 evidence file was generated only after multiple non-decisive validation tails | repeated tail failures prevented review TXT creation despite a completed bounded Writer delta | evidence checkpoint ordered too late | preserve exact semantic Writer delta/identity evidence immediately after scope proof and before environment-sensitive/non-decisive validation tails |

The early wrapper/preflight failures above are avoidable generated-command defects, not Trader Assist application failures. The OpenCode semantic repair completed only once the wrapper reached the declared semantic boundary. Later validation-environment failures must not be reclassified as Writer failures or used to rerun a completed semantic attempt when its exact delta remains provable.

---

## 3. Universal pre-delivery command reliability gate

Before any nontrivial generated command is presented to the user, the controlling role must record:

```text
GENERATED_COMMAND_RELIABILITY_GATE=PASS|FAIL
TASK=
EXECUTION_SURFACE=MACOS_TERMINAL|GITHUB_ACTIONS_UBUNTU|ISOLATED_LIGHTSAIL_LINUX|FINALSHELL_TARGET_HOST|LOCAL_RUNNER|OTHER
TARGET_OS=
TARGET_SHELL=
TARGET_SHELL_VERSION=
PRIVILEGE_MODEL=
CANONICAL_WORKFLOW=
LOCAL_ENVIRONMENT_FIT=PASS|FAIL|NOT_APPLICABLE
VALIDATION_ENVIRONMENT_ROUTE=
VALIDATION_PLATFORM_CLASS=PLATFORM_NEUTRAL|MACOS|LINUX|TARGET_HOST_SPECIFIC|OTHER|NOT_APPLICABLE
AUTHORITATIVE_VALIDATION_ENVIRONMENT=
CANONICAL_VALIDATION_COMMANDS=
KNOWN_ENVIRONMENT_MISMATCHES=
LINUX_FALLBACK_REASON=
REQUIRED_TOOLS=
REQUIRED_TOOLS_PROVEN=YES|NO
CLI_INVOCATION_CONTRACT_PROOF=PASS|FAIL|NOT_APPLICABLE
CLI_INPUT_TRANSPORT=
OS_SHELL_PORTABILITY_REVIEW=PASS|FAIL
SCRIPT_TRANSPORT=FILE_BACKED|SHORT_INLINE|HEREDOC_EXCEPTION
SYNTAX_CHECK=PASS|FAIL|NOT_AVAILABLE
STATIC_ANALYSIS=PASS|FAIL|NOT_AVAILABLE
SAFE_STOP_GATES_BOUND_TO_CANONICAL_INVARIANTS=YES|NO
ALLOWLIST_SEMANTICS_PROOF=PASS|FAIL|NOT_APPLICABLE
RELEASE_SENSITIVE_SINGLE_SOURCE_OF_TRUTH=PASS|FAIL|NOT_APPLICABLE
CROSS_ARTIFACT_SEMANTIC_CONSISTENCY=PASS|FAIL|NOT_APPLICABLE
STALE_RELEASE_LITERAL_SCAN=PASS|FAIL|NOT_APPLICABLE
ONE_SHOT_SEMANTIC_BOUNDARY=
SIDE_EFFECT_FREE_PREFLIGHT_COMPLETE_BEFORE_ONE_SHOT=YES|NO|NOT_APPLICABLE
CHECKPOINT_RESUME_PLAN=
POST_SEMANTIC_EVIDENCE_CHECKPOINT_PLAN=
EVIDENCE_EGRESS_PATH=
EVIDENCE_EGRESS_PLAN=PASS|FAIL|NOT_APPLICABLE
EVIDENCE_EGRESS_PREFLIGHT=PASS|FAIL|NOT_APPLICABLE
EVIDENCE_EGRESS_CANARY_OR_DIRECTORY_PROOF=PASS|FAIL|NOT_APPLICABLE
EVIDENCE_EGRESS_SERVER_PROOF=PENDING_POST_RUN|NOT_APPLICABLE
EVIDENCE_EGRESS_CLIENT_VISIBILITY=PENDING_POST_RUN|NOT_APPLICABLE
EXPECTED_IRREDUCIBLE_USER_INTERACTIONS=
COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION
```

A nontrivial generated command must not be delivered with `GENERATED_COMMAND_RELIABILITY_GATE=FAIL`.

Pre-delivery egress fields prove the **route and capability to return future evidence**, not the existence of an evidence artifact that has not yet been generated. `EVIDENCE_EGRESS_SERVER_PROOF` and `EVIDENCE_EGRESS_CLIENT_VISIBILITY` are final post-execution proofs; before execution they must be `PENDING_POST_RUN` when evidence return is required, or `NOT_APPLICABLE` when it is not.

A task that begins as mechanical command generation but exposes a new architecture, authority, deployment model, persistence, retry, recovery or semantic design decision becomes MATERIAL and must return to the full Engineering Preflight Gate.

---

## 4. Target environment must be evidence, not assumption

Before generating a command that depends on platform-specific behavior, establish the actual environment from current accepted evidence or a minimal read-only probe.

Applicable facts include:

```text
OS / distribution / version
CPU architecture when relevant
shell implementation + version
interactive vs non-interactive execution
available command names / versions
Python/runtime version where used
current privilege / sudo shape
filesystem paths
service manager
artifact vs Git-checkout deployment model
file-transfer/evidence-return surface
```

Rules:

1. Do not assume GNU utility names on macOS or BSD utility behavior on Linux.
2. Do not assume a host is a Git checkout when the accepted deployment workflow uses exact transferred artifacts.
3. Do not assume a newer Bash feature is available merely because the prompt is being entered from zsh or another shell.
4. When one implementation can avoid platform variance, prefer a stable standard-library primitive such as Python `hashlib` over branching on unverified external utilities.
5. If a platform capability is unknown and decisive, issue the smallest read-only probe first rather than embedding an unverified assumption into a large mutation command.
6. A known local-environment incompatibility is a routing input, not a reason to keep patching the same local command indefinitely.
7. Do not require a local network check when a fresh authoritative control-plane GitHub identity already proves the live remote state and the current action only needs local exact-head/origin identity; redundant proof must have independent safety value to be a hard gate.

The probe itself must be short, non-mutating and reusable as exact input to the next command generation step.

### 4.1 Exact CLI invocation contract proof

For a versioned CLI whose argument/input semantics affect a model launch, deployment, evidence collection or other material action, prove the exact invocation shape before delivery.

Where applicable record:

```text
CLI_NAME=
CLI_VERSION=
CLI_SUBCOMMAND=
POSITIONAL_ARGUMENT_SEMANTICS=
FILE_ARGUMENT_SEMANTICS=
STDIN_SEMANTICS=
WORKING_DIRECTORY_SEMANTICS=
MODEL_OR_PROVIDER_ID_SEMANTICS=
OUTPUT_MODE_SEMANTICS=
EXACT_INVOCATION_SHAPE=
```

Rules:

- `--help` showing a flag exists is not enough when the flag may mean attachment/file input rather than prompt transport;
- prefer provider-native documented invocation shapes and the installed version's actual help/schema;
- statically inspect the final generated invocation for forbidden/ambiguous transport combinations where practical;
- freeze the exact model/provider ID when the route requires no fallback;
- do not silently change positional/file/stdin transport after route freeze.

Permanent invariant:

```text
CLI_INVOCATION_CONTRACT_PROOF=REQUIRED_FOR_VERSIONED_MATERIAL_CLI_LAUNCHES
```

---

## 5. Validation environment fidelity and Linux fallback ladder

Validation is authoritative only when both the command topology and environment match the contract being claimed.

Before material validation:

```text
CANONICAL_VALIDATION_COMMANDS=
VALIDATION_PLATFORM_CLASS=
AUTHORITATIVE_VALIDATION_ENVIRONMENT=
KNOWN_ENVIRONMENT_MISMATCHES=
LOCAL_ENVIRONMENT_FIT=
FALLBACK_VALIDATION_SURFACE=
```

Permanent invariants:

```text
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY_GATE=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_NONAUTHORITATIVE_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
NO_LOCAL_RETRY_AFTER_PROVEN_PLATFORM_MISMATCH=REQUIRED
```

If repository configuration or CI already defines the canonical command, reuse it unless a narrower command is explicitly proven semantically equivalent for the exact claim. Do not invent an ad-hoc stricter/narrower command and elevate its failure into a new application blocker.

When validation semantics depend on `sys.platform`, OS APIs, filesystem permissions, systemd, kernel behavior, Linux utilities or another platform-specific capability, run that proof on the authoritative platform class. A macOS result does not replace Ubuntu/Linux CI proof; Ubuntu hosted CI does not replace target-host-specific qualification.

When the user's local macOS environment cannot faithfully or efficiently validate Linux-targeted commands because of OS, shell, utility, architecture, dependency or packaging differences, do not repeatedly patch around the incompatibility.

Use the narrowest adequate validation surface in this order:

```text
1. LOCAL_MACOS
   when the required behavior is platform-neutral or macOS-compatible

2. EXISTING_GITHUB_ACTIONS_UBUNTU
   when isolated Linux shell/runtime/package/test behavior is sufficient

3. ISOLATED_LIGHTSAIL_LINUX_VALIDATION_ENVIRONMENT
   when real Linux/systemd/network/kernel/privilege or target-distribution behavior is required and hosted CI is insufficient

4. CURRENT_PRODUCTION_LIGHTSAIL_TARGET_HOST
   only for target-host-specific read-only checks or a separately authorized bounded deployment/qualification
```

Permanent invariants:

```text
LOCAL_ENVIRONMENT_CONFLICT_CAN_TRIGGER_LINUX_FALLBACK=YES
PRODUCTION_HOST_AS_GENERIC_DEVELOPMENT_SANDBOX=NO
GITHUB_ACTIONS_UBUNTU_PREFERRED_FOR_GENERIC_LINUX_VALIDATION=YES_WHEN_FIT
ISOLATED_LIGHTSAIL_PREFERRED_OVER_PRODUCTION_HOST_FOR_HOST_LIKE_MUTATING_TESTS=YES
TARGET_HOST_MUTATION_REQUIRES_CURRENT_EXPLICIT_AUTHORITY=YES
LIGHTSAIL_INSTANCE_CREATE_STOP_DELETE_REQUIRES_CURRENT_EXPLICIT_CLOUD_AUTHORITY=YES
VALIDATION_ENVIRONMENT_MUST_NOT_BECOME_SECOND_PRODUCTION_AUTHORITY=YES
```

### GitHub Actions Ubuntu

Use an existing accepted GitHub Actions Ubuntu runner when the needed proof is ordinary Linux command compatibility, Python/runtime behavior, packaging, shell syntax/static analysis, or repository tests and the runner exposes the required capability.

A hosted runner is preferred over production-host testing because it is isolated and disposable. Do not create a new permanent CI platform merely for one command check; use the existing workflow/capability when it fits.

### Isolated Lightsail Linux

If hosted CI cannot reproduce decisive target-host behavior, an isolated Lightsail Linux validation environment may be proposed or used under current explicit cloud authority.

Prefer, in order of fit:

- a separately designated non-production Lightsail instance;
- a temporary instance created from an accepted snapshot when matching host shape materially matters;
- another explicitly isolated Linux instance whose identity and purpose are frozen before use.

The validation instance must have:

```text
ENVIRONMENT_ROLE=NON_PRODUCTION_VALIDATION
SOURCE_OR_SNAPSHOT_IDENTITY=
OS_DISTRIBUTION_VERSION=
TEST_SCOPE=
PROHIBITED_PRODUCTION_STATE=
CREDENTIAL_BOUNDARY=
CLEANUP_OR_RETENTION_PLAN=
```

Do not copy real production credentials, private/account APIs, wallets, signing material, production databases, or live notification secrets merely to make the validation environment convenient.

### Current production Lightsail host

The current production/qualification host may not be silently reused as a generic development sandbox.

Without separate current mutation authority, only read-only target-host probes are allowed. Any package installation, service mutation, file replacement outside an already authorized staging area, production Registry/DB mutation, runtime start/stop, network/service change, or qualification remains subject to the normal user-retained authority gates.

The purpose of the Linux fallback is to increase first-pass command correctness, not to weaken production isolation.

Primary external evidence:

- GitHub-hosted runners reference: `https://docs.github.com/en/actions/reference/runners/github-hosted-runners`
- AWS Lightsail Linux/Unix SSH administration: `https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-connect-to-your-instance-virtual-private-server.html`
- AWS Lightsail create instance from snapshot: `https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-instance-from-snapshot.html`

---

## 6. File-backed execution is the default for long, critical or one-shot scripts

For any multi-phase, production-mutating, qualification, deployment, model-launch, one-shot, or otherwise high-cost command sequence:

```text
LONG_CRITICAL_LOGIC_IN_INTERACTIVE_TERMINAL_HEREDOC=AVOID_BY_DEFAULT
FILE_BACKED_SCRIPT=DEFAULT
SCRIPT_INCLUDED_IN_HASH_MANIFEST=YES_WHERE_ARTIFACT_WORKFLOW_APPLIES
TERMINAL_PASTE=SHORT_VERIFY_AND_EXECUTE_LAUNCHER
```

Preferred shape:

```text
GENERATE OR PACKAGE SCRIPT AS A FILE
-> CLOSE ALL HEREDOC/INPUT TRANSPORT
-> HASH / MANIFEST THE SCRIPT
-> RESOLVE RELEASE-SENSITIVE VALUES FROM ONE CANONICAL SOURCE
-> CROSS-CHECK GENERATED ARTIFACT SEMANTICS / STALE RELEASE LITERALS
-> SYNTAX / STATIC VALIDATE THE FILE
-> WHEN LINUX-TARGETED, REHEARSE ON THE SELECTED SAFE LINUX VALIDATION SURFACE WHEN PRACTICAL
-> TRANSFER FILE THROUGH THE ACCEPTED TRANSPORT
-> SHORT REMOTE/LOCAL LAUNCHER VERIFIES HASH
-> EXECUTE FILE NON-INTERACTIVELY
```

This extends the existing model-executor stdin-isolation rule: file-backed phase separation is valuable not only for Agents but also for production operator scripts because it prevents terminal input from becoming part of runtime control flow.

An inline heredoc remains acceptable for a short low-risk helper or when the execution environment genuinely requires it, but the closing delimiter/newline behavior and expected terminal prompt state must be explicit.

For the canonical FinalShell artifact workflow, if the remote execution logic is substantial, it should be included in the uploaded exact-release folder and hash manifest. The user's remote paste should normally be a short verification/launch wrapper rather than hundreds of lines of release logic reconstructed from chat.

---

## 7. Syntax and mature static analysis before delivery

For generated shell files or substantial shell blocks:

1. run the target shell's syntax checker where available, e.g. `bash -n` for Bash;
2. use ShellCheck or an equivalent mature shell static analyzer when it is available in the generation/review environment and applicable to the target shell dialect;
3. configure/check against the intended shell dialect rather than silently assuming Bash/POSIX compatibility;
4. do not make the production target host depend on installing a new static-analysis tool merely to execute an otherwise ready release;
5. record `NOT_AVAILABLE` honestly when static analysis cannot be run, and compensate with narrower syntax/portability checks or the Linux validation fallback rather than inventing custom pseudo-lint rules;
6. for Linux-targeted commands whose correctness materially depends on GNU/systemd/Linux behavior, prefer a real Linux validation run before asking the user to execute the production-facing command.

ShellCheck is preferred over custom commodity lint logic for shell portability/pitfall detection. Project-specific safety/authority checks remain project-owned and may supplement, not replace, mature shell analysis.

Primary references:

- ShellCheck official project/manual: `https://github.com/koalaman/shellcheck`
- GNU Bash Reference Manual: `https://www.gnu.org/software/bash/manual/`

---

## 8. No false SAFE_STOP gates

`SAFE_STOP` remains mandatory for real authority, identity, safety, state or correctness uncertainty. It must not be weakened merely to improve success rate.

However, every generated-command fail-closed gate must map to a real invariant:

```text
GATE_ID=
AUTHORITY_OR_INVARIANT_SOURCE=
WHAT_EXACTLY_IS_PROVEN=
WHY_FAILURE_BLOCKS_THE_CURRENT_ACTION=
```

Prohibited false-gate patterns include:

- requiring a runtime result field to exist as literal source text when exact accepted control-flow evidence proves the same invariant;
- treating one historical deployment example as the only legal deployment identity mechanism when current canonical governance permits an exact artifact manifest;
- treating a missing convenience tool as a safety failure when an already-available standard/native primitive or approved Linux validation surface can provide the exact proof;
- checking implementation formatting or incidental source shape instead of the actual authoritative artifact/state;
- creating stricter ad-hoc proof requirements that are not derived from Product / Strategy / Security / Operations / Engineering authority;
- interpreting an allowlist as a requirement that every allowlisted path must change;
- requiring a redundant local-network proof when fresh authoritative control-plane state plus local exact identity already proves the current invariant.

The goal is not fewer `SAFE_STOP`s. The goal is that each `SAFE_STOP` protects a real boundary and therefore saves time rather than wasting it.

### 8.1 Allowlist semantics are set membership, not exact change count

Unless the active semantic contract explicitly requires named paths to change:

```text
ALLOWLIST_PROOF:
CHANGED_PATHS ⊆ ALLOWLIST
```

A path being permitted to change does not mean it must change. A narrow repair may legitimately modify one of two allowlisted files while proving the other remained byte-identical.

Permanent invariant:

```text
ALLOWLIST_PROOF_IS_SET_MEMBERSHIP_NOT_CHANGE_COUNT=REQUIRED
```

### 8.2 Release-sensitive values require one source of truth and semantic rebinding proof

Release-specific values must not be copied into multiple generated artifacts as independent hard-coded truths when one canonical source can be parsed or derived.

Release-sensitive values include, where applicable:

```text
release SHA / tree
source manifest hash / entry count
package / artifact identity
CI run/head identity
Registry version / content hash
provider/market identity assertions
other exact-release constants that change between accepted releases
```

Required invariants:

```text
RELEASE_SENSITIVE_SINGLE_SOURCE_OF_TRUTH=PASS
CROSS_ARTIFACT_SEMANTIC_CONSISTENCY=PASS
STALE_RELEASE_LITERAL_SCAN=PASS
MECHANICAL_REBIND_EQUALS_SEMANTIC_REBIND_PROOF=NO
```

Preferred implementation:

- derive counts/hashes/identities from a hash-protected manifest or release-identity file instead of duplicating literal values;
- if a generated script must contain a release-sensitive literal, generate it from the same canonical metadata and verify it against that metadata before execution;
- scan the final generated artifact set for stale old-release SHA/tree/hash/count/package/version literals where those literals are expected to disappear;
- compare semantic cross-artifact invariants, not only byte equality between a generated script and its template/heredoc.

For a source-manifest-backed release, at minimum prove when applicable:

```text
ACTUAL_MANIFEST_ENTRY_COUNT
== RELEASE_IDENTITY_SOURCE_FILE_COUNT
== GENERATED_DEPLOY_OR_RUN_SCRIPT_EXPECTATION_OR_DERIVED_VALUE
```

The preferred route eliminates the third independent value entirely by making the deploy/run script derive the count from the manifest or release identity.

`RUN_SCRIPT_EQUALS_GENERATOR_HEREDOC=PASS` proves generation fidelity only. It does **not** prove that every release-sensitive constant inside the generator was rebound correctly.

For production-facing one-shot execution, release-sensitive consistency checks must be exercised on the selected safe Linux validation surface before target-host execution when practical. A wrapper that cannot pass its release-sensitive preflight off-production is not eligible to consume a production semantic attempt.

---

## 9. Side-effect-free preflight must finish before a one-shot attempt is consumed

For expensive, irreversible, rate-limited, qualification or one-shot actions, split the workflow into explicit phases:

```text
PHASE 0 — READ-ONLY ENVIRONMENT / CAPABILITY PREFLIGHT
PHASE 1 — ARTIFACT / DEPLOYMENT / CONFIG PREPARATION AND VERIFICATION
PHASE 2 — REHEARSAL ON SAFE VALIDATION SURFACE WHERE PRACTICAL
PHASE 3 — SEMANTIC ONE-SHOT PREFLIGHT
PHASE 4 — CREATE ATTEMPT SENTINEL IMMEDIATELY BEFORE THE SEMANTIC ACTION
PHASE 5 — EXECUTE THE SEMANTIC ACTION EXACTLY ONCE
PHASE 6 — EVIDENCE / CLEANUP / ADJUDICATION
```

Everything that can be proven before the semantic attempt must be proven before the attempt sentinel or equivalent consumption boundary.

A deployment command failing before qualification starts must not be reported as a failed qualification. A wrapper failing before an application runtime starts must not be reported as an application runtime failure.

Attempt accounting must distinguish:

```text
PREFLIGHT_FAILURE
VALIDATION_ENVIRONMENT_FAILURE
DEPLOYMENT_FAILURE
WRAPPER_OR_HARNESS_FAILURE
SEMANTIC_ATTEMPT_STARTED
SEMANTIC_ATTEMPT_COMPLETED_PASS
SEMANTIC_ATTEMPT_COMPLETED_FAIL
POST_ACTION_EVIDENCE_OR_CLEANUP_FAILURE
```

Do not collapse all of these into a single exit code or generic `SAFE_STOP` label.

A wrapper-level sentinel may record that an operator execution was attempted, but it must not be conflated with semantic-attempt consumption. Semantic attempt accounting begins only at the declared semantic boundary after all applicable preflight/deployment/rehearsal gates have passed.

---

## 10. Checkpoint, evidence preservation and resume

Every multi-phase generated workflow must state the exact checkpoint after each expensive or authority-bearing phase.

If an upstream phase completed successfully and its exact artifact/state can still be verified, a downstream failure resumes from that checkpoint.

Examples:

- package generation PASS + metadata verification failure -> verify/reuse the exact package; do not regenerate source by default;
- semantic Writer completed + later deterministic validation failed -> do not rerun the Writer;
- deployment completed + evidence packaging failed -> prove deployment identity, then resume evidence collection rather than redeploying;
- one-shot semantic attempt completed + download failed -> repair only evidence egress; never repeat the semantic attempt merely to recreate a downloadable file;
- macOS validation fails because of a platform mismatch -> reroute validation to the approved Linux surface; do not rewrite otherwise platform-correct production logic merely to satisfy macOS.

For model-backed Writer work, once the semantic Writer has completed and exact mutation scope can be proven, create/preserve the minimum reviewable delta/identity evidence **before** running non-decisive platform-sensitive validation tails. Later environment/typing/lint/evidence failures must not make the semantic delta unrecoverable.

Permanent invariant:

```text
POST_WRITER_EVIDENCE_CHECKPOINT_BEFORE_NONDECISIVE_TAIL=REQUIRED
```

Hidden retry, silent rerun and “start again because the wrapper failed” are prohibited unless the active authority explicitly permits another semantic attempt.

---

## 11. Generated-command repair budget

Avoidable operator-command defects have their own bounded repair discipline and must not become an endless `CONT1 -> CONT2 -> CONT3` chain.

```text
INITIAL_GENERATED_COMMAND
-> AT MOST ONE BOUNDED COMMAND CORRECTION
-> IF A SECOND AVOIDABLE COMMAND/WRAPPER DEFECT APPEARS IN THE SAME STAGE:
   STOP PATCH CHAIN
   -> COMMAND_RELIABILITY_HOLISTIC_REGENERATION
```

`COMMAND_RELIABILITY_HOLISTIC_REGENERATION` requires:

- re-read the actual target environment facts;
- re-read the canonical workflow;
- classify every prior command failure;
- remove stale assumptions instead of adding more conditionals;
- reconsider whether the validation environment itself is wrong;
- prove the exact installed CLI invocation contract when a versioned CLI is involved;
- reuse canonical validation commands and authoritative platform classes;
- prefer a file-backed script / accepted project capability / mature tool / approved Linux validation surface;
- regenerate one complete replacement rather than another append-only patch;
- repeat the pre-delivery reliability gate.

A pre-semantic command defect does not automatically consume the application's implementation repair budget, but it must be recorded as an operator-command/tooling incident so the same defect is not rediscovered in another task.

Repeated command-generation defects across tasks trigger Tooling Control / holistic workflow convergence under Issue #115 or its successor authority.

---

## 12. Evidence egress is part of acceptance, not an afterthought

Evidence egress has two distinct proof phases. Do not require a final evidence artifact to exist before the action that generates it.

### Pre-delivery / pre-execution egress proof

Before an expensive target-host run, freeze and validate the evidence-return route:

```text
EVIDENCE_OUTPUT_PATH=
EVIDENCE_OWNER=
EVIDENCE_MODE=
TRANSFER_SURFACE=
EXPECTED_DOWNLOAD_OR_FETCH_ROUTE=
FALLBACK_PATH=
EVIDENCE_EGRESS_PLAN=PASS|NOT_APPLICABLE
EVIDENCE_EGRESS_PREFLIGHT=PASS|NOT_APPLICABLE
EVIDENCE_EGRESS_CANARY_OR_DIRECTORY_PROOF=PASS|NOT_APPLICABLE
EVIDENCE_EGRESS_SERVER_PROOF=PENDING_POST_RUN|NOT_APPLICABLE
EVIDENCE_EGRESS_CLIENT_VISIBILITY=PENDING_POST_RUN|NOT_APPLICABLE
```

`EVIDENCE_EGRESS_PREFLIGHT=PASS` proves that the intended directory/ownership/permissions/transfer surface are suitable for a future evidence artifact. It does not claim that the final evidence file already exists.

When evidence return is required and the transfer path is materially uncertain, prove the path before the semantic attempt with a tiny non-sensitive canary, a directory write/read/traverse proof, or an already-existing readable artifact when this can be done without materially increasing operator burden. The canary/directory proof is a capability proof, not final evidence proof.

For the current FinalShell/SFTP workflow, prefer an operator-readable directory under the login user's home, for example:

```text
/home/ubuntu/trade-os-evidence/<task-or-run-id>/
```

over a root-owned or UI-inconvenient temporary location when the evidence is intended for manual SFTP download.

`/tmp` may still be used for internal staging, but a final downloadable copy should be placed under the operator-readable evidence path before terminal success is declared.

### Post-execution server-side proof

Only after the final evidence artifact exists may `EVIDENCE_EGRESS_SERVER_PROOF` become `PASS`. Verify at minimum:

```text
EXACT_FILE_EXISTS=YES
EXACT_FILE_SHA256=
EXACT_FILE_SIZE=
OWNER_GROUP=
MODE=
LOGIN_USER_READABLE=YES
PARENT_DIRECTORY_TRAVERSABLE=YES
```

Do not infer success merely from a copy command returning zero.

### Post-execution client-side visibility/download proof

Only after the final evidence artifact exists may `EVIDENCE_EGRESS_CLIENT_VISIBILITY` become `PASS`.

A FinalShell/SFTP file-manager view may be stale after files are created from the terminal. Therefore:

1. refresh the file-manager directory before inferring that a newly created file is absent;
2. verify that the exact expected filename becomes visible in the intended directory;
3. when an evidence return is required for independent review, successful client visibility/download is part of workflow completion rather than an optional postscript;
4. if server-side proof passes but client visibility/download fails, classify `EVIDENCE_EGRESS_FAILURE` and repair only the transfer/client path.

The final result must print at least:

```text
EVIDENCE_PATH
EVIDENCE_SHA256
EVIDENCE_SIZE
EVIDENCE_OWNER_MODE
EVIDENCE_LOGIN_USER_READABLE
EVIDENCE_EGRESS_SERVER_PROOF
EVIDENCE_EGRESS_CLIENT_VISIBILITY
```

If the evidence file is successfully generated but cannot be retrieved, do not rerun the underlying semantic action.

---

## 13. Human-interaction and terminal-UX budget

The current project explicitly counts human relay and waiting as engineering cost.

Generated workflows should minimize irreducible operator actions. Default target:

```text
LOCAL_ENGINEERING=
ONE NORMAL TERMINAL PASTE WHEN SAFE

FINALSHELL_DEPLOYMENT=
ONE LOCAL PACKAGE GENERATION ACTION
-> ONE FOLDER UPLOAD
-> ONE SHORT HASH-VERIFY/EXECUTE SERVER LAUNCHER
-> ONE EVIDENCE DOWNLOAD/RETURN
```

Do not ask the user to:

- manually splice command fragments;
- retype hashes or JSON;
- diagnose raw launcher output that the control role can classify;
- repeatedly paste nearly identical scripts after avoidable wrapper defects;
- wait indefinitely without an expected duration/progress marker;
- infer whether a `>` continuation prompt means “running” versus “still waiting for input”.

Long operations must emit phase/progress markers and an expected coarse duration when known. A terminal continuation prompt must never be described as an executing long-running task.

When a test can be moved from an unsuitable local environment to a safe automated Linux validation surface without adding meaningful user interaction, prefer the environment change over asking the user to troubleshoot local compatibility manually.

---

## 14. Command failure classification and learning loop

Every failed generated command in a material workflow must be classified before another command is issued:

```text
COMMAND_FAILURE_CLASS=
  ENVIRONMENT_CAPABILITY_MISMATCH
  WRONG_VALIDATION_ENVIRONMENT
  CLI_INVOCATION_CONTRACT_MISMATCH
  VALIDATION_COMMAND_TOPOLOGY_MISMATCH
  SHELL_PORTABILITY_OR_SYNTAX
  FALSE_SAFE_STOP_GATE
  ARTIFACT_IDENTITY_FAILURE
  RELEASE_REBIND_OR_CROSS_ARTIFACT_CONSISTENCY_FAILURE
  AUTHORITY_OR_SAFETY_BLOCK
  DEPLOYMENT_MECHANIC_FAILURE
  WRAPPER_OR_HARNESS_FAILURE
  APPLICATION_OR_STRATEGY_FAILURE
  EVIDENCE_PACKAGING_FAILURE
  EVIDENCE_EGRESS_FAILURE
  OPERATOR_INPUT_TRANSPORT_FAILURE
  UNKNOWN

SEMANTIC_ACTION_STARTED=YES|NO
SEMANTIC_ACTION_COMPLETED=YES|NO
SAFE_STATE_RESTORED=YES|NO|NOT_APPLICABLE
RESUME_FROM=
RERUN_SEMANTIC_ACTION=YES|NO
```

Do not issue the next command until the failure class and resume checkpoint are explicit.

When an avoidable failure reveals a reusable lesson, update canonical governance/tooling rather than relying on chat memory. Do not wait for the same defect to recur in a later deployment.

---

## 15. Relationship to mature tools and custom automation

This rule does not authorize a new deployment framework or custom orchestration service.

Apply the existing mature-solution order:

```text
EXISTING_ACCEPTED_PROJECT_CAPABILITY
-> PROVIDER_NATIVE / STANDARD TOOL
-> MATURE MAINTAINED EXTERNAL TOOL
-> THIN ADAPTER
-> SMALL PROJECT-SPECIFIC LOGIC
```

Examples:

- CLI contract: installed/provider-native `--help`, official command reference or machine-readable schema;
- canonical validation: repository config and existing accepted CI workflow before ad-hoc local variants;
- shell syntax: target shell native parser / `bash -n`;
- shell static analysis: ShellCheck where applicable;
- cross-platform hashing: Python standard library or verified platform-native utility;
- generic isolated Linux compatibility: existing GitHub Actions Ubuntu runner where fit;
- host-like Linux validation: isolated authorized Lightsail Linux environment where CI is insufficient;
- target-host transport: existing FinalShell SSH/SFTP workflow;
- long target-host execution: hash-manifested file-backed script inside the already approved artifact workflow.

Do not respond to command unreliability by building a persistent custom deployment agent, orchestration framework or new user relay layer unless the existing build-vs-buy gate independently proves it necessary.

---

## 16. Required pre-delivery disposition

Before presenting a nontrivial operator command, the controlling role must be able to state:

```text
GENERATED_COMMAND_RELIABILITY_GATE=PASS
TARGET_ENVIRONMENT_PROVEN=YES
LOCAL_ENVIRONMENT_FIT=PASS_OR_ROUTED_TO_VALIDATED_FALLBACK
VALIDATION_ENVIRONMENT_ROUTE=DEFINED
VALIDATION_PLATFORM_CLASS=DEFINED
AUTHORITATIVE_VALIDATION_ENVIRONMENT=DEFINED
CANONICAL_VALIDATION_COMMANDS=DEFINED
KNOWN_ENVIRONMENT_MISMATCHES=RECORDED
CLI_INVOCATION_CONTRACT_PROOF=PASS_OR_NA
PORTABILITY_REVIEW=PASS
CANONICAL_WORKFLOW_MATCH=PASS
FALSE_GATE_REVIEW=PASS
ALLOWLIST_SEMANTICS_PROOF=PASS_OR_NA
RELEASE_SENSITIVE_SINGLE_SOURCE_OF_TRUTH=PASS_OR_NA
CROSS_ARTIFACT_SEMANTIC_CONSISTENCY=PASS_OR_NA
STALE_RELEASE_LITERAL_SCAN=PASS_OR_NA
SIDE_EFFECT_FREE_PREFLIGHT_BEFORE_ONE_SHOT=PASS_OR_NA
CHECKPOINT_RESUME_PLAN=DEFINED
POST_SEMANTIC_EVIDENCE_CHECKPOINT_PLAN=DEFINED_OR_NA
EVIDENCE_EGRESS_PLAN=PASS_OR_NA
EVIDENCE_EGRESS_PREFLIGHT=PASS_OR_NA
EVIDENCE_EGRESS_CANARY_OR_DIRECTORY_PROOF=PASS_OR_NA
EVIDENCE_EGRESS_SERVER_PROOF=PENDING_POST_RUN_OR_NA
EVIDENCE_EGRESS_CLIENT_VISIBILITY=PENDING_POST_RUN_OR_NA
USER_INTERACTION_BUDGET=PASS
COMMAND_REPAIR_BUDGET=AVAILABLE
```

If these cannot be established, stop command generation and resolve the workflow/environment mismatch first. Final evidence proof is completed after execution and must not be required as a precondition for delivering the command that generates that evidence.