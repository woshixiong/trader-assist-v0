# First Launch 日内入场策略回测前冻结 R5

**记录 ID：** `TA-FIRST-LAUNCH-INTRADAY-ENTRY-STRATEGY-PRE-BACKTEST-FREEZE-R5-2026-08-02`  
**日期：** `2026-08-02`  
**状态：** `PRE-BACKTEST FREEZE / RESEARCH ONLY / NON-PRODUCTION / NON-DEPLOYMENT`  
**关联：** PR #52、三 Setup R1/R1.1/R1.2、Pre-Backtest R2/R3/R4、Research Playbook V4、Position Management R2  
**优先级：** 本文件取代与其冲突的 R2/R3/R4。  
**权限边界：** 允许形成回测工程任务包，不授权生产代码修改、部署、账户访问、交易所写入或自动下单。

---

## 1. 最终交易目标

```text
CONTEXT_TIMEFRAME = 1h
PRIMARY_STRUCTURE_TIMEFRAME = 15m
EXECUTION_TIMEFRAME = 5m
MICRO_TIMEFRAME = 1m/3m OPTIONAL_PATH_EVIDENCE_ONLY
TRADING_HORIZON = INTRADAY
HOLDING_TIME = PATH_DEPENDENT_NOT_FIXED
ENTRY_FIRST = YES
INITIAL_STRUCTURAL_STOP_REQUIRED = YES
MINIMUM_REFERENCE_OPPORTUNITY = APPROX_1R_AFTER_COSTS
HUMAN_FINAL_AUTHORITY = YES
REALTIME_DYNAMIC_EXIT_ENGINE = OUT_OF_SCOPE
```

本轮只优化和回测：

- 1h 背景标签及其增量价值；
- 15m 关键价格带；
- 5m 入场确认；
- Sweep、Breakout、Range；
- FAST / STANDARD；
- 初始结构止损、Chase Limit；
- 参考止盈与影子退出；
- 趋势分段重新入场。

---

## 2. 最高优先级因果原则

```text
DECISION_INPUT = CLOSED_AND_RECEIVED_FACTS_ONLY
LOOKAHEAD = PROHIBITED
FUTURE_PATH_ASSUMPTION = PROHIBITED
TIME_TO_COMPLETION_FORECAST = PROHIBITED
FIXED_TIME_AS_ECONOMIC_INVALIDATION = PROHIBITED
```

波动率只用于归一化、观察尺度、已发生速度/幅度分类和结果分层；不得预测行情将在多少分钟或多少根 K 线后完成。

STANDARD、Sweep 和趋势延续状态必须由价格事实推进或失效，不得因经过固定 N 根 K 线自动失效。

---

## 3. Signal Authority 与 1h 背景

```text
SIGNAL_AUTHORITY = SETUP_OBSERVED_FACTS
HTF_ROLE = CONTEXT_LABEL + ATTRIBUTION + POST_BACKTEST_POLICY
FIRST_BACKTEST_HTF_HARD_FILTER = NONE
```

只要 Setup 自身成立、5m/15m 数据有效、Entry/Stop/Chase/Target Feasibility 可定义，候选就进入第一轮回测。

不得因以下原因预先删除：

- 与 1h 方向相反；
- 1h 中性；
- 1h 转换；
- 动量和结构冲突；
- 只有 1h 背景暂时不可用。

---

## 4. 1h 双标签定义

### 4.1 动量标签主候选

只使用闭合 1h K 线：

```text
A1H = Wilder ATR14 on closed 1h candles
ER8_1H = abs(C[-1]-C[-9]) / sum(abs(C[i]-C[i-1]), last 8 closed bars)
D8_1H = (C[-1]-C[-9]) / A1H
```

第一轮候选：

```text
HTF_MOMENTUM_UP:
ER8_1H >= 0.35 AND D8_1H >= 0.75

HTF_MOMENTUM_DOWN:
ER8_1H >= 0.35 AND D8_1H <= -0.75

HTF_MOMENTUM_NEUTRAL:
data ready and neither directional state

HTF_MOMENTUM_UNAVAILABLE:
insufficient or unavailable 1h context
```

