# Trader Assist V0：产品功能、工程复用、健康新鲜度与开发前规划基线

**文档 ID：** `TA-V0-PRODUCT-ENGINEERING-HEALTH-AND-PREDEVELOPMENT-PLANNING-BASELINE-2026-07-28-R1`  
**日期：** 2026-07-28  
**项目：** `TRADER_ASSIST_V0_FIRST_LAUNCH_R3`  
**仓库：** `woshixiong/trader-assist-v0`  
**文档性质：** V0 产品功能与工程路线研究基线；用于 First Launch 上线后的统一规划  
**适用窗口：** Product Function and Priority Control、Engineering Optimization、Project Control、Strategy Research and Validation  
**状态：** `PRODUCT_PLANNING_BASELINE / GITHUB_DRAFT_SYNC / NOT_IMPLEMENTATION_AUTHORITY`  
**输入来源：**
- `Trader_Assist_First_Launch后V0产品功能规划_完整研究输入包_2026-07-28(1).md`
- `Trader_Assist_V0_Open_Source_Integration_and_Product_Planning(2).md`
- 当前 First Launch 产品基线、延期注册表、三窗口职责体系及产品功能规划裁决

**权限边界：**  
本文不授权 V0 激活、账户读取、凭据创建、API Wallet、私钥、签名、nonce、Testnet/Mainnet 写入、订单提交、撤单、自动保护单、自动交易、GitHub 合并、部署或运行时权限。

---

## 0. 文档目的

本文不是 V0 的最终可执行计划，而是 V0 开发前的产品与工程规划基线。

本文负责：

1. 拆解和校正两份研究报告；
2. 固定当前已经能够确认的 V0 产品与工程原则；
3. 明确 First Launch 上线后需要收集的证据；
4. 给出数据新鲜度和系统健康度的最小可用解决路线；
5. 明确哪些工程能力应自研、复用、包裹、试验或延期；
6. 给出 V0 的候选技术路线和依赖关系；
7. 列出 V0 最终规划前必须解决的问题；
8. 定义产品团队与策略团队的合并接口；
9. 为未来形成最终可执行方案提供完整输入。

最终正式链路为：

```text
FIRST LAUNCH ACCEPTED REAL OPERATION
→ GATE B EVIDENCE COLLECTION
→ PRODUCT PLANNING INPUT
+ STRATEGY RESEARCH INPUT
→ UNIFIED V0 PLANNING
→ V0_PRODUCT_AND_STRATEGY_SCOPE_DECISION_V1
→ V0_ENGINEERING_STAGE_PLAN_V1
→ PROJECT CONTROL BOUNDED ACTIVATION
```

---

# 1. 执行结论

## 1.1 V0 的目标保持不变

V0 的目标不是建设完整量化交易平台，而是：

> 用最少的开发资源、最短的时间，把 First Launch 已经形成的信号与 TradePlan 能力升级成更可靠、更容易执行、可以逐步获得受控交易权限的实用交易辅助系统。

V0 必须继续遵循：

```text
当前真实交易价值
→ 最小充分控制
→ 优先复用成熟能力
→ 最小端到端实现
→ 真实运行证据
→ 再增加权限和复杂度
```

## 1.2 当前默认产品假设

在缺少 Gate B 最终证据之前，当前合理的默认假设是：

```text
First Launch 稳定运行
→ 数据与健康状态可被可靠判断
→ 账户只读与 Order Preview
→ 系统生成 exact TradePlan
→ 用户确认 exact plan
→ 服务端重新校验
→ 受控 Testnet 下单与对账
→ 极小资金、逐笔人工确认 Mainnet
→ 再评估受限自动批准
```

这只是默认候选路线，不是预先授权的固定顺序。

Gate B 可能把优先级改为：

- 继续取样；
- 先修可靠性；
- 先改进现有策略；
- 先开发互补策略；
- 先开发人工确认执行；
- 在严格隔离条件下并行策略 Shadow 与执行基础。

## 1.3 最重要的技术方向

V0 不应把 Trader Assist 整体迁入大型框架。

推荐长期方向：

```text
Trader Assist 自有交易决策域
→ 版本化边界合同
→ 可替换研究或执行侧车
→ 交易所与成熟开源工程能力
```

Trader Assist 保留权威：

- 策略语义；
- 市场状态与适用性；
- Signal；
- TradePlan；
- 产品风险政策；
- 用户确认；
- 权限门禁；
- 结果归因；
- 产品优先级。

外部能力负责：

- 历史回测和偏差检测；
- API/Connector；
- 订单生命周期；
- 部分成交；
- 撤单与替换；
- 用户流；
- 启动和持续对账；
- 标准执行器；
- 通用监控和故障处理。

## 1.4 当前建议的最小权限边界

