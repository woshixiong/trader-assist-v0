# Strategy Research Discovery and Convergence Playbook V1

**记录 ID：** `TA-STRATEGY-RESEARCH-DISCOVERY-CONVERGENCE-PLAYBOOK-2026-08-02-V1`  
**日期：** `2026-08-02`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `MANDATORY FUTURE RESEARCH METHOD / NON-EXECUTABLE / NON-AUTHORIZING`  
**适用范围：** 后续所有 Setup、Scanner、市场状态、入场、止损、止盈、持仓管理和策略参数研究。  
**关系：** 本文是 `STRATEGY_RESEARCH_AND_BACKTEST_OPERATING_STANDARD_V1_2026-08-01.md` 之前的“第 0 阶段”。本文负责把研究问题发现并收敛；Operating Standard 负责把已收敛候选进行可复现回测、登记、稳健性验证和晋级裁决。  
**权限边界：** 本文不授权代码修改、回测执行、依赖安装、工程派发、部署、账户访问、交易所写入或自动交易。

---

## 1. 目的

本 Playbook 来自 First Launch 三 Setup、Scanner、价格带、突破、Sweep、Range、止损和影子退出的多轮研究讨论。

它解决以下低效率问题：

- 在没有确认真实交易目标前就开始写量化规则；
- 把人工经验直接当作最终策略，或反过来完全忽略人工经验；
- 因解释“谁推动价格”而偏离可交易价格行为；
- 只搜索 ETH 或单一市场，错过成熟跨市场研究；
- 把外部市场参数直接复制到本系统；
- 先给出工程方案，后发现策略目标没有研究清楚；
- 一次讨论扩展过多问题，无法收敛；
- 用术语和参数堆砌，导致产品目标和策略含义难以理解；
- 在研究尚未收敛时过早冻结合同或安排开发；
- 为追求完美而无限增加指标、回测和基础设施。

以后每个策略研究默认按以下流程推进：

```text
REAL TRADING OBJECTIVE
→ CURRENT SYSTEM IN PLAIN LANGUAGE
→ HUMAN OBSERVATION AS HYPOTHESIS
→ OBSERVABLE MARKET OBJECTS AND STATES
→ EXTERNAL EVIDENCE ACROSS MATURE MARKETS
→ COMMON EVENT MODEL
→ FINITE CANDIDATE METHODS
→ FIRST-ROUND PARAMETER PACKET
→ FORMAL BACKTEST OPERATING STANDARD
→ PRODUCT / ENGINEERING HANDOFF
```

---

## 2. 第一原则

### 2.1 先确认系统当前阶段的真实目标

同一策略在不同阶段使用不同优化目标。

必须先回答：

```text
当前阶段是：
- 发现机会？
- 产生足够测试样本？
- 人工辅助交易？
- 半自动执行？
- 自动交易？
```

例如 First Launch 的目标是：

```text
GENERATE_ENOUGH_REAL_TEST_SAMPLES
+ HUMAN_FINAL_FILTER
+ MANUAL_EXECUTION
+ COMPLETE_EVIDENCE
```

因此不能错误地以“尽量减少所有误报”为首要目标，把 Scanner 和 Setup 设计得过于保守。

### 2.2 策略研究只关注可观察、可交易事实

研究重点：

- 价格带；
- 突破、收回和带外接受；
- 波动压缩与扩张；
- K 线和高低点结构；
- 成交量、OI、订单流和深度；
- 前方结构空间；
- 价格路径和结果。

不需要证明：

- 是机构、大资金、散户还是算法推动；
- 某市场是否正在“吸筹”或“派发”；
- 市场参与者的真实主观意图。

主体和意图可以帮助形成经济解释，但不能成为无法验证的信号输入。

```text
OBSERVABLE_BEHAVIOR > UNVERIFIABLE_ACTOR_NARRATIVE
```

### 2.3 人类经验是高价值假设，不是自动权威

交易员经验应被保留，因为它通常包含：

- 位置；
- 市场状态；
- 形态质量；
- 执行时机；
- 风险和失败反例。

但必须翻译成：

```text
可观察字段
+ 明确数学定义
+ 可复现决策时点
+ 对照候选
+ 可证伪结果
```