这些阈值是回测候选，不是生产结论。

### 4.2 价格结构标签主候选

使用三 K 线局部 Pivot，只有右侧 1h K 线闭合并已收到后才确认：

```text
pivot_high_i = high_i > high_i-1 AND high_i >= high_i+1
pivot_low_i  = low_i  < low_i-1  AND low_i  <= low_i+1
```

使用最近两个已确认 swing high 和 swing low：

```text
HTF_STRUCTURE_UP:
HH AND HL

HTF_STRUCTURE_DOWN:
LH AND LL

HTF_STRUCTURE_RANGE:
high/low structure does not progress directionally and remains bounded

HTF_STRUCTURE_TRANSITION:
one side progresses while the other conflicts, or prior structure is causally broken

HTF_STRUCTURE_INSUFFICIENT:
not enough confirmed swings

HTF_STRUCTURE_UNAVAILABLE:
1h context unavailable
```

第一轮不得用结构标签作为硬过滤器。

### 4.3 交易方向关系标签

```text
HTF_ALIGNED_STRONG
HTF_ALIGNED_PARTIAL
HTF_COUNTERTREND_STRONG
HTF_COUNTERTREND_PARTIAL
HTF_CONFLICTED
HTF_NEUTRAL
HTF_CONTEXT_INCOMPLETE
```

定义：

- 动量与结构均同向：`ALIGNED_STRONG`；
- 一项同向，另一项中性/不足：`ALIGNED_PARTIAL`；
- 两项均反向：`COUNTERTREND_STRONG`；
- 一项反向，另一项中性/不足：`COUNTERTREND_PARTIAL`；
- 动量与结构方向互相冲突：`CONFLICTED`；
- 两项均无明确方向：`NEUTRAL`；
- 1h 背景不足或不可用：`CONTEXT_INCOMPLETE`。

所有标签全部进入回测。

---

## 5. 数据质量合同

### 5.1 正常市场不确定

```text
HTF_NEUTRAL | HTF_TRANSITION | HTF_CONFLICTED
SIGNAL_GENERATION = YES
DATA_QUALITY = READY
```

### 5.2 只有 1h 背景不可用

```text
DATA_5M = READY
DATA_15M = READY
DATA_1H = UNAVAILABLE
SIGNAL_GENERATION = YES
HTF_RELATION = CONTEXT_INCOMPLETE
```

不得自动降低仓位、风险或信号等级；只记录标签并回测。

### 5.3 核心时间轴或 5m/15m 数据无效

```text
MULTITIMEFRAME_DATA_INVALID
ACTIONABLE_SIGNAL = NO
RAW_CANDIDATE_AND_ERROR_EVIDENCE = RETAINED
```

---

## 6. 15m 关键价格带主候选

### 6.1 数据与窗口

```text
A5  = Wilder ATR14 on closed 5m candles
A15 = Wilder ATR14 on closed 15m candles
M20 = median volume of previous 20 closed 5m candles
ZONE_LOOKBACK_15M_PRIMARY = 96 closed bars
ZONE_LOOKBACK_15M_SENSITIVITY = 64 closed bars
```

### 6.2 因果 Pivot、聚类与反应

```text
pivot_high_i = high_i > high_i-1 AND high_i >= high_i+1
pivot_low_i  = low_i  < low_i-1  AND low_i  <= low_i+1
CLUSTER_DISTANCE <= max(0.20*A15, 2*spread_price)
MIN_REACTION_SEPARATION = 2 closed 15m bars
REACTION_MOVE_AWAY >= 0.50*A15 using already-closed future reaction bars
```

### 6.3 Zone 几何

```text
ZONE_CENTER = median(reaction_prices)
RAW_HALF_WIDTH = max(1.5*MAD(reaction_prices), 0.15*A15)
ZONE_HALF_WIDTH = clamp(RAW_HALF_WIDTH, 0.15*A15, 0.40*A15)
ZONE_WIDTH = 0.30*A15 ... 0.80*A15
```

