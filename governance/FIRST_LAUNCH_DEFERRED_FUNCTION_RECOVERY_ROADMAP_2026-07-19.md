# Trader Assist V0 — First Launch Deferred-Function Recovery Roadmap

**Roadmap ID:** `TA-FIRST-LAUNCH-DEFERRED-FUNCTION-RECOVERY-ROADMAP-2026-07-19-R1`  
**Companion baseline:** `TA-FIRST-LAUNCH-SIGNAL-FIRST-BASELINE-2026-07-19-R1`  
**Effective composite baseline:** `TA-FIRST-LAUNCH-SIGNAL-FIRST-BASELINE-2026-07-19-R2`  
**Date:** 2026-07-19  
**Repository:** `woshixiong/trader-assist-v0`  
**Status:** User-approved product-roadmap addendum; documentation-only; pending independent review/merge  

---

## 1. Purpose

Deferral from the First Launch critical path does **not** mean cancellation.

This roadmap prevents functions removed from the First Launch sprint from being forgotten after launch. It binds each deferred capability to:

- a future recovery phase;
- an activation trigger or dependency;
- a current backlog/authority status;
- a mandatory review mechanism.

This document and the companion signal-first baseline together form the effective R2 product baseline.

No deferred capability may disappear merely because it is omitted from a later prompt, package, state file, PR description or status report.

---

## 2. Recovery phases

| Phase | Purpose | Activation condition |
|---|---|---|
| `FL-0` | Restricted ETH public-data signal pilot | Current First Launch acceptance gates pass |
| `POST-FL-1` | Product-value validation | 7–14 operating days or 10–20 actionable signals |
| `POST-FL-2` | Strategy breadth and operator usability | Product-value gate supports continued development and observed market gaps are identified |
| `POST-FL-3` | Reviewed order workflow | Signal lifecycle is stable and fund-protection prerequisites are implemented |
| `POST-FL-4` | Outcome closure and V0 foundation recovery | Reviewed execution exists or enough manual/pilot evidence exists to justify deeper automation |
| `POST-FL-5` | Asset, surface and operational expansion | ETH workflow is useful and operationally stable |
| `POST-FL-6` | Advanced microstructure, intelligence and automation | Multiple strategies/data sets have sufficient evidence and explicit new authority is granted where required |

These phases define default ordering, not automatic authorization. Every phase still requires a separate user product decision and Project Control activation.

---

## 3. Deferred capability ledger

| Deferred capability | Planned destination | Activation trigger or dependency | Current status |
|---|---|---|---|
| Additional market-condition strategies | `POST-FL-2` | Pilot evidence identifies missed regimes or repeated failure modes | `POST_LAUNCH_PRIORITY` |
| 1m/5m microstructure confirmation strategies | `POST-FL-2` or `POST-FL-6` | A named strategy requires it and exact data requirements are defined | `DEFERRED_PRESERVED` |
| Funding z-score and longer-history derivatives models | `POST-FL-2` / `POST-FL-4` | Sufficient historical OI/Funding observations exist and deterministic validation is possible | `DEFERRED_PRESERVED` |
| BBO, spread and basic executable-price checks | `POST-FL-3` | Mandatory before order preview or exchange submission | `SAFETY_GATED_REQUIRED` |
| Account read: balances, positions, open orders and fills | `POST-FL-3` | Mandatory conflict/risk checks before exchange submission; separate account-read authority required | `SAFETY_GATED_REQUIRED` |
| Deterministic one-click Order Preview | `POST-FL-3` | Stable signals, current-data recheck and complete TradePlan confirmation | `POST_LAUNCH_PRIORITY` |
| Testnet user-confirmed submission | `POST-FL-3` | Order Preview accepted; signing, nonce, duplicate prevention and kill-switch controls pass | `EXPLICIT_AUTHORITY_REQUIRED` |
| Mainnet very-small-risk user-confirmed submission | `POST-FL-3` | Testnet acceptance, fund-protection controls and explicit Mainnet authority | `EXPLICIT_AUTHORITY_REQUIRED` |
| Automatic protective SL/TP and cancellation handling | `POST-FL-3` | Submission workflow exists; protective-order result verification and recovery are proven | `EXPLICIT_AUTHORITY_REQUIRED` |
| Signal / user decision / order / fill closure | `POST-FL-4` | Stable identifiers and manual or assisted execution evidence exist | `DEFERRED_PRESERVED` |
| Shadow-to-real execution matching | `POST-FL-4` | Fill evidence becomes available and matching rules are deterministic | `DEFERRED_PRESERVED` |
| Real-time DecisionBundle integration | `POST-FL-4` | Live signal and execution objects are stable | `DEFERRED_PRESERVED` |
| Automatic Outcome, MFE/MAE and Pilot Review integration | `POST-FL-4` | Sufficient closed trades/signals and reliable timestamps exist | `DEFERRED_PRESERVED` |
| Full audit-grade lifecycle persistence and tamper evidence | `POST-FL-4` | Operational volume, exchange-write authority or audit needs justify stronger guarantees | `DEFERRED_PRESERVED` |
| Full historical backtest, walk-forward and parameter-grid platform | `POST-FL-4` / `POST-FL-6` | Required for promoting or comparing additional strategies; not a First Launch gate | `RESEARCH_BACKLOG` |
| Automated reports, strategy scorecards and broader analytics | `POST-FL-4` | Outcome data is sufficiently complete and reliable | `DEFERRED_PRESERVED` |
| Full operator dashboard | `POST-FL-5` | Notification/log workflow is proven and a richer surface has clear user value | `DEFERRED_PRESERVED` |
| BTC and ETHBTC support | `POST-FL-5` | ETH workflow proves useful; asset-specific data, strategy and risk scope are separately approved | `DEFERRED_PRESERVED` |
| Full L2, trades, OFI, CVD, wall persistence/refill/cancel scoring | `POST-FL-2` or `POST-FL-6` | A named strategy needs it; behavioral validation is defined; no universal platform build by default | `STRATEGY_DEPENDENT_BACKLOG` |
| Multi-strategy automatic selection and switching | `POST-FL-6` | Multiple strategies are independently validated and conflict/arbitration rules are accepted | `EXPLICIT_AUTHORITY_REQUIRED` |
| AI explanation, context, second opinion and post-trade review | `POST-FL-5` / `POST-FL-6` | Deterministic signal authority remains unchanged and provider/runtime boundaries are approved | `NON_AUTHORITATIVE_BACKLOG` |
| AI strategy research and candidate generation | `POST-FL-6` | Suggestions pass deterministic implementation, testing, shadow evaluation and Review | `NON_AUTHORITATIVE_BACKLOG` |
| Automatic optimization or direct production-rule mutation | No automatic phase | Requires a new explicit product, risk and governance authority decision | `PROHIBITED_PENDING_NEW_AUTHORITY` |
| Multi-instance HA, Kubernetes, multi-region and distributed operations | `POST-FL-5` / `POST-FL-6` | Actual availability, scale or recovery requirements justify the complexity | `OPERATIONS_BACKLOG` |

