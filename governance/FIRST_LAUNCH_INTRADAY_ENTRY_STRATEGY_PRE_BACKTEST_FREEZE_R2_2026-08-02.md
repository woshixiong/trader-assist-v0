# First Launch 日内入场策略回测前冻结 R2

**记录 ID：** `TA-FIRST-LAUNCH-INTRADAY-ENTRY-STRATEGY-PRE-BACKTEST-FREEZE-R2-2026-08-02`  
**日期：** `2026-08-02`  
**状态：** `PRE-BACKTEST FREEZE / RESEARCH ONLY / NON-PRODUCTION / NON-DEPLOYMENT`  
**关联：** PR #52、三 Setup R1/R1.1/R1.2、Zone-State-Entry Candidate R1、Research Playbook V2、Position Management R2  
**优先级：** 本文件取代与其冲突的 `FIRST_LAUNCH_ZONE_STATE_ENTRY_STRATEGY_RESEARCH_CANDIDATE_R1_2026-08-02.md`。  
**权限边界：** 本文允许形成回测任务包，但不授权生产代码修改、部署、账户访问、交易所写入或自动下单。

---

## 1. 研究目标

```text
PRIMARY_STRUCTURE_TIMEFRAME = 15m
EXECUTION_TIMEFRAME = 5m
TRADING_HORIZON = INTRADAY
HOLDING_TIME = NOT_FIXED
ENTRY_FIRST = YES
INITIAL_STRUCTURAL_STOP_REQUIRED = YES
MINIMUM_REFERENCE_OPPORTUNITY = APPROX_1R_AFTER_COSTS
HUMAN_FINAL_DECISION = YES
REALTIME_DYNAMIC_EXIT_ENGINE = OUT_OF_SCOPE
```

本轮只优化和回测：

- 关键价格带；
- Sweep、Breakout、Range 入场；
- FAST / STANDARD 模式；
- 初始结构止损；
- Chase Limit；
- 参考目标和完整影子退出证据。

---

## 2. 候选优先级

### P0 Comparator

