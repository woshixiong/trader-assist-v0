# Trader Assist / Trade OS — Unified Engineering Governance and Execution Standard V1

**Status:** CANONICAL GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-17  
**Repository:** `woshixiong/trader-assist-v0`  
**Purpose:** provide one mandatory engineering ruleset that every project participant checks before research, route selection, implementation, review, handoff, automation or operational engineering work.

This document consolidates the durable engineering rules previously distributed across merged governance, Draft governance PRs, issue discussions and workflow lessons. It does not grant Mark Ready, merge, deployment, runtime, cloud, credential, account/private API, signing, wallet, exchange-write, order-submission or trading authority.

When this document conflicts with an older general engineering-process rule, this document governs for future engineering. More specific current product, strategy, security, operations or authority contracts still govern their own narrower domain when they are stricter or more specific.

---

## 1. Canonical operating principle

The project optimizes for **validated useful progress per unit of engineering effort** while preserving the minimum real safety and authority boundary.

The default sequence is:

```text
LOAD CANONICAL RULES + LIVE STATE
→ DEFINE THE EXACT CURRENT PROBLEM
→ INDEPENDENT ANALYSIS
→ EXTERNAL / MATURE-SOLUTION RESEARCH
→ SYNTHESIS
→ SIMPLICITY + REUSE + CONTINUITY + SCALE GATES
→ FREEZE ROOT CAUSE / AUTHORITIES / INVARIANTS / ATTACK MATRIX
→ CAPABILITY-MATCHED EXECUTION PLAN
→ ONE COMPLETE TASK PACKET
→ ONE COHERENT IMPLEMENTATION STAGE
→ LOCAL / REALISTIC VALIDATION
→ EXACT ARTIFACT FREEZE
→ EXACT-HEAD CI
→ INDEPENDENT REVIEW
→ BOUNDED REPAIR OR REPLAN
→ SEPARATE USER AUTHORITY GATES
→ CAPTURE LESSONS / DEFERRED WORK
```

Every material task must end in an explicit disposition:

```text
PROCEED
REPAIR
REPLAN
DEFER
REPLACE
SHIP_CANDIDATE
SAFE_STOP
```

Repeated research, patching, prompt addenda or message routing without convergence is not progress.

---

## 2. Mandatory pre-work comparison for every participant

Before beginning any project work, every ChatGPT window, Codex Writer/Reviewer, Trae lane, Hermes operator, human contributor or other Agent must compare the task against this ruleset.

