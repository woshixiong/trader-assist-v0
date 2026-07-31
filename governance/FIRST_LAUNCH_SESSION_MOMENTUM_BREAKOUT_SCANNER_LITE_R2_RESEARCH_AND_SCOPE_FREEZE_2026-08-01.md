# First Launch Session Momentum Breakout Scanner Lite R2 研究与范围冻结

**记录 ID：** `TA-FIRST-LAUNCH-SCANNER-LITE-R2-2026-08-01`  
**状态：** `RESEARCH AND SCOPE FREEZE / NON-EXECUTABLE`  
**关联：** PR #52、R1 Scanner Lite 条件性计划、First Launch 三 Setup 同日最小上线计划  
**权限边界：** 本文不授权代码修改、部署、账户访问、交易所写入、自动资产切换或自动下单。

---

## 1. 本轮目标

First Launch 的目标不是盈利最大化，而是尽快产生足够多的真实候选与信号样本，用来验证：

1. Scanner 参数和分级是否合理；
2. Sweep / Breakout / Range 三个 Setup 在真实市场中是否有效；
3. 信号、人工判断、影子结果、实际成交和复盘流程是否顺畅。

因此第一版 Scanner 必须采用：

```text
HIGH_RECALL
+ HUMAN_FINAL_FILTER
+ COMPLETE_EVIDENCE
```

候选数量过少本身是 First Launch 的失败风险。

---

## 2. 对 R1 的主要修正

### 2.1 不按资产类别硬分池或硬排除

第一版扫描所有能够通过最低市场质量和数据健康门槛的 Hyperliquid 永续市场，包括：

- 原生加密资产；
- 山寨币；
- HIP-3 股票；
- 股票指数；
- 黄金、原油等商品；
- 其他 builder-deployed perpetual markets。

资产类别不直接决定是否可交易，仅作为：

- 展示标签；
- 事件和交易时段上下文；
- 后续统计归因维度；
- 风险解释字段。

### 2.2 不把“流动性”简化为成交量

成交量高是必要信号之一，但不足以代表可执行流动性。第一版最低应区分：

```text
TURNOVER / ACTIVITY
SPREAD
ORDER-BOOK DEPTH
EXPECTED SLIPPAGE AT REFERENCE NOTIONAL
OPEN INTEREST
DATA / MARKET INTEGRITY
```

核心原因：成交量可以很高，但当前盘口仍可能很薄、点差很宽或价格冲击很大。

### 2.3 统一市场池 + 统一算法 + 统计标签

推荐结构：

```text
ALL ELIGIBLE PERP MARKETS
→ COMMON MARKET-QUALITY GATES
→ COMMON MOMENTUM / BREAKOUT SCAN
→ WATCH / SETUP_READY 分级
→ ASSET-CLASS / SESSION / LIQUIDITY TAGS
→ HUMAN REVIEW
```

不预设 crypto、股票、指数和商品一定使用不同策略参数。先记录，再用真实结果检验类别是否有增量解释力。

---

## 3. 最低市场质量门槛

仅以下情况硬拒绝：

- 市场暂停、结算或不可交易；
- metadata、mid、mark、BBO 或必要 candle 缺失/陈旧/冲突；
- 历史长度不足以计算所需 ATR、结构位和基线；
- 点差、盘口深度或参考名义滑点明显不可接受；
- 当前价格、mark/oracle 或精度表现异常；
- API 证据无法完整保存。

不因资产类别本身拒绝。

### 3.1 建议的流动性度量

第一版应保存并排序：

```text
spread_bps
best_bid_size / best_ask_size
book_depth_within_10bps_or_20bps
estimated_slippage_for_reference_notional
24h_notional_volume
open_interest
turnover_to_open_interest
```

参考名义金额应采用配置，不写死在策略代码中。最终由工程与风险配置决定测试档位。

---

## 4. Scanner 两级输出

### 4.1 WATCH

目的：尽早提醒人类打开盘面，不等待完整 Setup 成立。

建议由以下任意组合触发：

- 时段绝对涨跌幅进入全市场较高分位；
- 相对 BTC 或全市场中位数出现显著超额；
- normalized move 达到初始研究区间；
- 量能、OI 或交易活跃度明显放大；
- 接近或刚刚突破预先存在的前高/前低。

WATCH 允许较高召回率，必须显示：

- 距离结构位；
- 当前追价距离；
- 流动性摘要；
- 资产类别和 session；
- `NOT_YET_SETUP_CONFIRMED`。

### 4.2 SETUP_READY

目的：标记已经接近现有策略规则、值得立即人工判断的候选。

至少包括：

- `BREAKOUT_RETEST_READY`；
- `FAILED_BREAKOUT_SWEEP_WATCH`；
- 未来可加入 `RANGE_EDGE_WATCH`，但不阻塞第一版。

Scanner 只提供候选状态；现有三个 Setup 与人类交易员拥有最终判断权。

---

## 5. 参数研究框架

第一版不冻结单点最优参数，只冻结低复杂度参数族和研究区间。

### 5.1 活跃度和动量

```text
session_return
relative_return_vs_BTC
relative_return_vs_universe_median
normalized_move = abs(session_return) / ATR_percent
relative_volume
OI_change
```

