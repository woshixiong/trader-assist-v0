# First Launch External Contract and Predeployment Validation Standard V1

**Status:** FROZEN  
**Effective date:** 2026-07-29  
**Project:** `TRADER_ASSIST_V0_FIRST_LAUNCH_R3`  
**Repository:** `woshixiong/trader-assist-v0`  
**Applies to:** external APIs, protocol fields, timestamps, canonical payloads and hashes, persistence authority, deployment/runtime integration, notifications, credentials, cloud services and exchange-facing read paths

## 1. Governing decision

The PR #55 Hyperliquid candle incident exposed a process defect rather than a complex product defect:

- production code and test fixtures shared the same incorrect external-contract assumption;
- real public API behavior was not fixed as canonical evidence before implementation;
- a lower-layer contract change was not accompanied by a repository-wide semantic impact map;
- focused tests passed before the complete downstream strategy, TradePlan, demo and persistence chain was exercised;
- the supported-host deployment became the first meaningful end-to-end integration test.

This must not recur.

Effective immediately, a change that touches an external contract or a foundational internal contract is incomplete until it passes all gates in this standard. Focused tests, green code review, exact-head CI or deployment evidence cannot individually substitute for the complete sequence.

```text
REAL CONTRACT EVIDENCE
→ CANONICAL FIXTURE
→ REPOSITORY-WIDE SEMANTIC IMPACT MAP
→ ONE COHERENT IMPLEMENTATION
→ AFFECTED TESTS
→ FULL LOCAL GATES
→ EXACT-HEAD CI
→ NO-WRITE PREDEPLOYMENT REHEARSAL
→ SEPARATE ACTIVATION AUTHORITY
```

## 2. Incident record: Hyperliquid candle contract

### 2.1 Observed external contract

The public `candleSnapshot` request requires bounded `startTime` and `endTime` values.

Hyperliquid candle close timestamps use an inclusive boundary:

```text
5m:  T - t = 299999
15m: T - t = 899999
```

The next candle still opens at the full interval boundary:

```text
next_open - current_open = interval_ms
```

The old repository assumption treated the next candle open boundary as the previous candle close:

```text
5m:  T - t = 300000
15m: T - t = 900000
```

### 2.2 Why tests initially passed

The same incorrect formula was duplicated in production validation, demo helpers and test helpers. The fixtures and validators therefore agreed with one another while disagreeing with the exchange.

This is classified as:

```text
SELF-CONSISTENT TEST FIXTURE ERROR
+
MISSING REAL-CONTRACT EVIDENCE
+
INCOMPLETE CONTRACT IMPACT AUDIT
```

### 2.3 Why deployment found it

The supported-host run was the first point where the exact release interacted with the live public API through the real HTTP/runtime chain. The runtime failed closed, exhausted bounded reconnect attempts and stopped before exchange-write authority existed.

Incident severity:

```text
FIRST_LAUNCH_AVAILABILITY: BLOCKING
DATA_CONTRACT: MATERIAL
ACCOUNT_OR_FUND_LOSS: NONE OBSERVED
EXCHANGE_WRITE_AUTHORITY: ABSENT
SECURITY_BREACH: NONE OBSERVED
FAIL_CLOSED_BEHAVIOR: EFFECTIVE
```

The safety boundary worked, but the validation sequence was too late.

## 3. Scope of this standard

This standard is mandatory when a change affects any of the following:

- third-party HTTP, WebSocket, webhook or cloud API requests and responses;
- timestamps, intervals, inclusive/exclusive boundaries, time zones, clocks or freshness;
- normalized market-data objects;
- canonical JSON, hashes, identifiers, signatures or idempotency keys;
- strategy inputs, snapshots, TradePlan or operator-review authority;
- serialized evidence, journals, bundles, SQLite persistence or replay readers;
- credentials, systemd, filesystem permissions or host-specific runtime behavior;
- notification delivery contracts;
- any type, field or invariant reused across three or more modules or test suites.

A task owner may not classify such a change as a narrow local fix merely because the source diff is small.

## 4. Mandatory Gate A — real external-contract evidence

Before implementing or repairing an external integration, obtain one bounded, read-only, credential-free probe whenever the external system supports it.

The evidence must record:

- exact endpoint and operation;
- request method and public request shape;
- required fields;
- timestamp unit and boundary semantics;
- HTTP status or WebSocket message type;
- sanitized response shape;
- empty-result behavior;
- public error behavior;
- observation date;
- whether documentation and observed behavior agree.

Do not store secrets, private account data or unrestricted raw production data.

Where a live probe is impossible, use official provider documentation plus an independently obtained real response sample. Synthetic examples alone are insufficient.

