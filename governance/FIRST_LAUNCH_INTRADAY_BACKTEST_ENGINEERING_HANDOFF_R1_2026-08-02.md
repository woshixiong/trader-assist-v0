# First Launch 日内策略第一轮回测工程交接 R1

**记录 ID：** `TA-FIRST-LAUNCH-INTRADAY-BACKTEST-ENGINEERING-HANDOFF-R1-2026-08-02`  
**日期：** `2026-08-02`  
**目标窗口：** 工程优化窗口  
**状态：** `ENGINEERING ROUTE REQUEST / IMPLEMENTATION NOT YET AUTHORIZED`  
**策略权威：** `FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R5_2026-08-02.md`  
**研究方法：** `STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V4_2026-08-02.md`  
**权限边界：** 当前要求工程优化窗口核验事实、设计路线并生成项目总控执行包；不得直接部署、访问账户、写入交易所、修改生产运行时或自行改变策略参数。

---

## 1. 任务背景

当前 First Launch 已运行，但下一次统一部署前需要先完成三 Setup 日内策略的系统回测和有限优化。策略研究已经完成回测前冻结，当前阶段不处理 Scanner、产品 UI、生产运维修复、reconnect-budget、部署或动态实时退出系统。

当前唯一主线：

```text
R5 STRATEGY FREEZE
→ ENGINEERING ROUTE
→ PROJECT CONTROL DISPATCH
→ CAUSAL REPLAY AND ROUND-1 BACKTEST
→ STRATEGY REVIEW
→ LIMITED REVISION IF JUSTIFIED
→ OUT-OF-SAMPLE VALIDATION
→ LATER COMBINED RELEASE WORK
```

工程优化窗口不拥有策略裁决权。任何参数变化必须由策略优化窗口基于回测证据批准。

---

## 2. 必须先核验的 GitHub 身份

仓库：

```text
woshixiong/trader-assist-v0
```

已知生产比较基线：

```text
ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
ETH-LDAR-v0.1
```

研究 Draft PR：

```text
PR #52
branch = agent/v0-strategy-predevelopment-analysis-r1
state = open / draft / unmerged / documentation-oriented
```

禁止直接假定 PR #52 文档分支适合作为代码实现基线。工程窗口必须核验：

- 当前 `main` HEAD；
- 当前生产基线与 `main` 关系；
- PR #52 最新 Head；
- 是否存在包含 Bronze replay / three-setup research foundation 的可复用分支或提交；
- 这些分支是否基于过期祖先；
- 是否需要从最新可信基线新建专用回测分支并仅移植必要研究能力。

推荐分支命名候选：

```text
feature/v0-intraday-strategy-backtest-r1
```

最终名称由工程窗口在核验后确定。

---

## 3. 必读权威文件

按以下优先级读取：

1. `governance/FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R5_2026-08-02.md`
2. `governance/STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V4_2026-08-02.md`
3. `governance/STRATEGY_RESEARCH_AND_BACKTEST_OPERATING_STANDARD_V1_2026-08-01.md`
4. `governance/FUTURE_V0_POSITION_MANAGEMENT_AND_EXIT_RESEARCH_PLAN_R2_2026-08-02.md`
5. 三 Setup R1/R1.1/R1.2 合同及其语义修正
6. 现有生产 `src/trader_assist_v0/first_launch/strategy.py`
7. 所有现有 research/replay/outcome/shadow-order/tests 文件和相关历史分支

冲突优先级：

```text
Pre-Backtest R5 > R4 > R3 > R2
Playbook V4 > V3 > V2 > V1
R1.2 > R1.1 > R1 for non-conflicting legacy semantics
```

---

## 4. 本阶段唯一允许范围

允许：

- 仓库和分支事实核验；
- 回测专用代码与测试路线设计；
- 公开市场数据只读获取计划；
- 因果回放；
- P0/P1/P2 研究候选；
- 影子退出 evaluator；
- Trial Registry；
- 机器可读与人类可读报告；
- 项目总控可执行任务包。