若 V0 选择真实执行路线，当前最合理的默认架构是：

```text
Strategy/Public Runtime
无私钥、无 nonce、无交易所写入
        │
        │ Versioned ExecutionIntent
        ▼
独立 Execution Guard
唯一持有 API Wallet 和交易所写权限
        │
        ▼
Execution Adapter
官方 Hyperliquid SDK / NautilusTrader / Hummingbot / CCXT
通过有界 Spike 选择
```

该架构仍需工程验证，但它比：

- 策略与私钥同进程；
- 全面迁移大型框架；
- 四个以上微服务；
- 多主机和分布式 fencing；

更符合当前速度、资源与安全边界。

---

# 2. 对两份研究报告的校正

## 2.1 主观成功概率不进入产品门禁

报告中的成功概率区间属于研究者先验，不是项目统计结果。

统一状态：

```text
SUBJECTIVE_RESEARCH_PRIOR
NOT_PRODUCT_GATE
NOT_BUDGET_COMMITMENT
NOT_PROFITABILITY_CLAIM
```

未来只使用真实 Gate B、Shadow、Testnet 和小资金证据更新判断。

## 2.2 不立即启动三个大型并行研究 Lane

原建议在 First Launch 后立即并行：

- Freqtrade 实验室；
- 执行引擎 Bake-off；
- Hummingbot 震荡/做市实验室。

这不符合“最少资源、最快上线”的默认原则。

修正为：

### 必须立即做

- Gate B 最小证据；
- Health/Freshness 最小模型；
- 当前 V0 首要矛盾判断。

### 仅在执行路线被选择时做

- Account Read / Order Preview discovery；
- 1–3 个有效开发日的 Execution Adapter Spike。

### 由策略团队按证据决定

- Freqtrade 研究镜像；
- 基准与消融；
- Regime 和第二策略研究。

### 仅在明确 RANGE_STABLE 缺口成立时做

- Hummingbot 做市/网格实验室。

不得为了“可能有用”同时启动所有研究。

## 2.3 Account Read 不是所有 V0 路线的绝对前置

若 V0 最终选择：

```text
STRATEGY_OR_REGIME_GAP_PRIMARY
```

且仍不进入真实执行，则 Account Read 可以延期。

只有在以下路线中，Account Read 才成为必需：

- Order Preview；
- Testnet 写入；
- Mainnet 写入；
- 自动管理真实仓位；
- 真实账户风险校验。

## 2.4 执行优先不是无条件固定路线

当前“先人工确认执行，再自动交易”是高价值默认假设。

但只有当 Gate B 表明：

- 信号具有实际价值；
- 人工愿意执行；
- MANUAL_EXECUTION_GAP 显著；
- 主要损失来自延迟或操作；

才应升级为首要 V0 路线。

如果信号质量、频率或市场覆盖是主要问题，应优先策略或继续取样。

## 2.5 工期估算不得作为承诺

报告中的：

- 23–42 个有效开发日；
- 4–7 周；
- 6–10 周；

只作为高层级粗估。

不得在以下信息未知时冻结排期：

- Gate B 结论；
- 当前 live main 与未合并 PR；
- Hyperliquid 实际账户条件；
- Adapter Spike；
- Testnet 行为；
- 部分成交和保护单复杂度；
- Review 与 Repair 情况。

正式工期必须由 Engineering Optimization 在产品范围确定后重新估算。

## 2.6 官方 SDK 的 Python 3.10 说明需要正确解释

官方 SDK 仓库目前说明其**贡献开发环境**要求 Python 3.10 exactly。

这不等同于：

- 已证明运行时只能使用 Python 3.10；
- 必须把 Trader Assist 主进程降级；
- 必须提前建立永久双版本架构。

正确处理：

- Spike 中测试实际安装和运行兼容性；
- 若隔离环境最简单，则 Execution Guard 使用独立 venv；
- 不修改现有 Strategy Runtime 的 Python 版本，除非实测证明必须。

## 2.7 不预先指定 Nautilus、Hummingbot 或官方 SDK 胜出

当前可以确认的是能力边界，不是最终产品选型。

- 官方 SDK：最薄、最接近 venue，但需要自研状态和对账；
- NautilusTrader：当前 Hyperliquid adapter 已覆盖执行、外部订单检测和周期性对账，但框架复杂；
- Hummingbot：当前 Hyperliquid spot/perp connector 和 V2 Executor/Controller 具备复用价值，但其产品运行模型较重；
- CCXT：适合轻量统一接口和研究便利，但不能假设它提供完整 OMS；
- Freqtrade：适合研究和偏差检测，不作为生产信号权威。

最终选型必须由有限 Spike 的故障证据决定。

## 2.8 不提前开发完整 StrategyManifest 和热插拔平台

