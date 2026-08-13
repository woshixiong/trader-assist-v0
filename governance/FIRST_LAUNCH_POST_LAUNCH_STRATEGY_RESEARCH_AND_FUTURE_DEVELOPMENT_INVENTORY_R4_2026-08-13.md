# First Launch 上线后策略研究与未来开发完整清单 R4

**记录 ID：** `TA-FIRST-LAUNCH-POST-LAUNCH-STRATEGY-RESEARCH-FUTURE-DEV-INVENTORY-R4-2026-08-13`  
**日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `CURRENT COMPLETE RESEARCH / FUTURE DEVELOPMENT INVENTORY / NON-EXECUTABLE / NON-AUTHORIZING`  
**父级：** `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_SHADOW_EVIDENCE_BACKLOG_R1_2026-08-12.md`  
**取代关系：** 本文件取代 `...INVENTORY_R3_2026-08-13.md` 作为完整未来候选清单。R3/R2 保留审计价值。未来全局优先级仍未冻结，必须等 First Launch Forward/Shadow Evidence 后统一排序。

---

## 1. 当前发布边界不变

```text
CURRENT_RELEASE_NEW_STRATEGY_LOGIC = 0
CURRENT_MACHINE_PARAMETER_CHANGE = 0
NEW_FORMAL_SETUP_COMMITTED = 0
AUTO_TRADE_THIS_RELEASE = NO
```

