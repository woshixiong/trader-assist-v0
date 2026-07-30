# First Launch 震荡 Setup 工程优化实施交接

**记录 ID：** `TA-FIRST-LAUNCH-RANGE-STRATEGY-ENGINEERING-HANDOFF-2026-07-30-R1`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**分支：** `agent/v0-strategy-predevelopment-analysis-r1`  
**关联 Draft PR：** `#52`  
**状态：** `ENGINEERING OPTIMIZATION INPUT / NON-EXECUTABLE / PRE-IMPLEMENTATION`  
**权限边界：** 本文不直接授权生产代码修改、部署、激活、账户访问、签名、交易所写入、自动下单或真实资金风险。工程优化窗口应先完成方案拆解、投入产出比评估、回测设计、实现范围和 Gate，再由 Project Control 安排具体执行。

---

## 1. 已固定的 GitHub 策略文件

工程优化窗口必须先阅读并核验以下文件：

1. `governance/V0_STRATEGY_PREDEVELOPMENT_ANALYSIS_AND_DECISION_BASELINE_2026-07-28.md`
2. `governance/FIRST_LAUNCH_RANGE_STRATEGY_AND_COMBINED_BACKTEST_DECISION_2026-07-30.md`
3. `governance/FIRST_LAUNCH_RANGE_STRATEGY_ENGINEERING_OPTIMIZATION_HANDOFF_2026-07-30.md`

其中：

- 第一份文件固定 V0 前策略架构、研究、回放、数据、Regime、第二策略和生命周期原则；
- 第二份文件固定 `RANGE_EDGE_REJECTION` 的结构身份、互斥触发、数据边界和联合回测要求；
- 本文件固定工程优化窗口的实施任务、停止条件和交付格式。

所有文件目前属于 Draft PR #52 的文档性治理输入，不得将其误解为已经获得生产部署权限。

---

## 2. 核心概念：为什么未来仍可能需要独立第二策略

`RANGE_EDGE_REJECTION` 当前推荐作为 `ETH-LDAR` 内部第三个 `SetupFamily`，是为了最小投入、最快复用现有运行链。该选择不代表独立第二策略永远没有价值。

独立第二策略的价值来自结构能力，而不是“多一条触发规则”。它在以下情况下是合理且必要的：

1. **独立经济机制**  
   两套策略依赖不同的市场行为、不同的失败机制和不同的持有逻辑，不应被压缩成同一 evaluator 中的优先级分支。

2. **独立启停与晋级**  
   一个策略可以 ACTIVE，另一个可以 SHADOW、PAUSED 或 RETIRED，不需要整体重新部署同一个策略核心。

3. **独立风险预算**  
   可以设置独立的 `StrategyRiskCap`、最大开放风险、日损失限制和回撤停止规则。

4. **独立并发候选**  
   两个策略可以同时产生同向或反向候选，系统可显式比较、压制或组合，而不是由代码排列顺序静默吞掉候选。

5. **持仓归属与结果归因**  
   可以明确哪一个策略拥有仓位、止损和退出逻辑，并分别评价真实收益、成本、滑点和人工执行价值。

6. **不同数据和执行需求**  
   例如一个策略只用 OHLCV，另一个依赖 L2、trades、Volume Profile 或不同的执行算法，此时继续塞入同一核心会造成强耦合。

7. **故障与演进隔离**  
   一个策略的错误、暂停或版本升级不必影响另一个策略。

因此，独立第二策略不是当前最低成本方案，但它是未来多策略组合、独立风险和并发决策能力的必要结构。

---

## 3. 当前实验 Setup 是否可以长期沿用

可以长期沿用，但必须区分“结构身份”和“成熟度状态”。

```text
结构身份可以长期保持：
RANGE_EDGE_REJECTION = ETH-LDAR 内部 SetupFamily

成熟度状态不能无限期保持：
EXPERIMENTAL = 临时研究/上线阶段
```

经过联合回测、Live Shadow、人工 Canary 和证据裁决后，应选择：

- `PROMOTE_TO_ACTIVE_SETUP`
- `REVISE`
- `RESTRICT_TO_STATE`
- `KEEP_SHADOW_WITH_REASON_AND_REVIEW_DATE`
- `SPLIT_TO_INDEPENDENT_STRATEGY`
- `REJECT / RETIRE`

不得无限期保留一个没有明确审查日期和晋级标准的“实验性”生产 Setup。

