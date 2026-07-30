# First Launch Third Setup Strict Strategy Audit and Interaction Replay Gate

Record ID: `TA-FIRST-LAUNCH-THIRD-SETUP-STRICT-AUDIT-2026-07-30-R1`

Status: `STRATEGY_AUDIT_BASELINE / PRE-BACKTEST / NON-EXECUTABLE / NON-DEPLOYMENT`

Repository: `woshixiong/trader-assist-v0`

Live baseline reviewed: `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d`

Candidate SetupFamily: `RANGE_EDGE_REJECTION`

Current strategy core: `ETH-LDAR-v0.1`

## 1. Authority and scope

This record does not authorize:

- production code changes;
- production deployment or service restart;
- activation of a new SetupFamily;
- account credentials, signing, or exchange writes;
- automatic order submission;
- database schema migration;
- strategy parameter optimization;
- PR Mark Ready or merge.

This record freezes the minimum strategy-audit and interaction-replay work that must precede implementation.

## 2. Decision corrections

### 2.1 The earlier Range thresholds were provisional

Previous discussion established a plausible economic mechanism and a low-cost integration direction, but did not constitute a completed quantitative-strategy audit.

The following must therefore be treated as research hypotheses until the audit and replay gates pass:

- range lookback;
- boundary-touch tolerance;
- minimum range width;
- prior-touch count;
- rejection-candle strength;
- volume threshold;
- FAST/STANDARD split;
- entry zone;
- chase limit;
- stop buffer;
- target feasibility;
- invalidation and expiry.

No implementation team may treat those provisional values as production-approved merely because they appeared in an earlier planning note.

### 2.2 FAST is not cancelled

`RANGE_EDGE_REJECTION` remains one SetupFamily with two possible confirmation modes:

- `FAST`: same closed 5m candle creates the final StrategyOutput;
- `STANDARD`: the first candle creates a PreparedSetup and a later closed 5m candle confirms it.

Both modes must be included in offline research and interaction replay.

The production disposition may later be:

- FAST + STANDARD;
- STANDARD only;
- FAST only;
- one unified confirmation mode;
- REVISE;
- REJECT.

That decision must be evidence-led, not pre-decided.

### 2.3 No new feature flag is required by default

The user has rejected a new Range-specific operational feature flag as unnecessary scope.

The system is manual-only and every published TradePlan remains `NOT_SUBMITTED`; the human operator decides whether to trade.

Operational rollback will rely on:

- exact previous SHA;
- exact previous configuration;
- pre-deployment SQLite snapshot;
- deterministic post-deployment acceptance checks.

A feature flag may only be reintroduced if Engineering Optimization proves that it lowers total risk and work relative to exact-SHA rollback. It is not part of the default plan.

### 2.4 No additional Shadow subsystem

The existing First Launch pipeline already creates a durable `NOT_SUBMITTED` ShadowOrder for each published signal.

A separate controlled-shadow service, database, feature, or rollout framework is not authorized.

Operationally:

- the system may publish a signal;
- the operator may trade or skip it;
- the existing ShadowOrder and later Outcome evidence record the counterfactual and actual result.

`SHADOW` in this plan describes evidence use, not a new engineering subsystem.

## 3. Mature external evidence used

The strategy and replay plan must be informed by, but not copied blindly from, mature external sources.

### 3.1 Support and resistance evidence

Ken Chung and Anthony Bellotti, *Evidence and Behaviour of Support and Resistance Levels in Financial Time Series*:

- support/resistance zones can show statistically significant temporary reversal behavior;
- levels with more prior bounces are more likely to bounce again;
- level usefulness decays over time.

Source:

- https://arxiv.org/abs/2101.07410

Implication for Trader Assist:

- a Range setup must require prior evidence that the boundary is meaningful;
- one arbitrary rolling high/low is not enough;
- prior touch count and freshness are research variables;
- stale boundaries must not retain permanent authority.

### 3.2 Support/resistance as an optimal-stopping problem

Vicky Henderson, Saul Jacka, Ruiqi Liu, *The Support and Resistance Line Method: An Analysis via Optimal Stopping*:

- support/resistance trading is path dependent;
- entry and exit should be treated jointly, not as an isolated trigger;
- a valid boundary does not automatically imply a valid trade at every touch.

Sources:

- https://arxiv.org/abs/2103.02331
- https://link.springer.com/article/10.1007/s00780-026-00596-6

