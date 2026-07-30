# First Launch 震荡策略、策略身份与联合回测决策记录

**记录 ID：** `TA-FIRST-LAUNCH-RANGE-STRATEGY-DECISION-2026-07-30-R1`  
**日期：** 2026-07-30  
**仓库：** `woshixiong/trader-assist-v0`  
**状态：** `STRATEGY RESEARCH DECISION / NON-EXECUTABLE / PRE-IMPLEMENTATION`  
**关联基线：** `TA-V0-STRATEGY-PREDEVELOPMENT-ANALYSIS-2026-07-28-R1`  
**权限边界：** 本文不授权修改生产策略、部署、激活、账户访问、签名、交易所写入、自动下单或真实资金风险。任何生产实现必须经过独立任务、回测、测试、审查、CI、部署授权和上线裁决。

---

## 1. 关键概念纠正

“实验性策略”和“独立第二策略”不是对立选项，而是两个正交维度。

### 1.1 结构身份维度

- `SetupFamily`：同一个产品策略核心内部的一个可区分交易形态，共用 evaluator、Signal/TradePlan、风险和发布链。
- `IndependentStrategy`：拥有独立 `strategy_id`、版本、启停、证据、风险上限、输出流、归因和生命周期的策略。

### 1.2 成熟度与权限维度

- `RESEARCH`
- `SHADOW_CANDIDATE`
- `SHADOW`
- `CANARY`
- `ACTIVE`
- `PAUSED / RETIRED / REJECTED`

因此：

```text
一个 SetupFamily 可以是 EXPERIMENTAL。
一个 IndependentStrategy 也可以是 EXPERIMENTAL。
```

本次最小投入建议是：

```text
STRUCTURE = THIRD_SETUP_FAMILY_INSIDE_ETH_LDAR
SETUP = RANGE_EDGE_REJECTION
ROLLOUT = EXPERIMENTAL
NOT = INDEPENDENT_SECOND_STRATEGY
```

---

## 2. 日常使用差异

若 `RANGE_EDGE_REJECTION` 作为现有策略核心中的第三个 SetupFamily：

- 用户仍收到同一种 Operator Review Card；
- 仍使用相同 TradePlan、ShadowOrder、通知和人工下单流程；
- 信号必须明确显示 `setup_family=RANGE_EDGE_REJECTION` 和 `rollout_stage=EXPERIMENTAL`；
- 同一评估周期只发布一个最终候选；
- 现有两个 SetupFamily 保持优先；
- 新 Setup 可以在不满足条件时保持 WAIT/WATCH；
- 若没有独立启停配置，关闭该 Setup 需要重新部署策略版本。

若作为独立第二策略：

- 两个策略可以同时、同向或反向产生候选；
- 必须独立启停、独立风险、独立绩效和独立归因；
- 必须增加 StrategyConflictResolver、position ownership、同方向风险去重和反方向政策；
- 用户可能同时看到两个互相冲突的信号；
- 工程和产品复杂度显著增加。

本次为了最短周期，不建设独立第二策略结构。

---

## 3. 是否可以同时增加多个实验性 Setup

技术上可以，但产品和研究上不应一次增加多个。

原因：

- 每增加一个 Setup 都增加候选重叠、优先级和测试矩阵；
- 会扩大参数搜索和回测多重比较风险；
- 会使一个统一策略版本变成难以解释的规则集合；
- 当前 runtime 不是多策略并发输出与组合风险系统；
- 无法快速判断新增收益来自哪一个机制。

固定约束：

```text
ONE_NEW_EXPERIMENTAL_SETUP_PER_ITERATION
OTHER_CANDIDATES = OFFLINE_RESEARCH_ONLY
```

当出现以下任一条件时，必须停止继续堆叠 Setup，转向独立策略设计：

- 需要同一时刻输出多个候选；
- 需要单独启停和单独风险预算；
- 需要持仓归属和策略间冲突处理；
- 经济机制、适用 regime 和退出逻辑明显独立；
- 需要不同数据产品或执行方式。

---

## 4. 推荐实验 Setup：RANGE_EDGE_REJECTION

### 4.1 经济机制

稳定区间中，价格接近边缘但未形成被市场接受的突破；边缘外侧流动性和对手盘使价格重新回到区间。该 Setup 交易“边缘拒绝”，不是泛化的指标超买超卖。

### 4.2 与其他均值回归方法的区别

#### RANGE_EDGE_REJECTION

