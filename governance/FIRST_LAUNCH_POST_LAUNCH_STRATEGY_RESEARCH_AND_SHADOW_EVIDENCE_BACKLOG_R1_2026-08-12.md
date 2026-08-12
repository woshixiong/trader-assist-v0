# First Launch 上线后策略研究与 Shadow Evidence Backlog R1

**记录 ID：** `TA-FIRST-LAUNCH-POST-LAUNCH-STRATEGY-RESEARCH-SHADOW-EVIDENCE-R1-2026-08-12`  
**日期：** `2026-08-12`  
**状态：** `CURRENT POST-LAUNCH STRATEGY RESEARCH AUTHORITY / NON-EXECUTABLE / NON-AUTHORIZING`  
**适用阶段：** `POST_FIRST_LAUNCH / SHADOW_FORWARD_VALIDATION / V0.2 STRATEGY_OPTIMIZATION`  
**目的：** 不扩大当前发布范围，利用真实 ShadowOrder、Candidate、Transition、Outcome 和市场路径数据验证最近实盘发现的策略问题，为下一轮策略优化提供可审计证据。

---

## 1. 当前发布结论

本文件不增加第四个 Setup，不修改当前 Machine Strategy R1/R1.1，不授权新增正式交易信号。

当前固定：

```text
NEW_FORMAL_SETUP_THIS_RELEASE = 0
MAJOR_STRATEGY_CONTRACT_CHANGE_THIS_RELEASE = 0
FAILED_ACCEPTED_BREAKOUT_FORMAL_SIGNAL_THIS_RELEASE = NO
EVENT_REGIME_LOGIC_THIS_RELEASE = NO
CASH_OPEN_STRATEGY_THIS_RELEASE = NO
PROBE_ADD_ENGINE_THIS_RELEASE = NO
DYNAMIC_LOGICAL_EXIT_THIS_RELEASE = NO
CROSS_MARKET_HARD_GATE_THIS_RELEASE = NO
```

当前三 Setup 继续为：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST  # including Micro FAST + Standard
RANGE_EDGE_REJECTION
```

当前 Scanner R3 已有的 Momentum / Relative Strength / Failed Breakout Watch 继续按既有合同实施。

---

## 2. 为什么 Shadow Forward Validation 足以成为下一轮研究主数据源

现有 Forward Validation 合同已经要求 Candidate 级保存：

- setup family / market event identity；
- scanner score components / rank；
- HTF labels；
- volatility / liquidity；
- prior level / zone；
- breakout / retest / sweep path；
- chase status；
- linked signal / plan。

Outcome 已要求自动生成：

```text
30m_MFE_MAE
60m_MFE_MAE
120m_MFE_MAE
ATR_normalized_MFE_MAE
1R_1_5R_2R_hit_if_plan_exists
stop_hit_if_plan_exists
time_to_retest
time_to_1R
return_inside_range
failed_breakout
path_maturity_status
```

因此本轮原则是：

```text
USE_REAL_FORWARD_MARKET_EVIDENCE = YES
BUILD_NEW_STRATEGY_BEFORE_EVIDENCE = NO
```

研究必须同时保留 Taken / Skipped / Rejected / Unlabeled，不得只分析盈利或人工实际执行的订单。

---

## 3. 最高优先研究项目：FAILED_ACCEPTED_BREAKOUT / FAILED_IMPULSE

### 3.1 研究问题

区分：

```text
A. IMMEDIATE_SWEEP
level 被短暂刺破后快速收回