Implication for Trader Assist:

- the new Setup requires a complete contract: eligibility, trigger, confirmation, stop, target feasibility, expiry, and invalidation;
- a boundary-touch-only implementation is rejected.

### 3.3 Transaction costs and technical-rule false discovery

Bajgrowicz and Scaillet, *Technical trading revisited: False discoveries, persistence tests, and transaction costs*:

- apparently successful technical rules can fail persistence tests;
- even low transaction costs can eliminate apparent in-sample value.

Source:

- https://doi.org/10.1016/j.jfineco.2012.06.001

Hudson and Urquhart, *Technical trading and cryptocurrencies*:

- transaction costs are mandatory in cryptocurrency technical-strategy evaluation;
- positive gross results are not sufficient.

Source:

- https://doi.org/10.1007/s10479-019-03357-1

Implication for Trader Assist:

- the Range setup must be evaluated net of entry fee, exit fee, spread/slippage, funding where applicable, and manual delay;
- higher signal frequency is not itself evidence of value.

### 3.4 Mean reversion and OU limits

Tim Leung and Xin Li, *Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit*:

- OU models are appropriate only when the traded object can defensibly be modeled as a mean-reverting spread/process;
- entry, exit, transaction costs, stop-loss, and parameter stability are coupled.

Source:

- https://arxiv.org/abs/1411.5062

Implication for Trader Assist:

- ETH absolute price must not be assumed to be a stable OU process;
- OU is a future research comparator for validated spreads or stationary constructs, not a prerequisite for the first Range setup.

### 3.5 Lookahead and startup-window validation

Freqtrade official documentation:

- full-dataframe backtests can accidentally access future data;
- lookahead analysis must compare baseline and sliced runs;
- recursive/startup-candle differences can make backtest and live signals diverge;
- all signal types must actually trigger in the validation set or a false negative is possible.

Sources:

- https://github.com/freqtrade/freqtrade/blob/develop/docs/lookahead-analysis.md
- https://github.com/freqtrade/freqtrade/blob/develop/docs/recursive-analysis.md
- https://github.com/freqtrade/freqtrade/blob/develop/docs/backtesting.md

Implication for Trader Assist:

- the native replay must advance one closed candle at a time;
- no complete future dataframe may be exposed to strategy decisions;
- each SetupFamily, side, and confirmation mode must trigger at least once in deterministic validation fixtures;
- startup length must reproduce the live 64x5m and 20x15m contract.

### 3.6 Backtest overfitting and multiple trials

Bailey, Borwein, López de Prado, and Zhu, *The Probability of Backtest Overfitting*:

- ordinary holdout procedures can be unreliable for investment backtests;
- testing more configurations increases false-discovery probability.

Source:

- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

Bailey and López de Prado, *The Deflated Sharpe Ratio*:

- reported performance should account for selection bias, multiple testing, non-normality, and sample length.

Source:

- https://doi.org/10.3905/jpm.2014.40.5.094

Implication for Trader Assist:

- first-pass parameter variants must be pre-registered and few;
- every attempted variant must be recorded;
- the best-looking variant must not be reported without the full trial ledger;
- advanced PBO/DSR is not a First Launch blocker, but becomes mandatory if the research expands into many variants.

### 3.7 Open-source strategy repositories are research inputs, not proof

The official Freqtrade strategy repository states that its strategies are educational, should be backtested and dry-run first, and that results depend heavily on pair, timeframe, exchange, and timerange.

Source:

- https://github.com/freqtrade/freqtrade-strategies

Implication for Trader Assist:

- no external strategy is accepted by copy/paste;
- economic mechanism, data semantics, execution assumptions, and license obligations must be reviewed;
- external code is not evidence that a rule works on Hyperliquid ETH 5m/15m.

### 3.8 SQLite rollback method

SQLite's official Online Backup API can create a consistent snapshot of a live database and avoids unsafe ad-hoc copying while writes may be occurring.

Sources:

- https://www.sqlite.org/backup.html
- Python `sqlite3.Connection.backup` documentation.

Implication for Trader Assist:

- deployment rollback should use a real SQLite backup/snapshot procedure;
- a blind `cp` of a live WAL database is not the preferred evidence-grade rollback method.

## 4. Current-code audit findings

### 4.1 Current live strategy facts

At live baseline `ac649659...`:

