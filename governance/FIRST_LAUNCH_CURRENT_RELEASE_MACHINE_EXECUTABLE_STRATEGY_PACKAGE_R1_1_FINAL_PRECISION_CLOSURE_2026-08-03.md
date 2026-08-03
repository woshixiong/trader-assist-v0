# First Launch 当前发布机器策略包 R1.1 最终精度闭环

**记录 ID：** `TA-FIRST-LAUNCH-MACHINE-STRATEGY-R1.1-PRECISION-CLOSURE-2026-08-03`  
**日期：** `2026-08-03`  
**状态：** `FINAL PRECISION CLOSURE / NON-EXECUTABLE / NON-AUTHORIZING`  
**父合同：** `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_2026-08-03.md`  
**优先级：** 本文件关闭 R1 中剩余的镜像、身份、成本与目标精度问题；冲突时 `R1.1 > R1 > R5`。R1 中未被本文件修改的内容继续有效。

---

## 1. Market Identity 精度闭环

```text
venue = HYPERLIQUID
```

```text
dex = MAIN
```

用于 Hyperliquid 原生 perp。

对 builder/HIP-3 DEX：

```text
dex = exact non-empty DEX name returned by the authoritative public metadata source
```

```text
coin = exact non-empty API coin string used by the corresponding candle/BBO endpoint
```

不得自行去除 DEX 前缀、改变大小写或使用显示名称替代 API coin。

```text
market_key = "HYPERLIQUID|" + dex + "|" + coin
market_id = lowercase_hex_sha256(UTF8(market_key))
```

---

## 2. 固定流动性硬门槛

正式 Shadow Plan 创建时：

```text
HARD_MAX_SPREAD_BPS = 40
HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS = 35
PRIMARY_REFERENCE_NOTIONAL_USD = 1000
```

任一超过：

```text
SHADOW_PLAN = NO
REJECTION = LIQUIDITY_HARD_LIMIT
```

Preferred 20bps 只作为 Warning / Attribution，不是正式硬拒绝。

---

## 3. Sweep Short 唯一公式

扫 Resistance 后做空：

```text
outside_excursion = candle.high - ZONE_HIGH
0.10*A5_EVENT <= outside_excursion <= 0.75*A5_EVENT
candle.close <= ZONE_HIGH - 0.05*A5_EVENT
sweep_extreme = candle.high
reclaim_candle_low = candle.low
```

后续首次：

```text
close < reclaim_candle_low
AND high < sweep_extreme
AND close <= ZONE_HIGH - 0.05*A5_EVENT
```

即确认。

失效：

```text
close >= ZONE_HIGH + 0.05*A5_EVENT
→ INVALIDATED_ACCEPTED_OUTSIDE
```

更高 high 且该 K 线重新满足 Short Sweep Candidate：创建新 Event，旧未确认 Event `SUPERSEDED`。

```text
IDEAL_ENTRY_LOW  = max(ZONE_CENTER, ZONE_HIGH - 0.25*A5_EVENT)
IDEAL_ENTRY_HIGH = ZONE_HIGH - 0.05*A5_EVENT
CHASE_LIMIT      = ZONE_HIGH - 0.35*A5_EVENT
STOP             = sweep_extreme + 0.10*A5_EVENT
STRUCTURAL_TARGET = ZONE_CENTER
```

Short planned entry 必须 `>= CHASE_LIMIT`；低于 Chase Limit 表示已经向下追价过度。

---

## 4. Breakout Micro FAST Short 唯一公式

Initial Short Breakout：

```text
close <= ZONE_LOW - 0.15*A5_EVENT
body >= 0.50*A5_EVENT
CLV_SHORT >= 0.70
volume >= 1.20*M20_EVENT
```

Pullback Start 尚未发生时，后续首次：

```text
close <= ZONE_LOW - 0.10*A5_EVENT
AND high <= ZONE_LOW + 0.10*A5_EVENT
AND (
  close < initial_breakout_close
  OR (high < initial_breakout_high AND close < open)
)
```

即确认。

```text
IDEAL_ENTRY_LOW  = ZONE_LOW - 0.40*A5_EVENT
IDEAL_ENTRY_HIGH = ZONE_LOW - 0.10*A5_EVENT
CHASE_LIMIT      = ZONE_LOW - 0.75*A5_EVENT
STOP             = max(initial_breakout_high, ZONE_LOW + 0.25*A5_EVENT)
```

Short planned entry 必须 `>= CHASE_LIMIT`。

Accepted Re-entry：

```text
close >= ZONE_LOW + 0.05*A5_EVENT
```

---

## 5. Breakout STANDARD Short 唯一公式

Pullback Start：Initial Short Breakout 后第一次：

```text
close > previous_close
```

Impulse Extreme：从 Initial Breakout 到 Pullback Start 前最低 low，记为 `impulse_low`。

Deep Retest bar：

```text
high >= ZONE_LOW - 0.25*A5_EVENT
AND close <= ZONE_LOW - 0.05*A5_EVENT
AND no accepted re-entry
```

保存 `pullback_high`。其后第一次：

```text
close < previous_closed_5m.low
```

即确认。

Shallow Retest：

```text
pullback_high < ZONE_LOW - 0.25*A5_EVENT
retrace_ratio = (pullback_high-impulse_low)/(ZONE_LOW-impulse_low)
0.25 <= retrace_ratio <= 0.60
no accepted re-entry
```

其后第一次：

```text
close < previous_closed_5m.low
```

即确认。

