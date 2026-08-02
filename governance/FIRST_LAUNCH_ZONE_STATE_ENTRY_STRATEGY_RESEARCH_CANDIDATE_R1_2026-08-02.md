# First Launch 价格带、状态分流与入场策略第一轮研究候选 R1

**记录 ID：** `TA-FIRST-LAUNCH-ZONE-STATE-ENTRY-RESEARCH-CANDIDATE-R1-2026-08-02`  
**日期：** `2026-08-02`  
**状态：** `RESEARCH CANDIDATE / PRE-BACKTEST / NON-EXECUTABLE / NON-DEPLOYMENT`  
**关联：** PR #52、三 Setup R1/R1.1/R1.2、Scanner Lite R3、外部价格行为研究、Position Management R2  
**权限边界：** 本文只记录第一轮研究候选参数，不覆盖既有生产合同，不授权代码修改、回测执行、任务派发、部署、账户访问、交易所写入或自动下单。

---

## 1. 研究目标

当前研究只解决四件事：

1. 怎样把单一价格线升级为 15m 关键价格带；
2. 价格攻击并离开价格带后，怎样区分收回、平稳接受、猛烈位移和双向歧义；
3. Sweep、Breakout FAST、Breakout STANDARD 和 Range 的第一轮入场参数；
4. 入场时的结构止损、参考目标和影子退出证据。

固定交易模式：

```text
PRIMARY_STRUCTURE_TIMEFRAME = 15m
EXECUTION_TIMEFRAME = 5m
MICRO_TIMEFRAME = 1m/3m OPTIONAL_RESEARCH_EVIDENCE_ONLY
HUMAN_FINAL_DECISION = YES
MANUAL_EXECUTION = YES
REALTIME_DYNAMIC_EXIT_ENGINE = OUT_OF_SCOPE
```

---

## 2. 外部研究采用原则

外部研究支持以下机制，但不证明本文件参数在 ETH 或 Hyperliquid 上有效：

- 历史反应次数和新鲜度可提高支撑阻力区域的解释力；
- 止损在可观察技术位置聚集后可能形成价格级联；
- 日内突破效果依赖波动状态和时段；
- 短周期价格变化与订单流失衡及市场深度的关系通常比总成交量更直接；
- Volume/Market Profile 边界本身不保证突破延续，回踩深度和退出方法可能显著影响结果。

因此：

```text
EXTERNAL_MECHANISM_REUSE = YES
EXTERNAL_PARAMETER_COPY = NO
FIRST_ROUND_PARAMETERS = TESTABLE_HYPOTHESES
```

---

## 3. 共同数据定义

```text
A5  = Wilder ATR14 on closed 5m candles
A15 = Wilder ATR14 on closed 15m candles
M20 = median volume of previous 20 closed 5m candles
CLV = (close - low) / max(high - low, minimum_tick)
BODY_A5 = abs(close - open) / A5
TR_A5 = true_range / A5
ER3 = abs(close_t - close_t-3) / sum(abs(close_i-close_i-1), last 3 bars)
ER6 = same definition over 6 closed 5m bars
```

最低启动历史：

```text
MIN_5M_HISTORY = 288 bars
MIN_15M_HISTORY = 64 bars
```

所有决策只使用决策时已经闭合并到达的数据。

---

## 4. 15m 关键价格带候选模型

### 4.1 Lookback

```text
ZONE_LOOKBACK_15M = 64 closed bars
```

即约 16 小时，只用于第一轮日内研究。

### 4.2 因果 Pivot

使用三 K 线局部极值：

```text
pivot_high_i = high_i > high_i-1 AND high_i >= high_i+1
pivot_low_i  = low_i  < low_i-1  AND low_i  <= low_i+1
```

Pivot 只有在 `i+1` 闭合后才成为可用证据。

### 4.3 价格聚类

同方向 pivot 或反应价格满足：

