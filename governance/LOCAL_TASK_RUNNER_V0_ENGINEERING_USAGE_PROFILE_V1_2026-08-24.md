# Trader Assist / Trade OS — Local Task Runner V0 Engineering Usage Profile V1

**Status:** GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-24 after independent acceptance and merge  
**Issue:** #121  
**Scope:** canonical local execution/validation/evidence envelope for an already-selected OpenCode engineering stage

This profile does not select the engineering route, Writer model, architecture, requirements or authority. It grants no commit/push, Mark Ready, merge, deployment, runtime/cloud, credential/private-API, signing/wallet, exchange-write, order-submission or trading authority.

## 1. Accepted tool identity

The following Local Task Runner V0 candidate completed separate T4 independent onboarding review with `PASS` before this profile was proposed:

```text
LOCAL_TASK_RUNNER_VERSION=0.1.0-candidate+v0-r2
DEFAULT_LOCAL_RUNNER_HOME=$HOME/trade-os-local-runner-v0-candidate

RUNNER_PY_SHA256=1b010fbc33c15af3b933e339241215050a753cdd36d16fde93398ff95bbc8cd9
VERSION_SHA256=ee1abfd99559e5473f9625fe9acfb12b6d4925477adc3025b8be831d9e70d347
TASK_SCHEMA_SHA256=498c9a67390d5dee1b85dc4b5646fb23ea5375639e1603598f65e96fbb46a2c0
RESULT_SCHEMA_SHA256=7839bdd61fa57a862e359b0f81eebcacebfd4be40f169272b25a92d9053a76e3
TEST_RUNNER_SHA256=499537c6abad23eb3b00f2cdb4a3a62ea7ad38bceb3717113620de2b9aef2d6d

ACCEPTED_IMPLEMENTATION_ARTIFACT_SHA256=678a17856fa1cc8b31370716434758742fd6dc49585fec9fe18e66165c875a8e
ACCEPTED_FINAL_QUALIFICATION_ARTIFACT_SHA256=0c5409fa6a261de858aac104645abe8c67a22c8fdb25c25a5b0a70f9d2c18474
FINAL_T4_INDEPENDENT_REVIEW=PASS
FIRST_REAL_TRADER_ASSIST_USE_AUTHORIZED=YES
FIRST_REAL_TRADER_ASSIST_USE_AUTHORIZED_DATE=2026-08-24
```

The current local path is a user-local installation detail, not repository architecture. Generated commands should resolve:

```bash
LOCAL_TASK_RUNNER_HOME="${TRADE_OS_LOCAL_RUNNER_HOME:-$HOME/trade-os-local-runner-v0-candidate}"
```

If the installed version or accepted core hashes drift, fail closed with `LOCAL_TASK_RUNNER_IDENTITY_DRIFT` and route the incident to tooling control. Do not silently accept a changed runner.

A material change to authority, executor/model-selection semantics, retry/resume behavior, packet integrity, evidence transport, mutation/publication behavior, sandbox/network surface or instruction precedence requires re-acceptance under `ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md`.

## 2. Position in the engineering control plane

The canonical relationship is:

```text
ENGINEERING CONTROL / L1
-> live GitHub + mandatory preflight
-> research / root cause / architecture / attack matrix when material
-> Router V2 selects executor + model
-> frozen complete Task Packet
-> IF executor = OPENCODE and Runner-compatible:
     LOCAL TASK RUNNER V0
     -> exact packet-hash verification
     -> runner/OpenCode surface preflight
     -> Git HEAD/branch/clean-worktree preflight
     -> exactly one OpenCode execution
     -> changed-path policy gate
     -> frozen deterministic checks
     -> final Git/mutation gate
     -> result/evidence/log artifacts
-> normal Engineering Control disposition
-> exact-head CI when applicable
-> separate strongest-ChatGPT T4 independent review
-> separate user publication/merge/deploy/runtime gates
```

The Runner is therefore an **execution, validation and evidence envelope**, not an engineering decision-maker.

It must never:

- choose `OPENCODE` instead of another Router-selected executor;
- choose or silently substitute a model;
- reinterpret or redesign the frozen Task Packet;
- widen `allowed_changed_paths`;
- invent a broader check plan;
- perform a hidden retry or automatic resume;
- perform commit/push, Mark Ready, merge, deployment or runtime/cloud mutation;
- receive credentials/private API, wallet/signing or exchange-write authority merely because it is executing a task.

## 3. First real task rule

Do **not** manufacture a synthetic project task merely to test the Runner.

```text
FIRST_REAL_TASK =
  first naturally occurring real Trader Assist engineering stage
  for which Router V2 legitimately selects OPENCODE
  and the frozen task is compatible with Local Task Runner V0
```

Do not lower Writer quality or override Router V2 merely to exercise the Runner. If the next real task legitimately selects Codex, Trae or DeepSeek Harness, use that route. The Runner's first project use occurs at the first naturally arising compatible OpenCode stage.