```text
IDEAL_ENTRY_LOW  = ZONE_LOW - 0.20*A5_EVENT
IDEAL_ENTRY_HIGH = ZONE_LOW + 0.05*A5_EVENT
CHASE_LIMIT      = ZONE_LOW - 0.35*A5_EVENT
STOP             = max(pullback_high, ZONE_LOW + 0.10*A5_EVENT)
```

Short planned entry 必须 `>= CHASE_LIMIT`。

---

## 6. Range Short 唯一公式

Resistance Edge Rejection：

```text
high >= resistance_low - 0.10*A5_EVENT
close <= resistance_high - 0.05*A5_EVENT
CLV_SHORT >= 0.70
upper_wick = high - max(open, close)
true_range = max(high-low, abs(high-previous_close), abs(low-previous_close))
upper_wick/true_range >= 0.35
volume >= M20_EVENT
```

```text
IDEAL_ENTRY_LOW  = resistance_low - 0.10*A5_EVENT
IDEAL_ENTRY_HIGH = resistance_high
CHASE_LIMIT      = resistance_low - 0.35*A5_EVENT
STOP             = event_high + 0.10*A5_EVENT
STRUCTURAL_TARGET = RANGE_CENTER
```

Short planned entry 必须 `>= CHASE_LIMIT`。

Range Long 对应 true range 与 lower wick：

```text
lower_wick = min(open, close)-low
lower_wick/true_range >= 0.35
```

---

## 7. Planned Entry 与 Chase 唯一判断

Long：

```text
planned_entry = tick-rounded best_ask
within_chase = planned_entry <= CHASE_LIMIT
```

Short：

```text
planned_entry = tick-rounded best_bid
within_chase = planned_entry >= CHASE_LIMIT
```

Entry Quality：

```text
IDEAL_ENTRY_LOW <= planned_entry <= IDEAL_ENTRY_HIGH
→ IDEAL

within_chase AND outside ideal zone
→ LATE_BUT_WITHIN_CHASE

NOT within_chase
→ no Shadow Plan; CHASE_LIMIT_EXCEEDED
```

---

## 8. Opposite Event 与 Supersession 唯一含义

```text
OPPOSITE_FORMAL_EVENT
=
same market_id
AND opposite side
AND FORMAL_SETUP_CONFIRMED after current Event creation
```

触发后，当前未确认 Event：

```text
INVALIDATED_BY_OPPOSITE_FORMAL_EVENT
```

```text
NEW_INDEPENDENT_EVENT
=
same market_id
AND same setup family
AND same side
AND different market_event_id
```

每个 `market_id × setup_family × side` 只保留最新 active unconfirmed Event；旧者 `SUPERSEDED`。

不同 Setup 的同方向 Event 不互相 Supersede；但一个底层 Breakout Event 按 R1 第 13 节 Mode Priority 最多生成一个正式 Plan。

---

## 9. Breakout 结构目标唯一选择

Long Breakout：

- 在 Event 创建时已存在的 ZQ2+ High Zone 中，选择 `zone_low > planned_entry` 且 `zone_low` 最小者；
- `structural_target = selected zone_low`。

Short Breakout：

- 在 Event 创建时已存在的 ZQ2+ Low Zone 中，选择 `zone_high < planned_entry` 且 `zone_high` 最大者；
- `structural_target = selected zone_high`。

若不存在，或最近目标距离超过 2R：

```text
TARGET_CONTEXT = OPEN_SPACE_REFERENCE
structural_target = planned_entry +/- 2*risk_distance
```

正号用于 Long，负号用于 Short。

---

## 10. TP1 / TP2 唯一公式

Long：

```text
TP1 = planned_entry + 1.0*risk_distance
```

Short：

```text
TP1 = planned_entry - 1.0*risk_distance
```

若结构目标 gross distance `<1.25R`：

```text
TP2 = NONE
```

否则：

```text
Long TP2  = min(structural_target, planned_entry + 2.0*risk_distance)
Short TP2 = max(structural_target, planned_entry - 2.0*risk_distance)
```

Target Feasibility 仍以结构目标的成本后 `net_R >=1.00` 为准。

---

## 11. 成本与参考数量唯一公式

```text
entry_cost_per_unit = planned_entry*(fee_bps_per_side+slippage_bps_per_side)/10000
stop_cost_per_unit  = structural_stop*(fee_bps_per_side+slippage_bps_per_side)/10000
estimated_loss_per_unit = abs(planned_entry-structural_stop)+entry_cost_per_unit+stop_cost_per_unit
```

```text
round_trip_cost_to_target_per_unit =
planned_entry*(fee_bps_per_side+slippage_bps_per_side)/10000
+
structural_target*(fee_bps_per_side+slippage_bps_per_side)/10000
```

```text
net_R_to_target =
(abs(structural_target-planned_entry)-round_trip_cost_to_target_per_unit)
/
risk_distance
```

Reference quantity 使用 `estimated_loss_per_unit`，不得使用仅价格距离的简化值。

如果 `max_leverage` 不可用：

```text
leverage_cap_notional = REFERENCE_MAX_NOTIONAL_USD
```

如果可用：

```text
leverage_cap_notional = REFERENCE_SHADOW_EQUITY_USD*max_leverage
```

---

## 12. Current State

经过本文件闭环后：

```text
STRATEGY_MACHINE_SEMANTICS = CLOSED
USER_PARAMETER_DECISION_REQUIRED = NO
READY_FOR_ENGINEERING_ROUTE = YES
```

Engineering 仅可提出实现冲突或数据不可得问题，不得重新解释策略参数。

本文件不授权代码修改、依赖安装、部署、账户访问、签名或交易所写入。