例如人工 Pin Bar 规则应成为重要 comparator 或质量标签，而不是未经比较就成为唯一生产策略。

### 2.4 系统应争取优于人工，但不能凭空创造复杂度

系统优势应来自：

- 同时观察更多市场；
- 使用更一致的规则；
- 记录人工无法持续记录的路径；
- 结合价格、成交量、OI、深度和时间；
- 比较多个确认模式；
- 保存失败样本；
- 计算成本后的长期期望值。

系统不应通过堆叠大量未经验证的指标来假装优于人工。

---

## 3. 每次研究开始前必须建立 Plain-Language Baseline

在公式和参数之前，必须用普通语言回答：

1. 当前生产策略到底在做什么；
2. 已经写入合同但没有上线的版本是什么；
3. 当前运行缺陷是什么；
4. 人工交易方法是什么；
5. 二者相同和不同在哪里；
6. 当前研究要解决哪个具体缺口。

最低输出模板：

```text
CURRENT_SYSTEM:
一句话说明当前系统如何找机会、如何确认、何时入场。

INTENDED_BUT_NOT_LIVE:
一句话说明尚未上线的候选版本。

HUMAN_REFERENCE:
一句话说明交易员当前怎么做。

MAIN_GAP:
一句话说明系统与目标策略之间最重要的差距。
```

禁止在用户尚未理解策略含义时，直接使用大量变量、代码对象和工程术语。

---

## 4. 把截图和人工观察转化为研究对象

截图和交易经验用于发现问题，不直接用于证明结论。

处理顺序：

```text
SCREENSHOT / OBSERVATION
→ DESCRIBE WHAT IS VISIBLE
→ SEPARATE INFERENCE
→ IDENTIFY REPEATABLE EVENT
→ DEFINE REQUIRED DATA
→ CREATE TESTABLE HYPOTHESIS
```

必须区分：

```text
VISIBLE FACT
例如：价格在区间边界外收盘，随后回踩并延续。

TRADER INTERPRETATION
例如：这里可能发生止损级联。

SYSTEM HYPOTHESIS
例如：压缩后的带外位移比普通突破具有更高延续率。
```

单张截图不能确定 ATR、成交量基线、实时盘口或统计优势；需要对应数据和更多事件验证。

---

## 5. 先定义共同市场对象，再定义 Setup

未来优先寻找多个 Setup 共用的底层对象，避免每个策略单独发明一套边界和状态。

本轮形成的范式是：

```text
COMMON MARKET OBJECT
= KEY PRICE ZONE

COMMON EVENT
= PRICE ATTACKS OR LEAVES THE ZONE

STATE BRANCHES
= RECLAIMED_INSIDE
| ACCEPTED_OUTSIDE_ORDERLY
| ACCEPTED_OUTSIDE_DISPLACEMENT
| AMBIGUOUS_TWO_SIDED

ROUTING
= SWEEP
| STANDARD BREAKOUT
| FAST BREAKOUT
| WATCH / NO ACTION
```

以后研究新策略时优先问：

- 它是否真的是新经济机制；
- 还是已有共同事件的另一种状态或确认方式；
- 能否作为现有 Setup 的 mode、quality label 或 comparator；
- 是否真的需要第四个 Setup。

```text
NEW_SETUP_ONLY_IF_NEW_ECONOMIC_MECHANISM
```

---

## 6. 价格“线”优先升级为价格“带”进行研究

人类通常交易支撑/阻力区域，而不是一个无限精确价格。

未来价格带研究优先考虑：

- 多次独立反应；
- 反应价格聚类；
- 新鲜度；
- 时间接受度；
- Volume Profile 的 HVN、LVN、POC 和价值区边缘；
- 区域宽度相对 ATR；
- 下一关键区域；
- 压缩是否发生在区域附近。

输出应至少是：

```text
ZONE_LOW
ZONE_HIGH
ZONE_CENTER
ZONE_WIDTH
ZONE_QUALITY
NEXT_ZONE
```

Volume Profile 表示历史成交接受度，不等于当前 L2 挂单深度。两者可以组合研究，但不能混为同一变量。

---

## 7. 外部研究必须跨市场寻找成熟机制

研究不得只限于当前交易资产。

