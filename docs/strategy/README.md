# Trade OS Strategy Research / Validation Index

Status: DRAFT CANDIDATE FILESET / NON-EXECUTABLE
Date: 2026-09-11
Canonical discussion authority: GitHub Issues #161, #150, #85 and transition authority #163.

This directory turns the current Strategy research into a versioned, reviewable closed loop:

`Strategy specification -> causal data contract -> deterministic replay/backtest -> E4 live Shadow -> E5 fresh Forward evidence -> promotion gate -> separately authorized execution -> actual-vs-shadow calibration -> next immutable Strategy version`.

It grants no production Strategy change, Mark Ready, merge, deployment, credential/private API, signing, exchange write, order submission or autonomous trading authority.

## Active candidate files

- `TA_VNEXT_E4_C1_STRATEGY_SPEC_2026-09-11.md` — bounded Strategy/Policy/Parameter/Derivation candidate frozen for first causal Shadow comparison.
- `TA_VNEXT_VALIDATION_BACKTEST_SHADOW_AND_PROMOTION_STANDARD_V1_2026-09-11.md` — common validation standard from replay/backtest through Forward Shadow and later real-capital promotion.
- `TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11.md` — causal market/decision/order/outcome evidence required to make the Strategy testable and improvable.
- `TA_VNEXT_OPEN_QUESTIONS_AND_HYPOTHESIS_LEDGER_V1_2026-09-11.md` — every unresolved material Strategy question, its evidence need, test method and research-investment disposition.
- `TA_VNEXT_ENGINEERING19_PRE_E4_HANDOFF_2026-09-11.md` — self-contained Strategy -> Engineering requirements, including the prior Q1-Q16 answers plus the new validation/data loop.
- `TA_VNEXT_PRE_E4_REPAIR1_CONTRACT_ADDENDUM_2026-09-11.md` — mandatory bounded repair after independent third-party review. **Read this file before using the four files above; it overrides only their conflicting clauses on BBO validity, pre-decision capture, order-active fill semantics, U21/U23/U25 dispositions, timestamp terminology and E5 multi-Challenger selection.**

Current handoff status after Repair 1:

```text
STRATEGY_PRE_E4_HANDOFF=REPAIR_APPLIED_PENDING_DELTA_REVIEW
ENGINEERING19_HANDOFF_ALLOWED=NO_PENDING_DELTA_REVIEW
E4_HARD_HOLD=ACTIVE
```

Historical/superseded Strategy decisions are indexed under:

- `archive/strategy/STRATEGY_RESEARCH_DECISION_ARCHIVE_THROUGH_2026-09-11.md`

## Version rule

Never silently mutate an observed candidate in place.

- core Thesis/Activation/lifecycle semantics change -> new `strategy_version`;
- participation/re-entry/winner/exit policy semantics change -> new `policy_version`;
- thresholds/windows/grids change with semantics unchanged -> new `parameter_version`;
- feature/raw-input/timestamp/gap/normalization definition changes -> new `derivation_version`.

Forward evidence starts when the exact immutable version becomes active. A newer version never inherits an older version's Forward duration.

## Evidence authority rule

Repository files define schemas, contracts, formulas and research manifests only. Raw private/account trading data, credentials, wallets, production DBs/logs and real account identifiers never enter Git. Actual fills, when separately authorized, must be retained in an approved private evidence store and linked only through non-secret research identities/hashes.
