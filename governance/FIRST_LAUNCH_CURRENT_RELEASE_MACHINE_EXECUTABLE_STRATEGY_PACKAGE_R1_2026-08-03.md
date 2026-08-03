# First Launch 当前发布机器可执行策略包 R1

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-RELEASE-MACHINE-STRATEGY-R1-2026-08-03`  
**日期：** `2026-08-03`  
**状态：** `CURRENT MACHINE SEMANTICS FREEZE / NON-EXECUTABLE / NON-AUTHORIZING`  
**父合同：** Pre-Backtest R5、Scanner R3、Playbook V5、多资产并行替代架构 R1  
**优先级：** 本文件是当前发布候选机器执行语义最高权威；与 R5 或旧三 Setup 文件冲突时，以本文件为准。  

---

## 1. 身份、范围和权限

```text
STRATEGY_VERSION = FL-MA-PRICE-ACTION-v0.1
PARAMETER_VERSION = 2026-08-03-r1
SCANNER_VERSION = SESSION-MOMENTUM-R3
SCHEMA_VERSION = 1
RELEASE_MODE = MULTI_ASSET_SHADOW_FORWARD_VALIDATION
```

适用：

```text
ETH + ALL ELIGIBLE HYPERLIQUID PERPETUAL MARKETS
```

权限：

```text
PUBLIC_DATA_ONLY = YES
HUMAN_FINAL_DECISION = YES
SUBMISSION_STATUS = NOT_SUBMITTED
ACCOUNT_ACCESS = NO
SIGNING = NO
EXCHANGE_WRITE = NO
AUTO_TRADE = NO
```

每个完整 Setup 的信号字段对 ETH 和非 ETH 完全一致。

---

## 2. Canonical Market Identity

```text
market_key = venue + "|" + dex + "|" + coin
market_id  = sha256(UTF8(market_key))
```

字段：

```text
venue = "HYPERLIQUID"
dex = exact API DEX identity; native perp uses one fixed canonical value chosen by Engineering
coin = exact API coin identity, including DEX prefix when the API requires it
asset_class = CRYPTO | EQUITY | INDEX | COMMODITY | OTHER
tick_size > 0
size_decimals >= 0
max_leverage = positive decimal or UNAVAILABLE
```

缺少 `market_id`、`coin`、`tick_size` 或 `size_decimals`：

```text
FORMAL_SETUP_EVALUATION = NO
REJECTION = MARKET_METADATA_INCOMPLETE
```

---

## 3. 时间轴与数据权威

```text
SIGNAL_BASE_TIMEFRAME = 5m
STRUCTURE_TIMEFRAME = 15m
CONTEXT_TIMEFRAME = 1h
OUTCOME_PATH_TIMEFRAME = 1m for formal plans; 5m allowed for ordinary WATCH
TIMEZONE = UTC
```

- 只使用已经闭合并已经收到的 5m K 线产生策略状态和 Signal。
- 15m 和 1h 必须由相同的闭合 5m 序列按 UTC 边界因果聚合。
- 15m K 线只有最后一根组成 5m 闭合后可见。
- 1h K 线只有最后一根组成 5m 闭合后可见。
- 未闭合、缺口、重复冲突或时间边界错误不得进入正式 Setup。

核心数据无效：

```text
ACTIONABLE_SIGNAL = NO
RAW_CANDIDATE = RETAIN
REJECTION = MULTITIMEFRAME_DATA_INVALID
```

只有 1h 不足而 5m/15m 有效：

```text
FORMAL_SETUP_EVALUATION = YES
HTF_RELATION = CONTEXT_INCOMPLETE
```

---

## 4. 指标

### 4.1 Wilder ATR14

对任一周期：

```text
TR_t = max(
  high_t-low_t,
  abs(high_t-close_t-1),
  abs(low_t-close_t-1)
)
ATR14_seed = mean(first 14 TR)
ATR14_t = (13*ATR14_t-1 + TR_t)/14
```

需要至少 15 根闭合 K 线。

```text
A5  = ATR14 on closed 5m
A15 = ATR14 on closed 15m
A1H = ATR14 on closed 1h
```

ATR 非正、非有限或历史不足：相关正式 Setup 不可执行。

### 4.2 M20

```text
M20 = median(volume of previous 20 closed 5m bars)
```

不包含当前触发 K 线。

### 4.3 CLV

```text
range = high-low
if range <= 0: candle is invalid for Setup confirmation
CLV_LONG  = (close-low)/range
CLV_SHORT = (high-close)/range
```

### 4.4 Directional Efficiency

```text
ER8_TF = abs(C[-1]-C[-9]) / sum(abs(C[i]-C[i-1]) for last 8 changes)
```

分母为 0 时：

```text
ER8_TF = 0
```

---

## 5. 1h Momentum 与 Structure

### 5.1 Momentum

```text
D8_1H = (C[-1]-C[-9])/A1H
```

```text
HTF_MOMENTUM_UP:
ER8_1H >= 0.35 AND D8_1H >= 0.75

