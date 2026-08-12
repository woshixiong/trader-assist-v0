# First Launch 固定 40 市场人工 Registry 快速路线与 Timeframe Profile Backlog R1

**记录 ID：** `TA-FIRST-LAUNCH-MANUAL-40-REGISTRY-FAST-ROUTE-TIMEFRAME-BACKLOG-R1-2026-08-12`  
**日期：** `2026-08-12`  
**状态：** `CURRENT PRODUCT/ENGINEERING ROUTE AUTHORITY / NON-EXECUTABLE / NON-AUTHORIZING`  
**适用：** 当前多资产 First Launch 快速上线；Post-Launch / V0.2 条件性策略优化 Backlog  
**目的：** 用最低开发成本替代此前高成本的全市场自动发现与扩张容量路线，同时固定当前时间周期语义以及未来按市场配置稳定 Timeframe Profile 的研究/开发入口。

---

## 1. 当前 Universe / API 路线

当前发布采用：

```text
MANUALLY_MAINTAINED_VERSIONED_MARKET_REGISTRY = YES
INITIAL_MARKET_COUNT = 40
HOT_ADD_REMOVE_TIER_CHANGE = REQUIRED
FULL_EXCHANGE_DYNAMIC_DISCOVERY = NO
EXPANDING_CAPACITY_HARNESS = CANCELLED_FOR_CURRENT_RELEASE
AUTOMATIC_UNIVERSE_SCORING = NO
AUTOMATIC_WHOLE_EXCHANGE_REFRESH = NO
```

40 个市场由用户人工维护并可不定期增删或调整 P0/P1/P2。Registry 更新不得要求修改策略代码、重新发布版本或完整重新部署；应在验证后原子应用，并在安全 closed-5m 边界生效。

当前 P0/P1/P2 初始名单与精确工程实现以最新 Engineering Optimization 任务包为准；其中所有 Tier 均运行完整三 Setup、Formal Signal、ShadowOrder 和 Outcome。Tier 只影响展示优先级、真实执行资格和可选的数据获取深度。

---

## 2. 当前唯一时间周期语义

本轮固定：

```text
RAW_STRATEGY_CANDLE_FEED = 5m ONLY
SIGNAL_BASE_TIMEFRAME = 5m
STRUCTURE_TIMEFRAME = 15m
CONTEXT_TIMEFRAME = 1h
OUTCOME_PATH_TIMEFRAME = 1m ON DEMAND FOR FORMAL SHADOW PLANS
```

15m 与 1h 必须由同一套已闭合、已确认的 5m K 线严格因果聚合：

```text
5m → local 15m
5m → local 1h
```

不得为了 15m/1h 再维护独立持续 Candle Feed，除非未来另有独立证据和版本化合同。

当前所有市场统一使用：

```text
FAST_5M_PROFILE
Execution = 5m
Structure = 15m
Context = 1h
```

不同市场波动差异继续通过 A5/A15/A1H、ATR-normalized distance、Chase、Stop、Target 和参考仓位等机器策略语义处理。

---

## 3. 本轮明确不开发实时动态周期切换

禁止当前版本实现：

```text
REALTIME_DYNAMIC_TIMEFRAME_SWITCH
```

例如不得根据短期波动率在同一市场运行过程中实时：

```text
5m → 15m → 5m
```

主要原因：

- 会改变 Event / Zone / Confirmation 语义；
- 容易产生同一行情的重复或错配 Signal；
- 破坏不同市场和不同阶段的样本可比性；
- 增加状态迁移、恢复、测试和审计复杂度；
- 容易引入事后选择有利周期的偏差；
- 当前缺少真实前向证据证明收益足以覆盖开发成本。

固定：

```text
REALTIME_DYNAMIC_TIMEFRAME_SWITCH = NOT_PLANNED
CURRENT_ACTIVE_TIMEFRAME_PROFILE = FAST_5M_ONLY
```

---

## 4. Post-Launch / V0.2 条件性 Backlog：Per-Market Stable Timeframe Profile

未来有价值的方向不是“实时动态切换”，而是：

```text
PER_MARKET_STABLE_TIMEFRAME_PROFILE
```

建议阶段：

```text
POST_FIRST_LAUNCH
V0.2 / STRATEGY_OPTIMIZATION_PHASE
CONDITIONAL_BACKLOG
```

该功能不能因为进入 Backlog 就自动开发。只有前向证据达到下列任一触发条件，Strategy Optimization 才重新开启研究：

1. 某些市场长期表现出 5m 噪声显著过高；
2. 某些市场的 5m Formal Signals 在成本后 Net Edge 持续显著弱于可解释的较慢周期替代方案；
3. 某些市场的 15m Zone 在当前波动结构下长期过宽，导致 Entry/Stop/Target 经济性明显恶化；
4. Shadow / Offline 对照证明一个稳定较慢 Profile 在足够样本内持续改善 Net Expectancy、回撤或执行可靠性；
5. 当前 5m Profile 导致某类资产持续产生大量噪声/重复/低价值 Formal Signal，而不是单次偶发现象。

未来候选示例：

