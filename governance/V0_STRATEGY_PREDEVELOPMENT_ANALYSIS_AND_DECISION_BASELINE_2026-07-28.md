# Trader Assist V0：策略体系评估、开源能力嫁接与 V0 开发前置决策基线

**记录 ID：** `TA-V0-STRATEGY-PREDEVELOPMENT-ANALYSIS-2026-07-28-R1`  
**日期：** 2026-07-28  
**仓库：** `woshixiong/trader-assist-v0`  
**编制基准：** live `main` at `b9a11d56ac869f1371ca5444fdb68fc3bb352c92`  
**状态：** `CONFIRMED STRATEGY PLANNING BASELINE / NON-EXECUTABLE / PRE-V0 INPUT`  
**适用阶段：** First Launch 上线后证据采集，至 V0 产品、策略和工程统一规划完成之前  
**目标读者：** Strategy Research、Product Function and Priority Control、Engineering Optimization、Project Control  
**权限边界：** 本文不授权修改生产策略、增加策略、账户读取、签名、交易所写入、自动下单、自动 SL/TP、V0 Package 激活或真实资金运行。

---

## 0. 文档定位

本文综合并修正以下两份研究输入：

1. `Trader_Assist_V0_Open_Source_Integration_and_Product_Planning(1).md`
2. 产品功能规划窗口提交的策略框架评估与 V0 建议

本文不是 V0 最终可执行方案，而是未来制定该方案前的**策略侧权威输入**。它负责：

- 固定已经能够确认的策略架构原则；
- 纠正两份输入中不准确、过早或容易引起范围膨胀的结论；
- 区分“已确认事实”“研究假设”“证据触发任务”和“延期能力”；
- 列出 V0 开发前必须解决的策略问题；
- 定义 First Launch 上线后应收集的证据；
- 为后续产品侧与策略侧统一规划提供结构化输入。

未来 V0 开发前，应将本文与产品功能规划团队的对应报告合并，形成：

```text
V0_PRODUCT_AND_STRATEGY_UNIFIED_PLANNING_PACKET
→ 用户最终裁决
→ Engineering Optimization 工程分解
→ Project Control 执行冻结
```

---

# 1. 执行摘要

## 1.1 总体结论

Trader Assist 当前策略方向总体合理，不应推翻重建。

最正确的长期定位是：

> **Trader Assist 保留交易观点、策略、风险、证据与权限权威，通过稳定版本化边界调用可替换的研究和执行工具。**

推荐长期结构：

```text
Trader Assist Strategy Authority
├─ 规范化、因果有效的数据产品
├─ 市场状态描述
├─ 策略经济机制与确定性规则
├─ Signal / TradePlan
├─ 风险与权限政策
├─ 人工确认
├─ 策略版本与晋级
└─ 结果归因和产品决策

Versioned Boundary Contracts
├─ ResearchDataset
├─ StrategyManifest
├─ OrderPreview
├─ ExecutionIntent
├─ ExecutionEvent
└─ ReconciliationSnapshot

Replaceable Sidecars / Services
├─ Freqtrade 或轻量研究工具
├─ Hyperliquid 官方 SDK
├─ Hummingbot
├─ NautilusTrader
└─ 标准监控、SQLite、systemd 和云工具
```

## 1.2 当前成熟度判断

当前 Trader Assist 已经具备较强的：

- 公共市场数据因果性；
- fail-closed 数据质量；
- 确定性信号状态；
- FAST / STANDARD 生命周期；
- volatility safety overlay；
- TradePlan；
- 入场、追价、止损、止盈和仓位风险；
- 人工执行边界；
- Signal → Decision → Outcome 的部分证据闭环。

但尚未形成成熟的：

- 策略经济机制合同；
- 策略研究数据合同；
- 生产—研究一致性机制；
- 简单基准与消融流程；
- 过拟合和参数稳定性流程；
- 全部信号的反事实评价；
- 市场事件独立性统计；
- 多维 regime 描述；
- 第二个独立策略的选择方法；
- 多策略冲突、风险分配和归因；
- 策略晋级、暂停和淘汰制度。

因此当前状态应定义为：

```text
STRATEGY_ENGINEERING_FOUNDATION = STRONG_FOR_FIRST_LAUNCH
ECONOMIC_HYPOTHESIS = PLAUSIBLE_BUT_INCOMPLETE
PRODUCTION_CORRECTNESS = SUBSTANTIALLY_ENGINEERED
LIVE_EDGE_EVIDENCE = INSUFFICIENT
MULTI_STRATEGY_READINESS = NOT_YET_ESTABLISHED
AUTOMATED_ROUTING_READINESS = NOT_ESTABLISHED
```

## 1.3 V0 前最重要的原则

V0 策略工作的起点不是马上开发第二个、第三个策略，也不是先建设通用策略平台。

正确起点是：

> **把 First Launch 现有策略变成一个可以被严格观察、严格比较、严格证伪、严格简化、严格限制或严格淘汰的研究对象。**

First Launch 真实证据随后决定：

- 当前策略有效且人工执行损失高：优先用户确认执行；
- 当前策略局部有效但 regime 覆盖不足：优先互补策略；
- 当前策略本身无明显优势：优先简化、修正、限制或淘汰；
- 两类缺口同时高：再评估两个隔离 Lane 并行；
- 系统数据或运行不可靠：先修系统，禁止用污染证据判断策略。

---

# 2. 当前项目策略事实基线

## 2.1 当前产品策略身份

当前生产代码使用统一策略版本：

