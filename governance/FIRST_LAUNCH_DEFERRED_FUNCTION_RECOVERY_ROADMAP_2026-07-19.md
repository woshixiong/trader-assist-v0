# Trader Assist V0 — Deferred Capability Registry and Adaptive Post-Launch Planning Gate

**Registry ID:** `TA-FIRST-LAUNCH-DEFERRED-CAPABILITY-REGISTRY-2026-07-19-R2`  
**Companion baseline:** `TA-FIRST-LAUNCH-SIGNAL-FIRST-BASELINE-2026-07-19-R1`  
**Effective composite baseline:** `TA-FIRST-LAUNCH-SIGNAL-FIRST-BASELINE-2026-07-19-R3`  
**Supersedes:** `TA-FIRST-LAUNCH-DEFERRED-FUNCTION-RECOVERY-ROADMAP-2026-07-19-R1`  
**Date:** 2026-07-19  
**Repository:** `woshixiong/trader-assist-v0`  
**Status:** User-approved product-planning correction; documentation-only; pending independent review/merge

---

## 1. Purpose

Functions removed from the First Launch sprint are **deferred, preserved, and unscheduled**. They are not cancelled, but they are also not automatically placed into a fixed phase between First Launch and V0.

The project must first run First Launch in the real user workflow. Only after observing actual signal quality, usability, missed opportunities, operational friction, and trading value may Product Function and Priority Control redesign the subsequent roadmap.

This registry prevents deferred capabilities from being forgotten while preventing an outdated pre-launch roadmap from forcing unnecessary development.

No deferred capability may disappear merely because it is omitted from a later prompt, package, state file, pull-request description, or status report.

---

## 2. Product planning constitution

All future product planning must follow these principles in order.

### 2.1 Trading assistance is the purpose

Every product capability must have a clear connection to assisting real trading, including at least one of:

- finding or filtering actionable opportunities;
- improving timing or clarity;
- controlling trading risk;
- reducing monitoring or execution workload;
- improving post-trade learning in a way that changes future trading decisions.

A function with no credible trading-assistance value must not be developed merely because it is technically interesting or architecturally complete.

### 2.2 Fast iteration and fast reaction

The project should prefer:

- small end-to-end usable increments;
- rapid deployment;
- short feedback cycles;
- strategy-specific data additions;
- reversible decisions;
- direct observation of user value.

The project should avoid large foundation programs that postpone practical use.

### 2.3 Core need before feature breadth

Features must serve the current core trading need. The project must not expand scope simply because a complete trading platform could contain more data, infrastructure, automation, dashboards, or governance.

The default question is:

> What is the smallest reliable capability that materially improves the user's trading workflow now?

### 2.4 Balance instead of institutional perfection

The project is not attempting to reproduce an institutional quantitative trading stack.

The target is a balanced system that is:

- useful;
- understandable;
- sufficiently reliable;
- sufficiently safe for the authority granted;
- affordable to build and operate;
- easy to change when trading evidence changes.

Production hardening must be proportional to actual risk and usage. Institution-grade infrastructure, exhaustive audit systems, universal data platforms, and extreme optimization are not goals by themselves.

### 2.5 Safety directly protecting funds remains mandatory

“Do not pursue perfection” does not weaken controls that directly protect funds.

Before account access or exchange write, the project must implement the minimum controls necessary for:

- exact user confirmation;
- risk and notional limits;
- current-data and price checks;
- duplicate-order prevention;
- position/order conflict checks;
- signing and nonce correctness;
- protective-order verification;
- kill-switch behavior.

Safety controls directly connected to financial loss are product requirements, not optional engineering polish.

---

## 3. Adaptive post-First-Launch planning gate

There is no pre-authorized development phase named “between First Launch and V0.”

The only fixed next step after First Launch becomes operational is:

```text
FIRST LAUNCH REAL OPERATION
→ EVIDENCE COLLECTION
→ POST-FIRST-LAUNCH PRODUCT REPLANNING GATE
→ USER SELECTS THE NEXT PRODUCT CONFIGURATION
```

The replanning gate should normally occur after either:

- 7–14 operating days; or
- 10–20 actionable signals;

but may occur earlier if a clear product blocker or high-value opportunity appears.

At this gate, Product Function and Priority Control must review:

- signal frequency;
- signal quality and clarity;
- user response time;
- missed market regimes;
- false or noisy signals;
- manual execution friction;
- data and runtime failures;
- which existing First Launch components were useful;
- which V0 plans still match observed needs;
- which deferred functions now have evidence-based value;
- which newly discovered needs were not in the old roadmap.

The user then chooses one or more of the following dispositions:

1. **Integrate selected deferred capabilities into a revised V0 plan.**
2. **Extract selected V0 capabilities and combine them with selected deferred capabilities into a new iteration.**
3. **Create a new product milestone that does not follow the old V0 order.**
4. **Keep capabilities preserved but unscheduled.**
5. **Explicitly cancel or supersede capabilities that no longer serve trading assistance.**

