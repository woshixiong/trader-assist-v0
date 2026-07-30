# First Launch 三 Setup 研究工具、角色、资源与新窗口交接

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-RESEARCH-TOOL-AND-HANDOFF-2026-07-30-R1`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**状态：** `STRATEGY RESEARCH GOVERNANCE / NON-EXECUTABLE`

本文不授权生产修改、部署、重启、账户访问、签名、交易所写入、自动下单、Mark Ready 或 merge。

---

## 1. 本轮任务核心

本轮不是发明策略，也不是寻找历史收益最高的组合。

本轮只做：

```text
成熟主观交易机制
→ 因果量化合同
→ 成熟开源引擎中的联合回测
→ 最小策略实现
→ 植入 First Launch
```

三个 Setup：

1. `SWEEP_RECLAIM`
2. `BREAKOUT_RETEST`
3. `RANGE_EDGE_REJECTION`

FAST 与 STANDARD 均保留在研究和回测中，最终是否按 Setup 分别保留，由证据决定。

---

## 2. 研究工具裁决

### 2.1 不自研回测平台

本轮禁止自建完整 backtesting engine、broker simulator、通用研究平台或参数优化系统。

### 2.2 主回测工具：Backtesting.py

推荐使用成熟开源框架 `Backtesting.py` 作为本轮主要事件回放与交易结果模拟引擎。

选择依据：

- 支持 event-based `Strategy.next()`，每根新 bar 到来时执行；
- 支持单资产 OHLCV，适合当前 ETH-only；
- 支持从低周期向高周期重采样，适合 5m + 15m；
- 支持 commission、spread、margin、trade-on-close；
- 支持 stop loss、take profit、订单与交易标签；
- 输出交易、收益、回撤和交互图表；
- API 较小，接入成本低；
- 不需要把 First Launch 重构成新的交易框架。

官方输入：

- https://kernc.github.io/backtesting.py/
- https://kernc.github.io/backtesting.py/doc/backtesting/
- https://kernc.github.io/backtesting.py/doc/examples/Multiple%20Time%20Frames.html

### 2.3 Freqtrade 的角色

Freqtrade 不作为本轮唯一的权威回放引擎，但可以承担：

1. Hyperliquid / 其他支持交易所的 OHLCV 数据下载与格式转换；
2. 简单独立基准策略；
3. 费用和结果交叉检查；
4. 可选的 lookahead-analysis / recursive-analysis；
5. 导出信号和交易作二次分析。

不将 Freqtrade 作为唯一权威引擎的原因：

- Freqtrade 的策略指标与入场信号通常先在完整 DataFrame 上计算；
- 当前 First Launch 存在有状态的 `PREPARE → later confirmation`；
- 本轮必须枚举同一 K 线全部 raw candidates，而不是只输出最终 entry；
- 必须保持当前生产策略的精确语义和逐 bar 因果状态；
- 将全部逻辑重写成 Freqtrade DataFrame 规则可能扩大翻译误差。

官方输入：

- https://www.freqtrade.io/en/stable/backtesting/
- https://docs.freqtrade.io/en/stable/lookahead-analysis/
- https://docs.freqtrade.io/en/stable/recursive-analysis/
- https://docs.freqtrade.io/en/stable/advanced-backtesting/
- https://docs.freqtrade.io/en/latest/exchanges/

### 2.4 不采用的主路线

本轮不采用 NautilusTrader、QuantConnect LEAN 或完整 Backtrader 集成作为主路线。

这些框架具备成熟事件驱动、组合、订单、风险和 live/backtest 能力，但对当前 1–2 工作日、ETH-only、人类执行、已有生产架构的任务而言接入范围过大。

它们保留为 V0 自动交易或多策略阶段候选。

### 2.5 必须编写的内容不是“造工具”

仍需要一个非常薄的策略适配层。任何通用引擎都不知道以下 Trader Assist 专属语义：

- `StrategySnapshot`；
- `SWEEP_RECLAIM / BREAKOUT_RETEST / RANGE_EDGE_REJECTION`；
- FAST / STANDARD；
- `PREPARE` 和后续确认；
- raw candidate enumeration；
- market-event deduplication；
- Chase Limit；
- signal expiry；
- manual response delay；
- `TradePlan` 的 1R / 2R；
- 三 Setup 的互斥和交互政策。

因此只允许编写：

```text
BACKTESTING_PY_ADAPTER
RAW_CANDIDATE_RECORDER
MARKET_EVENT_GROUPER
RESULT_EXPORT_MAPPING
```

这些是策略对成熟引擎的适配，不是自研回测平台。

适配层必须：

- 独立于生产部署；
- 不修改 candle transport；
- 不修改数据库 Schema；
- 不增加服务；
- 不包含交易所写权限；
- 优先调用当前生产策略的纯函数和数据对象；
- 不复制出一套不同语义的策略实现。

---

## 3. 数据路线

### 3.1 Hyperliquid 精确场地数据

Hyperliquid `candleSnapshot` 只提供最近 5000 根 K 线。

用途：

- 精确场地、成交量和时间语义校验；
- 最近市场状态检查；
- First Launch 候选的最终 venue sanity check。

限制：

- 5000 根 5m 约 17.4 天；
- 不足以稳定覆盖所有 regime 和足够独立事件。

官方输入：

- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- https://docs.freqtrade.io/en/latest/exchanges/

### 3.2 长历史代理数据

为了不建设历史数据工程，推荐使用成熟交易所的 ETH perpetual OHLCV 作为长期代理，例如 Binance 或 Bybit，并通过 Freqtrade 下载。

用途：

- 覆盖趋势、震荡、过渡、极端波动等更多 regime；
- 审计三个交易机制和 FAST / STANDARD；
- 不用于声称 Hyperliquid 精确收益。

最终报告必须分开：

```text
LONG_HISTORY_PROXY_EVIDENCE
HYPERLIQUID_EXACT_RECENT_EVIDENCE
```

不得混成一个无来源区分的收益数字。

### 3.3 1m 数据

建议使用 1m 数据解决同一 5m bar 内 Stop 与 TP 的先后问题。

如缺少 1m：

- 标记 `AMBIGUOUS_PATH`；
- 使用保守 Stop-first；
- 单独报告其数量和收益影响。

---

## 4. 成本与现实执行默认值

除非用户提供实际账户费率，第一轮使用官方 Hyperliquid perps 基础费率的保守模型：

- taker：0.045% 每侧；
- maker：0.015% 每侧；
- 人类 First Launch 主场景优先按 taker 计算；
- maker 只作敏感性对照；
- funding 按持仓跨 funding 时段计算；
- 手工反应延迟预注册为 30 秒主场景，15 秒与 60 秒作敏感性对照。

官方输入：

- https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees
- https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding

这些默认值不需要账户密钥、钱包地址或交易权限。

---

## 5. 角色与职责

### 5.1 策略研究窗口

属于策略上层管理者，负责：

- 外部成熟研究；
- 三 Setup 的经济机制；
- 因果量化合同；
- FAST / STANDARD；
- regime / event 两层分类；
- 触发、失效、止损、目标和成本；
- 候选参数预注册；
- 回测问题和报告验收；
- 回测结果的策略解释；
- 向产品规划窗口提供策略输入。

不负责具体工程任务派发，不直接修改生产。

### 5.2 产品规划窗口

属于产品与策略上层管理者，负责：

- 策略与产品路线是否一致；
- 策略与框架之间的产品适配；
- 研究结果如何进入 First Launch / V0；
- 是否值得进入生产；
- 与工程优化窗口共同给出策略—框架对接的最终建议。

### 5.3 工程优化窗口

只负责：

- 开发路径；
- 技术路线；
- Backtesting.py / Freqtrade 与当前代码的接入方式；
- 最小修改范围；
- 技术风险和停止条件；
- 把策略合同转成可执行技术方案；
- 与产品规划窗口确认策略—框架对接。

不负责：

- 具体任务派发；
- 执行节奏控制；
- 擅自重写策略参数；
- 直接部署生产。

### 5.4 总控窗口

是唯一的具体任务派发者，负责：

- 接收策略研究、产品规划和工程优化的最终输入；
- 建立阶段、任务、分支和允许范围；
- 向 Codex CLI / Writer / Reviewer / CI / Deployment 窗口派发任务；
- 控制顺序、停止条件和变更权限；
- 汇总证据并提交最终裁决。

### 5.5 Codex CLI / 开发执行者

由总控窗口派发，负责：

- 安装或使用批准的开源工具；
- 编写最薄适配层；
- 获取和校验历史数据；
- 运行联合回测；
- 导出原始结果；
- 在获得 GO 后生成最小生产 patch。

### 5.6 独立 Reviewer

由总控窗口派发，负责：

- 因果性；
- v0.1 parity；
- 数据时间对齐；
- raw candidate 完整性；
- FAST / STANDARD 实际触发；
- 同 K 线和跨 K 线交互；
- 成本模型；
- 结果可重复性；
- 代码、数据和报告一致性。

---

## 6. 当前资源是否齐全

### 6.1 已具备

- First Launch 当前生产 exact SHA；
- 当前策略代码和测试；
- 三 Setup 研究方向；
- FAST / STANDARD 决策；
- GitHub 治理基线；
- 当前 5m / 15m 数据接口；
- Hyperliquid 官方近期 K 线；
- 开源回测框架选择；
- 当前风险配置和 1R / 2R TradePlan；
- 无生产写权限的研究边界。

### 6.2 仍需确认但不阻塞策略研究

1. 是否允许使用 Binance / Bybit ETH perpetual 长历史作为代理数据；
2. 用户真实手工反应延迟是否接近 15 / 30 / 60 秒；
3. 用户实际 Hyperliquid fee tier，如不提供则使用官方基础 taker 费率；
4. 是否已有长期 ETH 1m / 5m / 15m 数据文件；没有则由总控安排 Freqtrade 下载代理数据，并下载 Hyperliquid 最近 5000 根。

当前不需要用户提供：

- API key；
- 钱包地址；
- 私钥；
- 交易账户访问；
- 生产服务器写权限。

---

## 7. 两个前置工作包

### 工作包 A：三 Setup 策略研究与量化合同

执行者：新策略研究窗口。  
协作：产品规划窗口。  
技术咨询：工程优化窗口。  
任务派发：不涉及执行派发；研究结论完成后交给总控。

输出：

- 三 Setup 完整合同；
- FAST / STANDARD 合同；
- environment / event 分类；
- 外部研究证据矩阵；
- 一个主候选和最多一个敏感性对照；
- 反例和归属矩阵；
- 联合回测输入合同。

### 工作包 B：开源工具适配与联合回测

执行者：由总控窗口派发的 Codex / 开发执行者。  
技术路线：工程优化窗口负责。  
产品与策略适配：产品规划窗口 + 策略研究窗口。  
验收：独立 Reviewer。  
最终派发与裁决：总控窗口。

工具：

- Backtesting.py：主要事件回放；
- Freqtrade：数据下载、可选基准和偏差检查；
- 不自研 backtesting engine。

输出：

```text
V0_1_EXACT_BASELINE
V0_1_INSTRUMENTED_PARITY
SWEEP_CANDIDATE
BREAKOUT_CANDIDATE
RANGE_FAST_STANDARD
ALL_RAW_CANDIDATES_NO_ARBITRATION
COMBINED_EXACT_POLICY
```

---

## 8. 后续完整计划

### Stage 0 — 本文存档

完成。

### Stage 1 — 新策略研究窗口

完成工作包 A，不修改生产，不派发工程任务。

### Stage 2 — 产品规划与工程优化联合审查

- 产品规划确认产品价值和 First Launch / V0 定位；
- 工程优化确认 Backtesting.py 薄适配路径、数据路径和最小实现范围；
- 两者共同输出给总控的最终建议。

### Stage 3 — 总控窗口建立执行包

总控派发：

1. 数据准备；
2. 开源工具安装与隔离环境；
3. STANDARD progression 核验；
4. Backtesting.py 薄适配；
5. v0.1 parity；
6. 联合回测；
7. 独立审查。

### Stage 4 — 策略研究窗口审阅结果

输出：

- 策略合同是否成立；
- FAST / STANDARD 的每 Setup 建议；
- 三 Setup 是否清晰归属；
- 成本后是否可行；
- `GO / REVISE / INCONCLUSIVE / REJECT`。

### Stage 5 — 后续生产工作

只有 GO 后才讨论：

- 最终生产参数；
- 最小 strategy-only patch；
- v0.2 版本；
- 测试；
- CI；
- 部署；
- 回滚。

---

## 9. 新策略研究窗口一键提示词

```text
ROLE:
FIRST_LAUNCH_THREE_SETUP_STRATEGY_RESEARCH_LEAD