The first real task is genuine project work. Its output may become a real implementation candidate if the normal tests, CI, independent review and user gates pass. It is not another qualification fixture.

## 4. Engineering-window generation contract

For normal use the user should **not** manually author Runner JSON, calculate packet hashes, construct Runner commands or return to a tooling window to obtain routine commands.

Once Engineering Control has frozen the real task, **the Engineering window must generate one complete ordinary-Terminal paste block** that performs the authorized local stage end-to-end.

The block must contain, in this order where applicable:

1. resolve the exact project worktree and `LOCAL_TASK_RUNNER_HOME`;
2. verify `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS` and, for material Writer work, `ENGINEERING_PREFLIGHT_GATE=PASS` before local launch;
3. verify the accepted Runner version and accepted core hashes;
4. verify the selected OpenCode installation/surface (`opencode --version`, `opencode run --help`) and exact required options;
5. verify the task worktree is the expected Git branch/HEAD and clean before executor launch;
6. create the complete frozen `local-task-packet-v0` JSON without asking the user to edit it manually;
7. compute the packet SHA-256 locally;
8. call `runner.py validate` with the exact packet hash;
9. call `runner.py run` **once** with the exact packet hash;
10. capture the emitted `RUN_ID` and display/read the final `result.json` and `evidence.md` (or equivalent accepted evidence files);
11. print a compact telemetry/result summary sufficient for Engineering Control and later independent review;
12. stop on failure. No automatic second `run`, hidden retry, silent fallback or guessed resume.

The ordinary primitive is:

```bash
LOCAL_TASK_RUNNER_HOME="${TRADE_OS_LOCAL_RUNNER_HOME:-$HOME/trade-os-local-runner-v0-candidate}"
PACKET="<absolute path generated by Engineering Control>"
PACKET_SHA256="$(shasum -a 256 "$PACKET" | awk '{print $1}')"

python3 "$LOCAL_TASK_RUNNER_HOME/runner.py" validate \
  --packet "$PACKET" \
  --expected-sha256 "$PACKET_SHA256"

python3 "$LOCAL_TASK_RUNNER_HOME/runner.py" run \
  --packet "$PACKET" \
  --expected-sha256 "$PACKET_SHA256"
```

This snippet is explanatory only. Engineering Control must generate the full task-specific one-paste block; the user is not expected to assemble it.

## 5. Frozen Task Packet requirements

A project Task Packet handed to the Runner must at minimum freeze:

```text
schema_version=local-task-packet-v0
task_id
workdir
executor.kind=opencode
executor.model=<exact Router-selected provider/model>
executor.variant=<exact value or null>
prompt=<complete frozen Writer instruction>
timeout_seconds
expected_git.required=true
expected_git.head=<exact start HEAD>
expected_git.branch=<exact task branch>
allowed_changed_paths=<minimum exact allowlist>
checks=<frozen argv-based deterministic validation>
```

Rules:

- `workdir` must be the bounded task worktree, never an ambiguous parent directory.
- The worktree must be clean before executor launch.
- `expected_git.head` and `expected_git.branch` come from live exact state, not a stale prompt.
- `allowed_changed_paths` must be the smallest task-complete set. Scope expansion returns to Engineering Control.
- The Writer prompt must already contain the complete requirements, invariants, prohibited scope and result expectations.
- Checks must be deterministic argv-based commands and must not use direct `git` mutation or shell escape as validation authority.
- An executor exit code of `0` is not sufficient for success. Policy and deterministic checks still govern final status.

## 6. What the Runner covers

The Runner covers the bounded **local execution envelope** after the engineering decision is already frozen:

```text
COVERED
- input Task Packet SHA-256 identity
- accepted Runner identity preflight
- required OpenCode CLI surface preflight
- exact OpenCode model/variant transport
- exact Git workdir / branch / HEAD / clean-start observation
- exactly one OpenCode execution
- executor stdout/stderr/event evidence capture
- changed-path observation
- allowed-path policy enforcement
- frozen deterministic checks
- post-check Git/mutation observation
- final status + stop reason
- RUN_ID and inspectable result/evidence artifacts
- retry count observation
```

The Runner does **not** cover or replace:

```text
NOT_COVERED
- problem definition or requirements discovery
- material research / architecture / route selection
- Engineering Preflight or attack-matrix judgment
- model quality/routing decision
- semantic code review
- automatic repair decisions
- commit/push/publication
- GitHub PR creation or Mark Ready
- exact-head CI service itself
- final independent T4 adjudication
- merge
- deployment or production runtime/cloud mutation
- credentials/private API / wallet / signing / exchange write / trading authority
- preventive filesystem sandboxing
- network sandboxing
```

In simple words: **Engineering decides what to build and which Writer should build it; the Runner makes one selected OpenCode local implementation attempt observable, bounded and mechanically verifiable.**

## 7. Required operational telemetry

The first real use and later representative uses should capture the following when available without creating synthetic work:

