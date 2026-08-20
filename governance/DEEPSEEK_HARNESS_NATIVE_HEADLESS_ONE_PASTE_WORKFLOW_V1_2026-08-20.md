# Trader Assist / Trade OS — DeepSeek Harness Native Headless One-Paste Workflow V1

**Status:** SPECIALIZED GOVERNANCE PROPOSAL  
**Effective date:** 2026-08-20  
**Repository:** `woshixiong/trader-assist-v0`  
**Scope:** user-operated macOS Terminal delivery when `DEEPSEEK_HARNESS` is the selected L2 coding executor, plus the bounded `0.1.0-rc.8` first-real-task upgrade-validation transition.

This file is a narrow execution companion to the canonical Unified Engineering Governance, Mandatory Engineering Preflight, DeepSeek Harness executor profile, DeepSeek Harness mandatory usage rules, and current tooling-priority rule. It does not create a new executor authority and does not grant Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission, cancellation, autonomous trading, or financial-action authority.

---

## 1. Frozen operator workflow

For ordinary user-operated macOS DeepSeek Harness engineering tasks, the default delivery path is:

```text
L1 ENGINEERING CONTROL freezes the task
→ Engineering emits ONE contiguous ordinary-Terminal block
→ user pastes that block ONCE
→ the block resolves the exact repo/worktree/preflight/task packet
→ the block launches native DeepSeek Harness headless execution directly
→ DeepSeek performs the bounded Writer stage
→ raw result/evidence returns to Terminal
→ independent Review evaluates the exact artifact/head
```

Binding defaults:

```text
DEFAULT_USER_DELIVERY=ONE_CONTIGUOUS_TERMINAL_PASTE
DEFAULT_DSH_EXECUTION_SURFACE=NATIVE_HEADLESS
DEFAULT_DSH_COMMAND=dsh --profile headless <task>
WEB_UI=OPTIONAL_INTERACTIVE_SURFACE
SECOND_PROMPT_PASTE=NOT_REQUIRED_BY_DEFAULT
MANUAL_BROWSER_OPEN=NOT_REQUIRED_BY_DEFAULT
MANUAL_WORKSPACE_SELECTION=NOT_REQUIRED_BY_DEFAULT
```

This intentionally mirrors the project's established one-paste Codex operator UX at the workflow level while preserving DeepSeek Harness's own first-party execution surface. Codex and DeepSeek Harness remain separate peer L2 executors with different CLIs and session semantics.

The Web UI remains available for human exploration, manual inspection, interactive debugging, or cases where a specific task genuinely benefits from it. It is not the normal delivery requirement for a bounded Writer task.

---

## 2. Engineering owns the routing inside the paste block

When DeepSeek Harness is selected, Engineering must generate the complete Terminal block. The user must not be required to separately:

- `cd` into a repository or worktree;
- create/select the branch or isolated worktree;
- open the DeepSeek Harness Web UI;
- select the workspace in a browser;
- launch a second DSH command;
- paste the authoritative task prompt a second time;
- manually reconstruct architecture-critical prompt addenda.

The block should mechanically perform every safe deterministic step that can be encoded without crossing a retained user authority gate.

For Writer mutation, the block must preserve the existing project rule:

```text
PROJECT_MAIN_WORKTREE_MUTATION=NO
ISOLATED_WORKTREE=YES
```

The exact worktree path, expected base/head, allowed scope, prohibited scope, tests, stop conditions and output evidence remain frozen by L1 in the Task Packet.

---

## 3. Native headless is the preferred DSH seam

The first-party DSH `headless` profile is the preferred user-operated non-GUI seam because it:

- accepts one task as the positional job;
- treats the invoking directory as the default workspace root;
- creates a fresh persisted Agent/session for the one-shot task;
- waits for completion;
- prints the final assistant result to stdout;
- exits success only for a completed run;
- mounts no browser, HTTP server, Web runtime or ApiProxy.

