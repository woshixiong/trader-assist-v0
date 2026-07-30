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

本轮禁止自建：

- 通用 backtesting engine；
- broker / matching simulator；
- 资金曲线和绩效平台；
- 数据下载平台；
- 通用参数优化系统；
- 图表平台；
- 生产级策略插件框架。

### 2.2 策略判定权威：当前生产策略代码

策略触发、FAST / STANDARD、PREPARE、失效、expiry、Chase Limit、Setup 归属与最终候选，必须尽量调用当前生产策略的纯函数和数据对象。

目的：

- 避免在第三方框架中重写出第二套策略语义；
- 保证回测候选与未来生产候选一致；
- 能运行 `V0_1_EXACT_BASELINE` 和 `V0_1_INSTRUMENTED_PARITY`；
- 将策略问题与撮合、费用、统计问题分离。

### 2.3 有限本地原生判定 runner

允许一个很小的、本地隔离运行的判定 runner，仅负责：

- 逐根闭合 K 线推进；
- 5m / 15m 因果时间对齐；
- 构造 `StrategySnapshot`；
- 调用或薄包装生产策略判定；
- 推进 FAST / STANDARD / PREPARE；
- 枚举三个 Setup 的全部 raw candidates；
- 输出标准化候选记录；
- 进行简单 market-event 归并。

它不负责撮合、账户资金、手续费引擎、收益曲线、最大回撤、图表或参数优化。

这属于“有限本地回测的策略判定层”，不是自研回测平台。

### 2.4 Freqtrade：主要数据、交易模拟和统计工具

本轮优先使用 Freqtrade 负责：

- 成熟交易所 OHLCV 下载与增量更新；
- 1m / 5m / 15m 数据管理；
- 将标准化最终候选映射为交易信号；
- fee、trade、SL / TP 和结果模拟；
- `--timeframe-detail 1m` 细化主周期 K 线内路径；
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
- 需要一个轻量逐 bar 独立实现交叉验证；
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

这些代码必须：

- 只存在于隔离研究环境或明确的研究目录；
- 不成为生产运行依赖；
- 不修改 candle transport；
- 不修改数据库 Schema；
- 不增加生产服务、线程或异步任务；
- 不访问账户、私钥或交易所写权限；
- 优先复用生产纯函数；
- 不复制一套独立策略实现。

## 3. “Trader Assist 专属”内容的价值裁决

“专属”本身没有价值。只有表达真实经济机制、实际人工执行方式、生产一致性或统计正确性的专属内容才保留。

### 3.1 必须保留的策略语义

- `SWEEP_RECLAIM / BREAKOUT_RETEST / RANGE_EDGE_REJECTION`；
- `FAST / STANDARD / PREPARE`；
- Setup 失效与 expiry；
- Chase Limit；
- 结构止损与目标可行性；
- v0.1 exact parity；
- 同一关键边界的事件归属。

### 3.2 只在研究层需要的内容

- raw candidate recorder；
- simple market-event grouper；
- overlap / suppression / opposite-candidate reporting。

这些用于避免 first-match 隐藏候选、避免同一行情被重复计数，不自动要求进入长期生产架构。

### 3.3 应交给成熟工具的内容

- OHLCV 下载与格式；
- fee / spread / slippage 基础模拟；
- SL / TP 订单结果；
- 资金曲线；
- 最大回撤；
- 胜率、Profit Factor 等统计；
- trade / signal export；
- lookahead / recursive 检查；
- 图表。

### 3.4 不进入策略回测的生产内容

- Discord 发送；
- Operator Review Card 渲染；
- systemd；
- `ta-status`；
- production SQLite transaction；
- WebSocket / HTTP candle authority；
- reconnect；
- 账户或交易权限。

这些通过生产代码回归和部署验收验证，不塞入策略回测。

## 4. 数据路线

### 4.1 Hyperliquid 精确场地近期证据

使用 Hyperliquid 官方可获得的近期 5m / 15m K 线进行 venue 时间语义校验、近期成交量和价格行为 sanity check，以及 First Launch 最终候选的近期场地验证。

Hyperliquid candle 历史窗口有限，因此不能单独用于覆盖大量 regime。

### 4.2 长历史代理证据

