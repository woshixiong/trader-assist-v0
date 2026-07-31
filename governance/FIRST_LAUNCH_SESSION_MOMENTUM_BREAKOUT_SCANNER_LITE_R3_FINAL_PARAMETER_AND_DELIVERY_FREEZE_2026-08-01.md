# First Launch Session Momentum Breakout Scanner Lite R3 最终参数与交付范围冻结

**记录 ID：** `TA-FIRST-LAUNCH-SCANNER-LITE-R3-2026-08-01`  
**日期：** 2026-08-01  
**状态：** `FINAL RESEARCH / PARAMETER / PRODUCT SCOPE FREEZE / NON-EXECUTABLE`  
**关联：** PR #52、R1 条件性计划、R2 研究与范围冻结、First Launch 三 Setup 最小上线计划  
**优先级：** 与 R1/R2 冲突时，以本文件 R3 为准。  
**权限边界：** 本文不授权代码修改、依赖安装、部署、服务启动、账户访问、交易所写入、自动切换资产或自动下单。实施必须由 Project Control 在工程与产品范围确认后单独派发。

---

## 1. 最终产品目标

First Launch 的目标不是最大化盈利，也不是证明自动交易级别的稳定优势，而是尽快产生足够多、可审计、可复盘的真实市场候选与正式信号样本，用于验证：

1. Scanner 的候选发现参数和两级分级是否合理；
2. `SWEEP_RECLAIM`、`BREAKOUT_RETEST`、`RANGE_EDGE_REJECTION` 三个 Setup 是否经得起实盘环境检验；
3. 数据、候选、信号、TradePlan、通知、人工判断、影子结果、真实成交和复盘流程是否顺畅。

固定原则：

```text
SCANNER_BIAS = HIGH_RECALL
HUMAN_FINAL_FILTER = REQUIRED
COMPLETE_EVIDENCE = REQUIRED
AUTO_TRADE = NO
AUTO_ASSET_SWITCH = NO
```

候选过少本身是 First Launch 的测试失败风险。

---

## 2. 系统定位与边界

Scanner 是候选发现层，不是第四个 Setup，也不直接拥有正式交易权威。

```text
ALL ELIGIBLE HYPERLIQUID PERPS
→ MARKET QUALITY GATES
→ MOMENTUM / RELATIVE STRENGTH / STRUCTURE SCAN
→ WATCH / SETUP_READY
→ EXISTING SETUP AUTHORITY OR HUMAN REVIEW
→ T/S/R + SHADOW/ACTUAL OUTCOME
```

固定边界：

```text
SCANNER_OUTPUT != PRODUCTION_CONFIRMED_SIGNAL
FINAL_SETUP_AUTHORITY = EXISTING_THREE_SETUP_ENGINE_WHERE_REUSABLE
FINAL_TRADE_DECISION = HUMAN
MANUAL_EXECUTION_REQUIRED = YES
```

Scanner 与 ETH 主运行时可以进入同一发布包和同一次部署，但默认保持独立模块、独立失败边界：

```text
SAME_RELEASE = TARGET
SAME_DEPLOYMENT = TARGET
SAME_RUNTIME_PROCESS = NO_BY_DEFAULT
SCANNER_FAILURE_MUST_NOT_DEGRADE_ETH_RUNTIME = REQUIRED
```

---

## 3. 市场 Universe

第一版发现并评估所有能够通过最低市场质量门槛的 Hyperliquid 永续市场，包括：

- 原生加密资产；
- 高流动性及其他山寨币；
- HIP-3 股票；
- 股票指数；
- 黄金、原油及其他商品；
- 其他 builder-deployed perpetual markets。

资产类别仅作为标签和统计维度，不作为硬排除条件。

### 3.1 硬拒绝条件

仅在以下情况拒绝进入扫描：

- 市场已暂停、结算、下线或不可交易；
- metadata、mid、mark、BBO 或必要 candle 缺失、陈旧、冲突；
- 价格、oracle/mark 偏离、精度或市场状态明显异常；
- BBO 为空；
- 历史长度不足以计算最低基线；
- 当前点差或参考名义滑点超过绝对安全上限；
- 无法保存 point-in-time 证据。

### 3.2 历史长度

```text
MIN_5M_CANDLES_FOR_WATCH = 64
MIN_5M_CANDLES_FOR_SETUP_READY = 288
MIN_15M_CANDLES_FOR_CONTEXT = 32
```