禁止：

- 修改生产策略或生产运行时；
- Scanner 开发或集成；
- Discord/UI/通知；
- reconnect-budget 或其他运维修复；
- 服务重启、permit、部署或 merge；
- 账户、私钥、签名、交易所写入；
- 实时动态退出；
- 自动或半自动下单；
- 工程窗口自行改变策略参数；
- 新建大型通用回测平台。

---

## 5. 固定交易和研究语义

```text
CONTEXT_TIMEFRAME = 1h
PRIMARY_STRUCTURE_TIMEFRAME = 15m
EXECUTION_TIMEFRAME = 5m
MICRO_TIMEFRAME = 1m/3m PATH_EVIDENCE_ONLY
TRADING_HORIZON = INTRADAY
HOLDING_TIME = PATH_DEPENDENT_NOT_FIXED
ENTRY_FIRST = YES
INITIAL_STRUCTURAL_STOP_REQUIRED = YES
MINIMUM_REFERENCE_OPPORTUNITY = APPROX_1R_AFTER_COSTS
HUMAN_FINAL_AUTHORITY = YES
REALTIME_DYNAMIC_EXIT_ENGINE = OUT_OF_SCOPE
```

多周期职责：

- 1h：已发生的上层背景，不是方向预测；
- 15m：价格带与交易机会；
- 5m：执行确认与入场；
- 1m/3m：路径还原、Stop/Target 顺序和附加证据。

---

## 6. 不可违反的因果原则

```text
OBSERVED_FACTS_ONLY = YES
CLOSED_AND_RECEIVED_DATA_ONLY = YES
LOOKAHEAD = PROHIBITED
FUTURE_PATH_ASSUMPTION = PROHIBITED
TIME_TO_COMPLETION_FORECAST = PROHIBITED
FIXED_TIME_AS_ECONOMIC_INVALIDATION = PROHIBITED
```

必须保证：

- 1h/15m/5m/1m 聚合只在对应周期闭合后可见；
- Pivot 只有右侧确认 K 线闭合并到达后才生效；
- PREPARE 状态可跨任意数量后续闭合 K 线推进；
- 机会确认或失效由价格、结构、Chase、Target Feasibility 和数据事实决定；
- 固定 bar count 只用于指标窗口、启动历史、工程归档或 comparator；
- 工程归档不得被报告为经济失效。

---

## 7. 1h 背景最终合同

第一轮不得用 1h 做硬过滤。

### 7.1 双标签

每个有效 Setup 候选同时记录：

```text
HTF_MOMENTUM_STATE
HTF_STRUCTURE_STATE
HTF_RELATION
```

动量主候选：

```text
A1H = Wilder ATR14
ER8_1H = 8h directional efficiency
D8_1H = 8h net displacement / A1H
```

结构主候选：

- 已因果确认的 1h Pivot；
- 最近两个 Swing High 与 Swing Low；
- UP / DOWN / RANGE / TRANSITION / INSUFFICIENT / UNAVAILABLE。

关系标签：

```text
ALIGNED_STRONG
ALIGNED_PARTIAL
COUNTERTREND_STRONG
COUNTERTREND_PARTIAL
CONFLICTED
NEUTRAL
CONTEXT_INCOMPLETE
```

### 7.2 所有有效信号进入回测

下列信号不得预先排除：

- 顺势；
- 逆势；
- 1h 中性；
- 1h 转换；
- 动量/结构冲突；
- 仅 1h 背景缺失而 5m/15m 有效。

### 7.3 数据状态区分

```text
HTF_DIRECTION_UNKNOWN:
normal market state; signal allowed

HTF_CONTEXT_UNAVAILABLE:
5m/15m valid, 1h context missing; signal allowed and labeled

MULTITIMEFRAME_DATA_INVALID:
core timeline or 5m/15m invalid; no actionable signal, evidence retained
```

