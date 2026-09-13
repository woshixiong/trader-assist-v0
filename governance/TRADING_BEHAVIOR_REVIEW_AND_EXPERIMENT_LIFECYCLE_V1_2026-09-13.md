# Trader Assist / Trade OS — Trading Behavior Review and Experiment Lifecycle V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-09-13  
**Parent review method:** `governance/TRADING_BEHAVIOR_AND_EDGE_REVIEW_PROCEDURE_V1_2026-09-06.md`  
**Scope:** lifecycle separation between durable discretionary-trading review principles and short-horizon weekly/stage experiments.

This file is a narrow lifecycle companion to the parent Trading Behavior and Edge Review Procedure. It does not create project-wide governance, strategy authority, sizing authority, exchange-write authority, order-submission authority, or autonomous-trading authority.

Its purpose is to prevent weekly training goals from being promoted prematurely into permanent repository authority.

---

## 1. Two-layer operating model

Use exactly two layers for discretionary trading behavior optimization:

```text
DURABLE PRINCIPLES / CANONICAL REVIEW METHOD
-> versioned repository files
-> material changes use branch / PR / exact-head CI when applicable / independent review / merge gate

WEEKLY OR SHORT-STAGE EXPERIMENT TARGETS
-> GitHub Issue #171: Trading Behavior — Weekly Optimization Log
-> one dated comment per active week or stage
-> no new weekly governance file
-> no weekly PR by default
```

Raw trade/account data remains outside Git history.

The dated `week beginning 2026-09-07` baseline embedded in §13 of the parent procedure remains historical experiment evidence only after 2026-09-14. It must not be treated as the current active weekly target set. Current and future short-horizon targets are resolved from Issue #171.

---

## 2. Durable principles currently retained

The following are durable review / behavior-control principles. They are not claimed to be mathematically optimal trading parameters.

### 2.1 Adverse-direction adding remains prohibited

The parent procedure already freezes:

```text
ADVERSE_DIRECTION_ADD / AVERAGING_DOWN = PROHIBITED
```

This remains a durable behavior-control rule unless a future material strategy/risk decision explicitly supersedes it.

A few profitable examples do not override the tail-risk and process-control concern.

### 2.2 Preserve right-tail winners; do not optimize win rate in isolation

The parent procedure already requires protection of right-tail winners and prohibits recommending a small fixed take-profit merely to raise win rate without testing expectancy and winner concentration.

This remains durable.

The exact live exit technique remains research / experiment territory unless separately promoted.

### 2.3 Human-executability is a design constraint

For live manual/discretionary execution, an active behavior rule must be simple enough to execute repeatedly under time pressure.

```text
ACTIVE_MANUAL_RULE
=> SHORT
=> OBSERVABLE
=> REPEATABLE
=> LOW_DECISION_OVERHEAD
```

A theoretically superior rule that requires calculation or discretion the user cannot execute reliably should remain a research/reference method rather than being forced into the active manual rule set.

This principle does not claim that simpler rules have higher market expectancy by themselves. It states that compliance/executability is part of the real strategy implementation boundary.

### 2.4 Impaired-state new-entry gate

When the user self-identifies materially degraded trading state, including fatigue, concentration loss, slower reaction, or emotional impulsivity:

```text
NEW_DISCRETIONARY_ENTRY = BLOCKED
```

This is a durable behavior-control principle, not a claim that a particular clock time is universally bad.

Late-night performance may be analyzed as a risk context, but fills alone cannot prove mental state. Compliance requires user annotation or other direct evidence; otherwise report `UNKNOWN` rather than infer psychology from PnL.

### 2.5 Attempt failure does not automatically invalidate the broader thesis; blind retry is prohibited

A fast stop / scratch may end one Attempt without proving the broader directional Thesis invalid.

However:

```text
STOPPED_OUT
!=
BLIND_IMMEDIATE_RETRY_AUTHORITY
```

After returning flat, a same-thesis / same-direction re-entry requires a fresh decision and new qualifying information/trigger under the currently active experiment or Strategy authority.

This durable behavior-control rule prohibits unexamined retry/revenge behavior. It does **not** claim that any specific fresh-trigger definition is economically optimal. Exact re-entry trigger design remains Strategy research / weekly experiment territory and must stay consistent with current Strategy authority, including Issue #161.

---

## 3. Weekly / stage experiment layer