```text
ETH-LDAR-v0.1
```

并包含至少两个 `SetupFamily`：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST
```

同时支持：

- LONG / SHORT；
- FAST / STANDARD；
- WAIT / WATCH / PREPARE；
- TRIGGERED_FAST / TRIGGERED_STANDARD；
- EXPIRED / INVALIDATED；
- LOW / NORMAL / HIGH / EXTREME volatility state。

在 V0 正式重新分类前，统一采用以下产品解释：

> **当前是一个 First Launch 产品策略核心，内部包含两个 setup family 和多个方向、速度及状态变体。**

这一定义避免两种错误：

1. 把每个 setup、方向或速度都夸大成独立策略；
2. 假设两个 setup family 永远只能被合并评价。

V0 研究必须分别报告两个 setup family 的表现；若证据表明其经济机制、适用市场、风险和生命周期显著不同，可以在后续版本中拆分为独立 `strategy_id`。

## 2.2 当前 volatility layer 的正确定位

当前 `LOW / NORMAL / HIGH / EXTREME` 来自短周期 ATR ratio。

它是：

```text
VolatilityState
+
One-way Safety Overlay
```

它可以：

- 确认；
- 降级；
- 否决；
- 收紧追价；
- 降低风险。

它不能：

- 单独创造交易；
- 完整描述趋势、区间、流动性、杠杆和事件状态；
- 直接成为未来自动策略路由器。

## 2.3 当前权限和执行边界

当前策略与 TradePlan 坚持：

```text
manual_execution_required = true
submission_status = NOT_SUBMITTED
```

策略、AI、研究和上下文模块不得获得交易凭证或调用交易所写端点。

未来执行能力必须通过单独批准的版本化边界进入，不允许外部框架直接获得策略或风险权威。

## 2.4 当前治理状态的解释

仓库中部分 JSON 治理快照仍记录较早阶段状态，例如 capture-only、未授权策略运行等。它们属于历史冻结或安全停止输入，不得压过后续已合并代码、最新治理文件和 live GitHub 对象。

未来调取本文时必须重新核验：

- live `main`；
- 已合并 PR；
- 当前产品裁决；
- 当前执行权限；
- 当前 First Launch 运行证据。

---

# 3. 对两份输入文档的纠错矩阵

## 3.1 可以确认并保留的结论

| 原结论 | 最终处理 | 修正后的权威表述 |
|---|---|---|
| 自有交易大脑 + 标准化意图接口 + 可替换工程侧车 | `ACCEPT` | 作为长期目标架构 |
| 不整体迁移到 Freqtrade/Hummingbot/Nautilus | `ACCEPT` | 外部工具不成为产品策略权威 |
| 使用 Anti-Corruption Layer | `ACCEPT` | 外部对象不得直接进入核心域 |
| Freqtrade 用于研究、基准和偏差检测 | `ACCEPT_WITH_REFINEMENT` | 原生 replay 为首要语义权威，Freqtrade 为交叉验证侧车 |
| Hummingbot 是执行/做市工具，不是盈利保证 | `ACCEPT` | 做市研究必须由产品证据触发 |
| NautilusTrader 值得借鉴 reconciliation | `ACCEPT` | 先参考和 Bake-off，不默认整体采用 |
| StrategyManifest、晋级和停用长期必要 | `ACCEPT_WITH_SCOPE_CONTROL` | 先最小 Manifest，第二策略获批后再扩展 |
| Gate A 与 Gate B 分离 | `ACCEPT` | 技术正确不等于策略盈利 |
| 经济机制、基准、消融、Shadow 必要 | `ACCEPT` | 固定为策略研发方法 |
| 自动下单和多策略优先级由 First Launch 决定 | `ACCEPT` | 不在本文提前选择 |

## 3.2 必须修正的结论

### 修正 1：不得把 ATR 状态称为完整 Regime Engine

错误风险：

```text
LOW / NORMAL / HIGH / EXTREME
=
完整市场状态
```

修正为：

```text
VolatilityState
≠
Complete Market Regime
```

未来市场状态至少拆为：

- `VolatilityState`
- `DirectionState`
- `RangeState`
- `LiquidityState`
- `LeverageState`
- `EventRiskState`
- `TradabilityState`

最后可派生 `RegimeDescriptor`，但原始正交状态必须保留。

### 修正 2：Regime 不能成为黑箱总策略

不采用：

```text
Regime Engine
→ 直接选择策略和风险
```

采用：

```text
RegimeClassifier
→ StrategyEligibilityPolicy
→ StrategyConflictResolver
→ RiskBudgetPolicy
```

四者权限不同：

- Classifier 描述状态；
- Eligibility 决定策略是否有资格；
- Conflict Resolver 处理并发候选；
- Risk Policy 只降低或限制风险，不创造信号。

### 修正 3：First Launch 后不默认立即启动三个同等级大研究

原建议同时启动：

- Freqtrade 研究实验室；
- 执行底座 Bake-off；
- Hummingbot 做市实验室。

修正为三类任务：

#### 必做基础

- First Launch 证据质量闭合；
- 原生 replay；
- ResearchDataset；
- 简单基准、消融和成本模型；
- 最小 StrategyManifest。

#### 条件触发

- `MANUAL_EXECUTION_GAP` 高：执行底座 Bake-off；
- `REGIME_COVERAGE_GAP` 高：互补策略研究；
- `RANGE_STABLE` 缺口显著且做市假设成立：Hummingbot 实验。

#### 延期

- 多执行引擎长期并存；
- 通用做市平台；
- 多 venue；
- 通用热插拔；
- 全自动策略路由。

### 修正 4：不能预先固定官方 SDK 为最终执行底座

`Official SDK + Thin Gateway` 是窄执行链的领先候选，不是已冻结结论。

必须通过统一故障矩阵比较：

- 官方 SDK；
- Hummingbot；
- NautilusTrader；
- 必要时其他维护良好的组件。

重点比较：

- 模糊提交结果；
- 幂等；
- 部分成交；
- 重启恢复；
- reconciliation；
- 凭证隔离；
- Hyperliquid 语义；
- 维护成本。

### 修正 5：Freqtrade 不应成为生产策略的第二份独立手写权威

完整重写“研究镜像”容易产生语义漂移。

优先级应为：

```text
共享纯策略核心或原生 deterministic replay
→ 生产语义权威