The minimum pre-work record is:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS/FAIL
ROLE=
TASK_CLASS=MATERIAL/MECHANICAL
LIVE_REPO=
LIVE_MAIN_SHA=
ACTIVE_ISSUE_OR_PR=
EXACT_START_HEAD=
CURRENT_AUTHORITY_SOURCES=
APPLICABLE_RULE_SECTIONS=
CAPABILITY_MATCH=PASS/SAFE_STOP
USER_AUTHORITY_REQUIRED_NOW=YES/NO
```

For a **material** task, this record must also include or reference the complete Engineering Preflight record defined by `MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`.

No Writer implementation prompt may be issued for material work until:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

Mechanical execution may use a shortened preflight, but if it exposes a new technical route, authority, architecture, provider, persistence, recovery, concurrency, scale or product decision, it immediately becomes material work and the full gate is required.

---

## 3. Source of truth and precedence

### 3.1 GitHub is canonical

GitHub repository state is the project engineering source of truth.

Before acting:

- resolve current `main` and exact SHA;
- resolve current issue/PR/branch/head and CI where relevant;
- read the mandatory successor-window path in `AGENTS.md` and `PROJECT_RULES_INDEX.md`;
- prefer actual code, exact diffs, accepted artifacts and live GitHub objects over stale chat summaries or stale PR-body narrative.

Permanent engineering rules must not exist only in chat memory, one Issue comment, one local prompt or one unmerged Draft indefinitely.

### 3.2 Rule precedence

Use this order when rules appear to conflict:

1. explicit current user authority and safety boundary;
2. current accepted product/strategy/security/operations authority for the narrow domain;
3. this unified engineering standard;
4. mandatory preflight and research-method documents;
5. specialized execution contracts such as Hermes when the relevant role is active;
6. older merged workflow documents;
7. Draft/historical governance and chat summaries as research inputs only.

A less strict general rule never weakens a stricter authority or safety rule.

### 3.3 Stale governance disposition

Older governance PRs may contain useful ideas, but they are not automatically active authority. Their useful durable principles must be absorbed into the canonical path or explicitly rejected/superseded.

Do not keep multiple overlapping engineering constitutions active when one canonical rule can express the current decision.

---

## 4. Mandatory three-stage research and decision method

For every material research, product/strategy/engineering route, architecture choice, framework/tool/provider selection, migration, optimization or other direction-setting task, use this order:

### Phase 1 — independent analysis first

Before consulting external conclusions, determine from first principles and project facts:

- the exact problem;
- root-cause hypotheses;
- known facts, assumptions and unknowns;
- affected authorities and invariants;
- decision criteria;
- candidate routes;
- causal/mechanical reasoning;
- expected advantages and failure modes;
- what evidence could confirm, weaken or falsify the preliminary position.

Preserve a short pre-research position for material decisions.

### Phase 2 — external evidence and mature solutions

Then research the strongest available evidence, including where applicable:

- official/provider documentation and specifications;
- first-party source repositories and SDKs;
- primary technical research, papers, datasets and benchmarks;
- mature maintained frameworks and standard-library capabilities;
- validated production cases and postmortems;
- maintained open-source implementations;
- competing approaches;
- failure cases, limitations and disconfirming evidence.

Do not search only for support of the initial idea.

For crypto/blockchain/transaction/arbitrage work, English-language primary and technical sources are preferred unless another source is demonstrably more authoritative.

### Phase 3 — synthesis and decision

Explicitly state:

- what external evidence confirms;
- what it changes or refines;
- what it contradicts or falsifies;
- unresolved uncertainty;
- rejected routes and why;
- selected route and why it fits current Trader Assist / Trade OS constraints;
- required validation or experiment.

Research must converge to a decision. It must not become unlimited information collection.

---

## 5. Mature-solution-first and proprietary-value rule

Project engineering effort should concentrate on differentiating trading value and thin integration, not reimplement mature commodity infrastructure.

For a nontrivial technical capability, evaluate in this order:

```text
REUSE AN ACCEPTED EXISTING PROJECT CAPABILITY
→ USE PROVIDER-NATIVE CAPABILITY
→ USE STANDARD / OFFICIAL LIBRARY CAPABILITY
→ ADOPT A MATURE MAINTAINED EXTERNAL SOLUTION
→ ADD THE THINNEST PRACTICAL ADAPTER
→ IMPLEMENT SMALL PROJECT-OWNED DOMAIN LOGIC
→ BUILD CUSTOM INFRASTRUCTURE ONLY AS A DOCUMENTED LAST RESORT
```

Technical difficulty is a signal to broaden the search before increasing custom R&D.

Custom engineering is most justified for project-specific value such as:

- Scanner and candidate semantics;
- Setup and Market Event semantics;
- Strategy Kernel and causal decision contracts;
- risk/trade-plan semantics;
- authoritative evidence relationships;
- Outcome research and rapid strategy iteration;
- project-specific human-confirmed/future execution workflow integration.

Commodity scheduling, transport, backup, persistence tooling, deployment tooling, observability, orchestration and generic workflow infrastructure should use mature/provider-native solutions when they fit.

Any custom-infrastructure decision must record the concrete alternatives considered and the blocking fit gaps.

---

## 6. Simplicity-first and total-cost rule

After minimum safety, authority, correctness and recovery boundaries are preserved, select the simplest viable route by **total burden**, not lines of code.

Total burden includes:

```text
IMPLEMENTATION
+ TESTING
+ INDEPENDENT REVIEW
+ CI / RELEASE
+ OPERATOR ACTIONS
+ DEBUGGING / EVIDENCE COLLECTION
+ MODEL / TOKEN COST
+ THIRD-PARTY QUOTAS / OUTAGE RISK
+ MAINTENANCE
+ RESTART / MIGRATION / RECOVERY
+ FUTURE REPLACEMENT COST
```

A low-code/no-code route that imposes uncertain UI steps, manual payload editing, repeated screenshots, hidden quotas or difficult recovery is not automatically simple.

### Preferred solution order for low-frequency operational work

```text
EXISTING COMMAND
→ SHORT CHECKLIST
→ ONE-PASTE TEMPORARY COMMAND/SCRIPT
→ PROVIDER-NATIVE OR MAINTAINED TOOL
→ SMALL PERMANENT COMPONENT AFTER REPEATED VALUE
→ FRAMEWORK/SERVICE ONLY WHEN OBJECTIVELY REQUIRED
```

Do not build institution-grade infrastructure for a rare task that can be safely completed by a bounded human-assisted procedure.

### Minimum verification ladder

Test from the smallest decisive boundary outward:

1. component/direct-contract test;
2. bounded integration test;
3. required failure semantics;
4. realistic composition/end-to-end test;
5. broader regression where the changed boundary requires it.

Do not start with the largest workflow when a smaller test can answer the current question.

---

## 7. Current value, bounded delivery and cumulative learning

Default delivery loop:

```text
TEST SMALL
→ OBSERVE REAL EVIDENCE
→ REVIEW
→ DECIDE
→ IMPLEMENT THE MINIMUM COHERENT CHANGE
→ FORWARD VALIDATE
→ ITERATE
```

Rules:

- solve the current validated product/strategy need, not a speculative complete future platform;
- preserve completed/reusable accepted work;
- do not delete useful code merely to simplify the current stage;
- defer non-blocking future capability rather than partially implementing it;
- preserve raw evidence when future research can be performed offline instead of promoting uncertain research into live semantics;
- a real gap is not automatically a current-release blocker;
- late discoveries block the current release only when deferral creates material safety loss, unrecoverable evidence loss or failure of the current objective.

The project should reach a useful 5/10 system and learn from real evidence before spending heavily to perfect a 7–8/10 system.

---

## 8. Continuity-first without speculative platform building

Code must have a deliberate continuation path.

A bounded implementation is unacceptable when it predictably forces a near-term rewrite of stable authority, data identity or mainline architecture merely because the current launch is smaller.

Before implementation, state:

```text
CURRENT_BOUNDED_NEED=
NEXT_EXPECTED_STAGE=
STABLE_INTERFACES=
STABLE_AUTHORITIES=
REPLACEABLE_IMPLEMENTATION_POLICY=
TUNING_PARAMETERS=
KNOWN_MIGRATION_OR_LOCKIN_RISK=
```

Prefer:

```text
STABLE NARROW CONTRACT / SEAM
+ ONE CURRENT IMPLEMENTATION
+ REPLACEABLE POLICY
```

over either:

- a throwaway host/market/provider-specific shortcut; or
- a speculative generalized platform for hypothetical future needs.

Launch-specific values such as market count, host identity, pacing, concurrency or provider policy must not become architectural constants unless the product contract makes them permanent.

Where an implementation is expected to change later, require a bounded replaceability proof or test demonstrating that a substitute can be introduced without rewriting unrelated upper layers.

---

## 9. Global-before-local root-cause rule

Do not repeatedly repair local symptoms when several failures may share one misplaced global responsibility.

Warning signs include:

- whole-cohort behavior driven by one local callback;
- global state changes triggered by one market or one event;
- many special cases around the same transition;
- increasing tests without a stable state/invariant model;
- Reviewer repeatedly discovering new mixed-state combinations;
- every repair adds adjacent-layer conditionals;
- strict authority conflicts expose repeated duplicate work.

When these signs appear:

```text
STOP LOCAL PATCHING
→ MODEL THE GLOBAL STATE / AUTHORITY / INVARIANT
→ RE-RUN RESEARCH + SIMPLICITY + CONTINUITY GATES
→ REDESIGN OR REPLACE THE FAILED RESPONSIBILITY BOUNDARY
```

When strict immutable authority correctly exposes duplicate or conflicting work, fix the duplicate work. Do not weaken authority validation to make the conflict disappear.

---

## 10. Architecture, authority and attack-matrix gate

Before Writer dispatch for cross-layer or material runtime work, freeze:

- root cause level: local / cross-layer / architectural / unknown;
- affected authorities;
- current source of truth for each durable or live state;
- prohibited second authorities/caches/queues;
- state transitions and precedence rules;
- restart/replay semantics;
- idempotency/duplicate behavior;
- time/freshness semantics;
- current and future replaceability seams;
- attack matrix.

The attack matrix should cover the important applicable combinations:

- normal first execution;
- duplicate wakeup/retry;
- stale/out-of-order evidence;
- missing evidence;
- conflicting immutable evidence;
- partial cohort/mixed state;
- provider delay/error/omission;
- process restart;
- persistent-store reopen/replay;
- shutdown/interruption;
- supersession/race;
- boundary clocks where time semantics matter;
- scale/freshness pressure;
- unauthorized or malformed inputs.

Tests for integration claims must exercise the real composition path rather than a fake substitute that bypasses the authority boundary being claimed.

---

## 11. External/foundational contract rule

For external APIs, WebSocket frames, provider timestamps, canonical payloads, hashes, persistence formats or shared foundational invariants, use:

```text
REAL READ-ONLY CONTRACT EVIDENCE
→ CANONICAL REALISTIC FIXTURE
→ REPOSITORY-WIDE SEMANTIC IMPACT MAP
→ ONE COHERENT IMPLEMENTATION
→ AFFECTED TESTS
→ FULL APPLICABLE LOCAL GATES
→ EXACT-HEAD CI
→ INDEPENDENT REVIEW
→ LOWEST-AUTHORITY REALISTIC REHEARSAL WHEN REQUIRED
```

Synthetic fixtures that encode the same wrong assumption as production code do not prove an external contract.

For foundational changes, classify affected code as:

```text
MUST_CHANGE
MUST_REMAIN
TEST_FIXTURE
HISTORICAL_COMPATIBILITY
UNRELATED
```

Deployment/First Live must not become the first meaningful real integration test when a safe read-only or no-write rehearsal is available.

---

## 12. Scale / provider / freshness gate

Before first deployment or any material change to market count, history depth, cadence, confirmation/retry count, REST/WS usage, concurrency, database workload or cohort size, calculate the relevant workload budget.

At minimum where applicable:

```text
market_count × calls_per_market × provider_weight × cadence
market_count × history_points × database_operations
```

Estimate or measure:

- provider headroom including retries;
- p50/p95/worst-case completion and freshness latency;
- CPU/memory/DB operation order of magnitude;
- event-loop responsiveness;
- shutdown responsiveness;
- intended trading/scanner freshness SLA.

Tiny-fixture correctness is insufficient for a scale-dependent bottleneck. Include at least one realistic-order-of-magnitude acceptance test when production scale materially differs.

Do not respond by building a generic capacity platform unless evidence requires one.

---

## 13. Capability-matched task allocation

A task must never be assigned to an environment that cannot perform its mandatory gates.

Before execution, record applicable capabilities:

```text
REPOSITORY_ACCESS
PRIVATE_CLONE_ACCESS
LOCAL_GIT
WORKTREE_SUPPORT
SUPPORTED_RUNTIME/DEPENDENCIES
TEST_EXECUTION
STATIC_ANALYSIS
COMMIT_AUTHORITY
PUSH_AUTHORITY
GITHUB_PR_ACCESS
GITHUB_CI_ACCESS
HOST/CLOUD_ACCESS
CREDENTIAL_ACCESS
```

If a mandatory capability is absent:

```text
SAFE_STOP
→ REASSIGN THE ROLE OR SPLIT CAPABILITY OWNERSHIP EXPLICITLY
→ DO NOT WEAKEN THE GATE
```

A connector-only chat window is not a local code Writer when local implementation/testing is required.

Documentation-only governance changes may be performed through a GitHub connector when exact base/scope are verified and no unavailable local/generated-artifact gate is required.

---

## 14. Coherent stage execution and user-attention rule

One engineering stage should represent one coherent objective, not one file, command, lint finding or Reviewer comment.

Within one authorized stage, a capability-matched Writer may continuously perform the actions already authorized by the task contract, including applicable:

```text
IDENTITY / WORKTREE PREFLIGHT
→ IMPLEMENTATION
→ IN-SCOPE TEST CORRECTION
→ FOCUSED TESTS
→ FULL/RELEVANT REGRESSION
→ RUFF / MYPY / COMPILE
→ DIFF / SCOPE / SECRET CHECKS
→ AUTHORIZED COMMIT/PUSH IF INCLUDED
→ EXACT-HEAD CI OBSERVATION
```

Do not use the user as a routine message bus between Engineering, Writer, CI and Reviewer when the workflow can carry exact evidence directly.

Stop when the task reaches a materially new boundary, including:

- new root cause;
- allowlist expansion;
- product/strategy scope decision;
- architecture/authority change not frozen in the task;
- new dependency/framework/service;
- repair budget exhaustion;
- Mark Ready;
- merge;
- deployment/runtime/cloud mutation;
- credentials/private API/signing/exchange write/trading action.

---

## 15. Writer, Reviewer and parallelism rules

### One primary Writer per coherent shared-authority stage

```text
PARALLELIZE INDEPENDENT WORK
SERIALIZE SHARED AUTHORITY
```

Do not run competing Writers against the same durable truth, state machine, authority or release branch.

Disjoint modules may be parallelized only when contracts and ownership are frozen and integration responsibility is explicit.

### Independent review

Writer self-reported PASS is execution evidence, not independent acceptance.

Independent Reviewer must inspect actual code/artifact/delta, authority seams, test authenticity and exact-head CI.

Reviewer context should be independent from Writer reasoning when independence is a control objective.

### Exact artifact review

Review one exact object:

- exact GitHub head;
- integrity-bound dirty-worktree review packet; or
- exact delta against an independently accepted fingerprint/baseline.

Do not review an approximation.

### Delta-first after accepted baseline

Once a baseline is independently accepted, narrow subsequent work is reviewed as:

```text
ACCEPTED BASELINE
+ EXACT NEW DELTA
+ TARGETED REGRESSION / BYPASS CHECKS
```

Do not repeatedly reread thousands of unchanged accepted lines unless the delta touches them, changes a dependency or provides concrete regression evidence.

---

## 16. Repair budget and convergence stop-loss

For one bounded design route:

```text
INITIAL IMPLEMENTATION
+ AT MOST ONE NORMAL CONSOLIDATED REPAIR
+ AT MOST ONE EXPLICITLY AUTHORIZED EXCEPTIONAL NARROW REPAIR
```

No routine Repair 3/4/5.

Exceptional repair is allowed only when the architecture has otherwise passed, the remaining blocker is narrow and understood, no new authority/platform is introduced, and replacement cost is clearly disproportionate.

If the same root problem survives, or a blocker proves the problem crosses previously assumed authority/layer boundaries:

```text
HOLISTIC_CONVERGENCE_GATE
```

Then:

- stop Writer coding;
- review base→HEAD and the whole affected state/authority path;
- identify the common root cause;
- re-run the research, mature-solution, simplicity, continuity and scale gates;
- salvage independently accepted work;
- reduce scope, replace the failed design, adopt a mature pattern, or defer;
- issue a new route only after convergence.

Sunk cost never authorizes another patch.

Consolidate accepted findings by root cause. Do not issue one repair prompt per finding/file/test.

---

## 17. Complete-task-packet rule

The Writer must receive one complete self-contained task contract before execution.

A material task packet should contain, as applicable:

```text
ROLE / MODE
TASK_ID
REPOSITORY
LIVE_MAIN / EXACT_BASE / EXPECTED_HEAD
BRANCH / WORKTREE
OBJECTIVE / ROOT_CAUSE
CURRENT_AUTHORITIES / FROZEN_INVARIANTS
ALLOWED_FILES / PROHIBITED_SCOPE
REQUIRED_BEHAVIOR / MUST_REMAIN_BEHAVIOR
EXTERNAL_EVIDENCE OR REFERENCES
CONTINUITY / REPLACEABILITY REQUIREMENTS
SCALE / FRESHNESS REQUIREMENTS
ATTACK_MATRIX
TEST_PLAN / LOCAL_GATES / CI
COMMIT / PUSH AUTHORITY
REVIEW REQUIREMENT
REPAIR_STAGE / REPAIR_BUDGET
SAFE_STOP CONDITIONS
FINAL USER AUTHORITY BOUNDARY
OUTPUT CONTRACT
```

If a new architecture invariant, provider constraint, authority boundary, future-continuity requirement or major attack case is discovered after the task has been issued but before execution, the old prompt is VOID. Regenerate one complete replacement prompt.

Do not make the user assemble architecture-critical addenda.

---

## 18. Lossless handoff and command propagation

Authoritative handoffs must preserve exact meaning and control fields.

Do not convert:

```text
AUTHORITATIVE TASK
→ INTERMEDIARY SUMMARY/PARAPHRASE
→ DOWNSTREAM EXECUTOR
```

when that transformation could change scope, permissions, acceptance criteria, stop conditions, route, executor or authority.

Prefer:

```text
EXACT PACKET / POINTER + HASH
→ DOWNSTREAM READS EXACT PACKET
→ IDENTITY ACKNOWLEDGEMENT
→ EXECUTION
→ RAW EVIDENCE RETURN
```

When the Hermes operator path is used, its merged `HERMES_EXECUTION_OPERATOR_CONTRACT` and Lossless Task Packet schema are mandatory and stricter. Hermes transports/executes frozen work only; it does not research, select routes, choose models/executors, review, repair, approve or infer missing fields.

Raw evidence remains authoritative over intermediary summaries.

---

## 19. Operator one-paste Terminal rule

For user-operated macOS engineering actions, the default deliverable is **one contiguous block pasted once into an ordinary Terminal**.

The user should not have to separately:

- `cd` into a repository;
- launch Codex;
- decide which text belongs to zsh versus Codex;
- paste a second prompt;
- create a transport file merely to move the prompt;
- manually select branch/worktree when Engineering can encode it safely.

The block should self-contain, where material:

- absolute repository/worktree path;
- `cd` or tool working-directory targeting;
- fail-closed repo/branch/SHA/worktree/environment/authority preflight;
- complete Agent prompt if Codex/another executor is invoked;
- model/reasoning/sandbox/approval settings;
- authorized mutation boundary;
- required tests/verification;
- commit/push/PR behavior only when authorized;
- explicit refusal to cross merge/deploy/runtime/cloud/account/exchange gates;
- concise evidence/output to return.

For multi-step scripts, contain failures in a subshell/heredoc or equivalent so `exit` does not unnecessarily close the parent interactive Terminal/SSH session.

### Supersession of the older user-facing routing distinction

The orchestrator still must internally know whether execution is shell, Codex CLI, GitHub, FinalShell or another executor. However, the user must not be required to perform an extra routing step merely to distinguish `Terminal local command` from `Terminal -> Codex CLI`.

One-paste execution supersedes the older requirement to expose that distinction as a mandatory user action/header when doing so adds no safety value.

An extra human step is allowed only when technically unavoidable or when an authority/security boundary requires it, such as MFA, OS credential approval, secret handling, explicit merge/deploy/runtime authorization or a genuinely GUI-only action.

For an already-connected FinalShell target-host session, provide one contiguous remote-shell block rather than repeating SSH setup.

---

## 20. Codex session, prompt and token-efficiency rules

Token efficiency is an engineering constraint, never a reason to weaken correctness or independence.

### Session selection

Reuse the exact Writer session when all are true:

- same role;
- same coherent stage;
- same authorized worktree;
- prior context remains trustworthy;
- independence is not required.

Use a new independent session for:

- Writer versus final Reviewer;
- security/authority review;
- clean-route adjudication after failed architecture;
- any review where inherited Writer reasoning could bias acceptance.

Terminal-window continuity does not imply model-session continuity.

### Prompt construction

Prefer compact prompts that reference canonical repository authority rather than repasting long project histories.

Use a stable reusable prefix for:

- role/mode;
- safety/authority boundary;
- canonical rule-read requirement;
- Writer/Reviewer independence;
- output contract.

Place mutable task facts later:

- branch/base/head;
- current blocker IDs;
- allowlist;
- CI run;
- task delta.

Prompt caching is automatic; optimize stable-prefix reuse rather than telling the model to use a cache.

### Model/reasoning economy

Use the least expensive model/reasoning level likely to complete the task correctly in one pass.

Reserve highest reasoning for architecture resets, durable authority/restart semantics, security/execution boundaries, independent blocker adjudication and release-critical acceptance.

Use deterministic scripts/commands for mechanical work before spending high-capability model tokens.

### Avoid duplicate context work

Do not repeatedly re-prove accepted facts at the same exact-head boundary. After acceptance, operate on exact deltas and relevant bypass/regression risk.

---

## 21. Automation and toil rule

Automation is a means, not the objective.

Before automating repetitive work, measure or estimate:

- frequency;
- active human time;
- error/risk reduction;
- deterministic-script feasibility;
- implementation/review/maintenance cost;
- whether the underlying workflow can be simplified or eliminated instead.

Preferred order:

```text
ELIMINATE THE UNNECESSARY STEP
→ DETERMINISTIC COMMAND/SCRIPT
→ BOUNDED OPERATOR AUTOMATION
→ LOW-COST AGENT TRANSPORT
→ HIGH-CAPABILITY AGENT ONLY FOR MATERIAL JUDGMENT
```

Do not automate a bad or unnecessarily complex process merely to reduce manual clicks.

Hermes exists to reduce copy/paste/routing/waiting toil after decisions are frozen. It must not become another technical-decision authority.

---

## 22. Third-party service / UI rule

Before placing a third-party service on a critical path, evaluate:

- quota/credit/usage limits;
- exhaustion behavior;
- rate limits and outage/suspension risk;
- credential scope and rotation;
- current plan/cost where relevant;
- direct/provider-native alternative;
- replaceability and exit path.

Do not rely on remembered or assumed third-party UI when the user's current interface differs. Prefer APIs, exact commands, direct tests and current screenshots over repeated speculative button-search instructions.

Repeated variants of the same ineffective UI instruction count as the same failed route.

---

## 23. Exact release and CI discipline

Engineering acceptance and release routing must bind to exact identities.

Where applicable:

```text
EXACT BASE
EXACT HEAD
EXACT CHANGED PATHS
EXACT ARTIFACT/FINGERPRINT
EXACT CI RUN FOR THAT HEAD
```

CI from an older SHA is stale evidence.

Before commit/push when local execution is part of the stage, run all applicable local gates. GitHub CI verifies exact remote content; it should not be used as the first avoidable downstream test.

After semantic acceptance, freeze exact content before release finalization. Commit content must match the accepted candidate when a pre-commit artifact-review workflow is used.

Mark Ready, merge, deployment and production activation remain separate authority gates.

---

## 24. Authority boundaries

Engineering research, implementation, review, CI or governance never implicitly grants:

- Mark Ready;
- merge;
- deployment;
- production-host/cloud mutation;
- service start/restart/enable/reboot;
- credentials/private keys;
- account/private API;
- wallet/signing/nonce;
- real notification when separately gated;
- exchange write;
- order submission/cancellation;
- autonomous trading or financial action.

These require explicit current authorization and may not be inferred from prior approval of another stage.

Uncertain, stale, gapped, disconnected, conflicted or unreconciled mandatory state means no new risk.

---

## 25. Completion report standard

A completed material engineering stage must report applicable fields:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=
ENGINEERING_PREFLIGHT_GATE=
REVIEW_STATUS=
EXACT_BASE=
FINAL_HEAD=
BRANCH=
COMMITS=
CHANGED_FILES=
CAPABILITY_PREFLIGHT=
IMPLEMENTATION_RESULT=
FOCUSED_TESTS=
REALISTIC_SCALE_OR_COMPOSITION_TEST=
FULL/RELEVANT_REGRESSION=
RUFF=
MYPY=
COMPILEALL=
DIFF_CHECK=
SCOPE_CHECK=
SECRET_SCAN=
EXACT_HEAD_CI=
INDEPENDENT_REVIEW=
REPAIR_STAGE=
RESIDUAL_RISKS=
DEFERRED_WORK=
ROLLBACK_OR_SAFE_STOP=
MARK_READY_EXECUTED=
MERGE_EXECUTED=
DEPLOYMENT_EXECUTED=
ACTIVATION_EXECUTED=
ACCOUNT_ACCESS_EXECUTED=
EXCHANGE_WRITE_EXECUTED=
```