- 使用离散的近期结构边界；
- 依赖触边、影线、收盘位置、ATR、成交量和方向状态；
- 不估计统计均值、回归速度或半衰期；
- 优点是解释性高、停止位置自然、可复用现有 OHLCV；
- 缺点是适用范围较窄，不能证明价格过程统计平稳。

#### Bollinger 类方法

- 使用移动均值和滚动标准差定义相对高低；
- Bands 只是相对位置工具，触碰 Bands 本身不是反转信号；
- 需要额外趋势或量价确认；
- 更连续、更频繁，但在趋势中可能持续沿 Band 运行；
- 参数和过滤器更多。

#### OU 类模型

- 假设被交易过程符合均值回归随机过程；
- 需要估计长期均值、回归速度、波动和半衰期；
- 更适合经过验证的平稳 spread，而不是默认把 ETH 绝对价格视为稳定 OU；
- 可推导成本、止损和期限下的进入退出边界；
- 模型错误和参数漂移是核心风险。

结论：不能事先宣称 RANGE_EDGE_REJECTION 的收益高于或低于 Bollinger/OU。简单规则可能因更少参数而更稳健，也可能遗漏更广泛机会。必须以同一数据、成本模型和样本外回放比较。

---

## 5. 数据现状与未来数据路线

### 5.1 当前已有

- ETH 5m OHLCV；
- ETH 15m OHLCV；
- mark price / mid price；
- activeAssetCtx 中的 open interest 和 funding；
- OI/funding 的 5m/15m 上下文变化与分类；
- ATR、近期高低边界、成交量中位数和 15m 方向。

当前 `evaluate_signal` 的硬触发主要使用 OHLCV、ATR、近期边界、成交量和 15m 方向。OI/funding 已进入上下文和 TradePlan 证据，但不是当前两个 SetupFamily 的硬触发门槛。

### 5.2 当前没有进入生产策略的数据产品

- L2 Order Book；
- BBO/order-book imbalance；
- trades/order-flow imbalance；
- Volume Profile / VAH / VAL / POC；
- liquidation feed；
- 历史可回放的完整微观结构数据集。

### 5.3 何时增加

#### OI/funding

优先级最高，因为已有数据入口。仅在以下条件下升级为过滤或风险变量：

- 策略经济假设明确涉及杠杆 build/unwind 或拥挤；
- 历史数据时间语义可靠；
- shadow 特征和消融证明具有增量价值；
- 不能只是增加叙事复杂度。

#### L2/trades

只有在以下情况投入：

- 信号后短期方向或入场时机是主要损失来源；
- 策略目标周期足够短，微观结构可能影响结果；
- 可以连续采集、重放、处理 reconnect 和缺口；
- 订单簿不平衡在费用后提供增量价值。

#### Volume Profile

只有在策略明确交易 value area、POC 或成交密集区时增加。5m K 线总成交量不能重建可靠的 price-by-volume 分布，需要 trades 或更细数据。

### 5.4 可信度原则

没有 L2、Volume Profile 或 OI 硬过滤的 OHLCV 策略仍然可以可信。可信度来自：

- 因果有效的数据；
- 确定性规则；
- 历史回放；
- 成本后结果；
- live shadow；
- 样本外和 regime 分层；
- 可解释的失败机制。

数据字段数量不等于策略可信度。更多数据也会增加时间对齐、漂移和过拟合风险。

---

## 6. 三个 Setup 的互斥触发设计

不能只依赖代码中的候选排列顺序；应在定义层面建立互斥域。

### 6.1 BREAKOUT_RETEST

- 收盘在近期边界外至少 `0.10 ATR`；
- 有实体、成交量和 15m 方向支持；
- `RANGE_EDGE_REJECTION` 要求收盘回到区间内，因此与其互斥。

### 6.2 SWEEP_RECLAIM

- 极值穿越边界至少 `0.10 ATR`；
- 随后收盘收回区间；
- `RANGE_EDGE_REJECTION` 的外侧穿越必须严格小于 `0.10 ATR`；
- 恰好等于 `0.10 ATR` 归入 SWEEP_RECLAIM。

### 6.3 RANGE_EDGE_REJECTION

基础 eligibility：

```text
long_bias = false
short_bias = false
volatility_state = NORMAL
existing BREAKOUT_RETEST candidate = false
existing SWEEP_RECLAIM candidate = false
```

做多研究原型：

- 触及下沿附近；
- 外侧穿越 `< 0.10 ATR`；
- 收盘回到区间内且至少高于边界一定缓冲；
- 收盘位于 K 线偏上位置；
- 下影线体现拒绝；
- 成交量不异常缺失。

做空完全镜像。

