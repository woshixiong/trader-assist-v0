# First Launch 日内入场策略回测前冻结 R3

**记录 ID：** `TA-FIRST-LAUNCH-INTRADAY-ENTRY-STRATEGY-PRE-BACKTEST-FREEZE-R3-2026-08-02`  
**日期：** `2026-08-02`  
**状态：** `PRE-BACKTEST FREEZE / RESEARCH ONLY / NON-PRODUCTION / NON-DEPLOYMENT`  
**关联：** PR #52、三 Setup R1/R1.1/R1.2、Pre-Backtest Freeze R2、Research Playbook V2、Position Management R2  
**优先级：** 本文件取代与其冲突的 `FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R2_2026-08-02.md`。  
**权限边界：** 本文允许形成回测任务包，但不授权生产代码修改、部署、账户访问、交易所写入或自动下单。

---

## 1. 最终研究目标

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
HUMAN_FINAL_DECISION = YES
REALTIME_DYNAMIC_EXIT_ENGINE = OUT_OF_SCOPE
```

本轮回测只解决：

- 1h 大方向是否提高 15m/5m 日内入场质量；
- 15m 关键价格带；
- Sweep、Breakout、Range 入场；
- FAST / STANDARD；
- 波动率自适应确认与生命周期；
- 初始结构止损、Chase Limit；
- 参考目标与影子退出路径。

---

## 2. 多周期职责

```text
1h = higher-timeframe directional context
15m = key zone and opportunity structure
5m = executable confirmation and entry timing
1m/3m = path reconstruction and optional microstructure evidence
```

禁止：

- 用未闭合 1h K 线决定趋势；
- 用 1m/3m 单根形态独立产生正式策略权威；
- 让 1h 方向替代 Setup 自身入场确认；
- 把顺势过滤的减少交易数误报为策略改进，必须同时报告漏失机会。

---

## 3. 1h 方向状态候选

### 3.1 数据

```text
A1H = Wilder ATR14 on closed 1h candles
ER8_1H = abs(C[-1]-C[-9]) / sum(abs(C[i]-C[i-1]), last 8 closed 1h bars)
D8_1H = (C[-1]-C[-9]) / A1H
```

最低启动历史：

```text
MIN_1H_HISTORY = 64 closed bars
```

### 3.2 Primary state

```text
HTF_UP:
ER8_1H >= 0.35
AND D8_1H >= 0.75

HTF_DOWN:
ER8_1H >= 0.35
AND D8_1H <= -0.75

HTF_NEUTRAL:
data ready
AND neither HTF_UP nor HTF_DOWN

HTF_UNCERTAIN:
data incomplete, ATR invalid, causal alignment failure, or conflicting state
```

最近两个已因果确认的 1h swing high / swing low 顺序只作为 `HTF_STRUCTURE_ALIGNMENT` 影子字段，不作为第一轮硬门槛。

### 3.3 Alignment label

```text
ALIGNED
NEUTRAL_CONTEXT
COUNTERTREND
UNCERTAIN
```

规则：

- Long + HTF_UP = ALIGNED；Short + HTF_DOWN = ALIGNED；
- HTF_NEUTRAL = NEUTRAL_CONTEXT；
- Long + HTF_DOWN 或 Short + HTF_UP = COUNTERTREND；
- HTF_UNCERTAIN = UNCERTAIN。

### 3.4 第一轮使用政策

P1 主候选：

```text
Breakout / Sweep actionable:
ALIGNED OR NEUTRAL_CONTEXT

COUNTERTREND:
retain raw candidate and full outcome
but not actionable in P1

