# Trader Assist 策略研究与回测日常工作模型 V1

**记录 ID：** `TA-STRATEGY-RESEARCH-BACKTEST-OPERATING-MODEL-V1-2026-07-30`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**状态：** `LONG-TERM RESEARCH OPERATING MODEL / NON-EXECUTABLE`

本文记录本轮研究沉淀出的长期工具和方法路线，使策略研究、回测和生产候选评估逐步成为可重复的日常工作，而不是每次从零开始。

本文不授权生产修改、自动下单、账户访问、部署或交易权限扩张。

---

## 1. 长期目标

建立一个轻量、可重复、可审计的日常流程：

```text
交易观点或市场问题
→ 经济机制合同
→ 有限候选预注册
→ 本地因果判定
→ 成熟工具模拟和统计
→ 独立偏差检查
→ 策略 / 产品 / 工程联合裁决
→ 最小生产变更
→ 实时证据回流
```

目标不是打造机构级研究平台，而是降低未来每次策略研究的边际成本和周期。

---

## 2. 工具长期分工

### 2.1 Trader Assist 原生策略库

长期作为：

- 生产策略语义权威；
- Setup、FAST / STANDARD、PREPARE、失效和 TradePlan 规则来源；
- 回测与生产 parity 的比较对象；
- 每个策略版本的冻结合同和身份来源。

原则：策略逻辑只维护一个权威实现，避免研究版和生产版长期分叉。

### 2.2 有限本地因果 runner

长期保留为轻量研究适配层，只负责：

- 历史 K 线逐步推进；
- 多时间周期因果对齐；
- 生产策略对象输入；
- raw candidate 和最终候选导出；
- FAST / STANDARD 状态推进；
- market-event 归并；
- parity 检查。

不得逐步膨胀成撮合平台、数据平台或通用研究框架。

### 2.3 Freqtrade

长期作为首选成熟工具，用于：

- OHLCV 数据下载和增量更新；
- 不同交易所和 timeframe 数据管理；
- 交易模拟和手续费模型；
- `--timeframe-detail`；
- signal / trade export；
- 结果统计和分期 breakdown；
- lookahead-analysis；
- recursive-analysis；
- 简单公开指标策略基准；
- 在未来必要时进行 dry-run 对照。

官方资料：

- https://www.freqtrade.io/en/stable/backtesting/
- https://www.freqtrade.io/en/stable/lookahead-analysis/
- https://docs.freqtrade.io/en/stable/recursive-analysis/
- https://docs.freqtrade.io/en/latest/data-download/

### 2.4 Backtesting.py

长期作为可选轻量第二引擎，用于：

- 单一策略或单一事件模型快速复核；
- 逐 bar 独立实现的结果交叉验证；
- 交互图表和研究演示；
- 对 Freqtrade 结果存在重大疑点时的第二意见。

不作为强制双引擎流程，不进入 First Launch 生产依赖。使用前确认 AGPL-3.0 边界。

官方资料：

- https://kernc.github.io/backtesting.py/doc/backtesting/
- https://github.com/kernc/backtesting.py

### 2.5 未来工具候选

NautilusTrader、LEAN 等保留为自动执行、多策略、复杂订单和研究—实盘一致性需求真正出现后的候选；当前不预先引入。

---

## 3. 标准研究目录建议

未来由工程优化和总控确认实际路径。逻辑结构建议保持：

```text
research/
  contracts/
  datasets/
  adapters/
  candidates/
  baselines/
  reports/
  evidence/
```

要求：

- 研究依赖不进入生产 requirements；
- 大型历史数据不直接提交 Git；
- 数据集记录来源、时间范围、hash 和缺口；
- 每次回测记录策略版本、候选合同、工具版本和命令；
- 结果文件可重复生成；
- 不在生产服务器进行探索性回测。

---

## 4. 每次策略研究的标准输入

必须先具备：