## 5. Mandatory Gate B — canonical fixture authority

Every external contract must have one canonical fixture source derived from real, sanitized evidence.

Rules:

1. Parser and normalization tests consume the canonical fixture or a generator whose semantics are explicitly derived from it.
2. Strategy, demo, persistence and outcome tests must reuse the same approved helper or fixture semantics.
3. Test helpers may vary prices, quantities and timing positions, but may not redefine protocol fields or boundaries.
4. A fixture must identify whether a timestamp represents:
   - candle open;
   - inclusive candle close;
   - next-candle open;
   - evidence receipt;
   - evaluation cutoff;
   - expiry.
5. Old incompatible fixtures must be rejected, not silently accepted alongside the new contract.

A production validator and a test generator must never be treated as independent evidence when they were written from the same assumption.

## 6. Mandatory Gate C — repository-wide semantic impact map

Before changing a foundational contract, perform a read-only repository-wide audit.

Search for:

- field names;
- constants and literal values;
- arithmetic expressions;
- parser and normalizer code;
- strategy and risk consumers;
- snapshot and TradePlan invariants;
- canonical payloads and hash inputs;
- demo and CLI helpers;
- persistence writers and readers;
- replay and outcome validation;
- tests and fixture generators;
- documentation and runbooks.

Classify every match as:

```text
MUST_CHANGE
MUST_REMAIN
TEST_FIXTURE
HISTORICAL_COMPATIBILITY
UNRELATED
```

For timestamp work, explicitly separate:

```text
single-candle inclusive close: open + width - 1
adjacent candle cadence:       next_open = open + width
expiry or validity window:     domain-specific full duration
```

The impact map must be completed before the first remote repair commit. It may not be reconstructed one failing test at a time.

## 7. Mandatory Gate D — one coherent implementation

After the impact map is fixed:

- authorize one exact source/test allowlist;
- implement the complete contract synchronization in one working tree;
- do not use the user as a repeated patch-script runner;
- do not create V13/V14-style speculative scripts for successive failures;
- do not amend, rebase or force-push unless separately authorized;
- do not weaken validators by accepting both incompatible contracts;
- preserve historical versions only through explicit versioned compatibility paths.

A large test-failure count after a foundational change must first be treated as possible fan-out from a shared helper or invariant, not as hundreds of independent defects.

## 8. Mandatory Gate E — local validation before remote movement

Before commit or push, run:

1. parser/contract tests;
2. every directly affected functional test module;
3. downstream strategy, operator-review, persistence and outcome tests where the changed object flows into them;
4. full repository pytest;
5. full Ruff;
6. authoritative mypy;
7. compileall;
8. `git diff --check`;
9. changed-file scope verification;
10. secret and credential scan where relevant.

Focused tests are an early feedback tool, not a completion gate.

A remote branch must not be moved merely to discover the next downstream failure in GitHub CI when the full suite can run in the supported development environment.

When a local platform cannot run an authoritative gate, the task packet must identify the supported environment and run the gate there before implementation is declared complete.

## 9. Mandatory Gate F — exact-head CI and independent review

After local gates pass:

- create one normal cohesive commit within the approved budget;
- push by normal fast-forward;
- verify CI against the exact new head SHA;
- require completed/success;
- perform one independent base-to-head semantic review;
- review the complete impact map, not only changed lines;
- record any intentionally deferred hardening item.

CI from an earlier SHA is invalid evidence.

Green CI is not permission to Mark Ready, merge, deploy or activate.

## 10. Mandatory Gate G — no-write predeployment rehearsal

Before accepted real operation, run a rehearsal on the supported host using the exact release candidate.

The rehearsal must use the lowest practical authority:

- public/read-only data only;
- no account or exchange-write authority;
- no signing or nonce authority;
- no order or cancellation authority;
- no automatic activation beyond the approved rehearsal step;
- credentials absent unless the exact read path requires a separately approved non-trading credential;
- notification smoke separately controlled.

The rehearsal must prove, as applicable:

- systemd and filesystem compatibility;
- exact release SHA;
- external HTTP snapshot recovery;
- parser acceptance of real responses;
- WebSocket connection and subscription;
- warmup and READY transition;
- SQLite creation and readback;
- status publication;
- bounded restart/reconnect behavior;
- fail-closed behavior for malformed or unavailable external data.

This rehearsal occurs before final activation authority, not during the first production activation.

## 11. Stop and escalation rules

### 11.1 Fan-out rule

When a small foundational change produces many failures:

```text
STOP SERIAL PATCHING
→ IDENTIFY SHARED CONSTRUCTOR OR INVARIANT
→ RUN FULL SEMANTIC AUDIT
→ FIX ONE COHERENT SCOPE
```

