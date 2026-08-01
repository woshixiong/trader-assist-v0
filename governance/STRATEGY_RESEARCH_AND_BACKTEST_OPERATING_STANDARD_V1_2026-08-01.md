# Strategy Research and Backtest Operating Standard V1

**记录 ID：** `TA-STRATEGY-RESEARCH-BACKTEST-OPERATING-STANDARD-2026-08-01-V1`  
**日期：** `2026-08-01`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**目标分支：** `agent/v0-strategy-predevelopment-analysis-r1`  
**来源研究：**

- `FIRST_LAUNCH_THREE_SETUP_AND_SCANNER_EXTERNAL_PRICE_ACTION_RESEARCH_R1_2026-08-01.md`
- `FIRST_LAUNCH_THREE_SETUP_AND_SCANNER_EXTERNAL_RESEARCH_ADOPTION_DECISION_R1_2026-08-01.md`
- `FIRST_LAUNCH_SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE_R3_FINAL_PARAMETER_AND_DELIVERY_FREEZE_2026-08-01.md`

**状态：** `FUTURE OPERATING STANDARD / NON-EXECUTABLE / NON-AUTHORIZING`  
**生效边界：** 本标准在当前 First Launch 三 Setup + Scanner 发布完成后，作为后续策略研究、回测、参数优化和候选晋级的默认流程。当前发布仅吸收已明确列入最低证据合同的内容，不因本标准自动扩大实现范围。

---

## 1. 目的

当前研究流程存在以下问题：

- 研究问题临时产生；
- 数据、成本和延迟假设不统一；
- 参数尝试缺少完整登记；
- 简单策略与复杂策略缺少统一对照；
- 失败试验容易被遗忘；
- 回测、实盘候选和人工判断证据无法完整串联；
- 容易因单次结果继续增加参数或策略；
- 工程实现、产品验证和策略裁决边界不清楚。

本标准建立固定的高效率研究流程：

```text
RESEARCH INTAKE
→ HYPOTHESIS REGISTRATION
→ DATA AND EVIDENCE CONTRACT
→ SIMPLE COMPARATOR
→ CAUSAL IMPLEMENTATION CHECK
→ MINIMUM SCREEN
→ PRE-REGISTERED DIAGNOSTICS
→ COST / DELAY / ROBUSTNESS
→ LIVE SHADOW EVIDENCE
→ DECISION
→ VERSIONED PROMOTION OR REJECTION
```

目标不是建立昂贵的学术平台，而是以最少重复劳动，持续提高策略研究的可解释性、可复现性和决策质量。

---

## 2. 阶段边界

### 2.1 当前 First Launch 发布

当前发布目标保持：

```text
MINIMUM_USABLE_THREE_SETUP_AND_SCANNER
+ HUMAN_FINAL_DECISION
+ MANUAL_EXECUTION
+ SUFFICIENT_REAL_TEST_SAMPLES
```

当前发布不得因为本标准新增：

- 第四个 Setup；
- 完整研究平台；
- 新回测引擎；
- 完整 PBO / Deflated Sharpe 管线；
- 大规模参数网格；
- 机器学习；
- 自动交易；
- 自动资产切换；
- L2/order-flow 生产硬依赖。

### 2.2 First Launch 后

First Launch 上线并积累初始证据后，逐步启用本标准。每个研究任务仍需单独控制范围、时间和工程成本。

固定原则：

```text
RESEARCH_RIGOR_INCREASES_BY_STAGE
NOT_ALL_CAPABILITIES_AT_ONCE
```

---

## 3. 研究输入分级

外部研究、开源策略和社区实现统一分级：

```text
GRADE_A = 成熟同行评议或经典微观结构证据
GRADE_B = 高质量工作论文、官方数据或大样本研究
GRADE_C = 有限样本或探索性研究
GRADE_D = 开源代码、社区规则或交易员经验
```

使用规则：