B. FAILED_ACCEPTED_BREAKOUT
市场先完成有效 Breakout / Acceptance / Impulse，随后整个突破被否定
```

B 是当前正式机器策略未完全覆盖的研究缺口。

典型 Long Breakout Failure：

```text
Breakout
→ Acceptance
→ Favorable Impulse
→ Return Into Old Value / Zone
→ Failed Reclaim
→ Lower High / Weak Recovery
→ Breakdown
```

Short 全部镜像。

### 3.2 研究样本

至少纳入：

```text
ALL FORMAL BREAKOUT MICRO FAST SHADOW ORDERS
ALL FORMAL BREAKOUT STANDARD SHADOW ORDERS
ALL FAILED_BREAKOUT_SWEEP_WATCH CANDIDATES
ALL BREAKOUT EVENTS INVALIDATED BY ACCEPTED RE-ENTRY
ALL SUBSEQUENT OPPOSITE SWEEP / FORMAL EVENTS LINKABLE TO THE SAME MARKET PATH
```

不得只看“被止损”的 Breakout；成功 Breakout 必须作为对照组。

### 3.3 必须可恢复的 Breakout 特征

优先复用当前策略/Scanner 已经计算的数据；本轮不得为此建设新实时策略引擎。

研究导出必须能够直接保存或离线重建：

```text
market_id
setup_mode = MICRO_FAST | STANDARD
direction
zone_id
zone_quality
initial_breakout_candle_id
initial_breakout_time
initial_breakout_open/high/low/close
A5_EVENT
M20_EVENT
breakout_body_atr
breakout_volume_ratio
breakout_clv
breakout_distance_atr
HTF_RELATION
scanner_relative_strength_rank
session_tag
planned_entry
stop
tp1
tp2
```

如果这些值已经存在于 Strategy/Candidate 对象，只持久化现有值；不得重复建立第二套计算公式。

### 3.4 必须可恢复的后续路径

优先通过现有 5m Candidate/Event path 与 Formal ShadowOrder 的 on-demand 1m Outcome path 离线计算：

```text
max_favorable_excursion_before_first_reentry
bars_outside_breakout_zone
time_outside_breakout_zone
first_return_inside_range_time
return_inside_range_depth_atr
accepted_reentry_time
max_adverse_excursion_after_reentry
reclaim_attempt_count
reclaim_success_or_failure
post_failure_reverse_30m_MFE_MAE
post_failure_reverse_60m_MFE_MAE
post_failure_reverse_120m_MFE_MAE
original_trade_stop_hit
original_trade_net_R_if_available
```

第一版不要求把所有上述衍生值实时写成数据库列；只要求现有 Evidence 数据足以在导出后确定性重建。若某一关键值无法离线恢复，Engineering 才允许增加最小原始字段，不得增加正式策略行为。

### 3.5 后续离线分类

未来 Strategy Optimization 可以离线建立研究标签：

```text
SUCCESSFUL_BREAKOUT
IMMEDIATE_BREAKOUT_FAILURE
DELAYED_FAILED_ACCEPTED_BREAKOUT
AMBIGUOUS_FAILURE_PATH
INSUFFICIENT_DATA
```

这些标签当前：

```text
RESEARCH_ONLY = YES
LIVE_SIGNAL_AUTHORITY = NO
```

不得在当前发布中根据该标签生成新的反向 Formal Signal。

### 3.6 下一轮升级门禁

只有真实前向数据证明 `FAILED_ACCEPTED_BREAKOUT`：

- 可重复识别；
- 不依赖事后观察才能定义；
- 在多个市场/不同市场状态中重复出现；
- 与成功 Breakout 的特征存在稳定可解释差异；
- 反向交易后的 Net Expectancy / MFE/MAE / Drawdown 有实际价值；
- Cluster-normalized 后仍保留有效性；

才重新讨论：

```text
SWEEP_RECLAIM.FAILURE_MODE = IMMEDIATE_SWEEP | FAILED_ACCEPTED_BREAKOUT
```

优先作为现有 Setup Extension，而不是第四个 Setup。

---

## 4. 第二优先研究项目：PER_MARKET_STABLE_TIMEFRAME_PROFILE

本项目已经由：

`FIRST_LAUNCH_MANUAL_40_MARKET_REGISTRY_FAST_ROUTE_AND_TIMEFRAME_PROFILE_BACKLOG_R1_2026-08-12.md`

单独冻结。

本轮数据应允许后续比较：

```text
FAST_5M_PROFILE
vs
future slower profile simulated offline
```

当前原始 5m 数据可以严格聚合 15m / 1h，因此未来大部分周期对照研究应优先离线完成，不先增加生产多周期分支。

重点观察：

- 5m 噪声率；
- Formal Signal 频率；
- Stop Distance；
- Zone Width；
- Gross / Net R；
- Drawdown；
- Failed Breakout 率；
- 不同资产类别表现。

---

## 5. 第三优先研究项目：SECTOR / PEER RELATIVE STRENGTH

当前 Scanner R3 已经包含：

```text
cross-sectional return rank
relative return vs universe median
relative return vs BTC
```

本轮不增加第二套 Relative Strength Engine。

上线后利用固定 40 市场数据研究简单 Peer Group：

示例：

```text
MEMORY = SKHX / MU / SNDK / DRAM
SEMICONDUCTOR = NVDA / AMD / MU / related available peers
CRYPTO_CORE = BTC / ETH / SOL / HYPE / XRP
INDEX_CONTEXT = XYZ100 / SP500
```

未来仅在证据支持时研究：

```text
PEER_RELATIVE_RETURN_RANK
AS SCANNER RANKING BONUS/PENALTY
```

禁止直接升级为 Formal Signal Hard Gate，除非之后独立证明跨市场依赖的稳定性和故障隔离安全性。

---

## 6. EVENT REGIME 研究

当前不自动接入经济日历，也不改变 Breakout/Sweep 参数。

上线后可以通过人工标记或离线时间 Join 研究：

```text
NORMAL
EVENT
```

重点事件包括但不限于：

- NFP；
- CPI；
- FOMC；
- PCE；
- 财报；
- 已知高影响预定事件。

研究：

- 第一根 spike 的失败率；
- Micro FAST 成功率；
- Standard Retest 成功率；
- accepted re-entry；
- slippage / spread；
- MFE / MAE；
- Failed Breakout 比例。

只有真实数据证明需要不同参数，才讨论 `EVENT_REGIME` 正式策略合同。

---

## 7. CASH OPEN / OPENING REPRICING 研究

Scanner 已有 US Cash Session Tag / Anchor，优先复用现有 session evidence。

研究：

```text
PREMARKET_IMPULSE
→ CASH_OPEN_CONTINUATION
or
→ CASH_OPEN_REPRICING_FAILURE
```

本轮不新增 Opening Setup。

未来分析至少比较：

- Cash Open 前已有趋势 vs 开盘后方向；
- 开盘 30/60/120m MFE/MAE；
- Breakout accepted-reentry；
- Sweep 频率；
- Failed Breakout 率；
- P0/P1 股票、指数和 commodity 的差异。

---

## 8. LOGICAL INVALIDATION vs HARD STOP 研究

本轮不开发动态退出引擎。

但 Formal ShadowOrder 的 1m Outcome path 必须足够支持离线比较：

```text
CURRENT HARD / STRUCTURAL STOP RESULT
vs
HYPOTHETICAL LOGICAL INVALIDATION EXIT
```

未来研究问题：

- 如果 Breakout 已 accepted re-entry，提前退出是否减少 MAE / Drawdown；
- 是否也会过早退出最终成功交易；
- Sweep / Range 是否存在类似结构失效点；
- 扣除手续费/滑点后是否仍改善 Net Expectancy。

研究通过前不得改变当前正式 Stop 合同。

---

## 9. PROBE → ADD 研究

当前不建设多腿 Position Management Engine。

利用 1m Shadow path 可以在离线环境模拟：

```text
25% / 33% PROBE
→ confirmation
→ hypothetical ADD
```

比较：

- full-entry baseline；
- Probe only；
- Probe + Add；
- Failed Breakout 下的损失；
- Trend continuation 下的收益牺牲；
- Net R / Drawdown。

只有离线与前向数据证明收益足以覆盖工程复杂度，才进入未来 Execution Rule 开发。

---

## 10. Cross-Market Confirmation 研究

本轮不得作为 Hard Gate。

现有 Scanner Relative Strength、固定 40 市场数据和 Exposure Cluster 已足够作为研究基础。

未来可离线生成：

```text
CROSS_MARKET_CONTEXT_SCORE
```

例如同一 Peer Group 中支持当前方向的市场数量/排名。

只研究其是否改善信号排序、选择 Leader 和预测 Failed Breakout；不得因 Peer 数据缺失而让当前合格 Formal Signal 失效。

---

## 11. 当前发布需要保证的数据，不新增策略功能

Engineering 只需确认当前 Evidence Pipeline 能够做到：

```text
1. 保存所有 P0/P1/P2 Formal Signals / ShadowOrders / Outcomes；
2. 保存 Scanner WATCH / SETUP_READY / FAILED_BREAKOUT_SWEEP_WATCH；
3. 保存 Breakout/Sweep/Retest 关键 Transition 和 Candle Identity；
4. 保存当前策略已经计算的 ATR / volume / CLV / Zone / HTF / relative-strength / session evidence；
5. Formal ShadowOrder 具备 on-demand 1m Outcome path 或可回补路径；
6. 30/60/120m MFE/MAE、return_inside_range、failed_breakout 等 Outcome 可导出；
7. 导出绑定 strategy_version / parameter_version / release_sha；
8. 保留 Raw 和 Correlation Cluster Identity，避免相关市场重复样本污染研究。
```

如果现有计划已经满足：

```text
ADDITIONAL_STRATEGY_ENGINEERING = 0
```

如果缺少某个无法离线重建的关键原始字段：

```text
ALLOW_MINIMAL_EVIDENCE_FIELD_ONLY
NO_NEW_LIVE_DECISION_LOGIC
NO_NEW_FORMAL_SIGNAL
```

不得借本研究 Backlog 扩大当前发布范围。

---

## 12. Post-Launch 策略研究优先级

当前冻结顺序：

```text
R1 = FAILED_ACCEPTED_BREAKOUT / FAILED_IMPULSE
R2 = PER_MARKET_STABLE_TIMEFRAME_PROFILE
R3 = SECTOR / PEER RELATIVE STRENGTH
R4 = EVENT REGIME
R5 = CASH OPEN / OPENING REPRICING
R6 = LOGICAL INVALIDATION EXIT
R7 = PROBE → ADD
R8 = CROSS-MARKET CONFIRMATION SOFT SCORE
```

该顺序允许 Strategy Optimization 根据真实数据调整，但任何开发都必须先有 Evidence Review 和新版本化 Strategy Contract。

---

## 13. 何时启动下一轮 Strategy Optimization

不预设固定日期或固定 ShadowOrder 数量。

启动条件为实际 Evidence 足以回答至少一个明确问题，例如：

- 同类 Failed Breakout 重复出现；
- 某类市场 5m Profile 持续表现异常；
- Peer Relative Strength 明显区分成功/失败；
- Event/Cash Open 标签下收益分布出现稳定差异；
- Logical Exit / Probe-Add 离线对照产生显著一致的改善。

Strategy Optimization 必须同时审查：

```text
RAW_SAMPLE_COUNT
INDEPENDENT_CLUSTER_COUNT
MARKET_DIVERSITY
SETUP / MODE DISTRIBUTION
P0/P1/P2 DISTRIBUTION
GROSS_OUTCOME
NET_OUTCOME_IF_AVAILABLE
MFE / MAE
DRAWDOWN
CORRELATION_COMPRESSION
DATA_COMPLETENESS
```

禁止仅凭几次人工印象升级正式策略。

---

## 14. 最终固定状态

```text
CURRENT_RELEASE_STRATEGY_DELTA_FOR_NEW_IDEAS = ZERO
SHADOW_DATA_AS_PRIMARY_NEXT_STRATEGY_RESEARCH_SOURCE = YES
FAILED_ACCEPTED_BREAKOUT_RESEARCH = HIGH_PRIORITY
FAILED_ACCEPTED_BREAKOUT_LIVE_SIGNAL = NO
EVENT_REGIME_RESEARCH = YES
CASH_OPEN_RESEARCH = YES
SECTOR_RELATIVE_STRENGTH_RESEARCH = YES
LOGICAL_EXIT_RESEARCH = YES
PROBE_ADD_RESEARCH = YES
CROSS_MARKET_SOFT_SCORE_RESEARCH = YES
PER_MARKET_TIMEFRAME_PROFILE_RESEARCH = YES

NEW_STRATEGY_DEVELOPMENT_REQUIRES_FORWARD_EVIDENCE = YES
ENGINEERING_MAY_ADD_MINIMAL_EVIDENCE_FIELDS_ONLY_IF_NOT_RECONSTRUCTABLE = YES
ENGINEERING_MAY_ADD_NEW_LIVE_STRATEGY_LOGIC_FROM_THIS_FILE = NO
```

本文件不授权代码修改、工程派发、部署、重启、账户访问、签名、交易所写入、自动交易、PR Mark Ready 或 Merge。