Freqtrade adapter
→ 数据转换、回测循环、基准、偏差检查和报告
```

若必须维护独立镜像，逐信号 parity report 为强制要求。

### 修正 6：不能只评价 TAKEN 交易

只评价人类实际执行的交易会产生选择偏差。

必须并行评价：

```text
ALL_ACTIONABLE_SIGNAL_SHADOW_OUTCOME
TAKEN_REAL_OUTCOME
SKIPPED_COUNTERFACTUAL_OUTCOME
EXPIRED_COUNTERFACTUAL_OUTCOME
HUMAN_SELECTION_VALUE
MANUAL_EXECUTION_GAP
```

否则无法判断：

- 策略是否有效；
- 人类过滤是否增加价值；
- 自动执行是否会误执行低质量信号。

### 修正 7：主观成功概率不是正式门槛

文件中的成功概率区间仅属于：

```text
PRIOR_HEURISTIC
```

不得作为：

- 资本授权；
- V0 排期；
- 策略晋级；
- 工程选择；
- 停止项目的自动规则。

### 修正 8：固定样本数不是机械晋级门槛

20、50、100、150 或 300 个信号只能作为研究规划参考。

必须同时考虑：

- 独立市场事件数；
- regime 覆盖；
- 时间跨度；
- 信号相关性；
- 成本和尾部风险；
- 数据质量；
- 策略频率。

### 修正 9：不能预先认定 V0 第一优先级是“验证策略”或“增加策略”

证据质量闭合和策略诊断是所有路径的前置条件，但产品优先级仍由 Gate B 决定。

正确表述：

```text
Evidence and diagnosis are mandatory prerequisites.
Next product priority remains user-decided after evidence.
```

### 修正 10：完整 StrategyManifest 和热插拔不应提前建设

V0 前期仅冻结最小声明：

```text
strategy_id
strategy_version
code_hash
parameter_set_id
parameter_hash
required_data
supported_states
prohibited_states
risk_ceiling
rollout_stage
evidence_version
enabled
```

以下内容只在第二个独立策略获得产品授权后扩展：

- conflict group；
- priority；
- position ownership；
- multi-strategy risk allocation；
- automatic routing；
- hot reload；
- strategy migration。

---

# 4. 当前策略框架合理性评估

## 4.1 经济和产品路线：合理

Trader Assist 采用：

```text
人类交易认知
→ 明确经济假设
→ 可观察结构
→ 确定性规则
→ 完整 TradePlan
→ 真实前向证据
```

该路线适合当前条件：

- 用户拥有交易经验；
- 系统需要可解释；
- 数据和资源有限；
- 不适合黑箱训练；
- 策略需快速否证和迭代；
- 风险权限必须逐级增加。

## 4.2 状态机：合理

当前 PREPARE、FAST、STANDARD、expiry、invalidation、do-not-chase 等机制明显优于单点指标信号。

它们降低：

- 重复触发；
- 事后解释；
- 信号无限悬空；
- 追价；
- 风险与信号分离；
- 重启后信号复活。

## 4.3 策略与风险分离：基本合理

策略先描述交易结构，TradePlan 再处理：

- 精度；
- planned entry；
- chase；
- stop；
- TP；
- quantity；
- notional；
- risk budget。

未来必须继续保持：

```text
Strategy may propose.
Risk may restrict.
Execution may implement.
No lower layer may expand authority.
```

## 4.4 数据和因果性：强项

当前策略已经高度重视：

- closed candle；
- source/receive cutoff；
- data continuity；
- complete source correspondence；
- no future evidence；
- deterministic hashes；
- fail closed。

这部分应保留，不能为了快速研究而使用不同时间语义的“方便数据”。

## 4.5 证据框架：有基础但不完整

当前已经有：

- Decision；
- Outcome；
- MFE / MAE；
- R multiple；
- deviation；
- pilot review。

不足在于：

- alert/signal latency；
- WAIT quality；
- 全部 actionable signal counterfactual；
- skipped outcome；
- 独立市场事件；
- 人工语义一致性；
- regime 归因；
- 生产—研究 parity。

---

# 5. 策略概念体系：V0 前必须统一

## 5.1 三层策略身份

统一定义：

```text
Strategy
└─ SetupFamily
   └─ SignalVariant
```

### Strategy

独立的经济机制、适用市场、风险和晋级单位。

### SetupFamily

同一经济机制下的不同可观察结构。

### SignalVariant

方向、速度、确认等级或执行展示变体，例如：

- LONG / SHORT；
- FAST / STANDARD。

这些不是自动独立策略。

## 5.2 当前暂定映射

```text
strategy_id:
ETH_LIQUIDITY_DIRECTIONAL_ASSIST