第一轮不得自动降低背景缺失信号的仓位、风险或等级。

---

## 8. Setup 和候选优先级

### P0 Comparator

```text
V0_1_EXACT_BASELINE
FIXED_1_TO_6_BAR_STANDARD_COMPARATOR
SIMPLE_SWEEP_RECLAIM_BASELINE
SIMPLE_CLOSE_BREAKOUT_BASELINE
DONCHIAN_TURTLE_BREAKOUT_BASELINE
SIMPLE_RANGE_EDGE_REJECTION_BASELINE
```

### P1 Primary

```text
ZONE_MODEL_R5
HTF_DUAL_LABEL_R5
SWEEP_FACT_CONFIRMED_RECLAIM_R5
BREAKOUT_MICRO_CONFIRMED_FAST_R5
BREAKOUT_STATE_DRIVEN_STANDARD_R5
RANGE_EDGE_REJECTION_R5
TREND_SEGMENT_REENTRY_R5
```

### P2 Secondary / Sensitivity

```text
BREAKOUT_IMMEDIATE_DISPLACEMENT_FAST
SWEEP_SAME_BAR_FAST
PIN_BAR_QUALITY_FILTER
SHALLOW_VS_DEEP_RETEST
ZONE_LOOKBACK_64
30M_CONFIRMATION_SCALE
```

### P3 Deferred evidence

```text
VOLUME_PROFILE_HVN_LVN_POC
OI_FUNDING_CONTEXT
L2_DEPTH_ORDER_FLOW
REALTIME_DYNAMIC_EXIT
```

P3 只在取得成本很低时记录，不得阻塞第一轮。

---

## 9. 关键策略实现要求

### 9.1 Zone Model

必须实现 R5 中因果 15m Pivot、独立反应、聚类、Zone Center、Zone Width、ZQ1/ZQ2/ZQ3、96-bar 主候选和 64-bar sensitivity。

### 9.2 Sweep

P1 是状态驱动的事实确认型 Reclaim，不得限制为同一根或固定后两根 K 线。状态持续与失效按 R5 事实条件实现。Same-bar FAST 为 P2。

### 9.3 Micro-confirmed FAST

必须独立于 Immediate FAST。确认来自已经发生的带外接受、方向推进或因果高低点结构，不以未来预测为依据。

### 9.4 STANDARD

必须建立可跨后续 K 线推进的 PREPARE 状态机，支持深回踩和浅回踩。固定 1–6 bar 只作为 comparator。

### 9.5 Range

上下两侧满足 Range Setup 的信号全部生成。1h 只作标签，不作过滤。

### 9.6 趋势分段重新入场

必须支持同一大趋势中的多个独立 market event，同时防止同一事件重复信号。首次入场和 re-entry 必须独立统计。

---

## 10. 推荐的最小工程路线

工程窗口应优先验证以下路线，而不是立即引入外部大型框架：

1. 保持生产 `strategy.py` 为只读比较基线；研究候选放在独立 research 包中。
2. 核验是否已有 Bronze replay / three-setup research foundation；可用则在可信祖先上复用，不可用则只实现最小事件驱动 runner。
3. 使用单一因果时间轴，从 1m 原始数据聚合 5m/15m/1h；若 exact source 只提供部分周期，必须记录构造差异。
4. 每根闭合 5m 推进一次：更新 15m/1h、Zone、原始事件、状态机、候选、信号和 Outcome。
5. STANDARD/Sweep PREPARE 存于显式状态存储；事件被确认、失效或 supersede 后追加不可变终态记录。
6. 使用 append-only Trial Registry；参数、代码、数据 manifest、费用和延迟模型全部哈希。
7. 输出 JSONL/CSV 或现有 SQLite 能力；不建设新服务和 Dashboard。
8. 首先完成 deterministic fixtures，再运行较长数据。
9. 不新增大型依赖。任何依赖建议必须证明比仓库现有 Python 能力更低成本、更可审计。

建议工程目录原则：

