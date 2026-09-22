# FDML Phase 1 Real Data Collection Experiment Protocol

## Purpose

Establish the first real-data research loop:

Observed State -> Decision Snapshot -> Future Outcome -> Evaluation Result

This phase is research-only. It does not implement trading strategy, execution, profit optimization, or automated decision systems.

---

# 1. Experiment Definition

## State Sampling Frequency

Primary sampling interval:

- 5 seconds

Event-based snapshots:

- Immediate capture when decision or evidence state changes.

Each sample records:

- timestamp
- market identity
- state identity
- evidence reference
- freshness
- schema version

## Observation Window

Window:

- 60 minutes before decision timestamp

Purpose:

- preserve observable context before decision generation;
- support reproducible evaluation.

## Decision Timestamp

Decision timestamp (T0) is the exact time when Decision Record is generated.

At T0 freeze:

- state snapshot
- evidence snapshot
- model identity
- confidence

Frozen records cannot be modified after creation.

## Outcome Window

Initial evaluation windows:

- 5 minutes
- 15 minutes
- 60 minutes

Outcome records contain:

- experiment_id
- decision_timestamp
- evaluation_timestamp
- reference state
- future state
- observed change

---

# 2. Data Quality Rules

## Missing Data

Invalid conditions:

- required field missing;
- timestamp missing;
- evidence reference missing;
- interrupted sampling sequence.

Status:

- MISSING_DATA

## Stale State

State is stale when:

state_age > sampling_interval x 3

Status:

- STALE_STATE

## Invalid Evidence

Invalid evidence conditions:

- missing evidence identity;
- inconsistent state hash for same timestamp;
- unsupported schema version.

Status:

- INVALID_EVIDENCE

## Data Quality Status

Allowed states:

- VALID
- DEGRADED
- INVALID

---

# 3. Evaluation Metrics

Phase 1 metrics only:

## Directional Accuracy

Measure whether predicted direction matches observed future direction.

Output:

- directional_accuracy

No profit or trading performance measurement is included.

## Confidence Calibration

Compare recorded confidence against actual correctness.

Output:

- calibration_error

Purpose:

- detect over-confidence;
- detect under-confidence.

## Failure Rate

Failure includes:

- invalid data;
- invalid evidence;
- missing outcome;
- evaluation failure.

Output:

- failure_rate

---

# Phase 1 Constraints

Allowed:

- state collection;
- evidence recording;
- decision recording;
- outcome observation;
- deterministic evaluation.

Forbidden:

- trading execution;
- strategy engine;
- order system;
- model training;
- profit optimization.

---

# Success Criteria

- reproducible experiment records;
- stable evaluation outputs;
- deterministic evaluation for identical experiment inputs.