MODEL:
GPT-5.6 THINKING

PROJECT:
TRADER_ASSIST_V0_FIRST_LAUNCH_POST_LAUNCH_THREE_SETUP_QUANTIFICATION

REPOSITORY:
woshixiong/trader-assist-v0

MODE:
STRICT_READ_ONLY_STRATEGY_RESEARCH
NO_PRODUCTION_MUTATION
NO_TASK_DISPATCH
NO_BACKTEST_EXECUTION_YET

CURRENT_PRODUCTION_BASELINE:
CODE_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
STRATEGY_VERSION = ETH-LDAR-v0.1

CORE_OBJECTIVE:
本轮不是发明策略，也不是寻找历史最高收益组合。
本轮要把三种成熟主观交易机制转换为因果、可重复、可回测、可植入 First Launch 的量化合同：

1. SWEEP_RECLAIM
2. BREAKOUT_RETEST
3. RANGE_EDGE_REJECTION

FAST 与 STANDARD 对所有适用 Setup 均保留在研究中。回测后再决定各 Setup 是否保留 FAST、STANDARD 或两者。

MANDATORY_GITHUB_INPUTS:
读取 Draft PR #52，Branch：
agent/v0-strategy-predevelopment-analysis-r1

优先读取：

1. governance/V0_STRATEGY_PREDEVELOPMENT_ANALYSIS_AND_DECISION_BASELINE_2026-07-28.md
2. governance/FIRST_LAUNCH_RANGE_STRATEGY_AND_COMBINED_BACKTEST_DECISION_2026-07-30.md
3. governance/FIRST_LAUNCH_RANGE_STRATEGY_ENGINEERING_OPTIMIZATION_HANDOFF_2026-07-30.md
4. governance/FIRST_LAUNCH_THIRD_SETUP_STRICT_STRATEGY_AUDIT_AND_INTERACTION_REPLAY_GATE_2026-07-30.md
5. governance/FIRST_LAUNCH_THREE_SETUP_UNIFIED_AUDIT_OPTIMIZATION_REPLAY_AND_ROLLBACK_PLAN_2026-07-30.md
6. governance/FIRST_LAUNCH_THREE_SETUP_48H_STRATEGY_FIRST_SCOPE_ADDENDUM_2026-07-30.md
7. governance/FIRST_LAUNCH_THREE_SETUP_RESEARCH_TOOL_SELECTION_ROLES_RESOURCES_AND_WINDOW_HANDOFF_2026-07-30.md

