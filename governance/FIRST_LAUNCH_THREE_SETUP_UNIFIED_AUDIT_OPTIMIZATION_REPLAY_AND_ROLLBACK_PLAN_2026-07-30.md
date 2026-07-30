# First Launch 三 Setup 统一审计、有限优化、联合回放与无损回滚计划

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-UNIFIED-AUDIT-2026-07-30-R1`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `STRATEGY RESEARCH AND ENGINEERING GOVERNANCE / NON-EXECUTABLE`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**权限边界：** 本文不授权生产修改、部署、重启、账户访问、签名、交易所写入、自动下单、Mark Ready 或 merge。

## Superseding scope correction

本文件的工程范围、时间和回滚要求，现由以下附录进一步收敛：

`governance/FIRST_LAUNCH_THREE_SETUP_48H_STRATEGY_FIRST_SCOPE_ADDENDUM_2026-07-30.md`

若本文与该附录在以下方面存在差异，以附录为准：

- `1–2` 工作日策略优先 timebox；
- 不以寻找历史最高收益为目标；
- 三个已知主观交易机制的合理量化；
- 两层 `environment state + event outcome` 模型；
- 不做完整回滚演练项目；
- 最小回滚仅要求 exact SHA、配置、SQLite 一致性备份和恢复命令；
- 工程架构默认不变。

## 1. 本轮范围重新定级

本轮不再只是“新增一个 `RANGE_EDGE_REJECTION` Setup”。本轮定义为：

```text
CURRENT_PRODUCTION_BASELINE = IMMUTABLE_COMPARATOR_AND_ROLLBACK_TARGET
AUDIT_EXISTING_SETUP_1 = SWEEP_RECLAIM
AUDIT_EXISTING_SETUP_2 = BREAKOUT_RETEST
AUDIT_NEW_SETUP_3 = RANGE_EDGE_REJECTION
FAST_AND_STANDARD = RETAIN_IN_RESEARCH_FOR_ALL_APPLICABLE_SETUPS
OPTIMIZATION = BOUNDED_PRE_REGISTERED_CANDIDATE_COMPARISON
BACKTEST = CAUSAL_NATIVE_JOINT_REPLAY
PRODUCTION_TARGET = ONE_REVIEWED_V0_2_CANDIDATE
ROLLBACK_TARGET = EXACT_CURRENT_V0_1
```

“整体优化”不等于最大化历史收益，也不等于无限参数搜索。它表示：

1. 使用统一的经济机制和量化合同重新审计三个 Setup；
2. 对现有 v0.1 保持不可变的 exact baseline；
3. 在回测前冻结极少量、具备经济解释的候选修改；
4. 同时运行旧版本、单 Setup 候选、全部原始候选和最终组合政策；
5. 只接受具有成本后、因果和跨状态合理性的修改；
6. 未被证据支持的现有逻辑保持不变；
7. 新候选失败时能够恢复到当前生产版本。

## 2. 统一审计而不直接重写

统一优化的收益：

- 三个 Setup 使用相同审计模板、数据、成本模型和回放引擎；
- 可以直接测量各自覆盖的状态、重复事件和组合效果；
- 可以判断 FAST / STANDARD 在不同 Setup 中应如何保留；
- 可以发现现有两个 Setup 已存在但此前未被充分验证的问题。

直接重写的风险：

- 无法区分变化来自哪个规则；
- 原有已经上线的行为失去可靠比较基准；
- 参数组合数量急剧增加；
- 三个 Setup 的交互和测试矩阵非线性扩大；
- 一旦失败，无法确认是新增 Setup、旧 Setup 修改、生命周期还是兼容问题。

因此执行路线必须是：

```text
v0.1 EXACT BASELINE
→ INSTRUMENTED BASELINE WITH IDENTICAL OUTPUT
→ PRE-REGISTERED CANDIDATE VARIANTS
→ JOINT RAW-CANDIDATE REPLAY
→ EXACT POLICY REPLAY
→ EVIDENCE-BASED SELECTION
→ MINIMUM v0.2 PRODUCTION CHANGE
```

## 3. 外部成熟经验与证据基础

本轮设计不得只依赖内部经验。至少纳入以下成熟证据：

1. Chung and Bellotti, *Evidence and Behaviour of Support and Resistance Levels in Financial Time Series*：历史反应次数较多的支持阻力位更可能再次产生反应，同时边界效力会随时间衰减。
2. Carol Osler, Federal Reserve Bank of New York, *Currency Orders and Exchange-Rate Dynamics*：止盈和止损订单在支持阻力附近聚集，可解释边界处反转与突破后的趋势加速。
3. Carol Osler, *Stop-Loss Orders and Price Cascades in Currency Markets*：止损聚集可能形成快速、自我强化的价格级联，支持 Sweep/Breakout 机制，同时要求防范 Range 在真正突破时逆势。
4. Moskowitz, Ooi and Pedersen, *Time Series Momentum*；Daniel and Moskowitz, *Momentum Crashes*：趋势延续具有跨资产证据，但在高波动反转状态中可能出现严重损失。
5. Leung and Li, *Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit*：均值回归入场、止盈、止损和交易成本必须联合设计。
6. Bailey et al., *The Probability of Backtest Overfitting*；Bailey and López de Prado, *The Deflated Sharpe Ratio*：限制多重测试和选择偏差。
7. Freqtrade 官方 `lookahead-analysis` 与 `recursive-analysis`：回放必须避免未来数据并保持启动历史一致。

这些来源用于定义机制、风险和验证方法，不代表其具体参数可以直接复制到 ETH 5m/15m First Launch。

## 4. 三 Setup 统一策略审计模板

每个 Setup 必须在回测前完成同一套合同：

```text
ECONOMIC_HYPOTHESIS
TARGET_REGIME
PROHIBITED_REGIME
EVENT_BOUNDARY_DEFINITION
HISTORICAL_LEVEL_QUALITY
ENTRY_CANDIDATE
FAST_CONFIRMATION
STANDARD_PREPARE
STANDARD_CONFIRMATION
INVALIDATION
EXPIRY
ENTRY_ZONE
CHASE_LIMIT
STRUCTURAL_STOP
TARGET_FEASIBILITY
TRANSACTION_COST_ASSUMPTIONS
EXPECTED_FAILURE_MODE
INTERACTION_WITH_OTHER_SETUPS
```

不得存在无法量化的“明显、强势、较大、靠近”。

## 5. Sweep Reclaim 审计

必须审计：

- 边界质量、历史触碰和时效性；
- excursion 阈值；
- reclaim close 深度和 K 线位置；
- FAST 成交量和收盘强度；
- STANDARD 后续 1–3 根 5m 推进；
- 15m directional conflict；
- material extreme 与结构止损；
- 1R/2R 结构空间；
- 与 Breakout 和 Range 的唯一归属。

## 6. Breakout Retest 审计

必须审计：

- 边界是否经过历史反应验证；
- breakout close、body、volume 和 15m direction；
- FAST acceptance；
- STANDARD retest；
- false breakout 和 immediate reclaim；
- 高波动反转状态；
- chase limit；
- retest structure stop；
- 与 Sweep 和 Range 的唯一归属。

## 7. Range Edge Rejection 审计

必须审计：

- 区间窗口、宽度、触碰次数、触碰独立性和边界衰减；
- 15m 非趋势和 volatility state；
- dual-edge veto；
- shallow excursion；
- close-inside、wick、volume 和 follow-through；
- 区间转趋势失败模式；
- FAST / STANDARD；
- 结构止损；
- 区间内目标空间；
- 与原有两个 Setup 的交互。

此前提出的 Range 参数只属于研究候选，不属于生产批准参数。

## 8. FAST 与 STANDARD

研究阶段两个模式都保留：

```text
FAST = initial closed candle confirms immediately
STANDARD = initial candle creates PREPARE and later closed candle confirms
```

三个 Setup 必须分别报告：

- FAST / STANDARD event count；
- FAST-only / STANDARD-only；
- 同一 market event 的先后和重复；
- FAST 入场优势；
- STANDARD 假信号过滤；
- 延迟、滑点、MAE、MFE、回撤和净期望。

## 9. 联合因果回放

必须运行：

```text
A. V0_1_EXACT_BASELINE
B. V0_1_INSTRUMENTED_BASELINE
C. SWEEP_CANDIDATE_VARIANTS
D. BREAKOUT_CANDIDATE_VARIANTS
E. RANGE_FAST_AND_STANDARD
F. ALL_RAW_CANDIDATES_NO_ARBITRATION
G. COMBINED_V0_2_EXACT_POLICY
```

必须逐根推进闭合 K 线，只暴露当时可见数据。

重点输出：

- exact baseline parity；
- all raw candidates；
- same-candle / cross-candle overlap；
- same-direction duplicates；
- opposite candidates；
- suppressed candidates；
- independent market events；
- FAST / STANDARD；
- gross / net R；
- fees、slippage、funding、manual delay；
- drawdown、losing streak、MFE、MAE；
- top-trade concentration。

## 10. 工程边界

默认不改变架构。

禁止：

- transport、candle authority、reconnect；
- 新服务或第三方 runtime；
- 数据库 Schema migration；
- 通用多策略平台；
- L2、trades、Volume Profile；
- 自动下单；
- 自动参数优化。

## 11. 回滚

最低回滚目标：

```text
ROLLBACK_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
ROLLBACK_STRATEGY_VERSION = ETH-LDAR-v0.1
DATABASE_SCHEMA_CHANGE = NO
```

保存 exact code、配置、systemd unit、permit、SQLite 一致性备份和恢复命令。

本轮不要求建立完整回滚平台或单独安排大规模回滚演练。若新版本失败，恢复 exact SHA 与配置；若 mixed-version 数据阻止旧代码启动，则恢复部署前数据库备份，然后执行最小生产健康核验。

## 12. 延期功能

Strategy enablement、kill switch、自动交易 Shadow、Canary 和自动晋级控制保留在 Backlog Issue #62，不进入当前人工执行阶段。

## 13. 时间与停止条件

当前目标 timebox 由 48 小时策略优先附录规定为 `1–2` 工作日。

出现以下情况不得强行上线：

- 当前 STANDARD 生命周期缺陷；
- 三 Setup 无法清晰量化；
- instrumented parity 失败；
- raw overlap 无法解释；
- 成本后明显不可行；
- 数据样本不足；
- 需要运行架构或数据库迁移；
- 无法恢复当前 exact v0.1。