UNCERTAIN:
NO_ACTION
```

Range：

```text
P1 actionable only when HTF_NEUTRAL
HTF directional Range candidates retained as shadow evidence
```

必须同时运行无 1h 过滤对照，判断方向过滤是否真正提高成本后期望，而不是只减少交易。

```text
P0_HTF_COMPARATOR = R2_NO_HTF_FILTER
P1_HTF_POLICY = R3_HTF_ALIGNMENT
```

---

## 4. 固定 K 线数量的分类

不是所有固定 bar count 都应取消。

### 4.1 可保留为首轮研究参数

以下属于统计估计或结构上下文窗口，可保留固定候选并做 sensitivity：

- ATR14；
- volume median 20；
- 1h ER8 / D8；
- 15m zone lookback 96 vs 64；
- reaction freshness。

它们必须使用 ATR 或其他波动率归一化，并接受后续敏感性检验。

### 4.2 必须波动率自适应

以下属于事件发展速度，不应只由固定 bar count 决定：

- Breakout STANDARD retest 等待；
- Sweep reclaim confirmation lifecycle；
- FAST acceptance observation；
- stale/no-progress event expiry。

固定时间只允许作为安全上限，不得作为确认成立的主要条件。

---

## 5. 波动率状态与自适应执行时钟

### 5.1 因果实现波动率

```text
RV60 = sqrt(sum(log_return_5m^2, last 12 closed 5m bars))
RV60_PERCENTILE = percentile of current RV60 against prior 7 days of causal RV60 observations
```

第一轮状态：

```text
VOL_LOW      = percentile < 30
VOL_NORMAL   = 30 <= percentile < 70
VOL_HIGH     = 70 <= percentile < 95
VOL_EXTREME  = percentile >= 95
```

数据不足时沿用现有 ATR-based volatility label，并标记 `VOL_CLASSIFIER_FALLBACK`。

### 5.2 Execution clock

```text
VOL_NORMAL / VOL_HIGH:
PRIMARY_CONFIRMATION_CLOCK = closed 5m

VOL_LOW:
PRIMARY_CONFIRMATION_CLOCK = closed 15m
5m path still retained for causality and entry price

VOL_EXTREME:
no new STANDARD candidate
raw evidence retained
```

30m confirmation只作为 P2 影子 sensitivity，不进入第一轮 P1 硬触发。

### 5.3 安全上限

```text
VOL_HIGH    MAX_WALL_CLOCK = 30 minutes
VOL_NORMAL  MAX_WALL_CLOCK = 60 minutes
VOL_LOW     MAX_WALL_CLOCK = 120 minutes
```

这些上限只防止 PREPARE 永久存活。确认与失效仍由价格形态、结构和路径决定。

---

## 6. Breakout STANDARD 波动率自适应形态合同

以下以 Long 为例，Short 镜像。

### 6.1 Freeze at breakout

```text
ZONE_LOW / ZONE_HIGH / ZONE_CENTER
A5_EVENT / A15_EVENT
HTF_STATE
VOL_STATE
initial breakout candle
initial breakout close
initial impulse extreme
entry and chase reference
structural obstacle set
```

不得在后续回踩过程中漂移价格带或重选有利边界。

### 6.2 Initial breakout

沿用 R2：

```text
close >= ZONE_HIGH + 0.15*A5
BODY_A5 >= 0.50
CLV >= 0.70
volume >= 1.20*M20
HTF alignment is ALIGNED or NEUTRAL_CONTEXT
```

### 6.3 Retest classification

不按“第几根 K 线”确认，只按路径分类。

#### Deep zone retest

```text
price enters [ZONE_HIGH - 0.15*A_EXEC, ZONE_HIGH + 0.25*A_EXEC]
AND closes back outside by >= 0.05*A_EXEC
AND old zone is not accepted again
```

#### Shallow structural retest

```text
pullback retraces 25% ... 60% of frozen impulse
AND remains outside old zone
AND forms higher low
AND resumes by closing above local pullback trigger
```

`A_EXEC` 使用当前 confirmation clock 对应的因果 ATR：5m 或 15m。

### 6.4 Confirmation

```text
DEEP:
close outside zone by >=0.05*A_EXEC
AND rejection/continuation structure valid