Report only commands/results actually observed. Do not convert unrun checks into PASS.

---

## 26. Governance maintenance rule

When a new durable engineering lesson is discovered:

1. determine whether it is project-wide or task-specific;
2. avoid creating another overlapping constitution if this document can be amended cleanly;
3. apply the three-stage research method for material new policy;
4. update this canonical file and `AGENTS.md` / `PROJECT_RULES_INDEX.md` when project-wide;
5. explicitly disposition superseded Draft governance;
6. preserve historical incidents as rationale, not as competing active authority;
7. independently review governance changes before merge.

The governance system itself must follow simplicity-first: **one canonical engineering ruleset, small specialized contracts only where role/domain specificity requires them**.

---

## 27. Consolidated disposition of prior engineering-governance inputs

This unified standard intentionally absorbs the durable principles from the following prior governance lines:

- merged research/evidence/decision method — retained as a specialized detailed method and mandatory companion;
- PR #107 mandatory preflight/convergence gate — retained as the detailed material-task preflight companion;
- Draft PR #101 continuity/scale-provider principles — absorbed;
- Draft PR #96 one-paste Terminal delivery rule — absorbed, and its lower-user-burden one-paste semantics supersede the older mandatory user-facing Terminal/Codex classification;
- Draft PR #86 Engineering Workflow V4 — durable workflow, Research-Before-Build, reuse, review, repair-stop and model-routing principles absorbed;
- Draft PR #79 Codex token-efficiency rules — durable session/prompt/token rules absorbed;
- Draft PR #67 mature-solution-first / cumulative small-step principles — absorbed;
- Draft PR #58 capability-matched continuous-stage execution rules — absorbed;
- Draft PR #51 simplicity-first / two-attempt route / third-party burden principles — absorbed;
- merged Hermes execution contract and Lossless Task Packet schema — remain specialized binding companions when Hermes is the executor/operator.