第二个生产策略尚未批准前，最小策略元数据即可：

```text
strategy_id
strategy_version
code_hash
parameter_set_id
required_data
supported_states
prohibited_states
risk_ceiling
rollout_stage
evidence_version
```

以下能力继续延期：

- 动态加载任意策略代码；
- 多策略自动切换；
- 旧持仓自动迁移；
- 完整冲突调度；
- 多策略组合风险平台。

## 2.9 V0 与 Mainline 不应形成过度组织拆分

产品和权限边界需要清楚，但当前可以暂时同仓库、单主机、两个进程。

不需要因为未来可能拆仓库或多主机，就提前开发：

- 网络微服务；
- service mesh；
- etcd/ZooKeeper；
- 多地域；
- Kubernetes；
- 通用权限平台。

---

# 3. V0 产品决策方法

## 3.1 First Launch 后先识别首要矛盾

V0 最终规划必须先分类：

```text
EVIDENCE_INSUFFICIENT
RELIABILITY_GAP_PRIMARY
MANUAL_EXECUTION_GAP_PRIMARY
STRATEGY_OR_REGIME_GAP_PRIMARY
BOTH_GAPS_MATERIAL
```

## 3.2 各分类对应的默认动作

### EVIDENCE_INSUFFICIENT

- 继续 First Launch；
- 改善最小记录；
- 不增加高权限；
- 不启动大型框架集成。

### RELIABILITY_GAP_PRIMARY

- 先解决数据、通知、持久化、恢复和状态判断；
- 不用受污染证据评价策略；
- 不进入真实写入。

### MANUAL_EXECUTION_GAP_PRIMARY

- Account Read；
- Order Preview；
- 用户确认；
- Execution Guard；
- Testnet；
- 极小资金逐笔确认。

### STRATEGY_OR_REGIME_GAP_PRIMARY

- 现有策略基准、消融和语义验证；
- 补充策略或数据研究；
- 新策略只进入 Shadow；
- 执行写入只做有限 discovery，不进入资金关键路径。

### BOTH_GAPS_MATERIAL

允许两条隔离 Lane：

```text
Execution Foundation / Testnet
+
New Strategy Shadow
```

禁止两个 Lane 同时持有生产写权限或修改同一策略/执行边界。

---

# 4. V0 最小健康与数据新鲜度模型

## 4.1 为什么这是 V0 的硬问题

First Launch 的 `ta-status` 解决的是：

> 当前公共信号是否可以参考？

当 V0 增加账户、确认和下单后，系统必须分别回答：

```text
信号是否可靠？
账户事实是否可靠？
订单状态是否可靠？
保护状态是否可靠？
系统现在是否允许增加新风险？
```

因此：

```text
SIGNAL_READY != EXECUTION_READY != PROTECTION_READY
```

## 4.2 不建设通用监控平台

V0 应建设：

```text
ReadinessEnvelopeV1
```

而不是完整监控平台。

它只需要：

- 组件状态；
- 最后有效时间；
- 必需/可选依赖；
- reason code；
- 当前权限允许的顶层判断；
- fail-closed 行为。

## 4.3 分层状态

### ProcessHealth

- systemd service；
- PID/session；
- event loop progress；
- fatal error；
- status publication。

### TransportHealth

- HTTP/WS 连接；
- 最近接收；
- heartbeat；
- reconnect/backoff；
- rate-limit 状态。

### SubscriptionHealth

分别判断：

- 5m candle；
- 15m candle；
- activeAssetCtx；
- metadata；
- 未来 BBO；
- 未来 account/user/order streams。

连接成功不等于所需订阅全部 READY。

### MarketDataFreshness

每类数据记录：

```text
source_event_time
receive_time
accepted_time
last_valid_identity
age
freshness_threshold_version
last_rejection_reason
```

### MarketDataContinuity

- candle gap；
- duplicate；
- same identity conflict；
- time reversal；
- open candle misuse；
- reconnect gap；
- backfill completion。

### StrategyReadiness

- warm-up；
- required data；
- strategy/config version；
- regime dependency；
- current state eligibility；
- expired lifecycle cleanup。

### NotificationHealth

- local outbox persisted；
- downstream request；
- downstream completed；
- failure classification；
- user-visible latency。

### AccountHealth

执行路线选择后增加：

- account/subaccount identity；
- snapshot age；
- available margin；
- positions；
- open orders；
- leverage/mode；
- API Wallet binding；
- external order conflicts。

### ExecutionHealth

- execution service；
- single writer；
- order/user stream；
- local/venue reconciliation；
- in-flight and unknown outcome；
- last successful round trip；
- execution database state。

### ProtectionHealth

- current position；
- stop/TP confirmed；
- reduce-only；
- protection quantity；
- orphan protection；
- protection update after partial fill。