setup_families:
SWEEP_RECLAIM
BREAKOUT_RETEST

signal_variants:
LONG_FAST
LONG_STANDARD
SHORT_FAST
SHORT_STANDARD
```

该名称仅用于概念说明，最终 ID 在 V0 统一规划时确定。

## 5.3 策略与参数版本必须分开

未来每次实验和生产输出至少绑定：

```text
strategy_code_version
parameter_set_id
parameter_hash
risk_policy_version
data_contract_version
```

禁止：

- 看到结果后无记录地改参数；
- 参数变化仍沿用同一版本；
- 研究参数自动进入生产；
- 在线自动优化生产规则。

---

# 6. 策略经济机制合同

每个策略或候选 setup 必须先完成：

```text
StrategyHypothesisV1
```

字段：

```text
STRATEGY_ID
SETUP_FAMILY
EDGE_HYPOTHESIS
PAYER_OR_BEHAVIORAL_SOURCE
TARGET_MARKET_BEHAVIOR
SUPPORTED_STATES
PROHIBITED_STATES
REQUIRED_DATA
OPTIONAL_CONTEXT
ENTRY_ASSUMPTION
EXIT_ASSUMPTION
EXECUTION_ASSUMPTION
PRIMARY_FAILURE_MODES
CAPACITY_OR_LIQUIDITY_LIMIT
INVALIDATION_EVIDENCE
STOP_RULE
```

## 6.1 Sweep Reclaim 必须回答

- 流动性扫出后，为什么回收会形成后续运动？
- 谁承担损失或提供行为性优势？
- 哪类 sweep 只是噪声？
- FAST 和 STANDARD 是否共享相同 edge？
- OI、Funding 和 basis 是必需机制还是展示上下文？
- 趋势延续中的 sweep 和区间边缘 sweep 是否同一策略？
- 什么条件下该机制失效？

## 6.2 Breakout Retest 必须回答

- 突破接受的可观察定义是什么？
- retest 的时间和空间边界是什么？
- 假突破如何区分？
- 趋势强度与成交条件如何影响 edge？
- FAST 与 STANDARD 是否经济机制一致？
- LOW/HIGH volatility 下是否应使用相同几何？
- 是否只是简单 breakout beta 的复杂表达？

---

# 7. 人工语义还原与标注验证

必须建立最小人工案例库：

```text
POSITIVE_CANONICAL
NEGATIVE_CANONICAL
AMBIGUOUS
PREPARE
FAST
STANDARD
INVALIDATE
DO_NOT_CHASE
```

每个案例记录：

- 截止时点；
- 用户看到的图形；
- 人工分类；
- 系统分类；
- 关键边界；
- expected entry/stop/chase；
- 分歧类型。

指标：

```text
SEMANTIC_PRECISION
SEMANTIC_RECALL
TRIGGER_DELAY
GEOMETRY_DISAGREEMENT
STATE_TRANSITION_DISAGREEMENT
HUMAN_LABEL_STABILITY
```

目的不是让系统完全复制事后主观判断，而是区分：

```text
经济概念错误
规则表达错误
实现错误
人工判断不一致
```

---

# 8. ResearchDataset 与生产—研究一致性

## 8.1 ResearchDatasetV1

至少固定：

```text
dataset_id
dataset_hash
source
asset
time_range
event_time
receive_time
accepted_time
candle_identity
closed_candle_semantics
missing_data_policy
conflict_policy
precision
OI/Funding/basis semantics
fees
funding
slippage assumptions
excluded periods
strategy version
parameter set
```

## 8.2 原生 replay 是首要语义权威

优先顺序：

```text
Trader Assist native deterministic replay
→ production semantic reference

