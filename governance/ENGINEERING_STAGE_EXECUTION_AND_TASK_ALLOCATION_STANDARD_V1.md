# Engineering Stage Execution and Task Allocation Standard V1

**Status:** FROZEN  
**Effective date:** 2026-07-29  
**Project:** `TRADER_ASSIST_V0_FIRST_LAUNCH_R3`  
**Repository:** `woshixiong/trader-assist-v0`  
**Supersedes for future execution:** ad hoc multi-window micro-step development, repeated speculative patch scripts, and any task assignment that requires capabilities unavailable in the assigned execution environment

## 1. Governing outcome

All future engineering work must use the following default operating model:

```text
ONE COHERENT STAGE OBJECTIVE
→ CAPABILITY-MATCHED PROJECT CONTROL AND WRITER
→ ONE CONTINUOUS STAGE EXECUTION
→ COMPLETE LOCAL GATES BEFORE REMOTE MOVEMENT
→ EXACT-HEAD CI
→ INDEPENDENT READ-ONLY REVIEW
→ AT MOST ONE CONSOLIDATED REPAIR
→ SEPARATE USER AUTHORITY GATES
```

The goal is to reduce unnecessary user interaction without weakening review, safety or authority separation.

The user must not be used as a routine message bus between Project Control, Writer, CI and Reviewers.

## 2. Permanent lessons

### 2.1 PR #55 — external contract and test-fixture failure

The Hyperliquid candle incident showed that production validators and synthetic test helpers can share the same incorrect assumption and still pass focused tests.

Permanent conclusions:

- real external behavior must be observed before implementation when a safe public probe exists;
- synthetic fixtures do not prove a provider contract;
- foundational contract changes require a repository-wide semantic impact map;
- focused tests do not replace the full suite;
- GitHub CI must not be the first full downstream test;
- deployment must not be the first real end-to-end integration test;
- repeated failures require a full semantic audit, not another speculative patch script.

### 2.2 PR #57 — continuous execution and independent review

PR #57 showed that a bounded task can be implemented, tested, committed, pushed and brought to exact-head CI success in one continuous execution stage when the objective, allowlist and environment are fixed.

It also showed why independent review remains mandatory: exact-head CI passed while an independent review still found a millisecond receipt-time boundary race. The repair was then completed within the same bounded route.

Permanent conclusions:

- stage-internal engineering steps should be continuous;
- independent review must remain separate from the Writer;
- CI success does not authorize merge or deployment;
- one authoritative time sample must govern one event path when boundary semantics depend on time.

### 2.3 Capability-mismatch SAFE_STOP

An ordinary ChatGPT Project Control window correctly stopped when it was asked to clone a private repository, create a worktree, run Python 3.12 tests, commit and push, but only had a GitHub Connector and no authenticated local execution environment.

Permanent conclusion:

> A task must never be assigned to an environment that cannot satisfy its mandatory preconditions and gates.

Changing windows without changing capabilities is not a recovery strategy.

## 3. Mandatory capability preflight before task assignment

Before issuing a stage execution bundle, Project Control must classify the task and verify that the assigned environment has every required capability.

Record:

```text
TASK_CLASS
REPOSITORY_ACCESS
PRIVATE_CLONE_ACCESS
LOCAL_GIT
WORKTREE_SUPPORT
SUPPORTED_PYTHON_ENVIRONMENT
DEPENDENCY_INSTALL_OR_REUSE
TEST_EXECUTION
STATIC_ANALYSIS
COMMIT_AUTHORITY
PUSH_AUTHORITY
GITHUB_PR_ACCESS
GITHUB_CI_ACCESS
HOST_OR_CLOUD_ACCESS
CREDENTIAL_ACCESS
```

A task may start only when every mandatory capability is `AVAILABLE` or an explicitly approved separate participant owns that capability.

If a mandatory capability is unavailable:

```text
SAFE_STOP
→ REASSIGN THE ROLE
→ DO NOT WEAKEN THE GATE
→ DO NOT MOVE THE REMOTE BRANCH TO DISCOVER FAILURES
```

## 4. Fixed role allocation

### 4.1 Project Control

Project Control owns:

- exact live GitHub identity;
- stage objective and acceptance criteria;
- capability preflight;
- Writer assignment;
- exact file/source allowlist;
- commit budget;
- required local gates;
- CI and review routing;
- consolidated repair control;
- safe-stop and escalation;
- authority-boundary enforcement.

Project Control does not need to execute code locally if a capability-matched Writer owns local execution.

### 4.2 Local Writer

A code-writing task requiring local gates must be assigned to a Writer environment that has:

- authenticated access to the private repository;
- a valid clone and clean worktree;
- the supported Python environment and dependencies;
- ability to run focused and full tests;
- Ruff, mypy, compileall and diff checks;
- normal commit and fast-forward push capability.

Approved examples include an authenticated local Codex CLI, Codex desktop workflow with repository access, or TRAE IDE SOLO with the required local toolchain.

A Connector-only chat window is not a local Writer.

### 4.3 Independent Reviewer

