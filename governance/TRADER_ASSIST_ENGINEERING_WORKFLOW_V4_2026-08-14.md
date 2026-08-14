# Trader Assist / Trade OS — Engineering Workflow V4

**Status:** FROZEN CANDIDATE  
**Effective date:** 2026-08-14  
**Project:** Trader Assist / Trade OS V0  
**Repository:** `woshixiong/trader-assist-v0`  
**Supersedes for future work:** `TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md` where the two conflict  
**Historical rule:** V3 remains retained as a record of the prior operating model.

---

## 1. Governing objective

The engineering process optimizes for **validated delivery per unit of engineering effort**, not raw coding volume.

The default loop is:

```text
LIVE STATE
→ VERIFY THE REAL PROBLEM
→ RESEARCH MATURE EXTERNAL / PROVIDER-NATIVE OPTIONS
→ COMPARE WITH INTERNAL OPTIONS
→ CHECK FUTURE MAINLINE / V0 REUSE
→ CONVERGE SCOPE + COST + ACCEPTANCE
→ IMPLEMENT ONE BOUNDED STAGE
→ INDEPENDENTLY VERIFY ACTUAL ARTIFACTS
→ REPAIR WITH A HARD STOP-LOSS
→ FREEZE EXACT CONTENT
→ RELEASE THROUGH SEPARATE AUTHORITY GATES
→ CAPTURE LEARNINGS AND DEFERRED WORK
```

The process must be able to end in one of five explicit dispositions:

```text
PROCEED
REPAIR
REPLAN
DEFER
SHIP
```

Repeated analysis without a decision is not progress.

---

## 2. What changed in the August 12–14, 2026 delivery cycle

The Multi-Asset Shadow delivery cycle demonstrated a materially more efficient operating model than the prior V3 workflow.

### 2.1 Parallelize bounded components, not shared authority

When contracts were sufficiently frozen and Codex capacity was available, independent modules were developed and verified in parallel. Parallel work was allowed only where ownership and interfaces were separable. Shared authority paths were integrated only after component boundaries were clear.

The rule is:

```text
PARALLELIZE INDEPENDENT WORK
SERIALIZE SHARED AUTHORITY
```

Do not use parallel Agents to write competing versions of the same durable authority, state machine, database truth, or release branch.

### 2.2 Stop patching a failed route merely because work already exists

The PR78 route accumulated independently confirmed authority/restart/integration defects. Rather than continue serial repairs indefinitely, the project preserved accepted work and moved to a clean replacement route. This avoided sunk-cost escalation.

The replacement path reused accepted integration work where valid, while replacing only the failed authority-ingress design. This became PR81 and was independently accepted.

The governing rule is:

```text
SALVAGE ACCEPTED WORK
REPLACE FAILED DESIGN
DO NOT DEFEND SUNK COST
```

### 2.3 Use bounded repair budgets

Bootstrap V2 used a consolidated Repair 1 for the known multi-market fan-in, no-prior-checkpoint recovery, authentic restart, and suppressed-discovery gaps. The independent artifact review then found one genuinely new, narrow time-variance defect. One exceptional Repair 2 was authorized only for that blocker.

The critical rule was frozen before Repair 2:

```text
ONE NORMAL CONSOLIDATED REPAIR
+ AT MOST ONE EXCEPTIONAL NARROW REPAIR
= MAXIMUM FOR ONE DESIGN ROUTE
```

If the same root problem survives that budget:

```text
STOP_REPLAN
NO REPAIR 3
```

This is a project-wide engineering stop-loss, not a recommendation.

### 2.4 Review the actual artifact, not the Writer's PASS statement

The Writer reported duplicate-wakeup idempotency as PASS after Repair 1. Independent artifact review found the test was masking a real clock-dependent conflict. The defect was discovered because the Reviewer inspected actual code and test semantics rather than accepting the Writer report.

Therefore:

