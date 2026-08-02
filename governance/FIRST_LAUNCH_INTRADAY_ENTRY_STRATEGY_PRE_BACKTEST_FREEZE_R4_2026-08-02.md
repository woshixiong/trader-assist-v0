# First Launch 日内入场策略回测前冻结 R4

**记录 ID：** `TA-FIRST-LAUNCH-INTRADAY-ENTRY-STRATEGY-PRE-BACKTEST-FREEZE-R4-2026-08-02`  
**日期：** `2026-08-02`  
**状态：** `PRE-BACKTEST FREEZE / RESEARCH ONLY / NON-PRODUCTION / NON-DEPLOYMENT`  
**关联：** PR #52、R1/R1.1/R1.2、Pre-Backtest R2/R3、Research Playbook V3、Position Management R2  
**优先级：** 本文件取代与其冲突的 R2/R3。  
**权限边界：** 允许形成回测任务包，不授权生产代码修改、部署、账户访问、交易所写入或自动下单。

---

## 1. 最终目标

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
REALTIME_DYNAMIC_EXIT_ENGINE = OUT_OF_SCOPE
```

本轮只优化和回测：

- 1h 上层方向背景；
- 15m 关键价格带；
- 5m 入场确认；
- Sweep、Breakout、Range；
- FAST / STANDARD；
- 初始结构止损、Chase Limit；
- 参考止盈和完整影子退出结果；
- 趋势分段重新入场。

---

## 2. 事实驱动、禁止预测完成时间

```text
DECISION_INPUT = CLOSED_AND_RECEIVED_FACTS_ONLY
FUTURE_PATH_ASSUMPTION = PROHIBITED
FIXED_TIME_AS_ECONOMIC_INVALIDATION = PROHIBITED
```

15m 波动率、ATR 或实现波动率只能用于：

- 归一化价格距离、Zone Width、Stop、Chase；
- 描述已经发生的运行速度与幅度；
- 选择当前观察 5m、15m 或 30m 的研究尺度；
- 结果分层。

不得根据波动率推断行情将在多少分钟或多少根 K 线后完成回踩、延续或反转。

固定 bar count 可作为指标统计窗口和 comparator，但不能单独决定机会有效或失效。

---

## 3. 多周期方向政策

### 3.1 1h 状态

只使用闭合 1h K 线：

```text
A1H = Wilder ATR14
ER8_1H = abs(C[-1]-C[-9]) / sum(abs(delta close), last 8 bars)
D8_1H = (C[-1]-C[-9]) / A1H