```text
RESEARCH_QUESTION
ECONOMIC_HYPOTHESIS
TARGET_REGIME
PROHIBITED_REGIME
DATA_REQUIREMENTS
CAUSAL_SIGNAL_CONTRACT
ENTRY_AND_EXIT_CONTRACT
COST_ASSUMPTIONS
FAILURE_MODES
PRIMARY_CANDIDATE
OPTIONAL_SENSITIVITY_CONTROL
BASELINE_VERSION
```

没有这些输入，不进入编码和回测。

---

## 5. 每次回测的最小验证层

### Layer 1 — Exact Baseline

证明当前生产或上一批准版本可以被精确重放。

### Layer 2 — Instrumented Parity

增加候选记录和分析后，最终输出仍与 baseline 一致。

### Layer 3 — Candidate Isolation

每个新候选或修改单独运行，报告独立事件和结果。

### Layer 4 — All Raw Candidates

不进行 first-match 裁决，暴露重叠、重复和反向候选。

### Layer 5 — Exact Combined Policy

运行拟议生产裁决和生命周期政策。

### Layer 6 — Bias Checks

至少执行：

- 时间因果审查；
- lookahead-analysis；
- recursive-analysis；
- startup lookback 检查；
- 未实际触发的策略分支补充构造测试。

### Layer 7 — Venue and Regime Evidence

长历史代理数据与目标交易所近期数据分开报告。

---

## 6. 固定报告结构

每次报告至少包含：

- 数据源、时间范围、hash、缺口；
- 策略版本和候选合同 ID；
- 工具和依赖版本；
- 运行命令；
- 信号数和独立市场事件数；
- LONG / SHORT；
- FAST / STANDARD；
- regime 分层；
- gross / net expectancy；
- fee / spread / slippage / delay / funding；
- win rate、average win / loss；
- maximum drawdown；
- longest losing streak；
- MFE / MAE；
- Stop / TP ambiguous path；
- overlap、suppression、opposite candidate；
- top-trade concentration；
- baseline parity；
- GO / REVISE / INCONCLUSIVE / REJECT。

---

## 7. 防止回测滥用

长期禁止：

- 自动寻找最高收益参数后直接生产化；
- 不记录失败候选；
- 同一数据上无限迭代；
- 混合不同交易所数据后声称精确 venue 收益；
- 忽略手续费、延迟和人工执行；
- 用单元测试冒充历史回测；
- 用回测代替实时证据；
- 未通过 parity 就修改生产策略；
- 将研究工具悄然变成生产交易权限来源。

---

## 8. 日常使用节奏

### 事件驱动研究

当出现以下情况时启动一次小型研究包：

- 持续无信号；
- 某类行情频繁错过；
- 某 Setup 连续失败；
- 人类交易员反复采用未量化方法；
- 新数据字段可能提供增量价值；
- First Launch 实际执行与回测存在差异。

### 定期复盘

First Launch 阶段可按积累到足够独立事件后复盘，而不是固定高频调参。自动交易阶段再由产品规划定义固定月度或版本节奏。

### 版本化

每次批准策略合同生成：

- Strategy Contract ID；
- Dataset Manifest；
- Backtest Run ID；
- Report ID；
- Production Candidate SHA；
- 回滚 SHA。

---

## 9. 角色治理

- 策略优化窗口：提出和审阅策略合同；
- 产品功能规划窗口：决定产品价值和准入；
- 工程优化窗口：决定工具和技术路线；
- 总控窗口：唯一任务派发；
- Codex / Writer：实际实现和运行；
- 独立 Reviewer：验证因果、parity、偏差和可重复性。

任何窗口不得越权同时承担策略定义、技术路线、任务派发和最终验收全部角色。

---

## 10. 本轮落地边界

本轮只建立最小可复用骨架：

- 原生策略判定复用；
- 有限本地 runner；
- Freqtrade 数据与模拟；
- 可选 Backtesting.py 复核；
- 数据 manifest；
- 结构化报告；
- parity 与偏差检查。

不提前开发自动调参、策略市场、实时研究服务或自动生产晋级。