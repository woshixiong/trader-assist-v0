# First Launch 上线后策略研究与未来开发优先级路线 R2

**记录 ID：** `TA-FIRST-LAUNCH-POST-LAUNCH-STRATEGY-RESEARCH-DEV-ROADMAP-R2-2026-08-13`  
**日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `CURRENT POST-LAUNCH STRATEGY PRIORITY ROADMAP / NON-EXECUTABLE / NON-AUTHORIZING`  
**父级：** `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_SHADOW_EVIDENCE_BACKLOG_R1_2026-08-12.md`  
**作用：** 在不改变当前 Machine Strategy R1/R1.1 的前提下，综合 Strong Breakout / No-Retest、Auction/Market Microstructure、Scheduled Macro Event、Event Asset Selection 与既有研究 Backlog，形成下一阶段统一研究和开发排序。

---

## 1. 当前发布结论：策略逻辑零新增

当前发布继续固定：

```text
NEW_FORMAL_SETUP_THIS_RELEASE = 0
CURRENT_MACHINE_PARAMETER_CHANGE = 0
AUCTION_REGIME_LIVE_GATE_THIS_RELEASE = NO
NEW_BREAKOUT_ENTRY_MODE_THIS_RELEASE = NO
BREAKOUT_PROBE_THIS_RELEASE = NO
L2_OFI_STRATEGY_THIS_RELEASE = NO
MACRO_EVENT_LIVE_STRATEGY_THIS_RELEASE = NO
AUTO_TRADE_THIS_RELEASE = NO
```

当前正式三 Setup 不变：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST  # MICRO_FAST + STANDARD
RANGE_EDGE_REJECTION
```

Engineering 应继续完成当前路线，不得因本文件重新打开机器策略参数或扩大 First Launch 范围。

---

## 2. 对 Strong Breakout / No-Retest 的关键纠偏

Strong Breakout 并非当前完全未覆盖。

当前 Machine Strategy 已经具有：

```text
INITIAL_BREAKOUT
→ MICRO_FAST when Pullback Start has not occurred
→ STANDARD after Pullback Start
```

当前 Initial Breakout 已要求：

```text
close outside zone >= 0.15*A5_EVENT
body >= 0.50*A5_EVENT
CLV >= 0.70
volume >= 1.20*M20_EVENT
```

MICRO_FAST 已要求下一根后续闭合 5m 继续保持在 Zone 外并表现出 continuation，且 Chase Limit 为 `0.75*A5_EVENT`。

STANDARD 已包含 Deep Retest 与 25%–60% 的 Shallow Retest。

因此：

```text
NO_RETEST_STRONG_BREAKOUT_MAIN_VALUE_ALREADY_PARTIALLY_COVERED = YES
NEW_MOMENTUM_SETUP_REQUIRED_NOW = NO
```

真实剩余研究缺口主要是：

1. `MICRO_FAST` 等待下一根闭合 5m 是否系统性错过高质量 runaway；
2. 5m 内部 `MICRO_PULLBACK` 是否提供比现有 5m confirmation 更优的入场点；
3. 价格不回旧边界、但通过 1m 级别 outside micro-balance 完成的 `TIME_ACCEPTANCE` 是否有额外 edge；
4. 为降低 missed-runaway opportunity cost，`BREAKOUT_PROBE` 是否值得承担额外 false-breakout / slippage / execution complexity；
5. `>0.75 ATR` 的 missed valid breakout 是否应该继续合法地被放弃，而不是为了提高 capture rate 强行追价。

---

## 3. Auction Market Theory 的定位

建议保留以下研究/解释状态：

```text
BALANCE
EDGE_TEST
FAILED_AUCTION
ACCEPTED_BREAK
REBALANCE
```

但当前：

```text
AUCTION_REGIME = RESEARCH / ATTRIBUTION TAXONOMY
AUCTION_REGIME = NOT A LIVE HARD GATE
```

理由：该框架对三个 Setup 的统一解释非常清晰：

```text
BALANCE / EDGE REJECTION → RANGE_EDGE_REJECTION
FAILED_AUCTION           → SWEEP_RECLAIM
ACCEPTED_BREAK            → BREAKOUT CONTINUATION FAMILY
```

但 Auction/Market Profile 语言本身不能证明增量交易 edge。只有离线/Shadow 比较显示加入这些状态后，能够稳定提高 Net Expectancy、MFE/MAE、Drawdown 或 Signal Ranking，才进入新的 Strategy Contract。

`EDGE_TEST` 特别适合作为研究状态，因为 Range Edge Short 与 Breakout Long 在同一边界存在潜在方向冲突；但当前不因此重写 Range 或 Breakout 状态机。

---

## 4. RANGE_EDGE_REJECTION 当前结论

当前不降低其 Formal Signal 权限，也不改变参数。

研究假设：

```text
RANGE_EDGE_REJECTION_INFORMATION_STRENGTH
<
SWEEP_RECLAIM / ACCEPTED_BREAKOUT
```

原因是 Range Edge 交易发生时，市场尚未证明边界最终是 Reject 还是 Accept。

但该结论必须通过 Shadow Evidence 验证。

未来比较至少包括：

```text
Net Expectancy
Win Rate
MFE / MAE
Stop Rate
False Breakout Follow-on Rate
Range Age / Width
Edge Test → Reject / Accept Transition
```

结果可影响未来 Ranking / Confidence / Reference Size，但在证据出现前不改变当前 Setup。

---

## 5. Market Microstructure 的定位

原始研究支持以下机制作为可检验假设：

```text
SHORT-HORIZON PRICE CHANGE
≈ ORDER FLOW IMBALANCE × INVERSE AVAILABLE DEPTH
```

queue imbalance、order flow、addition/cancellation 和 book resiliency 在短周期内可能具有预测信息。

但这些结果主要来自传统股票 LOB，不能直接假定参数可迁移至 Hyperliquid。

因此：

```text
CANDLE / VOLUME / CURRENT BBO FIRST
L2 / OFI / QUEUE IMBALANCE LATER
```

第一阶段不得为了 OFI 建设高复杂度常驻 L2 基础设施。

---

## 6. 当前唯一值得考虑的本轮 Evidence 增量

策略逻辑保持零新增。

但需要 Engineering / Project Control 在不拖慢当前发布的前提下核验一个**不可恢复 Evidence 风险**：

```text
BREAKOUT_RESEARCH_1M_PATH_FOR_ALL_INITIAL_BREAKOUT_EVENTS
```

原因：当前 Formal Shadow Plan 才拥有 on-demand 1m Outcome；但未来研究 `MICRO_PULLBACK / TIME_ACCEPTANCE / MISSED_RUNAWAY` 时，恰恰需要研究那些没有产生 Formal Plan 的 Initial Breakout Event。

Hyperliquid 标准 candleSnapshot 只保留最近 5000 根 candle，因此长期以后无法依赖 API 无限制恢复历史 1m path。

优先方案：

```text
IF existing on-demand 1m collector can be reused with a bounded change
AND no new strategy decision logic
AND no material launch delay
THEN
  retain a bounded 1m post-breakout research path for qualified Initial Breakout Events