拥有 64–287 根 5m candle 的新市场可以进入 `WATCH_NEW_MARKET`，但不得进入 `SETUP_READY`。

---

## 4. 扫描频率与时段

第一版不只在固定两个小时运行。每一根闭合 5m candle 后执行一次扫描：

```text
SCAN_CADENCE = EVERY_CLOSED_5M_CANDLE
SCAN_INTERVAL_SECONDS_NOMINAL = 300
```

固定时段只作为锚点、显示标签和后续归因维度：

```text
ASIA_ANCHOR = 07:00 Asia/Shanghai
ASIA_ACTIVE_LABEL = 07:00-10:00 Asia/Shanghai

US_CASH_ANCHOR = 09:30 America/New_York
US_ACTIVE_LABEL = 09:30-11:30 America/New_York

CONTINUOUS_24_7_SCAN = ENABLED
MANUAL_SCAN = ENABLED
```

`America/New_York` 必须用于自动处理夏令时。

### 4.1 动量观察周期

```text
RETURN_HORIZONS = 15m, 30m, 60m
SESSION_RETURN = current_mid / session_anchor_mid - 1
```

每个周期分别计算，不允许用窗口结束后的数据回填早期候选。

---

## 5. 数据获取与 API 预算原则

优先使用 Hyperliquid 官方公开接口：

- `perpDexs` / `allPerpMetas`：市场发现和元数据；
- `allMids` / `allDexsAssetCtxs`：全市场廉价更新；
- `candleSnapshot`：少量候选的 5m/15m 历史；
- `bbo` 或 `l2Book`：最终候选点差、深度与滑点估算。

建议两阶段获取：

```text
STAGE_A_ALL_MARKETS
- metadata
- mids
- asset contexts
- cheap return/activity ranking

STAGE_B_TOP_CANDIDATES
- 5m candles
- optional 15m context
- BBO/L2
- structure/retest state
```

不得为所有市场持续运行完整三 Setup。

API 调用必须有预算、缓存、候选数量上限和 fail-closed 行为。工程 Spike 必须核对官方权重和实际 DEX 数量。

---

## 6. 多维流动性定义

不得将流动性等同于 24h 成交量。

最低记录：

```text
24h_notional_volume
open_interest
spread_bps
best_bid_size
best_ask_size
book_depth_within_10bps
book_depth_within_20bps
estimated_one_way_slippage_bps_at_reference_notional
turnover_to_open_interest
```

### 6.1 参考名义金额

```text
REFERENCE_NOTIONAL_USD_PRIMARY = 1000
REFERENCE_NOTIONAL_USD_SECONDARY = 5000
```

两个值必须可配置，不得硬编码进策略语义。Primary 用于 Scanner 市场质量；Secondary 用于显示接近当前 First Launch 名义上限时的风险。

### 6.2 初始绝对上限

为了高召回，硬门槛保持宽松：

```text
HARD_MAX_SPREAD_BPS = 40
HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS = 35
```

`SETUP_READY` 的质量目标更严格：

```text
PREFERRED_SETUP_READY_SPREAD_BPS <= 20
PREFERRED_SETUP_READY_PRIMARY_SLIPPAGE_BPS <= 20
```

超过 preferred 但未超过 hard maximum 时，可以保留候选，但必须显示 `LIQUIDITY_WARNING`。

### 6.3 横截面活动门槛

不使用单一长期固定美元成交量门槛。首版采用横截面分位数：

```text
REJECT_LOW_ACTIVITY_ONLY_IF =
24H_VOLUME_PERCENTILE < 20
AND OI_PERCENTILE < 20
AND DEPTH/SLIPPAGE_QUALITY_FAILS
```

成交量或 OI 单项较低不能直接拒绝；盘口执行质量优先。

---

## 7. 动量、相对强度与走势效率

每个 15m/30m/60m 周期计算：

```text
return_h
relative_return_vs_universe_median_h
relative_return_vs_BTC_h
move_atr_h = abs(close_now - close_h_ago) / ATR14_5M
```

`relative_return_vs_BTC` 对所有资产记录，但首版不作为非 crypto 标的的硬门槛。

### 7.1 首发 WATCH 动量门槛

满足以下任一方向：

```text
CROSS_SECTIONAL_RETURN_RANK = TOP_15_PERCENT_OR_BOTTOM_15_PERCENT
```