```text
A/B = 支持经济机制、数据合同和研究问题
C = 形成待验证假设
D = 建立实现参考、fixture 或简单 comparator
```

禁止：

```text
PUBLIC_PARAMETER_COPY → PRODUCTION
PUBLIC_BACKTEST_RESULT → PRODUCTION_AUTHORITY
COMMUNITY_NARRATIVE → HARD_TRIGGER
```

每个研究记录必须保存：

- 来源；
- 证据等级；
- 可复用机制；
- 不可直接迁移部分；
- 许可证或使用状态；
- 未来复核日期。

---

## 4. 每个研究任务的强制 Research Card

任何参数、过滤器、Setup、Scanner 排名或执行规则研究，开始前必须登记：

```text
research_id
research_question
hypothesis
primary_metric
secondary_metrics
strategy_or_scanner_version
changed_variable
unchanged_variables
candidate_family
primary_or_sensitivity
expected_mechanism
failure_condition
data_cut
exact_or_proxy_source
cost_model
delay_model
maximum_trials
owner
```

没有 Research Card 的试验不得用于策略晋级。

---

## 5. Trial Registry

所有尝试，包括失败和无结论结果，都必须进入 Trial Registry：

```text
trial_id
research_id
run_time
code_commit
config_hash
data_snapshot_or_manifest
changed_variable
result_summary
primary_metric_result
robustness_result
selection_status
decision
rejection_reason
```

固定纪律：

```text
FAILED_TRIAL_DELETION = PROHIBITED
HIDDEN_PARAMETER_CHANGE = PROHIBITED
UNREGISTERED_RESULT_SELECTION = PROHIBITED
```

Trial Registry 应优先采用简单、可审计的 append-only Markdown/JSONL/SQLite 记录，不要求第一阶段建立复杂实验管理平台。

---

## 6. 数据与点时证据合同

### 6.1 数据来源必须分层

```text
EXACT_RECENT = Hyperliquid exact recent evidence
PROXY_LONG_HISTORY = Binance / Bybit / other proxy evidence
```

两者不得静默混合。

必须分别记录：

- venue；
- symbol mapping；
- candle construction；
- funding；
- fee；
- slippage；
- data gaps；
- available history；
- observed contradictions。

### 6.2 Point-in-Time Universe

任何 Scanner 历史研究必须使用可恢复的 point-in-time universe：

```text
universe_snapshot_id
universe_members
market_active_state
market_first_seen_or_age
history_sufficiency
eligibility_reason
exclusion_reason
liquidity_features
data_quality_features
asset_class
session
```

禁止用当前存活市场列表重建历史 universe。

### 6.3 因果和闭合 K 线

所有研究默认：

```text
CLOSED_CANDLE_ONLY = YES
LOOKAHEAD = PROHIBITED
DECISION_CUTOFF_RECORDED = YES
DATA_RECEIPT_TIME_RECORDED_WHERE_RELEVANT = YES
```

使用 swing、BOS/CHoCH、FVG 或其他左右窗口算法时，必须明确实时确认延迟；未修正 lookahead 的实现只能离线标注，不能参与实时策略资格。

---

## 7. 简单 Comparator 是强制项

任何复杂策略必须和一个或多个最简单、经济机制一致的规则比较。

当前固定 comparator 库：