## 4.4 顶层输出

建议保留现有用户习惯，同时扩展：

```text
OVERALL_STATUS:
READY / NOT_READY / STATUS_UNKNOWN

SIGNAL_STATUS:
READY / NOT_READY / UNKNOWN

EXECUTION_STATUS:
READY / NOT_READY / UNKNOWN / NOT_APPLICABLE

PROTECTION_STATUS:
READY / NOT_READY / UNKNOWN / NOT_APPLICABLE

PRIMARY_REASON:
...

SAFE_ACTION:
...
```

示例：

```text
SIGNAL_STATUS=READY
EXECUTION_STATUS=NOT_READY
PRIMARY_REASON=ACCOUNT_STATE_STALE
SAFE_ACTION=DO_NOT_SUBMIT
```

## 4.5 新鲜度阈值原则

不同数据不得共享一个固定秒数。

- activeAssetCtx：First Launch 的 15 秒可作为初始基线；
- closed candles：使用预期 close + 宽限；
- BBO/depth：根据实测分布设置更短阈值；
- account/position：确认页面和提交前重新查询或依赖足够新的用户流；
- order state：未知结果不能仅按时间判失败；
- notification：分别记录本地持久化、下游成功和用户看到。

阈值必须：

- 版本化；
- 可测试；
- 由真实延迟分布校准；
- 缺失或检查失败时 fail closed。

## 4.6 最小实现顺序

1. 保留 `ta-status` 顶层分类；
2. 增加内部 component reason codes；
3. 给每类数据保存 source/receive/accepted 时间；
4. 增加 subscription readiness 和 reconnect gap；
5. 执行路线选择后增加 AccountHealth；
6. Testnet 前增加 ExecutionHealth；
7. 真实仓位前增加 ProtectionHealth；
8. 自动批准前增加硬门禁和告警。

---

# 5. 建议的 V0 技术架构

## 5.1 自有领域权威

Trader Assist 保留：

```text
Market Evidence
→ Causal Data Authority
→ Strategy
→ TradePlan
→ Product Risk Policy
→ Human Decision
→ ExecutionIntent
```

外部框架不得：

- 更改 side；
- 扩大 quantity；
- 放宽 chase；
- 延长 expiry；
- 删除 reduce-only；
- 提高风险；
- 自动把不可执行计划转换为 market order；
- 将自己的 Strategy 对象变成产品权威。

## 5.2 Anti-Corruption Layer

稳定边界对象建议为：

```text
TradePlanVx
OrderPreviewV1
ExecutionIntentV1
RiskDecisionV1
ExecutionEventV1
AccountSnapshotV1
ReconciliationSnapshotV1
ExecutionOutcomeV1
```

第一版不需要把每个对象做成大型通用 schema。

要求只有：

- 版本化；
- stable ID；
- canonical hash；
- exact plan binding；
- 明确时间语义；
- unknown 状态不被伪装成失败；
- adapter 可替换。

## 5.3 默认双进程模型

### Strategy/Public Runtime

- 继续运行现有策略和公共数据；
- 不引入私钥；
- 不持有 nonce；
- 不直接 import 写入 adapter；
- 生成 TradePlan 和 ExecutionIntent。

### Execution Guard

- 独立进程和独立权限；
- 唯一 signer；
- 单一 writer；
- 服务端重新验证；
- 读取真实账户、订单、仓位；
- 风险门禁；
- submit/cancel；
- 部分成交；
- protection；
- reconciliation；
- kill/pause；
- 独立 execution.db。

### IPC

V0 首选：

- 本地 Unix Domain Socket；
- 不开放网络端口；
- distinct Unix users；
- 文件权限；
- peer UID 验证；
- strict bounded schema；
- request ID；
- timeout 后不生成随机新 intent 重试。

## 5.4 为什么不在同一进程

同进程的模块边界、import guard 和 code review 不构成权限边界。

策略进程一旦失控，只要能访问私钥，就可能直接构造有效写请求。

双进程的核心价值是：

> Strategy 进程即使完全失控，也没有签名材料。

## 5.5 为什么不拆成更多服务

首版不把：

- Supervisor；
- Risk；
- Signer；
- Reconciliation；

拆成四个部署单元。

它们可以作为 Execution Guard 内部模块。

只有出现：

- 多主机；
- 多 writer；
- 多账户；
- 多执行团队；
- 合规或隔离要求；

才重新评估进一步拆分。

---

# 6. 开源框架的 V0 使用裁决

## 6.1 Hyperliquid 官方 SDK

**定位：** 最小执行 adapter 首选候选。

适合：

- 单 venue；
- ETH；
- API Wallet；
- Testnet；
- 订单、撤单和查询；
- 薄 Execution Guard。

不提供：