```text
CLUSTER_DISTANCE <= max(0.20 * A15, 2 * current_spread_price)
```

归入同一候选带。

### 4.4 独立反应

两个反应至少间隔：

```text
MIN_REACTION_SEPARATION = 2 closed 15m bars
```

一次反应在进入候选区域后，未来已经闭合的 1–3 根 15m 中至少离开该区域：

```text
REACTION_MOVE_AWAY >= 0.50 * A15
```

### 4.5 Zone 几何

```text
ZONE_CENTER = median(reaction_prices)
RAW_HALF_WIDTH = max(1.5 * MAD(reaction_prices), 0.15 * A15)
ZONE_HALF_WIDTH = clamp(RAW_HALF_WIDTH, 0.15 * A15, 0.40 * A15)
ZONE_LOW  = CENTER - HALF_WIDTH
ZONE_HIGH = CENTER + HALF_WIDTH
```

因此第一轮 zone 总宽度限制为：

```text
0.30 * A15 <= ZONE_WIDTH <= 0.80 * A15
```

### 4.6 Zone Quality

```text
ZQ1 = 1 independent reaction
ZQ2 = >=2 reactions AND latest reaction age <=24 closed 15m bars
ZQ3 = >=3 reactions AND latest reaction age <=24 closed 15m bars
```

正式三 Setup 第一轮要求：

```text
ZONE_QUALITY >= ZQ2
```

ZQ3 作为排序和归因标签，不设为首轮硬门槛。

### 4.7 Volume Profile

Volume Profile / Value Area / POC / HVN / LVN 第一轮作为：

```text
SHADOW_FEATURE_AND_TARGET_CONTEXT
```

不作为硬入场门槛，直到历史构建方式、binning、因果 cutoff 和跨市场一致性通过验证。

最低记录：

```text
ZONE_OVERLAPS_HVN
ZONE_NEAR_VALUE_AREA_EDGE
NEXT_HVN_DISTANCE
LVN_CORRIDOR_WIDTH
```

---

## 5. 波动压缩标签

压缩不预测方向，只作为位移 FAST 的前置质量证据。

```text
SHORT_TR_MEDIAN = median(TR of last 6 closed 5m)
LONG_TR_MEDIAN  = median(TR of previous 24 closed 5m)
COMPRESSION_RATIO = SHORT_TR_MEDIAN / LONG_TR_MEDIAN
RANGE_12_A5 = (highest_high_12 - lowest_low_12) / A5
```

首轮标签：

```text
COMPRESSION =
COMPRESSION_RATIO <= 0.70
AND RANGE_12_A5 <= 2.00
```

至少持续：

```text
MIN_COMPRESSION_DURATION = 9 closed 5m bars
```

Compression 不是 Sweep、STANDARD 或 Range 的硬门槛。

---

## 6. 价格带攻击后的四状态

### 6.1 RECLAIMED_INSIDE

价格穿越外侧至少：

```text
PENETRATION >= 0.10 * A5
```

并在同一根或随后两根 5m 内重新收回价格带至少：

```text
CLOSE_INSIDE_DEPTH >= 0.05 * A5
```

路由到 `SWEEP_RECLAIM`。

### 6.2 ACCEPTED_OUTSIDE_DISPLACEMENT

方向镜像，Long 条件：

```text
close >= ZONE_HIGH + 0.30*A5
BODY_A5 >= 0.80
CLV >= 0.80
TR_A5 >= 1.20
volume >= 1.50*M20
ER3 >= 0.65
```

并且至少满足一项：

```text
COMPRESSION = true
OR
(BODY_A5 >= 1.20 AND volume >= 2.00*M20)
```

路由到 `BREAKOUT_DISPLACEMENT_FAST`。

### 6.3 ACCEPTED_OUTSIDE_ORDERLY

初始 Long 条件：

```text
close >= ZONE_HIGH + 0.15*A5
BODY_A5 >= 0.50
CLV >= 0.70
volume >= 1.20*M20
```