### 3.1 同一策略核心长期沿用的优点

- 复用现有数据、Signal、TradePlan、风险、ShadowOrder、通知和人工流程；
- 开发、测试、部署和运维成本低；
- 同一评估周期只输出一个最终候选；
- 对当前单资产、人工执行 First Launch 足够简单；
- 生产—研究语义更容易保持一致。

### 3.2 同一策略核心长期沿用的弊端

1. **独立启停困难**  
   若没有最小 feature gate，关闭一个 Setup 需要发布新的策略版本。

2. **候选压制不可避免**  
   单 evaluator、单返回值会导致优先级靠后的候选被压制。

3. **跨 K 线状态可能干扰**  
   一个 Setup 的 `PREPARE`、FAST 或有效期，可能与另一个 Setup 的新候选重叠。

4. **共享风险和版本**  
   无法自然表达每个 Setup 的独立风险预算、停止规则和 rollout stage。

5. **测试矩阵持续膨胀**  
   每增加一个 Setup，方向、速度、状态、Overlay、冲突和历史兼容测试会显著扩大。

6. **归因变复杂**  
   一个统一 `strategy_version` 中包含越来越多机制，容易降低可解释性。

7. **故障域共享**  
   一个 Setup 的生产错误可能使整个策略核心需要回滚或停用。

### 3.3 必须拆成独立策略的触发条件

出现以下任一条件，应停止继续作为普通 Setup 堆叠，并评估独立策略：

- 需要同一时刻保留多个候选；
- 需要独立启停且不能依赖重新部署；
- 需要独立风险预算或独立回撤停止；
- 需要独立持仓、止损、加仓或退出逻辑；
- 可能长期与原策略产生反方向信号；
- 使用不同的数据产品或执行方式；
- 经济机制、适用 regime 和持仓周期明显不同；
- 需要单独暂停、淘汰或版本迁移。

---

## 4. 当前实施裁决

本轮固定：

```text
IMPLEMENT_ONE_NEW_EXPERIMENTAL_SETUP = YES
SETUP_FAMILY = RANGE_EDGE_REJECTION
STRUCTURE = INSIDE_ETH_LDAR
INDEPENDENT_SECOND_STRATEGY = NO
ADDITIONAL_NEW_SETUP_IN_SAME_ITERATION = NO
FIRST_LAUNCH_PRODUCTION_IMPACT_DURING_RESEARCH = NONE
```

目标不是为了制造更多通知，而是：

- 覆盖已观察到的震荡/区间 regime 缺口；
- 产生足够研究事件，验证工程底座和人工执行流程；
- 在同一数据和成本模型下验证三个 Setup 的互斥、压制和组合效果；
- 为 V0 决定 execution-first、complementary-strategy-first 或 refine/retire 提供证据。

---

## 5. 三个 Setup 的互斥和影响是本轮最高优先级

工程优化方案不得只验证每个 Setup 单独能够触发，还必须证明组合运行时不会静默干扰。

### 5.1 同一根 K 线定义域互斥

#### `BREAKOUT_RETEST`

- 收盘在近期边界外至少 `0.10 ATR`；
- 有实体、成交量和 15m 方向支持。

#### `SWEEP_RECLAIM`

- 极值穿越边界至少 `0.10 ATR`；
- 收盘重新回到区间。

#### `RANGE_EDGE_REJECTION`

- 触及或浅度穿越区间边界；
- 外侧穿越必须严格 `< 0.10 ATR`；
- 收盘重新位于区间内；
- 15m 不存在明确 long/short bias；
- 第一版只在明确允许的 volatility state 中运行。

边界值必须唯一归属：

```text
outside_excursion >= 0.10 ATR
→ RANGE_EDGE_REJECTION not eligible

outside_excursion == 0.10 ATR
→ belongs to SWEEP_RECLAIM domain
```

### 5.2 防御优先级

```text
1. SWEEP_RECLAIM
2. BREAKOUT_RETEST
3. RANGE_EDGE_REJECTION
4. WATCH / WAIT
```

优先级不能替代数学互斥，只能作为最后防御线。

### 5.3 跨 K 线 active-signal gate

必须研究并明确：

```text
EXISTING_PREPARE_OR_TRIGGERED_ACTIVE
→ whether a new candidate from another Setup is suppressed

OPPOSITE_SIGNAL_DURING_ACTIVE_EXPIRY
→ default policy = NO_NEW_SIGNAL unless explicitly authorized
```