- `STRATEGY_VERSION = ETH-LDAR-v0.1`;
- SetupFamily contains only `SWEEP_RECLAIM` and `BREAKOUT_RETEST`;
- FAST expires after 180 seconds;
- STANDARD is represented by PreparedSetup and a later StrategyOutput, with a 15-minute preparation window;
- TradePlan targets are fixed at 1R and 2R;
- runtime is manual-only and `NOT_SUBMITTED`.

### 4.2 High-risk finding: STANDARD progression must be verified before adding Range

The current runtime evaluates each newly finalized 5m candle by calling `evaluate_signal(snapshot)`.

When the returned object is a new PreparedSetup, the runtime:

1. accepts that PreparedSetup into the in-memory lifecycle;
2. immediately calls `advance` using the same snapshot.

The reviewed code does not visibly iterate all previously retained PreparedSetups on each later 5m candle.

This creates a material audit question:

`CAN_EXISTING_STANDARD_PREPARE_ADVANCE_ON_A_LATER_REAL_5M_CANDLE?`

Before any new strategy work, Engineering Optimization must produce a deterministic runtime-level test proving either:

- PASS: existing SWEEP/BREAKOUT STANDARD setups are advanced on subsequent candles; or
- FAIL: current production STANDARD progression is incomplete/unreachable.

If FAIL:

- this is an existing First Launch defect, not a Range-specific enhancement;
- the defect must be isolated and fixed before using STANDARD for Range;
- the fix must not be hidden inside the Range strategy patch without explicit scope and review.

### 4.3 Current lifecycle is keyed by setup_id, not globally single-active

`InMemorySignalLifecycle` retains dictionaries of states, prepared setups, and outputs keyed by setup_id.

This structure can retain more than one setup identity unless a higher layer prevents it.

The current `evaluate_signal` accepts `decided_setup_ids`, but the reviewed runtime call does not pass a non-empty decided set.

Therefore the following must be measured and tested, not assumed:

- multiple PreparedSetups across different setup IDs;
- multiple active outputs across different setup IDs;
- same-direction duplicates;
- opposite-direction outputs;
- restart/reconnect behavior;
- duplicate publications prevented only by signal ID uniqueness, not by market-event identity.

### 4.4 Same-candle first-match behavior hides raw overlap

Current `evaluate_signal` returns the first matched candidate in a fixed order.

This proves only the final selected output. It does not prove that later candidate predicates were false.

A research-only candidate enumerator is required to record all raw candidate predicates before arbitration.

The production evaluator does not need a large refactor; the research harness may reproduce the exact predicates independently and verify parity.

### 4.5 TradePlan 1R/2R is not automatically suitable for Range

Current TradePlan enforces:

- TP1 = 1R;
- TP2 = 2R.

A range-edge trade has finite space before the range midpoint/opposite boundary.

Therefore the Range setup requires a target-feasibility gate:

- calculate planned entry and stop;
- calculate R;
- require that the available distance inside the validated range supports TP2 plus a cost reserve;
- otherwise reject the setup before publication.

This preserves the current TradePlan schema and avoids inventing a new range-specific target model in the minimum release.

If backtest evidence shows midpoint/opposite-edge exits are materially better, that becomes a separate TradePlan-version decision.

### 4.6 Strategy version is hard-coded across live and offline authorities

The current code binds the global `STRATEGY_VERSION` into:

- setup_id;
- TradePlan fixed-authority validation;
- signal_id;
- offline Outcome validation;
- historical plan semantics.

A naive global change from `ETH-LDAR-v0.1` to `ETH-LDAR-v0.2` can invalidate old serialized records in offline tooling.

The minimum compatibility route must preserve:

- database schema version 1;
- TradePlan version 3 unless schema changes are genuinely required;
- old publication JSON unchanged;
- exact old SHA for old-record interpretation;
- new strategy version for new outputs;
- version-aware offline validation based on the record's embedded version, not only the current global constant.

Mandatory compatibility tests:

1. current production database opens under candidate code;
2. old publication rows remain queryable;
3. old pending notification payloads remain deliverable;
4. publication existence checks remain valid;
5. new v0.2 Range rows can be inserted;
6. mixed v0.1/v0.2 rows do not block runtime startup;
7. current SHA can be restored;
8. if exact-SHA rollback cannot operate on the mixed database, restoring the pre-deployment SQLite snapshot succeeds.

### 4.7 No database schema change is justified for the minimum release