优先搜索：

- 高流动性加密永续；
- 黄金、原油和商品期货；
- 美股股指期货；
- 外汇；
- 高流动性股票；
- 其他具有标准订单簿和成熟微观结构的衍生品。

原因：

```text
MECHANISM MAY TRANSFER
PARAMETERS MAY NOT TRANSFER
```

可跨市场借鉴：

- 支撑阻力和订单聚集；
- stop cascade；
- intraday momentum/reversal；
- opening range breakout；
- volatility compression/expansion；
- market/volume profile；
- order-flow imbalance；
- trend following and trailing protection；
- mean reversion and range execution。

不得直接迁移：

- 固定 ATR 阈值；
- 固定时间窗口；
- 固定成交量倍数；
- 固定盈亏比；
- 其他市场的公开收益结果。

---

## 8. 外部资料和工具的使用顺序

### 8.1 信息源优先级

```text
1. 官方交易所/API/市场规则文档
2. 成熟同行评议微观结构和市场研究
3. 高质量工作论文和大样本研究
4. 官方或成熟开源框架
5. 可复现开源策略实现
6. 社区规则、交易员经验和教学资料
```

每个结论必须标记：

```text
SOURCE_DERIVED
MODEL_INFERENCE
TRADER_EXPERIENCE
PROJECT_DECISION
```

### 8.2 官方工具和数据

用于确认：

- 可以获得哪些字段；
- 数据历史长度；
- candle、trade、BBO、L2、OI、funding 的语义；
- rate limit；
- 市场身份和精度；
- 实时与历史边界。

不能因为理论上需要某字段，就假定当前系统能够低成本取得。

### 8.3 学术和成熟市场研究

用于：

- 经济机制；
- 失败机制；
- 应记录的变量；
- comparator；
- 稳健性问题。

不用于直接复制参数。

### 8.4 开源框架和策略代码

优先借鉴：

- market discovery / pairlist；
- data pipeline；
- causal replay；
- lookahead analysis；
- indicator warmup；
- simple baseline；
- fixture 和测试结构；
- experiment/report schema。

不应未经工程评估将整个框架引入关键路径。

### 8.5 GitHub 作为项目长期记忆

GitHub 中必须保留：

- 外部研究原文或摘要；
- 采用/不采用裁决；
- 当前候选参数；
- 被替代版本；
- 未解决问题；
- 产品和工程边界；
- 后续研究计划。

任何重要策略结论不得只留在聊天记录中。

---

## 9. 讨论必须收敛到最多三个核心课题

初始讨论可以发散，但进入研究执行前必须压缩为最多三个主问题。

推荐结构：

```text
QUESTION_A = COMMON MARKET OBJECT
例如：关键价格带怎样定义？

QUESTION_B = MARKET STATE / EVENT CLASSIFICATION
例如：价格离开价格带后属于收回、平稳接受还是猛烈位移？

QUESTION_C = ACTION
例如：每种状态如何入场、止损和评估？
```

次要问题进入：

```text
SHADOW_FEATURE
SENSITIVITY
POST_FIRST_LAUNCH_RESEARCH
DEFERRED
```

不得让每个合理想法都进入当前主候选。

---

## 10. 把一个策略拆成“环境—事件—确认—风险—结果”

每个候选必须按相同结构描述：

```text
ENVIRONMENT
→ MARKET OBJECT
→ EVENT TRIGGER
→ CONFIRMATION MODE
→ ENTRY ZONE
→ INITIAL STRUCTURAL STOP
→ CHASE LIMIT
→ TARGET / REFERENCE SPACE
→ INVALIDATION
→ EXPIRY
→ SHADOW OUTCOME
```

必须区分：

- 环境只决定是否允许参加判断；
- 事件说明市场发生了什么；
- 确认决定何时行动；
- 初始止损决定计划亏损；
- 止盈参考和动态退出是后续价格路径研究。

---

## 11. 同一经济机制允许有限多种确认模式

不能因入场方式不同就自动定义新 Setup。

例如 Breakout 可以有：

```text
DISPLACEMENT_FAST
MICRO_CONFIRMED_FAST
STANDARD_PULLBACK
PIN_BAR_CONSERVATIVE_REFERENCE
```