```text
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
DONCHIAN_TURTLE_BREAKOUT_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

未来新增策略也必须定义自己的 simple comparator。

Comparator 必须和正式策略使用相同的：

- 数据截止；
- 成本；
- 延迟；
- funding；
- ambiguous path；
- time exit；
- 事件去重；
- 统计报告。

核心问题：

```text
DOES_COMPLEXITY_ADD_VALUE?
```

复杂规则若不能稳定优于简单 subset，应优先简化，而不是继续增加参数。

---

## 8. 分阶段回测流程

### Stage 0：Contract and Correctness

目标：证明实现符合策略合同。

最低检查：

- closed-candle；
- no-lookahead；
- deterministic fixture；
- Long/Short 对称性或显式非对称；
- event identity；
- duplicate suppression；
- stop/target/expiry 路径；
- missing data fail closed。

### Stage 1：Minimum Historical Screen

目标：快速排除明显错误或明显负面方案。

输出：

- signal count；
- net expectancy；
- median R；
- win rate；
- profit factor；
- rough drawdown；
- losing streak；
- MFE/MAE；
- fee/slippage/delay 后结果。

裁决：

```text
KEEP_FOR_RESEARCH
REVISE_ONCE
REJECT
INCONCLUSIVE
```

### Stage 2：Comparator and Attribution

目标：衡量复杂规则的增量价值。

包括：

- simple comparator；
- Level Attribution；
- event-path attribution；
- setup × side × mode；
- asset class；
- liquidity decile；
- session；
- volatility bucket；
- exact recent vs proxy。

### Stage 3：Pre-Registered Diagnostics

只运行 Research Card 中预注册的单变量或有限消融。

禁止看到结果后临时增加大量新分组，再选择最好结果。

### Stage 4：Robustness and Selection-Bias Controls

按项目成熟度逐步增加：

- cost stress；
- 30s / 60s delay；
- bootstrap confidence；
- trial count warning；
- Deflated Sharpe；
- PBO 或可实施近似；
- walk-forward 或时间样本外；
- venue contradiction report。

这些能力按价值逐步建设，不要求 First Launch 后第一轮全部上线。

### Stage 5：Live Shadow and Human Evidence

使用：

```text
Candidate / Signal
+ T/S/R
+ Planned Outcome
+ MFE/MAE
+ Actual Fill Match when available
```

比较：

- 系统判断；
- 人类判断；
- 理论路径；
- 实际执行；
- 成本和延迟差异。

### Stage 6：Promotion Decision

只能裁决：

```text
KEEP
REVISE
INCONCLUSIVE
REJECT
PROMOTE_TO_NEXT_EVIDENCE_STAGE
```

不得以单次高收益直接晋级生产。

---

## 9. 统一证据对象

后续研究应逐步统一以下字段，但不要求当前发布一次性全部实现。

### Identity

```text
event_id
raw_candidate_id
scanner_cycle_id
universe_snapshot_id
strategy_id
strategy_version
parameter_version
setup_family
side
confirmation_mode
symbol
dex
asset_class
```

### Time and Causality

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

### Level and Event Path

```text
level_price
level_source
level_age_bars
reaction_cluster_count
latest_reaction_age
excursion_ATR
outside_duration
reclaim_latency
breakout_extension_ATR
acceptance_closed_bars
time_to_retest
pre_retest_extension_ATR
retest_depth_ATR
range_age
range_rotation_count
midpoint_slope
```

### Market Context

```text
relative_volume
volume_percentile
ATR
volatility_bucket
spread_bps
estimated_slippage_bps
open_interest
OI_change
funding
premium
mark_oracle_divergence
```

### Execution and Outcome

```text
planned_entry
actual_entry
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
TP_hit
stop_hit
time_exit
realized_R
T/S/R
failure_taxonomy
```

---

## 10. Scanner 研究标准

Scanner 必须与正式 Setup 分离：

```text
SCANNER = DISCOVERY_AND_RANKING
SETUP = FORMAL_CAUSAL_ELIGIBILITY
```

Scanner 研究最低指标：

```text
watch_to_setup_ready_conversion
watch_recall_of_future_setup_ready
watch_precision
median_lead_time
p90_lead_time
missed_setup_ready
false_watch
alerts_per_hour
duplicate_watch_rate
top_1 / top_3 / top_5 quality
outcome_by_score_decile
```

所有 WATCH 和 SETUP_READY 都保存；Top-N 仅限制通知。

跨标的研究逐步增加：

```text
market_event_cluster_id
cross_asset_cluster_id
correlation_cluster
btc_beta_bucket
```

避免把同一市场冲击产生的多资产候选当作完全独立样本。

---

## 11. 参数治理

参数必须：

- 版本化；
- 可重建；
- 有默认值；
- 有变更原因；
- 有前后结果；
- 有回滚版本。

固定规则：

```text
ONE_PRIMARY_CHANGE_PER_TRIAL
BOUNDED_SENSITIVITY_ONLY
NO_LARGE_UNREGISTERED_GRID
NO_PARAMETER_CHANGE_FROM_ONE_OR_FEW_TRADES
```

首次实盘证据不足时，优先积累样本，不进行高频调参。

---

## 12. 工程、产品和策略职责

### Strategy Optimization

负责：

- Research Card；
- comparator；
- evidence fields；
- diagnostics；
- result interpretation；
- KEEP/REVISE/REJECT 裁决。

不负责直接修改生产代码或部署。

### Product Optimization

负责：

- 人工操作负担；
- WATCH/SETUP_READY/Signal 区别；
- T/S/R；
- 报告可读性；
- 研究结果如何支持用户决策。

不负责选择统计方法或技术文件范围。

### Engineering Optimization

负责：

- 数据和实现可行性；
- exact file scope；
- causal implementation；
- persistence；
- testing；
- performance；
- cost/time；
- failure isolation。

不负责根据回测结果擅自改变策略语义。

### Project Control

负责：

- scope freeze；
- capability-matched dispatch；
- gates；
- CI/review；
- deployment authorization；
- production boundary。

---

## 13. 效率原则

未来研究流程必须提高效率，而不是增加仪式性工作。

固定原则：

```text
REUSE_ONE_EVIDENCE_PIPELINE
REUSE_ONE_OUTCOME_EVALUATOR
REUSE_ONE_TRIAL_REGISTRY
REUSE_ONE_REPORT_SCHEMA
```

优先自动生成：

- identity；
- parameters；
- data manifest；
- costs；
- metrics；
- comparison tables；
- failure reasons。

人工只负责：

- 研究问题；
- 假设；
- 边界裁决；
- 少量盘面抽查；
- 结果解释。

禁止让用户反复手工搬运大段测试结果和逐单复盘字段。

---

## 14. 当前发布吸收矩阵

### 当前发布必须或优先低成本吸收

```text
recoverable point-in-time universe
all-candidate retention
candidate / setup authority separation
strategy/scanner/parameter version identity
minimum event-path evidence already available
T/S/R linkage
MFE/MAE / planned outcome linkage
low-cost no-signal proof
```

### 当前发布仅在近乎零成本时吸收

```text
additional Level Attribution tags
independent setup watch scores
extra OI/funding fields
range path expansion
```

### First Launch 后研究流程再建设

```text
four simple comparators
full Trial Registry workflow
expanded event paths
cross-asset clustering
formal Scanner recall/precision report
Deflated Sharpe / PBO
walk-forward framework
future Setup research
```

本矩阵优先于文档中将所有 P0 理解为当前发布阻断项的任何解释。

---

## 15. 最终状态

```text
FUTURE_RESEARCH_STANDARD_CREATED = YES
CURRENT_RELEASE_SCOPE_EXPANSION_AUTHORIZED = NO
CURRENT_PARAMETER_CHANGE_AUTHORIZED = NO
FOURTH_SETUP_AUTHORIZED = NO

EXTERNAL_RESEARCH_REUSE = REQUIRED
TRIAL_REGISTRY_FUTURE_DEFAULT = YES
SIMPLE_COMPARATOR_FUTURE_DEFAULT = YES
POINT_IN_TIME_UNIVERSE_FUTURE_DEFAULT = YES
EVENT_PATH_ATTRIBUTION_FUTURE_DEFAULT = YES
SELECTION_BIAS_CONTROL_BY_MATURITY = YES

CURRENT_FIRST_LAUNCH_GOAL = MINIMUM_EFFECTIVE_TESTING
RESOURCE_AND_TIME_CONTROL = REQUIRED
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```