The current publication schema stores canonical JSON blobs and opaque identifiers.

The new SetupFamily should fit the existing publication bundle without adding a column or table.

If implementation requires a schema migration, stop and return to Engineering Optimization. The minimum route is no longer being followed.

## 5. Quantitative strategy architecture

The following is the pre-backtest strategy contract. Values are initial pre-registered research values, not profitability claims.

Engineering Optimization may recommend a smaller variant set, but may not silently expand it after seeing results.

### 5.1 Economic hypothesis

In a non-directional market, a recently validated horizontal boundary that has produced multiple prior reactions may temporarily reject price again when:

- the current closed 5m candle touches or only shallowly crosses the boundary;
- the market does not accept price beyond the boundary;
- the candle closes back inside the range;
- enough reward space remains inside the range after costs.

Failure mechanism:

- the range is transitioning into a true trend/breakout;
- the boundary is stale or accidental;
- the range is too narrow to pay costs;
- the bar touches both sides and has ambiguous meaning;
- the price reaction is only noise without confirmation.

### 5.2 Data

No new production data source:

- ETH closed 5m OHLCV;
- ETH closed 15m OHLCV;
- current Wilder ATR14 authority;
- current 15m bias features;
- current activeAssetCtx for mark/mid/OI/funding context;
- current volatility regime.

OI and funding remain attribution variables in the first replay. They are not hard trigger gates.

### 5.3 Range-establishment window

Primary pre-registered value:

- `RANGE_LOOKBACK_5M = 24` closed 5m candles, excluding the trigger candle.

Reason:

- two hours provides more evidence than the current one-hour breakout boundary;
- it remains fully inside the existing 64-candle snapshot;
- it allows distinct prior reactions to be counted.

Research comparator:

- `RANGE_LOOKBACK_5M = 18`.

No wider parameter grid is permitted in the first pass.

### 5.4 Boundary construction

- `upper = max(high)` over the range window;
- `lower = min(low)` over the range window;
- `width = upper - lower`;
- `midpoint = (upper + lower) / 2`.

### 5.5 Range-width eligibility

Primary pre-registered band:

- `1.50 ATR <= width <= 4.00 ATR`.

Reason:

- below 1.50 ATR, fee/slippage and stop distance can consume too much of the available movement;
- above 4.00 ATR, one rolling high/low pair is less likely to represent one coherent intraday range.

Research comparator:

- lower bound 1.25 ATR;
- upper bound unchanged.

### 5.6 Prior touch evidence

A historical candle touches an edge when its extreme is within `0.15 ATR` of that edge.

Distinct touch events must be separated by at least three 5m candles.

Primary eligibility:

- candidate edge has at least two prior distinct touch events;
- opposite edge has at least one prior distinct touch event;
- the latest opposite-edge touch occurred within the previous 12 candles.

This encodes mature support/resistance findings that repeated reactions increase relevance and stale levels decay.

### 5.7 Direction and volatility eligibility

First-pass Range eligibility requires:

- current 15m `long_bias == false`;
- current 15m `short_bias == false`;
- volatility regime `NORMAL`.

LOW/HIGH/EXTREME are attribution-only in the first research run.

They may be tested as explicit second-pass variants only after the primary run is frozen and reported.

### 5.8 Same-bar dual-edge veto

If the trigger candle touches both the upper-edge zone and lower-edge zone:

- no Range candidate is eligible;
- reason: `RANGE_DUAL_EDGE_AMBIGUOUS`.

This prevents one unusually large bar from simultaneously appearing as a long and short rejection.

### 5.9 Long setup predicate

Required common conditions:

- Range eligibility passes;
- trigger low is within the lower-edge touch zone;
- outside excursion below lower is strictly less than `0.10 ATR`;
- trigger closes inside the range;
- trigger does not touch the upper-edge zone;
- Sweep Long raw predicate is false;
- Breakout Long raw predicate is false;
- Sweep Short and Breakout Short raw predicates are false.

Short is the exact mirror.

### 5.10 FAST confirmation mode

Primary FAST Long contract:

- trigger low touches or shallowly crosses lower;
- outside excursion `< 0.10 ATR`;
- close `>= lower + 0.10 ATR`;
- close location within candle range `>= 0.70`;
- lower wick / full candle range `>= 0.35`;
- volume `>= 1.20 x` prior-20 median volume;
- target-feasibility gate passes.

FAST Short is mirrored.

FAST authority:

- final StrategyOutput on the same closed 5m candle;
- expiry remains 180 seconds unless replay shows the current expiry makes the setup operationally unusable.

### 5.11 STANDARD confirmation mode

Initial PreparedSetup Long contract:

- common Range predicate passes;
- close is inside range;
- close location `>= 0.55`;
- volume `>= 0.80 x` prior-20 median volume;
- FAST predicate is false;
- target-feasibility gate can still plausibly pass.

Confirmation window:

- next one to three closed 5m candles;
- maximum 15 minutes from setup trigger.

Long confirmation requires:

- no close below `lower - 0.10 ATR`;
- no new low below initial extreme by more than `0.05 ATR`;
- confirmation close `>= lower + 0.05 ATR`;
- confirmation close is greater than the setup candle close OR confirmation low is greater than the setup candle low;
- target-feasibility gate passes using final entry/stop geometry.

Short is mirrored.

### 5.12 Entry, chase, and stop geometry

Primary FAST Long geometry:

- entry zone: `[lower, lower + 0.10 ATR]`;
- chase limit: `lower + 0.20 ATR`;
- stop: `min(initial_low - 0.10 ATR, lower - 0.20 ATR)`.

Primary STANDARD Long geometry:

- entry zone: `[lower - 0.05 ATR, lower + 0.10 ATR]`;
- chase limit: `lower + 0.20 ATR`;
- stop: `min(material_low - 0.05 ATR, lower - 0.20 ATR)`.

Short is mirrored.

All geometry remains subject to the existing TradePlan stop-distance authority:

- minimum 0.10 ATR;
- maximum 1.50 ATR.

### 5.13 Target-feasibility gate

Current TradePlan keeps:

- TP1 = 1R;
- TP2 = 2R.

For Long:

- `available_space = upper - planned_entry`.

For Short:

- `available_space = planned_entry - lower`.

Require:

- `available_space >= 2R + 0.10 ATR cost/resolution reserve`.

If false:

- no actionable Range signal;
- reason: `RANGE_REWARD_SPACE_INSUFFICIENT`.

This avoids changing the TradePlan target model in the minimum release.

### 5.14 Invalidation

Invalidate a Range PreparedSetup when any occurs:

- data quality ceases to be READY;
- preparation window expires;
- a close is accepted outside the candidate boundary by `>= 0.10 ATR`;
- a new material extreme violates the initial rejection by more than `0.05 ATR`;
- opposite-edge touch occurs before confirmation;
- reward-space gate no longer passes;
- an existing higher-priority setup owns the same market event under the final arbitration policy.

## 6. FAST versus STANDARD audit decision

### 6.1 They are not separate strategies

Both are confirmation modes inside one SetupFamily and one economic hypothesis.

User-facing presentation may show one strategy name and a confirmation label.

Internal separation must remain during research because they differ in:

- information available at decision time;
- entry delay;
- signal frequency;
- false-positive rate;
- expiry;
- entry price and stop geometry;
- transaction-cost sensitivity.

### 6.2 Do not literally merge before evidence

A literal merge would force one of two hidden choices:

- always act on the first rejection candle, effectively FAST only; or
- always wait for a later candle, effectively STANDARD only.

That would discard measurable information before replay.

The correct minimum design is:

- one SetupFamily;
- one shared economic contract;
- two explicit confirmation modes;
- one combined replay comparing both;
- one later production decision.

### 6.3 Range is not automatically simpler than Sweep/Breakout

The visible candle pattern is simpler, but the difficult problem is determining whether the market is genuinely range-bound or beginning a real breakout.

Therefore the Range strategy has lower trigger-code complexity but non-trivial regime and false-break risk.

It must not be treated as inherently safer merely because its chart pattern is visually simple.

## 7. Three-Setup interaction replay

### 7.1 Interaction can and must be tested before production

The replay must enumerate all raw candidates before selecting a final output.

For every finalized 5m candle, record:

- Sweep Long raw predicate;
- Sweep Short raw predicate;
- Breakout Long raw predicate;
- Breakout Short raw predicate;
- Range Long FAST raw predicate;
- Range Short FAST raw predicate;
- Range Long STANDARD prepare predicate;
- Range Short STANDARD prepare predicate;
- every active PreparedSetup;
- every active unexpired StrategyOutput;
- final selected output;
- suppression reason.

### 7.2 Required modes

A. `BASELINE_EXACT`