Freqtrade or other sidecar
→ independent research and comparison
```

## 8.3 Parity Report

逐信号比较：

- timestamp；
- cutoff；
- side；
- setup；
- state；
- regime descriptor；
- entry；
- chase；
- stop；
- TP；
- quantity；
- expiry；
- reason code。

每个差异必须分类：

```text
DATA_CONVERSION
TIME_SEMANTICS
WARMUP
FEATURE_CALCULATION
STRATEGY_LOGIC
LIFECYCLE
ROUNDING
FILL_MODEL
UNKNOWN
```

---

# 9. 基准、消融、稳健性和过拟合控制

## 9.1 最小基准

至少比较：

- buy-and-hold，作为市场方向参考而非等价策略；
- simple breakout；
- simple trend；
- simple mean reversion；
- same-frequency randomized entries；
- same-entry fixed stop/TP；
- current First Launch strategy。

## 9.2 最小消融

评估：

- 去掉 OI；
- 去掉 Funding；
- 去掉 basis；
- 去掉 volatility overlay；
- 去掉 longer-window support；
- FAST only；
- STANDARD only；
- 去掉 chase；
- 简化 entry geometry；
- 固定风险 vs regime-reduced risk。

每项回答：

- 是否提高净 expectancy；
- 是否降低 drawdown；
- 是否只降低交易频率；
- 是否改善 MFE/MAE；
- 是否只增加复杂度；
- 是否仅在某一状态有效。

## 9.3 稳健性

至少执行：

- lookahead 检查；
- recursive indicator 检查；
- walk-forward；
- 时间段 holdout；
- regime holdout；
- 参数邻域；
- session 分层；
- fee/slippage/funding 敏感性；
- 少量时间边界扰动；
- 数据缺口压力测试；
- 独立事件统计。

## 9.4 参数选择原则

接受稳定区域，不接受孤立最佳点。

不得以单次最佳回测作为晋级依据。

---

# 10. 全信号、人工选择与反事实评价

每个 actionable signal 都必须产生 shadow 结果，不论用户是否执行。

## 10.1 必须分开的结果

```text
ALL_SIGNAL_EXPECTANCY
TAKEN_SIGNAL_EXPECTANCY
SKIPPED_SIGNAL_EXPECTANCY
EXPIRED_SIGNAL_EXPECTANCY
HUMAN_SELECTION_VALUE
MANUAL_EXECUTION_GAP
```

## 10.2 Human Selection Value

用于判断人工判断是否增加价值：

```text
TAKEN outcome
vs
SKIPPED counterfactual outcome
```

若人工筛选显著提高收益，则自动执行不能直接覆盖全部信号。

## 10.3 Manual Execution Gap

记录：

- signal time；
- notification send/view time；
- decision time；
- order preparation/submission time；
- planned entry；
- realistic available entry；
- actual entry；
- missed flag；
- R loss due to delay；
- input error。

它决定执行链的产品价值，而不是开发时间单独决定。

---

# 11. 信号独立性与市场事件聚类

短周期信号不能直接把每条记录视为独立样本。

需要：

```text
market_event_id
setup_cluster_id
boundary_id
direction_cluster
independence_window
```

同时报告：

- raw signal count；
- unique setup count；
- independent market event count；
- independent trade opportunity count。

同一趋势或同一边界中的 FAST、STANDARD、retest 和重复确认可能属于同一事件。

样本充分性必须以独立事件和 regime 覆盖为核心，而不是仅看信号条数。

---

# 12. 成本、成交与可执行性模型

至少输出三类结果：

```text
IDEAL_PLAN_RESULT
REALISTIC_SHADOW_FILL_RESULT
MANUAL_ACTUAL_RESULT
```

纳入：

- maker/taker fee；
- spread；
- entry/exit slippage；
- funding；
- manual delay；
- expiry；
- chase；
- fill probability；
- partial fill；
- stop gap/slippage；
- execution reject。

对于快速 liquidity sweep，若理论结果好但 realistic fill 差，应分类为执行或产品问题，不能直接判定策略无效。

反之，若理想成交已无正期望，则不应通过自动执行挽救策略。

---

# 13. 多维市场状态与 RegimeDescriptor

## 13.1 正交状态

第一版建议：

```text
VolatilityState:
LOW / NORMAL / HIGH / EXTREME / UNKNOWN

DirectionState:
TREND_UP / TREND_DOWN / NON_DIRECTIONAL / TRANSITION / UNKNOWN

RangeState:
RANGE_STABLE / RANGE_BREAKING / BREAKOUT_ACCEPTED / FAILED_BREAKOUT / UNKNOWN

LiquidityState:
NORMAL / THIN / DISLOCATED / UNKNOWN

LeverageState:
OI_BUILD / OI_UNWIND / NEUTRAL / UNKNOWN

EventRiskState:
NORMAL / LIQUIDATION / NEWS_OR_EXTERNAL_RISK / UNKNOWN

