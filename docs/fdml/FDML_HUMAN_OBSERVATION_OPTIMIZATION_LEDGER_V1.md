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


### FDML-HO-20260923-001

- Timestamp: 2026-09-23
- Market: N/A — pre-live architecture / model-strategy research
- Related decision_event_id / signal_id: NONE
- Model / arm: Jev incumbent; Laya and future open System-1 / fast-decision challengers
- Category: FEATURE_IDEA, COST, SIGNAL_QUALITY, HUMAN_USEFULNESS
- Priority: P2
- Status: TODO
- What FDML showed: The current FDML core already exposes project-owned provider-neutral `DecisionModelAdapter`, `DecisionRequest`, `DecisionResult`, `ModelTarget` / `ModelIdentity`, and same-snapshot fan-out. This means a future local/open model can be added as another adapter without redesigning state, evidence, outcome, or cross-model comparison semantics.
- Data/signal age and validity, if known: N/A
- Shadow entry/reference price, if known: N/A
- What the user observed: Long-term preference is to converge toward a stable open model that can be fine-tuned on FDML's own trading-decision data, maintained by the project, and self-hosted on AWS. The first live version remains Jev; later phases may add multiple models in parallel or replace Jev if project-domain forward evidence supports it.
- What the user did, if any: Requested independent external research and durable recording as a basis for future FDML iteration. Explicitly declined high-frequency automatic model monitoring; use periodic stage-based screening instead.
- What happened afterward: External evidence supports the direction as technically and economically plausible, but does not justify locking Laya itself as the permanent long-term model today.
- Why this matters: A project-owned specialised open model could reduce long-run API/vendor dependence, make exact checkpoint identity and reproducibility easier, allow direct domain fine-tuning/calibration, and keep marginal inference cost low. The main risk is not compute; it is training-label quality, temporal leakage/overfit, probability calibration, model/project maturity, and operational maintenance.

#### Research synthesis

1. **Laya is a credible current challenger, not yet the permanent base-model choice.**
   - Upstream Laya is Apache-2.0, open-weight, local/self-hostable, and currently provides 421M English / typed-decision checkpoints and a 322M multilingual checkpoint.
   - Its own documentation explicitly positions fine-tuning as the main value path: the base model is materially weaker zero-shot on the typed-decisions benchmark, while the task-specialised checkpoint improves sharply.
   - Official Laya documentation includes a domain fine-tuning notebook; the published example reports roughly 4–5 hours on 2x T4 for about 30k questions. This supports the feasibility of periodic project-specific training rather than continuous expensive training.
   - Community and independent results remain mixed: Laya is consistently attractive on local latency/openness, while Jev often remains stronger zero-shot and better calibrated out of the box on harder/general tasks. Therefore Laya should be treated as a challenger until same-snapshot FDML evidence proves otherwise.

2. **The user's proposed long-term route is reasonable.**
   - Keep a strong external incumbent while FDML accumulates causal forward evidence.
   - Periodically screen open fast-decision models.
   - Select a stable open base only after it passes license/maturity/training/inference/context-fit/calibration gates.
   - Fine-tune or otherwise adapt that base on project-domain data.
   - Validate on chronologically later / genuinely unseen data.
   - Run it as a champion/challenger against Jev before any primary-provider switch.
   - After acceptance, self-host inference and maintain exact model/checkpoint/calibration identity.

3. **FDML's current architecture is already capable of supporting this direction.**
   - Provider-neutral model contracts and adapter isolation already exist.
   - Same-snapshot multi-model fan-out already exists.
   - Model/checkpoint/runtime/calibration identity fields already exist.
   - Evidence/outcome/export layers can support prospective head-to-head evaluation.
   - Therefore future open-model adoption should normally be `new adapter + model runtime/dependency + focused tests + qualification`, not a core-system rewrite.

4. **What FDML does not yet have — intentionally.**
   - No training/MLOps pipeline is currently implemented.
   - The Phase-1 real-data protocol explicitly forbids model training.
   - Existing FDML evidence is not yet sufficient to claim that a project-specific model can be trained well; live forward data quantity, regime diversity, and label quality must first be measured.
   - Current AWS host hardware suitability for local inference/fine-tuning has not yet been benchmarked and must not be assumed.

5. **Recommended training/deployment topology.**
   - Do not make the always-on trading host perform heavy training.
   - Use temporary GPU capacity for training/fine-tuning (for example AWS EC2/SageMaker Spot or another accepted ephemeral GPU route), persist exact artifacts/checkpoints, then deploy inference separately.
   - First benchmark CPU inference on the target AWS host because FDML's decision cadence is much slower than sub-second HFT; move to a small GPU inference instance only if latency/throughput/RAM measurements require it.
   - AWS supports GPU EC2 instances and managed Spot training; SageMaker documents Spot-training cost reductions of up to 90% versus on-demand, subject to interruption/checkpointing constraints.