```text
research/<dedicated_backtest_package>/
tests/research/
artifacts or reports excluded from production package
```

具体文件 allowlist 由工程窗口核验仓库后给出，不得凭提示词猜测现存路径。

---

## 11. 数据双轨计划

### Track A：Hyperliquid exact recent

用途：

- 验证生产 Candle 语义；
- 近期 ETH 适配；
- 费用、滑点和时间对齐；
- 与生产基线精确比较。

仅使用公开只读数据，不访问账户。

### Track B：一个长历史 ETH 永续代理市场

用途：

- 提供足够事件样本；
- 初步比较 Setup、HTF、波动率和退出路径；
- 支持开发/验证/保留区间。

第一轮只选择一个代理 venue，避免多 venue 工程扩张。不得静默混合 exact 与 proxy。

数据必须有 manifest：

```text
venue
symbol
interval/raw granularity
start/end
row count
missing intervals
duplicates
candle construction
timezone
fee model
slippage model
funding availability
source checksum
download timestamp
```

建议按时间顺序：

```text
DEVELOPMENT = 60%
VALIDATION = 20%
FINAL_HOLDOUT = 20%
```

Holdout 在参数冻结前不得用于调参。

---

## 12. 影子退出 evaluator

当前不开发实时退出系统，但必须尽量复用或补充最小 evaluator：

```text
initial structural stop
1R / 1.5R / 2R
next structural zone
30/60/120m MFE and MAE
time to 1R
maximum favorable excursion before stop
maximum profit giveback
profit-to-entry giveback
fixed-R outcomes
structure-target outcome
simple break-even / profit-lock outcome
simple structure-trailing outcome
no-progress label
reversal-exit label
hold-through-trend vs segmented-reentry shadow comparison
```

路径歧义：

1. 优先使用 1m；
2. 1m 同根仍同时触及 Stop/Target：`AMBIGUOUS_PATH`；
3. 主结果采用保守 `STOP_FIRST`；
4. 另行报告歧义样本。

人工主观退出和依赖完整实时 L2 的退出必须标记为不可完全历史复现。

---

## 13. 必须先完成的确定性测试

至少覆盖：

- 1h 动量 Up/Down/Neutral/Unavailable；
- 1h 结构 Up/Down/Range/Transition/Insufficient；
- Strong/Partial/Countertrend/Conflict/Incomplete 关系标签；
- 背景缺失但 5m/15m 有效仍生成信号；
- 核心多周期时间轴无效拒绝可执行信号；
- Zone 因果 Pivot 与聚类；
- Sweep confirmed reclaim 与重新接受带外失效；
- Micro FAST 与 Immediate FAST；
- STANDARD 深回踩；
- STANDARD 浅回踩；
- 超过 6 根 5m 后仍保持有效；
- accepted re-entry；
- opposite event；
- supersession；
- Chase failure；
- Target Feasibility failure；
- Range 双侧均生成；
- trend segment re-entry；
- same-event duplicate suppression；
- 1m Stop/Target 路径歧义；
- 1h/15m/5m/1m close boundary 对齐；
- runner 重复执行产生完全相同结果。

每个 Setup × Side × Mode 至少一个正向和一个拒绝 fixture。

---

## 14. 第一轮回测和报告维度

结果至少按以下维度分层：

```text
setup
× side
× confirmation_mode
× HTF_momentum_state
× HTF_structure_state
× HTF_relation
× volatility_state
× first_entry_or_reentry
× exact_or_proxy
```

每个单元至少报告：

```text
raw_candidate_count
independent_market_event_count
actionable_signal_count
filtered_or_invalid_count_by_reason
win_rate
average_gross_R
average_net_R
total_net_R
maximum_drawdown
longest_losing_streak
MFE / MAE
1R / 1.5R / 2R hit_rate
false_breakout_rate
missed_continuation_rate
confirmation_path_length
fixed_1_to_6_bar_missed_count
state_driven_added_count
30s / 60s delay_sensitivity
fee / slippage / funding assumptions
result_concentration
ambiguous_path_count
data_quality_exclusions
```

