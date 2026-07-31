# First Launch 三 Setup 与 Scanner 外部价格行为策略研究 R1

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-SCANNER-EXTERNAL-PRICE-ACTION-RESEARCH-2026-08-01-R1`  
**日期：** `2026-08-01`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**目标分支：** `agent/v0-strategy-predevelopment-analysis-r1`  
**生产比较基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**策略合同权威：** `R1.2 > R1.1 > R1`  
**Scanner 权威：** `FIRST_LAUNCH_SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE_R3_FINAL_PARAMETER_AND_DELIVERY_FREEZE_2026-08-01.md`  
**状态：** `EXTERNAL RESEARCH SUPPLEMENT / NON-EXECUTABLE / NON-AUTHORIZING`

---

## 0. 权限、用途与优先级边界

本文是对公开论文、官方交易所资料、经典机械化交易规则、开源策略实现和回测方法论的一轮外部研究补充，目标是：

1. 找出能提高 `SWEEP_RECLAIM`、`BREAKOUT_RETEST`、`RANGE_EDGE_REJECTION` 实际表现或解释力的外部证据；
2. 找出三 Setup 当前未覆盖或容易误判的价格行为维度；
3. 建立简单公开策略对照组，验证复杂规则是否真正提供增量价值；
4. 强化首次三 Setup 回测的实验设计，而不是在看到结果前继续堆叠参数；
5. 强化 Scanner 的候选发现、排序、证据保留和跨标的归因能力；
6. 向 Strategy Optimization Window 提供可直接执行的研究问题、字段、对照和消融清单。

本文不自动改变任何已经冻结的：

- Setup 身份；
- 主候选或敏感性 candidate ID；
- 数值阈值；
- FAST / STANDARD 语义；
- Scanner R3 参数；
- 生产代码、运行时、部署或交易权限。

本文建议按以下优先级处理：

```text
P0 = 首次回测前应加入的测量、对照和防偏差能力
P1 = 首次回测中应预注册的诊断或有限消融
P2 = 首次结果后再决定的二次开发
DEFER = 当前阶段明确不应进入
```

任何生产规则修改必须由 Strategy Optimization Window 形成新的策略裁决，再经 Product、Engineering 和 Project Control 的既有治理流程处理。

---

# 1. 执行摘要

## 1.1 总体判断

现有三 Setup 已经覆盖了价格在高质量边界附近最核心的三种结果：

```text
边界内拒绝
→ RANGE_EDGE_REJECTION

越界后未被接受并重新收回
→ SWEEP_RECLAIM