TradabilityState:
TRADEABLE / REDUCED / NO_NEW_RISK / UNKNOWN
```

不是所有状态都要在 V0 第一版实现。只实现经策略假设证明必要的最小集合。

## 13.2 Shadow-first

RegimeDescriptor 第一阶段只：

- 记录；
- 展示；
- 归因；
- 与人工判断比较。

未经 Shadow 验证，不得：

- 自动改变生产信号；
- 自动选择策略；
- 自动增加风险；
- 自动切换策略。

## 13.3 Hysteresis

必须处理：

- 状态频繁跳转；
- 置信度；
- transition；
- UNKNOWN；
- 最小持续时间；
- 进入和退出阈值不同。

---

# 14. 第二个策略的选择方法

第二策略不能预先指定为做市、网格、趋势或 OI 策略。

选择流程：

```text
First Launch evidence
→ identify largest validated coverage gap
→ define economic mechanism
→ choose minimum new data
→ compare with simplest baseline
→ shadow candidate
```

第二策略必须：

- 覆盖不同市场状态；
- 具有独立经济机制；
- 与当前策略重叠可测；
- 交易成本后有合理可能；
- 数据扩展与产品价值成比例；
- 能独立暂停或淘汰。

候选示例只能作为研究池：

- range edge reversal；
- failed breakout；
- trend continuation；
- second-test failure；
- OI-price trap/unwind；
- passive range maker。

不能把研究池变成预授权开发路线。

---

# 15. 最小 StrategyManifest 与策略生命周期

## 15.1 Pre-V0 最小 Manifest

```text
strategy_id
strategy_version
code_hash
parameter_set_id
parameter_hash
required_data_products
supported_states
prohibited_states
warmup
risk_ceiling
rollout_stage
evidence_version
enabled
```

## 15.2 生命周期

```text
RESEARCH
REPLAY_VALIDATED
SHADOW_CANDIDATE
SHADOW
CANARY
ACTIVE
REDUCED_RISK
PAUSED
RETIRED
REJECTED
```

First Launch 后不会自动获得 CANARY 或 ACTIVE 权限。

## 15.3 晋级结果

```text
PROMOTE
REVISE
SIMPLIFY
RESTRICT_TO_STATE
KEEP_SHADOW
PAUSE_INSUFFICIENT_EVIDENCE
REJECT
RETIRE
```

## 15.4 停用不是删除

停用必须保留：

- 版本；
- 历史结果；
- decoder；
- replay；
- 未平仓归属；
- 决策原因。

---

# 16. 多策略冲突和风险：V0 开发前必须设计

只有第二策略获批后才实现，但规划前必须回答。

## 16.1 同方向

- 是否视为重复风险？
- 是否允许增加仓位？
- 哪个策略归因？
- 是否共享 stop？
- 总风险如何限制？

默认建议：

```text
同方向重复信号
→ 不自动叠加完整风险
```

## 16.2 反方向

默认建议：

```text
相反方向同时触发
→ CONFLICT
→ NO_NEW_RISK
```

是否减仓、反手或优先某策略，需要独立政策。

## 16.3 已有仓位

新策略不得未经明确规则：

- 接管；
- 加仓；
- 改 stop；
- 反手；
- 取消保护。

## 16.4 风险层级

至少规划：

```text
AccountRiskCap
PortfolioOpenRiskCap
InstrumentRiskCap
StrategyRiskCap
CorrelatedSignalCap
DailyLossCap
```

多个 ETH 做多策略不是多个独立风险。

---

# 17. 开源框架最终定位

## 17.1 Freqtrade

状态：

```text
USE_AS_RESEARCH_SIDECAR
```

适合：

- 基准；
- 快速回测；
- lookahead；
- recursive analysis；
- 参数敏感性；
- 报告；
- Dry-run 对照。

不适合：

- 生产策略唯一权威；
- 直接替换生命周期；
- 直接决定 TradePlan；
- 直接获得真实账户写入权限。

## 17.2 Hyperliquid 官方 SDK

状态：

```text
LEADING_EXECUTION_CANDIDATE
NOT_YET_SELECTED
```

适合窄执行链，但 SDK 不提供完整：

- reconciliation；
- unknown outcome；
- crash recovery；
- protection lifecycle。

## 17.3 Hummingbot

状态：

```text
CONDITIONAL_EXECUTION_OR_MARKET_MAKING_LAB
```

只有在以下情况启动较完整研究：

- range coverage gap 已证实；
- 做市经济假设明确；
- L2/trades 数据值得投入；
- adverse selection 和 inventory 能被测量；
- 产品明确选择该路线。

## 17.4 NautilusTrader

状态：

```text
EXECUTION_SAFETY_REFERENCE_AND_BAKEOFF_CANDIDATE
```

适合：

- reconciliation；
- in-flight；
- event-driven order lifecycle；
- multi-strategy/multi-venue 后期。

单 venue、单资产、人工确认初期可能过重。

## 17.5 CCXT/CCXT Pro

状态：

```text
LIMITED_RESEARCH_OR_MULTI_VENUE_USE
```

不默认替代官方 SDK，防止交易所特定语义丢失。

---

# 18. First Launch 上线后策略工作顺序

以下是依赖顺序，不是固定产品优先级。

## S0 — 证据可用性

确保记录：

- all actionable/non-actionable evaluations；
- strategy/setup/variant；
- state descriptor；
- user decision；
- latency；
- realistic fill；
- MFE/MAE；
- fees/funding/slippage；
- independent event；
- incidents。

## S1 — 策略合同

完成：

- Sweep Reclaim hypothesis；
- Breakout Retest hypothesis；
- supported/prohibited state；
- failure mode；
- data/execution assumptions。

## S2 — ResearchDataset 和原生 replay

完成：

- exact data semantics；
- exact strategy/parameter version；
- deterministic replay；
- full signal export；
- parity contract。

## S3 — 基准、消融、稳健性

回答：

- 是否优于简单策略；
- 哪些组件有增量价值；
- 哪些参数稳定；
- 哪些状态有效；
- 费用后是否成立。

## S4 — First Launch 诊断

输出：

```text
CURRENT_STRATEGY_VALIDITY
HUMAN_SELECTION_VALUE
MANUAL_EXECUTION_GAP
REGIME_COVERAGE_GAP
SYSTEM_RELIABILITY
```

## S5 — 用户产品决策

选择：

- execution-first；
- complementary-strategy-first；
- parallel bounded lanes；
- refine/simplify/retire；
- continue observation。

## S6 — 获批能力的最小工程化

只有用户裁决后才：

- 启动执行 Bake-off；
- 启动第二策略；
- 扩展 Manifest；
- 建立 conflict/risk；
- 增加数据产品；
- 进入 Testnet/Canary。

---

# 19. V0 开发前必须解决的策略问题

以下问题必须进入未来统一规划包。

## A. 策略身份和机制

1. 当前两个 SetupFamily 是否一个经济机制？
2. 是否需要拆为两个 strategy_id？
3. FAST 和 STANDARD 是否共享 edge？
4. LONG 与 SHORT 是否对称？
5. 每个 edge 的 payer 是谁？
6. edge 为什么可能持续？
7. 主要失效机制是什么？

## B. 数据和时间语义

8. 生产与研究是否使用相同 cutoff？
9. OI/Funding/basis 的时间语义是什么？
10. 历史数据质量和范围是否足够？
11. 断连、缺口和 backfill 如何进入研究？
12. 数据版本如何冻结？
13. 哪些新数据是第二策略必需，而非“可能有用”？

## C. 语义正确性

14. 人工视觉定义是否稳定？
15. 系统 precision/recall 如何？
16. entry/stop/chase 是否符合人工意图？
17. near-miss 应如何记录？
18. WAIT/WATCH 是否过度过滤？

## D. 科学验证

19. 是否存在 lookahead？
20. 是否存在 recursive bias？
21. 是否优于简单基准？
22. 哪些组件通过消融？
23. 参数是否稳定？
24. walk-forward 是否成立？
25. 是否集中于单一 regime 或单一事件？
26. signal count 与独立事件数分别是多少？

## E. 交易成本和执行

27. ideal、realistic 和 actual outcome 差异多大？
28. fee、funding、spread、slippage 后是否为正？
29. 人工延迟损失多大？
30. 人工选择是否增加价值？
31. 自动执行全部信号是否会降低结果？
32. 快速信号是否真实可成交？

## F. Regime

33. volatility state 是否有增量价值？
34. 哪些额外状态确实需要？
35. 状态是否稳定？
36. UNKNOWN 如何处理？
37. hysteresis 如何定义？
38. regime 只用于归因，还是有证据可用于 eligibility？

## G. 第二策略

39. 最大 coverage gap 是什么？
40. 第二策略经济机制是什么？
41. 与当前策略重叠多少？
42. 需要什么最小新数据？
43. 是否优于简单基准？
44. 是否应先 Shadow？
45. Hummingbot/做市是否真正匹配该缺口？

## H. 多策略

46. 同方向信号如何处理？
47. 反方向如何处理？
48. 已有仓位由谁拥有？
49. 风险如何聚合？
50. 绩效如何归因？
51. 策略如何暂停、回滚和退休？

## I. 外部工具

52. Freqtrade parity 是否可维持？
53. Official SDK 的 unknown/reconciliation 是否足够？
54. Hummingbot Connector 是否可靠？
55. Nautilus 的复杂度是否值得？
56. 许可证和供应链风险是什么？
57. 何时停止集成路线并换候选？

## J. 权限和产品价值

58. First Launch 的主要瓶颈是信号还是执行？
59. 用户确认提供多少额外价值？
60. 策略开发和执行开发是否可安全并行？
61. 哪个能力对预期收益和实际机会捕获贡献更大？
62. 需要什么证据才能增加账户或交易权限？

---

# 20. Pre-V0 Strategy Decision Packet

策略窗口在 V0 统一规划前应提交：

```text
V0_STRATEGY_DECISION_PACKET_V1
```

至少包括：

## 20.1 Current Strategy Evaluation

- 策略和 setup 身份；
- economic hypothesis；
- semantic validation；
- baseline；
- ablation；
- robustness；
- per-state performance；
- all-signal outcome；
- human selection；
- execution gap；
- coverage gap；
- conclusion。

## 20.2 Candidate Capability Matrix

| 候选 | 用户价值 | 真实证据 | 最小数据 | 研究成本 | 工程成本 | 权限变化 | 当前分类 | 停止规则 |
|---|---|---|---|---|---|---|---|---|
| 优化现有策略 |  |  |  |  |  |  |  |  |
| 第二互补策略 |  |  |  |  |  |  |  |  |
| Regime Shadow |  |  |  |  |  |  |  |  |
| 用户确认执行 |  |  |  |  |  |  |  |  |
| Freqtrade Sidecar |  |  |  |  |  |  |  |  |
| Execution Bake-off |  |  |  |  |  |  |  |  |
| Hummingbot Lab |  |  |  |  |  |  |  |  |

每项必须给出：

```text
HYPOTHESIS
EVIDENCE
MINIMUM_BUILD
REUSE_CANDIDATE
AUTHORITY_CHANGE
ACCEPTANCE
STOP_RULE
```

## 20.3 User Decision

最终必须由用户明确选择：

```text
EXECUTION_FIRST
STRATEGY_FIRST
BOUNDED_PARALLEL
REFINE_CURRENT
CONTINUE_OBSERVATION
RETIRE_OR_RETHINK
```

---

# 21. 停止规则

## 21.1 策略停止

若策略：

- 费用后明显为负；
- 不优于简单基准；
- 主要依赖事后人工修正；
- 参数极不稳定；
- 独立样本不足且无法获得；
- 理想成交都无价值；

则不得通过增加过滤条件无限挽救。

允许：

- 简化；
- 限制 regime；
- Shadow；
- 暂停；
- 淘汰。

## 21.2 外部框架停止

若两轮有边界的修复后仍：

- 无法保持语义；
- unknown/reconciliation 不可靠；
- 需要深度 Fork；
- 凭证边界不满足；
- 上游不维护；
- Adapter 复杂度接近重写；

则停止该路线，切换候选。

## 21.3 做市停止

若：

- adverse selection 吞噬 spread；
- inventory 是主要亏损；
- 只依赖奖励盈利；
- trend breakout 退出不可靠；
- 仅单一区间有效；

不得进入真实资金。

---

# 22. 已确认、待验证与延期分类

## 22.1 已确认并固定

```text
CONFIRMED
```

- Trader Assist 保留策略、风险和证据权威；
- 外部框架通过版本化边界接入；
- First Launch 先获得真实证据；
- 技术正确与策略盈利分离；
- volatility state 不等于完整 regime；
- RegimeClassifier、Eligibility、Conflict、Risk 分权；
- 原生 replay 为生产语义首要权威；
- 必须评价全部信号；
- 必须建立基准、消融、成本和稳健性；
- 第二策略由 coverage gap 选择；
- 自动执行与多策略优先级由真实证据决定；
- Hummingbot 做市研究为条件触发；
- Official SDK 是候选而非最终结论；
- 不提前建设完整通用热插拔和自动路由；
- 所有权限逐级单独授权。

## 22.2 First Launch 后待验证

```text
EVIDENCE_REQUIRED
```

- 当前策略是否费用后正期望；
- Sweep Reclaim 和 Breakout Retest 是否应拆分；
- FAST/Standard 的真实价值；
- OI/Funding/basis 是否有增量；
- volatility overlay 是否改善结果；
- 人工选择是否增加价值；
- manual execution gap；
- regime coverage gap；
- 第二策略类型；
- 执行底座选择；
- 做市可行性。

## 22.3 延期并保留

```text
DEFERRED / PRESERVED / UNSCHEDULED
```

- 第三个及更多策略；
- 自动策略路由；
- 在线学习；
- 自动参数变更；
- 通用热插拔平台；
- 多 venue；
- 完整 L2/OFI/CVD 平台；
- Hummingbot 实盘做市；
- Nautilus 整体迁移；
- 多执行引擎长期并存；
- 黑箱 AI 策略权威；
- 完整机构级策略审计系统。

---

# 23. 与产品功能规划团队的合并接口

未来统一规划必须把产品侧和策略侧按以下方式合并：

```text
Product side:
用户价值、交互、功能、权限、成本、上线顺序