Therefore the normal Engineering-generated launch shape is conceptually:

```sh
cd <exact isolated worktree>
DSH_TOOLS_MODE=code dsh --profile headless "<exact frozen task packet>"
```

The user-facing delivery should normally use a here-document or temporary task-packet file inside the one paste block so shell quoting does not force a second prompt paste. The exact packet must be passed losslessly; it must never be shortened merely to fit an interface assumption.

If a packet approaches a verified operating-system argv/input limit, Engineering must SAFE_STOP or use a separately verified lossless transport seam. Do not silently truncate, summarize, or split authority-critical instructions across user messages.

---

## 4. One-paste block minimum responsibilities

A material DSH Writer block must encode or verify, as applicable:

```text
REPOSITORY=woshixiong/trader-assist-v0
LIVE_MAIN_SHA=<freshly verified by L1>
EXACT_BASE_SHA=<frozen>
BRANCH=<bounded branch>
WORKTREE=<absolute isolated worktree>
EXECUTOR=DEEPSEEK_HARNESS
DSH_VERSION=<expected version/candidate>
PROVIDER=deepseek-official
MODEL=<exact L1-frozen model>
REASONING=<exact L1-frozen thinking/reasoning state>
AGENT/TOOLS_MODE=code / PTC
PERMISSION_BASELINE=workspace-write + ask
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS              # material work
ALLOWED_PATHS=<explicit>
PROHIBITED_SCOPE=<explicit>
VALIDATION_COMMANDS=<explicit>
SAFE_STOP_CONDITIONS=<explicit>
USER_RETAINED_GATES=<explicitly NOT AUTHORIZED unless currently granted>
OUTPUT_CONTRACT=RESULT_PACKET / exact evidence
```

The block may perform deterministic repository/worktree setup before launching DSH. It must fail closed on base/head mismatch, unsafe dirty-state collision, existing conflicting worktree/branch ownership, missing executable, wrong expected DSH version, or any other frozen precondition failure.

A DeepSeek Writer still performs its own bounded task-start preflight skill and must not mutate files until the required session-baseline checks pass.

### 4.1 L1-frozen model and reasoning must match the actual headless Agent

In `rc.8`, a fresh headless Agent resolves its provider/model/reasoning selection through the shared `agent-default-model` service. The base composition provides a provider/model default, while the mounted settings provider can layer the user's saved selection over it; `reasoningEffort` is specifically part of that Settings selection.

Therefore the frozen Task Packet text is **not** by itself a model selector. Before task mutation begins, the one-paste route must establish that the effective provider/model/reasoning selection for the fresh headless Agent exactly matches the L1-frozen selection.

Acceptable routes are limited to:

1. verify that the current effective selection already matches the frozen selection; or
2. use a separately verified per-invocation selection seam that deterministically applies the frozen selection without broadening authority.

The block must not silently edit the user's persistent `$DSH_HOME/settings.yaml` merely to force task routing. If the effective selection cannot be proven before mutation, SAFE_STOP and return to L1.

### 4.2 `workspace-write + ask` is fail-closed in native headless unless an answerer exists

The `rc.8` base bundle configures `workspace-write` with approval policy `ask`, but the first-party approval service has no built-in human answerer. In a headless deployment, an operation that actually requires approval resolves unavailable and fails closed unless a separately configured answerer owns that Agent.

For the normal one-paste route this is intentional:

```text
NORMAL_HEADLESS_TASK=WORKSPACE-BOUNDED_OPERATIONS_THAT_REQUIRE_NO_ESCALATION
APPROVAL_REQUIRED_OPERATION=SAFE_STOP / RETURN_TO_L1
DANGER_FULL_ACCESS_AUTO_UPGRADE=PROHIBITED
SILENT_POLICY_WEAKENING=PROHIBITED
```

Do not wait for a browser approval prompt that native headless does not provide. Do not switch to `danger-full-access`, another executor or another permission policy merely to force progress.

