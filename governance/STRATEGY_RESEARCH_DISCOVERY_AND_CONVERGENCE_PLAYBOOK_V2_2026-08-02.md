# Strategy Research Discovery and Convergence Playbook V2

**记录 ID：** `TA-STRATEGY-RESEARCH-DISCOVERY-CONVERGENCE-PLAYBOOK-2026-08-02-V2`  
**日期：** `2026-08-02`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `MANDATORY FUTURE RESEARCH METHOD / NON-EXECUTABLE / NON-AUTHORIZING`  
**适用范围：** 后续所有 Setup、Scanner、市场状态、入场、止损、止盈、持仓管理和策略参数研究。  
**优先级：** 本文件取代与其冲突的 V1。  
**关系：** 本文是 `STRATEGY_RESEARCH_AND_BACKTEST_OPERATING_STANDARD_V1_2026-08-01.md` 之前的“第 0 阶段”。  
**权限边界：** 本文不授权代码修改、回测执行、工程派发、部署、账户访问、交易所写入或自动交易。

---

## 1. 固定策略研究目标：15 分钟日内交易

本项目默认研究目标不是波段、长线或无限持有趋势，而是：

```text
PRIMARY_STRUCTURE_TIMEFRAME = 15m
EXECUTION_TIMEFRAME = 5m
MICRO_TIMEFRAME = 1m/3m OPTIONAL_EVIDENCE_ONLY
TRADING_HORIZON = INTRADAY
HOLDING_TIME = PATH_DEPENDENT_NOT_FIXED
ENTRY_AND_EXIT = MAY_SCALE
HUMAN_FINAL_AUTHORITY = CURRENTLY_YES
```

日内研究必须承认：

- 日内可交易空间通常有限；
- 约 1R 的成本后机会可以接受；
- 不能用追求高 R 的方式消灭大部分日内机会；
- 必须在胜率、平均盈利 R、平均亏损 R、交易成本、回撤和信号数量之间平衡；
- 入场时必须明确结构止损和最大计划亏损；
- 盈利由后续价格路径决定，固定 R 只作为基线和影子检查点；
- 当前重点是识别高质量入场，动态退出引擎属于后续 V0。

每次研究开始时，若研究目标不是上述默认目标，必须显式写出例外，不得静默改成波段或长线策略。

---

## 2. 研究流程

```text
REAL TRADING OBJECTIVE
→ CURRENT SYSTEM IN PLAIN LANGUAGE
→ HUMAN OBSERVATION AS HYPOTHESIS
→ OBSERVABLE MARKET OBJECTS AND STATES
→ EXTERNAL EVIDENCE ACROSS MATURE MARKETS
→ COMMON EVENT MODEL
→ RESEARCH QUESTION SET
→ CANDIDATE PRIORITY QUEUE
→ FIRST-ROUND PARAMETER PACKET
→ FORMAL BACKTEST OPERATING STANDARD
→ PRODUCT / ENGINEERING HANDOFF
```

目标是快速收敛，而不是固定讨论轮数或固定问题数量。

---

## 3. 研究问题数量不设固定值

取消“每轮最多三个核心课题”的硬限制。

研究课题数量必须由问题本身决定，但在进入参数和回测前必须满足：

```text
EVERY_QUESTION_IS_NECESSARY_FOR_CURRENT_DECISION
EVERY_QUESTION_HAS_OBSERVABLE_INPUTS
EVERY_QUESTION_HAS_A_TESTABLE_OUTPUT
NO_DUPLICATE_OR_PURELY_NARRATIVE_QUESTION
NO_DEFERRED_PRODUCT_FEATURE_MIXED_INTO_CURRENT_RESEARCH
```

研究可以先发散，但必须通过 `CONVERGENCE_GATE`：

- 当前必须解决；
- 作为影子字段记录；
- 排入后续研究；
- 明确拒绝。

不得为了数量整齐而删除必要问题，也不得因为没有数量限制而无限扩张。

---

## 4. 候选优先级队列

任何有限候选集合必须记录完整优先级，不允许只保留主候选并遗忘其他候选。

固定层级：

```text
P0_COMPARATOR
P1_PRIMARY
P2_SECONDARY_OR_SENSITIVITY
P3_DEFERRED_EVIDENCE_CANDIDATE
REJECTED_WITH_REASON
```

### P0 Comparator

最简单、经济机制一致的基线，用来判断复杂规则是否真正增加价值。

### P1 Primary

当前最值得投入实现和第一轮回测资源的候选。

### P2 Secondary / Sensitivity

具有合理机制，但风险更高、实现更复杂、样本可能更少，或只改变一个关键变量的候选。P1 完成后按优先级研究。

### P3 Deferred Evidence Candidate

先记录数据，不进入当前硬触发，例如 Volume Profile、OI、L2、订单流或复杂退出逻辑。数据积累后再判断是否升级。

### Rejected

必须保存拒绝原因、证据和未来重新开启的条件。

候选不得静默消失。每个候选必须有：

```text
candidate_id
priority
mechanism
why_now_or_later
required_data
implementation_cost
promotion_condition
rejection_or_defer_reason
```

