# First Launch 三 Setup 48 小时策略优先范围附录

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-48H-STRATEGY-FIRST-2026-07-30-R1`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**生产基线与最低回滚目标：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**状态：** `STRATEGY-FIRST SCOPE CORRECTION / NON-EXECUTABLE`

## 1. 用户目标的精确定义

本轮不是发现新的“历史收益最高策略”，也不是建设完整量化研究平台。

三个经济机制已经由成熟主观交易实践长期使用：

1. `SWEEP_RECLAIM`：流动性清扫后未被市场接受，重新收回边界；
2. `BREAKOUT_RETEST`：关键边界突破、回踩确认并延续；
3. `RANGE_EDGE_REJECTION`：稳定震荡区间边缘拒绝和均值回归。

本轮工作的核心是：

```text
HUMAN_TRADING_CONCEPT
→ CAUSAL QUANTITATIVE CONTRACT
→ JOINT REPLAY
→ MINIMUM PRODUCTION IMPLEMENTATION
```

本轮不以最大化历史收益为目标；以正确量化、清晰归属、费用后可行性和生产可实现性为目标。

## 2. 范围收敛

### 必须完成

- 三个 Setup 使用同一模板完成经济机制和量化合同审计；
- FAST 与 STANDARD 对所有适用 Setup 均保留在研究和回测中；
- 建立最小因果联合回放；
- 枚举全部原始候选，不能让 first-match 顺序隐藏重叠；
- 评估同 K 线、跨 K 线、同方向重复和反方向候选；
- 对当前 v0.1 运行 exact baseline；
- 对最终候选运行费用、滑点、人工延迟和有效期模型；
- 只实现回测支持的最小策略改动；
- 保证可恢复到当前 exact v0.1。

### 本轮不做

- 通用策略插件平台；
- 独立多策略框架；
- 新服务、线程或异步运行链；
- WebSocket/HTTP candle authority 修改；
- 数据库 Schema migration；
- L2、trades、Volume Profile 或 liquidation feed；
- 自动下单；
- Strategy enablement / kill switch；
- 新自动交易 Shadow/Canary 子系统；
- 大规模参数优化；
- 完整回滚演练项目。

## 3. 两层量化模型

不能简单使用“一个 regime 对应一个 Setup”的单层模型，因为 Sweep 和 Breakout 可能围绕同一边界形成不同结果，Range 也可能正处于向 Breakout 转换的边界阶段。

本轮固定两层模型：

### Layer A — Environment State

```text
RANGE
DIRECTIONAL_UP
DIRECTIONAL_DOWN
TRANSITION
UNCERTAIN
```

### Layer B — Event Outcome

```text
SWEEP_RECLAIM
BREAKOUT_RETEST
RANGE_EDGE_REJECTION
NO_ACTION
```

Environment 决定 eligibility，Event Outcome 决定最终 SetupFamily。

示例：

- `RANGE` 环境允许 `RANGE_EDGE_REJECTION`，但若价格越界后满足明确 Sweep，则归 `SWEEP_RECLAIM`；
- `TRANSITION` 默认不允许 Range 逆势信号，但可以观察 Sweep 或 Breakout；
- `DIRECTIONAL_UP/DOWN` 主要允许方向一致的 Breakout，Sweep 是否允许由独立合同决定；
- `UNCERTAIN` 默认 `NO_ACTION`。

该分类属于纯策略层，不要求修改运行架构。

## 4. 三 Setup 合同要求

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

禁止使用未量化的“明显、强势、靠近、有效”等描述。

## 5. 有限优化规则

现有两个 Setup 重新审计，但不强制修改。

每个 Setup 第一轮最多允许：

- 一个 exact v0.1 baseline；
- 一个主候选合同；
- 最多一个具有明确经济解释的敏感性对照。

禁止：

- 同时搜索大量窗口、ATR、成交量、收盘位置和止损参数；
- 根据同一测试区间结果反复重写规则；
- 只报告表现最好的候选；
- 用组合总收益掩盖单 Setup 结果。

## 6. FAST 与 STANDARD

两个模式均保留在研究和回测中。

```text
FAST = 初始闭合 K 线直接确认
STANDARD = 初始 K 线进入 PREPARE，等待后续 1–3 根闭合 K 线确认
```

每个 Setup 独立输出：

- FAST-only event；
- STANDARD-only event；
- 同一 market event 中两者的先后；
- STANDARD 过滤的失败事件；
- STANDARD 因延迟错失或追价的事件；
- 两者净期望、MAE、MFE、回撤和连续亏损。

生产保留哪一种或两种都保留，只能在联合回测后决定。

## 7. 联合回测模式

最小 replay 必须运行：

```text
A. V0_1_EXACT_BASELINE
B. V0_1_INSTRUMENTED_PARITY
C. SWEEP_CANDIDATE
D. BREAKOUT_CANDIDATE
E. RANGE_FAST_STANDARD
F. ALL_RAW_CANDIDATES_NO_ARBITRATION
G. COMBINED_EXACT_POLICY
```

重点不是寻找最大收益，而是确认：

- v0.1 exact 行为；
- 三个经济机制是否能因果量化；
- regime/event 分类是否清晰；
- raw candidate overlap；
- same-candle overlap；
- cross-candle overlap；
- FAST/STANDARD duplicate event；
- opposite candidate；
- final policy 是否静默压制有效旧信号；
- 费用后是否具备最低可行性。

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

## 8. 1–2 工作日目标

### Day 1

- 固定 v0.1 exact baseline；
- 完成三 Setup 统一合同；
- 完成 external evidence mapping；
- 验证当前 STANDARD 是否能跨 K 线推进；
- 建立或完成最小 causal replay；
- 实现全部 raw candidate instrumentation。

### Day 2

- 运行联合回放；
- 输出三 Setup、FAST/STANDARD 和交互报告；
- 冻结最终最小候选；
- 仅在结果清晰时生成 strategy-only production patch；
- 运行必要策略测试、全仓回归、独立 review 和 CI；
- 门禁全部通过后才安排部署。

`1–2 工作日`是策略研究、联合回测和最小候选的目标窗口。若发现当前 STANDARD 生命周期存在真实缺陷、历史数据不足或策略合同结果不明确，不得以赶工为理由直接上线。

## 9. 最小回滚合同

本轮不建设完整回滚平台，也不要求单独安排大规模回滚演练。

部署前最低要求：

```text
ROLLBACK_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
ROLLBACK_STRATEGY = ETH-LDAR-v0.1
DATABASE_SCHEMA_CHANGE = NO
```

保存：

- 当前 exact 代码和部署包；
- 当前 systemd unit；
- 当前环境、风险配置和 permit 状态；
- 当前 SQLite 一致性备份；
- 当前 READY / PID / session 基线；
- 恢复旧 SHA、旧配置和必要时旧数据库的命令。

若新版本失败：

1. 先归档升级期间新日志和研究记录；
2. 恢复当前 exact SHA 与当前配置；
3. 若 mixed-version 数据导致旧代码不兼容，则恢复部署前数据库备份；
4. 核验 service、`ta-status`、candle finalization、strategy evaluation 和 notification。

这里的最低“无损”定义是：当前 v0.1 代码、配置、历史和运行能力不会因本次有限升级被破坏。

## 10. 延期功能

以下功能保留在 Backlog Issue #62：

- Setup/strategy enablement；
- kill switch；
- 自动交易 Shadow；
- Canary risk cap；
- 自动策略晋级、暂停和回滚控制。

当前人工最终决策阶段不开发上述能力。

## 11. 最终停止条件

出现以下情况，不得在 48 小时目标下强行上线：

- 当前 STANDARD 生命周期本身存在未闭合缺陷；
- 三 Setup 无法形成清晰的 environment/event 分类；
- v0.1 instrumented parity 失败；
- raw overlap 无法解释；
- 新合同改变旧信号但没有明确证据；
- 费用后明显不可行；
- 历史数据不足以产生基本事件样本；
- 需要运行架构、transport 或数据库迁移；
- 无法可靠恢复当前 exact v0.1。

## 12. 裁决

```text
SCOPE = STRATEGY_FIRST
TARGET = QUANTIFY_THREE_KNOWN_TRADING_MECHANISMS
TIMEBOX = 1_TO_2_WORKDAYS
ARCHITECTURE_CHANGE = NONE_BY_DEFAULT
FAST_STANDARD = BOTH_RETAINED_IN_RESEARCH
ROLLBACK = EXACT_SHA_CONFIG_DB_BACKUP
FULL_ROLLBACK_REHEARSAL = NOT_REQUIRED_IN_THIS_ITERATION
```