Strategy side:
edge、regime、证据、研究、风险、策略生命周期

Engineering side:
复用、自研、边界、Package、测试、维护

Unified decision:
V0 scope、优先级、Gate、预算、停止规则
```

任何一项 V0 能力都必须同时回答：

```text
WHY_PRODUCT
WHY_STRATEGY
WHY_NOW
WHAT_EVIDENCE
WHAT_MINIMUM
WHAT_REUSE
WHAT_AUTHORITY
WHAT_RISK
WHAT_STOP_RULE
```

---

# 24. 最终裁决

## 24.1 对现有策略框架

```text
KEEP_AND_EVOLVE
```

不推翻；保留其因果、状态、TradePlan 和风险优势。

## 24.2 对策略研究流程

```text
FORMALIZE_BEFORE_EXPANSION
```

优先补齐：

- 经济机制；
- ResearchDataset；
- native replay；
- parity；
- all-signal counterfactual；
- independent events；
- baselines；
- ablation；
- cost；
- robustness；
- promotion lifecycle。

## 24.3 对多策略

```text
NOT_PREAUTHORIZED
EVIDENCE_DRIVEN
```

第二策略由最大已验证 coverage gap 决定；第三策略不是 V0 前置条件。

## 24.4 对自动执行

```text
NOT_PREAUTHORIZED
VALUE_DEPENDS_ON_MANUAL_EXECUTION_GAP
```

若信号有效且人工大量漏单，执行链可能成为最高价值能力。

## 24.5 对开源框架

```text
REUSE_CAPABILITIES
DO_NOT_SURRENDER_AUTHORITY
```

- Freqtrade：研究侧车；
- Official SDK：窄执行领先候选；
- Hummingbot：条件执行/做市实验；
- Nautilus：安全参考与 Bake-off；
- CCXT：有限用途。

## 24.6 对 V0 开发前的最终要求

V0 详细开发方案不得在以下内容缺失时直接冻结：

1. First Launch 证据质量确认；
2. 当前策略诊断；
3. 产品侧能力优先级；
4. 策略侧经济和 regime 判断；
5. execution vs strategy 价值比较；
6. 最小权限变化；
7. 外部复用选型；
8. 验收和停止规则；
9. 用户最终裁决。

---

# 25. 权限声明

本文不授权：

- 修改现有策略；
- 增加第二或第三策略；
- 启用 Regime 路由；
- 创建账户或 API Wallet；
- 读取私人账户；
- 签名；
- Testnet/Mainnet 下单；
- 自动撤单；
- 自动 SL/TP；
- 自动参数优化；
- 自动学习；
- V0 工程 Package；
- Mark Ready；
- merge；
- runtime activation。

任何执行必须在 V0 统一规划后重新由用户授权。

---

# 附录 A：输入材料的最终使用方式

## 输入 1：开源工程能力嫁接研究

保留：

- 核心架构；
- Anti-Corruption Layer；
- 工具角色；
- 健康度分层；
- 故障测试清单；
- 停止规则。

修正：

- 主观概率不作门槛；
- 三研究不默认并行；
- Official SDK 不提前定案；
- Hummingbot 做市改为证据触发；
- Freqtrade 镜像改为原生 replay + parity 优先。

## 输入 2：产品规划窗口策略建议

保留：

- 人类认知量化；
- Gate A/Gate B；
- Regime 分权；
- 经济机制；
- 人工语义验证；
- 基准、消融、成本；
- 信号独立性；
- Shadow-first；
- 策略暂停和淘汰。

修正：

- “验证当前策略”是前置诊断，不自动成为唯一 V0 产品优先级；
- 最小 StrategyManifest 先行，完整热插拔延期；
- Regime Shadow 不在证据不足时扩张为生产路由；
- 样本数仅为 guidance。

---

# 附录 B：未来调取说明

用户准备启动 V0 统一规划时，策略窗口应首先读取：

1. 本文；
2. First Launch 最新运行数据；
3. live GitHub main 和当前治理索引；
4. 产品功能规划团队的预 V0 报告；
5. 最新产品裁决；
6. 最新工程约束和执行权限。

随后生成：

```text
V0_STRATEGY_DECISION_PACKET_V1
```

再与产品侧报告合并，不得直接把本文当作工程 Task Contract。