ELSE
  DEFER and make this the first post-launch evidence-collector task
```

不授权为了该研究建设全市场 continuous 1m/tick/L2 系统。

BBO/L2 的历史不可恢复性同样重要，但 Breakout Probe 的真实 execution research 当前尚未达到必须阻塞发布的程度，因此不要求本轮增加常驻 L2 归档。

---

## 7. 统一 Breakout Lifecycle Research Program

未来最高优先级研究不再把“失败突破”和“强突破无回踩”割裂研究，而是统一观察同一个底层 Breakout Event 生命周期。

样本至少分类：

```text
A. MICRO_FAST_SUCCESS
B. STANDARD_SUCCESS
C. MISSED_RUNAWAY_BREAKOUT
D. IMMEDIATE_BREAKOUT_FAILURE
E. DELAYED_FAILED_ACCEPTED_BREAKOUT
F. AMBIGUOUS / INSUFFICIENT_DATA
```

比较共同特征：

```text
breakout_body_atr
breakout_volume_ratio
CLV
breakout_distance_atr
outside_dwell
reclaim_latency
relative_strength
session
market / asset class
MFE / MAE
spread / slippage if available
```

以及 1m path 可得时：

```text
micro_pullback_depth
micro_balance_width
micro_balance_duration
time_to_acceptance
time_to_reentry
```

这样可以用同一数据同时回答：

1. Micro FAST 是否已经足够；
2. 是否需要 Micro Pullback / Time Acceptance；
3. 什么特征区分 Healthy Breakout 与 Failed Accepted Breakout；
4. 是否存在值得参与但当前被 Chase Limit 放弃的 runaway；
5. 是否有足够经济价值支持 Breakout Probe。

---

## 8. 未来 Entry Mode 决策

以下均为 `RESEARCH_ONLY`：

```text
PRICE_RETEST      # 当前 STANDARD 已覆盖主要价值
MICRO_PULLBACK    # 研究是否产生增量 edge
TIME_ACCEPTANCE   # 研究 outside 1m micro-balance
BREAKOUT_PROBE    # 最后才考虑
```

优先顺序：

```text
CURRENT MICRO_FAST / STANDARD BASELINE
→ MICRO_PULLBACK / TIME_ACCEPTANCE OFFLINE TEST
→ SHADOW TEST IF PROMISING
→ BREAKOUT_PROBE ONLY IF MISSED-RUNAWAY ECONOMICS JUSTIFY IT
```

`BREAKOUT_PROBE` 不得以 `boundary crossed → full-size market order` 实现。

如果未来进入研究，应先比较：

```text
NAKED BOUNDARY TRIGGER
BUFFERED TRIGGER
BUFFERED SMALL PROBE
BUFFERED PROBE + ACCEPTANCE ADD
```

并把 false-breakout loss、slippage、missed-runaway opportunity cost 一起计入。

---

## 9. Strong / False Breakout 的研究基线

第一阶段不要重新发明 Strong Breakout 定义。

使用当前 Initial Breakout 机器合同作为 baseline strength definition，再研究增量字段：

```text
CURRENT BASELINE:
body >= 0.50*A5_EVENT
close outside >= 0.15*A5_EVENT
CLV >= 0.70
volume >= 1.20*M20_EVENT