No window, Agent, PR, governance document, or earlier roadmap may choose this disposition automatically.

---

## 4. Correction to the companion baseline

The following wording in the companion baseline is now interpreted as **candidate capability domains**, not an authorized sequence:

- “P1 — Immediately after First Launch”;
- “P2 — After assisted order execution exists”;
- “Post-launch development order”;
- the listed strategy-expansion and reviewed-order-workflow lanes.

Those items remain preserved candidates. They do not automatically start when First Launch launches.

Where this registry conflicts with a fixed post-launch sequence in the companion baseline or the superseded recovery roadmap, this R2 registry controls.

---

## 5. Canonical deferred capability ledger

All entries below are retained for future evidence-based replanning. “Preserved” does not mean “approved next.”

| Capability | Why deferred from First Launch | Possible future combination | Current disposition |
|---|---|---|---|
| Additional strategies for uncovered regimes | First prove the current signal loop and identify actual missed conditions | Revised V0, a focused strategy milestone, or a new post-launch iteration | `PRESERVED_UNSCHEDULED` |
| Range-edge sweep/reclaim, second-test, failed-retest, failed-breakout, OI-trap and key-wick strategies | Strategy need should be demonstrated by live observations | May be grouped by market regime rather than old project phase | `PRESERVED_UNSCHEDULED` |
| 1m/5m microstructure confirmation | Adds noise, data and implementation complexity before usefulness is proven | Attach only to a named strategy that needs it | `STRATEGY_DEPENDENT_PRESERVED` |
| Complete DCBR scoring, boundary registry and production regime overlay | Minimum volatility safety overlay is sufficient for the pilot | Combine with strategy validation or later risk-control work | `PRESERVED_UNSCHEDULED` |
| Funding z-score and longer-history derivatives models | Insufficient history and validation for hard gating | Combine with V0 analytics or a derivatives-context strategy | `DATA_DEPENDENT_PRESERVED` |
| Broader liquidation, session, macro, news, ETF or flow context | Not necessary for the minimum deterministic signal loop | Add only when a strategy or decision workflow demonstrates value | `CONTEXT_BACKLOG_PRESERVED` |
| BBO, spread and executable-price checks | Not required for manual signal notification | Combine with Order Preview or any exchange-write milestone | `SAFETY_PREREQUISITE_IF_SELECTED` |
| Full L2, trades, OFI, CVD and wall behavior | Universal microstructure platform would delay launch | Add only for a named strategy with defined behavioral evidence | `STRATEGY_DEPENDENT_PRESERVED` |
| Account read: balance, positions, orders and fills | No account authority in First Launch | Combine with reviewed order execution or reconciliation | `EXPLICIT_AUTHORITY_REQUIRED` |
| Deterministic user-reviewed Order Preview | Manual Hyperliquid execution is sufficient for the pilot | May combine with selected V0 execution components | `PRESERVED_UNSCHEDULED` |
| Testnet user-confirmed order submission | Requires execution controls and separate authority | Combine with Order Preview after evidence-based selection | `EXPLICIT_AUTHORITY_REQUIRED` |
| Mainnet very-small-risk user-confirmed submission | Fund risk requires prior acceptance and explicit authority | Combine with the minimum required safety controls | `EXPLICIT_AUTHORITY_REQUIRED` |
| Automatic protective SL/TP and cancellation recovery | Depends on a reliable submission workflow | Combine with any approved exchange-write milestone | `EXPLICIT_AUTHORITY_REQUIRED` |
| Human TAKEN/SKIPPED/REJECTED input surface | Signal notification is the immediate priority | Combine with operator usability or outcome closure | `PRESERVED_UNSCHEDULED` |
| Signal, decision, order and fill closure | Manual pilot can operate with stable signal IDs first | Combine with V0 outcome work or reviewed execution | `PRESERVED_UNSCHEDULED` |
| Shadow-to-real execution matching | Real fill evidence does not yet exist | Combine with execution or post-trade evaluation | `PRESERVED_UNSCHEDULED` |
| Real-time DecisionBundle integration | Existing offline modules need not block launch | Combine with a revised V0 evidence model if still useful | `PRESERVED_EXISTING_WORK` |
| Automatic Outcome, MFE/MAE and Pilot Review integration | Live signal usefulness must be proven first | Combine with selected V0 analytics or strategy evaluation | `PRESERVED_EXISTING_WORK` |
| Full historical backtest, walk-forward and parameter-grid platform | A general research platform is too large for the pilot | Build only when comparing/promoting specific strategies requires it | `RESEARCH_BACKLOG_PRESERVED` |
| Automated reports and strategy scorecards | Depend on meaningful outcome data | Combine with evaluation work if users need the reports | `PRESERVED_UNSCHEDULED` |
| Full operator dashboard | Notifications and minimal logs are sufficient initially | Combine with whichever live workflow proves valuable | `PRESERVED_UNSCHEDULED` |
| Richer notification channels and operator controls | One reliable channel is enough to launch | Add based on real response-time and usability evidence | `PRESERVED_UNSCHEDULED` |
| Full audit-grade persistence, tamper evidence and exactly-once guarantees | Minimum restart/de-duplication persistence is sufficient | Combine with higher authority, scale, or demonstrated audit need | `RISK_DEPENDENT_PRESERVED` |
| BTC and ETHBTC support | ETH-only scope accelerates learning | Combine with revised V0 or a separate asset expansion milestone | `PRESERVED_UNSCHEDULED` |
| Multi-strategy automatic selection and switching | Multiple independently validated strategies do not yet exist | Combine with a later strategy portfolio only after conflict rules exist | `EXPLICIT_AUTHORITY_REQUIRED` |
| AI signal explanation and evidence summary | Not required for authoritative deterministic signals | Combine with operator usability or contextual analysis | `NON_AUTHORITATIVE_PRESERVED` |
| AI market/news context and second opinion | Adds provider and reliability complexity | Combine only if it reduces monitoring or improves decisions | `NON_AUTHORITATIVE_PRESERVED` |
| AI post-trade review and failure-mode discovery | Requires sufficient live evidence | Combine with outcome analytics or strategy research | `NON_AUTHORITATIVE_PRESERVED` |
| AI strategy research and candidate generation | Candidate ideas are not production rules | Combine with a controlled research and validation process | `NON_AUTHORITATIVE_PRESERVED` |
| Automatic optimization or direct production-rule mutation | Unsafe without a new product/risk/governance decision | No default combination | `PROHIBITED_PENDING_NEW_AUTHORITY` |
| Multi-instance HA, Kubernetes, multi-region and distributed operations | No demonstrated scale or availability need | Add only if actual operations justify the cost | `OPERATIONS_BACKLOG_PRESERVED` |
| Broader V0 and mainline foundation work | The old sequence may not match post-launch evidence | Re-plan together with the deferred ledger after First Launch runs | `PRESERVED_FOR_REPLANNING` |