正式三 Setup 继续：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST  # MICRO_FAST + STANDARD
RANGE_EDGE_REJECTION
```

当前 Micro FAST 已经覆盖相当一部分 Strong / No-Retest Breakout；本轮不新增 Momentum Setup，不把 `BREAKOUT_RETEST` 重构成新的 Setup family 名称。

当前 live engineering integration PR #78 已进入 exact-head acceptance 阶段。任何新的代码变化都会移动 exact HEAD，并必须重新完成 CI / independent acceptance，因此 research-adjacent scope 必须具有明显的信息价值且工程成本极低才值得在 First Launch 前加入。

---

## 2. 本轮唯一高价值 Research-Evidence 候选

### 2.1 `BOUNDED_INITIAL_BREAKOUT_1M_RESEARCH_PATH`

目标：对**满足当前 Machine Strategy Initial Breakout 定义**的 Event 保存 bounded 1m raw path，即使最终没有产生 Formal Shadow Plan。

核心目的不是产生新信号，而是避免只观察 Formal Plans 的 selection bias，并保留以下未来反事实研究能力：

```text
MICRO_FAST coverage
MISSED_RUNAWAY_BREAKOUT
MICRO_PULLBACK
TIME_ACCEPTANCE / CHILD MICRO-BALANCE
IMMEDIATE_FAILURE
DELAYED_FAILED_ACCEPTED_BREAKOUT
CHASE_LIMIT opportunity cost
hypothetical earlier-entry MFE / MAE / drawdown
FAST_FAILURE / logical invalidation
```

推荐研究窗口优先直接复用当前 Formal Outcome 的 `30m / 60m / 120m` horizon 语义；为了能够看到 Initial Breakout 5m candle 内部路径，Engineering 应评估最小 pre-roll 是否从 `initial_breakout_5m_open_time` 开始，而不是只从 Formal confirmation / planned entry 后开始。多保存约 5 分钟 1m candles 的价值明显高于其数据成本。

实施原则：

```text
SAVE RAW RECONSTRUCTABLE EVIDENCE
DO NOT COMPUTE NEW LIVE STRATEGY FEATURES
FAIL OPEN FOR STRATEGY
FAIL CLOSED / INCOMPLETE FOR RESEARCH QUALITY
```

如果不能直接复用现有 on-demand 1m Outcome collector，或需要新 runtime framework / complex scheduler / large schema rewrite / material acceptance delay，则不阻塞 First Launch。

### 2.2 1m `volume` / `trade_count` 原始值——仅条件候选

Hyperliquid 1m candle 原生包含 `v`（volume）和 `n`（number of trades）。它们对 activity/event-time proxy 有研究价值。

但当前 PR78 的 `OneMinuteBar` 权威模型主要用于 OHLC path。是否扩展 `volume` / `trade_count` 必须由 Engineering 先核验：

```text
IF source/provider already exposes them
AND persistence can retain them with trivial bounded change
AND no material schema/migration/identity complexity
THEN estimate as OPTIONAL evidence extension
ELSE DEFER
```

即使保存 `n/v`，也只能支持 1m 聚合 activity proxy；它不能准确重建 trade-by-trade `outside_trade_ratio` 或 aggressive buy/sell flow。因此不得为了这一研究现在增加 trades WebSocket。

### 2.3 OI Snapshot——只在“现有数据零/近零成本复用”时估算

Hyperliquid public asset context 提供 open interest。未来 `Price × OI` 四象限值得研究，但目前没有足够证据证明固定象限规则具有生产 edge。

只有当当前 Scanner/Correlation/market-context 已经在 Initial Breakout Event 附近自然拥有 OI snapshot，且无需新请求循环、新 provider、新定时器即可绑定到 research evidence 时，Engineering 才可把最小 event-time OI snapshot 作为可选估算项。

不得为了 `OI_DELTA` 本轮新建持续 OI history subsystem。

---

# A. BREAKOUT ACCEPTANCE / LIFECYCLE

## A1. Unified Breakout Lifecycle

同一底层 Breakout Event 必须完整保留并分类：

```text
MICRO_FAST_SUCCESS
STANDARD_SUCCESS
MISSED_RUNAWAY_BREAKOUT
IMMEDIATE_BREAKOUT_FAILURE
DELAYED_FAILED_ACCEPTED_BREAKOUT
AMBIGUOUS / INSUFFICIENT_DATA
```

禁止只研究 taken / stopped / winning Shadow Orders。

## A2. Impact Retention / Giveback

新的高价值研究特征：

```text
max_displacement_from_old_edge
max_giveback
impact_retention
retention_at_1m / 3m / 5m / later horizons
```

研究假设来源于 market-impact 文献中 transient vs persistent impact 的区分。该指标当前**离线计算**，不作为 live gate。

30s retention 需要更高频 path，当前不为此扩展基础设施。

## A3. Retest / Continuation / Failure Competing Outcomes

每个 breakout 在因果窗口内记录第一个达到的结构事件：

```text
RETEST
CONTINUATION_0_5ATR
CONTINUATION_1ATR
FAILURE / ACCEPTED_REENTRY
AMBIGUOUS_SAME_1M_BAR
```

研究：

```text
time_to_retest
time_to_0_5ATR
time_to_1ATR
time_to_failure
```

第一阶段只做 deterministic first-event / bucket statistics；样本量足够以后才考虑 formal competing-risk survival model。

若同一 1m candle 同时触及多个互斥阈值且无法知道 intrabar sequence，必须标记 `AMBIGUOUS`，不得 hindsight 排序。

## A4. MICRO_PULLBACK

继续作为 `BREAKOUT_RETEST` 的未来 execution subtype 研究，而不是第四 Setup。研究 1m shallow pullback 是否改善 entry、MAE、stop distance 和 net expectancy。

## A5. TIME_ACCEPTANCE / Nested Auction / Child Micro-Balance

研究：

```text
PARENT BALANCE
→ Initial Breakout
→ outside CHILD MICRO-BALANCE
→ child breakout / failure
```

候选离线特征：

```text
child_high / child_low
child_width_atr
child_duration
child_distance_from_parent_edge
```

第一阶段从 bounded 1m path 离线识别；不新增实时 Auction engine。

## A6. Event-Time Acceptance

保留两个时间概念：

```text
CLOCK TIME
EVENT / ACTIVITY TIME
```

成熟 market-microstructure 文献支持使用 business/event time 与 calendar time 分开观察高频市场活动，但这不意味着 event-time 阈值天然有交易 edge。

第一阶段可使用已有/低成本 1m candle `volume` / `trade_count` 做粗 activity proxy（若可低成本保存）；真正的：

```text
outside_trade_count
outside_trade_ratio
outside_volume_ratio
aggressive directional flow
```

需要 trade-level path，当前延期。

## A7. Breakout Probe / Probe→Add

继续 Research Only。

只有当完整样本证明：

```text
MISSED_RUNAWAY economic cost
>
additional false-break loss + fee + slippage + implementation complexity
```

才进入开发评估。

未来比较： naked boundary / buffered trigger / buffered small probe / probe + acceptance add。禁止 full-size blind breakout chase。

## A8. Chase Economics / MISSED_VALID_BREAKOUT

当前 Chase 参数不改。合法 outcome 保留：

```text
MISSED_VALID_BREAKOUT
```

研究是否值得为减少 miss 付出更多 false-breakout loss。

## A9. Fast Failure / Logical Invalidation

统一研究 immediate reclaim、accepted re-entry、child-support failure 等是否能够比固定 Hard Stop 更早识别失效。先离线 Counterfactual，不改 current stop。

---

# B. AUCTION / RANGE

## B1. Auction Regime taxonomy

```text
BALANCE
EDGE_TEST
FAILED_AUCTION
ACCEPTED_BREAK
REBALANCE
```

定位：`RESEARCH / ATTRIBUTION ONLY`。

不建立完整 Market Profile / TPO / Footprint / DOM，不作为 current live Hard Gate。

## B2. RANGE_EDGE_REJECTION Information Strength

研究 Range Edge 在市场尚未完成 Reject/Accept 选择时是否天然信息较弱；比较其 expectancy / MAE / failure rate 与 Sweep / Accepted Breakout。

当前不降权、不 suppress。

---

# C. FLOW × IMPACT × LIQUIDITY

保留四类研究 taxonomy：

```text
CONTINUATION: strong directional flow + weak opposing liquidity / weak replenishment
ABSORPTION: strong flow + weak price impact
LIQUIDITY VACUUM: large price displacement with weak/modest flow because liquidity disappears
WEAK BREAK: weak flow + ordinary liquidity + weak impact
```

这是 Wyckoff `Effort vs Result` 的可量化研究版本，但不采用不可证伪的“庄家/Smart Money”叙事。

`Flow-to-Impact Efficiency`、OFI、CVD、queue imbalance、microprice、cancellation、replenishment、resiliency 全部属于后续层。经典 microstructure 研究支持 OFI × inverse depth、queue imbalance 和 resiliency 具有短周期信息，但参数来自传统 LOB，不能直接迁移到 Hyperliquid。

当前只保存低成本 price/volume/BBO evidence；L2/order-flow 层必须由上一层数据证明增量问题存在后再开发。

---

# D. OI / PERPETUAL-SPECIFIC RESEARCH

研究但不预设：

```text
Price Up + OI Up
Price Up + OI Down
Price Down + OI Up
Price Down + OI Down
```

这些只作为 positioning / leverage-flow hypothesis，不能直接解释成“新多/short covering/新空/long liquidation”的唯一因果标签。真实交易、开平仓和多空双方结构并不能仅由 aggregate OI + price 唯一识别。

后续比较 continuation / retest / failure / MFE / MAE。

Funding、mark/oracle basis、liquidation/forced-flow context 继续保留为未来 perpetual-specific attribution 候选。

---

# E. CLOCK / SESSION PHASE

`minute_mod_5 / minute_mod_15` 等字段原则上从已有 timestamps 离线计算，不应新增长期 schema 字段。

重要限制：当前 Machine Strategy 以 closed 5m candle 创建/确认事件，因此 `minute_mod_5` 对 Formal event timestamp 基本没有信息量；如果未来要研究“真实 boundary crossing 发生在 5m bar 的第几秒/第几分钟”，必须先有 sub-5m event path。

因此：

```text
CLOCK_PHASE = RESEARCH_ONLY_DERIVED
NO CURRENT SCHEMA FIELD REQUIRED
```

---

# F. EXISTING FUTURE INVENTORY — CONTINUES

R3 中以下全部方向继续有效，并被 R4 纳入：

```text
PER_MARKET_STABLE_TIMEFRAME_PROFILE
SECTOR / PEER RELATIVE STRENGTH
CROSS-MARKET CONFIRMATION SOFT CONTEXT
CORRELATION / EXPOSURE GOVERNANCE
SCHEDULED MACRO EVENT / EVENT ASSET ROUTER
PIT surprise vector / forecast disagreement / policy uncertainty / sensitivity
Investor Attention / FedWatch / prediction-market distribution
Macro-Pure vs Sector-Amplifier / Event Leader-Laggard / NO_TRADE
Event-window high-res evidence / execution quality
NQ/ES vs Hyperliquid index tracking
FOMC separate event family
Macro event volatility/options branch
CASH OPEN / OPENING REPRICING
LOGICAL INVALIDATION EXIT
PROBE→ADD / POSITION SCALING
POST-LAUNCH COST / EXECUTION MODEL
ADVANCED L2 / OFI / CVD / QUEUE / RESILIENCY
COMPLETE-SAMPLE / COUNTERFACTUAL SHADOW RESEARCH
CLUSTER-NORMALIZED STATISTICS
EXPERIMENT REGISTRY / PBO / DEFLATED SHARPE / WALK-FORWARD
```

Future global priority remains `NOT_YET_FROZEN`.

---

# G. ADVANCED METHODS — REGISTERED BUT DEFERRED

The following may later be used only if simple deterministic evidence is insufficient:

```text
Directional Change
CUSUM
Bayesian Change Point
HMM
Hawkes Process
ML classifier
```

No current production work is authorized.

---

# H. 当前 First Launch 前四档收敛

## MUST DO

```text
NO NEW STRATEGY LOGIC
SHIP / ACCEPT CURRENT PR78 ROUTE
KEEP THREE SETUPS FROZEN
```

## SHOULD ESTIMATE NOW — user decision required before implementation

```text
BOUNDED_INITIAL_BREAKOUT_1M_RESEARCH_PATH
prefer initial-breakout 5m-bar open pre-roll + existing 30/60/120m horizons
include no-Formal-Plan breakout events
```

## OPTIONAL ONLY IF NEAR-ZERO INCREMENTAL COST

```text
retain 1m candle volume + trade_count if already exposed and persistence extension is trivial
reuse already-available OI snapshot at event time if no new polling subsystem is required
```

## DEFER

```text
AUCTION live gate
Range Edge downrank
new Breakout entry modes
Breakout Probe
trade-level Event-Time engine
continuous OI history
continuous 1m/tick/L2
OFI/CVD/queue/microprice/resiliency
new ML/change-point/Hawkes systems
```

---

# I. Engineering Acceptance-Cost Rule

Because current PR78 has already reached exact-head CI / independent acceptance, any current-release evidence addition must include not only coding hours but also:

```text
HEAD movement
new exact-head CI
regression tests
independent review / acceptance reset
launch-delay risk
rollback impact
```

A feature that is locally “small” but materially reopens acceptance is not operationally small.

---

# J. Evidence Sources / Research Position

External evidence supports the **research questions**, not production rules:

- Cont, Kukanov & Stoikov — order-flow imbalance and inverse-depth price impact;
- Gould & Bonart — queue imbalance as short-horizon predictor;
- Tóth et al. — persistent order flow / order splitting;
- Bouchaud and related impact literature — transient/persistent price impact distinction;
- LOB resiliency literature — depth/spread/replenishment after liquidity shocks;
- business/event-time literature — activity-time vs calendar-time representations;
- Opening Range Breakout literature — breakout profitability is regime/sample dependent, not universally stable;
- recent exploratory QQQ retest work — time-to-retest and pre-retest excursion are useful hypotheses, not validated production rules;
- Hyperliquid official docs — price-time-priority book, candle volume/trade count, public trades/L2 streams, asset contexts including OI, bounded recent candle API history and separate historical archives.

Theory / literature labels must remain distinct from `EMPIRICAL_RESULT` and `SHADOW_VALIDATED_RULE`.

---

# K. Authority Boundary

本文件不授权代码修改、依赖安装、数据订阅购买、PR78 mutation、部署、重启、账户访问、签名、交易所写入、自动交易、PR Mark Ready 或 Merge。

任何 First Launch 前 Evidence addition 必须先由 Engineering 返回 exact incremental cost / changed files / schema impact / CI-reset / acceptance-reset / launch-delay risk，再由用户决定。