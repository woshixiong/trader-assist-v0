# Trader Assist / Trade OS — Engineering Tool Onboarding and Change Acceptance Rule V1

**Status:** HOLISTIC-CONVERGENCE GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-23

This rule governs the admission and material reconfiguration of coding executors, operators, orchestration layers, review-transport automation, and their project-local profiles/configuration. It grants no implementation, Mark Ready, merge, deployment, runtime/cloud, credential/private-API, signing/wallet, exchange-write or trading authority.

## 1. Permanent rule

```text
NEW_ENGINEERING_TOOL_OR_MATERIAL_TOOL_CONFIG
-> BOUNDED CANDIDATE
-> EXACT ARTIFACT / CONFIG IDENTITY
-> REPRESENTATIVE CAPABILITY / SAFETY EVIDENCE
-> SEPARATE INDEPENDENT CHATGPT REVIEW
-> PASS
-> USER PUBLICATION / ACTIVATION AUTHORITY
-> FIRST REAL TASK
```

A tool being installed, free, popular, provider-supported or technically functional does not make it accepted project infrastructure.

### 1.1 Mandatory pre-admission mature-solution / build-vs-buy gate

Before project engineering begins custom **commodity tooling, orchestration, transport, scheduling, workflow, evidence, deployment, observability, persistence or equivalent infrastructure**, decompose the required capability and evaluate in this order:

```text
REUSE_ACCEPTED_PROJECT_CAPABILITY
-> PROVIDER_NATIVE
-> STANDARD_OR_OFFICIAL
-> MATURE_MAINTAINED_EXTERNAL
-> THIN_PROJECT_ADAPTER
-> SMALL_PROJECT_SPECIFIC_DOMAIN_LOGIC
-> CUSTOM_COMMODITY_INFRASTRUCTURE_LAST_RESORT
```

The pre-admission record is mandatory:

```text
CUSTOM_COMMODITY_TOOL_BUILD_GATE=PASS|FAIL
CAPABILITY_DECOMPOSED=YES|NO
EXISTING_PROJECT_CAPABILITY_CHECKED=YES|NO
PROVIDER_NATIVE_CAPABILITY_CHECKED=YES|NO
STANDARD_OR_OFFICIAL_CAPABILITY_CHECKED=YES|NO
MATURE_EXTERNAL_SOLUTIONS_CHECKED=YES|NO
TARGET_HOST_COMPATIBILITY_CHECKED=YES|NO
TOTAL_BURDEN_COMPARISON_DONE=YES|NO
MATURE_SOLUTION_FIT_FOUND=YES|NO
BLOCKING_FIT_GAPS=
THIN_ADAPTER_SUFFICIENT=YES|NO
EXPECTED_NET_ENGINEERING_VALUE=POSITIVE|NON_POSITIVE|UNRESOLVED
CUSTOM_BUILD_JUSTIFICATION=PASS|FAIL
```

`TOTAL_BURDEN_COMPARISON_DONE` must include implementation, testing, independent review, operator relay, token/model cost, reliability, maintenance, recovery, migration/replacement cost and target-host constraints. Popularity or zero license cost alone is not proof of fit.

`CUSTOM_COMMODITY_TOOL_BUILD_GATE=PASS` means the comparison is complete and the selected route obeys this admission order. It does **not** mean a custom build is approved. A custom-build route additionally requires `CUSTOM_BUILD_JUSTIFICATION=PASS`; a mature-fit route passes the gate by selecting the mature/thin-adapter path and prohibiting the custom build.

If a mature/provider-native/standard solution fits the required capability with an acceptable thin adapter:

```text
MATURE_SOLUTION_FIT_FOUND=YES
CUSTOM_BUILD_JUSTIFICATION=FAIL
CUSTOM_COMMODITY_INFRASTRUCTURE_BUILD=PROHIBITED
```

Custom commodity infrastructure is admissible only when the comparison records concrete blocking fit gaps, target-host compatibility is proven, a thin adapter is insufficient, and the expected net engineering value is materially positive.

```text
SUNK_COST_IS_NOT_JUSTIFICATION
```

Repeated repair, high human relay, large one-off Bash/Python glue, maintenance burden approaching or exceeding the saved work, or exhausted repair budget triggers:

```text
STOP_CUSTOM_TOOLING
-> HOLISTIC_CONVERGENCE_GATE
-> SEARCH_MATURE_REPLACEMENT
```

Do not keep researching or patching the same failing custom design merely because prior effort has already been spent. This gate strengthens the mature-solution-first rule in Unified Governance; it does not create a new governance authority or permit speculative platform building.