---

## 5. Plain-Language Baseline

在公式和参数之前必须解释：

```text
CURRENT_SYSTEM
INTENDED_BUT_NOT_LIVE
HUMAN_REFERENCE
MAIN_GAP
CURRENT_RESEARCH_DECISION
```

禁止在交易含义没有被理解时直接进入工程对象、代码或复杂公式。

---

## 6. 人工经验的使用方式

人工经验是高价值研究输入，但不是自动权威。

```text
TRADER_OBSERVATION
→ OBSERVABLE_FIELDS
→ CAUSAL_DECISION_TIME
→ MATHEMATICAL_RULE
→ COMPARATOR_OR_QUALITY_LABEL
→ FALSIFIABLE_RESULT
```

人工规则可以：

- 成为主候选；
- 成为保守 comparator；
- 成为质量标签；
- 成为失败反例；
- 被数据否定。

系统目标是利用一致计算、更多数据和完整路径证据争取优于人工，而不是复制人工或堆叠指标。

---

## 7. 可观察事实优先

策略只依赖能够在决策时观察和复现的事实：

- 价格带；
- 突破、收回、带外接受；
- 波动压缩与扩张；
- K 线和高低点结构；
- 成交量、OI、订单流和深度；
- 前方结构空间；
- 后续价格路径。

不要求证明由谁推动价格。参与者叙事只能用于解释机制，不能成为无法验证的硬触发。

---

## 8. 外部研究方式

默认跨市场检索：

- 高流动性加密永续；
- 黄金、原油和其他商品期货；
- 美股股指期货；
- 外汇；
- 高流动性股票和其他成熟订单簿市场。

优先级：

```text
OFFICIAL_EXCHANGE_OR_API_DOCS
→ PEER_REVIEWED_MICROSTRUCTURE_OR_MARKET_RESEARCH
→ HIGH_QUALITY_WORKING_PAPERS
→ MATURE_OPEN_SOURCE_IMPLEMENTATIONS
→ REPRODUCIBLE_STRATEGY_CODE
→ COMMUNITY_AND_TRADER_RULES
```

固定原则：

```text
CROSS_MARKET_MECHANISM_REUSE = YES
DIRECT_PARAMETER_COPY = NO
PUBLIC_BACKTEST_RESULT_AS_PRODUCTION_AUTHORITY = NO
```

每个来源必须记录：证据等级、可复用机制、不可迁移部分、失败条件和本项目用途。

---

## 9. 共同市场对象优先

先研究多个 Setup 共用的市场对象和事件，再定义策略路由。

```text
COMMON_OBJECT
→ COMMON_EVENT
→ OBSERVED_STATE
→ SETUP_OR_MODE_ROUTING
```

新增 Setup 前必须证明存在新的经济机制；否则优先作为已有 Setup 的 mode、quality label、state 或 comparator。

---

## 10. 参数纪律

第一轮必须有限，但不固定候选数量。要求：

- P1 只包含当前决策真正需要的最少候选；
- P2/P3 完整保留并排序；
- 一个 sensitivity 候选原则上只改变一个关键变量；
- 所有参数标记为可测试假设，不称为最优值；
- 参数必须按 ATR、结构宽度、成本或时间进行标准化，避免永久硬编码 ETH 美元值；
- 第一轮结果不得触发无限参数网格。

---

## 11. 入场和退出分层

当当前问题是信号和入场质量时：

```text
ENTRY_FIRST
+ INITIAL_STRUCTURAL_STOP
+ PLANNED_RISK
+ REFERENCE_EXIT_INFORMATION
+ SHADOW_EXIT_EVIDENCE
```

当前可以回测和记录固定 R、结构目标、MFE/MAE、浮盈回吐、简单结构移动止损和无进展退出；实时动态退出、交易所订单管理和人工确认执行属于后续产品与工程工作包。

---

## 12. 进入正式回测前的强制输出

数量可随任务调整，但至少必须包括：

1. 日内交易目标和例外；
2. 简单语言策略地图；
3. 当前系统与目标差距；
4. 已收敛研究问题集合；
5. 外部证据矩阵；
6. 可观察字段和决策时点；
7. 共同市场对象与事件模型；
8. P0/P1/P2/P3/Rejected 候选队列；
9. 第一轮参数包；
10. 回测数据、成本、路径和无未来数据合同；
11. 影子退出评估字段；
12. 当前、延期和禁止范围。

完成后才进入 `STRATEGY_RESEARCH_AND_BACKTEST_OPERATING_STANDARD_V1`。

---

## 13. 默认未来行为

后续任何新策略研究必须先读取本文件，并按以下顺序工作：

```text
INTRADAY_OBJECTIVE
→ PLAIN_LANGUAGE_BASELINE
→ HUMAN_HYPOTHESES
→ OBSERVABLE_MODEL
→ CROSS_MARKET_EVIDENCE
→ CONVERGENCE_GATE
→ PRIORITIZED_CANDIDATES
→ PRE_BACKTEST_FREEZE
→ FORMAL_BACKTEST
```