- run the exact deployed v0.1 strategy;
- preserve all outputs as authority baseline.

B. `BASELINE_INSTRUMENTED`

- reproduce current predicates individually;
- prove selected outputs equal `BASELINE_EXACT` exactly;
- expose hidden raw overlaps between existing candidates.

C. `RANGE_ONLY`

- run FAST and STANDARD Range modes without existing setups;
- measure standalone behavior.

D. `COMBINED_ALL_RAW`

- retain every raw candidate without arbitration;
- measure same-candle and cross-candle overlap.

E. `COMBINED_EXACT_POLICY`

- apply the proposed mutual-exclusion and lifecycle policy;
- produce the final counterfactual production stream.

### 7.3 Same-candle interaction matrix

The replay must prove:

- Breakout vs Sweep: close-outside versus close-inside separation;
- Sweep vs Range: excursion `>= 0.10 ATR` versus `< 0.10 ATR`;
- Breakout vs Range: close outside versus close inside;
- Range Long vs Range Short: dual-edge veto;
- exact equality at `0.10 ATR` belongs to Sweep, not Range;
- final baseline output is never displaced by Range.

### 7.4 Cross-candle interaction matrix

Measure:

- existing Prepare followed by Range candidate;
- Range Prepare followed by existing candidate;
- active FAST followed by same-direction candidate;
- active FAST followed by opposite candidate;
- active STANDARD followed by same-direction candidate;
- active STANDARD followed by opposite candidate;
- multiple setup identities in one market event;
- reconnect while Prepare is active;
- process restart while Prepare/output is active.

Do not pre-assume the final policy.

The replay must report at least three counterfactual policies:

1. `PRIORITY_AND_SINGLE_ACTIVE`;
2. `ALLOW_SAME_DIRECTION_DEDUPLICATED`;
3. `PUBLISH_ALL_WITH_CONFLICT_LABEL` research-only.

Production selection must minimize silent displacement and operational ambiguity.

### 7.5 Interaction metrics

Mandatory:

- baseline output mismatch count;
- same-candle raw overlap count and rate;
- cross-candle overlap count and rate;
- same-direction duplicate count;
- opposite-direction conflict count;
- priority suppression count;
- active-state suppression count;
- dual-edge ambiguous count;
- unique market-event count;
- signals per market event;
- baseline signals displaced by Range;
- Range signals displaced by baseline;
- incremental net expectancy;
- incremental maximum drawdown;
- incremental longest losing streak;
- incremental fee/slippage drag.

### 7.6 Non-negotiable interaction gates

`BASELINE_PRESERVATION = PASS` requires:

- exact baseline output count equality;
- exact setup family, side, speed, candle identity, geometry, and publication decision equality;
- zero baseline signal displaced by Range.

`SAME_CANDLE_EXCLUSIVITY = PASS` requires:

- no final dual Setup output on one candle;
- every raw overlap has an explicit classification;
- exact threshold boundaries are deterministic.

`CROSS_CANDLE_SAFETY = PASS` requires:

- no silent overwrite;
- no automatic reversal;
- no orphan PreparedSetup;
- no duplicate publication for one market event;
- every suppression is counted and reason-coded.

If interaction conflicts are material and cannot be resolved without a multi-strategy architecture:

- stop the SetupFamily route;
- return `SPLIT_TO_INDEPENDENT_STRATEGY` or `REJECT`.

## 8. Replay rigor

### 8.1 Causal time

- advance one authoritative closed candle at a time;
- expose only data available at that historical timestamp;
- preserve 5m/15m cutoff semantics;
- no open candle decisions;
- no future dataframe aggregation.

### 8.2 Outcome path resolution

Use 1m data where possible to resolve intrabar ordering.

If Stop and TP are both touched within one unresolved bar:

- mark `AMBIGUOUS_SAME_BAR`;
- use conservative Stop-first for the primary result;
- report an optimistic alternative separately;
- never silently select the favorable path.

### 8.3 Costs

Report at minimum:

- ideal planned-entry outcome;
- realistic manual-delay outcome;
- stress outcome.

Include:

- entry fee;
- exit fee;
- spread/slippage;
- delay;
- chase rejection;
- expiry;
- funding where relevant.

### 8.4 Trial ledger

Record every tested variant:

- exact parameter set;
- dataset hash;
- code SHA;
- start/end timestamps;
- signal count;
- result.

Do not delete losing variants.