- 项目级完整 OMS；
- 自动 reconciliation 设计；
- 产品风险；
- 用户确认；
- 权限治理。

裁决：

```text
WRAP_AND_SPIKE
```

## 6.2 NautilusTrader

当前官方文档显示 Hyperliquid adapter 支持：

- live data；
- execution；
- external order detection；
- startup/periodic reconciliation；
- order/fill/position reports；
- reconnect/resubscribe。

它可能减少状态恢复自研，但仍需验证：

- 是否能只使用 ExecutionClient；
- 自定义 Risk Gateway 能否覆盖所有写路径；
- 部署与学习成本；
- 与现有数据和策略是否完全隔离；
- edge cases 对本项目是否足够。

裁决：

```text
REFERENCE_AND_BOUNDED_BAKEOFF
```

不提前整体迁移。

## 6.3 Hummingbot

当前 Hummingbot 提供：

- Hyperliquid spot/perp connectors；
- Testnet；
- Strategy V2；
- Controllers；
- Position/Grid/TWAP 等 Executors；
- InFlightOrder 和用户流等 connector 能力。

适合：

- 订单执行实验；
- 做市/网格研究；
- 标准 Executor 复用评估。

不适合默认成为：

- Trader Assist 策略权威；
- V0 首版完整运行平台；
- 震荡策略盈利保证。

裁决：

```text
EXECUTION_LAB_OR_RANGE_STRATEGY_LAB
NOT_DEFAULT_CORE
```

## 6.4 Freqtrade

当前官方文档提供：

- Hyperliquid 数据/交易所支持；
- backtesting；
- lookahead-analysis；
- recursive-analysis；
- 结果分析。

适合：

- 策略研究镜像；
- 简单基准；
- 偏差检测；
- 参数敏感性；
- Dry-run 对照。

不适合：

- 替换生产策略生命周期；
- 成为 Signal/TradePlan 权威；
- 自动决定 V0 策略。

裁决：

```text
STRATEGY_RESEARCH_SIDECAR
OWNED_BY_STRATEGY_RESEARCH_PROCESS
```

## 6.5 CCXT

适合：

- 轻量统一 API；
- 辅助研究；
- adapter 备选；
- 多 venue 的未来便利。

风险：

- venue-specific 语义抽象损失；
- 不提供完整 OMS；
- 默认行为必须逐项测试。

裁决：

```text
LIMITED_BAKEOFF_CANDIDATE
NOT_DEFAULT_AUTHORITY
```

## 6.6 systemd、SQLite 和标准工具

继续优先使用：

- systemd；
- SQLite；
- 云快照；
- 标准备份；
- 简单日志轮转；
- provider-native 工具；
- 小型脚本。

不为 V0 建设：

- Kubernetes；
- 分布式数据库；
- 通用消息总线；
- 多区域；
- 机构级监控平台。

---

# 7. 有界 Execution Adapter Spike

## 7.1 何时启动

只有当产品正式选择以下之一：

- Order Preview 后进入 Testnet；
- 人工确认执行；
- 真实账户写入 discovery。

不因未来可能自动交易而提前启动。

## 7.2 候选

最多选择两条主要候选进行实际编码：

1. Official SDK + Thin Adapter；
2. NautilusTrader ExecutionClient 或 Hummingbot Executor 中更匹配的一条。

CCXT 可作为轻量 fallback，不要求四套同时实现。

## 7.3 统一测试问题

- Testnet 下单；
- client order ID / cloid；
- 明确拒绝；
- submit timeout；
- 查询 order status；
- cancel；
- partial fill；
- restart with open order；
- external order；
- account/subaccount binding；
- credential isolation；
- risk gateway position；
- deployment dependency；
- exact event mapping。

## 7.4 时间盒

```text
1–3 个有效开发日
最多两条候选
每条最多一次正常修复
无法闭合则停止
```

不得把 Spike 演变成平台迁移。

## 7.5 选择原则

优先选择：

1. 权限边界清晰；
2. 风险不可绕过；
3. unknown submit 可对账；
4. 部分成交可恢复；
5. 代码和部署成本低；
6. 可以被替换；
7. 不污染现有策略；
8. Testnet 证据可信。

---

# 8. V0 候选开发路线

以下是规划框架，不是授权。

## Stage 0 — First Launch Closeout

- Accepted Real Operation；
- final baseline；
- notification；
- backup/recovery；
- known residuals；
- no exchange write。

## Stage 1 — Gate B 与最小 ReadinessEnvelope

- 信号；
- 用户反应；
- manual gap；
- strategy/regime gap；
- runtime/data/notification reliability；
- component health；
- reason codes。

**退出：** 形成 primary gap 分类。

## Stage 2 — 统一产品与策略规划

必须合并：