HTF_UP   = ER8_1H >= 0.35 AND D8_1H >= 0.75
HTF_DOWN = ER8_1H >= 0.35 AND D8_1H <= -0.75
HTF_NEUTRAL = data ready and neither directional state
HTF_UNCERTAIN = incomplete or invalid
```

因果确认的 1h HH/HL 或 LH/LL 作为影子结构字段，第一轮不增加第二套硬门槛。

### 3.2 Alignment

```text
ALIGNED
NEUTRAL_CONTEXT
COUNTERTREND
UNCERTAIN
```

P1：

- ALIGNED / NEUTRAL_CONTEXT 可操作；
- COUNTERTREND 保留完整候选和结果，但不进入主策略；
- UNCERTAIN 不操作。

必须同时回测 `NO_HTF_FILTER` 对照，分别报告信号减少、期望变化、回撤变化和漏失机会。

### 3.3 Range 修正

Range 不要求 1h 必须中性，而按交易方向判断：

```text
HTF_UP:   Range Long aligned; Range Short countertrend
HTF_DOWN: Range Short aligned; Range Long countertrend
HTF_NEUTRAL: both neutral context
```

---

## 4. STANDARD 生命周期：结构驱动

删除“突破后 1–6 根 5m 内必须完成”的主候选限制。

### 4.1 PREPARE 继续存在的事实条件

Breakout Long 示例：

```text
price has not obtained accepted re-entry inside old zone
AND no opposite confirmed Setup
AND no newer independent market event supersedes the original event
AND current executable price remains within Chase Limit
AND target feasibility remains >= 1R after costs
AND causal data quality remains valid
```

Short 镜像。

### 4.2 深回踩确认

```text
price revisits zone edge or partially enters zone
AND does not obtain accepted re-entry into old structure
AND closes back outside in breakout direction
AND forms renewed directional evidence
```

### 4.3 浅回踩确认

```text
price remains outside old zone
AND retraces part of the prior impulse
AND forms higher low / lower high or equivalent causal structure
AND resumes directional progress
```

回撤百分比、Zone Penetration 和 ATR 距离作为归因字段和有限 sensitivity，不让固定时间决定确认。

### 4.4 事实失效

```text
accepted re-entry into old zone
opposite confirmed event
new structural zone supersedes original event
entry exceeds Chase Limit
structural target space falls below 1R after costs
data quality / causal alignment failure
```

工程实现可对长期未变化的状态做归档或重建，但归档不得被报告为“因为经过 N 分钟所以策略失效”。

---

## 5. Sweep 生命周期

Sweep 不再仅限同一根或后续固定两根 K 线。

P1 Confirmed Sweep 需要已经发生：

```text
qualified zone excursion
AND accepted reclaim inside zone
AND subsequent causal evidence preserves reclaim
AND higher low / lower high or renewed inward progress
```

失效由：重新接受带外、扫单极值被有效破坏、对侧 Breakout 确认、Chase/Target/Data failure 触发。

Same-bar Sweep FAST 保持 P2 独立候选。

---

## 6. 观察尺度自适应，但不预测时间

第一轮按已经观测到的波动率状态记录：

```text
LOW / NORMAL / HIGH / EXTREME
```

用途：

- LOW：15m 结构确认可能比单独 5m 更稳定；5m 仍保存用于真实入场价格与路径；
- NORMAL/HIGH：5m 为主要执行确认；
- EXTREME：STANDARD 主候选不建立新可操作状态，保留原始证据；Immediate Displacement FAST 独立评估。

30m 只作为 P2 观察尺度 sensitivity。

这里不设“LOW 最多 120 分钟”等经济失效阈值。

---

## 7. 趋势分段重新入场

同一 1h/15m 趋势可产生多笔独立 TradePlan：

```text
initial breakout/reclaim entry
→ favorable segment
→ human or shadow exit / structure interruption
→ new pullback or new zone
→ new causal continuation signal
→ independent re-entry
```

每次重新入场必须具有新的：

```text
market_event_id
entry
structural_stop
planned_risk
chase_limit
target context
outcome
```

必须防止同一事件重复发布，但不得因已有一笔历史信号而屏蔽后续独立趋势段。

回测必须报告：

- 每个趋势事件的可交易分段数量；
- 首次入场与后续重新入场表现；
- 错过首段后能否在后续段恢复参与；
- 分段交易成本后的净结果；
- 一直持有与分段重新入场的影子对照。

---

## 8. 候选优先级

### P0

```text
V0_1_EXACT_BASELINE
NO_HTF_FILTER_COMPARATOR
FIXED_1_TO_6_BAR_STANDARD_COMPARATOR
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
DONCHIAN_TURTLE_BREAKOUT_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

### P1

```text
ZONE_MODEL_R4
HTF_ALIGNMENT_POLICY_R4
SWEEP_FACT_CONFIRMED_RECLAIM_R4
BREAKOUT_MICRO_CONFIRMED_FAST_R4
BREAKOUT_STATE_DRIVEN_STANDARD_R4
RANGE_DIRECTION_ALIGNED_FAST_R4
TREND_SEGMENT_REENTRY_R4
```

### P2

```text
BREAKOUT_IMMEDIATE_DISPLACEMENT_FAST
SWEEP_SAME_BAR_FAST
PIN_BAR_QUALITY_FILTER
SHALLOW_VS_DEEP_RETEST
ZONE_LOOKBACK_64
30M_CONFIRMATION_SCALE
```

### P3

```text
VOLUME_PROFILE_HVN_LVN_POC
OI_FUNDING_CONTEXT
L2_DEPTH_ORDER_FLOW
REALTIME_DYNAMIC_EXIT
```

---

## 9. 退出影子回测

当前不开发实时退出系统，但每个信号必须输出和评估：

```text
initial structural stop
1R / 1.5R / 2R reference
next structural zone
30/60/120m MFE and MAE
maximum favorable excursion before stop
maximum profit giveback
fixed-R outcomes
structure-target outcome
simple break-even / profit-lock outcome
simple structure-trailing outcome
no-progress and reversal-exit shadow labels
```

人工主观退出与依赖完整实时 L2 的退出不能由历史 OHLCV 完全重建，必须明确标记证据限制。

---

## 10. 第一轮必须回答

1. 1h 顺势政策是否提高成本后期望和回撤质量；
2. Range 按方向对齐是否优于只允许 1h 中性；
3. 状态驱动 STANDARD 比固定 1–6 bar 少漏掉多少慢趋势；
4. 不同波动状态下最有效的确认尺度；
5. 微确认 FAST 与立即 FAST 的差异；
6. 深回踩、浅回踩和趋势分段重新入场的贡献；
7. 约 1R 可行性门槛是否适合日内机会；
8. 影子退出字段能否为未来动态退出提供充分数据。

结果必须按 `setup × side × mode × HTF alignment × volatility state × first/re-entry` 分层，同时提供汇总，禁止用汇总掩盖负单元。