并至少满足一个周期的 ATR 标准化移动：

```text
15M_MOVE_ATR >= 0.60
OR 30M_MOVE_ATR >= 0.90
OR 60M_MOVE_ATR >= 1.20
```

为了提高召回，接近结构位的候选可在略低于上述移动门槛时进入 `WATCH_NEAR_LEVEL`，但必须满足：

```text
DISTANCE_TO_PRIOR_LEVEL <= 0.35 * ATR14_5M
AND CROSS_SECTIONAL_RETURN_RANK = TOP_OR_BOTTOM_20_PERCENT
```

### 7.2 Relative Volume

```text
RELATIVE_VOLUME_5M = current_5m_volume / median(previous_20_closed_5m_volumes)
```

首发解释：

```text
RELATIVE_VOLUME_5M >= 1.20 = ACTIVITY_SUPPORT
RELATIVE_VOLUME_5M >= 1.50 = STRONG_ACTIVITY_SUPPORT
```

Relative volume 是加分和解释证据，不是 WATCH 的单一硬门槛。

### 7.3 Directional Efficiency

```text
ER_h = abs(close_now - close_h_ago) / sum(abs(consecutive_5m_close_changes))
```

解释：

```text
ER >= 0.45 = CLEAN_DIRECTIONAL_MOVE
ER >= 0.55 = STRONG_DIRECTIONAL_MOVE
```

ER 低不自动拒绝，但用于降低排序并识别高噪声异动。

### 7.4 OI 与 Funding

第一版：

```text
OI_CHANGE = RECORD_AND_SCORE_IF_AVAILABLE
FUNDING = RECORD_AND_WARN
OI_OR_FUNDING = NOT_HARD_TRIGGER
```

原因是完整历史 OI/funding 可能增加数据和持久化工作量，不能阻塞首发。缺失时必须显式记录，不得使用默认值。

---

## 8. 结构位与突破参数

### 8.1 Prior Level

使用突破前已存在的闭合 candle：

```text
PRIMARY_PRIOR_HIGH_LOW = previous_12_closed_5m_bars
SECONDARY_PRIOR_HIGH_LOW = previous_36_closed_5m_bars
```

突破 12-bar level 可进入候选；同时突破 36-bar level 获得更高结构评分。

### 8.2 Breakout Buffer

```text
BREAKOUT_BUFFER = max(
    0.10 * ATR14_5M,
    2.0 * current_spread_price,
    2 * minimum_tick
)
```

只有闭合 5m candle 的收盘价超过 level + buffer（做多）或低于 level - buffer（做空）才能成为 `BREAKOUT_DETECTED`。

### 8.3 Breakout Bar Quality

记录 candle close location：

```text
CLV = (close - low) / max(high - low, minimum_tick)
```

解释：

```text
LONG_CLV >= 0.65 = CLOSE_SUPPORTS_BREAKOUT
SHORT_CLV <= 0.35 = CLOSE_SUPPORTS_BREAKOUT
```

CLV 和 `RELATIVE_VOLUME_5M >= 1.20` 用于提高排序；第一版不作为所有资产的绝对硬门槛。

### 8.4 Chase Distance

```text
CHASE_DISTANCE_ATR = abs(current_price - breakout_level) / ATR14_5M
```

状态：

```text
<= 0.75 = EARLY / ACCEPTABLE_FOR_REVIEW
> 0.75 and <= 1.50 = LATE_WATCH / DO_NOT_CHASE
> 1.50 = REJECTED_CHASE_FOR_ACTION, KEEP_FOR_RESEARCH
```

即使超过 Chase Limit，仍保存候选和后续结果，用于检验 Chase 参数；但不得显示为可追价。

---

## 9. 回踩与失败突破参数

### 9.1 回踩观察窗口

```text
RETEST_WINDOW_BARS = 1_TO_12_CLOSED_5M_BARS
RETEST_WINDOW_MINUTES = 5_TO_60
```

超过窗口仍没有回踩：

```text
EXPIRED_NO_RETEST
```

### 9.2 回踩区

```text
RETEST_ZONE_HALF_WIDTH = max(
    0.25 * ATR14_5M,
    2.0 * current_spread_price
)
```

### 9.3 回踩确认候选

`BREAKOUT_RETEST_READY` 至少要求：