这些模式必须：

- 使用同一个已确认的关键价格带；
- 共享同一突破事件身份；
- 独立统计；
- 不重复发布同一事件；
- 不用一个模式的盈利掩盖另一个模式的亏损。

Sweep、Range 也适用相同原则。

---

## 12. 第一轮参数必须是有限、可解释候选

第一轮禁止大规模参数网格。

推荐纪律：

```text
ONE PRIMARY CANDIDATE
+ AT MOST ONE ECONOMICALLY EXPLAINED SENSITIVITY
PER IMPORTANT VARIABLE FAMILY
```

参数来源顺序：

1. 当前生产语义；
2. 人工经验转译；
3. 外部机制建议；
4. 数据尺度标准化；
5. 对称性和工程可实现性。

优先使用：

- ATR 标准化距离；
- 横截面分位数；
- 相对成交量；
- 方向效率；
- 结构反应次数；
- 闭合 K 线数量；
- 成本后 R。

避免永久硬编码单一资产的美元距离。

所有首轮参数必须标记：

```text
TESTABLE_HYPOTHESIS
NOT_OPTIMAL
NOT_PRODUCTION_PROVEN
```

---

## 13. 入场优先，退出分层研究

当主要问题是信号稀缺或入场质量时：

```text
ENTRY RESEARCH FIRST
```

当前阶段优先冻结：

- Entry Zone；
- Initial Structural Stop；
- Planned Risk；
- Chase Limit。

同时保留参考退出和完整路径证据：

- 1R、1.5R、2R；
- 下一结构区；
- MFE/MAE；
- 浮盈回吐；
- 时间到结果；
- 人工实际退出。

实时动态退出引擎、止损调整和自动止盈属于后续独立工作包。不能因未来价值高而阻塞当前入场研究。

---

## 14. 研究对话的反驳和纠错规则

助手不能只肯定用户观点。

每个关键观点应分别判断：

```text
CORRECT / SUPPORTED
PLAUSIBLE_BUT_UNPROVEN
PARTIALLY_CORRECT
OVERSTATED
INCORRECT_OR_MISDEFINED
```

纠错时必须：

1. 先保留有价值的交易机制；
2. 指出过强或不可验证的部分；
3. 转换成可观察假设；
4. 给出如何验证；
5. 不把讨论拖入对交易决策没有价值的因果争论。

例如：

```text
“机构推动”
→ 不验证主体
→ 研究同方向大额订单、深度消耗、位移和级联样价格行为
```

---

## 15. 常见研究失败模式

以后必须主动检查：

### 15.1 优化目标错位

把人工 First Launch 错当成自动交易，导致过度保守、信号不足。

### 15.2 资产类别先验过强

在没有结果前默认排除股票、商品、指数或山寨币。资产类别应优先作为标签和归因变量。

### 15.3 单一价格线错误

用最近高低点替代人类真正观察的支撑/阻力带。

### 15.4 总成交量解释过度

把放量直接解释为“机构吸收”；把 Volume Profile 直接解释为实时 L2 深度。

### 15.5 FAST 与 Sweep 概念混淆

两者可能从同一价格带攻击开始，但结果分别是带外接受和收回带内。

### 15.6 只研究 ETH

忽略黄金、原油、股指、外汇等成熟市场的机制证据。

### 15.7 过早工程化

策略定义尚未收敛就开始开发，造成后续返工。

### 15.8 研究无限膨胀

把所有有价值的长期能力都加入当前发布，破坏最短关键路径。

### 15.9 只报告最终盈利

不保存 raw candidate、事件路径、未通知候选、T/S/R、MFE/MAE 和失败原因。

### 15.10 反复在同一数据上调参

没有冻结样本外数据，形成回测过拟合。

---

## 16. 每轮讨论必须形成的八项输出

在进入正式回测前，至少输出：

1. **Plain-Language Strategy Map**  
   当前、人工参考和目标候选各自是什么。

2. **Three Focus Questions**  
   最多三个需要解决的核心研究问题。

3. **External Evidence Matrix**  
   来源、市场、机制、限制、采用方式。

4. **Observable Feature Dictionary**  
   每个概念对应哪些可以获得的数据和因果定义。