收盘越界并获得接受，随后回踩延续
→ BREAKOUT_RETEST
```

因此，本轮最大潜在收益不来自仓促加入第四个 Setup，也不来自继续增加更多指标，而来自以下五个方向：

1. **Level Quality 从单一 Q 等级扩展为可归因证据。**
2. **记录事件发生路径，而不仅记录最终触发 K 线。**
3. **建立简单、公开、可解释的机械策略对照组。**
4. **把 Scanner 的点时宇宙、流动性和候选漏斗纳入回测证据。**
5. **完整记录尝试次数，控制多重比较和回测过拟合。**

## 1.2 本轮最重要的 P0 建议

### P0-A：四类简单对照组

- `SIMPLE_SWEEP_RECLAIM_BASELINE`
- `SIMPLE_CLOSE_BREAKOUT_BASELINE`
- `DONCHIAN_TURTLE_BREAKOUT_BASELINE`
- `SIMPLE_RANGE_EDGE_REJECTION_BASELINE`

这些对照组不参与生产准入，只用于回答：

> 当前 Q2、环境分类、成交量确认、FAST/STANDARD、目标可行性和冲突处理，究竟增加了多少净收益、稳定性或风险控制价值？

### P0-B：事件路径字段

对每个 raw candidate 和 market event 记录：

- 边界来源和年龄；
- 历史独立反应次数；
- 首次触边时间；
- 最大越界幅度；
- 边界外停留时间；
- 收回或接受时间；
- confirmation 延迟；
- pre-entry MFE / MAE；
- retest 深度和时间；
- 目标空间；
- Chase Limit 超限状态；
- 当时的流动性、OI、funding、premium 与 session。

### P0-C：Scanner 点时宇宙快照

每次扫描必须保存当时实际存在且可被扫描的市场集合，而不能在回测结束后用今天的标的列表重建历史。至少保存：

- dex / market / coin；
- 是否 active；
- 上线年龄；
- 5m、15m 历史是否充足；
- 24h 名义成交额；
- OI 与 OI notional；
- bid/ask spread；
- impact price / estimated slippage；
- mark/oracle divergence；
- funding / premium；
- 数据缺口和新鲜度；
- 资产类别、流动性分位、session 标签。

### P0-D：试验登记册

每次候选、参数、过滤器和结果都必须留痕，包括失败结果。首次回测至少记录：

```text
trial_id
hypothesis
changed_variable
unchanged_variables
dataset_cut
cost_model
delay_model
result
decision
```

这是评估 PBO、Deflated Sharpe Ratio 和选择偏差的基础。

## 1.3 暂不建议做的工作

当前阶段不建议：

- 引入第四个 Setup；
- 以 FVG、Order Block、BOS/CHoCH 替代当前三 Setup；
- 使用机器学习、LLM 或模糊逻辑决定交易；
- 把 OI/funding 直接设为硬触发；
- 引入 L2/order flow 作为当前生产硬门槛；
- 根据首次回测结果临时增加新阈值；
- 用一个综合分数替代三个 Setup 的因果判断。

---

# 2. 当前三 Setup 的理论定位

当前设计最适合被理解为：

```text
Auction / Price-Action Boundary Event State Machine
```

即：

1. 先识别市场环境；
2. 再识别高质量结构边界；
3. 再判断价格对边界的实际反应；
4. 再做确认、执行与目标可行性判断；
5. 最后对同一 market event 去重和处理状态转换。

这比“看到一根 Pin Bar 就交易”或“看到 BOS 就交易”更接近成熟主观交易员。

### `SWEEP_RECLAIM`

外侧止损、强平或流动性被触发，但价格未被持续接受在边界外，随后重新收回。

对应外部理论：false breakout、Turtle Soup、2B reversal、liquidity sweep、failed auction、stop-run exhaustion。

### `BREAKOUT_RETEST`

高质量边界被收盘突破并获得接受；价格回踩边界附近但没有重新回到旧结构，随后继续重新定价。

对应外部理论：Donchian/Turtle breakout、support-resistance breakout、opening-range breakout、breakout acceptance、breakout-pullback continuation。

### `RANGE_EDGE_REJECTION`

稳定非方向区间中的高质量边缘发生浅度触碰或越界后回收，且区间内部仍有足够的成本后目标空间。

对应外部理论：range rotation、failed auction at range edge、support/resistance rejection、bounded mean reversion、auction-market value rotation。

---

# 3. 外部证据的分级方法

## Grade A

成熟、同行评议或经典微观结构证据。可支持经济机制和回测设计，但不能直接证明 ETH 5m/15m 的具体数值阈值。

## Grade B

高质量工作论文、官方交易所文档或大样本公开研究。可用于形成候选特征、对照或数据合同。

## Grade C

近期独立研究、单市场研究或样本有限的探索性结果。只能形成待验证假设，不能直接改写生产策略。

## Grade D

开源代码、社区策略或交易者机械规则。可用于学习实现、建立对照或减少重复研发；收益声明不构成证据。

固定原则：

```text
EXTERNAL_EVIDENCE_CAN_SUPPORT_MECHANISM = YES
EXTERNAL_EVIDENCE_CAN_DEFINE_OUR_ETH_THRESHOLDS = NO
PUBLIC_BACKTEST_CAN_AUTHORIZE_PRODUCTION = NO
```

---

# 4. Level Quality：最值得强化的共同基础

## 4.1 外部研究的主要结论

Carol Osler 对外汇市场的研究表明：

- 支撑阻力附近存在可预测的短期趋势中断；
- 止盈和止损订单会在可观察位置，尤其整数附近聚集；
- 边界未被突破时可能产生反转；
- 止损密集区被突破后可能触发正反馈和价格级联。

Chung 与 Bellotti 的研究表明：

- 历史反应次数越多，边界再次发生反应的概率往往越高；
- 边界效力会随时间衰减。

这些结论支持当前的独立反应次数、Q0–Q3、freshness，以及 Sweep 与 Breakout 对同一边界的不同解释。

## 4.2 当前设计仍缺少的 Level Attribution

当前 Q 等级适合做资格门槛，但为了判断为什么某些边界有效，建议增加以下**只记录、不先做硬门槛**的字段：

```text
level_source
level_price
level_age_bars
reaction_cluster_count
latest_reaction_age
reaction_strength_median
reaction_strength_max
level_roundness_distance_bps
level_session_identity
level_higher_timeframe_identity
level_confluence_count
```

### `level_source` 建议枚举

```text
ROLLING_12_HIGH_LOW
ROLLING_24_HIGH_LOW
LOCAL_SWING
PREVIOUS_DAY_HIGH_LOW
PREVIOUS_WEEK_HIGH_LOW
ASIA_SESSION_HIGH_LOW
US_SESSION_HIGH_LOW
ROUND_NUMBER
OTHER_STRUCTURAL
```

首次回测仍以冻结的 U12/L12/U24/L24 为交易权威；其他来源只做 tag 和归因。

## 4.3 为什么不能立刻加入“多重共振硬门槛”

如果在首次回测前把前日高低、Session 高低、round number、swing、volume profile 全部设为硬过滤，会造成：

- 参数和定义急剧增加；
- 信号数量下降；
- 无法判断单个因素的增量价值；
- 多重比较风险上升；
- 可能把少样本偶然性误认为优质过滤器。

因此正确路线是：

```text
先记录全部 Level Attribution
→ 按字段分层报告
→ 只在样本外显示稳定增量后升级为过滤器
```

---

# 5. `SWEEP_RECLAIM` 深度研究与优化方向

## 5.1 当前优势

当前 Sweep 已经优于大量公开“假突破策略”，因为它包含：

- 最小和最大 excursion；
- close-inside reclaim；
- 收盘位置；
- 成交量确认；
- 方向环境约束；
- FAST / STANDARD；
- 结构止损；
- Target Feasibility；
- 与 Range/Breakout 的数学域分离。

## 5.2 公开策略中最接近的对照

Turtle Soup / 2B Reversal 的典型机械规则是：

1. 价格穿越最近 N 根高点或低点；
2. 未能在外侧持续；
3. 重新收盘回到边界内；
4. 在收回后反向入场；
5. 止损放在 sweep extreme 外。

其价值不是替换现有 Sweep，而是提供一个简单基线：

```text
SIMPLE_SWEEP_RECLAIM_BASELINE
```

Long 示例：

```text
boundary = prior rolling low
low_t < boundary
close_t >= boundary
maximum excursion bounded
no Q2 requirement
no environment filter
no volume filter
same cost / delay / stop accounting
```

## 5.3 当前最缺的是事件路径

同样是收回边界，以下两种市场事实可能完全不同：

```text
A. 轻微越界后几分钟内快速收回
B. 深度越界、长时间停留后勉强收回
```

建议新增：

```text
outside_excursion_A
outside_duration_seconds
outside_closed_bar_count
reclaim_latency_seconds
reclaim_close_distance_A
reclaim_body_A
reclaim_wick_ratio
initial_rejection_velocity
post_reclaim_1bar_MFE_A
post_reclaim_3bar_MFE_A
post_reclaim_3bar_MAE_A
```

### 核心待验证假设

1. reclaim 越快，越可能是流动性冲击耗尽；
2. 边界外停留越久，越可能正在建立新的接受；
3. excursion 过深后收回，可能只是趋势中的短暂反弹；
4. 同样的 excursion，在高流动性与低流动性市场中的含义不同；
5. 反向成交量放大可能提高成功率，也可能只是极端波动噪声。

这些都应以 bucket 归因验证，不能先变成新阈值。

## 5.4 OI / funding / premium 的正确用途

止损级联理论支持观察杠杆与拥挤，但当前没有证据证明某一固定 OI 或 funding 阈值能提高 ETH 5m Sweep。

本轮建议：

```text
OI / funding / premium = DIAGNOSTIC_FEATURE
NOT = HARD_TRIGGER
```

记录：

```text
oi_notional
oi_change_5m
oi_change_15m
funding
premium
mark_oracle_divergence
```

待回答：

- sweep 前 OI 快速增加是否代表拥挤；
- sweep 发生时 OI 快速下降是否更接近去杠杆完成；
- 高 funding 是否只影响某一方向；
- OI 变化在高流动性与低流动性标的中是否具有不同意义。

## 5.5 Sweep 的 P1 有限消融

只建议预注册以下单变量诊断：

1. `Q1 / Q2 / Q3` 分层，不改变主候选；
2. excursion bucket；
3. reclaim latency bucket；
4. outside-duration bucket；
5. relative volume bucket；
6. session / asset class / liquidity decile；
7. OI change bucket；
8. level source tag。

不得同时调 excursion、volume、close location、level quality 和 stop。

---

# 6. `BREAKOUT_RETEST` 深度研究与优化方向

## 6.1 当前优势

当前 Breakout 已经避免了公开策略中常见的错误：

- 不是影线越界就算突破；
- 需要收盘 extension；
- 需要实体、收盘位置与成交量；
- 有方向或 Range transition 支持；
- STANDARD 要求回踩后继续站在旧结构外；
- 失败后可以转为 Sweep；
- 有结构障碍和 2R 成本后目标可行性。

## 6.2 最重要的公开对照

### Donchian / Turtle Breakout

核心逻辑是突破过去 N 周期高低点，配合 ATR 风险和趋势退出。它应被用作：

```text
DONCHIAN_TURTLE_BREAKOUT_BASELINE
```

而不是直接成为生产策略。

### Simple Close Breakout

```text
close_t >= rolling_high + extension
```

不要求 Q2、retest、volume、environment、structural obstacle。用途是衡量各层过滤器对收益、回撤和信号频率的增量。

### Opening Range Breakout

公开 ORB 研究最有价值的结论不是某个固定开盘区间参数，而是：

> 突破策略的效果可能高度依赖“当天/当时是否存在异常活动”，而不是所有标的、所有时段一视同仁。

对 Scanner 的启示是：

```text
relative_activity / stocks-in-play analogue
= ranking and attribution feature
NOT = immediate hard gate
```

Crypto 对应字段可以包括 24h volume percentile、current relative volume、OI change、volatility expansion、spread/depth、session、mark-oracle divergence。

## 6.3 Retest 路径是当前最值得强化的部分

建议记录：

```text
breakout_close_extension_A
breakout_body_A
breakout_relative_volume
acceptance_closed_bar_count
time_to_first_retest_seconds
time_to_confirmed_retest_seconds
pre_retest_MFE_A
retest_depth_A
retest_close_distance_A
retest_duration_bars
post_retest_1bar_MFE_A
post_retest_3bar_MFE_A
failed_breakout_latency
```

### 关键研究假设

1. retest 太快可能代表边界尚未真正获得接受；
2. retest 太晚可能意味着主要移动已经发生，入场接近追高；
3. breakout 后在 retest 前已经运行过远，后续 continuation 的成本后空间可能下降；
4. 边界外连续收盘数量可能比单根 breakout K 线更能代表 acceptance；
5. retest 深度和 re-acceptance 速度可能比是否“精确触碰边界”更重要。

近期单一市场的探索性研究提出 time-to-retest 和 pre-retest excursion 可能与 continuation 有关，但证据尚不足以直接设置阈值，因此只应作为 P1 分层变量。

## 6.4 Breakout 失败必须被当作独立研究对象

建议增加 failure taxonomy：

```text
FAILED_IMMEDIATE_RECLAIM
FAILED_DEEP_REENTRY
FAILED_LOW_VOLUME
FAILED_CHASE_LIMIT
FAILED_TARGET_SPACE
FAILED_OPPOSITE_SIGNAL
FAILED_DATA_QUALITY
```

分别统计是否转 Sweep、转换延迟、MFE/MAE、是否在同一 market event 内、是否只是 Scanner WATCH 误报。

## 6.5 Breakout 的 P1 有限消融

1. Immediate breakout vs retest-confirmed；
2. time-to-retest bucket；
3. retest depth bucket；
4. pre-retest excursion bucket；
5. relative volume bucket；
6. Q1/Q2/Q3；
7. structural obstacle present vs absent；
8. long / short；
9. liquidity decile / session / asset class。

当前 FAST extension sensitivity 已冻结，不应再增加第三个 extension 候选。

---

# 7. `RANGE_EDGE_REJECTION` 深度研究与优化方向

## 7.1 当前优势

当前 Range 不是“触碰 Bollinger Band 就反转”，而是：

- 明确非方向环境；
- 双侧边界都需历史验证；
- 区间宽度受 ATR 约束；
- 只允许浅度触边/越界；
- 排除 Sweep 和 Breakout；
- 有 dual-edge veto；
- 有 volatility eligibility；
- 有结构止损和成本后目标空间。

这是合理的结构型均值回归，而不是默认 ETH 绝对价格服从 OU。

## 7.2 均值回归研究给出的关键警告

均值回归策略的入场、退出、成本、止损和期限必须联合设计。即使存在统计回归，如果 spread 太大、目标太近、反应太慢、止损太紧或交易成本太高，仍可能没有可交易价值。

因此当前 `TARGET_FEASIBILITY` 是必须保留的核心，不应为了提高信号数量而削弱。

## 7.3 建议增加 Range 结构稳定性字段

```text
range_age_bars
range_rotation_count
upper_reaction_count
lower_reaction_count
edge_reaction_balance
range_midpoint
midpoint_slope_A_per_bar
range_width_A
range_width_change
inside_close_ratio
false_breakout_count
time_since_last_breakout_attempt
current_volatility_percentile
volatility_expansion_ratio
```

### 需要回答的问题

1. 区间是否需要至少完成若干次 rotation 才可靠；
2. 上下边缘反应高度不对称时，是否已经接近趋势转换；
3. midpoint 持续漂移是否代表“看似区间、实为通道”；
4. width 快速扩大是否应比静态 HIGH volatility 更早 veto；
5. 多次 false breakout 后，下一次 breakout 的概率是否上升；
6. Range 在不同流动性标的上是否需要不同成本 reserve。

## 7.4 Target 应先作为结果标签比较，而不是立刻改规则

对每个 Range 事件同时离线计算：

```text
MIDPOINT_TARGET_OUTCOME
PARTIAL_ROTATION_TARGET_OUTCOME
OPPOSITE_EDGE_TARGET_OUTCOME
TIME_EXIT_OUTCOME
```

首次主回测仍按冻结合同执行。目的是判断当前 opposite-edge/2R 目标是否过于理想、midpoint 是否改善命中率但牺牲 expectancy、分批止盈是否降低回撤，以及 Range 的经济价值来自完整 rotation 还是短期回弹。

## 7.5 Range 的 P1 有限消融

1. range age bucket；
2. rotation count bucket；
3. edge symmetry bucket；
4. midpoint slope bucket；
5. width bucket；
6. volatility expansion bucket；
7. midpoint vs opposite-edge outcome label；
8. candidate edge Q2 + opposite Q1/Q2（只使用已冻结敏感性）。

---

# 8. 三 Setup 共同不足与弥补路线

当前尚未完整覆盖：

- **Trend Pullback Continuation**：已形成趋势后的第二次、第三次结构回调；
- **Compression Expansion**：Inside Bar、NR4/NR7、ATR 收缩后扩张；
- **Session / Previous-Day Extremes**：前日、前周和 Session 高低；
- **VWAP / Volume Profile Auction**：VWAP、VAH、VAL、POC。

本轮裁决：

```text
ADD_FOURTH_SETUP_NOW = NO
```

理由：三 Setup 首次回测尚未完成，加入新 Setup 会扩大多重比较；Scanner 正在扩展跨标的证据；当前更需要证明现有复杂度的增量价值。

低成本弥补方式是只增加 attribution tag：

```text
session_extreme_proximity
previous_day_extreme_proximity
compression_state
trend_pullback_context
vwap_distance_if_available
```

这些字段不参与 trigger，只用于发现未来候选机制。

---

# 9. Scanner：公开研究对当前设计的具体启示

## 9.1 Scanner 不应成为第四个策略

Scanner 的职责是：

```text
发现候选
→ 提供上下文
→ 形成 WATCH / SETUP_READY
→ 排序和通知
```

最终策略权威仍为三 Setup。

## 9.2 高召回与完整证据并不矛盾

正确实现是：

```text
所有合格市场都扫描
所有 raw WATCH 都留存
所有 SETUP_READY 都留存
通知只展示 Top-N
```

不能只保存被推送的 Top-N，否则会产生 selection bias，无法测量 WATCH recall，也无法知道未通知候选的结果。

## 9.3 推荐四层漏斗

### Stage 0：Market/Data Integrity

硬门槛，不可由评分补偿：market active、candle history sufficient、closed-candle alignment、no material gaps、mark/mid/oracle valid、spread and impact computable、no stale context、contract metadata valid。

### Stage 1：High-Recall WATCH

计算距 15m/30m/60m 结构边界的距离、接近 breakout/sweep/range edge 的程度、session extreme proximity、relative activity、volatility state、liquidity context。Stage 1 不得声称已经产生交易信号。

### Stage 2：Exact Three-Setup Evaluation

只使用正式三 Setup 语义产生 `SETUP_READY / NO_ACTION / PREPARE-WATCH`。

### Stage 3：Notification Ranking

对已经合格的候选排序，不改变其 Setup 身份和交易资格。

## 9.4 不建议单一综合分数

建议至少保留：

```text
sweep_watch_score
breakout_watch_score
range_watch_score
liquidity_quality_score
data_quality_state
```

不要用 `one_global_score` 隐式替代因果规则。

## 9.5 Multidimensional Liquidity

24h volume 不能独立代表可交易性。建议至少使用：

```text
day_notional_volume
open_interest
open_interest_notional
bid_ask_spread_bps
impact_price_slippage_bps
book_depth_at_reference_notional
mark_oracle_divergence_bps
data_update_age
```

Hyperliquid 官方接口已经提供 perpetual metadata/context、mark、funding、OI、day notional volume、oracle/mid/premium、impact prices、L2 snapshot 和 candle snapshots。当前只需使用现有低成本数据；L2 不应成为 First Launch 的新依赖，除非工程范围已冻结并证明不会拖延核心 release。

## 9.6 Relative Activity 的正确使用

ORB 公开研究显示，突破策略在异常活跃标的中可能更有效。Crypto 可以测试：

```text
relative_volume
volume_percentile
oi_change_percentile
volatility_expansion_percentile
attention_proxy
```

首次使用应为 `ranking / attribution`，不是 hard eligibility，因为股票“Stocks in Play”通常由公司新闻驱动，不能直接等同于加密市场的高成交量。

## 9.7 Point-in-Time Universe

每个扫描时点必须冻结：

```text
universe_snapshot_id
universe_members
eligibility_reason
exclusion_reason
market_age
data_availability
liquidity_features
```

不能使用最终仍存活的标的列表回测历史，否则会形成 survivorship bias。

## 9.8 跨标的相关性与事件聚类

全市场扫描会产生大量由同一个 BTC/市场事件驱动的 alt 信号。若把它们视为独立样本，会夸大统计显著性。

建议：

```text
market_event_cluster_id
cross_asset_cluster_id
btc_beta_bucket
correlation_cluster
```

报告原始 candidate 数、独立 market event 数、同一宏观事件内的标的数、组合风险和信号集中度。

---

# 10. WATCH 与 SETUP_READY 的验证合同

Scanner 自身必须被回测，而不仅是三 Setup。

## 10.1 WATCH 质量指标

```text
watch_to_setup_ready_conversion_rate
watch_recall_of_future_setup_ready
watch_precision
median_lead_time
p90_lead_time
missed_setup_ready_count
false_watch_count
alerts_per_hour
duplicate_watch_rate
```

## 10.2 SETUP_READY 质量指标

```text
setup_ready_count
human_taken_rate
human_skipped_rate
human_rejected_rate
net_expectancy
MAE
MFE
chase_limit_breach_rate
cost_stress_survival
delay_stress_survival
```

## 10.3 排名质量

对每个 Setup 独立评估：

```text
top_1_hit_rate
top_3_hit_rate
top_5_hit_rate
NDCG_or_rank_correlation
outcome_by_score_decile
```

排名只能在合格候选之间排序，不能让高分补偿数据失效或目标空间失败。

---

# 11. 首次回测应增加的简单对照组

所有对照必须使用与主策略相同的数据截止、closed-candle 语义、手续费、滑点、人工延迟、funding、ambiguous path、time exit、事件去重和结果报告。

## 11.1 `SIMPLE_SWEEP_RECLAIM_BASELINE`

保留 rolling boundary、越界、close-inside、maximum excursion、structural stop；移除 Q2、environment、volume、FAST/STANDARD 和复杂优先级。

测量：

```text
incremental_value_of_level_quality
incremental_value_of_environment
incremental_value_of_confirmation
```

## 11.2 `SIMPLE_CLOSE_BREAKOUT_BASELINE`

保留 rolling high/low、close extension、structural stop；移除 Q2、volume、direction、retest 和 structural obstacle。

测量：

```text
incremental_value_of_acceptance
incremental_value_of_retest
incremental_value_of_target_feasibility
```

## 11.3 `DONCHIAN_TURTLE_BREAKOUT_BASELINE`

使用经典 Donchian 突破、ATR/N 风险和简单退出作为趋势策略基准。不复制公开参数后直接生产化，只作为统一数据上的基准。

## 11.4 `SIMPLE_RANGE_EDGE_REJECTION_BASELINE`

保留 24-bar high/low、width、shallow rejection、structural stop；移除双侧 Q2、environment classification、wick/volume confirmation 和复杂事件互斥。

测量：

```text
incremental_value_of_two_sided_quality
incremental_value_of_range_environment
incremental_value_of_confirmation
```

---

# 12. 回测设计：公开研究带来的必要修正

## 12.1 Market Event 是统计单位

同一边界附近的 FAST、STANDARD、repeated WATCH 和多标的同步信号不能简单按记录条数当作独立样本。

至少报告：

```text
raw_candidates
deduplicated_candidates
independent_market_events
cross_asset_event_clusters
```

## 12.2 保持当前最小准入单位

继续使用：

```text
setup × side × confirmation_mode
```

Scanner 扩展后增加归因维度：asset_class、liquidity_decile、session、volatility、level_source。这些维度用于解释异质性，不能在样本不足时无限拆分后挑选最佳子组。

## 12.3 Multiple Testing Ledger

每次研究都记录：

```text
number_of_trials
candidate_family
primary_or_sensitivity
selection_rule
result_visibility
```

建议输出 ordinary Sharpe/expectancy、Deflated Sharpe Ratio、PBO 或可实施近似、bootstrap lower bound、trial count 和 false-discovery warning。

## 12.4 Exact Recent 与 Proxy Long History

继续严格区分 Hyperliquid exact recent evidence 与 proxy venue long-history evidence。Hyperliquid candle snapshot 只提供最近 5000 根，因此不能独立构建长历史。若使用 Binance/Bybit proxy：不得混用 funding、不得混用成本、需单独报告方向冲突，并在 exact recent 上验证最近市场适配。

## 12.5 成本与延迟

至少进行：

```text
base fee/slippage
cost stress
30s delay
60s delay
chase-limit enforcement
funding when crossing timestamp
```

对 Scanner 多标的还需使用流动性分层的 estimated slippage。

## 12.6 不能只看平均收益

至少报告：

```text
net expectancy
median R
win rate
profit factor
maximum drawdown
longest losing streak
MAE / MFE
tail loss
concentration
liquidation feasibility
```

---

# 13. 建议的统一证据字段

## Identity

```text
event_id
raw_candidate_id
scanner_cycle_id
universe_snapshot_id
strategy_id
strategy_version
setup_family
side
confirmation_mode
symbol
dex
asset_class
```

## Time and Causality

```text
decision_cutoff
first_touch_time
trigger_close_time
prepare_time
confirmation_time
expiry_time
data_receipt_time
session_tag
```

## Level

```text
level_price
level_source
level_age_bars
reaction_cluster_count
latest_reaction_age
level_quality
opposite_level_quality
round_number_distance_bps
higher_timeframe_confluence
```

## Event Path

```text
excursion_A
outside_duration_seconds
outside_closed_bars
reclaim_latency_seconds
breakout_extension_A
acceptance_closed_bars
time_to_retest_seconds
pre_retest_MFE_A
retest_depth_A
range_age_bars
range_rotation_count
midpoint_slope
```

## Candle and Activity

```text
close_location
body_A
wick_ratio
relative_volume
volume_percentile
ATR
volatility_regime
volatility_percentile
```

## Liquidity and Derivatives Context

```text
day_notional_volume
spread_bps
impact_slippage_bps
depth_reference_notional
open_interest
open_interest_notional
oi_change_5m
oi_change_15m
funding
premium
mark_oracle_divergence_bps
```

## Execution and Outcome

```text
planned_entry
actual_entry
entry_zone
chase_limit
structural_stop
target
available_space
planned_R
actual_R
fee
slippage
funding_cashflow
human_delay
MFE_R
MAE_R
TP1_hit
TP2_hit
stop_hit
time_exit
realized_R
decision_taken_skipped_rejected
failure_taxonomy
suppression_reason
```

---

# 14. 开源资源的可利用方式

| 资源 | 可学习内容 | 许可证/状态 | 推荐用途 | 主要风险 |
|---|---|---|---|---|
| `joshyattridge/smart-money-concepts` | Swing、BOS/CHoCH、Liquidity、FVG、Order Block、Session | MIT | 离线特征原型、fixture、未来结构库 | 常见 swing 定义使用前后窗口；实时使用会产生 lookahead，必须延迟确认或重写 |
| `gabekutner/turtle-trading` | Turtle entries、N/ATR、position sizing、stop、exit | MIT | Donchian/Turtle 简单对照组 | 不适合复制股票/期货参数到 ETH 5m |
| `je-suis-tm/quant-trading` | London Breakout、Dual Thrust、形态策略 | Apache-2.0 | Session baseline 和代码结构参考 | 示例常使用无费用、无滑点假设 |
| Freqtrade ecosystem | Crypto 策略格式、回测、dry-run、lookahead/recursive 检查 | 开源 | 研究工具和测试方法 | 社区策略参数可能严重过拟合 |
| TA-Lib patterns | Hammer、Engulfing、Hikkake 等标准形态 | BSD | confirmation feature | 形态没有环境、位置和目标空间，不能独立作为 Setup |
| LLM/BreakGPT 类研究原型 | 自然语言与价格行为解释 | 研究代码 | 后续人工审核解释实验 | 不应在 First Launch 充当信号权威 |

对 SMC 的明确裁决：可以学习统一结构对象接口、Liquidity 与 BOS/CHoCH 的离线标注、Session/previous high-low 和测试数据；本轮不直接引入 Order Block、FVG、未做因果修正的 swing，或用“机构订单流”叙事替代可测规则。

---

# 15. P0 / P1 / P2 优先级表

## P0：首次回测前

1. 四个简单对照组；
2. 事件路径字段；
3. Level Attribution；
4. Scanner 点时宇宙快照；
5. 全量 WATCH/SETUP_READY 留存；
6. 多维流动性字段；
7. trial registry；
8. 事件级和跨标的去重；
9. Scanner 自身质量指标；
10. 统一成本与延迟。

## P1：首次回测中预注册

1. Level Q 分层；
2. Sweep excursion/duration/reclaim latency；
3. Breakout time-to-retest/depth/pre-retest excursion；
4. Range age/rotation/symmetry/midpoint slope；
5. relative activity bucket；
6. OI/funding 诊断；
7. asset class/session/liquidity decile；
8. long-short asymmetry；
9. simpler-policy dominance；
10. exact recent vs proxy contradiction。

## P2：首次结果后

1. Session/previous-day levels 升级为 LevelSource 候选；
2. Trend Pullback 第四 Setup 研究；
3. Compression Expansion Setup 研究；
4. VWAP/value area；
5. L2/trade imbalance；
6. fuzzy quality score；
7. 机器学习排序。

## DEFER

- 自动交易；
- 自动切换标的；
- 用 ML 直接决定 eligibility；
- 复杂 order-flow 依赖；
- 大规模参数网格；
- 在首次结果后删除失败 trial；
- 只保留最佳资产或最佳时段结果。

---

# 16. Strategy Optimization Window 必须回答的问题

## 三 Setup 共同

1. Q2+ 相比简单 rolling high/low 是否有稳定增量？
2. Environment State 是提高 expectancy，还是只减少样本？
3. FAST 与 STANDARD 哪个在成本和延迟后更有效？
4. Target Feasibility 是否改善净收益和尾部风险？
5. 复杂三 Setup policy 是否被更简单 subset 支配？
6. 信号是否集中在少数日期、标的或异常事件？
7. long/short 是否需要不同准入？
8. exact recent 与 proxy 是否方向一致？

## Sweep

1. excursion 与收益是否单调或存在最优区间？
2. reclaim latency 是否有明显失效区？
3. outside duration 是否比单根 close 更重要？
4. volume confirmation 是否增加 edge，还是只降低数量？
5. OI unwind 是否具有增量解释力？
6. 哪些 LevelSource 更有效？

## Breakout

1. Immediate breakout 与 retest-confirmed 的成本后差异？
2. time-to-retest 是否存在稳定区间？
3. pre-retest excursion 过大是否降低 continuation？
4. acceptance closed bars 是否优于单根扩展？
5. failed breakout 转 Sweep 是否真实有价值？
6. abnormal activity 是否提升成功率？

## Range

1. range age 与 rotation count 是否提高质量？
2. edge asymmetry 是否预示 transition？
3. midpoint slope 是否能排除斜向通道？
4. midpoint 与 opposite-edge target 哪个更稳健？
5. volatility expansion 是否应成为更早 veto？
6. 在成本较高标的中 Range 是否天然失效？

## Scanner

1. WATCH 对未来 SETUP_READY 的 recall 与 lead time 是多少？
2. Top-N ranking 是否优于随机或简单流动性排序？
3. 哪种流动性维度最能解释滑点与结果？
4. 24h volume、OI、spread、impact 中哪些有增量？
5. 资产类别是否只是归因维度，还是出现稳定差异？
6. Scanner 是否遗漏正式三 Setup 会发现的事件？
7. 同一 BTC 驱动事件产生多少重复 alt candidates？
8. no-signal runtime proof 是否完整？

---

# 17. 推荐执行顺序

```text
STEP 1
读取 R1 / R1.1 / R1.2 与 Scanner R3