SHALLOW:
higher low confirmed
AND close breaks the local pullback high or resumes beyond the prior confirmation threshold
```

确认时仍必须：

```text
price <= Chase Limit
space >= 1R + cost reserve
HTF state not COUNTERTREND or UNCERTAIN
```

### 6.5 Invalidation

Long：

```text
close accepted inside zone by >0.20*A_EXEC
OR opposite confirmed event
OR price exceeds Chase Limit before entry
OR HTF becomes confirmed DOWN
OR structural target space falls below 1R + cost reserve
OR adaptive safety wall-clock expires
OR data quality fails
```

---

## 7. Sweep 自适应生命周期

Sweep 的越界与收回阈值沿用 R2，但确认等待改为相同的 volatility clock：

```text
VOL_NORMAL / HIGH = observe closed 5m structure
VOL_LOW = allow closed 15m confirmation
VOL_EXTREME = raw evidence only unless same-bar FAST comparator
```

确认依赖：

- 收回后仍在价格带内；
- higher low / lower high；
- 或收盘继续远离被清扫极值；
- 未被同方向真实 breakout 接管。

不再以固定“下一根或第二根”作为唯一有效条件。安全上限仍为 30/60/120 分钟。

---

## 8. FAST 和 Range 的 1h 政策

### 8.1 Micro-confirmed FAST

P1 只允许：

```text
ALIGNED OR NEUTRAL_CONTEXT
```

COUNTERTREND 保留完整候选和结果，用于量化“1h 过滤的机会成本”。

### 8.2 Immediate displacement FAST

仍为 P2 高风险候选。要求：

```text
HTF ALIGNED
```

HTF neutral immediate FAST 只记录 sensitivity，COUNTERTREND 拒绝。

### 8.3 Range

P1 Range 只允许 HTF_NEUTRAL。若 1h 已形成明确趋势，则 Range 边缘反向交易只作为 shadow candidate。

---

## 9. 第一轮回测必须新增的对照

### 9.1 Higher-timeframe value

同一事件、相同入场规则比较：

```text
NO_HTF_FILTER
HTF_ALIGNED_ONLY
HTF_ALIGNED_PLUS_NEUTRAL
COUNTERTREND_SHADOW
```

报告：

- 信号数量变化；
- 假突破率；
- 平均净 R；
- 最大回撤；
- 错失正收益事件；
- Long/Short 不对称；
- Setup/mode 级结果。

### 9.2 Adaptive lifecycle value

比较：

```text
FIXED_1_TO_6_5M_REFERENCE
R3_VOLATILITY_ADAPTIVE_CLOCK
```

报告：

- 确认率；
- 延迟；
- Chase 超限率；
- 浅回踩/深回踩捕获率；
- 假突破率；
- 净 R；
- 超过 30 分钟才确认的有效事件；
- stale candidate 误确认率。

### 9.3 30m shadow

低波动情况下记录 30m 聚合确认标签，但第一轮不作为正式 P1 信号。只有 15m adaptive 仍明显漏失慢速有效回踩时，才允许晋级 P2。

---

## 10. 影子退出保持不变

每个候选与正式 Signal 继续计算：

```text
1R / 1.5R / 2R hit
next structural zone hit
MFE / MAE at 30m, 60m, 120m
maximum MFE before stop
time to 1R
maximum profit giveback
return to entry after MFE
fixed-R outcomes
structural target outcome
simple break-even / trail / no-progress / reversal references where low-cost
```

动态实时退出系统仍不进入当前开发范围。

---

## 11. 最终候选优先级

### P0 Comparator

```text
V0_1_EXACT_BASELINE
R2_NO_HTF_FILTER
FIXED_1_TO_6_5M_STANDARD_REFERENCE
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
DONCHIAN_TURTLE_BREAKOUT_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

### P1 Primary

```text
ZONE_MODEL_R2
HTF_CONTEXT_R3
SWEEP_VOL_ADAPTIVE_CONFIRMED_RECLAIM_R3
BREAKOUT_MICRO_CONFIRMED_FAST_HTF_R3
BREAKOUT_VOL_ADAPTIVE_STANDARD_RETEST_R3
RANGE_EDGE_REJECTION_HTF_NEUTRAL_FAST_R3
```

### P2

```text
BREAKOUT_IMMEDIATE_DISPLACEMENT_FAST_HTF_ALIGNED
SWEEP_SAME_BAR_FAST
PIN_BAR_QUALITY_FILTER
SHALLOW_VS_DEEP_RETEST_ATTRIBUTION
ZONE_LOOKBACK_64_SENSITIVITY
LOW_VOL_30M_CONFIRMATION_SHADOW
```

### P3

```text
VOLUME_PROFILE_HVN_LVN_POC
OI_AND_FUNDING_CONTEXT
L2_DEPTH_AND_ORDER_FLOW_IMBALANCE
REALTIME_DYNAMIC_EXIT
```

---

## 12. 回测轮次

```text
ROUND_1:
P0 + P1 + all required shadow evidence

ROUND_2:
only failure-attributed limited changes + ordered P2

ROUND_3:
frozen out-of-sample validation

ROUND_4:
only implementation/data contradiction or one decisive unresolved variable
```

本文件是第一轮回测的策略权威。工程不得自行改变方向状态、波动率分位、阈值、候选优先级或报告单位。