6. **Fine-tuning method should remain model-specific, not prematurely frozen.**
   - Parameter-efficient methods such as LoRA/PEFT are mature ways to reduce trainable parameters and memory, and can support multiple lightweight task adapters.
   - However Laya currently exposes its own RLCD/domain fine-tuning path. If Laya or another System-1 model is selected, use the best validated model-native training route rather than forcing LoRA merely because it is popular.
   - The training method is subordinate to project-domain forward performance and calibration.

#### Critical safeguards for future project-specific model training

- Do **not** train only on Jev outputs and then describe the result as independently learned trading intelligence. That would primarily be Jev distillation. If teacher labels are used, record them explicitly as such.
- Prefer labels/rewards derived from causal later market outcomes plus deliberately defined human/domain annotations where needed.
- Freeze dataset/schema/question/label/reward versions before each training epoch.
- Use chronological train/validation/test splits; retain a genuinely later forward set. Randomly mixing nearby market events across train/test risks leakage.
- Fit probability calibration on data disjoint from model training; evaluate reliability/calibration in addition to simple accuracy.
- Preserve complete model lineage: base-model revision, license, weight digest, training code/config, dataset version/hash, seed, calibration config, evaluation manifest and deployment artifact digest.
- Keep Jev or another accepted external model available during transition until the self-hosted challenger proves reliability and usefulness prospectively.
- Do not auto-promote a model based on one backtest or one in-sample improvement.

#### Periodic future screening criteria

For Laya, Von, SemIf, djev, Reflex, or future peers, screen at stage boundaries rather than continuously:

```text
OPEN_LICENSE / COMMERCIAL_USE
MAINTENANCE_AND_RELEASE_HEALTH
TRAINING_OR_FINE_TUNING_ROUTE
STATE/CONTEXT_FIT
TYPED_PROBABILITY_OUTPUT
CALIBRATION
LOCAL_INFERENCE_LATENCY / MEMORY
AWS_OPERATIONAL_FIT
REPRODUCIBLE_MODEL_IDENTITY
SAME-SNAPSHOT_FDML_FORWARD_EVIDENCE
TOTAL_LIFECYCLE_COST
```

#### Current disposition

```text
FIRST_LIVE_MODEL=JEV
LONG_TERM_DIRECTION=OPEN_SELF_HOSTED_DOMAIN_SPECIALISED_MODEL_IS_PREFERRED_IF_EVIDENCE_SUPPORTS
LAYA_STATUS=CREDIBLE_FIRST_OPEN_CHALLENGER; NOT YET PERMANENT_SELECTION
MULTI_MODEL_FDML_ARCHITECTURE=RETAIN
MODEL_MONITORING=PERIODIC_STAGE_SCREENING; NO HIGH_FREQUENCY_AUTOMATIC_CHECK
TRAINING_PIPELINE_NOW=NO
NEXT_TRIGGER=SUFFICIENT_LIVE_FDML_DATA + LABEL/OUTCOME QUALITY REVIEW + TARGET_HOST INFERENCE BENCHMARK
```

#### External evidence / references

- Laya upstream repository / fine-tuning documentation: https://github.com/NandhaKishorM/laya
- Laya model family / model cards: https://huggingface.co/convaiinnovations/laya
- Laya typed-decisions specialist: https://huggingface.co/convaiinnovations/laya-typed-decisions
- Hugging Face PEFT / LoRA: https://huggingface.co/docs/peft/
- AWS SageMaker Managed Spot Training: https://docs.aws.amazon.com/sagemaker/latest/dg/model-managed-spot-training.html
- AWS EC2 accelerated-computing instances: https://aws.amazon.com/ec2/instance-types/accelerated-computing/
- Scikit-learn probability calibration guidance: https://scikit-learn.org/stable/modules/calibration.html
- Scikit-learn time-sensitive cross-validation guidance: https://scikit-learn.org/stable/modules/cross_validation.html

- Evidence / screenshots / GitHub locators: Issue #216; current FDML provider-neutral contracts/fan-out on main; PR #230 (this ledger); external sources listed above.
- Action / TODO:
  1. Keep the current first-live Jev plan unchanged.
  2. Accumulate FDML real forward evidence before building a training pipeline.
  3. At a later stage, run a bounded open-model candidate screen rather than committing to Laya now.
  4. When data sufficiency is reached, define the target labels/reward and chronological validation protocol before any fine-tuning.
  5. Benchmark candidate local inference on the actual AWS target host.
  6. If the route remains favorable, create a separately governed model-training/adaptation task and champion/challenger Shadow qualification.
- Resolution / follow-up: OPEN. This record is a future-iteration basis only; it does not authorize model training, deployment, runtime/cloud mutation, provider replacement, or trading execution.