趋势分段重新入场另报：

- 每个趋势事件的独立段数；
- 首次入场与后续 re-entry；
- 错过首段后的恢复参与率；
- 分段成本；
- 一直持有与分段交易的影子对照。

---

## 15. HTF 后验政策比较

在同一批事件结果上比较：

```text
POLICY_ALL
POLICY_MOMENTUM_ALIGNED
POLICY_STRUCTURE_ALIGNED
POLICY_CONSENSUS_ALIGNED
POLICY_ALIGNED_OR_NEUTRAL
POLICY_SETUP_SPECIFIC
```

必须报告信号数、平均/总净 R、回撤、漏失盈利事件、样本量和结果集中度。不得只比较胜率。

---

## 16. 当前要求工程优化窗口先返回的内容

工程窗口当前先不要实施，先提交完整路线包：

### A. `LIVE_GITHUB_IDENTITY`

- main/production/PR #52 实时 SHA；
- 可复用研究分支和提交；
- 推荐实现基线；
- 推荐新分支；
- 祖先和冲突风险。

### B. `EXISTING_CAPABILITY_MAP`

- 生产策略比较入口；
- 可复用 Candle/aggregation/parser/replay；
- 可复用 Outcome/ShadowOrder/evidence；
- 可复用 tests/research；
- 当前缺口；
- 以前 STANDARD 生命周期缺陷在研究 runner 中如何纠正。

### C. `MINIMUM_IMPLEMENTATION_ROUTE`

- 分阶段路线；
- 为什么最短且安全；
- 哪些内容明确不做；
- 为什么不采用大型外部框架。

### D. `EXACT_FILE_ALLOWLIST`

- 预计新增/修改文件；
- 每个文件目的；
- 生产文件只读/禁止范围；
- 测试和报告路径。

### E. `DATA_PLAN`

- exact recent 和 long-history proxy；
- 缓存、manifest、checksum；
- 1m 聚合；
- 数据质量门禁；
- 成本和延迟模型。

### F. `TEST_PLAN`

- fixtures；
- no-lookahead；
- state lifecycle；
- data-quality；
- outcome ambiguity；
- reproducibility；
- performance bounds。

### G. `REPORT_SCHEMA`

- 机器可读结果；
- 人类总结；
- Trial Registry；
- config/data/code hashes；
- failure attribution。

### H. `WORK_BREAKDOWN`

- 由哪个本地 Writer/Codex CLI 执行；
- 每阶段工时估算；
- 可否一次连续完成；
- 必须停回策略窗口的位置。

### I. `ACCEPTANCE_GATES`

至少：

```text
LIVE_IDENTITY_VERIFIED
NO_PRODUCTION_MUTATION
DETERMINISTIC_FIXTURES_PASS
NO_LOOKAHEAD_PASS
LIFECYCLE_PASS
DATA_MANIFEST_PASS
P0_COMPLETE
P1_COMPLETE
SHADOW_OUTCOME_COMPLETE
REPRODUCIBLE_RERUN_PASS
REPORT_COMPLETE
```

### J. `FINAL_EXECUTION_PROMPT`

输出一份项目总控可直接派发给本地 Writer/Codex CLI 的完整执行提示词。工程窗口不得在该提示词中授权生产部署或自行调参。

---

## 17. 第一轮完成后的流程

```text
ENGINEERING FACTS AND REPORT
→ STRATEGY OPTIMIZATION REVIEW
→ FAILURE ATTRIBUTION
→ AT MOST 1–2 JUSTIFIED VARIABLE CHANGES PER UNIT
→ ROUND 2
→ PARAMETER FREEZE
→ FINAL HOLDOUT ROUND
```

正常预计三轮；只有实现错误、重大数据矛盾或一个决定性未解决变量时才允许第四轮。回测完成后再统一处理 Scanner、运维和部署。