After this unified rule is independently accepted and merged, the above Draft governance PRs should not be treated as separate competing active constitutions. Their branches may remain as historical evidence until explicitly closed or otherwise disposed, but future participants should start from this canonical file.

---

## 28. Frozen concise rules

```text
GITHUB_CANONICAL_SOURCE=YES
PRE_WORK_RULESET_COMPARISON=MANDATORY
MATERIAL_WRITER_DISPATCH_REQUIRES_PREFLIGHT_PASS=YES
INDEPENDENT_ANALYSIS_FIRST=MANDATORY
EXTERNAL_MATURE_SOLUTION_RESEARCH_SECOND=MANDATORY_WHEN_MATERIAL
SYNTHESIS_BEFORE_DECISION=MANDATORY
MATURE_SOLUTION_FIRST=YES
PROPRIETARY_TRADING_VALUE_FOCUS=YES
SIMPLICITY_BY_TOTAL_COST=YES
CURRENT_VALUE_BEFORE_SPECULATIVE_PLATFORM=YES
CODE_CONTINUITY_AND_REPLACEABLE_SEAMS=MANDATORY
PROVIDER_SCALE_FRESHNESS_BUDGET=MANDATORY_WHEN_APPLICABLE
GLOBAL_ROOT_CAUSE_BEFORE_LOCAL_PATCH_LOOPS=YES
REAL_EXTERNAL_CONTRACT_EVIDENCE=MANDATORY_WHEN_APPLICABLE
CAPABILITY_MATCH=MANDATORY
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
PARALLEL_READ_ONLY_OR_DISJOINT_WORK=ENCOURAGED_WHEN_SAFE
WRITER_REPORT_NOT_INDEPENDENT_ACCEPTANCE=YES
EXACT_ARTIFACT_REVIEW=MANDATORY
DELTA_REVIEW_AFTER_ACCEPTED_BASELINE=DEFAULT
NORMAL_REPAIR_LIMIT=1
EXCEPTIONAL_REPAIR_LIMIT=1
REPAIR_3_PLUS_SAME_ROUTE=PROHIBITED
HOLISTIC_CONVERGENCE_AFTER_BUDGET=MANDATORY
ARCHITECTURE_CRITICAL_PROMPT_ADDENDA=PROHIBITED_REGENERATE_COMPLETE_PACKET
LOSSLESS_HANDOFF=REQUIRED_FOR_AUTHORITY_BEARING_TASKS
MACOS_OPERATOR_DELIVERY=ONE_PASTE_TERMINAL_BY_DEFAULT
CODEX_SESSION_REUSE=SAME_ROLE_SAME_STAGE_ONLY
INDEPENDENT_REVIEW_SESSION=NEW
TOKEN_EFFICIENCY=CONSTRAINT_NOT_AUTHORITY
AUTOMATION=MEANS_NOT_GOAL
EXACT_HEAD_CI=MANDATORY_WHEN APPLICABLE
MARK_READY_MERGE_DEPLOY_RUNTIME_CREDENTIAL_ACCOUNT_EXCHANGE=SEPARATE_USER_AUTHORITY
```