- 已存在有效 `BREAKOUT_DETECTED`；
- 价格在窗口内触及 retest zone；
- 未完成失效；
- 后续闭合 5m candle 再次收于突破方向；
- 当前 chase distance 未超过 1.50 ATR；
- 数据和流动性仍健康。

优先排序证据：

```text
RETEST_VOLUME_RATIO <= 1.00
CONFIRMATION_CLV_SUPPORTS_DIRECTION
ER_30M >= 0.45
```

这些证据第一版用于排序和显示，不全部升级为硬门槛。

### 9.4 Breakout 失效

```text
INVALIDATION_INSIDE_RANGE = 0.25 * ATR14_5M
```

做多突破后，闭合 5m candle 收回旧区间超过该距离；做空对称处理。

### 9.5 Failed Breakout / Sweep Watch

若突破后 1–6 根闭合 5m candle 内：

- 价格重新收回旧区间至少 `0.10 * ATR14_5M`；
- 数据和流动性仍健康；

则输出：

```text
FAILED_BREAKOUT_SWEEP_WATCH
```

该状态只表示值得交给现有 Sweep 逻辑或人类复核，不等于正式 Sweep 信号。

---

## 10. 两级输出与通知策略

### 10.1 WATCH

WATCH 目的是尽早让交易员打开盘面，不等待完整 Setup。

建议状态：

```text
WATCH_MOMENTUM
WATCH_NEAR_LEVEL
WATCH_NEW_MARKET
BREAKOUT_DETECTED
RETEST_PENDING
LATE_WATCH
```

必须显示：

- 标的、DEX、资产类别；
- Long/Short 方向；
- 15m/30m/60m 收益和排名；
- move ATR；
- relative volume；
- level 与距离；
- liquidity summary；
- 当前状态；
- `NOT_YET_SETUP_CONFIRMED`；
- `DO NOT CHASE`（适用时）。

### 10.2 SETUP_READY

首版：

```text
BREAKOUT_RETEST_READY
FAILED_BREAKOUT_SWEEP_WATCH
```

`RANGE_EDGE_WATCH` 仅在能够直接复用现有 Range evaluator 且不扩大关键路径时加入；否则 ETH 主运行时负责 Range 样本。

### 10.3 提醒数量与去重

Scanner 内部记录所有通过门槛的候选，但对人类表面采用汇总和状态变化通知：

```text
WATCH_SUMMARY_INTERVAL = 15_MINUTES
WATCH_SUMMARY_MAX = 20_TOTAL
WATCH_SUMMARY_DIRECTION_BALANCE = UP_TO_10_LONG_AND_10_SHORT
SETUP_READY_NOTIFICATION = IMMEDIATE_ON_STATE_CHANGE
PER_ASSET_LEVEL_DEDUP_COOLDOWN = 30_MINUTES
```

不设每日候选硬上限。重复状态不重复提醒；新 level、新方向或升级状态可以重新提醒。

---

## 11. 排序分数

Scanner score 只用于排序，不授予交易权限。

```text
MOMENTUM_AND_RELATIVE_STRENGTH = 25
STRUCTURE_PROXIMITY_OR_BREAKOUT_QUALITY = 25
RETEST_OR_FAILED_BREAKOUT_STATE = 20
LIQUIDITY_AND_EXECUTION_QUALITY = 20
ACTIVITY_VOLUME_OI = 10
TOTAL = 100
```

初始显示建议：

```text
WATCH_SCORE_THRESHOLD = 45
HIGH_PRIORITY_WATCH_THRESHOLD = 60
SETUP_READY_REQUIRES_STRUCTURAL_STATE = YES
```

`SETUP_READY` 不能只靠总分产生，必须满足对应结构状态。

所有单项分数、权重和总分必须写入版本化配置和日志。

---

## 12. No-Signal / Runtime 证明

只要能够以低成本复用现有状态或日志，三 Setup 主运行时应提供：

```text
last_evaluated_candle
last_evaluation_time
runtime_ready
sweep_state / wait_reason
breakout_state / wait_reason
range_state / wait_reason
```

用于区分：

- 系统正常评估但市场无机会；
- 系统没有正常完成评估。

不得为此建设新 Dashboard 或复杂状态平台。

---

## 13. 证据与影子结果

### 13.1 每次 Scan

保存：