---

## 4. Mandatory backlog-control rules

1. **Canonical ledger:** Section 3 is the canonical deferred-function ledger for the effective R2 product baseline.
2. **No silent deletion:** A deferred capability cannot disappear from future planning by omission.
3. **Milestone review:** At every product-value gate, package closeout and release-boundary decision, Project Control must report:
   - items activated;
   - items still deferred;
   - items superseded;
   - items explicitly cancelled by the user;
   - items awaiting separate authority.
4. **Status accuracy:** First Launch may be reported as complete while deferred items remain, but the overall product roadmap must not be reported as complete.
5. **Preserve existing work:** Existing offline modules and evidence paths must not be deleted merely because live integration is deferred.
6. **Product ownership:** Product Function and Priority Control decides whether and when a deferred item moves into an active milestone.
7. **Engineering boundary:** Engineering Optimization may improve implementation efficiency but may not reorder, cancel or activate deferred product capabilities.
8. **Project Control boundary:** Project Control must translate an activated deferred item into a bounded task and Write Lease; it may not infer activation from this roadmap alone.
9. **Safety authority:** Account access, signing, Testnet/Mainnet write, automatic orders, automatic SL/TP, AI authority and automatic production mutation always require explicit separate authority.
10. **Roadmap continuity:** Every future control-window handoff must reference the effective composite baseline ID and include the deferred-ledger delta since the previous milestone.

---

## 5. Default post-First-Launch sequence

Unless changed by a later explicit user decision, the default sequence is:

```text
FIRST LAUNCH SIGNAL PILOT
→ PRODUCT-VALUE REVIEW
→ STRATEGY EXPANSION + ORDER PREVIEW
→ TESTNET USER-CONFIRMED EXECUTION
→ VERY-SMALL-RISK MAINNET USER-CONFIRMED EXECUTION
→ SIGNAL/DECISION/FILL + OUTCOME CLOSURE
→ V0/MAINLINE FOUNDATION RECOVERY
→ BTC / DASHBOARD / STRATEGY-SPECIFIC MICROSTRUCTURE
→ ADVANCED AI / MULTI-STRATEGY / AUTOMATION
```

Strategy expansion and Order Preview may proceed as parallel product lanes after the product-value gate. Exchange-write steps remain sequential and safety-gated.

---

## 6. Change control

A deferred item remains active in this ledger until one of the following exact dispositions is recorded:

- `IMPLEMENTED_AND_ACCEPTED`
- `EXPLICITLY_CANCELLED_BY_USER`
- `SUPERSEDED_BY_USER_APPROVED_DESIGN`
- `PROHIBITED_PENDING_NEW_AUTHORITY`

Engineering Optimization, Project Control, Writer and Reviewer windows may not infer cancellation, activation, authority expansion or priority change from this document alone.

Changes require an explicit user product decision and an updated canonical ledger.