Project-specific trading/domain value such as Scanner, Setup, Strategy Kernel, Market Event, risk/trade-plan or evidence-authority semantics is not reclassified as commodity infrastructure by this gate; it remains subject to the normal research, architecture, implementation and review rules.

### 1.2 Mandatory stdin isolation for model-backed executors/operators

Any coding Agent, model-backed executor/operator, or CLI that may read from standard input MUST NOT share the same stdin stream that carries a one-paste shell program or heredoc launcher body.

The prohibited pattern is:

```text
ONE_PASTE_HEREDOC_IS_THE_RUNNING_SHELL_PROGRAM
+
MODEL_EXECUTOR_INHERITS_THE_SAME_STDIN
```

This is prohibited even when the model prompt is supplied through argv, because an executor may still probe, consume, or wait on inherited stdin. The resulting failure can corrupt the outer shell control flow, consume later launcher lines, or make a completed semantic turn appear unstarted or failed.

Required execution pattern:

```text
ONE_PASTE_TERMINAL_INPUT
-> WRITE_PLAIN_TEXT_LAUNCHER_OR_TASK_PACKET_TO_FILE
-> CLOSE_HEREDOC
-> EXECUTE_FILE_BACKED_LAUNCHER
-> GIVE_MODEL_EXECUTOR_AN_EXPLICITLY_SEPARATE_STDIN
```

Acceptable executor stdin shapes include:

```text
EXECUTOR_STDIN=/dev/null
```

when the prompt is fully supplied through supported non-stdin arguments, or:

```text
EXECUTOR_STDIN=DEDICATED_PROMPT_FILE_WITH_EXPLICIT_EOF
```

when the provider-native CLI requires or benefits from stdin prompt transport.

Permanent invariants:

```text
AGENT_AND_LAUNCHER_STDIN_SHARED=PROHIBITED
FILE_BACKED_PHASE_SEPARATED_LAUNCH=REQUIRED_FOR_ONE_PASTE_AGENT_WORKFLOWS
MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT
MODEL_EXECUTOR_MUST_NOT_CONSUME_OUTER_SCRIPT_BYTES=YES
SEMANTIC_COMPLETION_EVIDENCE=PROVIDER_NATIVE_SUCCESSFUL_TERMINAL_LIFECYCLE_PLUS_FINAL_RESULT_OR_EQUIVALENT_WHERE_EXPOSED
AUTHORITATIVE_FAILURE_ERROR_CANCEL_ABORT=PRECEDES_MERE_TERMINAL_LIFECYCLE
WRITER_COMPLETED_REQUIRES=SUCCESSFUL_TERMINAL_LIFECYCLE+FINAL_SEMANTIC_RESULT_OR_EQUIVALENT+NO_AUTHORITATIVE_FAILURE_ERROR_CANCEL_ABORT
SHELL_EXIT_STATUS=SUPPORTING_EVIDENCE_NOT_SOLE_SEMANTIC_COMPLETION_AUTHORITY
POST_WRITER_DETERMINISTIC_VALIDATION=SEPARATE_PHASE
WRITER_COMPLETED_THEN_VALIDATION_INTERRUPTED=DO_NOT_RERUN_WRITER
```

Where the executor exposes provider-native lifecycle, status, error and final-result telemetry, Engineering must persist that telemetry before downstream deterministic validation. A lifecycle terminal/completion event alone does not establish successful semantic completion. `WRITER_COMPLETED` may be asserted only when provider-native evidence establishes a successful terminal lifecycle, a final semantic model result or provider-native equivalent, and no authoritative failure, error, cancel or abort state. Any authoritative failure/error/cancel/abort state takes precedence over a mere terminal/completion event. If the execution surface exposes evidence needed to distinguish success from failure and successful completion cannot be proven, fail closed and do not classify the Writer as completed. Shell exit status remains supporting evidence rather than the sole semantic-completion authority.

A successfully completed semantic Writer turn must not be automatically repeated merely because a later wrapper, network check, evidence-packaging step, or deterministic validation phase fails. Such a downstream failure resumes from the exact completed semantic checkpoint rather than launching another semantic Writer turn.

This invariant applies to Codex, OpenCode and future model-backed executors/operators whenever their actual CLI/runtime surface can read stdin. It is transport safety, not a model-specific exception. A tool profile may define a stricter provider-native launch or success-evidence contract, but may not weaken these invariants.

## 2. What requires independent acceptance