### 6.4 优先级与同周期行为

```text
1. SWEEP_RECLAIM
2. BREAKOUT_RETEST
3. RANGE_EDGE_REJECTION
4. WATCH / WAIT
```

但优先级只是防御线，主要隔离必须来自上述不相交条件。

### 6.5 跨 K 线冲突

同一 K 线只返回一个候选不能解决跨 K 线并发。部署前必须验证并固定：

```text
EXISTING_PREPARE_OR_TRIGGERED_ACTIVE
→ RANGE_EDGE_REJECTION may not publish a new candidate

RANGE_EDGE_REJECTION_ACTIVE
→ opposite new candidate defaults to NO_NEW_SIGNAL
```

若当前 lifecycle 无法实现该最小 gate，则不能声称“零干扰”；必须增加最小 active-signal eligibility guard，或将新 Setup 保持 SHADOW_ONLY。

---

## 7. 联合回测决策

新增 Setup 不应只做单独回测。使用同一个原生 replay、同一个数据集和同一个成本模型，一次运行三组结果：

```text
A. BASELINE_ONLY
   ETH-LDAR-v0.1：SWEEP_RECLAIM + BREAKOUT_RETEST

B. EXPERIMENT_ONLY
   RANGE_EDGE_REJECTION only

C. COMBINED_EXACT_POLICY
   原有 Setup + 新 Setup + 精确优先级 + active-signal gate
```

必须分别报告：

- 各 Setup 的 signal count 和 independent event count；
- LONG/SHORT、FAST/STANDARD、regime；
- gross/net expectancy in R；
- fees、slippage、manual delay；
- win rate、average win/loss、max drawdown；
- overlap matrix；
- suppressed-by-priority 数量；
- opposite-signal-within-expiry 数量；
- combined incremental expectancy；
- combined drawdown 与信号频率变化。

联合回测比先做旧策略、再做新策略更节省时间，也能直接发现互相干扰。旧策略结果仍须单独保留，不能只给组合总收益。

第一轮禁止自动参数优化。只允许少量预先冻结的候选参数；看到结果后不得反复调整同一测试区间。

---

## 8. 今日最短执行路线

### Stage 0 — 冻结范围

- 不改工程架构；
- 不增加服务、依赖、数据库 schema 或交易权限；
- 只研究一个新 Setup；
- 先回测，后决定生产实现；
- First Launch 生产继续独立运行。

### Stage 1 — 原生联合回测与研究原型

交付：

- 一次性离线 ResearchDataset；
- exact production baseline replay；
- RANGE_EDGE_REJECTION 原型；
- A/B/C 三组报告；
- overlap/conflict 报告；
- GO / REVISE / REJECT 裁决。

### Stage 2 — 只有 GO 才实现生产候选

最小实现：

- 增加 SetupFamily；
- 增加互斥条件；
- 增加 active-signal gate；
- 策略版本更新；
- 复用 TradePlan、ShadowOrder、通知和人工执行链；
- 补齐策略、overlay、risk、serialization、runtime 和 outcome 测试。

### Stage 3 — 审查与上线阶段

- Writer 不直接部署；
- 独立 patch review；
- exact-head CI；
- 受控部署；
- 初始 rollout 默认 SHADOW 或明确的低风险 CANARY；
- 未完成独立风险政策时，不得把“实验性”解释为与成熟策略同等置信度。

---

## 9. 今日停止条件

出现以下任一情况，不进入生产实现：

- 原生 baseline replay 无法与生产语义对应；
- 新 Setup 在合理费用后明显负期望；
- 信号主要来自少数相关事件；
- overlap/conflict 无法在小范围内消除；
- 需要第二策略架构、数据库 schema、新数据源或新服务；
- 需要通过大量调参才得到正结果；
- 无法在当前风险模型下表达实验性权限。

---

## 10. 当前推荐裁决

```text
RECOMMENDED_STRUCTURE = THIRD_SETUP_FAMILY
RECOMMENDED_SETUP = RANGE_EDGE_REJECTION
RECOMMENDED_MATURITY = EXPERIMENTAL
INDEPENDENT_SECOND_STRATEGY = DEFERRED
MULTIPLE_NEW_SETUPS_IN_ONE_PASS = PROHIBITED
BACKTEST_MODE = BASELINE + EXPERIMENT + COMBINED
NEW_DATA_PRODUCTS = DEFERRED_UNLESS_EVIDENCE_TRIGGERED
PRODUCTION_AUTHORIZATION = NOT_GRANTED_BY_THIS_DOCUMENT
```