### 6.4 Zone Quality

```text
ZQ1 = 1 independent reaction
ZQ2 = >=2 reactions AND latest age <=24 closed 15m bars
ZQ3 = >=3 reactions AND latest age <=24 closed 15m bars
```

P1 Setup 要求 `ZQ2+`；ZQ3 用于排序和归因。

---

## 7. 状态路由

```text
RECLAIMED_INSIDE              → SWEEP
ACCEPTED_OUTSIDE_ORDERLY      → MICRO_FAST or STANDARD
ACCEPTED_OUTSIDE_DISPLACEMENT → IMMEDIATE_FAST
AMBIGUOUS_TWO_SIDED           → WATCH / NO_ACTION
```

`AMBIGUOUS_TWO_SIDED`、数据冲突和同一事件重复候选必须保留证据，但不能产生重复 TradePlan。

---

## 8. Sweep P1：事实确认型 Reclaim

以下以向下扫支撑后做多为例，做空镜像。

候选起点：

```text
ZONE_QUALITY >= ZQ2
outside_excursion >= 0.10*A5
accepted reclaim inside zone >= 0.05*A5
```

状态继续存在，只要：

```text
reclaim remains accepted inside zone
AND sweep extreme is not validly broken
AND no opposite breakout is confirmed
AND entry remains within Chase Limit
AND target feasibility remains >=1R after costs
AND data remains valid
```

确认必须来自已经发生的事实，例如：

```text
higher_low / lower_high
OR renewed inward progress
OR causal close that preserves reclaim and advances toward zone interior
```

止损与追价：

```text
STOP = sweep_extreme -/+ 0.10*A5
MAX_CHASE_FROM_ZONE_EDGE = 0.35*A5
```

Same-bar Sweep FAST 为 P2 独立候选。

---

## 9. Breakout P1-A：Micro-confirmed FAST

初始突破以向上为例：

```text
close >= ZONE_HIGH + 0.15*A5
BODY_A5 >= 0.50
CLV >= 0.70
volume >= 1.20*M20
```

确认不是固定等待时间，而是下一项已发生的带外接受事实：

```text
price remains accepted outside old zone
AND does not obtain accepted re-entry
AND produces renewed directional progress or causal higher-low/lower-high structure
AND remains within Chase Limit
```

Immediate Displacement FAST 为 P2，必须独立统计。

---

## 10. Breakout P1-B：状态驱动 STANDARD

删除“突破后 1–6 根 5m 内必须完成”的主候选限制。

### 10.1 PREPARE 继续存在

```text
no accepted re-entry into old zone
AND no opposite confirmed Setup
AND no newer independent event supersedes the original event
AND current executable price remains within Chase Limit
AND target feasibility remains >=1R after costs
AND causal data quality remains valid
```

### 10.2 深回踩确认

```text
price revisits zone edge or partially enters zone
AND does not obtain accepted re-entry
AND closes back outside in breakout direction
AND forms renewed directional evidence
```

### 10.3 浅回踩确认

```text
price remains outside old zone
AND retraces part of prior impulse
AND forms higher low / lower high or equivalent causal structure
AND resumes directional progress
```

### 10.4 事实失效

```text
accepted re-entry into old zone
opposite confirmed event
new independent structure supersedes original event
entry exceeds Chase Limit
target space falls below 1R after costs
data quality or causal alignment failure
```

固定 `1–6 bar` 只作为 P0 Comparator。

---

## 11. Range P1：边缘拒绝

Range 交易不使用 1h 硬过滤。

```text
RANGE_VALID_EDGES = BOTH_SIDES
HTF_CONTEXT = ATTRIBUTION_ONLY
```

基本要求：

```text
upper_zone >= ZQ2
lower_zone >= ZQ2
range remains structurally bounded
entry occurs at qualified edge rejection/reclaim
initial stop is outside event extreme/zone
space_to_range_center >=1R after costs
```