Independent acceptance is required before first project use when adding a new:

- L2 semantic coding executor/harness;
- L3 operator/orchestrator such as Hermes;
- review-transport automation that can launch apps, upload files or submit prompts;
- project-local agent configuration that materially changes model/tool/permission/context/session behavior;
- automation schema or protocol that can mutate local/GitHub state or transport authority-bearing Task Packets.

It is also required again when an accepted tool receives a material change to:

- authority or permissions;
- executor/destination/model-selection semantics;
- session/resume/retry behavior;
- packet integrity or evidence transport;
- sandbox/network/browser/computer-use capability;
- review independence;
- publication/commit/push behavior;
- context-discovery or instruction precedence in a way that can change correctness or safety.

A narrow refresh of a current-model snapshot that does not change durable workflow semantics may use the specialized refresh rule already defined for that profile; do not force a full harness re-acceptance for model-label churn alone.

## 3. Reviewer default

When exact GitHub/config artifacts and CI/evidence are sufficient:

```text
REVIEWER_SURFACE = STRONGEST_APPROPRIATE_ACCEPTED_FRESH_INDEPENDENT_REVIEW_SURFACE
REVIEWER_CONTEXT = FRESH_AND_SEPARATE_FROM_CONTROL_AND_IMPLEMENTATION
REVIEWER_PERMISSION = READ_ONLY
ORDINARY_CHATGPT_NEW_WINDOW = ACCEPTED_FALLBACK
PROVIDER_NATIVE_REVIEWER_AGENT = ALLOWED_AFTER_INDEPENDENT_ACCEPTANCE
REASONING = HIGHEST_APPROPRIATE_LEVEL
```

The implementation/configuration Writer, its Supervisor and the controlling Engineering context must not independently accept their own work.

An authority-bearing provider-native Reviewer Agent is acceptable only after the exact reviewer configuration/route has itself been independently accepted. It must receive a compact Review Manifest, read exact canonical evidence directly, inherit no Writer/Supervisor/Engineering-Control PASS conclusion as fact, have no implementation/repair authority, and produce an independently attributable idempotent result.

If local evidence is needed, prefer deterministic evidence generation into a review bundle and deliver that exact bundle to the fresh independent Reviewer. Do not choose a materially weaker Reviewer merely to increase automation; reviewer capability must remain appropriate to the consequence of the task. A new ordinary ChatGPT review window remains the fail-safe fallback when an automated reviewer route is unavailable, unaccepted, ambiguous or degraded.

## 4. Required acceptance evidence

At minimum, the reviewer verifies as applicable:

```text
TOOL / HARNESS VERSION
EXACT PROJECT CONFIG / PROFILE
MODEL / PROVIDER ROUTING SURFACE
PERMISSIONS / SANDBOX / NETWORK
SESSION / RESUME / RETRY POLICY
TASK PACKET / AUTHORITY TRANSPORT
FAIL-CLOSED CONDITIONS
LOCAL MUTATION BOUNDARY
GITHUB / PUBLICATION BOUNDARY
REVIEW INDEPENDENCE
SECRET / CREDENTIAL BOUNDARY
REPRESENTATIVE SMOKE OR REAL-TASK EVIDENCE
ROLLBACK / DISABLE PATH
```

For code/config in GitHub, independently verify exact candidate HEAD and exact-head CI when CI applies.

## 5. Human takeover and observability requirement

Any autonomous operator/orchestrator must be inspectable and recoverable. A workflow is not acceptable if, after partial automation failure, the user/L1 cannot determine exactly which step completed and which artifact/state is authoritative.

Every multi-step automation must therefore expose checkpointed evidence sufficient to answer:

```text
RUN_ID
CURRENT_PHASE
LAST_COMPLETED_PHASE
INPUT_ARTIFACT / HASH
OUTPUT_ARTIFACT / HASH
TARGET / DESTINATION
EXECUTOR / MODEL WHEN APPLICABLE
LOCAL/GIT HEAD BEFORE/AFTER WHEN APPLICABLE
ACTION RESULT / EXIT STATUS
RETRY_COUNT
STOP_REASON
RESUME_FROM
```

No hidden semantic retry loop is allowed. Resume is from an exact accepted checkpoint, never from a model guess about prior progress.

## 6. Activation gates

Independent PASS does not itself grant:

```text
Mark Ready
merge
first project use
production deployment/runtime/cloud mutation
credential/private API access
exchange write/trading action
```

The user retains the separate current activation/publication gates defined by the canonical project governance.