Issue #171 is the single lightweight log for short-horizon targets.

Typical weekly/stage items include:

- exact dollar-loss targets such as approximately `$0.20`;
- temporary practice-size targets;
- entry checklists such as `STATE + LEVEL + SETUP + TRIGGER + INVALIDATION + ROOM`;
- exact no-trade windows such as the first 15 minutes after Korea/US open or Tier-1 releases;
- temporary trade-frequency reduction targets;
- regime filters such as `HIGH VOL + TWO-WAY CHAOS + NO CLEAR CONSENSUS = PASS`;
- exact cooldown durations;
- exact winner-management implementation under observation.

These items may be valuable and may be explicitly user-directed, but they remain `PROVISIONAL_RULE` / `TEST_MORE` unless promoted under §4.

A weekly comment is sufficient to make them the current review target. No branch, PR, independent review, or merge is required for routine weekly updates.

---

## 4. Promotion gate: Weekly Log -> durable principle

Promote a weekly/stage item into repository authority only when it has become a durable cross-week principle rather than a tunable experiment.

Promotion should require one or more of:

- repeated support across multiple reviews and materially different regimes;
- the item is a stable evidence/accounting/process invariant rather than a numeric threshold;
- explicit user decision that the rule is intended to remain durable beyond the current stage;
- future review comparability would be damaged if different windows applied different definitions;
- the rule is required for safety/process integrity independent of one week's PnL.

Do not promote because:

- one week was profitable;
- a post-hoc loser-removal counterfactual looked attractive;
- one market/session happened to fit the rule;
- the rule is convenient to document;
- the rule is currently fashionable or intuitively appealing.

When a promotion is material, use the normal GitHub PR / independent review / merge process. Promotion of a behavioral rule never grants trading/exchange authority by itself.

---

## 5. Weekly review workflow

At each review cycle:

```text
1. READ canonical parent review procedure
2. READ this lifecycle rule
3. READ latest applicable Issue #171 weekly/stage comment
4. ANALYZE official fills/orders + approved path/context evidence
5. SCORE each active focus item: PASS / PARTIAL / FAIL / UNKNOWN
6. PRODUCE no more than 3-5 next-week priorities
7. APPEND one new dated Issue #171 comment
8. IDENTIFY promotion candidates, if any
9. OPEN a PR only for true durable-method/principle changes
```

Do not create a new repository file merely because a new week begins.

---

## 6. Current classification for week beginning 2026-09-14

### Durable / repository layer

```text
ADVERSE_DIRECTION_ADD / AVERAGING_DOWN = PROHIBITED
RIGHT_TAIL_WINNER_PRESERVATION = REQUIRED REVIEW OBJECTIVE
ACTIVE_MANUAL_RULES_MUST_BE HUMAN-EXECUTABLE
MATERIALLY_IMPAIRED_STATE -> NO NEW DISCRETIONARY ENTRY
BLIND_IMMEDIATE_RETRY_AFTER_STOP = PROHIBITED
ATTEMPT_FAILURE != AUTOMATIC_THESIS_INVALIDATION
```

### Weekly / Issue #171 layer

```text
TARGET_NORMAL_REALIZED_LOSS ~= <= $0.20
CURRENT_REDUCED_PRACTICE_SIZE
STATE + LEVEL + SETUP + TRIGGER + INVALIDATION + ROOM CHECKLIST
KOREA_OPEN_FIRST_15M = NO NEW ENTRY
US_OPEN_FIRST_15M = NO NEW ENTRY
TIER1_RELEASE_FIRST_15M = NO NEW ENTRY
REDUCE_TRADES_PER_DAY
HIGH_VOL + TWO_WAY_CHAOS + NO_CLEAR_CONSENSUS = PASS
CURRENT_WINNER_HOLD / EXIT IMPLEMENTATION = TEST_MORE
```

The split above is a lifecycle classification, not evidence that every durable behavior-control rule has positive standalone alpha or that every weekly target will later be promoted.

---

## 7. Privacy and authority boundary

Do not store in this lifecycle file or Weekly Log:

- raw fills / order-history dumps;
- public account/wallet identifiers tied to the user's trading history;
- private keys, API credentials, signing material;
- exact private account equity/position data;
- screenshots containing private account information unless sanitized and explicitly authorized.

Weekly comments should contain only sanitized targets, review status, and aggregate/non-sensitive conclusions needed for continuity.