- 产品功能规划输入；
- 策略研究输入；
- Deferred Ledger；
- live GitHub；
- Gate B evidence。

输出：

```text
V0_PRODUCT_AND_STRATEGY_SCOPE_DECISION_V1
```

## Stage 3R — Reliability First（条件路线）

当可靠性是首要问题：

- DB lifecycle；
- freshness/continuity；
- notification；
- restart/recovery；
- minimum monitoring。

完成后回到产品决策，不自动进入执行。

## Stage 3E — Account Read + Order Preview（执行路线）

- account/subaccount identity；
- balance/margin；
- position/open orders；
- BBO/spread；
- price deviation；
- risk preview；
- 无写入。

## Stage 4E — Execution Adapter Spike

- 官方 SDK / 外部框架；
- Testnet；
- bounded decision。

## Stage 5E — Execution Guard Shadow

- ExecutionIntent；
- server-side revalidation；
- would-approve/reject；
- execution.db；
- no order submit。

## Stage 6E — Testnet Human-Confirmed Execution

- exact plan approval；
- submit；
- cancel；
- partial fill；
- protection；
- reconciliation；
- restart；
- unknown result。

## Stage 7E — Tiny Mainnet Human-Confirmed Pilot

- isolated capital；
- ETH only；
- low leverage；
- every order confirmed；
- human online；
- automatic protection；
- explicit stop rules。

## Stage 8E — Supervised Auto Approval

只有在：

- 信号价值成立；
- 人工确认主要是机械步骤；
- 执行稳定；
- 风险和保护通过；
- 用户明确授权；

才评估。

## Stage 3S — Strategy First（条件路线）

由策略团队提出：

- current strategy verdict；
- baseline/ablation；
- regime gap；
- candidate strategy；
- data requirement；
- shadow acceptance。

新策略默认：

```text
SHADOW_ONLY
NO_ACCOUNT_AUTHORITY
NO_EXCHANGE_WRITE
```

## 并行规则

允许：

```text
Execution Testnet Lane
+
Strategy Shadow Lane
```

条件：

- 文件隔离；
- Writer 隔离；
- 权限隔离；
- 策略 Lane 无真实资金；
- Integration point 已冻结。

---

# 9. 功能分类基线

## 9.1 V0 开发前必需输入

- First Launch final baseline；
- Gate B evidence；
- Deferred Ledger reconciliation；
- live GitHub state；
- strategy research verdict；
- primary gap classification；
- V0 objective；
- authority boundary；
- acceptance criteria。

## 9.2 所有路线都需要的最小能力

- component health reason codes；
- data source/receive/accepted timestamps；
- signal/plan stable IDs；
- configuration/version binding；
- minimum result evidence；
- safe stop/replan rules。

## 9.3 执行路线选择后必需

- Account Read；
- Order Preview；
- exact approval semantics；
- ExecutionIntent；
- Execution Guard；
- credential lifecycle；
- single writer；
- order lifecycle；
- reconciliation；
- protective order lifecycle；
- execution outcome。

## 9.4 策略路线选择后必需

- strategy economic hypothesis；
- production/research parity；
- baseline and ablation；
- signal independence；
- cost/fill model；
- state/regime attribution；
- promotion/pause/retire rules。

## 9.5 Evidence Triggered

- complementary strategy；
- Freqtrade research mirror；
- Hummingbot range lab；
- L2/trades/OFI/CVD；
- PWA/Dashboard；
- supervised automatic approval；
- BTC/ETHBTC；
- advanced reporting。

## 9.6 Deferred

- complete multi-strategy hot plug；
- full StrategyManifest platform；
- automatic strategy switching；
- unattended trading；
- multi-host；
- HA；
- distributed fencing；
- universal data platform；
- institution-grade audit；
- automatic production parameter mutation；
- AI authoritative trading。

---

# 10. 真实执行前的最低安全不变量

1. Strategy 进程无签名凭据；
2. 唯一 Execution Guard writer；
3. intent 绑定 exact plan/hash/version；
4. expired intent 不执行；
5. confirm 后重新检查市场和账户；
6. stale、gapped、unreconciled 时不增加新风险；
7. timeout 不等于失败；
8. unknown 状态先对账；
9. venue facts 高于 local memory；
10. duplicate intent 不重复提交；
11. 部分成交按真实数量保护；
12. protection 未确认时不继续增仓；
13. KILLED 后不自动 re-arm；
14. 真实资金初期逐笔人工确认；
15. 资金隔离且全部损失可接受；
16. 任何权限扩展需用户单独授权。

---

# 11. V0 最终规划前必须解决的问题

## 11.1 产品目标

- V0 一句话目标是什么？
- 首要用户问题是什么？
- 是可靠性、执行、策略还是证据？
- V0 是否包含 Testnet？
- V0 是否包含真实资金？
- V0 成功的最低证据是什么？

