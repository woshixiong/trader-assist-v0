# Trade OS Strategy Research / Validation Index

Status: PUBLICATION-CLEAN CANDIDATE / NON-EXECUTABLE
Date: 2026-09-16
Canonical domain authorities: GitHub Issues #161, #150, #85; Engineering transition/control #163; Product stage placement #174.
Source accepted artifact: PR #168 exact HEAD `5fb311de457aa8a449c7c6fa2028630c2f4a36be`.

This directory publishes the accepted ordinary/VNext Strategy, causal data, validation and engineering-handoff contracts on current `main` without changing Strategy economics.

It grants no production Strategy change, Mark Ready, merge, deployment, credential/private API, signing, exchange write, order submission, Testnet/Mainnet, real-capital or autonomous-trading authority.

## Required read order

Read the accepted September 11 files as one layered contract:

1. base Strategy/Data/Validation files;
2. `TA_VNEXT_PRE_E4_REPAIR1_CONTRACT_ADDENDUM_2026-09-11.md` — overrides only the conflicting Repair-1 clauses;
3. `TA_VNEXT_POST_ACCEPTANCE_CONSOLIDATION_ADDENDUM_2026-09-16.md` — latest publication/status, bounded execution-realism, independent-validation and stage-placement precedence.

Historical `PENDING_DELTA_REVIEW`, `E4_HARD_HOLD`, and Engineering19 stage-status text inside the byte-preserved September 11 files is publication history. The September 16 addendum supplies the current status/pointer layer; it does not rewrite the accepted economic semantics.

## Published files

- `TA_VNEXT_E4_C1_STRATEGY_SPEC_2026-09-11.md` — accepted bounded ordinary/VNext Strategy candidate.
- `TA_VNEXT_VALIDATION_BACKTEST_SHADOW_AND_PROMOTION_STANDARD_V1_2026-09-11.md` — accepted common validation standard.
- `TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11.md` — accepted causal evidence/data contract.
- `TA_VNEXT_OPEN_QUESTIONS_AND_HYPOTHESIS_LEDGER_V1_2026-09-11.md` — unresolved hypotheses and research-investment dispositions.
- `TA_VNEXT_ENGINEERING19_PRE_E4_HANDOFF_2026-09-11.md` — accepted Strategy-to-Engineering requirements snapshot.
- `TA_VNEXT_PRE_E4_REPAIR1_CONTRACT_ADDENDUM_2026-09-11.md` — Repair-1 precedence for BBO validity, pre-decision capture, order-active fill semantics, U21/U23/U25 dispositions, timestamp terminology and multi-Challenger Forward selection.
- `TA_VNEXT_POST_ACCEPTANCE_CONSOLIDATION_ADDENDUM_2026-09-16.md` — current publication/status and later bounded-delta precedence.
- `../../archive/strategy/STRATEGY_RESEARCH_DECISION_ARCHIVE_THROUGH_2026-09-11.md` — historical/superseded decision rationale.

## Current accepted identity

```text
STRATEGY_VERSION=TA_VNEXT_E4_C1_2026-09-11
POLICY_VERSION=TA_FRICTION_POSITION_POLICY_V0_1
PARAMETER_VERSION=TA_PRE_E4_GRID_V0_1
DERIVATION_VERSION=TA_MICROSTRUCTURE_DERIV_V0_1
CURRENT_THREE_SETUP_AUTHORITY=UNCHANGED
THIRD_PARTY_PRE_E4_DELTA_REVIEW=PASS
STRATEGY_DATA_VALIDATION_CLOSED_LOOP_ACCEPTED=YES
COMMON_NAUTILUS_E4_FOUNDATION=MERGED
LIVE_STRATEGY_CHANGE=NO
EXCHANGE_WRITE=NO
```

No later accepted authority has changed those four VNext version identities. Any future material Strategy/Policy/Parameter/Derivation change creates a new immutable version and follows the normal OOS/Forward reset rules.

## Workstream separation

```text
STRATEGY_WORKSTREAM
= economic hypotheses + Strategy/Policy/Parameter/Derivation semantics + preregistration

ENGINEERING_WORKSTREAM
= causal evidence/replay/Shadow/report implementation + technical correctness

INDEPENDENT_VALIDATION_WORKSTREAM
= formal G2/G3/G4/G5 evidence execution/adjudication + claim-scope control
```

Strategy and Engineering do not self-authorize formal edge/promotion claims.

## Current program relationship

This directory is the ordinary Three-Setup/VNext lane. It does not absorb or redefine:

- Explosive Strategy / `HL_EXPLOSIVE_SHADOW_C1` / X1-X3 authority;
- `SESSION_OPEN_IMPULSE V0.1` research Challenger authority;
- Nautilus rc4/rc5 infrastructure-version decisions;
- Product E6 Human-approval UI/runtime.

Those lanes may share accepted infrastructure and validation machinery but retain their own Strategy identities and evidence clocks.

## Version and evidence rules

Never silently mutate an observed candidate in place.

- core Thesis/Activation/lifecycle semantics change -> new `strategy_version`;
- participation/re-entry/winner/exit policy semantics change -> new `policy_version`;
- thresholds/windows/grids change with semantics unchanged -> new `parameter_version`;
- feature/raw-input/timestamp/gap/normalization definition changes -> new `derivation_version`.

A confirmatory E5 Forward clock begins only after the exact immutable candidate and applicable PRE-E5 method controls are frozen. A newer version never inherits an older version's Forward duration.

Repository files define schemas, contracts, formulas and research manifests only. Raw private/account trading data, credentials, wallets, production DB/logs and real account identifiers never enter Git history.