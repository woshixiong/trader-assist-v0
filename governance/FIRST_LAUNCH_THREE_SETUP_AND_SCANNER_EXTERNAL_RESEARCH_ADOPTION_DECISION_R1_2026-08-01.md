# First Launch 三 Setup 与 Scanner 外部研究采用裁决 R1

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-SCANNER-EXTERNAL-RESEARCH-ADOPTION-2026-08-01-R1`  
**日期：** `2026-08-01`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**目标分支：** `agent/v0-strategy-predevelopment-analysis-r1`  
**输入研究：** `FIRST_LAUNCH_THREE_SETUP_AND_SCANNER_EXTERNAL_PRICE_ACTION_RESEARCH_R1_2026-08-01.md`  
**策略语义权威：** `R1.2 > R1.1 > R1`  
**Scanner 参数权威：** `FIRST_LAUNCH_SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE_R3_FINAL_PARAMETER_AND_DELIVERY_FREEZE_2026-08-01.md`  
**状态：** `RESEARCH ADOPTION DECISION / NON-EXECUTABLE / NON-AUTHORIZING`

---

## 1. 最终裁决

外部研究有明确价值，应纳入后续策略研究和 Scanner 验证体系，但其主要价值是：

```text
MEASUREMENT
+ SIMPLE COMPARATORS
+ EVENT-PATH ATTRIBUTION
+ POINT-IN-TIME EVIDENCE
+ MULTIPLE-TESTING CONTROL
```

而不是：

```text
IMMEDIATE PARAMETER REWRITE
OR FOURTH SETUP
OR NEW PRODUCTION HARD FILTERS
```

固定结论：

```text
THREE_SETUP_IDENTITY_CHANGE_NOW = NO
SCANNER_R3_THRESHOLD_CHANGE_NOW = NO
FOURTH_SETUP_NOW = NO
MEASUREMENT_AND_VALIDATION_OPTIMIZATION = YES
EXTERNAL_RESEARCH_REUSE_IN_FUTURE = REQUIRED
```

---

## 2. 对现有三 Setup 的判断

现有三 Setup 已覆盖高质量结构边界附近最重要的三类市场结果：

```text
RANGE_EDGE_REJECTION = 边界内拒绝
SWEEP_RECLAIM = 越界后未被接受并收回
BREAKOUT_RETEST = 越界、接受、回踩后延续
```

外部研究没有证明需要立即增加第四个 Setup，也没有提供可以直接复制为 ETH 5m/15m 生产阈值的参数。

因此，当前策略优化重点从“增加形态和指标”调整为：

1. 判断高质量边界为什么有效；
2. 保存完整事件路径，而不仅是最终触发 candle；
3. 用简单规则验证当前复杂规则是否真正增加价值；
4. 记录成本、延迟、流动性和标的异质性；
5. 控制试验次数和选择偏差。

---

## 3. 当前发布应保留不变的内容

以下内容不因本研究自动改变：

- 三个 Setup 的身份和经济机制；
- 当前主候选和敏感性候选；
- Q2 主资格逻辑；
- closed-candle / no-lookahead；
- FAST / STANDARD 语义；
- Target Feasibility；
- Chase Limit；
- market-event 去重原则；
- Scanner R3 首发数值参数；
- 人工最终判断与人工执行；
- 无交易所写权限。

任何参数修改必须等待真实回测和实盘证据，并形成新的策略合同裁决。

---

## 4. 当前发布的最低证据优化

为了不扩大为完整研究平台，当前三 Setup + Scanner 发布只把以下内容视为最低证据合同。

### 4.1 Scanner 点时市场宇宙

每次 Scanner cycle 必须能够恢复当时真实 universe。

允许两种实现：

1. 完整不可变 universe snapshot；
2. content-addressed immutable snapshot + 可解析引用 hash。

禁止只保存无法恢复成员和字段的孤立 hash。

最低成员证据：

```text
market / coin / dex
active_state
market_age_or_first_seen
history_sufficiency
asset_class / HIP3 flag
mid / mark / oracle validity
24h notional activity
open_interest when available
spread / impact or estimated slippage
data freshness / gaps / rejection reasons
session and liquidity tags
```

### 4.2 全候选留存

```text
ALL_ELIGIBLE_WATCH_RETAINED = YES
ALL_SETUP_READY_RETAINED = YES
TOP_N_LIMITS_NOTIFICATION_ONLY = YES
```

不得只保存推送给用户的 Top-N，否则无法计算 Scanner recall、missed candidates 和 selection bias。

### 4.3 Scanner 与 Setup 权威分离

Scanner 的综合分数只允许承担通知排序，不能替代三个 Setup 的因果规则。

首发最低字段：

```text
candidate_path
breakout_watch_evidence
sweep_watch_evidence
range_watch_evidence_if_available
notification_rank_score
exact_setup_evaluation_state
```

若工程成本允许，保存独立：

```text
breakout_watch_score
sweep_watch_score
range_watch_score
```

若首发不实现三个独立数值分数，至少必须保存策略路径和各组成证据，避免一个 global score 隐式成为交易权威。

### 4.4 最小事件路径

当前发布优先保存可直接从已有数据低成本产生的路径字段：

```text
level_price
level_source_or_current_contract_source
level_age_bars
first_touch_time
maximum_excursion_ATR
outside_or_acceptance_closed_bar_count
reclaim_or_acceptance_time
breakout_extension_ATR
time_to_first_retest
pre_retest_maximum_extension_ATR
retest_depth_ATR
chase_limit_state
range_age_and_rotation_if_already_available
```

不要求为了完整字段重构主策略；无法低成本获得的扩展字段进入首次研究包而非发布阻断。

### 4.5 参数与试验身份

每条 candidate、Signal 和结果至少绑定：

```text
scanner_version
parameter_version
strategy_version
setup_family
candidate_id / event_id
universe_snapshot_id
```

隐藏修改参数或无法还原当时参数的结果无研究效力。

### 4.6 No-Signal 证明

低成本情况下继续要求：

```text
last_evaluated_candle
last_evaluation_time
runtime_ready
sweep_state / wait_reason
breakout_state / wait_reason
range_state / wait_reason
```

---

## 5. 首次正式研究包必须增加的四个简单对照组

以下 comparator 是离线研究基线，不进入生产信号和交易权限：

```text
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
DONCHIAN_TURTLE_BREAKOUT_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