HTF_MOMENTUM_DOWN:
ER8_1H >= 0.35 AND D8_1H <= -0.75

HTF_MOMENTUM_NEUTRAL:
data ready and neither UP nor DOWN

HTF_MOMENTUM_UNAVAILABLE:
insufficient or invalid 1h data
```

### 5.2 Causal Pivot

只有右侧 K 线闭合后，中心 K 线才确认：

```text
pivot_high_i = high_i > high_i-1 AND high_i >= high_i+1
pivot_low_i  = low_i  < low_i-1  AND low_i  <= low_i+1
```

取最近两个 confirmed highs `H1,H2` 和 lows `L1,L2`。

```text
EPS_1H = 0.10*A1H at evaluation time
```

```text
HH = H2 > H1 + EPS_1H
LH = H2 < H1 - EPS_1H
EH = otherwise

HL = L2 > L1 + EPS_1H
LL = L2 < L1 - EPS_1H
EL = otherwise
```

```text
HTF_STRUCTURE_UP    = HH AND HL
HTF_STRUCTURE_DOWN  = LH AND LL
HTF_STRUCTURE_RANGE = (LH OR EH) AND (HL OR EL)
HTF_STRUCTURE_TRANSITION = all other combinations with sufficient swings
HTF_STRUCTURE_INSUFFICIENT = fewer than 2 confirmed highs or fewer than 2 confirmed lows
HTF_STRUCTURE_UNAVAILABLE = invalid or unavailable 1h data
```

### 5.3 HTF Relation

如果 Momentum 或 Structure 为 `UNAVAILABLE`：

```text
HTF_RELATION = CONTEXT_INCOMPLETE
```

否则将 Momentum directional state 和 Structure directional state 分别映射为 `+1 / -1 / 0`；Range、Transition、Insufficient、Neutral 为 0。

对 Long 信号，signal direction=+1；Short=-1。

```text
both equal signal direction       → ALIGNED_STRONG
one equals signal, other is 0     → ALIGNED_PARTIAL
both equal opposite direction     → COUNTERTREND_STRONG
one equals opposite, other is 0   → COUNTERTREND_PARTIAL
one equals signal, one opposite   → CONFLICTED
both are 0                         → NEUTRAL
```

HTF 只记录和归因，不过滤正式 Setup。

---

## 6. 15m Zone

### 6.1 Lookback

```text
ZONE_LOOKBACK_15M = 96 closed 15m bars
```

64-bar 只保留为未来敏感性，不属于当前正式参数。

### 6.2 反应点资格

对已确认的 15m Pivot：

- High Pivot 的 reaction price = pivot high；
- Low Pivot 的 reaction price = pivot low；
- 使用 Pivot 右侧 K 线闭合时的 `A15` 作为 `A15_REACTION`；
- 在 Pivot K 线之后最多 4 根闭合 15m 内：
  - High Pivot 要求 `pivot_high - minimum_subsequent_low >= 0.50*A15_REACTION`；
  - Low Pivot 要求 `maximum_subsequent_high - pivot_low >= 0.50*A15_REACTION`；
- 只有 move-away 已经发生后，reaction 才可加入 Zone；
- 4 根内未满足，丢弃该 reaction，不形成 Zone 成员。

该 4-bar 窗口只属于 Zone 反应资格统计，不是交易机会经济超时。

### 6.3 独立反应

同类型 reaction 的 Pivot bar index 间隔必须 `>=2`。

间隔小于 2 时视为同一次反应：

- High Pivot 保留价格更高者；
- Low Pivot 保留价格更低者；
- 价格相同时保留更早确认者。

### 6.4 聚类

High 和 Low 分开聚类。

按 reaction confirmed time 从旧到新处理。

加入已有同类型 Cluster 的条件：

```text
distance(reaction_price, cluster_center)
<= max(0.20*A15_REACTION, 2*minimum_tick)
```

不使用历史不可恢复的 spread 构造 Zone Identity。

若可加入多个 Cluster：

1. 距离 center 最小；
2. 建立时间最早；
3. `zone_id` 字典序最小。

否则新建 Cluster。

一个 reaction 只能属于一个 Cluster。

### 6.5 Zone Geometry

对 Cluster 成员价格：

```text
ZONE_CENTER = median(member_prices)
MAD = median(abs(price-ZONE_CENTER))
RAW_HALF_WIDTH = max(1.5*MAD, 0.15*A15_current)
ZONE_HALF_WIDTH = clamp(RAW_HALF_WIDTH, 0.15*A15_current, 0.40*A15_current)
ZONE_LOW  = ZONE_CENTER-ZONE_HALF_WIDTH
ZONE_HIGH = ZONE_CENTER+ZONE_HALF_WIDTH
```

### 6.6 Quality

```text
ZQ1 = 1 independent reaction
ZQ2 = >=2 independent reactions AND latest reaction age <=24 closed 15m bars
ZQ3 = >=3 independent reactions AND latest reaction age <=24 closed 15m bars
```

只有 ZQ2+ 可创建正式 Market Event。

超过 24 bars：

```text
ACTIVE_FOR_NEW_EVENT = NO
```

已创建 Event 继续使用创建时冻结的 Zone Snapshot。

### 6.7 Zone ID 与选择

```text
zone_id = sha256(
  market_id + zone_type + sorted(member_reaction_ids) + PARAMETER_VERSION
)
```

同类型 Zone 区间重叠达到较窄 Zone 宽度的 50% 时，活动选择只保留一个 Winner：

1. ZQ3 优于 ZQ2；
2. reaction count 多者；
3. latest reaction 更新者；
4. 当前价格距离近者；
5. zone_id 字典序小者。

被压制 Zone 继续保留证据。

```text
ACTIVE_SUPPORT = current close 下方或包含 current close 的最近 ZQ2+ Low Zone
ACTIVE_RESISTANCE = current close 上方或包含 current close 的最近 ZQ2+ High Zone
```

---

## 7. Market Event 与状态

```text
market_event_id = sha256(
  market_id
  + zone_id
  + side
  + first_attack_5m_candle_id
  + STRATEGY_VERSION
  + PARAMETER_VERSION
)
```

Same Event：

```text
same market_id
AND same zone_id
AND same side
AND prior event not terminal
```

一个 Market Event 最多生成一个正式 Shadow Plan。

每个 `market_id × setup_family × side` 最多一个 active unconfirmed Event。

新的独立 Event 出现时，旧未确认 Event：

```text
SUPERSEDED_BY_NEW_INDEPENDENT_EVENT
```

已生成 Shadow Plan 的历史 Event 不允许回写。

终态：

```text
CONFIRMED
INVALIDATED
SUPERSEDED
DATA_INVALID
UNRESOLVED_AT_SHUTDOWN
```

无固定 bar 或 wall-clock 经济超时。

---

## 8. Scanner 与正式策略边界

```text
WATCH
→ persist candidate + forward Outcome