```text
scan_id
scanner_version
parameter_version
scan_time
session_tags
complete_universe_snapshot_or_hash
market_data_freshness
eligible_and_rejected_markets
rejection_reasons
```

### 13.2 每个 Candidate

保存：

```text
candidate_id
asset / dex / asset_class / HIP3_flag
alert_level / state / direction
15m_30m_60m_returns
relative_returns
move_atr_values
relative_volume / ER / OI / funding
spread / depth / slippage / liquidity_buckets
prior_levels
breakout_buffer
breakout_candle_identity
retest_state
chase_distance
score_components / total_score / rank
linked_signal_id / plan_id when available
```

### 13.3 人工标记

交易过程中只要求对 `SETUP_READY` 或正式 Signal 进行一次短标记：

```text
T = TAKEN
S = SKIPPED
R = REJECTED
```

可选原因码继续沿用：

```text
1 = 市场环境
2 = 入场过晚 / Chase
3 = 结构冲突
4 = 风险收益
5 = 信号逻辑错误
```

WATCH 不要求人工逐条标记。

### 13.4 Outcome

最低自动计算：

```text
MFE / MAE at 30m, 60m, 120m
MFE / MAE normalized by ATR
WATCH → SETUP_READY conversion
breakout → retest time
maximum extension before retest
return inside range / failed breakout
TP / Stop / Expiry when a TradePlan exists
actual fill / fees / PnL / R when available
```

---

## 14. 资产类别、流动性和分级的验证设计

每条候选带上：

```text
asset_class
native_or_HIP3
perp_dex
session
liquidity_decile
spread_bucket
slippage_bucket
volatility_bucket
setup_family
alert_level
```

比较：

```text
MODEL_A = LIQUIDITY + VOLATILITY + STRUCTURE
MODEL_B = MODEL_A + ASSET_CLASS + SESSION + HIP3_FLAG
```

目的：判断资产类别是否真的提供增量解释力；不在首版先验地假定股票、商品、指数和 crypto 必须使用不同参数。

最低统计：

- WATCH → SETUP_READY 转化率；
- WATCH 是否在回踩完成前出现；
- SETUP_READY 人工接受/拒绝比例；
- WATCH 与 SETUP_READY 的 MFE、MAE、净 R 差异；
- 按资产类别、流动性分位、波动率、session、方向、Setup 分组；
- 与同一时间随机 eligible 标的基线比较；
- Scanner 候选与没有 Scanner 条件的现有策略信号比较。

若 `SETUP_READY` 没有优于 WATCH，必须重新审查分级参数，不能仅凭命名认为其更准确。

---

## 15. 参数纪律与首轮复核门槛

本文件冻结的是首发默认参数，不宣称最优。

```text
PARAMETERS = VERSIONED_CONFIG
MISSING_PARAMETER = FAIL_CLOSED
HIDDEN_PARAMETER_CHANGE = PROHIBITED
```

首轮不因几笔结果频繁调参。建议首次正式参数复核在至少满足以下之一后进行：

```text
TOTAL_WATCH_CANDIDATES >= 100
AND TOTAL_SETUP_READY >= 30
```

或积累足够覆盖多个交易时段和主要资产标签的连续运行证据。

任何参数修改必须保留旧版本、变更原因和前后结果。

---

## 16. 研究结论与风险

### 16.1 支持机制

成熟研究和工程实践支持以下方向具有合理性：

- Opening Range / intraday momentum 在部分资产、时段和状态中存在延续；
- crypto 的高成交量或高波动时段可能具有更强的日内动量可预测性；
- 高流动性 crypto 更可能表现为动量，低流动性资产更容易出现短期反转；
- 支撑/阻力具有可观察的统计行为，但会随时间衰减；
- 动态 pairlist 的成熟结构是市场发现、活动度排序、年龄/状态/点差/波动过滤后再交给策略。

### 16.2 不能宣称的内容

现有研究不能证明本 Scanner 已经在 Hyperliquid 上具有稳定正期望。

主要风险：

- 多重比较和偶然极端标的；
- 事件冲击后延续与反转并存；
- 高成交量但当前盘口薄；
- HIP-3 oracle、时段和事件风险；
- 山寨币跳价、操纵和强平链；
- 跨资产相关导致重复候选；
- 时区、API rate limit、数据陈旧和 candle 缺口；
- 候选提醒诱导追价。

因此固定用途：