后续 3 根闭合 5m 中至少 2 根保持在 zone 外：

```text
close >= ZONE_HIGH + 0.05*A5
```

同时：

```text
0.40 <= ER6 <= 0.80
no single TR_A5 > 1.80
```

路由到 `BREAKOUT_MICRO_CONFIRMED_FAST` 或 `BREAKOUT_STANDARD_RETEST`。

### 6.4 AMBIGUOUS_TWO_SIDED

任一成立：

- 3 根 5m 内价格攻击同一结构的两侧；
- 3 根 5m 内在 zone 内外来回闭合两次以上；
- 同一根 K 线同时形成有效双侧候选；
- 数据、时间或价格身份冲突。

结果：

```text
WATCH_OR_NO_ACTION
```

---

## 7. SWEEP_RECLAIM 第一轮参数

Long/Short 镜像。

### 7.1 Event domain

```text
ZONE_QUALITY >= ZQ2
0.10*A5 <= outside_penetration <= 0.75*A5
reclaim occurs within same or next 2 closed 5m bars
close >= ZONE_LOW + 0.05*A5 for Long
CLV >= 0.65 for Long
```

### 7.2 FAST Sweep

同一根 5m 完成穿越和收回：

```text
CLV >= 0.75
volume >= 1.20*M20
```

### 7.3 STANDARD Sweep

1–2 根 5m 内收回，并满足：

```text
confirmation close remains inside zone
AND
(higher low for Long OR confirmation close > reclaim close)
```

成交量不是 STANDARD 硬门槛，但必须记录。

### 7.4 Pin Bar quality tag

只作为高质量标签和人工参考：

```text
rejection_wick / max(body, minimum_tick) >= 2.0
rejection_wick / candle_range >= 0.55
CLV >= 0.70 for Long
volume >= 1.20*M20
```

### 7.5 Entry / Stop / Chase

Long：

```text
ENTRY_ZONE = [ZONE_LOW, ZONE_LOW + 0.10*A5]
STRUCTURAL_STOP = sweep_extreme - 0.10*A5
CHASE_LIMIT = ZONE_LOW + 0.35*A5
```

### 7.6 Reference target feasibility

```text
R = planned_entry - structural_stop
reserve = max(0.10*A5, round_trip_cost)
require distance_to_zone_center >= 1.0*R + reserve
```

Zone opposite edge、1.5R、2R 仅作为扩展参考。

---

## 8. BREAKOUT_RETEST 三种第一轮模式

每个模式必须独立统计，不能合并补样本。

### 8.1 DISPLACEMENT_FAST_IMMEDIATE

使用 `ACCEPTED_OUTSIDE_DISPLACEMENT` 条件。

Long：

```text
ENTRY_ZONE = [ZONE_HIGH + 0.25*A5, ZONE_HIGH + 0.45*A5]
CHASE_LIMIT = ZONE_HIGH + 0.60*A5
STRUCTURAL_STOP = min(breakout_low - 0.05*A5, ZONE_HIGH - 0.20*A5)
OUTPUT_EXPIRY = 180 seconds
```

必须显示：

```text
NO_RETEST_FAST
HIGH_FALSE_BREAKOUT_RISK
```

### 8.2 MICRO_CONFIRMED_FAST

初始触发：

```text
close >= ZONE_HIGH + 0.15*A5
BODY_A5 >= 0.50
CLV >= 0.70
volume >= 1.20*M20
```

等待下一根闭合 5m：

```text
confirmation_close >= ZONE_HIGH + 0.10*A5
confirmation_low >= ZONE_HIGH - 0.10*A5
```

并满足至少一项：

```text
confirmation_close > breakout_close
OR
confirmation_low > breakout_low
```

Long：

```text
ENTRY_ZONE = [ZONE_HIGH + 0.05*A5, ZONE_HIGH + 0.25*A5]
CHASE_LIMIT = ZONE_HIGH + 0.50*A5
STRUCTURAL_STOP = min(confirmation_low - 0.10*A5, ZONE_HIGH - 0.20*A5)
OUTPUT_EXPIRY = 600 seconds
```