---

## 5. First-real-task baseline check stays inside the same invocation

The existing current-priority rule remains unchanged: there is no separate synthetic paid qualification stage.

At the start of the first real bounded DSH task, before Writer file mutation, the same one-paste/headless run must establish:

```text
EXPECTED_DSH_VERSION_VISIBLE=PASS
DEEPSEEK_OFFICIAL_PROVIDER_VISIBLE=PASS
PTC_CODE_PRESET_VISIBLE=PASS
WORKSPACE_WRITE_PLUS_ASK_VISIBLE=PASS
ROOT_AGENTS_AUTOLOAD=PASS
FOUR_PROJECT_SKILLS_DISCOVERED=PASS
L1_FROZEN_MODEL_REASONING_MATCH=PASS
HEADLESS_APPROVAL_FAIL_CLOSED_SEMANTICS=PASS_BY_FIRST_PARTY_CONTRACT
```

The last approval item does not require a synthetic approval attempt or an extra paid model request. It is a contract check against the pinned first-party release; the real task should simply stay inside operations that do not require approval escalation.

If any required baseline item fails:

```text
SAFE_STOP_BEFORE_FILE_MUTATION
```

The real task's normal implementation, tests, exact artifact/head, CI where applicable, and independent review remain the coding capability evidence. Cache/skill-body telemetry is collected naturally where observable and is not a reason to create extra paid model turns.

---

## 6. `0.1.0-rc.8` transition rule

The previously frozen accepted project setup baseline remains historical evidence:

```text
PREVIOUS_ACCEPTED_DSH_BASELINE=0.1.0-rc.7
PREVIOUS_UPSTREAM_SHA=99f6f02fecdb7dff40c3fbc9470f5907c29f74ca
```

The current first-party upstream release and local upgrade candidate are:

```text
DSH_UPGRADE_CANDIDATE=0.1.0-rc.8
DSH_UPGRADE_CANDIDATE_UPSTREAM_SHA=141eb6fef83422698aef7a981029e843e8161534
FIRST_REAL_TASK_MAY_VALIDATE_RC8=YES
```

This proposal authorizes `rc.8` only as the bounded candidate for the next real DSH task's pre-mutation seam validation. It does **not** declare `rc.8` independently accepted merely because it installs or launches.

The first real task may proceed on `rc.8` only when the required baseline checks above pass before mutation. If the real task then completes its normal validation and independent acceptance without exposing a DSH seam regression, Engineering may propose the narrow follow-up governance update that promotes `rc.8` from candidate to accepted project baseline.

Any incompatible change to command grammar, provider/model/reasoning selection, Code/PTC behavior, permission/approval semantics, instruction loading, skill discovery, session semantics, task/result transport or evidence behavior requires SAFE_STOP and L1 route resolution.

---

## 7. Session semantics: do not invent Codex behavior for DSH

Workflow parity with Codex means **one-paste operator UX**, not pretending the two executors have identical session commands.

For the native DSH headless route currently verified from first-party `rc.8` documentation:

```text
DEFAULT_HEADLESS_SESSION_MODE=NEW_FRESH_PERSISTED_SESSION
```

Do not invent `--last`, implicit resume, or an exact-session headless resume grammar that has not been verified from the current first-party DSH release.

The existing project rule permitting same-Writer/same-stage session reuse remains a semantic allowance only when the selected DSH surface actually provides a verified exact-session continuation mechanism. Until that mechanism is explicitly verified for headless execution, Engineering should use a fresh one-shot headless session for each bounded task invocation rather than guessing resume behavior.

Independent Review always uses independent context as required by project governance.

---

## 8. Result and acceptance boundaries

A successful DSH process exit or Writer self-reported `PASS` is execution evidence, not independent acceptance.

The one-paste block should preserve enough raw output to identify:

- executor/version/provider/model/reasoning;
- task/session identity where available;
- exact repository/worktree/branch/head;
- files changed;
- validation commands actually observed;
- exit/failure state;
- Result Packet/final Writer summary;
- token/cache/time evidence where naturally available.

After Writer completion:

```text
WRITER_PASS != INDEPENDENT_ACCEPTANCE
```

Mark Ready, merge, deployment, runtime/cloud mutation and all other retained gates remain separate current user authorizations.

---

## 9. Failure semantics

The default one-paste DSH route must fail closed for at least these cases:

- `dsh` missing or wrong expected version;
- expected main/base/head mismatch;
- wrong repository or worktree;
- main-worktree mutation attempt;
- conflicting branch/worktree ownership;
- missing/stale L1 preflight attestations;
- provider/model/reasoning mismatch;
- preset/permission/instruction/skill baseline failure;
- an operation requires approval but native headless has no configured answerer;
- task packet corruption/truncation;
- new material route or scope decision discovered by the Writer;
- required allowlist expansion;
- DSH process nonzero exit;
- validation failure;
- request for an authority explicitly retained by the user.

Do not respond to a failed headless task by silently switching to Web UI, another executor, a different model, broader permissions or a higher reasoning/cost tier. Return the exact failure to L1 for bounded repair/replan.

---

## 10. First-party evidence for this route

External evidence was checked after the independent workflow analysis, using DeepSeek's first-party repository at the `rc.8` release commit:

```text
UPSTREAM_REPOSITORY=deepseek-ai/deepseek-harness
UPSTREAM_RELEASE_SHA=141eb6fef83422698aef7a981029e843e8161534
CLI_README=apps/cli/README.md
CLI_BEHAVIOR_REFERENCE=apps/cli/reference/README.md
AGENT_DEFAULT_MODEL_README=packages/core/agent-default-model/README.md
USER_APPROVAL_README=packages/interaction/user-approval/README.md
BASE_BUNDLE_PATCH=packages/bundle/base/cordis.patch.yml
HEADLESS_BUNDLE_PATCH=packages/bundle/headless/cordis.patch.yml
```

The first-party material confirms:

- `dsh --profile headless "job"` is a supported entry mode;
- the invoking directory is the default workspace root;
- headless creates a fresh persisted one-shot session and exits after deriving the final result;
- headless mounts no Host/HTTP/Web/browser layer;
- `dsh web` remains a separate browser-surface alias;
- `DSH_TOOLS_MODE=code` is a supported process tool-mode selector;
- new sessions default to the `workspace-write` permission preset with approval policy `ask`;
- headless Agent creation reads the shared `agent-default-model` selection, including a Settings-layer provider/model and optional `reasoningEffort`;
- the approval service has no built-in answerer, so headless approval-required operations fail closed unless a separately configured answerer exists.

This evidence confirms the independent conclusion that native headless execution is the simplest provider-native path for Codex-like one-paste operator UX. It also tightens the route: model/reasoning authority must be proven before mutation, and `ask` in native headless is a fail-closed boundary rather than an implied interactive Terminal approval surface.

---

## 11. Current decision

```text
DECISION=PROCEED
USER_OPERATED_DSH_DEFAULT=ONE_PASTE_NATIVE_HEADLESS
WEB_UI_DEFAULT=NO
WEB_UI_OPTIONAL=YES
HERMES_REQUIRED=NO
CUSTOM_DSH_PLUGIN_REQUIRED=NO
L1_MODEL_REASONING_MUST_MATCH_BEFORE_MUTATION=YES
HEADLESS_APPROVAL_REQUIRED_ACTION=SAFE_STOP
FIRST_REAL_TASK_DOUBLES_AS_RC8_SEAM_AND_CAPABILITY_VALIDATION=YES
INDEPENDENT_REVIEW_REQUIRED=YES
```

This rule changes the operator transport/UX only. It does not change product, strategy, runtime, trading, release or financial authority.