```text
FAST_INTRADAY_PROFILE
Execution = 5m
Structure = 15m
Context = 1h

SLOW_INTRADAY_PROFILE  # only if future evidence supports it
Execution = 15m
Structure = 1h
Context = 4h
```

SLOW Profile 当前没有参数授权，也不是简单把 5m 数字替换成 15m；如未来立项，必须重新冻结完整 Machine Semantics，包括历史长度、ATR、Zone、Event、Confirmation、Chase、Stop、Target、Outcome 和版本身份。

---

## 5. Registry Schema 的未来兼容要求

当前 Registry 可以低成本预留字段：

```text
timeframe_profile = FAST_5M
```

但本轮只允许唯一有效值：

```text
FAST_5M
```

不得因为预留字段而提前实现多 Profile 分支。

未来 V0.2 若经用户和 Strategy Optimization 明确授权，可以把该字段扩展为版本化、稳定的 per-market Profile 选择；Profile 变更应只在安全边界发生，不能在同一个活动 Market Event 中途切换。

---

## 6. 1m 数据的当前定位

取消：

```text
FULL_UNIVERSE_CONTINUOUS_1M
```

保留：

```text
FORMAL_SHADOW_ORDER
→ 1m ON-DEMAND PATH
→ STOP/TP ORDERING
→ MFE/MAE
→ 30/60/120m OUTCOME
→ unsubscribe when no active outcome remains
```

这不会降低三 Setup 的 Signal Detection / Confirmation 准确性，因为正式策略信号由 5m + 本地 15m/1h 产生。1m 负责正式 ShadowOrder 之后的 Outcome 路径精度，并可用 REST backfill 补齐中断。

---

## 7. 手续费功能当前工程边界

本轮手续费功能只有在**非常小**的情况下加入：

```text
OPTIONAL_MICRO_FEE_GUARD
TOTAL_INCREMENTAL_ENGINEERING_TIME_INCLUDING_TESTS <= 90 MINUTES
```

允许的最小功能：

- 读取现有 HIP-3 metadata 中的 `growthMode`；
- 保存 `growth_mode`、`fee_class`、`fee_observed_at`；
- P0 HIP-3 在 Growth Mode 不满足时标记 `FEE_EXECUTION_BLOCKED`；
- Shadow research 继续，不删除 Formal Signal / ShadowOrder / Outcome。

如果 Engineering 核验认为包含测试的总增量：

```text
> 90 minutes
```

则当前发布立即延期该功能，继续依赖人工维护 P0 Fee Eligibility。

当前明确不开发：

- `userFees` 账户级集成；
- 精确账户 fee tier；
- staking/referral discount；
- TT/MT/MM 完整净收益引擎；
- 自动 maker/taker routing；
- 自动按手续费换市场；
- 自动 Net Opportunity 拒绝。

这些进入 Post-Launch Cost Model R2 条件性 Backlog。

---

## 8. 当前开发优先级

当前 First Launch 继续优先：

```text
Manual Hot-Plug Registry
→ Generic Multi-Asset 5m Data Core
→ Causal 15m/1h Aggregation
→ Asset-Neutral Three-Setup Kernel
→ Formal Signal / ShadowOrder
→ On-Demand BBO/L2
→ On-Demand 1m Outcome
→ T/S/R + Evidence + Export
→ Correlation Cluster Evidence
→ Unified Notifications
→ Optional <=90m Fee Guard
→ 40-Market Load Smoke
→ Ops Blockers
→ Review / Rollback / Deploy / Cutover
→ Shadow Forward Validation
```

不得让未来 Timeframe Profile Backlog 阻塞当前发布。

---

## 9. 最终固定状态

```text
CURRENT_RAW_CANDLE = 5m ONLY
CURRENT_SIGNAL_TIMEFRAME = 5m
CURRENT_STRUCTURE_TIMEFRAME = 15m LOCAL_FROM_5m
CURRENT_CONTEXT_TIMEFRAME = 1h LOCAL_FROM_5m
CURRENT_FULL_UNIVERSE_CONTINUOUS_1m = NO
CURRENT_FORMAL_OUTCOME_1m = ON_DEMAND
CURRENT_REALTIME_DYNAMIC_TIMEFRAME_SWITCH = NO

FUTURE_PER_MARKET_STABLE_TIMEFRAME_PROFILE = YES_CONDITIONAL
FUTURE_STAGE = POST_LAUNCH_V0.2_STRATEGY_OPTIMIZATION
FUTURE_DEVELOPMENT_REQUIRES_FORWARD_EVIDENCE = YES

CURRENT_MANUAL_HOT_PLUG_REGISTRY = YES
CURRENT_INITIAL_MARKET_COUNT = 40
CURRENT_EXPANDING_CAPACITY_HARNESS = CANCELLED

OPTIONAL_MICRO_FEE_GUARD_BUDGET = <=90_MINUTES_INCLUDING_TESTS
FEE_GUARD_OVER_BUDGET_ACTION = DEFER
```

本文件不授权代码修改、部署、重启、账户访问、签名、交易所写入、自动交易、PR Mark Ready 或 Merge。