### 8.3 STANDARD_RETEST

初始触发与 Micro-confirmed FAST 相同。

回踩窗口：

```text
RETEST_WINDOW = 1_TO_6_CLOSED_5M_BARS
```

#### Deep retest

```text
retest_low ∈ [ZONE_HIGH - 0.15*A5, ZONE_HIGH + 0.25*A5]
confirmation_close >= ZONE_HIGH + 0.05*A5
```

#### Shallow retest

没有触及 zone，但：

```text
retracement_of_breakout_impulse between 25% and 60%
retest_low > ZONE_HIGH
AND
next closed 5m forms higher low or closes above retest high
```

Long：

```text
ENTRY_ZONE = [ZONE_HIGH - 0.05*A5, ZONE_HIGH + 0.20*A5]
CHASE_LIMIT = ZONE_HIGH + 0.50*A5
STRUCTURAL_STOP = min(retest_low - 0.10*A5, ZONE_HIGH - 0.20*A5)
OUTPUT_EXPIRY = 900 seconds
```

#### Invalidation

```text
close <= ZONE_HIGH - 0.20*A5
OR retest window expired
OR opposite confirmed breakout
OR data quality not READY
```

### 8.4 Breakout reference target feasibility

```text
R = abs(planned_entry - structural_stop)
reserve = max(0.10*A5, round_trip_cost)
```

若存在下一结构带：

```text
distance_to_next_zone >= 1.0*R + reserve
```

若不存在：

```text
NO_KNOWN_STRUCTURAL_OBSTACLE = PASS_WITH_FLAG
```

同时输出 1R、1.5R、2R 和 next-zone 参考，不强制固定止盈。

---

## 9. RANGE_EDGE_REJECTION 第一轮参数

### 9.1 Range structure

使用最近 24 根闭合 15m：

```text
RANGE_LOOKBACK = 24 bars
upper_zone quality >= ZQ2
lower_zone quality >= ZQ2
2.0*A15 <= distance_between_zone_centers <= 6.0*A15
ER8_15M <= 0.35
abs(net_move_last_8_15m) <= 1.0*A15
center_drift_last_8_15m <= 0.50*A15
```

当前价格出现 zone 外 accepted close 或位移扩张时，Range 不可操作。

### 9.2 Event trigger — Long

```text
low <= LOWER_ZONE_HIGH + 0.15*A5
outside_penetration < 0.10*A5
close >= LOWER_ZONE_HIGH + 0.05*A5
upper zone not touched in same candle
```

### 9.3 FAST Range

```text
CLV >= 0.70
lower_wick / candle_range >= 0.35
volume >= 1.00*M20
```

### 9.4 STANDARD Range research candidate

不作为首发必需实现，但进入回测：

```text
confirmation within next 1–2 closed 5m
all closes remain above LOWER_ZONE_LOW - 0.10*A5
higher low OR confirmation close > trigger close
```

### 9.5 Entry / Stop / Chase

Long：

```text
ENTRY_ZONE = [LOWER_ZONE_HIGH, LOWER_ZONE_HIGH + 0.10*A5]
STRUCTURAL_STOP = min(event_low - 0.10*A5, LOWER_ZONE_LOW - 0.10*A5)
CHASE_LIMIT = LOWER_ZONE_HIGH + 0.30*A5
```

### 9.6 Reference target feasibility

```text
R = planned_entry - structural_stop
reserve = max(0.10*A5, round_trip_cost)
require distance_to_range_center >= 1.0*R + reserve
```

对侧 zone 是扩展参考，不是首轮硬要求。

---

## 10. 冲突与事件分流

