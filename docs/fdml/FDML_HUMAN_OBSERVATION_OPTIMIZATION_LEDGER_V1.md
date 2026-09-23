# FDML Human Observation / Optimization Ledger V1

## Status

```text
PROJECT=FAST_DECISION_MODEL_LAB
LEDGER_TYPE=HUMAN_QUALITATIVE_OBSERVATION_AND_OPTIMIZATION
STATUS=ACTIVE_AFTER_MERGE
QUANTITATIVE_SHADOW_LABEL_AUTHORITY=NO
SOURCE_REQUIREMENT=Issue #216 comment 5757114450
CREATED=2026-09-23
```

## Purpose

This is the dedicated durable ledger for human observations made while monitoring FDML live decisions and using them as discretionary trading references.

It is deliberately separate from FDML quantitative Shadow evidence.

Human observations may identify usefulness, failure modes, bugs, timing problems, data problems, or future improvements. They must never overwrite, relabel, or retroactively alter the model's quantitative Shadow outcomes.

## Fixed workflow

```text
USER OBSERVES FDML LIVE DECISION
-> USER SENDS OBSERVATION / REAL-TRADE FEEDBACK IN CHAT
-> ASSISTANT RECORDS MATERIAL OBSERVATION HERE
-> CLASSIFY
-> ACTIONABLE ITEM BECOMES TODO
-> REPEATED ITEMS MAY BE CONSOLIDATED
-> RESOLUTION IS APPENDED
-> STATUS BECOMES RESOLVED OR REJECTED
```

Do not silently delete historical entries. If an entry needs correction, append a correction/supersession note referencing the original entry ID.

## Categories

Use one or more:

- `SIGNAL_QUALITY`
- `TIMELINESS`
- `DATA_QUALITY`
- `HORIZON_ERROR`
- `HUMAN_USEFULNESS`
- `UI_OPERABILITY`
- `COST`
- `BUG`
- `FEATURE_IDEA`

## Status values

- `OBSERVATION` — recorded evidence, no development action yet.
- `TODO` — actionable item accepted for investigation or implementation.
- `RESOLVED` — addressed; resolution evidence is recorded.
- `REJECTED` — reviewed and deliberately not pursued, with reason.

## Priority

- `P0` — invalidates safety/data integrity or makes live output unusable.
- `P1` — material signal/timing/operability problem affecting usefulness.
- `P2` — meaningful improvement, not immediately blocking.
- `P3` — low-priority idea or convenience.

## Required record template

Append new entries under **Observation Records** using this format:

```markdown
### FDML-HO-YYYYMMDD-NNN

- Timestamp:
- Market:
- Related decision_event_id / signal_id:
- Model / arm:
- Category:
- Priority:
- Status:
- What FDML showed:
- Data/signal age and validity, if known:
- Shadow entry/reference price, if known:
- What the user observed:
- What the user did, if any:
- What happened afterward:
- Why this matters:
- Evidence / screenshots / GitHub locators:
- Action / TODO:
- Resolution / follow-up:
```

Unknown fields may be recorded as `UNKNOWN`; do not invent values.

## Quantitative / qualitative separation

The following are authoritative quantitative evidence only when produced by the FDML Shadow/evidence pipeline:

- decision probabilities and typed outputs;
- market state and freshness;
- shadow execution references;
- forward path / outcomes;
- deterministic evaluations;
- calibration / MFE / MAE / first-passage metrics.

This ledger is a separate practical-use layer. Human discretionary PnL, whether positive or negative, does not replace model Shadow outcome labels.

## Triage rules

1. Record material observations even when no immediate fix is proposed.
2. Do not convert every observation into development work.
3. Group repeated manifestations under one TODO when they share a root cause.
4. Keep exact signal/event IDs whenever available so human observations can be joined to quantitative evidence.
5. A material proposed strategy/model change must go through the normal FDML research/governance path; this ledger does not itself authorize implementation.
6. Production/runtime/exchange actions remain separately authorized.

# Observation Records

_No live-use observations recorded yet._