采用分位数 + 波动率标准化，避免不同资产天然波动差异导致排名失真。

### 5.2 结构突破

- 只允许使用突破前已经存在的 prior high / prior low；
- 只认 closed 5m candle；
- 突破缓冲使用 ATR 与 spread 的组合；
- 必须记录突破后最大延伸和距离 level；
- 超过 Chase Limit 仍可保留为研究样本，但不得显示为可追价候选。

### 5.3 回踩 / 反抽

必须记录：

- 突破到第一次回踩的 bar 数和分钟数；
- 回踩深度；
- 是否重新进入旧区间；
- 回踩时量能变化；
- 再次向突破方向收盘；
- 后续 MFE / MAE。

R2 不预设所有资产类别需要不同回踩参数；通过分组结果再判断。

---

## 6. 资产类别是否重要：用数据回答

本轮不争论“流动性足够是否已经足够”，而是设计可检验结构。

每条候选至少带上：

```text
asset_class
perp_dex
native_or_HIP3
session
liquidity_decile
spread_bucket
slippage_bucket
volatility_bucket
setup_family
alert_level
```

后续比较两类解释：

```text
MODEL_A = LIQUIDITY + VOLATILITY + STRUCTURE ONLY
MODEL_B = MODEL_A + ASSET_CLASS + SESSION + HIP3 FLAG
```

如果加入资产类别后没有明显提高解释力，则未来可以简化为以市场质量为主；如果股票、商品、指数或某类 crypto 的结果显著不同，再建立独立 Instrument Profile。

---

## 7. 分级本身必须接受验证

WATCH 和 SETUP_READY 都必须进入日志和结果统计。

最低指标：

- WATCH → SETUP_READY 转化率；
- WATCH 提醒是否发生在回踩完成之前；
- SETUP_READY 经人工认可的比例；
- T / S / R 和拒绝原因；
- 后续 MFE / MAE、TP、Stop、Expiry；
- 真实成交结果（可获得时）；
- 按 asset_class、liquidity_decile、session、setup_family 分组；
- WATCH 与 SETUP_READY 的净 R 和信号质量差异；
- 同资产、同时间随机 eligible 候选基线。

如果 SETUP_READY 没有显著优于 WATCH，说明分级逻辑无效或过严/过松。

---

## 8. No-Signal / Runtime 证明

只要能够低成本复用现有状态或日志，应增加：

```text
last_evaluated_candle
last_evaluation_time
runtime_ready
sweep_state / wait_reason
breakout_state / wait_reason
range_state / wait_reason
```

用于区分：

- 系统正常评估但没有机会；
- 系统未正常运行或未完成评估。

该项不得引入复杂 UI 或新平台。

---

## 9. 技术结构

第一版仍采用隔离旁路：

```text
Hyperliquid public APIs / official SDK-compatible schema
→ market discovery
→ common market-quality gates
→ common ranker
→ breakout / retest state tracker
→ append-only evidence
→ terminal / optional existing notification transport
```

与当前 ETH-only runtime 同一发布、同一次部署，但不强行合并为同一运行进程。

成熟架构参考：

- Freqtrade Dynamic Pairlist / VolumePairList / PercentChangePairList；
- Age / Delist / Spread / Volatility / Range Stability filters；
- Hyperliquid official Python SDK and public API schemas。

复用的是 pipeline 设计，不因此引入完整外部交易框架。

---

## 10. 当前尚不冻结工期

本记录明确取消此前未经 exact scope 审查的固定开发时长。

```text
TIME_ESTIMATE = PENDING_ENGINEERING_SCOPE
```

工程优化必须先给出：

- ETH-only 绑定解除需要与不需要的部分；
- exact file scope；
- 是否新增依赖；
- HTTP / WebSocket / rate-limit 预算；
- 状态跟踪是否需要持久化；
- 通知复用方式；
- 测试和部署边界；
- 与三 Setup 合并发布的关键路径。

只有这些明确后，才能给出可信工期。

---

## 11. 当前冻结结论

```text
PURPOSE = GENERATE SUFFICIENT REAL-MARKET EVIDENCE
SCANNER_BIAS = HIGH_RECALL
HUMAN_FINAL_DECISION = REQUIRED
UNIVERSE = ALL ELIGIBLE HYPERLIQUID PERPS
ASSET_CLASS = TAG_AND_ATTRIBUTION, NOT HARD EXCLUSION
LIQUIDITY = MULTI-DIMENSIONAL, NOT VOLUME_ONLY
ALERT_LEVELS = WATCH + SETUP_READY
ALERT_LEVEL_VALIDATION = REQUIRED
ASSET_CLASS_PERFORMANCE_ATTRIBUTION = REQUIRED
NO_SIGNAL_RUNTIME_EVIDENCE = INCLUDE_IF_LOW_COST
SAME_RELEASE_AND_DEPLOYMENT_WITH_THREE_SETUPS = TARGET
SAME_PROCESS = NOT_REQUIRED
AUTO_TRADE = NO
AUTO_ASSET_SWITCH = NO
TIME_ESTIMATE = NOT_YET_FROZEN
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```

R2 supersedes R1 wherever the two records conflict.