```text
V0_1_EXACT_BASELINE
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
DONCHIAN_TURTLE_BREAKOUT_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

### P1 Primary

```text
ZONE_MODEL_R2
SWEEP_CONFIRMED_RECLAIM_R2
BREAKOUT_MICRO_CONFIRMED_FAST_R2
BREAKOUT_STANDARD_RETEST_R2
RANGE_EDGE_REJECTION_FAST_R2
```

### P2 Secondary / Sensitivity

```text
BREAKOUT_IMMEDIATE_DISPLACEMENT_FAST_R2
SWEEP_SAME_BAR_FAST_R2
PIN_BAR_QUALITY_FILTER
SHALLOW_VS_DEEP_RETEST_ATTRIBUTION
ZONE_LOOKBACK_64_SENSITIVITY
```

### P3 Deferred evidence

```text
VOLUME_PROFILE_HVN_LVN_POC
OI_AND_FUNDING_CONTEXT
L2_DEPTH_AND_ORDER_FLOW_IMBALANCE
REALTIME_DYNAMIC_EXIT
```

P3 第一轮只记录可得证据，不作为硬触发，不得阻塞回测。

---

## 3. 共同数据

```text
A5  = Wilder ATR14 on closed 5m candles
A15 = Wilder ATR14 on closed 15m candles
M20 = median volume of previous 20 closed 5m candles
CLV = (close-low) / max(high-low, minimum_tick)
BODY_A5 = abs(close-open) / A5
TR_A5 = true_range / A5
ER3 = 3-bar directional efficiency on closed 5m bars
ER8_15 = 8-bar directional efficiency on closed 15m bars
```

最低启动历史：

```text
MIN_5M_HISTORY = 288
MIN_15M_HISTORY = 96
```

只使用在 decision cutoff 前已经闭合并到达的数据。

---

## 4. ZONE_MODEL_R2

### 4.1 Primary lookback

```text
ZONE_LOOKBACK_15M_PRIMARY = 96 closed bars
ZONE_LOOKBACK_15M_SENSITIVITY = 64 closed bars
```

Primary 约覆盖一个完整加密交易日；64-bar 仅作为 P2 sensitivity。

### 4.2 因果 pivot

```text
pivot_high_i = high_i > high_i-1 AND high_i >= high_i+1
pivot_low_i  = low_i  < low_i-1  AND low_i  <= low_i+1
```

只有 `i+1` 闭合后 pivot 才可用。

### 4.3 聚类和反应

```text
CLUSTER_DISTANCE <= max(0.20*A15, 2*spread_price)
MIN_REACTION_SEPARATION = 2 closed 15m bars
REACTION_MOVE_AWAY >= 0.50*A15 within next 1-3 already-closed 15m bars
```

### 4.4 Zone 几何

```text
ZONE_CENTER = median(reaction_prices)
RAW_HALF_WIDTH = max(1.5*MAD(reaction_prices), 0.15*A15)
ZONE_HALF_WIDTH = clamp(RAW_HALF_WIDTH, 0.15*A15, 0.40*A15)
ZONE_WIDTH = 0.30*A15 ... 0.80*A15
```

### 4.5 Zone quality

```text
ZQ1 = 1 independent reaction
ZQ2 = >=2 reactions AND latest age <=24 closed 15m bars
ZQ3 = >=3 reactions AND latest age <=24 closed 15m bars
```

P1 Setup 要求 `ZQ2+`。ZQ3 只用于排序和归因。

---

## 5. 状态路由

```text
RECLAIMED_INSIDE              → SWEEP
ACCEPTED_OUTSIDE_ORDERLY      → MICRO_FAST or STANDARD
ACCEPTED_OUTSIDE_DISPLACEMENT → IMMEDIATE_FAST
AMBIGUOUS_TWO_SIDED           → WATCH / NO_ACTION
```

### 5.1 Reclaimed inside

```text
outside_penetration >= 0.10*A5
AND close returns inside zone by >=0.05*A5
within same or next 2 closed 5m bars
```

### 5.2 Ambiguous

以下任一成立：

- 三根 5m 内连续攻击 zone 两侧；
- 同一根 K 线形成 dual-edge event；
- 多次 inside/outside 收盘且方向无法唯一归类；
- 数据不完整或对齐失败。

全部保留证据，不发 actionable 信号。

---

## 6. P1 Sweep confirmed reclaim

以下以向下扫支撑后做多为例，做空镜像。

```text
ZONE_QUALITY >= ZQ2
0.10*A5 <= outside_excursion <= 0.75*A5
reclaim inside >= 0.05*A5 within same or next 2 bars
reclaim CLV >= 0.55
```

确认必须发生在 reclaim 后下一根或第二根 5m：

```text
close remains inside zone
AND (higher_low OR close > reclaim_close)
```

入场：确认 K 线闭合后，必须仍处于：

```text
ENTRY_MAX_DISTANCE_FROM_INNER_EDGE <= 0.20*A5
```

止损：

```text
STOP = sweep_extreme -/+ 0.10*A5
```

Chase：

```text
MAX_CHASE_FROM_ZONE_EDGE = 0.35*A5
```

最低可行空间：

```text
space_to_zone_center >= 1.0R + cost_reserve
```

原始候选即使失败，也必须保留用于假突破和级联归因。

---

## 7. P1 Breakout micro-confirmed FAST

这是第一轮 Breakout 的首要 FAST 候选，不等待完整回踩，但等待一根闭合 5m 验证带外接受。

以下以向上为例，向下镜像。

### Initial breakout

```text
close >= ZONE_HIGH + 0.15*A5
BODY_A5 >= 0.50
CLV >= 0.70
volume >= 1.20*M20
```

### Next-bar confirmation

下一根闭合 5m 必须：

```text
close >= ZONE_HIGH + 0.10*A5
low >= ZONE_HIGH - 0.10*A5
AND (close > initial_close OR higher_low)
```

### Entry / stop / chase

```text
ENTRY = confirmation close
MAX_CHASE = ZONE_HIGH + 0.50*A5
STOP = min(confirmation_low - 0.10*A5, ZONE_HIGH - 0.20*A5)
```

### Target feasibility

```text
next_structural_obstacle_space >= 1.0R + cost_reserve
OR NO_KNOWN_STRUCTURAL_OBSTACLE
```

---

## 8. P1 Breakout STANDARD retest

使用与 Micro FAST 相同的 initial breakout，但不满足下一根确认或选择等待回踩时进入 STANDARD PREPARE。

```text
RETEST_WINDOW = next 1-6 closed 5m bars
```

### Deep retest

```text
retest enters [ZONE_EDGE - 0.15*A5, ZONE_EDGE + 0.25*A5]
confirmation close returns outside by >=0.05*A5
```

### Shallow retest

```text
retracement = 25% ... 60% of initial displacement leg
price remains outside zone
AND (higher_low/lower_high OR break of retest confirmation bar)
```

### Invalidation

```text
close re-enters zone deeper than 0.15*A5
OR window > 6 bars
OR opposite accepted breakout
OR DataQuality != READY
```

### Entry / stop / chase

```text
ENTRY = confirmation close
STOP = farther of:
  retest_extreme +/- 0.10*A5
  zone interior +/- 0.20*A5