```text
TOOL
RUNNER_VERSION
RUNNER_CORE_IDENTITY_CHECK
OPENCODE_VERSION
ROLE=WRITER|OPERATOR
TASK_ID
TASK_CLASS=T0|T1|T2|T3
EXECUTOR=OPENCODE
MODEL
VARIANT
INPUT_PACKET_SHA256
RUN_ID
START_HEAD
START_BRANCH
START_WORKTREE_CLEAN
EXECUTOR_EXIT_STATUS
CHANGED_PATHS
POLICY_VIOLATIONS
CHECK_NAMES_AND_EXIT_STATUS
FINAL_STATUS
STOP_REASON
RETRY_COUNT
ELAPSED_TIME
FIRST_PASS_RESULT
HUMAN_INTERVENTION_COUNT
TOKENS_OR_COST_IF_EXPOSED_BY_OPENCODE
LOCAL_TEST_RESULT
EXACT_HEAD_CI_RESULT_WHEN_APPLICABLE
INDEPENDENT_REVIEW_RESULT
INDEPENDENT_REVIEW_BLOCKERS
```

For the **first real project use**, Engineering Control must preserve this telemetry in the normal task/result evidence or PR/Issue evidence trail. Do not create a separate benchmark task just to collect it.

The metrics are used to answer practical questions:

- Did the Runner reduce user copy/paste and handoff burden?
- Did it preserve exact task/model/Git identity?
- Did the selected Writer finish first pass or require a new authorized run?
- Did checks fail closed rather than trust Writer self-report?
- Did the Runner itself create any new tooling blocker?
- How much elapsed time / human intervention did the flow add or save?

## 8. Failure routing

Normal failures stay with the component that owns them.

```text
NORMAL_CODE_OR_TEST_FAILURE
-> ENGINEERING CONTROL
-> apply the task's normal repair / convergence rules

TASK_SCOPE_OR_AUTHORITY_UNCLEAR
-> ENGINEERING CONTROL / L1
-> SAFE_STOP until the Task Packet is refrozen

MODEL_OR_PROVIDER_UNAVAILABLE_OR_DEGRADED
-> ENGINEERING CONTROL / ROUTER
-> decide whether a NEW authorized run/route is appropriate
-> Runner must not silently substitute

RUNNER_IDENTITY_DRIFT
RUNNER_SCHEMA_OR_RESULT_CORRUPTION
RUNNER_FALSE_SUCCESS_OR_FALSE_POLICY_BEHAVIOR
RUNNER_CLI_PREFLIGHT_BUG
RUNNER_EVIDENCE/STATE_MACHINE_DEFECT
-> TOOLING CONTROL
-> do not treat as normal application-code repair
```

The user should return to the tooling-control window only for the last class or another genuine workflow/tool defect. Normal project implementation problems remain in the Engineering window.

## 9. No hidden retry / rerun discipline

V0 is intentionally simple:

```text
AUTOMATIC_RETRY=NO
AUTOMATIC_RESUME=NO
SILENT_MODEL_FALLBACK=NO
```

A failed `run` is evidence. Engineering Control first classifies the cause, then explicitly freezes any allowed repair/new Task Packet/new model route before another run. Never loop the Runner until it passes.

## 10. Worktree and provider-native fit

The preferred local task boundary remains an isolated Git task branch/worktree. Git's native worktree mechanism is the mature repository primitive; the Runner does not replace it.

OpenCode's provider-native `opencode run` command is explicitly intended for non-interactive scripting/automation and exposes the model, working-directory, output-format and provider-specific variant surfaces used by this Runner. The project therefore keeps the Runner thin rather than introducing a custom daemon or another orchestration service.

## 11. Residual limitations

The independently accepted V0 boundaries remain explicit:

- detective control, not a preventive filesystem sandbox;
- no network sandbox;
- a trusted validation program can itself have side effects;
- Git-visible observation cannot prove absence of every external/non-Git side effect;
- outside a Git workdir mutation visibility is weaker;
- prompt semantics are not interpreted;
- no automatic retry or automatic resume;
- OpenCode/provider/model availability can change independently.

These limitations do not authorize weakening the existing policy gates. If a future task requires stronger isolation, that is a new material tooling/security decision, not an implicit Runner capability.

## 12. Current workflow disposition

After this profile is independently accepted and merged, the intended user workflow is:

```text
USER <-> ENGINEERING WINDOW for normal development

ENGINEERING WINDOW
-> live GitHub + preflight
-> freeze real task
-> Router selects executor/model
-> when OPENCODE + Runner-compatible:
     generate one complete Terminal block containing Runner workflow
-> user pastes once
-> Engineering Window receives/reads result evidence
-> Engineering Window handles normal code/test outcome
-> normal CI + independent review gates

USER -> TOOLING WINDOW only when the Runner/workflow itself is defective or its accepted identity changes materially
```

This is the canonical handoff objective: **the user should not need a separate tooling-window round trip for every normal Runner invocation.**