---

## 29. High-constraint prompt discipline for GLM and DeepSeek coding executors

GLM-family and DeepSeek-family models may be used as peer L2 coding executors only with an explicit **high-constraint task packet**. For these executors, prompt brevity is subordinate to execution clarity. A materially underspecified prompt is a capability mismatch, not token efficiency.

This rule is based on repeated project execution evidence that these coding executors are materially more reliable when the task is narrowed mechanically, and is consistent with provider guidance that coding-agent tasks should state the goal, relevant context, engineering constraints, completion criteria and controlled execution environment explicitly.

For every material GLM or DeepSeek coding task, Engineering Control must make the prompt concrete enough that the executor does not need to invent the route, scope, authority or acceptance semantics. The packet must include, where applicable:

```text
EXACT ROLE / STAGE / OBJECTIVE
EXACT REPOSITORY / BASE / HEAD / BRANCH / WORKTREE
FROZEN ROOT CAUSE OR ACCEPTED BASELINE
WHAT IS ALREADY ACCEPTED AND MUST NOT BE REOPENED
WRITE ALLOWLIST
READ-ONLY / PROHIBITED FILES AND SYSTEMS
REQUIRED BEHAVIOR
MUST-REMAIN BEHAVIOR
AUTHORITY / ARCHITECTURE INVARIANTS
ATTACK / NEGATIVE CASES
EXACT TEST / LINT / COMPILE / DIFF COMMANDS
EXPECTED FAIL-CLOSED SEMANTICS
NO-REFACTOR / NO-OPTIMIZATION / NO-GENERALIZATION BOUNDARY
SAFE_STOP CONDITIONS
POST-MUTATION SCOPE / HASH PROOF
OUTPUT CONTRACT
FINAL USER AUTHORITY BOUNDARY
```