MAX_CHASE_FROM_ZONE_EDGE = 0.40*A5
```

最低可行空间同样为 `1.0R + cost_reserve` 或无已知结构障碍。

Deep / Shallow 必须分别归因，但第一轮不为二者设置不同生产权威。

---

## 9. P1 Range FAST

Range 使用两个独立 `ZQ2+` 价格带。

```text
RANGE_LOOKBACK_15M = 24 bars
CENTER_DISTANCE = 1.5*A15 ... 5.0*A15
ER8_15 <= 0.35
NET_MOVE_8 <= 1.0*A15
CENTER_DRIFT <= 0.50*A15
VOLATILITY != EXTREME
```

下边缘做多，镜像做空：

```text
low <= lower_zone_inner_edge + 0.15*A5
outside_excursion < 0.10*A5
close returns inside range by >=0.05*A5
CLV >= 0.70
lower_wick / candle_range >= 0.35
volume >= 1.00*M20
```

```text
ENTRY_MAX_DISTANCE_FROM_EDGE = 0.15*A5
STOP = farther of event_low - 0.10*A5 or zone_outer_edge - 0.10*A5
MAX_CHASE_TOWARD_CENTER = 0.30*A5
space_to_range_center >= 1.0R + cost_reserve
```

Range STANDARD 继续延期，除非 P1 FAST 样本或表现明确不足。

---

## 10. P2 Immediate displacement FAST

高风险候选，独立统计，不与 Micro FAST 合并。

```text
close beyond zone >=0.30*A5
BODY_A5 >=0.80
CLV >=0.80
TR_A5 >=1.20
volume >=1.50*M20
ER3 >=0.65
```

并满足：

```text
COMPRESSION_TAG = true
OR (BODY_A5 >=1.20 AND volume >=2.00*M20)
```

Compression tag：

```text
median(TR last 6) / median(TR previous 24) <=0.75
AND range(last 12) <=2.00*A5
AND condition persists >=9 closed 5m bars
```

入场只允许在：

```text
0.25*A5 ... 0.45*A5 beyond zone edge
MAX_CHASE = 0.60*A5
```

止损采用突破 K 线结构与 zone 失效位中较远者。该模式必须单独报告假突破率、MAE、滑点和错过率。

---

## 11. P2 Sweep same-bar FAST / Pin Bar

Same-bar Sweep：

```text
same 5m bar penetrates and reclaims
CLV >=0.75
volume >=1.20*M20
```

Pin Bar 作为质量标签：

```text
wick/body >=2.0
wick/range >=0.55
close near rejection side
volume >=1.20*M20
```

不得把 Pin Bar 作为所有 Sweep 或 STANDARD 的硬条件，除非回测证明其增量价值。

---

## 12. 初始止损和计划风险

所有模式在信号产生时必须冻结：

```text
ENTRY_PRICE_OR_ZONE
INITIAL_STRUCTURAL_STOP
RISK_PER_UNIT
PLANNED_POSITION_SIZE_INPUTS
MAX_PLANNED_RISK
DO_NOT_CHASE_LEVEL
```

止损基于 Setup 失效结构和 `0.10*A5` 噪音缓冲；不得使用任意固定 ETH 美元止损。

---

## 13. 影子退出回测范围

第一轮必须计算：

```text
1R_hit
1.5R_hit
2R_hit
next_structural_zone_hit
MFE_30m_60m_120m
MAE_30m_60m_120m
maximum_MFE_before_initial_stop
time_to_1R
return_to_entry_after_MFE
maximum_profit_given_back
```

在定义完全确定且现有 evaluator 可低成本实现时，同时计算：

```text
FIXED_1R_EXIT
FIXED_1_5R_EXIT
FIXED_2R_EXIT
STRUCTURAL_TARGET_EXIT
SIMPLE_BREAK_EVEN_AFTER_NEW_STRUCTURE
SIMPLE_STRUCTURE_TRAIL
NO_PROGRESS_EXIT
REVERSAL_EXIT_REFERENCE
```

不回测人工主观退出，不将 L2/OI/订单流退出逻辑设为首轮硬依赖。

---

## 14. 回测轮次

计划三轮，最多四轮：

```text
ROUND_1 = broad causal screen and failure attribution
ROUND_2 = targeted correction, one or two variables per failed unit
ROUND_3 = frozen out-of-sample validation
ROUND_4 = only for implementation defect, data contradiction, or one decisive unresolved issue
```

不得因为普通结果不满意而无限增加回测轮次。

---

## 15. 回测晋级单位

所有结果按以下单位独立报告：

```text
setup_family × side × confirmation_mode
```

必须报告：

- independent event count；
- signal count；
- win rate under fixed reference exits；
- average / total net R；
- MFE / MAE；
- false breakout / failed reclaim；
- missed continuation；
- drawdown；
- longest losing streak；
- cost and delay sensitivity；
- exact recent versus proxy direction。

任何模式可以单独晋级、修改、延期或拒绝。

---

## 16. 当前范围边界

```text
CURRENT = strategy optimization + backtest + shadow exit evaluation
PAUSED = scanner integration + production reliability fixes + deployment bundling
DEFERRED = realtime dynamic exit + semi-automatic execution + L2 hard dependency
```

只有策略回测完成并形成冻结结论后，才恢复其他问题的统一工程与部署计划。