### 11.2 Repair budget

Follow the project-wide repair budget:

- one normal consolidated repair;
- at most one separately authorized exceptional repair;
- after that, reduce scope or choose a clean replacement route.

### 11.3 Scope expansion

If implementation requires a file outside the fixed allowlist:

- do not modify it automatically;
- report the exact semantic dependency;
- update the impact map;
- obtain a new engineering scope ruling.

### 11.4 Deployment failure

A supported-host failure is not permission to patch the server manually or create an unreviewed local script.

Required response:

1. preserve logs and exact identity;
2. return the service to a safe inactive state;
3. classify environment failure versus code/contract failure;
4. reproduce through a bounded read-only probe or supported test;
5. repair through the repository and exact-head process.

## 12. Definition of complete for external-contract changes

An external-contract task is complete only when all applicable fields are true:

```text
REAL_CONTRACT_EVIDENCE=PASS
CANONICAL_FIXTURE=PASS
SEMANTIC_IMPACT_MAP=PASS
ONE_SHOT_IMPLEMENTATION=PASS
AFFECTED_TESTS=PASS
FULL_LOCAL_TESTS=PASS
STATIC_GATES=PASS
EXACT_HEAD_CI=PASS
INDEPENDENT_REVIEW=PASS
NO_WRITE_PREDEPLOYMENT_REHEARSAL=PASS
AUTHORITY_BOUNDARIES_PRESERVED=PASS
```

Any omitted gate must have a written, explicit and time-bounded exception. Silence is not an exception.

## 13. Required evidence packet

Every qualifying PR or release candidate must report:

```text
EXTERNAL_CONTRACT:
provider
endpoint / operation
observed date
request shape
response shape
boundary semantics
source evidence

IMPACT_MAP:
must change
must remain
fixtures
historical compatibility
unrelated matches

IDENTITY:
base
branch
head
commits
changed files

VALIDATION:
affected tests
full pytest
Ruff
mypy
compileall
diff check
secret scan

CI:
workflow
run ID
head SHA
conclusion

PREDEPLOYMENT:
host
exact SHA
authority level
HTTP snapshot
parser
WebSocket
READY
persistence
restart
safe-stop

AUTHORITY:
MARK_READY
MERGE
DEPLOYMENT
ACTIVATION
ACCOUNT_ACCESS
EXCHANGE_WRITE
```

## 14. Ownership

### Engineering Optimization

Owns the semantic impact map, minimum complete scope, compatibility decision, test plan and repair route.

### Project Control

Verifies exact mutable state, enforces the gates in order, prevents scope drift and stops at authority boundaries.

### Writer

Implements only the approved coherent scope and runs local gates before remote movement.

### Independent Reviewer

Checks real-contract evidence, false-positive guards, downstream hash/persistence effects and exact-head evidence.

### User

Retains explicit authority for Mark Ready, merge, deployment, activation, credentials, paid/cloud resources, account access and exchange-write capability.

## 15. Fixed lessons from PR #55

The following lessons are permanent:

1. Provider documentation is not enough when a safe public probe is available.
2. Synthetic fixtures do not prove an external contract.
3. A test helper can encode the same defect as production code.
4. One-millisecond errors can invalidate parser, strategy, hashes and persistence simultaneously.
5. A large failure count can be one shared-contract fan-out.
6. Focused tests must not replace the full suite for foundational changes.
7. GitHub CI must not be the first full downstream test.
8. Deployment must not be the first real end-to-end integration test.
9. Fail-closed behavior limits harm but does not excuse late validation.
10. After repeated failures, stop scripting and perform a complete semantic audit.

## 16. Frozen ruling

```text
EXTERNAL_CONTRACT_EVIDENCE:
MANDATORY

CANONICAL_REALISTIC_FIXTURE:
MANDATORY

REPOSITORY_WIDE_SEMANTIC_IMPACT_MAP:
MANDATORY_FOR_FOUNDATIONAL_CONTRACT_CHANGES

FULL_LOCAL_SUITE_BEFORE_REMOTE_MOVEMENT:
MANDATORY

EXACT_HEAD_CI_AND_INDEPENDENT_REVIEW:
MANDATORY

NO_WRITE_PREDEPLOYMENT_REHEARSAL:
MANDATORY_BEFORE_ACCEPTED_REAL_OPERATION

SERIAL_SPECULATIVE_PATCH_SCRIPTS:
PROHIBITED

DEPLOYMENT_AS_FIRST_INTEGRATION_TEST:
PROHIBITED

AUTHORITY_BOUNDARIES:
UNCHANGED
```

This standard remains authoritative until superseded by a later merged governance document that explicitly names and replaces it.