上下两侧全部生成并按 HTF 标签分层。

---

## 12. 趋势分段重新入场

同一 1h/15m 趋势允许多个独立 TradePlan：

```text
initial signal
→ favorable segment
→ exit or structural interruption
→ new pullback / new zone / new market event
→ new causal continuation signal
→ independent re-entry
```

每次重新入场必须有新的：

```text
market_event_id
entry
structural_stop
planned_risk
chase_limit
target_context
outcome
```

必须去重同一事件，但不得屏蔽后续独立趋势段。

---

## 13. 候选优先级

### P0 Comparator

```text
V0_1_EXACT_BASELINE
FIXED_1_TO_6_BAR_STANDARD_COMPARATOR
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
DONCHIAN_TURTLE_BREAKOUT_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

### P1 Primary

```text
ZONE_MODEL_R5
HTF_DUAL_LABEL_R5
SWEEP_FACT_CONFIRMED_RECLAIM_R5
BREAKOUT_MICRO_CONFIRMED_FAST_R5
BREAKOUT_STATE_DRIVEN_STANDARD_R5
RANGE_EDGE_REJECTION_R5
TREND_SEGMENT_REENTRY_R5
```

### P2 Secondary / Sensitivity

```text
BREAKOUT_IMMEDIATE_DISPLACEMENT_FAST
SWEEP_SAME_BAR_FAST
PIN_BAR_QUALITY_FILTER
SHALLOW_VS_DEEP_RETEST
ZONE_LOOKBACK_64
30M_CONFIRMATION_SCALE
```

### P3 Deferred evidence

```text
VOLUME_PROFILE_HVN_LVN_POC
OI_FUNDING_CONTEXT
L2_DEPTH_ORDER_FLOW
REALTIME_DYNAMIC_EXIT
```

P3 不得阻塞第一轮。

---

## 14. 影子退出回测

当前不开发实时退出引擎，但每个信号必须尽量评估：

```text
initial structural stop
1R / 1.5R / 2R reference
next structural zone
30/60/120m MFE and MAE
time to 1R
maximum favorable excursion before stop
maximum profit giveback
profit-to-entry giveback
fixed-R outcomes
structure-target outcome
simple break-even/profit-lock outcome
simple structure-trailing outcome
no-progress and reversal-exit shadow labels
hold-through-trend vs segmented re-entry comparison
```

同一 5m K 线同时触及 Stop 和 Target：优先使用 1m 路径；1m 仍歧义时标记 `AMBIGUOUS_PATH`，主结果采用保守 `STOP_FIRST`，同时报告歧义数量。

---

## 15. 第一轮 HTF 后验政策比较

所有原始有效信号先完整回测，再基于相同结果比较：

```text
POLICY_ALL
POLICY_MOMENTUM_ALIGNED
POLICY_STRUCTURE_ALIGNED
POLICY_CONSENSUS_ALIGNED
POLICY_ALIGNED_OR_NEUTRAL
POLICY_SETUP_SPECIFIC
```

不得重新生成不同事件集来掩盖被过滤样本。

---

## 16. 第一轮必须回答

1. 1h 动量和价格结构各自是否提供增量价值；
2. 顺势、逆势、中性、冲突、背景缺失信号在不同 Setup 和波动状态下的表现；
3. Range 是否几乎不需要 HTF 过滤；
4. 状态驱动 STANDARD 比固定 1–6 bar 少漏掉多少慢趋势；
5. Micro FAST 与 Immediate FAST 的差异；
6. 深回踩、浅回踩和趋势分段重新入场的贡献；
7. 约 1R 可行性门槛是否适合日内机会；
8. 影子退出字段能否支持未来动态退出研究。

结果必须至少按：

```text
setup
× side
× confirmation_mode
× HTF_momentum_state
× HTF_structure_state
× HTF_relation
× volatility_state
× first_entry_or_reentry
× exact_or_proxy
```

分层，同时提供汇总，禁止用汇总掩盖负单元。