The prompt must explicitly prohibit the executor from filling gaps by convenience. Use direct language such as:

```text
DO NOT INFER MISSING REQUIREMENTS.
DO NOT REDESIGN THE ROUTE.
DO NOT EXPAND THE ALLOWLIST.
DO NOT FIX UNRELATED FAILURES.
IF THE REQUIRED CHANGE CROSSES THIS BOUNDARY: SAFE_STOP AND REPORT IT.
```

For a validation/review stage whose contract is test-only or read-only, state that production mutation is prohibited; discovering a production defect does not authorize the same executor to repair it. For a narrow repair, state the exact blocker and the exact semantics that must not change. For an accepted baseline, use delta-first instructions and identify the accepted fingerprint/hash when available.

The orchestrator must state the exact working directory or worktree path in user-operated coding tasks. If the active coding UI has a known direct-paste character limit, the complete authoritative prompt must either fit within that limit or be delivered losslessly through the approved Terminal/file/task-packet path. Never silently truncate, split architecture-critical instructions into ad-hoc fragments, or ask the user to reconstruct the authoritative prompt manually. For the current GLM/Trae direct-paste workflow, use a **20,000-character ceiling** unless a later verified interface limit supersedes it; if the complete prompt would exceed that ceiling, use the Terminal/file-based lossless delivery route and state the working directory explicitly.

Token efficiency still applies: omit stale history and repeated prose, but never remove scope, authority, negative constraints, tests, stop conditions or output evidence merely to make the prompt shorter. Prefer a detailed bounded packet that completes correctly in one pass over a shorter ambiguous prompt that increases repair/review cost.

DeepSeek-specific merged usage rules remain additionally binding when `DEEPSEEK_HARNESS` is selected and may be stricter than this section. A future specialized GLM contract may add stricter requirements, but may not weaken this baseline without an explicit canonical governance change.

Frozen execution rule:

```text
GLM_DEEPSEEK_MATERIAL_CODING_PROMPT=HIGH_CONSTRAINT_COMPLETE_PACKET_REQUIRED
GLM_TRAE_DIRECT_PROMPT_CEILING_CHARS=20000_UNLESS_VERIFIED_SUPERSEDED
PROMPT_TRUNCATION=PROHIBITED
OUT_OF_SCOPE_INFERENCE=PROHIBITED
WORKING_DIRECTORY=EXPLICIT
SAFE_STOP_ON_SCOPE_EXPANSION=MANDATORY
```