必须分别统计：

- same-candle overlap；
- cross-candle overlap；
- suppressed-by-priority；
- suppressed-by-active-signal；
- opposite candidate within active expiry；
- duplicate market-event clusters。

若当前 lifecycle 不能在小范围内实现安全 gate：

- 新 Setup 只能 `SHADOW_ONLY`；或
- 工程优化窗口必须提出最小 active-signal eligibility guard；
- 不得为了赶进度声称“无干扰”。

---

## 6. 联合回测要求

本轮不能只回测新 Setup，也不能只回测组合总收益。必须使用同一原生 replay、同一数据集、同一成本模型，一次运行：

```text
A. BASELINE_ONLY
   SWEEP_RECLAIM + BREAKOUT_RETEST

B. EXPERIMENT_ONLY
   RANGE_EDGE_REJECTION only

C. COMBINED_EXACT_POLICY
   三个 Setup + 精确互斥 + 优先级 + active-signal gate
```

建议额外加入只作研究基准、不得直接生产化的：

```text
D. SIMPLE_MEAN_REVERSION_BASELINE
   简单 Bollinger/RSI 或等价低参数基准
```

OU 模型只有在获得足够、适合检验统计平稳性的长期数据后再做研究，不作为本轮阻塞项，也不得默认把 ETH 绝对价格建模为稳定 OU。

### 6.1 统一报告

必须输出：

- signal count；
- unique setup count；
- independent market event count；
- LONG/SHORT；
- FAST/STANDARD；
- volatility/regime 分层；
- gross expectancy in R；
- net expectancy in R；
- fees、slippage、funding、manual delay；
- win rate；
- average win / average loss；
- max drawdown；
- longest loss streak；
- overlap matrix；
- suppressed-by-priority；
- suppressed-by-active-signal；
- opposite signal within expiry；
- combined incremental expectancy；
- combined frequency change；
- combined drawdown change；
- result concentration in top trades。

第一轮禁止自动参数优化。只允许少量、预先冻结、具有经济解释的候选参数。

### 6.2 回测 Gate

输出：

```text
REPLAY_CORRECTNESS = PASS / FAIL
EXPERIMENT_EVIDENCE = POSITIVE / NEGATIVE / INCONCLUSIVE
INTERACTION_SAFETY = PASS / FAIL / SHADOW_ONLY
IMPLEMENTATION_DISPOSITION = GO / REVISE / REJECT
```

`GO` 不等于直接生产部署。它只允许进入最小生产候选实现。

---

## 7. 数据范围

第一版只使用现有数据能力：

- ETH 5m OHLCV；
- ETH 15m OHLCV；
- ATR；
- 近期结构边界；
- 成交量中位数；
- 15m 方向；
- mark/mid reference；
- 当前已有的 OI/funding 上下文可作为研究分层，但不得未经证据直接变成硬门槛。

本轮禁止引入：

- L2 Order Book；
- BBO/order-book imbalance；
- trades/order-flow imbalance；
- Volume Profile / VAH / VAL / POC；
- liquidation feed；
- 新第三方运行时；
- Hummingbot/Nautilus 生产接入；
- 自动下单。

这些能力记录为后续证据触发项，不是彻底放弃。

---

## 8. 工程范围原则

工程优化窗口应优先设计：

```text
OFFLINE_RESEARCH_FIRST
NO_PRODUCTION_MUTATION_DURING_BACKTEST
ONE_REPLAY_RUNNER
ONE_DATASET
ONE_COST_MODEL
THREE_REQUIRED_MODES
NO_NEW_RUNTIME_SERVICE
NO_NEW_DEPENDENCY_UNLESS_STRICTLY_NECESSARY
NO_DATABASE_SCHEMA_CHANGE_UNLESS_PROVEN_REQUIRED
```

若回测为 `GO`，生产候选仍应尽量：

- 复用当前 StrategySnapshot；
- 复用当前 `Signal / PreparedSetup / StrategyOutput`；
- 复用当前 volatility Overlay；
- 复用 TradePlan、ShadowOrder、通知和 Outcome；
- 更新策略版本；
- 明确实验标签；
- 补齐旧版本兼容；
- 不改变账户和交易权限。

工程优化窗口必须评估是否可以加入一个**最小、明确、默认关闭或可快速关闭的 Setup eligibility gate**，但不得借此扩展为通用插件平台。