```text
FIRST_LAUNCH_USE = HUMAN_ASSISTED_DISCOVERY_AND_EVIDENCE_GENERATION
AUTO_TRADING_USE = PROHIBITED
MATHEMATICAL_STATUS = PLAUSIBLE_MECHANISM_NOT_PROVEN_EDGE
```

---

## 17. 工程范围必须先确认，不预设工期

当前不冻结 4–7 小时或其他开发时间。

Engineering Optimization 必须先输出：

- 当前 ETH-only 绑定的 exact impact map；
- 旁路 Scanner 与解除部分绑定两种路线的 exact file scope；
- 官方 API/SDK 可复用范围；
- DEX/market discovery 和 coin identity 规则；
- API rate-limit 预算；
- state persistence 与重启语义；
- Discord/JSON/SQLite 复用路线；
- deterministic tests、live public dry run 和部署边界；
- 单次部署方式；
- 最快合理时间与正常时间。

```text
TIME_ESTIMATE = PENDING_ENGINEERING_SCOPE
```

不能为了满足旧时间预估删掉已冻结的核心产品目标；也不能未经评估扩大为完整多资产自动交易系统。

---

## 18. 产品范围

Product Optimization 必须确认：

- WATCH 汇总和 SETUP_READY 即时提醒；
- 20 条 WATCH 汇总上限与多空平衡是否适合实际操作；
- 候选卡最少字段；
- `NOT_YET_SETUP_CONFIRMED`、`DO NOT CHASE`、流动性警告；
- 人工 T/S/R 的一次操作流程；
- Scanner 候选、正式 Signal、TradePlan 的视觉和语义区别；
- 资产类别只做标签和统计；
- 不建设复杂 Dashboard；
- 与三 Setup 同一发布/部署的产品验收。

---

## 19. 最终冻结字段

```text
TASK = SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE
VERSION = R3
QUALITY_TARGET = FIRST_LAUNCH_5_TO_6_OF_10
PRIMARY_PURPOSE = GENERATE_REAL_TEST_SAMPLES
SCANNER_BIAS = HIGH_RECALL
UNIVERSE = ALL_ELIGIBLE_HYPERLIQUID_PERPS
ASSET_CLASS = TAG_AND_ATTRIBUTION_NOT_HARD_FILTER
LIQUIDITY = MULTI_DIMENSIONAL
SCAN_CADENCE = EVERY_CLOSED_5M
RETURN_HORIZONS = 15M_30M_60M
ALERT_LEVELS = WATCH_AND_SETUP_READY
REQUIRED_SETUP_READY_STATES = BREAKOUT_RETEST_READY_AND_FAILED_BREAKOUT_SWEEP_WATCH
RANGE_EDGE_WATCH = OPTIONAL_ONLY_IF_NEGLIGIBLE_REUSE
HUMAN_FINAL_DECISION = YES
MANUAL_EXECUTION = YES
AUTO_TRADE = NO
AUTO_ASSET_SWITCH = NO
SAME_RELEASE = TARGET
SAME_DEPLOYMENT = TARGET
SAME_RUNTIME_PROCESS = NO_BY_DEFAULT
SCANNER_FAILURE_ISOLATION = REQUIRED
ASSET_CLASS_PERFORMANCE_ATTRIBUTION = REQUIRED
WATCH_VS_SETUP_READY_VALIDATION = REQUIRED
SIGNAL_EVIDENCE_LITE = REQUIRED
NO_SIGNAL_RUNTIME_PROOF = LOW_COST_REQUIRED
TIME_ESTIMATE = PENDING_ENGINEERING_SCOPE
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```

---

## 20. 研究参考

- Hyperliquid official docs: Perpetuals info endpoints, WebSocket subscriptions, candleSnapshot, L2 book and rate limits.
- Freqtrade official docs: dynamic Pairlists, VolumePairList, PercentChangePairList, Age/Delist/Spread/Volatility/Range Stability filters.
- Shen, Urquhart and Wang (2022), *Bitcoin intraday time-series momentum*, Financial Review.
- Zaremba et al. (2021), *Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets*, International Review of Financial Analysis.
- Wen et al. (2022), *Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both*, North American Journal of Economics and Finance.
- Chung and Bellotti (2021), *Evidence and Behaviour of Support and Resistance Levels in Financial Time Series*.
- *Assessing the profitability of intraday opening range breakout strategies* (2013), Finance Research Letters.