```text
WRITER REPORT = EXECUTION EVIDENCE
NOT = INDEPENDENT ACCEPTANCE
```

Reviews must inspect actual code/delta, authority control flow, and test authenticity.

### 2.5 After an accepted baseline, use delta review instead of rereading thousands of lines

Once Repair 1 had independently passed almost all V2 behavior, Repair 2 review was constrained to the actual Repair 2 delta plus targeted regression checks. The prior independently accepted artifact was fingerprinted and used as the comparison baseline.

This avoided repeatedly re-reviewing several thousand already accepted lines.

Rule:

```text
ACCEPTED BASELINE + EXACT DELTA
> REPEATED FULL RE-REVIEW
```

Reopen an accepted area only if the new delta touches it, changes one of its dependencies, or provides concrete evidence of regression.

### 2.6 Preserve strict authority by avoiding conflicting work, not by weakening validation

Repair 2 did not relax `runtime_readiness_hash` or remove time-varying readiness identity. It prevented duplicate Strategy evaluation when durable Strategy authority already existed, while allowing downstream Evidence-derived reconciliation to continue.

General rule:

```text
WHEN STRICT AUTHORITY EXPOSES A DUPLICATE-WORK BUG:
REMOVE THE DUPLICATE WORK
DO NOT WEAKEN THE AUTHORITY CHECK
```

### 2.7 Conserve scarce high-value model quota

When Codex quota was abundant, larger parallel work and local execution could use Codex. When quota became scarce, the workflow changed deliberately:

```text
Codex / strongest code-capable Agent
→ Writer + code changes + local execution

ordinary ChatGPT high reasoning
→ architecture/adjudication/independent semantic review

shell / local mechanical tooling
→ packet assembly, hashing, diff extraction

TRAE / other capable local Agents
→ bounded fallback implementation or mechanical support when useful
```

The project stopped spending scarce Writer quota on mechanical packaging and repeated semantic review.

This resource-routing policy is now permanent: use the most expensive model only where its incremental capability matters.

### 2.8 Remove the separate Project Control window by default

The prior V3 workflow introduced a separate Project Control role. During this delivery cycle, that extra message-routing layer was removed. Engineering Optimization directly performed stage design, Writer assignment, Review design, evidence consolidation, GitHub state verification, and user-gate routing.

The result was fewer handoffs and less context loss.

New default:

```text
USER
  ↓ material authority gates only
ENGINEERING OPTIMIZATION / IMPLEMENTATION AUTHORITY
  ↓ direct stage bundles
WRITER / EXECUTION AGENTS
  ↓ artifacts
INDEPENDENT REVIEW
```

A dedicated Project Control layer is **not** part of the normal path anymore.

It may be reintroduced only when measured coordination complexity justifies it—for example many simultaneous release trains, multiple human operators, or a number of independent branches large enough that direct orchestration becomes the bottleneck.

### 2.9 Freeze exact content before GitHub finalization

Before the Bootstrap V2 candidate was committed, the exact staged patch was fingerprinted. After commit, the committed patch was re-derived and required to match the frozen fingerprint exactly. Local and remote heads were then required to match.

Stacked PRs were merged bottom-up only after checking base/head topology and tree equivalence. Post-merge main CI completed successfully.

Rule:

```text
SEMANTIC ACCEPTANCE
→ EXACT ARTIFACT FREEZE
→ COMMIT CONTENT-EQUIVALENCE
→ REMOTE EXACT-HEAD CI
→ SEPARATE MARK-READY / MERGE AUTHORITY
→ POST-MERGE TREE / CI CHECK
```

### 2.10 Do not reopen an accepted release for low-frequency future value

After main was accepted, Exit Management research identified a genuine evidence gap beyond the normal +120m Formal Outcome window. Engineering verified that the gap matters mainly for less-common longer intraday holds and can be filled cheaply in the first post-live research-evidence batch.

The release was not reopened because the incremental evidence value before First Live did not justify reopening an already accepted authority/release surface.