STEP 2
确认本文只作为外部研究补充，不自动覆盖冻结合同

STEP 3
冻结四个 simple comparator 的精确定义

STEP 4
冻结 P0 evidence schema 和 point-in-time universe schema

STEP 5
确认 P1 仅为预注册分层/消融，不新增主候选

STEP 6
运行现有六个 candidate + comparators

STEP 7
输出 setup × side × mode 的主结果

STEP 8
输出 Scanner WATCH / SETUP_READY 质量

STEP 9
输出 attribution、cost/delay stress、exact/proxy、trial count

STEP 10
裁决 KEEP / REVISE / INCONCLUSIVE / REJECT

STEP 11
只有在结果支持时，提出 R1.3 或下一版策略合同
```

---

# 18. 明确的最终建议

## 应保持不变

- 三 Setup 身份；
- 当前冻结的主要经济机制；
- closed-candle/no-lookahead；
- Q2 主逻辑；
- FAST/STANDARD 分离；
- Target Feasibility；
- Chase Limit；
- market-event 去重；
- 人工最终决策和人工执行；
- Scanner 只负责发现与排序。

## 应立即补充

- simple baselines；
- Level Attribution；
- event-path instrumentation；
- point-in-time universe；
- multidimensional liquidity；
- all-candidate evidence retention；
- Scanner evaluation；
- trial registry；
- cross-asset event clustering。

## 应在首次回测后才决定

- 是否调整参数；
- 是否升级 OI/funding；
- 是否引入 Session levels；
- 是否增加 Trend Pullback；
- 是否引入 L2、VWAP 或 Volume Profile；
- 是否使用模糊评分或 ML ranking。

核心研究原则：

```text
不要问：
“公开策略有什么参数可以直接复制？”