SCANNER_SETUP_READY
→ eligible for full formal evaluator

FORMAL_SETUP_CONFIRMED
→ StrategyDecision + PlanDraft + ShadowOrder
```

`WATCH` 和 `SCANNER_SETUP_READY` 均不得直接生成 ShadowOrder。

Scanner R3 的 `RETEST_WINDOW_BARS=1..12` 只结束 Scanner 候选路径；不得让 Formal STANDARD 因该窗口结束而失效。

---

## 9. Sweep Reclaim

以下为扫 Support 后做多；做空镜像。

### 9.1 Candidate

冻结 Event 创建时的：

```text
A5_EVENT
ZONE_SNAPSHOT
M20_EVENT
```

```text
outside_excursion = ZONE_LOW - candle.low
```

必须：

```text
ZONE_QUALITY >= ZQ2
0.10*A5_EVENT <= outside_excursion <= 0.75*A5_EVENT
candle.close >= ZONE_LOW + 0.05*A5_EVENT
```

保存：

```text
reclaim_candle_high
reclaim_candle_low
sweep_extreme = candle.low
```

### 9.2 Confirmation

任意后续闭合 5m 第一次满足：

```text
close > reclaim_candle_high
AND low > sweep_extreme
AND close >= ZONE_LOW + 0.05*A5_EVENT
```

即 `FORMAL_SETUP_CONFIRMED`。

### 9.3 Invalidation / Supersession

```text
close <= ZONE_LOW - 0.05*A5_EVENT
→ INVALIDATED_ACCEPTED_OUTSIDE
```

若后续出现更低 low，但该 K 线重新满足 Candidate reclaim 条件：

```text
create new independent Sweep Event
old unconfirmed Event → SUPERSEDED
```

其他终止：

```text
OPPOSITE_FORMAL_EVENT
CHASE_LIMIT_EXCEEDED
TARGET_FEASIBILITY_FAILED
CORE_DATA_INVALID
```

### 9.4 Entry / Stop / Chase

Long：

```text
IDEAL_ENTRY_LOW  = ZONE_LOW + 0.05*A5_EVENT
IDEAL_ENTRY_HIGH = min(ZONE_CENTER, ZONE_LOW + 0.25*A5_EVENT)
CHASE_LIMIT      = ZONE_LOW + 0.35*A5_EVENT
STOP             = sweep_extreme - 0.10*A5_EVENT
STRUCTURAL_TARGET = ZONE_CENTER
```

Short 镜像。

---

## 10. Breakout Event

### 10.1 Initial Long Breakout

```text
close >= ZONE_HIGH + 0.15*A5_EVENT
body = abs(close-open)
body >= 0.50*A5_EVENT
CLV_LONG >= 0.70
volume >= 1.20*M20_EVENT
```

Short 镜像。

### 10.2 Accepted Re-entry

Long：

```text
close <= ZONE_HIGH - 0.05*A5_EVENT
```

Short：

```text
close >= ZONE_LOW + 0.05*A5_EVENT
```

触发即：

```text
INVALIDATED_ACCEPTED_REENTRY
```

如果同一 Market Event 尚未产生正式计划，且 re-entry K 线满足 Sweep Candidate，则路由为新的 Sweep Event；不得从原 Breakout Event 生成第二个 Plan。

---

## 11. Breakout Micro FAST

Long 在 Initial Breakout 后、尚未出现 Pullback Start 时，任意后续闭合 5m 第一次满足：

```text
close >= ZONE_HIGH + 0.10*A5_EVENT
AND low >= ZONE_HIGH - 0.10*A5_EVENT
AND (
  close > initial_breakout_close
  OR (low > initial_breakout_low AND close > open)
)
```

即确认。

Long：

```text
IDEAL_ENTRY_LOW  = ZONE_HIGH + 0.10*A5_EVENT
IDEAL_ENTRY_HIGH = ZONE_HIGH + 0.40*A5_EVENT
CHASE_LIMIT      = ZONE_HIGH + 0.75*A5_EVENT
STOP             = min(initial_breakout_low, ZONE_HIGH - 0.25*A5_EVENT)
```

Short 镜像。

---

## 12. Breakout STANDARD

### 12.1 Pullback Start

Long：Initial Breakout 后第一次 `close < previous_close` 的闭合 5m。

Short：第一次 `close > previous_close`。

Pullback Start 一旦发生，同一 Event 的 Micro FAST 路径关闭；Event 只继续 STANDARD 路径。

### 12.2 Impulse Extreme

Long：从 Initial Breakout 至 Pullback Start 前已观察到的最高 high。

Short：最低 low。

### 12.3 Deep Retest Long

Retest bar：

```text
low <= ZONE_HIGH + 0.25*A5_EVENT
AND close >= ZONE_HIGH + 0.05*A5_EVENT
AND no accepted re-entry
```

保存 pullback_low。

其后第一次：

```text
close > previous_closed_5m.high
```

即确认。

### 12.4 Shallow Retest Long

```text
pullback_low > ZONE_HIGH + 0.25*A5_EVENT
retrace_ratio = (impulse_high-pullback_low)/(impulse_high-ZONE_HIGH)
0.25 <= retrace_ratio <= 0.60
no accepted re-entry
```

其后第一次：

```text
close > previous_closed_5m.high
```

即确认。

Short 全部镜像。

### 12.5 Entry / Stop / Chase

Long：

```text
IDEAL_ENTRY_LOW  = ZONE_HIGH - 0.05*A5_EVENT
IDEAL_ENTRY_HIGH = ZONE_HIGH + 0.20*A5_EVENT
CHASE_LIMIT      = ZONE_HIGH + 0.35*A5_EVENT
STOP             = min(pullback_low, ZONE_HIGH - 0.10*A5_EVENT)
```

Short 镜像。

没有固定 1～6 bar 失效。

---

## 13. Breakout Mode Priority

同一 Breakout Market Event 最多一个正式计划。

顺序：

1. Accepted Re-entry 且满足 Sweep Candidate：原 Breakout 终止，创建新 Sweep Event；
2. Pullback Start 已发生：只允许 STANDARD；
3. Pullback Start 未发生：只允许 Micro FAST；
4. 第一个正式确认的路径关闭该 Market Event 的其他模式。

当前不实现 Immediate Displacement FAST。

---

## 14. Range Edge Rejection

### 14.1 Valid Range Pair

使用当前 ACTIVE_SUPPORT 与 ACTIVE_RESISTANCE，且两者均 ZQ2+。

```text
range_width = resistance_center-support_center
1.5*A15 <= range_width <= 5.0*A15
ER8_15M <= 0.35
abs(C15[-1]-C15[-9]) <= 1.0*A15
```

并且最近 8 根闭合 15m 的 close 全部满足：

```text
support_low - 0.10*A15
<= close
<= resistance_high + 0.10*A15
```

否则 Range 无效。

```text
RANGE_CENTER = (support_center+resistance_center)/2
```

### 14.2 Long Edge Rejection

```text
low <= support_high + 0.10*A5_EVENT
close >= support_low + 0.05*A5_EVENT
CLV_LONG >= 0.70
lower_wick/true_range >= 0.35
volume >= M20_EVENT
```

```text
IDEAL_ENTRY_LOW  = support_low
IDEAL_ENTRY_HIGH = support_high + 0.10*A5_EVENT
CHASE_LIMIT      = support_high + 0.35*A5_EVENT
STOP             = event_low - 0.10*A5_EVENT
STRUCTURAL_TARGET = RANGE_CENTER
```

### 14.3 Short Edge Rejection

全部镜像：

```text
high >= resistance_low - 0.10*A5_EVENT
close <= resistance_high - 0.05*A5_EVENT
CLV_SHORT >= 0.70
upper_wick/true_range >= 0.35
volume >= M20_EVENT
```

### 14.4 Range Invalidation

```text
15m close < support_low - 0.10*A15
OR
15m close > resistance_high + 0.10*A15
OR
Range Pair no longer satisfies section 14.1
```

1h 不过滤任何一侧。

---

## 15. BBO、Planned Entry 和 Entry Quality

正式 Setup 确认后取得 BBO。

BBO 必须：

```text
age <= 10 seconds
best_bid > 0
best_ask > best_bid
spread_bps <= HARD_MAX_SPREAD_BPS
```

Long：

```text
planned_entry = best_ask rounded according to market tick
```

Short：

```text
planned_entry = best_bid rounded according to market tick
```

如果 planned_entry 位于 Ideal Entry Zone：

```text
ENTRY_QUALITY = IDEAL
```

如果在 Ideal Entry Zone 外但未超过 Chase Limit：

```text
ENTRY_QUALITY = LATE_BUT_WITHIN_CHASE
```

超过 Chase Limit：

```text
SHADOW_PLAN = NO
REJECTION = CHASE_LIMIT_EXCEEDED
```

不得使用未来下一根 K 线 Open 作为计划入场价。

---

## 16. Target Feasibility、TP1 和 TP2

```text
risk_distance = abs(planned_entry-structural_stop)
```

必须 `risk_distance > 0` 且方向与 Stop 顺序正确。

```text
round_trip_cost_price = planned_entry*(2*fee_bps_per_side + 2*slippage_bps_per_side)/10000
net_R_to_target = (abs(structural_target-planned_entry)-round_trip_cost_price)/risk_distance
```

正式门槛：

```text
net_R_to_target >= 1.00
```

结构目标：

- Sweep：Zone Center；
- Range：Range Center；
- Breakout：方向上最近的、创建时已存在的对侧 ZQ2+ Zone near edge；
- Breakout 若 2R 内没有对侧 Zone：`OPEN_SPACE_REFERENCE`，结构参考目标=`2R`。

```text
TP1 = planned_entry +/- 1.0*risk_distance
```

如果结构目标距离 `>=1.25R`：

```text
TP2 = structural_target capped at 2R
```

否则：

```text
TP2 = NONE
```

费用与滑点属于版本化 Config，不写死在策略代码。当前基础研究配置：

```text
fee_bps_per_side = 4.5
slippage_bps_per_side = 2.0
stress_slippage_bps_per_side = 5.0
```

---

## 17. 参考数量与金额

```text
REFERENCE_SHADOW_EQUITY_USD = 200
REFERENCE_RISK_PCT_1 = 1.0
REFERENCE_RISK_PCT_2 = 2.0
REFERENCE_MAX_NOTIONAL_USD = 5000
```

对每个风险档：

```text
risk_budget = reference_equity*risk_pct/100
estimated_loss_per_unit = risk_distance + entry_cost_per_unit + stop_exit_cost_per_unit
risk_limited_qty = risk_budget/estimated_loss_per_unit
leverage_cap_notional = reference_equity*max_leverage if max_leverage available else REFERENCE_MAX_NOTIONAL_USD
effective_max_notional = min(REFERENCE_MAX_NOTIONAL_USD, leverage_cap_notional)
notional_limited_qty = effective_max_notional/planned_entry
reference_qty = floor_to_size_decimals(min(risk_limited_qty, notional_limited_qty))
reference_notional = reference_qty*planned_entry
```

输出：

```text
reference_qty_1pct
reference_notional_1pct
reference_qty_2pct
reference_notional_2pct
REFERENCE_SIZE_ONLY = YES
NOT_ACCOUNT_AUTHORITATIVE = YES
```

数量舍入后为 0：仍保留 Signal，但标记：

```text
REFERENCE_SIZE_UNAVAILABLE
```

---

## 18. Re-entry

Range 不进入趋势 Re-entry 分类。

对 Sweep/Breakout：

```text
FIRST_ENTRY = 自最近 opposite formal signal 或明确反向 HTF_STRUCTURE 后的首个同向正式 Signal
```

```text
REENTRY_N = 已有同向正式 Signal后，新的 independent market_event_id 产生的同向正式 Signal，且期间没有 opposite formal signal 或明确反向 HTF_STRUCTURE
```

每个 Re-entry 有独立 Signal、Plan、Stop、Outcome。

---

## 19. T/S/R

T/S/R 主要绑定 `shadow_order_id`。

```text
T = TAKEN
交易员接受计划并决定执行或尝试执行；不等于已经成交。