Rule:

```text
REAL GAP ≠ AUTOMATIC CURRENT-RELEASE BLOCKER
```

A late discovery becomes a current-release blocker only if postponement causes material safety loss, unrecoverable near-term evidence loss, or failure of the current product objective.

---

## 3. Why this cycle was more efficient

### 3.1 Better decisions happened before code

Architecture was repeatedly double-checked before implementation. The project did not treat the first plausible design as final. It compared internal proposals against existing provider-native or mature external patterns and reconsidered scope when the cost/benefit changed.

This reduced the amount of wrong code that had to be written and later removed.

### 3.2 Future development burden became an explicit acceptance dimension

Every substantial route must now answer:

- Does this create a reusable V0/mainline seam or only a one-off First Launch path?
- Does it preserve future execution, evidence, restart, and provider authority boundaries?
- Does it reduce or increase the number of durable truths?
- Does it create a framework/service/schema future work must maintain?
- Can later capability be added additively rather than replacing today's implementation?

A technically working solution may still be rejected if it creates disproportionate future migration burden.

### 3.3 Scope convergence was treated as engineering work

Repeated requests to simplify, rank priorities, estimate implementation/review burden, and remove nonessential capability improved throughput.

The project explicitly avoided optimizing for a theoretical 7–8/10 system before validating a usable 5/10 system in First Live.

### 3.4 Review cost was counted as part of implementation cost

Engineering cost is not just coding time.

For each proposed change evaluate:

```text
IMPLEMENTATION COST
+ TEST COST
+ REVIEW COST
+ RELEASE / CI COST
+ RESTART / MIGRATION COST
+ FUTURE MAINTENANCE COST
+ MODEL / TOKEN COST
+ HUMAN ATTENTION COST
```

A change that is trivial to code but reopens a large accepted authority surface may be expensive overall.

### 3.5 The workflow used evidence to decide when to stop

Failures did not automatically trigger another repair. Review findings were classified by root cause and route viability. Repeated failure of the same design axis triggers REPLAN rather than another patch.

### 3.6 High-value human gates were retained; routine message passing was removed

The user remained the authority for material product priorities, exceptional route decisions, Mark Ready, merge, deployment/runtime/cloud/trading boundaries. Routine routing between Writer and Reviewer was removed from the user's workload.

---

## 4. Mandatory Research-Before-Build Gate

Before custom implementation of any nontrivial technical capability, Engineering Optimization must complete the following sequence.

### Gate R1 — Verify current reality

Use live repository, exact SHA, CI, current provider/API documentation, and actual retained data contracts. Do not design from stale chat descriptions when authoritative state can be checked.

### Gate R2 — Search mature solutions first

For infrastructure, persistence, recovery, scheduling, data transport, deployment, observability, database tooling, and other commodity engineering problems, search in this order:

1. provider-native capability;
2. maintained standard library / official framework capability;
3. mature external managed/open-source solution;
4. small adaptation of an existing project component;
5. custom implementation only if the above do not satisfy the requirement.

Technical difficulty is a signal to broaden the external search before increasing custom R&D.

### Gate R3 — Separate differentiating work from commodity work

Custom effort is justified primarily where it creates project-specific value—for example strategy semantics, causal evidence contracts, trading risk logic, or unique workflow integration.

Do not spend strategy-development capacity reinventing generic infrastructure.

### Gate R4 — Compare alternatives explicitly

At minimum compare:

- expected engineering effort;
- review/test surface;
- authority/security implications;
- ongoing maintenance;
- future reuse;
- failure/recovery characteristics;
- provider/API dependence;
- reversibility;
- operator burden.

### Gate R5 — Converge

Research must end with one disposition:

```text
USE_EXISTING
ADAPT_EXTERNAL
BUILD_MINIMUM
DEFER
REPLAN
```

Do not keep researching merely because more information exists.

---

## 5. Future-Mainline Reuse Gate

Before authorizing implementation, classify the proposed design.