This ledger is deliberately not ordered by implementation priority.

---

## 6. Mandatory backlog-control rules

1. **No silent deletion.** A capability remains in the ledger until the user explicitly changes its disposition.
2. **No automatic activation.** First Launch completion does not activate any deferred item.
3. **No fixed bridge phase.** Deferred functions must not be inserted as a predetermined development phase between First Launch and V0.
4. **Joint replanning.** Deferred First Launch items, existing V0 plans, mainline plans, and newly discovered needs must be reviewed together.
5. **Evidence before priority.** Live trading-assistance evidence determines priority, not historical roadmap order.
6. **Existing work is preserved.** Offline modules and evidence paths must not be deleted merely because live integration is deferred.
7. **Minimal necessary build.** When an item is selected, implement the smallest end-to-end version that materially serves trading.
8. **Strategy-specific data.** Add data systems only when a selected strategy or workflow requires them.
9. **Proportional production quality.** Reliability work must match real authority and risk; institution-grade infrastructure is not a default goal.
10. **Direct fund-safety exception.** Safety controls required for account/exchange write cannot be waived by the speed principle.
11. **Product ownership.** Product Function and Priority Control decides selection, combination, sequencing, cancellation, and supersession.
12. **Engineering boundary.** Engineering Optimization may improve execution efficiency but may not reorder or activate product capabilities.
13. **Project Control boundary.** Project Control may activate only an explicitly user-selected bounded task.
14. **Ledger delta reporting.** At product gates and handoffs, report items added, selected, still preserved, superseded, or explicitly cancelled.
15. **No completeness claim.** First Launch may be complete while this ledger remains open; the broader product roadmap must not be described as complete.

---

## 7. Required post-launch planning output

The first formal post-First-Launch planning review must produce:

```text
POST_FIRST_LAUNCH_PRODUCT_REPLANNING_RULING
```

It must include:

- live operating evidence;
- the user's observed trading needs;
- missed regimes and workflow friction;
- current First Launch strengths and weaknesses;
- current V0/mainline relevance;
- a complete deferred-ledger review;
- newly discovered capabilities;
- proposed capability combinations;
- smallest viable next milestone;
- explicit items remaining unscheduled;
- explicit authority boundaries;
- explicit user decision.

It must not assume that the old V0 order remains correct.

---

## 8. Change control

A deferred item remains preserved until one of these exact dispositions is recorded:

- `SELECTED_FOR_USER_APPROVED_MILESTONE`
- `IMPLEMENTED_AND_ACCEPTED`
- `PRESERVED_UNSCHEDULED`
- `SUPERSEDED_BY_USER_APPROVED_DESIGN`
- `EXPLICITLY_CANCELLED_BY_USER`
- `PROHIBITED_PENDING_NEW_AUTHORITY`

Engineering Optimization, Project Control, Writer, Reviewer, Codex, or any other Agent may not infer cancellation, activation, priority, or authority from omission or from the prior roadmap.

Changes require an explicit user product decision and an updated canonical ledger.