RESEARCH FEATURES:
displacement_atr
outside_dwell
reclaim_latency
micro_pullback_depth
micro_balance_duration
relative_strength
spread/slippage
```

False Breakout 同样优先复用当前：

```text
ACCEPTED_REENTRY
FAILED_BREAKOUT_SWEEP_WATCH
FAILED_ACCEPTED_BREAKOUT research labels
```

而不是创建第二套互相冲突的公式。

---

## 10. 未来统一优先级

### R1 — BREAKOUT LIFECYCLE OPTIMIZATION

最高优先。

包含两个并行子问题：

```text
R1A = FAILED_ACCEPTED_BREAKOUT / FAILED_IMPULSE
R1B = STRONG / NO-RETEST BREAKOUT COVERAGE AUDIT
```

R1B 先验证现有 MICRO_FAST 的 coverage，只有存在显著增量价值时才研究：

```text
MICRO_PULLBACK
TIME_ACCEPTANCE
```

`BREAKOUT_PROBE` 属于 R1 的后段条件分支，不是前置开发。

### R2 — PER_MARKET_STABLE_TIMEFRAME_PROFILE

延续现有 Backlog。先离线比较 FAST_5M 与更慢 Profile；不得实时动态切换。

### R3 — SECTOR / PEER RELATIVE STRENGTH

优先作为 Ranking / Attribution，不作为 Hard Gate。

### R4 — SCHEDULED MACRO EVENT + EVENT ASSET ROUTER

继续使用既有 Scheduled U.S. Macro 子合同，初始 CPI / NFP / PCE。

新增明确研究问题：

```text
MACRO INTERPRETATION ASSET != TRADE ASSET
```

研究：

```text
US2Y / DXY / NQ / ES as interpreters
INDEX / HIGH-BETA SECTOR / BTC / ETH as candidate trade expressions
EVENT_RELATIVE_STRENGTH
IMPULSE_RETENTION
PRICE_ACCEPTANCE
EXECUTION QUALITY
IDIOSYNCRATIC_CATALYST_RISK
```

目标是未来形成 `EVENT ASSET ROUTER`，而不是默认每次 CPI/NFP 都交易 ETH 或任意固定资产。

### R5 — CASH OPEN / OPENING REPRICING

研究 Premarket Trend → Cash Open Continuation / Failure。

### R6 — LOGICAL INVALIDATION EXIT

比较结构提前失效 vs 当前 Hard Stop。

### R7 — POSITION ENTRY SCALING / PROBE→ADD

包括一般 Probe→Add；若 R1 证明 Breakout Probe 有价值，也在这一阶段进入真正多腿执行设计。

### R8 — CROSS-MARKET CONFIRMATION SOFT SCORE

只做 Context / Ranking，不做 Hard Gate。

### R9 — ADVANCED L2 / OFI / BOOK RESILIENCY

只有当低成本 price/volume/BBO evidence 已证明某个明确问题值得进一步区分时，才加入：

```text
aggressive buy/sell volume
CVD
OFI
queue imbalance
multi-level OFI
cancellation / replenishment
book resiliency
```

不得为了理论完整性提前建设。

---

## 11. 开发数量与产品边界

本路线当前识别：

```text
CURRENT RELEASE NEW STRATEGY FEATURES = 0
POST-LAUNCH RESEARCH / DEVELOPMENT STREAMS = 9
NEW FORMAL SETUP COMMITTED = 0
```

未来多数项目应优先实现为：

```text
Existing Setup Extension
Entry Mode
Research Label
Ranking Feature
Regime / Attribution
Execution Rule
Asset Router
```

而不是 New Setup。

---

## 12. Replay / Shadow 最小实验矩阵

Breakout 研究建议：

```text
A = CURRENT THREE-SETUP BASELINE
B = A + AUCTION LABELS (offline attribution only)
C = B + MICRO_PULLBACK / TIME_ACCEPTANCE HYPOTHETICAL ENTRIES
D = C + BREAKOUT PROBE HYPOTHETICAL EXECUTION
E = D + L2 / OFI only if prior stages justify
```

核心比较：

```text
signal count
capture rate
missed-runaway rate
false-breakout rate
win rate
expectancy
profit factor
MFE / MAE
stop rate
time to MFE
entry distance from boundary
net R
fee / slippage
30m / 60m / 120m outcome
```

必须按：

```text
market
asset class
session
volatility
liquidity
range age / width
breakout velocity / distance
correlation cluster
```

切片，并使用 cluster-normalized 主统计。

---

## 13. 当前明确不做

```text
NO FOURTH SETUP
NO MACHINE PARAMETER CHANGE
NO AUCTION_REGIME HARD GATE
NO RANGE_EDGE LIVE DOWNRANK
NO NEW MOMENTUM SETUP
NO IMMEDIATE DISPLACEMENT LIVE ENTRY
NO BREAKOUT PROBE LIVE ENTRY
NO MULTI-LEG POSITION ENGINE
NO CONTINUOUS FULL-UNIVERSE 1m
NO CONTINUOUS FULL-UNIVERSE L2
NO OFI / CVD / QUEUE ENGINE
NO MACRO AUTO-TRADING
NO EVENT ASSET ROUTER LIVE IMPLEMENTATION
NO CROSS-MARKET HARD GATE
```

---

## 14. 研究证据来源原则

理论只负责提出可证伪 hypothesis。

当前使用的外部研究方向包括：

- Cont, Kukanov & Stoikov — *The Price Impact of Order Book Events*；
- Gould & Bonart — *Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book*；
- Tóth et al. — *Why is Order Flow so Persistent?*；
- LOB resiliency / replenishment empirical literature；
- Holmberg, Lönnbark & Lundström — intraday Opening Range Breakout empirical work；
- recent exploratory QQQ breakout/retest work，仅作为 hypothesis source，不作为 production authority；
- Hyperliquid official Order Book / Order Types / TP-SL / WebSocket / Info API documentation。

Wyckoff / Market Profile / Auction Market Theory / SMC 可以用于描述和产生研究假设，但不得因为叙事合理直接成为机器参数。

---

## 15. 最终冻结状态

```text
LET_CURRENT_ENGINEERING_SHIP = YES
CURRENT_STRATEGY_DELTA = ZERO

BREAKOUT_LIFECYCLE_RESEARCH = NEW_HIGHEST_PRIORITY_UMBRELLA
FAILED_ACCEPTED_BREAKOUT_REMAINS_TOP_PRIORITY = YES
STRONG_NO_RETEST_COVERAGE_AUDIT = TOP_PRIORITY_PARALLEL_SUBTRACK

AUCTION_REGIME = RESEARCH_ONLY
RANGE_EDGE_DOWNRANK = RESEARCH_ONLY
MICRO_PULLBACK = RESEARCH_ONLY
TIME_ACCEPTANCE = RESEARCH_ONLY
BREAKOUT_PROBE = RESEARCH_ONLY_CONDITIONAL
L2_OFI = LATE_STAGE_CONDITIONAL

POST_LAUNCH_STREAM_COUNT = 9
NEW_FORMAL_SETUP_COMMITTED = 0
```

本文件不授权代码修改、依赖安装、数据订阅购买、部署、重启、permit 修改、账户访问、签名、交易所写入、自动下单、Mark Ready 或 Merge。