使用 Binance 或 Bybit ETH perpetual 1m / 5m / 15m 长历史覆盖 RANGE、DIRECTIONAL_UP、DIRECTIONAL_DOWN、TRANSITION 和 EXTREME VOLATILITY。

代理数据只证明交易机制在相近市场中的稳健性，不用于声称 Hyperliquid 精确收益。

报告必须区分：

```text
LONG_HISTORY_PROXY_EVIDENCE
HYPERLIQUID_EXACT_RECENT_EVIDENCE
```

### 4.3 1m 详细路径

优先使用 1m 数据解决同一 5m K 线内 Stop / TP 先后。

缺少 1m 时：

- 标记 `AMBIGUOUS_PATH`；
- 使用保守 Stop-first；
- 单独报告数量和影响。

## 5. 成本和人工执行合同

默认研究模型：

- 人工执行主场景按 taker；
- maker 只作敏感性；
- 人工响应延迟主场景 30 秒；
- 15 秒和 60 秒作敏感性；
- funding 仅在持仓跨 funding 时段时纳入；
- 不需要 API Key、钱包地址、私钥或生产写权限。

实际费率和延迟可在合同冻结前替换，但不得在看到回测收益后选择最有利值。

## 6. 角色与职责

### 6.1 策略优化窗口

负责外部成熟研究、三 Setup 经济机制、两层 Environment / Event 模型、完整因果量化合同、FAST / STANDARD、触发与失效、反例和交互、候选预注册以及回测输入与结果解释。

不负责具体工程任务派发、工具安装、生产修改、部署、Mark Ready 或 merge。

### 6.2 产品功能规划窗口

负责策略与 First Launch / V0 的产品定位、人类交易员使用流程、信号展示、TAKEN / SKIPPED / outcome 证据、产品准入与失败处理，并与策略优化、工程优化共同确认策略—产品—框架对接。

### 6.3 工程优化窗口

负责最小开发路径、技术路线、当前策略纯函数可复用性、有限本地 runner 与 Freqtrade 的最薄适配、Backtesting.py 可选复核条件、数据、许可证、文件范围、依赖和停止条件。

不负责具体任务派发、擅自确定策略参数、修改产品范围或直接部署。

### 6.4 总控窗口

是唯一任务派发者，负责接收三个上层窗口的冻结输入，并向 Codex CLI、数据准备、Reviewer、CI 和部署窗口派发。

### 6.5 Codex CLI / 执行者

只能由总控派发，负责隔离环境、数据准备、最薄适配、联合回测、结果导出以及获得 GO 后的最小 strategy-only patch。

### 6.6 独立 Reviewer

只能由总控派发，负责因果性、v0.1 parity、时间对齐、raw candidate 完整性、FAST / STANDARD 实际触发、成本与路径模型、结果可重复性，以及是否发生隐藏调参或选择偏差。

## 7. 当前资源状态

### 已具备

- exact 生产 SHA 与策略版本；
- 当前策略代码和测试；
- 三 Setup 成熟交易方向；
- FAST / STANDARD 决策；
- GitHub 治理基线；
- 5m / 15m 公共数据入口；
- Freqtrade 与 Backtesting.py 工具路线；
- 当前风险和 TradePlan 语义；
- 无生产写权限的研究边界。

### 由总控后续准备

- 长历史 ETH perpetual 1m / 5m / 15m 数据；
- Hyperliquid 最近可用 K 线；
- 隔离 worktree / Python 环境；
- Freqtrade 安装与 smoke；
- STANDARD progression 确定性核验；
- 数据完整性和时间语义报告。

### 不需要用户提供

- API Key；
- 钱包地址；
- 私钥；
- 交易账户访问；
- 生产服务器写权限。

## 8. 两个前置工作包

### 工作包 A：三 Setup 策略研究与量化合同

主责：策略优化窗口。  
协作：产品功能规划窗口。  
技术咨询：工程优化窗口。  
具体任务派发：无；冻结结论后提交总控。

### 工作包 B：工具技术路线与联合回测输入

策略输入：策略优化窗口。  
产品输入：产品功能规划窗口。  
技术路线：工程优化窗口。  
具体执行：总控派发。  
验收：独立 Reviewer。

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

## 9. 后续顺序

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

本文件的三个窗口完整初始化提示词已拆分到独立治理文件，避免职责混淆和单文件过长。