所有 comparator 必须使用与主策略相同的：

- 数据截止；
- closed-candle 语义；
- 手续费；
- 滑点；
- 人工延迟；
- funding 处理；
- ambiguous path；
- time exit；
- event dedup；
- 结果指标。

目的不是找到另一个公开策略，而是回答：

> Q2、环境、成交量、FAST/STANDARD、回踩确认、目标可行性和复杂冲突逻辑，相比简单规则究竟增加了多少价值？

Comparator 不阻断当前 First Launch 生产发布，但必须进入第一次正式策略优化/回测执行包。

---

## 6. 首次正式研究包必须增加 Trial Registry

每次参数、过滤器、候选或消融必须记录：

```text
trial_id
hypothesis
candidate_family
changed_variable
unchanged_variables
dataset_cut
cost_model
delay_model
primary_or_sensitivity
result
decision
number_of_visible_prior_trials
```

当前最低要求是完整 trial count 和选择偏差警告。

PBO、Deflated Sharpe Ratio 和更重的 bootstrap：

- 不进入当前最小发布；
- 不进入同日最低历史筛查的硬门槛；
- 在试验数量和数据规模足够时进入正式研究报告。

---

## 7. 三 Setup 的后续研究重点

### 7.1 Sweep

优先研究：

```text
excursion depth
outside duration
reclaim latency
reclaim speed
post-reclaim MFE / MAE
OI build or unwind when available
level source / age / reaction count
```

不得在取得结果前继续同时调整 excursion、volume、close location 和 level quality。

### 7.2 Breakout

优先研究：

```text
time to retest
pre-retest extension
retest depth
acceptance closed-bar count
failed-breakout taxonomy
relative activity
level quality and target space
```

`FAILED_BREAKOUT_SWEEP_WATCH` 继续只是候选路径，是否转换为正式 Sweep 必须由策略合同决定。

### 7.3 Range

优先研究：

```text
range age
rotation count
upper/lower reaction symmetry
midpoint drift
range width expansion
midpoint vs partial-rotation vs opposite-edge outcomes
```

Target Feasibility 不得为了增加信号而提前放宽。

---

## 8. Scanner 的后续研究重点

Scanner 必须被独立评估，而不只是统计最终交易结果。

### WATCH

```text
watch_to_setup_ready_conversion
watch_recall_of_future_setup_ready
watch_precision
median_and_p90_lead_time
missed_setup_ready
false_watch
alerts_per_hour
duplicate_watch_rate
```

### SETUP_READY

```text
human_T_S_R_rates
MFE / MAE
net expectancy when TradePlan exists
chase_limit_breach
cost_stress_survival
delay_stress_survival
```

### Ranking

对每个 Setup 路径分别评估：

```text
top_1 / top_3 / top_5 hit rate
outcome_by_score_decile
rank correlation or NDCG when sample permits
```

### Point-in-time and clustering

后续正式研究必须报告：

```text
raw_candidate_count
deduplicated_market_events
cross_asset_event_clusters
candidates_per_cluster
concentration_by_asset_and_date
```

跨资产事件聚类不要求阻断当前首发；但在全市场 Scanner 的统计结论中必须补上，否则不能把同一次 BTC/宏观驱动的多个标的当作完全独立样本。

---

