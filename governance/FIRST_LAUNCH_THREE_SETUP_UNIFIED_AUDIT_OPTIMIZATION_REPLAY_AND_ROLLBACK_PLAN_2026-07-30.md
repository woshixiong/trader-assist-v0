# First Launch 三 Setup 统一审计、有限优化、联合回放与无损回滚计划

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-UNIFIED-AUDIT-2026-07-30-R1`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `STRATEGY RESEARCH AND ENGINEERING GOVERNANCE / NON-EXECUTABLE`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**权限边界：** 本文不授权生产修改、部署、重启、账户访问、签名、交易所写入、自动下单、Mark Ready 或 merge。

---

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
5. 只接受具有样本外、成本后、跨 regime 稳健证据的修改；
6. 未被证据支持的现有逻辑保持不变；
7. 新候选失败时能够无损恢复到当前生产版本。

---

## 2. 为什么可以统一优化，但不能直接重写三个 Setup

统一优化的收益：

- 三个 Setup 使用相同审计模板、数据、成本模型和回放引擎；
- 可以直接测量各自覆盖的 regime、重复事件和组合效果；
- 可以在一次版本升级中完成策略版本、兼容、测试和部署；
- 可以判断 FAST / STANDARD 在不同 Setup 中应如何保留；
- 可以发现现有两个 Setup 已存在但此前未被充分验证的问题。

直接重写的风险：

- 无法区分收益变化来自哪个规则；
- 原有已经上线的行为失去可靠比较基准；
- 参数组合数量急剧增加，形成 backtest overfitting；
- 三个 Setup 的交互矩阵和测试矩阵非线性扩大；
- 一旦上线失败，无法确认是新增 Setup、旧 Setup 修改、生命周期还是兼容问题。

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

---

## 3. 外部成熟经验与证据基础

本轮设计不得只依赖内部经验。至少纳入以下成熟证据：

1. **支持阻力与边界有效性**  
   Chung and Bellotti, *Evidence and Behaviour of Support and Resistance Levels in Financial Time Series*：历史反应次数较多的支持阻力位更可能再次产生反应，同时边界效力会随时间衰减。  
   https://arxiv.org/abs/2101.07410

2. **突破、反转和订单聚集的微观机制**  
   Carol Osler, Federal Reserve Bank of New York, *Currency Orders and Exchange-Rate Dynamics*：止盈和止损订单在支持阻力附近聚集，可解释边界处反转与突破后的趋势加速。  
   https://www.newyorkfed.org/research/staff_reports/sr125.html

3. **扫损与价格级联风险**  
   Carol Osler, *Stop-Loss Orders and Price Cascades in Currency Markets*：止损聚集可能形成快速、自我强化的价格级联，支持 Sweep/Breakout 机制，同时要求防范 Range 策略在真正突破时逆势。  
   https://www.newyorkfed.org/research/staff_reports/sr150.html

4. **趋势和动量的状态依赖风险**  
   Moskowitz, Ooi and Pedersen, *Time Series Momentum*；Daniel and Moskowitz, *Momentum Crashes*：趋势延续具有跨资产证据，但在高波动反转状态中可能出现严重损失，要求 Breakout 策略按 regime 和波动分层。  
   https://ideas.repec.org/a/eee/jfinec/v104y2012i2p228-250.html  
   https://www.nber.org/papers/w20439

5. **均值回归必须联合考虑成本、期限与止损**  
   Leung and Li, *Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit*：均值回归入场、止盈、止损和交易成本必须联合设计，不能只定义“触边回归”。  
   https://arxiv.org/abs/1411.5062

6. **数据挖掘和多重测试风险**  
   Sullivan, Timmermann and White, *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*；Bailey et al., *The Probability of Backtest Overfitting*；Bailey and López de Prado, *The Deflated Sharpe Ratio*。  
   https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163  
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253  
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

7. **回测因果性与启动历史**  
   Freqtrade 官方 `lookahead-analysis` 与 `recursive-analysis`：完整 DataFrame、未触发信号和启动窗口差异都会造成错误结论。  
   https://docs.freqtrade.io/en/stable/lookahead-analysis/  
   https://docs.freqtrade.io/en/stable/recursive-analysis/

这些来源用于定义机制、风险和验证方法，不代表其具体参数可以直接复制到 ETH 5m/15m First Launch。

---

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

不得存在无法量化的词，例如“明显”“强势”“较大”“靠近”，除非转换为明确计算公式和边界归属。

---

## 5. `SWEEP_RECLAIM` 重新审计重点

经济机制：价格越过已确认边界并触发聚集流动性或止损，但突破未被接受，随后收回区间。

必须审计：

- 当前滚动边界是否具有足够历史触碰和时效性；
- `0.10 ATR` excursion 是否只是实现常量，还是合理研究阈值；
- reclaim close 的深度和 K 线位置是否足以区分真实收回与边界噪声；
- FAST 的成交量与收盘强度是否合理；
- STANDARD 是否能够在后续 1–3 根闭合 5m K 线上真正推进；
- 15m directional conflict 是否过严或过宽；
- 止损是否位于 material extreme 外侧且不会被普通噪声反复击穿；
- 1R/2R 是否与结构空间一致；
- 与 Breakout 的边界归属是否唯一；
- 与 Range 的 excursion 域是否严格互斥。

允许的候选修改数量必须有限。不得同时搜索大量 excursion、volume、close-location 和 stop 参数组合。

---

## 6. `BREAKOUT_RETEST` 重新审计重点

经济机制：价格越过具有意义的边界并被市场接受，订单流和止损级联支持延续；保守模式等待回踩确认。

必须审计：

- 边界是否经过历史反应验证，而不是任意短期极值；
- breakout close、body、volume 和 15m direction 是否共同提供增量价值；
- FAST 是否需要更高的 acceptance/volume 条件；
- STANDARD 的 retest 必须如何定义，是否确实在未来 K 线推进；
- false breakout 和 immediate reclaim 如何 fail closed；
- 高波动反转状态是否需要限制；
- chase limit 是否避免突破后过度追价；
- stop 是否基于 retest structure，而不是机械 ATR；
- 1R/2R 与可用结构空间是否一致；
- 与 Sweep 的“收盘区间内/区间外”归属是否唯一；
- 与 Range 的 close acceptance 是否严格互斥。

---

## 7. `RANGE_EDGE_REJECTION` 严格审计重点

经济机制：已经形成并仍有效的区间边缘被触及或轻微越过，但价格未被市场接受在区间外，随后向区间内部回归。

必须审计：

- 区间窗口、宽度、触碰次数、触碰独立性和边界衰减；
- 15m 非趋势和允许 volatility state；
- dual-edge candle veto；
- shallow excursion 与 Sweep 的唯一边界；
- close-inside、wick、volume 和 follow-through 的增量价值；
- 区间转趋势时的主要失败模式；
- FAST 与 STANDARD 的收益、回撤、错失和追价差异；
- 结构止损；
- 区间内是否容纳当前固定 2R 目标和成本缓冲；
- 与原有两个 Setup 的同 K 线和跨 K 线交互。

此前提出的 Range 参数只属于预注册研究候选，不属于生产批准参数。

---

## 8. FAST 与 STANDARD 决策

本轮研究阶段两个模式都保留。

```text
FAST = initial closed candle confirms immediately
STANDARD = initial candle creates PREPARE and later closed candle confirms
```

用户层面可以仍显示一个 SetupFamily，但证据层必须保留 `confirmation_mode`。

三个 Setup 必须分别报告：

- FAST signal count / independent event count；
- STANDARD signal count / independent event count；
- FAST-only events；
- STANDARD-only events；
- 同一市场事件中 FAST 与 STANDARD 的先后和重复；
- FAST 相比 STANDARD 的入场优势；
- STANDARD 相比 FAST 的假信号过滤；
- 手续费、滑点和人工延迟后的净期望；
- 最大回撤、连续亏损和 MAE；
- 被等待确认而错过的行情；
- 等待确认后追价超限的行情。

回测后允许每个 Setup 得出不同结论：

```text
KEEP_FAST_AND_STANDARD
KEEP_FAST_ONLY
KEEP_STANDARD_ONLY
MERGE_USER_PRESENTATION_BUT_KEEP_INTERNAL_MODES
REJECT_SETUP
```

禁止在回测前取消任一模式，也禁止为了减少代码量而将两种不同确认时序混成不可归因的单一规则。

---

## 9. 有限优化政策

为平衡严谨性和开发速度，固定以下限制：

1. 当前 v0.1 参数和输出永久保留为 exact baseline；
2. 每个 Setup 先完成机制审计，再冻结候选；
3. 每个关键机制最多保留主方案和一个合理对照；
4. 不允许自动 hyperopt、遗传搜索或大规模网格；
5. 所有尝试必须进入 trial ledger，包括失败结果；
6. 不能看到测试集结果后继续修改同一测试集；
7. 先使用开发区间冻结规则，再在未接触的时间区间验证；
8. 有足够数据时再使用 walk-forward / CSCV / DSR；样本不足必须判定 `INCONCLUSIVE`，不能降低门槛；
9. 复杂度增加必须由费用后增量价值证明；
10. 若某项修改没有稳定改善，则保留当前 v0.1 行为。

“最优化”的实际定义：

```text
BEST_SUPPORTED_CANDIDATE_WITHIN_PRE_REGISTERED_BOUNDED_SEARCH_SPACE
```

不是：

```text
BEST_HISTORICAL_RESULT_AFTER_UNLIMITED_SEARCH
```

---

## 10. 联合回放模式

必须使用同一个因果原生 replay、同一数据和同一成本模型运行：

```text
A. V0_1_EXACT_BASELINE
B. V0_1_INSTRUMENTED_BASELINE
C. SWEEP_CANDIDATE_VARIANTS
D. BREAKOUT_CANDIDATE_VARIANTS
E. RANGE_FAST_AND_STANDARD
F. ALL_RAW_CANDIDATES_NO_ARBITRATION
G. COMBINED_V0_2_EXACT_POLICY
H. ABLATION_AND_SIMPLE_BASELINES
```

`B` 的最终输出必须逐事件等同于 `A`，用于证明 instrumentation 没有改变生产语义。

`F` 必须记录所有原始候选，不能使用 first-match return 隐藏重叠。

`G` 才应用最终：

- 同 K 线数学互斥；
- 边界归属；
- Setup 优先级；
- PREPARE / active expiry 政策；
- duplicate market-event policy；
- opposite-signal policy。

必须输出：

- 每个 Setup、Side、FAST/STANDARD 的原始和最终信号；
- same-candle overlap；
- cross-candle overlap；
- suppressed-by-domain；
- suppressed-by-priority；
- suppressed-by-active-lifecycle；
- opposite candidate within expiry；
- duplicate market-event clusters；
- baseline events displaced by candidate policy；
- gross/net expectancy in R；
- fees、slippage、funding、manual delay；
- MFE、MAE、win rate、average win/loss；
- max drawdown、drawdown duration、longest loss streak；
- signal concentration and top-trade contribution；
- chronological and regime stability；
- parameter-neighborhood stability；
- trial count and selection record。

---

## 11. 生产候选选择原则

一个现有 Setup 的修改只有在以下条件同时成立时才可以替换 v0.1：

- replay correctness PASS；
- 无 lookahead 和启动窗口问题；
- 独立事件定义有效；
- 费用后表现不是明显负期望；
- 改善不只来自极少数异常交易；
- 在未参与规则选择的时间段中仍保持方向一致；
- 在合理成本压力下没有完全失效；
- 没有通过增加复杂度隐藏性能下降；
- 没有破坏与其他 Setup 的互斥和生命周期安全；
- 相比保留 v0.1 确实存在可解释的增量价值。

允许最终 v0.2 是混合结果：

```text
SWEEP = KEEP_V0_1 or ACCEPT_BOUNDED_IMPROVEMENT
BREAKOUT = KEEP_V0_1 or ACCEPT_BOUNDED_IMPROVEMENT
RANGE = ADD / REVISE / REJECT
FAST_STANDARD_POLICY = PER_SETUP_EVIDENCE_DECISION
```

不要求为了“统一升级”强行修改现有两个 Setup。

---

## 12. 延后 Backlog

以下能力对未来自动交易重要，但本轮不开发：

### `STRATEGY_SETUP_ENABLEMENT_AND_KILL_SWITCH_V1`

- 独立 Setup 启停；
- fail-closed configuration；
- 快速暂停；
- 自动交易阶段的 emergency kill switch；
- 独立 rollout stage。

### `AUTOMATED_TRADING_SHADOW_CANARY_AND_PROMOTION_CONTROL_V1`

- 自动交易前的独立 Shadow；
- Canary risk cap；
- 独立策略晋级、暂停和回退；
- 自动执行与人工执行分离；
- promotion evidence gate。

当前 First Launch 仍由人工决定是否交易，现有 `NOT_SUBMITTED` ShadowOrder 和 Outcome 流程继续复用，不新增子系统。

---

## 13. 当前生产基线和无损回滚合同

最低要求：任何 v0.2 升级失败，必须恢复到当前生产版本：

```text
ROLLBACK_CODE_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
ROLLBACK_STRATEGY_VERSION = ETH-LDAR-v0.1
ROLLBACK_SERVICE_CONFIGURATION = exact pre-upgrade copy
ROLLBACK_DATABASE = consistent pre-upgrade SQLite backup
```

生产实现必须避免数据库 Schema migration。若候选需要 Schema migration，立即停止重新规划。

部署前必须保存：

- exact 当前代码 bundle / commit identity；
- systemd unit 与环境配置；
- risk configuration；
- notification configuration identity（不得导出秘密值）；
- activation permit state；
- 一致性 SQLite backup；
- ta-status、PID、session 和运行状态基线；
- rollback command packet。

兼容测试必须覆盖：

- 新代码读取 v0.1 数据库；
- v0.1 与 v0.2 混合历史记录；
- 新代码重启；
- 旧代码是否能忽略/读取 v0.2 记录；
- 若旧代码不能读取，则先归档升级期数据库，再恢复 pre-upgrade backup；
- 新增期间产生的研究证据单独保存，不因恢复数据库而丢失；
- 回滚后服务、READY、K 线 finalization、evaluation 和 notification 全部恢复。

“无损回滚”定义：

1. 当前 v0.1 生产能力、配置和历史数据不被破坏；
2. 回滚不需要手工修复数据库；
3. 升级期新证据在恢复前完成只读归档；
4. 回滚后恢复与升级前同等的运行和安全状态；
5. 不承诺保留失败候选在生产数据库中的可执行状态。

---

## 14. 工程范围

本轮优先允许：

- 离线研究数据和 replay；
- strategy pure logic；
- candidate instrumentation；
- lifecycle correctness tests；
- TradePlan / Outcome version compatibility；
- notification rendering compatibility；
- rollback qualification scripts or runbook。

本轮禁止：

- market-data transport 修改；
- candle authority 修改；
- 新异步服务；
- L2 / trades / Volume Profile；
- 自动执行；
- 通用插件系统；
- 独立多策略平台；
- 数据库 Schema migration；
- 自动参数优化；
- 为了统一代码而重写稳定的运行链。

---

## 15. 预计时间与资源

在当前 STANDARD 生命周期、版本兼容和历史数据均无结构性问题时：

```text
Phase 0: current lifecycle and exact baseline qualification   0.5–1 day
Phase 1: three-setup external research and contract freeze    1–2 days
Phase 2: causal replay, data, raw-candidate instrumentation    1.5–3 days
Phase 3: bounded variants and joint evidence report           1–2 days
Phase 4: minimum selected v0.2 implementation                  1–2 days
Phase 5: regression, compatibility, review, CI, deploy         1–2 days
TOTAL BALANCED TARGET                                         6–10 working days
```

快速路径：若现有两个 Setup 保持 v0.1，仅新增通过审计的 Range，且 lifecycle/compatibility 均通过，可压缩到 `4–6` 个工作日。

扩展路径：若当前 STANDARD progression 有缺陷、现有两个 Setup 确需修改、或旧代码无法安全读取混合版本记录，预计 `8–12` 个工作日，并必须拆分修复与策略升级，不能塞进一个不可审查的大 PR。

最低角色：

- 1 个策略/工程优化负责人；
- 1 个实现执行者（可由 Codex CLI 承担 bounded writer）；
- 1 个独立只读 reviewer / Project Control；
- 用户只参与策略合同和最终上线授权，不参与逐错误修补。

---

## 16. Gate

必须按顺序：

```text
G0 CURRENT_STANDARD_LIFECYCLE = PASS / FAIL
G1 THREE_SETUP_STRATEGY_CONTRACT_AUDIT = PASS / REVISE
G2 REPLAY_CORRECTNESS = PASS / FAIL
G3 V0_1_INSTRUMENTATION_PARITY = PASS / FAIL
G4 FAST_STANDARD_EVIDENCE = PER_SETUP_DECISION / INCONCLUSIVE
G5 SAME_CANDLE_EXCLUSIVITY = PASS / FAIL
G6 CROSS_CANDLE_INTERACTION = PASS / FAIL
G7 CANDIDATE_EVIDENCE = POSITIVE / NEGATIVE / INCONCLUSIVE
G8 VERSION_COMPATIBILITY = PASS / FAIL
G9 LOSSLESS_ROLLBACK_QUALIFICATION = PASS / FAIL
G10 PRODUCTION_DISPOSITION = GO / REVISE / REJECT
```

任何 correctness、compatibility、rollback 或 interaction Gate 失败，都不得部署。

---

## 17. 最终裁决

本轮允许统一审计和有限优化三个 Setup，但不允许为了“这次一起升级”而强迫三个 Setup 都发生变化。

最短且严谨的生产路线是：

```text
冻结当前 v0.1
→ 审计三个 Setup
→ 保留 FAST 与 STANDARD 共同研究
→ 有限预注册候选
→ 联合因果回放
→ 每项修改独立举证
→ 只实施被支持的最小 v0.2
→ exact-SHA + SQLite backup 无损回滚保障
```
