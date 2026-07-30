# First Launch 三 Setup 研究工具、角色、资源与窗口交接（最终修正版）

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-RESEARCH-TOOL-AND-HANDOFF-2026-07-30-R2`  
**日期：** `2026-07-30`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**状态：** `FINAL STRATEGY-RESEARCH TOOL AND ROLE GOVERNANCE / NON-EXECUTABLE`

本文不授权生产修改、部署、重启、账户访问、签名、交易所写入、自动下单、Mark Ready 或 merge。

## 1. 本轮任务核心

本轮不是发明策略，也不是寻找历史收益最高的参数组合。

本轮要把三种成熟的主观交易机制转换为因果、可重复、可回测、可植入 First Launch 的量化合同：

1. `SWEEP_RECLAIM`：流动性清扫、止损或强平触发后，价格未被市场接受在边界外并重新收回；
2. `BREAKOUT_RETEST`：关键边界有效突破、被市场接受、回踩确认后延续；
3. `RANGE_EDGE_REJECTION`：稳定震荡区间边缘拒绝与向区间内部均值回归。

`FAST` 与 `STANDARD` 对所有适用 Setup 均保留在研究和回测中。最终按 Setup 分别决定保留 FAST、STANDARD 或两者。

固定主流程：

```text
成熟交易机制
→ 外部证据与人类交易语义
→ 因果量化合同
→ 有限本地原生判定
→ 成熟工具进行交易模拟与统计
→ 联合回测与交互分析
→ 最小生产候选
```

## 2. 回测工具最终裁决

### 2.1 不自研完整回测平台

本轮禁止自建通用 backtesting engine、broker / matching simulator、资金曲线和绩效平台、数据下载平台、通用参数优化系统、图表平台或生产级策略插件框架。

### 2.2 策略判定权威：当前生产策略代码

策略触发、FAST / STANDARD、PREPARE、失效、expiry、Chase Limit、Setup 归属与最终候选，必须尽量调用当前生产策略的纯函数和数据对象。

目的：

- 避免在第三方框架中重写出第二套策略语义；
- 保证回测候选与未来生产候选一致；
- 能运行 `V0_1_EXACT_BASELINE` 和 `V0_1_INSTRUMENTED_PARITY`；
- 将策略问题与撮合、费用、统计问题分离。

### 2.3 有限本地原生判定 runner

允许一个很小的、本地隔离运行的判定 runner，仅负责逐根闭合 K 线推进、5m / 15m 因果时间对齐、构造 `StrategySnapshot`、调用或薄包装生产策略判定、推进 FAST / STANDARD / PREPARE、枚举全部 raw candidates、输出标准化候选记录和进行简单 market-event 归并。

它不负责撮合、账户资金、手续费引擎、收益曲线、最大回撤、图表或参数优化。

这属于“有限本地回测的策略判定层”，不是自研回测平台。

### 2.4 Freqtrade：主要数据、交易模拟和统计工具

本轮优先使用 Freqtrade 负责：

- 成熟交易所 OHLCV 下载与增量更新；
- 1m / 5m / 15m 数据管理；
- 将标准化最终候选映射为交易信号；
- fee、trade、SL / TP 和结果模拟；
- `--timeframe-detail 1m`；
- trade / signal export；
- 收益、回撤和交易统计；
- `lookahead-analysis`；
- `recursive-analysis`；
- 简单独立基准。

Freqtrade 不能定义 Trader Assist 的 Setup 语义，也不能替代原生判定层。

官方参考：

- https://www.freqtrade.io/en/stable/backtesting/
- https://www.freqtrade.io/en/stable/lookahead-analysis/
- https://docs.freqtrade.io/en/stable/recursive-analysis/
- https://docs.freqtrade.io/en/latest/data-download/

### 2.5 Backtesting.py：可选交叉验证工具

Backtesting.py 不再是本轮强制主引擎。

只在以下情况启用：

- Freqtrade 与原生候选映射存在无法解释的差异；
- 需要轻量逐 bar 独立实现交叉验证；
- 需要快速可视化单一 Setup 的交易路径；
- 产品规划、策略研究或独立 Reviewer 要求第二引擎复核。

Backtesting.py 支持逐 bar `Strategy.next()`、commission、spread、SL / TP 和详细结果，但使用 AGPL-3.0；应保持在离线研究环境，不成为 First Launch 生产依赖。

官方参考：

- https://kernc.github.io/backtesting.py/doc/backtesting/
- https://github.com/kernc/backtesting.py

### 2.6 允许的最薄适配代码

仅允许：

```text
STRATEGY_SNAPSHOT_ADAPTER
LIMITED_CAUSAL_DECISION_RUNNER
RAW_CANDIDATE_EXPORT_ADAPTER
FREQTRADE_SIGNAL_ADAPTER
SIMPLE_MARKET_EVENT_GROUPER
RESULT_MAPPING_AND_REPORT_EXPORT
```

这些代码必须只存在于隔离研究环境或研究目录，不成为生产运行依赖，不修改 candle transport 或数据库 Schema，不增加生产服务、线程或异步任务，不访问账户、私钥或交易所写权限，优先复用生产纯函数，并且不复制一套独立策略实现。

## 3. “Trader Assist 专属”内容的价值裁决

“专属”本身没有价值。只有表达真实经济机制、实际人工执行方式、生产一致性或统计正确性的专属内容才保留。

必须保留：

- 三 Setup 语义；
- FAST / STANDARD / PREPARE；
- 失效与 expiry；
- Chase Limit；
- 结构止损与目标可行性；
- v0.1 exact parity；
- 同一关键边界的事件归属。

仅研究层需要：

- raw candidate recorder；
- simple market-event grouper；
- overlap / suppression / opposite-candidate reporting。

交给成熟工具：

- OHLCV 下载与格式；
- fee / spread / slippage 基础模拟；
- SL / TP 订单结果；
- 资金曲线与最大回撤；
- 胜率和 Profit Factor；
- trade / signal export；
- lookahead / recursive 检查；
- 图表。

不进入策略回测：Discord、Operator Review Card、systemd、`ta-status`、production SQLite transaction、WebSocket / HTTP candle authority、reconnect、账户或交易权限。

## 4. 数据路线

Hyperliquid 最近可用 5m / 15m K 线用于 `HYPERLIQUID_EXACT_RECENT_EVIDENCE`。

Binance 或 Bybit ETH perpetual 1m / 5m / 15m 长历史用于 `LONG_HISTORY_PROXY_EVIDENCE`。

两类证据必须分开报告。

优先使用 1m 数据解决同一 5m K 线内 Stop / TP 先后；缺少 1m 时标记 `AMBIGUOUS_PATH`、使用保守 Stop-first 并单独报告影响。

## 5. 成本和人工执行合同

默认研究模型：人工执行主场景按 taker；maker 只作敏感性；人工响应延迟主场景 30 秒，15 秒和 60 秒作敏感性；funding 仅在持仓跨 funding 时段时纳入。

实际费率和延迟可在合同冻结前替换，但不得在看到回测收益后选择最有利值。

## 6. 角色与职责

策略优化窗口负责策略经济机制、量化合同、FAST / STANDARD、反例、交互、候选预注册和回测验收，不负责工程任务派发。

产品功能规划窗口负责产品定位、人类交易员使用流程、信号展示、TAKEN / SKIPPED / outcome、产品准入和 First Launch / V0 边界。

工程优化窗口负责开发路径、技术路线、当前策略纯函数复用、有限本地 runner 与 Freqtrade 最薄适配、Backtesting.py 可选复核、数据、许可证、文件范围、依赖和停止条件，不负责具体任务派发。

总控窗口是唯一任务派发者，负责接收三个上层窗口的冻结输入，并向 Codex CLI、数据准备、Reviewer、CI 和部署窗口派发。

## 7. 当前资源状态

已具备 exact 生产 SHA、策略代码和测试、三 Setup 方向、FAST / STANDARD 决策、GitHub 治理基线、5m / 15m 公共数据入口、工具路线、风险和 TradePlan 语义。

由总控后续准备长历史 ETH perpetual 数据、Hyperliquid 最近 K 线、隔离 worktree / Python 环境、Freqtrade 安装与 smoke、STANDARD progression 核验、数据完整性和时间语义报告。

不需要用户提供 API Key、钱包地址、私钥、交易账户访问或生产服务器写权限。

## 8. 前置工作包与后续顺序

工作包 A：策略优化窗口完成三 Setup 研究与量化合同。

工作包 B：工程优化窗口形成工具技术路线与联合回测输入，具体执行由总控派发，独立 Reviewer 验收。

联合回测至少运行：

```text
V0_1_EXACT_BASELINE
V0_1_INSTRUMENTED_PARITY
SWEEP_CANDIDATE
BREAKOUT_CANDIDATE
RANGE_FAST_STANDARD
ALL_RAW_CANDIDATES_NO_ARBITRATION
COMBINED_EXACT_POLICY
```

顺序：

```text
三个上层窗口并行完成认领
→ GitHub 同步冻结
→ 总控读取三方输出
→ 总控派发数据与工具准备
→ 总控派发联合回测
→ 独立 Reviewer
→ 策略与产品联合裁决
→ GO 后才进入最小生产实现
```

三个窗口完整初始化提示词和长期日常工作模型均已拆分到独立治理文件。