## 11.2 Gate B 证据

- 信号样本是否足够？
- 是否存在重大数据污染？
- 信号质量如何？
- MANUAL_EXECUTION_GAP 多大？
- REGIME_COVERAGE_GAP 多大？
- 系统可靠性是否足以判断策略？
- 继续取样是否是合法结论？

## 11.3 数据新鲜度

- 每种数据的 source/receive/accepted 时间是什么？
- 哪些依赖是 mandatory？
- freshness threshold 如何校准？
- reconnect 后如何发现 gap？
- backfill 的最小范围是什么？
- SIGNAL_READY 和 EXECUTION_READY 如何区分？
- status 自身失败时如何 fail closed？

## 11.4 健康状态

- 顶层向用户展示什么？
- reason codes 如何稳定？
- 哪些状态允许看信号但禁止下单？
- AccountHealth 的最大允许 age？
- order/user stream 断开如何处理？
- ProtectionHealth 不通过时允许哪些动作？
- STATUS_UNKNOWN 的人工流程是什么？

## 11.5 用户确认

- CLI、Web/PWA、Discord 还是其他？
- delivered/viewed/approved 如何区分？
- 是否要求身份认证？
- plan 是否只能批准一次？
- approval 是否绑定 exact hash？
- expiry 后界面如何失效？
- confirm 后价格变化多少必须拒绝？

## 11.6 账户与资金

- subaccount 还是独立低资金账户？
- API Wallet 和账户关系？
- 是否允许人工外部订单？
- 最大资本、单笔风险、总 notional、杠杆、日损？
- credential rotation/revoke 流程？
- account snapshot 和 position facts 的权威来源？

## 11.7 执行

- 订单类型？
- post-only/IOC/GTC 使用边界？
- market 行为如何限制？
- partial fill policy？
- protection failure policy？
- cancel timeout？
- submit unknown？
- restart reconciliation？
- external order ownership？
- KILLED_RISK 与 KILLED_INTEGRITY 的行为？

## 11.8 开源复用

- 是否批准 1–3 日 Adapter Spike？
- 选择哪两条候选？
- 是否接受独立 Execution venv？
- 最多接受多少第三方依赖？
- 哪些默认行为必须被 adapter 覆盖？
- 何时停止外部框架集成？
- 是否禁止深度 fork？

## 11.9 策略接口

- 当前策略是否保留、简化、限制或淘汰？
- 哪些 Regime 有效？
- 第二策略是否有独立经济机制？
- 策略需要哪些新数据？
- 新策略是否只 Shadow？
- 策略与执行的冻结接口是什么？
- 多策略何时真正需要？

---

# 12. 与策略团队的统一规划接口

## 12.1 策略团队应提供

```text
V0_STRATEGY_RESEARCH_DECISION_INPUT_V1
```

至少包含：

- current strategy verdict；
- evidence quality；
- baseline and ablation；
- fee/slippage/funding；
- signal independence；
- supported/prohibited market states；
- regime coverage gap；
- candidate complementary strategies；
- required data；
- strategy versioning；
- promotion/pause/retire；
- unresolved research questions。

## 12.2 产品功能规划团队应提供

```text
V0_PRODUCT_FUNCTION_AND_PRIORITY_INPUT_V1
```

至少包含：

- primary user problem；
- selected workflow；
- notification and interface；
- human confirmation semantics；
- health/freshness requirements；
- account and authority request；
- capital boundary；
- included/excluded capabilities；
- product acceptance；
- Deferred Ledger disposition。

## 12.3 合并输出

产品与策略输入必须合并为：

```text
V0_PRODUCT_AND_STRATEGY_SCOPE_DECISION_V1
```

必须回答：

1. 先解决什么；
2. 哪些能力进入 V0；
3. 哪些能力进入 Mainline；
4. 哪些继续延期；
5. 策略、数据、执行如何连接；
6. 哪些权限增加；
7. 哪些证据才能进入下一阶段；
8. 哪些条件触发暂停或重规划。

## 12.4 工程优化和项目总控

合并后的产品决定交给 Engineering Optimization：

- 选择最短技术路径；
- Package；
- adapter；
- Writer/Reviewer；
- Spike；
- tests；
- Repair；
- estimates。

Project Control 只执行已经接受的产品和工程决定。

---

# 13. 最终可执行计划的必要输出

在 V0 正式开发前，必须形成：

```text
V0_PRODUCT_AND_STRATEGY_SCOPE_DECISION_V1
V0_ENGINEERING_STAGE_PLAN_V1
V0_PROJECT_CONTROL_ACTIVATION_PACKET_V1
```

第一份至少包含：