### REUSE_HIGH

- uses the same authoritative evidence/data identity future V0 will need;
- adds an additive seam rather than a temporary parallel system;
- preserves deterministic restart;
- does not create another durable truth;
- can be expanded without replacing its core contract.

### REUSE_MEDIUM

- useful to First Launch and likely reusable, but some adapter or boundary will later change;
- still avoids parallel truth and excessive migration burden.

### REUSE_LOW

- one-off state/cache/table/service;
- duplicate authority;
- special-case market logic that future mainline must remove;
- bespoke framework built only to solve a low-frequency temporary task;
- implementation likely to be deleted rather than extended.

Default ruling:

```text
REUSE_LOW
→ REJECT OR DEFER
```

unless the temporary implementation is significantly cheaper, explicitly disposable, isolated, and required to unlock immediate validated learning.

---

## 6. Complexity and investment gate

Classify proposed changes before implementation.

### C0 — Documentation / decision only

No runtime/code authority change.

### C1 — Trivial bounded delta

One or two narrow files/configs; no schema, durable authority, restart, dependency, or framework change.

### C2 — Bounded engineering stage

One coherent module or integration seam; meaningful tests; no new platform or broad authority redesign.

### C3 — Authority / persistence / restart boundary

Touches durable identity, schema, restart truth, credentials, execution authority, or large accepted surfaces. Requires explicit architecture and independent acceptance.

### C4 — New platform

New service/framework/database/distributed coordination/generalized workflow engine. Default is **do not build** unless objectively required by scale, safety, compliance, or product differentiation.

Engineering must prefer the lowest class that satisfies the actual requirement.

---

## 7. Scope convergence rules

### 7.1 Minimum useful release

Build only what is needed to validate the next real product/strategy hypothesis safely.

### 7.2 Do not solve speculative future problems inside the current release

Preserve a clean future seam, but defer implementation until evidence proves the need.

### 7.3 Do not turn research questions into production semantics

When future behavior can be tested through retained raw evidence and offline replay, prefer evidence retention over premature live decision logic.

### 7.4 Low-frequency event rule

For rare operational events, prefer existing commands, checklists, temporary scripts, provider-native tools, or guided human operation before permanent automation.

### 7.5 No infinite polish

A feature does not need to become "complete" before First Live. Once it meets current acceptance, additional sophistication competes with all other backlog items by user value and cost.

---

## 8. Repair and failure policy

### 8.1 Consolidate findings

Do not issue one repair prompt per file or Reviewer comment. Consolidate all accepted in-scope blockers by root cause.

### 8.2 Repair budget

```text
NORMAL_REPAIR_LIMIT = 1
EXCEPTIONAL_REPAIR_LIMIT = 1
```

Exceptional Repair is allowed only when:

- the architecture has otherwise passed;
- the remaining blocker is narrow and well understood;
- the fix does not introduce a new architecture or durable authority;
- replacement would cost substantially more than the bounded correction.

### 8.3 Stop-loss

If the same root cause remains after the exceptional repair:

```text
STOP_REPLAN
```

Allowed next actions:

- reduce scope;
- replace the design cleanly;
- salvage independently accepted work;
- defer the capability;
- use an external/provider-native alternative.

Forbidden:

```text
REPAIR 3
SERIAL PATCHING WITHOUT A NEW DESIGN
```

---

## 9. Review methodology

### 9.1 Writer and Reviewer independence

The Writer must not be treated as the independent Reviewer of its own work.

### 9.2 Exact artifact review

Review one of:

- exact GitHub head;
- exact dirty-worktree Review Packet with fingerprint;
- exact delta against a previously accepted fingerprint.

Do not review an approximation of the candidate.

### 9.3 Test authenticity

Tests must exercise the real composition path when the contract claims integration behavior.

Examples from the accepted Bootstrap V2 review discipline include:

- real Runtime → Bootstrap → Coordinator composition;
- advancing the clock when time variance matters;
- close/reopen a real SQLite file for restart claims;
- assert failures are empty, not merely record counts;
- prove no duplicate durable authority;
- avoid FakeCoordinator substitutes when the claim is about production composition.

### 9.4 Fail closed on authority mismatch

Never resolve idempotency by silently accepting conflicting immutable authority. Correct the duplicate work or inconsistent routing that caused the conflict.

### 9.5 Delta review after acceptance

Once a baseline is independently accepted, subsequent narrow repair should be reviewed as a delta plus relevant regression checks. Full historical review is repeated only when scope or architecture actually changed.

---

## 10. AI / Agent resource allocation

The project chooses model, reasoning level, and harness based on **risk and task type**, not habit.

### Highest reasoning

Use for:

- architecture resets;
- durable authority and restart semantics;
- credential/security/execution boundaries;
- independent blocker adjudication;
- release topology and exact-head acceptance.

### High reasoning code-capable Writer

Use for:

- complex production implementation;
- multi-file integration;
- difficult regression repair;
- local test execution requiring repository context.

### Standard / medium reasoning

Use for:

- mechanical bounded edits;
- straightforward tests;
- low-risk documentation or refactors;
- repetitive local checks.

### Ordinary ChatGPT high reasoning

Preferred for:

- external research and architecture comparison;
- independent semantic Review;
- Review Packet adjudication;
- GitHub exact-head acceptance;
- resource-conserving Reviewer work when local execution is not required.

### TRAE / alternate Agents

Use as:

- fallback Writer;
- local mechanical execution;
- parallel work on cleanly separated components;
- quota relief.

### Quota-rich mode

Parallelize independently owned tasks where interface contracts are frozen enough to avoid conflicting work.

### Quota-conservation mode

```text
ONE STRONG WRITER
+ LOCAL MECHANICAL PACKAGING
+ ORDINARY CHATGPT INDEPENDENT REVIEW
+ EXACT-HEAD CI
```

Do not consume scarce high-end coding quota for work that a shell command, connector, or ordinary Reviewer can perform accurately.

---

## 11. Direct orchestration model

The default operating model is now:

### Product / Strategy authorities

Own product value, strategy semantics, research questions, and prioritization in their existing windows.

### Engineering Optimization / Implementation Authority

Owns:

- live-state verification;
- external technical research;
- architecture selection;
- build-vs-buy analysis;
- future-mainline reuse check;
- scope/cost convergence;
- stage decomposition;
- Writer/model assignment;
- allowlists and repair budgets;
- Review design and artifact packaging instructions;
- GitHub/CI verification;
- technical stop/replan decisions;
- coordination of authorized GitHub finalization.

### No separate Project Control by default

Do not create another ChatGPT/Agent whose main function is relaying instructions between Engineering Optimization, Writers, Reviewers, and the user.

The user must not be used as the routine message bus either.

### User authority

User retains material gates including:

- product/strategy priority changes;
- exceptional scope expansion;
- Mark Ready;
- merge;
- deployment/runtime/AWS/paid resource actions;
- credentials/account/private API;
- signing/wallet/exchange write;
- automatic trading authority.

---

## 12. Standard stage lifecycle V4

### Stage 0 — Resolve live truth

Confirm current main/head/base, open PRs, CI, accepted artifacts, active TODO, and authority boundaries.

### Stage 1 — Problem definition

Write the actual problem, user value, current gap, constraints, acceptance criteria, and non-goals.

### Stage 2 — Double-check and external research

Verify assumptions and compare mature/provider-native solutions. Search official/primary sources first for technical questions.

### Stage 3 — Architecture and reuse ruling

Select the smallest route that preserves current authority and future V0/mainline reuse.

### Stage 4 — Scope / cost convergence

Classify C0–C4, estimate implementation + review + maintenance burden, and decide PROCEED / DEFER / REPLAN.

### Stage 5 — Writer execution