ROLE_BOUNDARY:

- 你是策略研究上层管理者；
- 产品规划窗口是产品与策略上层管理者；
- 工程优化窗口只负责开发路径、技术路线和策略—框架对接建议；
- 总控窗口是唯一具体任务派发者；
- 不得向 Codex、Reviewer 或 Deployment 直接派发执行任务；
- 不得修改生产、部署、Mark Ready 或 merge。

RESEARCH_METHOD:

1. 使用成熟论文、官方文档、研报和高质量开源项目作为证据；
2. 外部资料用于经济机制、失败模式、量化方法和验证流程；
3. 不直接复制其他市场和周期的具体参数；
4. 对三个 Setup 使用同一严格模板；
5. 不从历史收益倒推规则；
6. 每个 Setup 只允许：
   - 当前 v0.1 exact baseline；
   - 一个主要候选；
   - 最多一个具有明确经济解释的敏感性对照；
7. 禁止大规模参数搜索和回测后反复调参。

TWO_LAYER_MODEL:

Layer A — Environment State:
- RANGE
- DIRECTIONAL_UP
- DIRECTIONAL_DOWN
- TRANSITION
- UNCERTAIN

Layer B — Event Outcome:
- SWEEP_RECLAIM
- BREAKOUT_RETEST
- RANGE_EDGE_REJECTION
- NO_ACTION