The independent Reviewer must:

- be read-only toward the reviewed exact head;
- inspect the complete base-to-head diff;
- verify behavior, false-positive guards and authority boundaries;
- verify exact-head CI evidence;
- remain independent from the Writer’s implementation reasoning.

### 4.4 User

The user retains separate authority for:

- stage activation when required;
- Mark Ready;
- merge;
- deployment;
- service start, restart or enable;
- production smoke;
- AWS or paid-resource access;
- credentials;
- account access;
- signing, nonce and exchange writes;
- order submission and cancellation.

## 5. Stage granularity

One stage must contain one coherent engineering objective, not one file or one command.

A normal stage may continuously include:

```text
IDENTITY CHECK
→ WORKTREE PREPARATION OR REUSE
→ IMPLEMENTATION
→ FOCUSED TESTS
→ FULL PYTEST
→ RUFF
→ MYPY
→ COMPILEALL
→ DIFF CHECK
→ SCOPE CHECK
→ SECRET SCAN
→ COMMIT
→ NORMAL PUSH
→ EXACT-HEAD CI
```

Do not split a stage merely by:

- file;
- function;
- individual test;
- command;
- lint finding;
- one Reviewer comment.

Split or stop only when crossing a material boundary, including:

- product scope change;
- new runtime or production authority;
- AWS or paid resources;
- credentials;
- account or exchange-write authority;
- dependency, lockfile or workflow expansion not already authorized;
- unreviewable allowlist expansion;
- incompatible Writer ownership;
- a different root cause.

## 6. Stage execution bundle requirements

Every code stage must receive one complete execution bundle containing:

```text
ROLE
TASK_ID
REPOSITORY
PR OR NEW-BRANCH ROUTE
EXACT_BASE
EXPECTED_PARENT OR HEAD
BRANCH
WORKTREE
SUPPORTED_ENVIRONMENT
OBJECTIVE
ROOT_CAUSE OR DESIGN BASIS
ALLOWED_FILES
PROHIBITED_FILES
REQUIRED_BEHAVIOR
MUST_REMAIN_BEHAVIOR
TEST_PLAN
FULL_LOCAL_GATES
COMMIT_BUDGET
PUSH_METHOD
CI_REQUIREMENT
REVIEW_REQUIREMENT
REPAIR_BUDGET
SAFE_STOP_CONDITIONS
FINAL_AUTHORITY_BOUNDARY
REPORT_FORMAT
```

The bundle must be executable without repeated clarification or one-prompt-per-command interaction.

## 7. Continuous execution rule

After the user or governing authority activates a bounded stage, the capability-matched Writer may proceed continuously through all authorized stage-internal steps.

The Writer does not need repeated user confirmation to:

- edit files within the allowlist;
- add or update in-scope tests;
- run local tests and static checks;
- fix an in-scope formatting, typing or test failure;
- create the authorized normal commit;
- push by normal fast-forward;
- wait for and inspect exact-head CI.

The Writer must stop before:

- allowlist expansion;
- a new root cause;
- a second ordinary repair cycle;
- Mark Ready;
- merge;
- deployment;
- activation;
- credentials, account or exchange-write access.

## 8. External and foundational contract gate

For changes involving external APIs, WebSocket frames, timestamps, protocol fields, canonical payloads, hashes, persistence or shared invariants, use this sequence:

```text
REAL READ-ONLY CONTRACT EVIDENCE
→ CANONICAL REALISTIC FIXTURE
→ REPOSITORY-WIDE SEMANTIC IMPACT MAP
→ ONE COHERENT IMPLEMENTATION
→ AFFECTED TESTS
→ FULL LOCAL GATES
→ EXACT-HEAD CI
→ INDEPENDENT REVIEW
→ NO-WRITE PREDEPLOYMENT REHEARSAL
→ SEPARATE ACTIVATION AUTHORITY
```

### 8.1 Real-contract evidence

Record, as applicable:

- endpoint or channel;
- request shape;
- required fields;
- timestamp units and inclusive/exclusive boundaries;
- sanitized real response shape;
- empty and error behavior;
- observation date;
- whether provider documentation matches observed behavior.

### 8.2 Canonical fixture

Use one fixture source derived from real sanitized evidence. Test helpers may vary values but may not independently redefine protocol semantics.

### 8.3 Semantic impact map

Search and classify:

```text
MUST_CHANGE
MUST_REMAIN
TEST_FIXTURE
HISTORICAL_COMPATIBILITY
UNRELATED
```

Include parser, strategy, hashes, identifiers, demos, persistence, replay, outcome readers and tests.

### 8.4 No-write rehearsal

Before accepted real operation, test the exact release candidate on the supported host at the lowest practical authority, with no account or exchange-write authority.

Deployment must not be the first integration test.

## 9. Local validation before remote movement

Before commit or push, run all applicable gates:

1. focused parser/contract tests;
2. directly affected functional tests;
3. downstream tests for shared objects and invariants;
4. full repository pytest;
5. Ruff;
6. authoritative mypy;
7. compileall;
8. `git diff --check`;
9. exact changed-file scope check;
10. secret and credential scan.