5. **Common Event Model**  
   共用市场对象、事件状态和 Setup 路由。

6. **Finite Candidate Set**  
   主候选、有限对照和明确延期项。

7. **First-Round Parameter Packet**  
   参数、经济解释、失效条件和版本。

8. **Scope and Handoff Boundary**  
   当前研究、回测、产品和工程分别做什么；什么不做。

缺少上述任一项时，不应开始正式开发。

---

## 17. 高效率讨论模板

以后启动新策略研究时，第一轮直接使用以下问题：

```text
A. 交易目标
- 主要周期是什么？
- 想抓哪类行情？
- 人工、半自动还是自动？
- 需要高召回还是高精度？

B. 当前事实
- 现有系统实际上做什么？
- 已知缺陷是什么？
- 当前为什么无法满足目标？

C. 人工经验
- 交易员具体观察哪些位置、形态和路径？
- 哪些是硬规则？
- 哪些只是经验偏好？
- 最担心的失败场景是什么？

D. 市场对象
- 关键价格带、趋势、区间或事件怎样表示？
- 哪些 Setup 可以共享同一对象？

E. 外部证据
- 哪些成熟市场存在同类机制？
- 有哪些同行评议、官方文档和成熟实现？
- 哪些只能借鉴机制，不能复制参数？

F. 候选
- 最少几个候选能够回答问题？
- 最简单 comparator 是什么？
- 哪些内容延后？

G. 结果
- 用什么指标证明候选更好？
- 需要保存哪些失败样本和路径？
```

这套模板应替代无结构的自由讨论。

---

## 18. 研究与工程的停止门

### 18.1 研究尚未收敛时

以下任一成立，不得派发工程：

- 用户无法用普通语言解释目标策略；
- 当前系统和目标策略差异不清楚；
- 关键市场对象未定义；
- 研究问题超过三个且没有优先级；
- 候选参数无限增长；
- 外部证据只来自单一社区观点；
- 没有 simple comparator；
- 没有明确失败条件。

### 18.2 工程范围可能膨胀时

必须拆分：

```text
CURRENT_RELEASE_REQUIRED
CURRENT_RELEASE_ONLY_IF_NEAR_ZERO_COST
POST_FIRST_LAUNCH_RESEARCH
FUTURE_V0
```

策略研究价值高，不等于必须立即开发全部研究基础设施。

---

## 19. 与正式回测标准的衔接

本 Playbook 完成后，输出交给：

`STRATEGY_RESEARCH_AND_BACKTEST_OPERATING_STANDARD_V1_2026-08-01.md`

后者执行：

- Research Card；
- Trial Registry；
- point-in-time 数据合同；
- simple comparator；
- closed-candle/no-lookahead；
- 成本和延迟；
- deterministic test；
- 最小筛查；
- 样本外验证；
- Shadow evidence；
- GO / REVISE / INCONCLUSIVE / REJECT。

因此完整体系是：

```text
DISCOVER AND CONVERGE
→ REGISTER AND BACKTEST
→ SHADOW AND HUMAN REVIEW
→ VERSIONED PROMOTION
```

---

## 20. 默认治理结论

```text
THIS_PLAYBOOK_IS_DEFAULT_FIRST_READ = YES
APPLIES_TO_ALL_FUTURE_STRATEGY_RESEARCH = YES
PLAIN_LANGUAGE_BEFORE_PARAMETERS = REQUIRED
HUMAN_EXPERIENCE_AS_TESTABLE_HYPOTHESIS = REQUIRED
CROSS_MARKET_EXTERNAL_RESEARCH = REQUIRED
OBSERVABLE_BEHAVIOR_OVER_ACTOR_NARRATIVE = REQUIRED
MAX_CORE_RESEARCH_QUESTIONS = 3
COMMON_EVENT_MODEL_BEFORE_NEW_SETUP = REQUIRED
FINITE_CANDIDATES_BEFORE_BACKTEST = REQUIRED
ENGINEERING_BEFORE_RESEARCH_FREEZE = PROHIBITED
CURRENT_SCOPE_EXPANSION_BY_LONG_TERM_RESEARCH = PROHIBITED
GITHUB_AS_DURABLE_PROJECT_MEMORY = REQUIRED
```