S = SKIPPED
认为机会可能成立，但因非策略原因未执行。

R = REJECTED
认为机会本身存在结构、策略、流动性、执行或数据问题。
```

S 原因码：

```text
NOT_SEEN_IN_TIME
NO_CAPACITY
CONFLICTING_POSITION
PERSONAL_AVAILABILITY
OTHER_NON_STRATEGY
```

R 原因码：

```text
STRUCTURE_CONFLICT
ENTRY_TOO_LATE
CHASE_EXCEEDED
LIQUIDITY_POOR
RISK_REWARD_INSUFFICIENT
DATA_QUALITY
SIGNAL_LOGIC_ERROR
OTHER_STRATEGY_REASON
```

未标记：

```text
ANNOTATION_STATUS = UNLABELED
```

所有 T/S/R/UNLABELED 都进入自动 Outcome；必须分开报告。

重要 WATCH 只能使用 `human_attention_flag` 和 `human_note`，不得标记 TAKEN。

---

## 20. Outcome

普通 WATCH：从 Candidate reference price 计算 30/60/120m forward MFE/MAE，不宣称交易结果。

正式 Shadow Plan：优先使用 1m 路径计算：

```text
MFE_30M / MAE_30M
MFE_60M / MAE_60M
MFE_120M / MAE_120M
TP1_HIT
TP2_HIT
STOP_HIT
TIME_TO_1R
MAX_MFE_BEFORE_STOP
MAX_PROFIT_GIVEBACK
RETURN_TO_ENTRY_AFTER_PROFIT
UNRESOLVED
```

同一根 1m 同时触及 Stop 和 Target：

```text
AMBIGUOUS_PATH = YES
PRIMARY_RESULT = STOP_FIRST
```

Outcome 不得回写或改变 Signal、Plan 或历史策略状态。

---

## 21. 最小拒绝原因码

```text
MARKET_METADATA_INCOMPLETE
MULTITIMEFRAME_DATA_INVALID
INSUFFICIENT_HISTORY
ATR_INVALID
ZONE_NOT_QUALIFIED
RANGE_NOT_VALID
SETUP_CONDITION_NOT_MET
SCANNER_ONLY_NOT_FORMAL
DUPLICATE_MARKET_EVENT
SUPERSEDED_BY_NEW_INDEPENDENT_EVENT
INVALIDATED_ACCEPTED_OUTSIDE
INVALIDATED_ACCEPTED_REENTRY
OPPOSITE_FORMAL_EVENT
CHASE_LIMIT_EXCEEDED
TARGET_FEASIBILITY_FAILED
BBO_INVALID_OR_STALE
LIQUIDITY_HARD_LIMIT
REFERENCE_SIZE_UNAVAILABLE
UNRESOLVED_AT_SHUTDOWN
```

---

## 22. 最小 Fixtures

每个方向镜像测试。

必须至少覆盖：

1. 1h Momentum Up/Down/Neutral/Unavailable；
2. 1h Structure Up/Down/Range/Transition/Insufficient；
3. Zone reaction qualification、independence、cluster tie-break、ZQ2/ZQ3；
4. Sweep confirm、accepted-outside invalidation、new deeper sweep supersession；
5. Breakout Micro confirm；
6. STANDARD shallow/deep retest；
7. STANDARD 跨越 6 根 5m 后仍有效；
8. accepted re-entry 路由到 Sweep；
9. Range Long/Short；
10. same-event dedup；
11. independent re-entry；
12. BBO stale；
13. Chase failure；
14. Target Feasibility failure；
15. reference size 1%/2%；
16. Outcome ambiguous path；
17. ETH 与至少一个非 ETH 使用相同策略字段和计算路径。

---

## 23. 当前不包含

```text
IMMEDIATE_DISPLACEMENT_FAST
SAME_BAR_SWEEP_FAST
RANGE_STANDARD
FOURTH_SETUP
OI_OR_FUNDING_HARD_TRIGGER
L2_ORDER_FLOW_HARD_TRIGGER
DYNAMIC_EXIT_ENGINE
AUTOMATIC_ORDER_SUBMISSION
PORTFOLIO_CAPITAL_ARBITRATION
LONG_TERM_HISTORICAL_BACKTEST_PLATFORM
```

---

## 24. 工程解释禁止

Engineering 不得自行改变：

- 任何阈值；
- Setup 条件；
- Signal/Scanner 权威边界；
- Entry/Stop/TP 公式；
- T/S/R 含义；
- 参考金额语义；
- 无固定经济超时原则。

若实现中仍发现不能唯一编码的冲突，必须一次性列出精确表达式和冲突位置，返回 Strategy Optimization；不得用“合理默认值”自行填补。

本文件不授权实现、部署、重启、账户访问、签名或交易所写入。