- objective；
- user workflow；
- primary gap；
- evidence；
- strategy verdict；
- selected path；
- selected features；
- health/freshness model；
- open-source reuse；
- account/authority；
- capital limits；
- included/excluded/deferred；
- acceptance；
- stop/replan；
- unresolved questions；
- `UNRECORDED_KNOWN_DEFERRED_ITEMS = 0`。

第二份至少包含：

- exact live repository intake；
- package sequence；
- bounded spikes；
- dependencies；
- path ownership；
- Writer/Reviewer；
- tests/evidence；
- time estimate；
- repair and stop rules；
- rollout/rollback。

第三份才可以授权具体任务。

---

# 14. 资源与复杂度控制规则

1. 不因为未来可能需要而预建通用平台；
2. 一个 V0 里程碑只解决一个首要产品矛盾；
3. 优先现有功能和标准工具；
4. 优先官方 SDK 和薄 adapter；
5. 外部框架最多进行有界试验；
6. 不同时维护多个生产执行引擎；
7. 不深度 fork 大型框架；
8. 两轮仍无法闭合，换路线或降级；
9. 研究代码不自动进入生产；
10. 新策略不自动获得账户权限；
11. Dashboard 不阻塞最小 CLI/Web；
12. 机构级审计不阻塞小资金人工确认；
13. 直接保护资金的安全控制不能延期；
14. 实际运行证据优先于旧 roadmap。

---

# 15. 停止与重规划规则

## 15.1 证据不足

```text
CONTINUE_EVIDENCE_COLLECTION
```

是合法结果。

## 15.2 可靠性不足

先修可靠性，不评价策略，不进入写权限。

## 15.3 策略无价值

如果：

- 不优于简单基准；
- 费用后为负；
- 依赖主观修正；
- 参数极不稳定；
- OOS 失效；

则停止扩展自动执行，返回策略重构。

## 15.4 外部框架不适配

如果：

- 两轮仍不能闭合；
- 需要深度 fork；
- 无法保持权限边界；
- unknown/reconciliation 不可靠；
- adapter 复杂度接近重写；

停止该路线，选择下一候选或官方 SDK 最小自研。

## 15.5 小资金试点异常

立即停止新风险：

- duplicate order；
- unknown unresolved；
- position mismatch；
- protection unmanaged；
- credential/integrity failure；
- risk limit breach；
- wrong account；
- signer/nonce inconsistency。

---

# 16. 当前固定结论与未决结论

## 16.1 已固定

- First Launch 先上线并收集证据；
- V0 追求最快、最省资源；
- 核心策略和产品逻辑自有；
- 外部框架只作为研究或执行能力；
- 数据新鲜度和健康度在写权限前必须升级；
- SIGNAL_READY 与 EXECUTION_READY 分离；
- 执行路线默认采用独立最小权限边界；
- 真实资金初期逐笔人工确认；
- 不提前建设完整多策略、HA 或机构平台；
- 所有延期能力保留；
- 产品与策略必须在 V0 开发前统一规划。

## 16.2 有意未决

- V0 首要路线；
- 是否进入真实资金；
- 执行 adapter；
- 确认界面；
- subaccount/独立账户；
- 资本和风险上限；
- 是否增加第二策略；
- 是否开发 Regime Engine；
- 是否启动 Hummingbot Lab；
- V0 的最终 Package 和排期。

这些问题必须在 First Launch 真实证据和策略团队输入形成后裁决。

---

# 17. GitHub 与权限状态

本文应保存在独立 Draft 文档 PR 中。

它是：

```text
PLANNING_BASELINE
NOT FINAL V0 SCOPE
NOT ENGINEERING TASK
NOT WRITE LEASE
NOT RUNTIME AUTHORITY
NOT EXCHANGE-WRITE AUTHORITY
```

在 V0 最终规划前，需要重新核验：

- live main；
- open PRs；
- CI；
- Accepted Real Operation；
- Gate B；
- First Launch final baseline；
- Deferred Ledger；
- 产品与策略研究结论；
- 第三方框架最新版本和维护状态。

---

# 18. 结论

V0 的正确方向不是“选择一个成熟框架并把系统迁进去”，也不是“继续把所有底座自己开发完”。

正确路线是：

```text
保留 Trader Assist 的策略、风险和产品权威
→ 建立最小 Health/Freshness 可判定能力
→ 通过稳定边界合同连接成熟工具
→ 用有界 Spike 选择执行能力
→ 从人工确认 Testnet 和极小资金开始
→ 由真实证据决定自动化和多策略
```

产品和策略团队最终必须共同回答：

```text
当前真正有效的交易观点是什么？
用户当前真正损失在哪个环节？
系统需要增加哪一种最小能力？
需要增加多少权限？
什么证据证明可以进入下一阶段？
```

只有这些问题回答清楚后，才应生成 V0 最终可执行计划。
