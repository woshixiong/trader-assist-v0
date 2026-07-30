# First Launch 三 Setup 最终共识与并行工作计划

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-FINAL-ALIGNMENT-2026-07-30-R1`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**状态：** `FINAL CROSS-WINDOW ALIGNMENT / NON-EXECUTABLE`

本文用于让策略优化、产品功能规划、工程优化和后续总控窗口从同一事实与职责边界出发。本文不授权生产修改、部署、重启、账户访问、签名、交易所写入、自动下单、Mark Ready 或 merge。

---

## 1. 本轮任务核心

本轮不是发明新策略，也不是寻找历史收益最高的参数组合。

三种交易机制已经由长期主观交易实践和成熟市场研究反复使用：

1. `SWEEP_RECLAIM`：流动性清扫、止损或强平触发后，价格未被市场接受在边界外并重新收回；
2. `BREAKOUT_RETEST`：关键边界被有效突破、获得市场接受、回踩后继续延续；
3. `RANGE_EDGE_REJECTION`：稳定震荡区间的边缘拒绝与向区间内部均值回归。

本轮目标是：

```text
成熟交易思想
→ 合理量化
→ 因果联合回测
→ 只接受有证据的有限优化
→ 将三个优化版本植入 First Launch
```

不追求机构级完美，不建设大型量化研究平台，不把本轮扩张成 V0 大版本。

---

## 2. 固定策略研究原则

### 2.1 两层模型

Environment State：

- `RANGE`
- `DIRECTIONAL_UP`
- `DIRECTIONAL_DOWN`
- `TRANSITION`
- `UNCERTAIN`

Event Outcome：

- `SWEEP_RECLAIM`
- `BREAKOUT_RETEST`
- `RANGE_EDGE_REJECTION`
- `NO_ACTION`

Environment 决定 Setup 是否有资格参与；Event Outcome 决定最终 SetupFamily。

不能机械地规定一种 regime 只能对应一种 Setup，因为同一关键边界可能最终形成 Sweep、Breakout 或普通 Range Rejection。

### 2.2 FAST 与 STANDARD

两个确认模式对所有适用 Setup 均保留在研究和回测中：

- `FAST`：初始闭合 K 线已经提供足够证据，立即确认；
- `STANDARD`：初始 K 线进入 PREPARE，等待后续 1–3 根闭合 K 线确认。

最终按每个 Setup 的证据分别决定保留 FAST、STANDARD 或两者。不得在回测前取消任何一个模式。

### 2.3 有限优化

每个 Setup 第一轮最多允许：

- 一个 exact v0.1 baseline；
- 一个主要候选；
- 最多一个具有明确经济解释的敏感性对照。

禁止：

- 大规模窗口、ATR、成交量、止损和收盘位置网格搜索；
- 根据同一历史区间反复改规则；
- 只报告表现最好候选；
- 用组合收益掩盖单 Setup 表现；
- 从历史收益倒推经济机制。

### 2.4 三 Setup 统一合同

每个 Setup 必须在回测前冻结：

```text
ECONOMIC_HYPOTHESIS
TARGET_ENVIRONMENT
PROHIBITED_ENVIRONMENT
LEVEL_DEFINITION
LEVEL_QUALITY
EVENT_TRIGGER
FAST_CONFIRMATION
STANDARD_PREPARE
STANDARD_CONFIRMATION
INVALIDATION
EXPIRY
ENTRY_ZONE
CHASE_LIMIT
STRUCTURAL_STOP
TARGET_FEASIBILITY
COST_MODEL
FAILURE_MODE
INTERACTION_POLICY
```

禁止保留“明显、强势、靠近、有效、较大、正常回踩”等未量化描述。

---

## 3. 三 Setup 交互研究

目标不是先假设三个 Setup 一定冲突，也不是先假设绝不冲突。

必须通过 raw candidate 枚举和联合回测回答：

- Sweep 与 Range 的 excursion 边界；
- Breakout 与 Range 的 close acceptance；
- Sweep 与 Breakout 的 reclaim / acceptance；
- 同一根 K 线多个候选；
- 跨 K 线 PREPARE 和 active expiry；
- FAST / STANDARD 对同一 market event 的重复；
- 同方向重复候选；
- 反方向候选；
- `RANGE → TRANSITION → BREAKOUT`；
- failed Breakout → Sweep；
- dual-edge candle；
- regime 分类不严谨导致的伪冲突。

回测必须在最终裁决前记录所有 raw candidates，不能让生产 first-match 顺序隐藏候选。

---

## 4. 回测工具与方法

### 4.1 策略判定权威

当前生产策略代码与纯函数是策略语义权威。

### 4.2 有限本地 runner

只负责逐根闭合 K 线推进、时间对齐、StrategySnapshot 构造、FAST / STANDARD / PREPARE、raw candidate 输出和简单 market-event 归并。

不开发撮合、资金曲线、费用平台或图表平台。

### 4.3 Freqtrade

主要负责：

- 数据下载和更新；
- 1m / 5m / 15m 数据管理；
- 交易模拟；
- fee、SL / TP 和统计；
- `--timeframe-detail 1m`；
- signal / trade export；
- lookahead-analysis；
- recursive-analysis；
- 简单独立基准。

### 4.4 Backtesting.py

只作可选第二引擎交叉验证，不是本轮强制主路线，也不进入生产依赖。

### 4.5 联合回测模式

```text
A. V0_1_EXACT_BASELINE
B. V0_1_INSTRUMENTED_PARITY
C. SWEEP_CANDIDATE
D. BREAKOUT_CANDIDATE
E. RANGE_FAST_STANDARD
F. ALL_RAW_CANDIDATES_NO_ARBITRATION
G. COMBINED_EXACT_POLICY
```

必须输出：

```text
REPLAY_CORRECTNESS
V0_1_PARITY
STRATEGY_CONTRACT_COMPLETENESS
REGIME_EVENT_CLASSIFICATION
INTERACTION_CLASSIFICATION
FAST_STANDARD_EVIDENCE
COSTED_FEASIBILITY
PRODUCTION_DISPOSITION
```

---

## 5. 数据与成本

数据双轨：

1. Hyperliquid 最近可用数据：`HYPERLIQUID_EXACT_RECENT_EVIDENCE`；
2. Binance / Bybit ETH perpetual 长历史：`LONG_HISTORY_PROXY_EVIDENCE`。

两类结果必须分开报告。

优先使用 1m 数据解决同一 5m K 线内 Stop / TP 先后；缺少 1m 时标记 `AMBIGUOUS_PATH`、保守 Stop-first 并单独报告。

成本合同在回测前冻结。默认人工执行主场景按 taker，30 秒响应延迟为主场景，15 秒和 60 秒作敏感性；不得看到收益后选择最有利成本。

---

## 6. 架构与范围边界

本轮默认不修改 First Launch 架构。

禁止：

- WebSocket / HTTP candle authority 修改；
- 新生产服务、线程或异步任务；
- 数据库 Schema migration；
- L2、trades、Volume Profile、liquidation feed；
- 自动下单；
- 通用策略插件平台；
- 独立多策略框架；
- Setup enablement、kill switch、新自动交易 Shadow / Canary。

延期控制能力保留在 Backlog Issue #62。

唯一需要先确定性核验：当前 `STANDARD PREPARE` 是否能在后续闭合 K 线上正确推进。若失败，必须独立报告，不能藏在新策略实现中。

---

## 7. 回滚最低合同

固定回滚目标：

```text
ROLLBACK_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
ROLLBACK_STRATEGY = ETH-LDAR-v0.1
DATABASE_SCHEMA_CHANGE = NO
```

部署前保存 exact 代码、配置、systemd unit、permit 状态、SQLite 一致性备份、READY / PID / session 基线和恢复命令。

本轮不建设完整回滚平台，也不要求单独的大型回滚演练项目。

---

## 8. 固定角色与派发关系

### 策略优化窗口

决定策略经济机制、量化合同、FAST / STANDARD、反例、交互和回测验收。属于策略上层管理者，不派发工程任务。

### 产品功能规划窗口

决定产品目标、First Launch / V0 定位、人工使用流程、证据需求和产品准入。属于产品与策略上层管理者。

### 工程优化窗口

决定怎样开发、采用什么工具、如何最小接入、文件范围、依赖、许可证、风险和停止条件。不得派发具体任务，不得重新定义策略或产品范围。

### 总控窗口

唯一具体任务派发者。接收三个上层窗口的冻结输出后，向 Codex CLI、数据准备、Reviewer、CI 和部署窗口派发。

---

## 9. 三窗口可立即并行认领

### 策略优化窗口现在执行

- 三 Setup 外部证据矩阵；
- 两层模型；
- 三 Setup 完整合同；
- FAST / STANDARD；
- 反例矩阵；
- 边界与交互矩阵；
- 主候选和敏感性对照；
- 回测输入合同。

### 产品功能规划窗口现在执行

- 三 Setup 对用户的产品意义；
- 人类交易员收到信号后的流程；
- SetupFamily / confirmation mode 的展示要求；
- TAKEN / SKIPPED / outcome 证据需求；
- 生产准入和 INCONCLUSIVE 的产品处理；
- 本轮与 V0 后续能力边界。

### 工程优化窗口现在执行

- 当前策略纯函数和数据对象可复用性；
- 有限本地 runner + Freqtrade 最小路线；
- Backtesting.py 可选复核条件；
- STANDARD progression 核验方案；
- 数据与时间语义；
- 允许的最薄适配和预计文件范围；
- 依赖、许可证、测试、停止条件；
- 给总控的技术路线输入。

三个窗口完成后均将结果写入 GitHub，再由总控统一读取和派发。