If the current environment cannot run an authoritative gate, reassign the Writer or gate to a supported environment before moving the remote branch.

GitHub CI is exact-head verification, not a substitute for avoidably omitted local gates.

## 10. CI and review

After local gates pass:

- create a normal cohesive commit within budget;
- do not amend, rebase, squash or force-push unless explicitly authorized;
- push normally;
- verify CI against the exact head SHA;
- require completed/success;
- perform an independent base-to-head read-only review.

CI from an older SHA is invalid evidence.

## 11. Consolidated repair rule

All blocking review findings within the same root cause and stage must be combined into one repair packet.

Prohibited patterns:

- one prompt per finding;
- one prompt per file;
- one speculative script per failed test;
- V13/V14-style repeated user-run patch scripts;
- serial Reviewer-specific repairs;
- moving the branch merely to discover the next local failure.

Normal budget:

```text
ONE NORMAL CONSOLIDATED REPAIR
+
AT MOST ONE SEPARATELY AUTHORIZED EXCEPTIONAL REPAIR
```

If the route still does not close, reduce scope or start a clean replacement from current main.

## 12. Task allocation matrix

### Read-only repository or PR analysis

May be assigned to:

- GitHub Connector-backed ChatGPT;
- independent Reviewer window.

Required capabilities:

- repository read access;
- PR metadata, diff and CI visibility.

### Code implementation with local tests

Must be assigned to:

- authenticated local Codex CLI/Desktop environment; or
- TRAE IDE SOLO/local Writer with repository and toolchain access.

Required capabilities:

- private clone/worktree;
- supported environment;
- tests and static checks;
- commit and push.

### CI debugging

Assign to an environment with:

- exact-head metadata;
- workflow job and log access;
- local reproduction capability when code changes may be needed.

### Documentation-only governance change

May be performed through GitHub Connector when:

- the exact base and scope are verified;
- no generated artifacts or local validation are required;
- the PR remains Draft until reviewed;
- no direct main mutation occurs.

### Deployment or host work

Must be assigned only to an explicitly authorized host-capable environment with exact-SHA and authority controls.

### Credential, account or exchange-write work

Requires a separate explicit user authorization and a task-specific security boundary.

## 13. Mandatory task-allocation check in every future prompt

Every future Project Control or engineering prompt must include:

```text
EXECUTION_ENVIRONMENT:

AVAILABLE_CAPABILITIES:

MISSING_CAPABILITIES:

ROLE_ASSIGNMENT:
PROJECT_CONTROL=
WRITER=
REVIEWER=

CAPABILITY_MATCH:
PASS / SAFE_STOP
```

A prompt that assigns local implementation to a Connector-only window is invalid and must be rejected before work begins.

## 14. Completion report

Every completed stage must report:

```text
REVIEW_STATUS
EXACT_BASE
PARENT
FINAL_HEAD
BRANCH
COMMITS
CHANGED_FILES
CAPABILITY_PREFLIGHT
IMPLEMENTATION_RESULT
FOCUSED_TESTS
FULL_PYTEST
RUFF
MYPY
COMPILEALL
DIFF_CHECK
SCOPE_CHECK
SECRET_SCAN
EXACT_HEAD_CI
INDEPENDENT_REVIEW
RESIDUAL_RISKS
ROLLBACK
MARK_READY_EXECUTED
MERGE_EXECUTED
DEPLOYMENT_EXECUTED
ACTIVATION_EXECUTED
ACCOUNT_ACCESS_EXECUTED
EXCHANGE_WRITE_EXECUTED
```

## 15. Frozen ruling

```text
STAGE_INTERNAL_EXECUTION:
CONTINUOUS_BY_DEFAULT

USER_AS_ROUTINE_MESSAGE_BUS:
PROHIBITED

TASK_TO_ENVIRONMENT_CAPABILITY_MATCH:
MANDATORY

CONNECTOR_ONLY_WINDOW_AS_LOCAL_WRITER:
PROHIBITED

REAL_EXTERNAL_CONTRACT_EVIDENCE:
MANDATORY_WHEN_APPLICABLE

CANONICAL_REALISTIC_FIXTURE:
MANDATORY_WHEN_APPLICABLE

REPOSITORY_WIDE_IMPACT_MAP:
MANDATORY_FOR_FOUNDATIONAL_CONTRACT_CHANGES

FULL_LOCAL_GATES_BEFORE_REMOTE_MOVEMENT:
MANDATORY_WHEN SUPPORTED BY THE ASSIGNED TASK CLASS

EXACT_HEAD_CI:
MANDATORY

INDEPENDENT_READ_ONLY_REVIEW:
MANDATORY

CONSOLIDATED_REPAIR:
ONE NORMAL ROUND

MARK_READY_MERGE_DEPLOYMENT_ACTIVATION:
SEPARATE USER AUTHORITY
```

This standard is binding after merge into `main` and remains authoritative until a later merged governance document explicitly supersedes it.