## 9. 资产类别与流动性的研究原则

继续采用 Scanner R3 的原则：

```text
ASSET_CLASS = TAG_AND_ATTRIBUTION_NOT_HARD_FILTER
LIQUIDITY = MULTIDIMENSIONAL
```

后续比较：

```text
MODEL_A = LIQUIDITY + VOLATILITY + STRUCTURE
MODEL_B = MODEL_A + ASSET_CLASS + SESSION + HIP3_FLAG
```

只有当资产类别在控制流动性、波动率和结构后仍提供稳定增量解释力，才建立 Instrument Profile 或分类参数。

---

## 10. 外部框架与公开资源的固定用途

### 可以复用

- Freqtrade：动态 pairlist、过滤流水线、lookahead/recursive 检查、dry-run 研究方法；
- Turtle/Donchian 开源实现：简单趋势突破 comparator；
- smart-money-concepts：离线结构标签、fixture 和接口设计参考；
- TA-Lib patterns：confirmation feature 对照；
- Hyperliquid 官方 API：point-in-time market、candle、OI、funding、mark/oracle/premium、impact 和 L2 证据。

### 不得直接采用

- 社区公开收益或参数直接生产化；
- 未修正 lookahead 的 swing/BOS/CHoCH；
- FVG、Order Block 或“机构订单流”叙事直接成为新 Setup；
- LLM、ML 或 fuzzy score 直接决定 eligibility；
- 把 Freqtrade/Hummingbot 等完整框架强行引入当前 First Launch 关键路径。

所有开源实现进入代码前必须单独核对许可证、数据语义、lookahead、费用和测试。

---

## 11. 分阶段采用矩阵

### 当前发布必须或低成本应有

1. causal closed-candle；
2. point-in-time universe 可恢复证据；
3. all-candidate retention；
4. candidate/rejection/state/score versioning；
5. Scanner 与正式 Setup 权威分离；
6. 最小事件路径；
7. T/S/R 与 Outcome 链接；
8. No-Signal proof；
9. 相同发布和部署中的失败隔离。

### 第一次正式回测/策略优化包

1. 四个 simple comparators；
2. Trial Registry；
3. 完整 Level Attribution；
4. 扩展 event-path instrumentation；
5. 预注册 P1 buckets；
6. event-level dedup；
7. Scanner recall/precision/lead-time；
8. 统一成本和延迟压力；
9. exact recent vs proxy 分离。

### 首次结果后

1. Session/previous-day levels 是否升级；
2. OI/funding 是否成为过滤或风险变量；
3. Trend Pullback 第四 Setup；
4. Compression Expansion；
5. VWAP/Volume Profile；
6. L2/order-flow；
7. fuzzy/ML ranking；
8. Instrument Profile。

### 延期

- 自动交易；
- 自动资产切换；
- 新的复杂硬过滤器；
- 大规模参数网格；
- 只保留最佳资产或时段；
- 删除失败 trial；
- 根据公开收益声明直接复制策略。

---

## 12. 后续窗口必须沿用的研究原则

Strategy Optimization、Product Optimization、Engineering Optimization 和 Project Control 在后续任务中必须引用本记录和外部研究原文。

固定原则：

```text
PUBLIC_RESEARCH_PROVIDES_MECHANISMS_AND_COMPARATORS
NOT_PRODUCTION_THRESHOLDS

MEASURE_BEFORE_FILTERING
COMPARE_COMPLEX_RULES_TO_SIMPLE_BASELINES
RETAIN_FAILED_TRIALS
PRESERVE_POINT_IN_TIME_EVIDENCE
CONTROL_MULTIPLE_TESTING
DO_NOT_CONFUSE_SCANNER_RANK_WITH_SETUP_AUTHORITY
```

---

## 13. 最终状态

```text
EXTERNAL_RESEARCH_REVIEWED = YES
RESEARCH_VALUE = HIGH
THREE_SETUP_CURRENT_PARAMETER_CHANGE = NO
SCANNER_R3_CURRENT_PARAMETER_CHANGE = NO
FOURTH_SETUP_NOW = NO
CURRENT_RELEASE_EVIDENCE_OPTIMIZATION = YES
FIRST_FORMAL_RESEARCH_PACKET_EXPANSION = YES
FUTURE_STRATEGY_RESEARCH_REUSE = REQUIRED

BACKTEST_EXECUTED_BY_THIS_RECORD = NO
PERFORMANCE_IMPROVEMENT_PROVEN = NO
IMPLEMENTATION_AUTHORIZED = NO
DEPLOYMENT_AUTHORIZED = NO
EXCHANGE_WRITE_AUTHORITY = NO

NEXT_OWNER = STRATEGY_OPTIMIZATION_WINDOW
NEXT_ACTION = INCORPORATE_ADOPTION_MATRIX_INTO_RESEARCH_EXECUTION_PACKET
```