## 9. Version and rollback contract

### 9.1 Current baseline freeze

Before any implementation:

- record live SHA `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d`;
- record deployed unit/config hashes;
- record current database path and integrity check;
- create a consistent SQLite backup;
- preserve exact deployment bundle and restore procedure.

### 9.2 Minimum candidate version

Preferred candidate strategy version:

- `ETH-LDAR-v0.2`.

Do not keep `v0.1` while silently changing its SetupFamily set.

### 9.3 No schema migration

Keep:

- SQLite `user_version = 1`;
- publication schema unchanged;
- TradePlan version 3 unless the serialized field set changes.

### 9.4 Version-aware offline validation

Offline Outcome validation must calculate hashes and semantics using the strategy version embedded in each record.

It must not require every old record to equal the current global version.

Minimum allowlist:

- `ETH-LDAR-v0.1` with Sweep/Breakout only;
- `ETH-LDAR-v0.2` with Sweep/Breakout/Range.

Historical hashes remain immutable.

### 9.5 Rollback proof

Before production acceptance, prove one of:

A. `CODE_ONLY_ROLLBACK_PASS`

- old exact SHA starts on the mixed v0.1/v0.2 database;
- old pending notifications remain safe;
- no schema or startup error.

or

B. `CODE_PLUS_DB_RESTORE_REQUIRED`

- restore old exact SHA;
- restore pre-deployment SQLite snapshot;
- verify integrity and READY.

No deployment without an executed rollback rehearsal in a non-production copy.

## 10. Removed or deferred work

Not part of this iteration:

- Range feature flag;
- separate Shadow service;
- generic plugin framework;
- independent second-strategy architecture;
- L2 Order Book;
- trades/order-flow feed;
- Volume Profile;
- automatic regime router;
- Hummingbot/Nautilus production integration;
- automatic execution;
- database schema migration;
- broad UI work;
- automatic parameter optimization.

## 11. Required next Engineering Optimization deliverable

Before Project Control assigns any implementation, Engineering Optimization must return:

1. `REVIEW_STATUS`;
2. live identity and deployed strategy proof;
3. deterministic proof or failure of existing STANDARD progression;
4. exact Range strategy contract review;
5. accepted pre-registered parameter variants;
6. exact raw candidate enumerator design;
7. exact combined replay state machine;
8. same-candle interaction matrix;
9. cross-candle interaction matrix;
10. target-feasibility implementation;
11. version-aware compatibility design;
12. no-schema-change proof;
13. rollback rehearsal design;
14. expected file allowlist;
15. time and resource estimate;
16. stop conditions;
17. one-shot Project Control prompt;
18. one-shot replay/Codex task prompt;
19. independent strategy-audit reviewer prompt;
20. independent patch-review prompt.

## 12. Stop conditions

Return `STOP / REPLAN` if any occurs:

- existing STANDARD progression is broken and cannot be isolated safely;
- baseline outputs cannot be preserved exactly;
- Range requires a new market-data transport;
- Range requires database schema migration;
- three Setup interactions cannot be made explicit;
- material opposite-direction conflicts require parallel strategy ownership;
- 1R/2R target feasibility rejects nearly all valid Range events;
- positive results require repeated unregistered tuning;
- costs remove the apparent edge;
- version compatibility cannot be bounded;
- rollback cannot be rehearsed;
- implementation touches candle-authority transport;
- expected work exceeds the minimum SetupFamily route and approaches a multi-strategy platform.

## 13. Final pre-backtest disposition

Current disposition:

- `RANGE_EDGE_REJECTION_ECONOMIC_HYPOTHESIS = PLAUSIBLE`
- `QUANTITATIVE_CONTRACT = PRE_REGISTERED_FOR_REVIEW`
- `FAST = RETAIN_IN_RESEARCH`
- `STANDARD = RETAIN_IN_RESEARCH`
- `FAST_STANDARD_LITERAL_MERGE = NOT_AUTHORIZED_BEFORE_REPLAY`
- `THREE_SETUP_INTERACTION_REPLAY = MANDATORY`
- `FEATURE_FLAG = DEFERRED / NOT_REQUIRED`
- `NEW_SHADOW_SUBSYSTEM = REJECTED`
- `DATABASE_SCHEMA_CHANGE = NOT_EXPECTED`
- `PRODUCTION_IMPLEMENTATION = NOT_YET_AUTHORIZED`