```text
ZONE_ATTACK
→ RECLAIMED_INSIDE            → SWEEP
→ ACCEPTED_OUTSIDE_ORDERLY    → MICRO_FAST / STANDARD
→ ACCEPTED_OUTSIDE_DISPLACEMENT → IMMEDIATE_FAST
→ AMBIGUOUS_TWO_SIDED         → WATCH / NO ACTION
```

同一 zone attack event 只允许一个最终正式输出。

Breakout 失效后只有完整满足 Sweep 条件，才允许：

```text
FAILED_BREAKOUT_TO_SWEEP
```

---

## 11. 当前 Signal / TradePlan 参考退出字段

每个正式输出至少包含：

```text
ENTRY_ZONE
INITIAL_STRUCTURAL_STOP
PLANNED_RISK
REFERENCE_1R_PRICE
REFERENCE_1_5R_PRICE
REFERENCE_2R_PRICE
NEXT_STRUCTURAL_ZONE_IF_KNOWN
REFERENCE_EXIT_MODE
DO_NOT_CHASE
```

当前人工拥有最终止盈和止损调整权威。

---

## 12. 影子退出和路径证据

至少计算：

```text
1R_hit
1_5R_hit
2R_hit
next_structural_zone_hit
MFE/MAE at 30m, 60m, 120m
maximum_MFE_before_initial_stop
time_to_1R
return_to_entry_after_MFE
maximum_profit_given_back
```

若近零成本可复用，再计算：

```text
REFERENCE_BREAK_EVEN_OUTCOME
REFERENCE_STRUCTURE_TRAIL_OUTCOME
REFERENCE_NO_PROGRESS_OUTCOME
REFERENCE_REVERSAL_EXIT_OUTCOME
```

不建设实时动态退出引擎。

---

## 13. 第一轮有限研究候选

```text
ZONE_MODEL_R1_15M_REACTION_CLUSTER
SWEEP_ZONE_RECLAIM_FAST_STD_R1
BREAKOUT_DISPLACEMENT_FAST_IMMEDIATE_R1
BREAKOUT_MICRO_CONFIRMED_FAST_R1
BREAKOUT_STANDARD_DEEP_AND_SHALLOW_RETEST_R1
RANGE_ZONE_EDGE_FAST_R1
MANUAL_PINBAR_REFERENCE_R1
CURRENT_PRODUCTION_LINE_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

Pin Bar 只作为人工策略对照，不自动成为唯一生产确认。

---

## 14. 回测顺序

### Round 1 — Zone and entry

统一初始止损和成本模型，主要比较：

- signal count；
- independent event count；
- false breakout / reclaim rate；
- 30m/60m/120m MFE 与 MAE；
- 1R/1.5R/2R hit；
- maximum profit given back；
- human review match；
- 按模式、方向、资产、时段和流动性分组。

### Round 2 — One bounded correction

每个模式最多修改 1–2 个有明确失败原因的参数。

### Round 3 — Frozen out-of-sample

使用未参与调参的数据。失败不得继续在同一数据上无限修补。

---

## 15. 当前未决问题

必须由 Round 1 结果回答：

1. Immediate FAST 是否有独立正期望，还是只保留为 WATCH；
2. 一根 5m Micro confirmation 是否显著减少假突破而不损失过多机会；
3. Shallow retest 是否优于 deep retest；
4. Zone model 是否显著优于当前 U12/L12 单线；
5. Volume Profile 是否对 zone、target space 或 false breakout 提供增量解释；
6. 1R target-feasibility 是否比既有 2R 硬门槛更符合日内机会；
7. Range STANDARD 是否值得首发实现。

---

## 16. 当前状态

```text
RESEARCH_DIRECTION = FROZEN_FOR_ROUND_1
PARAMETERS = FIRST_ROUND_CANDIDATES_NOT_PROVEN
BACKTEST = NOT_EXECUTED
ENGINEERING_IMPLEMENTATION = NOT_AUTHORIZED
PRODUCTION_DEPLOYMENT = NOT_AUTHORIZED
```