One primary Writer owns a coherent stage. Parallel auxiliary work is allowed only on independent scopes.

### Stage 6 — Local evidence

Compile/tests/lint/type checks/security checks as applicable. Writer report is execution evidence only.

### Stage 7 — Independent Review

Review exact artifact/head. Use delta review when a baseline is already accepted.

### Stage 8 — Consolidated repair

One repair packet. Exceptional Repair only under Section 8.

### Stage 9 — Freeze

Freeze exact patch/diff fingerprint and changed-file scope before commit/push where practical.

### Stage 10 — GitHub candidate

Commit/push only under explicit authority. Create Draft PR, verify exact base/head, run exact-head CI.

### Stage 11 — Final independent acceptance

Verify exact remote candidate, CI, scope, and any required semantic/security acceptance.

### Stage 12 — Human finalization gates

Mark Ready and merge remain separate authorization gates unless the user explicitly grants a bounded sequence.

For stacked PRs, verify topology and merge bottom-up where required; preserve accepted heads and compare tree equivalence after merge commits.

### Stage 13 — Post-merge verification

Confirm final main tree/content equivalence and post-merge CI. Deployment is a separate authority stage.

### Stage 14 — Learn and reprioritize

Update canonical TODO/governance with real deferred work and process lessons. Do not retain stale temporary plans as active authority.

---

## 13. Decision heuristics

### Build-vs-buy heuristic

```text
IF difficult AND commodity:
    external/provider-native search first

IF difficult AND differentiating:
    custom research may be justified

IF easy BUT reopens large accepted authority:
    total cost may still be high
```

### Release reopening heuristic

```text
BLOCK CURRENT RELEASE
only if postponement creates:
- material safety failure;
- failure of current product objective;
- unrecoverable near-term data/evidence loss;
- unacceptable operational risk.

Otherwise:
DEFER TO EARLIEST COHERENT NEXT BATCH.
```

### Review escalation heuristic

```text
NARROW DELTA → NARROW REVIEW
AUTHORITY/SCHEMA/RESTART CHANGE → HIGH-REASONING REVIEW
NEW SERVICE/FRAMEWORK → REPLAN BEFORE BUILD
```

### Effort heuristic

Prefer measuring observable scope over speculative hour estimates:

- production files touched;
- new durable records/tables;
- new dependencies/services;
- authority boundaries crossed;
- restart paths changed;
- number of independent acceptance surfaces;
- expected Writer/Reviewer quota;
- operator steps added.

---

## 14. External-method alignment

V4 is consistent with established engineering practice; it is not a project-specific excuse for under-engineering.

### DORA / Google Cloud

DORA identifies working in small batches, fast feedback, work-in-process limits, continuous delivery, version control, documentation quality, and loosely coupled teams/architecture as capabilities associated with stronger software delivery performance. V4 maps these to bounded stages, limited active routes, exact-head CI, artifact review, and parallel work only across clean ownership boundaries.

References:

- https://dora.dev/capabilities/working-in-small-batches/
- https://dora.dev/capabilities/loosely-coupled-teams/
- https://dora.dev/research/
- https://dora.dev/capabilities/documentation-quality/

### AWS Well-Architected Operational Excellence

AWS recommends frequent, small, reversible changes; test and validate changes; plan for unsuccessful changes; use managed services where possible; and refine operating procedures based on experience. V4 maps this to bounded deltas, exact artifact freeze, rollback-aware releases, external/provider-native preference, and process updates after real delivery cycles.

References:

- https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_freq_sm_rev_chg.html
- https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/prepare.html

### Google SRE

Google SRE emphasizes simplicity, reducing repetitive toil, reproducible release engineering, learning from failures, and lightweight but robust launch processes. V4 maps this to avoiding unnecessary platforms, using shell/mechanical tooling for repetitive packaging, fingerprinted/reproducible release candidates, hard repair stop-losses, and codifying lessons from failed routes instead of repeating them.

References:

- https://sre.google/workbook/simplicity/
- https://sre.google/sre-book/eliminating-toil/
- https://sre.google/sre-book/release-engineering/
- https://sre.google/sre-book/postmortem-culture/
- https://sre.google/sre-book/reliable-product-launches/

---

## 15. Anti-patterns explicitly prohibited

```text
FIRST IDEA = FINAL ARCHITECTURE
```

```text
CUSTOM BUILD BEFORE CHECKING PROVIDER / MATURE EXTERNAL OPTIONS
```

```text
ONE-OFF FIRST-LAUNCH SYSTEM THAT FUTURE V0 MUST REPLACE
```

```text
PARALLEL AGENTS WRITING COMPETING DURABLE AUTHORITY
```

```text
SERIAL REPAIR AFTER REPAIR AFTER REPAIR
```

```text
REPEATED FULL REVIEW OF ALREADY ACCEPTED CODE WITHOUT A REGRESSION SIGNAL
```

```text
WEAKEN IMMUTABLE AUTHORITY TO MAKE A RETRY PASS
```

```text
SPEND HIGH-END CODING QUOTA ON MECHANICAL PACKAGING / ROUTINE REVIEW
```

```text
CREATE A PROJECT-CONTROL MESSAGE-BUS WINDOW BY DEFAULT
```

```text
BUILD A FRAMEWORK FOR A LOW-FREQUENCY EVENT THAT A COMMAND/CHECKLIST/EXTERNAL TOOL SOLVES
```

```text
KEEP RESEARCHING WITHOUT A DECISION OR STOP CONDITION
```

```text
REOPEN AN ACCEPTED RELEASE FOR LOW-VALUE SPECULATIVE FUTURE CAPABILITY
```

---

## 16. Frozen V4 rulings

```text
PRIMARY_PROCESS_GOAL = VALIDATED_DELIVERY_PER_ENGINEERING_EFFORT

EXTERNAL_MATURE_SOLUTION_CHECK = MANDATORY_FOR_NONTRIVIAL_COMMODITY_ENGINEERING
DOUBLE_CHECK_BEFORE_BUILD = MANDATORY
FUTURE_MAINLINE_REUSE_CHECK = MANDATORY
SCOPE_AND_TOTAL_COST_CONVERGENCE = MANDATORY

PROJECT_CONTROL_WINDOW_DEFAULT = RETIRED
DIRECT_ENGINEERING_ORCHESTRATION = DEFAULT

PARALLELISM = ALLOWED_ONLY_ACROSS_INDEPENDENT_OWNERSHIP
WIP = LIMIT_ACTIVE_CRITICAL_ROUTES

NORMAL_REPAIR_LIMIT = 1
EXCEPTIONAL_REPAIR_LIMIT = 1
SAME_ROOT_AFTER_EXCEPTIONAL_REPAIR = STOP_REPLAN

WRITER_REPORT = EXECUTION_EVIDENCE_ONLY
INDEPENDENT_REVIEW = REQUIRED_WHERE_STAGE_RISK_REQUIRES
ACCEPTED_BASELINE_REVIEW = DELTA_FIRST

SCARCE_CODEX_QUOTA = RESERVE_FOR_WRITING_AND_LOCAL_EXECUTION
ORDINARY_CHATGPT_HIGH_REASONING = PREFERRED_FOR_INDEPENDENT_SEMANTIC_REVIEW
MECHANICAL_PACKETIZATION = SHELL_OR_LOW_COST_TOOLING

LATE_NONBLOCKING_FEATURE = DEFER_TO_EARLIEST_COHERENT_NEXT_BATCH

MARK_READY = USER_AUTHORITY
MERGE = USER_AUTHORITY
DEPLOY_RUNTIME_CLOUD_TRADING = SEPARATE_USER_AUTHORITY
```

This workflow is intended to evolve only from observed delivery evidence. Future changes should cite the concrete bottleneck or failure mode they are solving rather than adding process for its own sake.