应当问：
“公开策略提供了什么经济机制、简单基线、因果字段和失败反例，
能够证明我们的复杂规则是否真正增加了价值？”
```

---

# 19. 主要参考资料

## 支撑阻力、订单聚集和价格级联

1. Carol L. Osler, **Support for Resistance: Technical Analysis and Intraday Exchange Rates**  
   https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html
2. Carol L. Osler, **Currency Orders and Exchange-Rate Dynamics**  
   https://www.newyorkfed.org/research/staff_reports/sr125.html
3. Carol L. Osler, **Stop-Loss Orders and Price Cascades in Currency Markets**  
   https://www.newyorkfed.org/research/staff_reports/sr150.html
4. Ken Chung and Anthony Bellotti, **Evidence and Behaviour of Support and Resistance Levels**  
   https://arxiv.org/abs/2101.07410

## Breakout、趋势和 Scanner 活跃度

5. Zarattini, Barbon, Aziz, **A Profitable Day Trading Strategy for the U.S. Equity Market**  
   https://ssrn.com/abstract=4729284
6. Liu and Tsyvinski, **Risks and Returns of Cryptocurrency**  
   https://www.nber.org/papers/w24877
7. Liu, Tsyvinski, Wu, **Common Risk Factors in Cryptocurrency**  
   https://www.nber.org/papers/w25882
8. Han, Kang, Ryu, **Momentum in the Cryptocurrency Market under Realistic Assumptions**  
   https://ssrn.com/abstract=4675565
9. Begušić and Kostanjčar, **Momentum and Liquidity in Cryptocurrencies**  
   https://arxiv.org/abs/1904.00890
10. Fičura and Colak, **Impact of Size and Volume on Cryptocurrency Momentum and Reversal**  
    https://ssrn.com/abstract=4378429
11. Brauneis et al., **How to Measure the Liquidity of Cryptocurrencies?**  
    https://ssrn.com/abstract=3503507

## Mean Reversion

12. Leung and Li, **Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit**  
    https://arxiv.org/abs/1411.5062
13. Kitapbayev and Leung, **Mean Reversion Trading with Sequential Deadlines and Transaction Costs**  
    https://arxiv.org/abs/1707.03498

## 回测过拟合和选择偏差

14. Bailey et al., **The Probability of Backtest Overfitting**  
    https://ssrn.com/abstract=2326253
15. Bailey and López de Prado, **The Deflated Sharpe Ratio**  
    https://ssrn.com/abstract=2460551
16. Sullivan, Timmermann, White, **Data-Snooping, Technical Trading Rule Performance, and the Bootstrap**  
    https://www.jstor.org/stable/2697739

## 官方数据接口

17. Hyperliquid, **Info Endpoint**  
    https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
18. Hyperliquid, **Perpetual Asset Contexts**  
    https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
19. Hyperliquid, **WebSocket Subscriptions**  
    https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions

## 开源实现

20. Smart Money Concepts Python  
    https://github.com/joshyattridge/smart-money-concepts
21. Turtle Trading Python  
    https://github.com/gabekutner/turtle-trading
22. Quant Trading Strategy Examples  
    https://github.com/je-suis-tm/quant-trading
23. Freqtrade Strategies  
    https://github.com/freqtrade/freqtrade-strategies

---

# 20. 最终状态

```text
EXTERNAL_RESEARCH_COMPLETED = YES
THREE_SETUP_IDENTITY_CHANGE_RECOMMENDED_NOW = NO
FROZEN_PARAMETER_CHANGE_AUTHORIZED = NO
FOURTH_SETUP_RECOMMENDED_NOW = NO

P0_MEASUREMENT_AND_BASELINE_EXPANSION = RECOMMENDED
P1_PRE_REGISTERED_DIAGNOSTICS = RECOMMENDED
SCANNER_POINT_IN_TIME_EVIDENCE = REQUIRED
MULTIPLE_TESTING_LEDGER = REQUIRED

BACKTEST_EXECUTED_BY_THIS_RECORD = NO
PERFORMANCE_IMPROVEMENT_PROVEN = NO
PRODUCTION_IMPLEMENTATION_AUTHORIZED = NO
DEPLOYMENT_AUTHORIZED = NO
EXCHANGE_WRITE_AUTHORITY = NO

NEXT_OWNER = STRATEGY_OPTIMIZATION_WINDOW
NEXT_ACTION = REVIEW_AND_FREEZE_RESEARCH_EXECUTION_PACKET
```