---

## 9. 建议阶段

### Phase 0 — 身份和事实核验

- 核验 live `main`、生产 exact SHA、当前策略 blob 和当前运行状态；
- 核验 PR #52 三份治理文件；
- 核验生产 First Launch 持续运行且研究工作完全隔离。

### Phase 1 — 研究合同冻结

- 固定 Range 经济机制；
- 固定 eligibility、触发、确认、失效和退出假设；
- 固定同 K 线互斥和跨 K 线 gate；
- 固定 A/B/C 回测模式；
- 固定成本和结果判定。

### Phase 2 — 离线原生联合回放

- 建立最小 replay；
- 运行 A/B/C；
- 输出信号、收益、回撤、重叠和压制报告；
- 输出 `GO / REVISE / REJECT`。

### Phase 3 — 最小生产候选

仅在 `GO` 后：

- 增加第三 SetupFamily；
- 加入互斥条件；
- 加入最小 active-signal gate；
- 明确实验标签和版本；
- 补齐单独触发、组合触发、生命周期和 TradePlan 测试。

### Phase 4 — 独立审查和 CI

- focused tests；
- affected tests；
- full tests；
- lint/type/compile；
- diff/scope/secret；
- independent patch review；
- exact-head CI。

### Phase 5 — Shadow / Canary 裁决

- 默认先 Shadow；
- 只有证据和用户单独授权后，才允许人工 Canary；
- 记录所有信号，不只记录 TAKEN；
- 设置明确的 review date 和晋级/暂停条件。

---

## 10. 停止条件

立即停止并返回重新规划，如果出现：

- 必须建设独立多策略框架才能安全运行；
- 必须修改 First Launch 数据传输或生产架构；
- 必须增加 L2/Volume Profile 才能定义第一版；
- 三个 Setup 无法建立清晰互斥；
- combined replay 出现大量静默压制或反向冲突；
- 费用后明显负期望；
- 结果依赖少数异常交易；
- 需要反复调参才能得到正结果；
- 需要大规模数据库或通知重构；
- 预计工作量明显超过最小投入目标。

---

## 11. 工程优化窗口最终交付

请输出一个统一实施包，至少包含：

1. `REVIEW_STATUS`
2. 当前 live identity 和治理输入核验
3. 推荐结构：SetupFamily 或独立策略，并说明依据
4. 精确触发规则与互斥表
5. 跨 K 线 active-signal policy
6. 联合回测设计
7. 数据来源、时间语义和成本模型
8. 预计文件范围和依赖
9. 开发时间、审查时间、部署时间
10. GO/REVISE/REJECT Gate
11. 风险、停止条件和回滚方案
12. 给 Project Control 的执行提示词
13. 给 Codex CLI Writer 的一次性任务提示词
14. 给独立 Reviewer 的只读验收提示词

工程优化窗口不得直接将规划文档视为生产修改授权。

---

# 附录 A：一键复制给工程优化窗口的提示词