Environment 决定 eligibility；Event Outcome 决定最终 SetupFamily。

MANDATORY_CONTRACT_FIELDS_FOR_EACH_SETUP:

- ECONOMIC_HYPOTHESIS
- TARGET_ENVIRONMENT
- PROHIBITED_ENVIRONMENT
- LEVEL_DEFINITION
- LEVEL_QUALITY
- EVENT_TRIGGER
- FAST_CONFIRMATION
- STANDARD_PREPARE
- STANDARD_CONFIRMATION
- INVALIDATION
- EXPIRY
- ENTRY_ZONE
- CHASE_LIMIT
- STRUCTURAL_STOP
- TARGET_FEASIBILITY
- COST_MODEL
- FAILURE_MODE
- INTERACTION_POLICY

禁止使用未量化词：
明显、强势、靠近、有效、较大、正常回踩等。
必须转换为公式、边界或确定性判断。

FAST_STANDARD:

FAST = 初始闭合 K 线直接确认。
STANDARD = 初始 K 线进入 PREPARE，等待后续 1–3 根闭合 K 线确认。

必须分别定义和研究：
- FAST-only event；
- STANDARD-only event；
- 同一 market event 中的先后和重复；
- STANDARD 过滤的失败；
- STANDARD 因延迟产生的错失和追价；
- 两者 MAE、MFE、费用、回撤和连续亏损。

INTERACTION_RESEARCH:

不要预设三个 Setup 必然冲突，也不要预设绝不冲突。
重点判断：

- 同一关键边界在不同 Event Outcome 下的唯一归属；
- Sweep 与 Range 的 excursion boundary；
- Breakout 与 Range 的 close acceptance；
- Sweep 与 Breakout 的 reclaim / acceptance；
- 同 K 线重叠；
- 跨 K 线 PREPARE / active expiry；
- FAST / STANDARD 重复 market event；
- opposite candidates；
- transition regime。

RESEARCH_TOOL_DECISION:

本轮不自研 backtesting engine。

主工具：Backtesting.py
用途：逐 bar 事件回放、5m/15m、多空交易、费用、spread、SL/TP、统计和图表。

辅助工具：Freqtrade
用途：Hyperliquid / 代理交易所数据下载、简单基准、信号导出、可选 lookahead-analysis / recursive-analysis。

任何通用工具都不了解 Trader Assist 的 Setup、FAST/STANDARD、PREPARE、raw candidates 和 market events，因此允许一个最薄适配层，但不允许建设新回测平台。

DATA_PLAN:

1. Hyperliquid 最近 5000 根：exact-venue recent evidence；
2. Binance 或 Bybit ETH perpetual 长历史：regime-coverage proxy evidence；
3. 两类证据必须分开报告；
4. 建议使用 1m 数据解决同 5m 内 Stop / TP 路径；
5. 无 1m 时使用 AMBIGUOUS_PATH + Stop-first。

DEFAULT_COST_ASSUMPTIONS:

- Hyperliquid perps base taker fee = 0.045% per side；
- maker fee = 0.015% per side，只作敏感性；
- 人工执行主场景按 taker；
- response delay = 30s primary；15s / 60s sensitivity；
- funding 按实际跨 funding 时段处理。

FIRST_TWO_WORK_ITEMS:

WORK_ITEM_A:
THREE_SETUP_STRATEGY_CONTRACT_RESEARCH

完成三个 Setup 的经济机制、量化合同、FAST/STANDARD、失败模式、反例、交互矩阵和有限候选。

WORK_ITEM_B:
BACKTEST_INPUT_CONTRACT

定义：
- 数据要求；
- 时间语义；
- 成本模型；
- raw candidate schema；
- market event schema；
- 必跑回测模式；
- 报告 schema；
- Gate。

注意：本窗口不运行回测，不开发适配层，不派发任务。
完成研究后，将结果交给产品规划窗口和工程优化窗口联合审查，再由总控窗口派发实际执行。

MANDATORY_OUTPUT:

1. REVIEW_STATUS
2. EVIDENCE_SOURCE_MATRIX
3. THREE_SETUP_ECONOMIC_MODEL
4. ENVIRONMENT_STATE_CONTRACT
5. SWEEP_RECLAIM_FULL_CONTRACT
6. BREAKOUT_RETEST_FULL_CONTRACT
7. RANGE_EDGE_REJECTION_FULL_CONTRACT
8. FAST_STANDARD_PER_SETUP_CONTRACT
9. THREE_SETUP_BOUNDARY_AND_INTERACTION_MATRIX
10. FAILURE_AND_COUNTEREXAMPLE_MATRIX
11. PRE_REGISTERED_PRIMARY_CANDIDATES
12. PRE_REGISTERED_SENSITIVITY_CONTROLS
13. BACKTEST_DATA_AND_TIME_CONTRACT
14. COST_AND_MANUAL_EXECUTION_CONTRACT
15. RAW_CANDIDATE_AND_MARKET_EVENT_SCHEMA
16. MANDATORY_REPLAY_MODES
17. RESULT_REPORT_SCHEMA
18. GO / REVISE / INCONCLUSIVE / REJECT GATES
19. INPUT_FOR_PRODUCT_PLANNING
20. INPUT_FOR_ENGINEERING_OPTIMIZATION
21. INPUT_FOR_PROJECT_CONTROL

STOP CONDITIONS:

- 需要发明缺乏经济机制的新策略；
- 需要大规模参数搜索；
- 需要 L2 / Volume Profile 才能定义第一版；
- 需要修改 First Launch 架构；
- 三 Setup 无法形成可量化合同；
- 数据不足以回答问题且代理数据也不可接受。
```

---

## 10. 当前用户只需确认的事项

为了进入联合回测准备，建议用户确认：

```text
ALLOW_LONG_HISTORY_PROXY_DATA = YES
PRIMARY_MANUAL_RESPONSE_DELAY_SECONDS = 30
USE_CONSERVATIVE_TAKER_FEE_MODEL = YES
```

若用户暂时不确认，策略研究仍可先开始；联合回测前必须冻结。