```text
ROLE:
ENGINEERING_OPTIMIZATION_LEAD_FOR_FIRST_LAUNCH_RANGE_STRATEGY_AND_COMBINED_BACKTEST

MODE:
STRICT_READ_ONLY_DISCOVERY_THEN_BOUNDED_IMPLEMENTATION_PLANNING

PROJECT:
TRADER_ASSIST_V0_FIRST_LAUNCH_POST_LAUNCH_STRATEGY_EXTENSION

REPOSITORY:
woshixiong/trader-assist-v0

CURRENT_PRODUCT_STATE:
- First Launch 已正式上线并持续运行。
- 当前为 ETH-only、公共数据、人工最终决策、人工下单。
- 系统不持有账户交易权限，不自动提交订单。
- 当前策略核心为 ETH-LDAR-v0.1，包含 SWEEP_RECLAIM 与 BREAKOUT_RETEST。
- 当前目标是在不改变 First Launch 总体工程架构、不影响现有生产运行的前提下，以最小投入研究并可能增加适合震荡/区间行情的 RANGE_EDGE_REJECTION。

MANDATORY_GITHUB_INPUTS:
请先在 GitHub Draft PR #52、分支 agent/v0-strategy-predevelopment-analysis-r1 中阅读并核验：
1. governance/V0_STRATEGY_PREDEVELOPMENT_ANALYSIS_AND_DECISION_BASELINE_2026-07-28.md
2. governance/FIRST_LAUNCH_RANGE_STRATEGY_AND_COMBINED_BACKTEST_DECISION_2026-07-30.md
3. governance/FIRST_LAUNCH_RANGE_STRATEGY_ENGINEERING_OPTIMIZATION_HANDOFF_2026-07-30.md

这些文件是本任务的策略和治理输入，但不是生产部署授权。你必须同时重新核验 live main、生产 exact SHA、当前策略代码、运行时接口和测试事实。若 GitHub 文档与 live code 冲突，以最新、已经合并且实际部署的事实为准，并明确记录差异。

KEY_CONCEPT_DECISION:
“实验性”和“独立第二策略”是两个不同维度：
- EXPERIMENTAL 描述成熟度和 rollout 权限；
- INDEPENDENT_STRATEGY 描述独立 strategy_id、启停、风险、并发候选、持仓归属、绩效和生命周期。

本轮默认方案：
STRUCTURE = THIRD_SETUP_FAMILY_INSIDE_ETH_LDAR
SETUP_FAMILY = RANGE_EDGE_REJECTION
ROLLOUT_STAGE = EXPERIMENTAL
INDEPENDENT_SECOND_STRATEGY = NO
ONE_NEW_EXPERIMENTAL_SETUP_PER_ITERATION = YES

这不是永久禁止独立第二策略。若需要独立风险、独立启停、并发候选、持仓归属、不同数据/执行、不同生命周期，必须重新评估拆分为独立策略。

PRIMARY_OBJECTIVE:
设计并安排一次最小、离线、原生联合回测，并在证据允许时提出最小生产候选实现方案。不得一开始就修改生产或部署。

REQUIRED_REPLAY_MODES:
A. BASELINE_ONLY
   SWEEP_RECLAIM + BREAKOUT_RETEST

B. EXPERIMENT_ONLY
   RANGE_EDGE_REJECTION only

C. COMBINED_EXACT_POLICY
   三个 Setup + 精确互斥 + 明确优先级 + active-signal gate

OPTIONAL_RESEARCH_BASELINE:
D. SIMPLE_MEAN_REVERSION_BASELINE
   低参数 Bollinger/RSI 或等价简单基准，仅用于比较，不得自动成为生产策略。

MUTUAL_EXCLUSIVITY_REQUIREMENTS:
必须优先证明三个 Setup 能够单独触发，并且组合时不会静默重叠或互相干扰。

1. BREAKOUT_RETEST:
- close outside prior boundary by at least 0.10 ATR
- body/volume/15m directional confirmation

2. SWEEP_RECLAIM:
- extreme outside prior boundary by at least 0.10 ATR
- close reclaimed inside range

3. RANGE_EDGE_REJECTION:
- touch or shallow excursion at range edge
- outside excursion strictly less than 0.10 ATR
- close back inside range
- no clear 15m long_bias or short_bias
- first version only in explicitly allowed volatility state
- existing breakout/sweep candidate must be false

Boundary ownership:
outside excursion == 0.10 ATR belongs to SWEEP_RECLAIM, not RANGE_EDGE_REJECTION.

Defensive evaluation order:
1. SWEEP_RECLAIM
2. BREAKOUT_RETEST
3. RANGE_EDGE_REJECTION
4. WATCH / WAIT

优先级只是最后防御；主要隔离必须来自不相交的逻辑条件。

CROSS_CANDLE_INTERACTION_REQUIREMENTS:
必须分析并提出最小政策：
- 已存在 PREPARE 时，其他 Setup 是否允许新候选；
- 已存在未过期 FAST/STANDARD 时，其他 Setup 是否允许新候选；
- 有效期内出现反方向候选时，默认 NO_NEW_SIGNAL，除非另行授权；
- 如何统计 same-candle overlap、cross-candle overlap、suppressed-by-priority、suppressed-by-active-signal、opposite-signal-within-expiry 和重复 market event。

若当前 lifecycle 无法用小范围 guard 安全闭合，则 RANGE_EDGE_REJECTION 只能保持 SHADOW_ONLY，不得声称无干扰。

DATA_SCOPE_FIRST_VERSION:
只使用当前已经具备的：
- ETH 5m OHLCV
- ETH 15m OHLCV
- ATR
- recent high/low boundary
- median volume
- 15m direction
- mark/mid reference
- 已存在的 OI/funding 只可用于研究分层，未经消融证明不得成为硬门槛

禁止引入：
- L2 Order Book
- BBO/order-book imbalance
- trades/order-flow imbalance
- Volume Profile / VAH / VAL / POC
- liquidation feed
- Hummingbot/Nautilus 生产接入
- 自动下单
- 新交易所写权限

BACKTEST_OUTPUTS:
必须分别报告 baseline、experiment、combined：
- signal count
- unique setup count
- independent market event count
- LONG/SHORT
- FAST/STANDARD
- volatility/regime 分层
- gross/net expectancy in R
- fee/slippage/funding/manual-delay impact
- win rate
- average win/loss
- max drawdown
- longest losing streak
- overlap matrix
- suppressed-by-priority
- suppressed-by-active-signal
- opposite-signal-within-expiry
- combined incremental expectancy
- combined frequency change
- combined drawdown change
- concentration in top trades

第一轮禁止自动参数优化。参数必须预先冻结、数量极少、具备经济解释。

DECISION_OUTPUTS:
REPLAY_CORRECTNESS = PASS / FAIL
EXPERIMENT_EVIDENCE = POSITIVE / NEGATIVE / INCONCLUSIVE
INTERACTION_SAFETY = PASS / FAIL / SHADOW_ONLY
IMPLEMENTATION_DISPOSITION = GO / REVISE / REJECT

GO 只允许进入最小生产候选开发，不等于部署授权。

IF_GO_IMPLEMENTATION_DIRECTION:
- 复用现有 StrategySnapshot、Signal、PreparedSetup、StrategyOutput、volatility overlay、TradePlan、ShadowOrder、notification、Outcome。
- 更新策略版本和兼容性。
- 显式标记 setup_family=RANGE_EDGE_REJECTION、rollout_stage=EXPERIMENTAL。
- 评估最小 default-off 或可快速关闭的 eligibility gate，但禁止扩展成通用插件平台。
- 补齐每个 Setup 单独触发、同 K 线互斥、跨 K 线冲突、FAST/STANDARD、LONG/SHORT、Overlay、TradePlan、序列化、Outcome、runtime publication 测试。
- 不修改账户权限，不自动下单，不影响现有 First Launch 持续运行。

WHY_INDEPENDENT_STRATEGY_MAY_BE_NEEDED_LATER:
必须在方案中说明：
- 独立经济机制
- 独立启停和 rollout
- 独立风险预算
- 并发候选
- 持仓归属
- 独立绩效和淘汰
- 不同数据/执行需求
- 故障隔离

若以上需求在本轮就不可避免，不得强行塞入同一 SetupFamily；应返回范围升级建议和投入产出比。

STOP_CONDITIONS:
- 必须建设完整多策略框架才安全
- 必须修改 First Launch 传输/生产架构
- 必须增加 L2/Volume Profile 才能定义第一版
- 三个 Setup 无法建立清晰互斥
- combined replay 出现大量静默压制或反向冲突
- 费用后明显负期望
- 结果依赖极少数异常交易
- 需要反复调参才得到正结果
- 需要大规模数据库或通知重构
- 预计投入明显超出最小目标

REQUIRED_FINAL_DELIVERABLE:
请输出一个完整统一实施包，包括：
1. REVIEW_STATUS
2. live identity 与三份 GitHub 文档核验
3. 推荐结构及理由
4. 精确触发与互斥矩阵
5. 跨 K 线 active-signal policy
6. 原生联合回测设计
7. 数据、时间语义、成本模型
8. 文件范围、依赖和测试矩阵
9. 时间/成本估算
10. GO/REVISE/REJECT Gate
11. 风险、停止条件、回滚
12. 给 Project Control 的执行提示词
13. 给 Codex CLI Writer 的一次性任务提示词
14. 给独立 Reviewer 的只读验收提示词

PROCESS_RULES:
- 先只读核验，再规划；没有明确授权不得修改生产。
- First Launch 生产运行与离线研究严格隔离。
- 不得为了产生更多信号放宽原有 Setup 阈值。
- 不得同时增加第二个新实验 Setup。
- 不得跳过 baseline-only 与 combined replay。
- 不得只给组合总收益而隐藏各 Setup 表现。
- 不得把单元测试或构造场景冒充历史回测。
- 不得因“今天完成”而跳过独立审查、CI 或部署 Gate。
```
