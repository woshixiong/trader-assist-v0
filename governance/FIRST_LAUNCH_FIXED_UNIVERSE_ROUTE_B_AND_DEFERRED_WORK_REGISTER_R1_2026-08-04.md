# First Launch 固定 Universe 快速路线 B 与延期任务总登记 R1

**记录 ID：** `TA-FIRST-LAUNCH-FIXED-UNIVERSE-ROUTE-B-DEFERRED-WORK-R1-2026-08-04`  
**日期：** `2026-08-04`  
**仓库：** `woshixiong/trader-assist-v0`  
**状态：** `ENGINEERING_ROUTE_PROPOSAL / DEFERRED_BACKLOG_REGISTER / PENDING_PRODUCT_AND_STRATEGY_ACKNOWLEDGMENT / NON_EXECUTABLE`  
**任务派发权威：** `PROJECT_CONTROL_ONLY`  
**目的：** 记录用户选择的固定 Universe 快速首发路线、首发不可删除的功能、为提速而延期但不得放弃的工作，以及后续重新启动这些工作的触发条件。

本文不修改机器策略公式、Setup 语义、Scanner 语义、交易权限或账户权限。本文只调整工程交付顺序。Product Optimization 与 Strategy Optimization 完成同步确认之前，本文不得被解释为已经取代 PR #52 当前权威索引或总任务登记表。

---

## 1. 用户选择与工程结论

用户选择采用：

```text
ROUTE_B = FIXED_USER_SELECTED_UNIVERSE_FAST_SHADOW_RELEASE
```

核心顺序调整为：

```text
USER-SELECTED FIXED UNIVERSE
→ TIMEBOXED SELECTED-MARKET NAUTILUS DATA FIT
→ MINIMUM MULTI-ASSET SHADOW IMPLEMENTATION
→ FIXED-UNIVERSE HEALTH / RECONNECT / RESOURCE VALIDATION
→ HUMAN-CONTROLLED DEPLOYMENT
→ SHADOW FORWARD VALIDATION
→ POST-LAUNCH FULL CAPACITY / QUALITY / UNIVERSE EXPANSION
```

首发前不再要求完成：

```text
8 → 16 → 32 → 64 → 128 → ...
FIRST FAILURE
BOUNDARY CONVERGENCE
FULL-MARKET QUALITY DISTRIBUTION
FINAL DYNAMIC APPROVED UNIVERSE
```

但完整容量、质量和 Universe 扩展工作仅被延期，不得取消。

固定状态：

```text
FULL_GATE_A_BEFORE_INITIAL_RELEASE = DEFERRED
INITIAL_UNIVERSE = USER_SELECTED_AND_VERSIONED
INITIAL_RELEASE_CAPACITY_CLAIM = FIXED_UNIVERSE_HEALTH_ONLY
POST_LAUNCH_FULL_GATE_A = REQUIRED
```

---

## 2. 为什么调整顺序

完整 Gate A 是首发前最耗费时间、但又可以在不破坏首发核心价值的情况下后移的工作。它包含：

- 全市场公共快照；
- 自动扩张与首次失败；
- 容量边界收敛；
- 完整质量指标与分布；
- 质量校准样本；
- 相关性数据成本验证；
- 多档 30/75 分钟综合 Profile；
- 质量门槛再次冻结；
- 最终 Universe 数量冻结。

这些工作主要解决未来扩大扫描范围和自动化资格问题，不是固定小范围 Shadow 首发的必要前置。

用户指定的市场是未来主要关注和可能交易的市场。首发样本范围会较窄，但样本本身仍可有效用于：

- 验证 Scanner 与三 Setup；
- 验证完整 Shadow 证据链；
- 获取用户熟悉市场的真实前向结果；
- 快速发现策略与工程缺陷；
- 支持小步迭代。

本次调整服从：

```text
TEST SMALL
→ OBSERVE REAL EVIDENCE
→ REVIEW
→ IMPLEMENT THE MINIMUM COHERENT CHANGE
→ FORWARD VALIDATE
→ ITERATE
```

---

## 3. 首发绝对不可删除的功能

以下内容是路线 B 的最低完整产品，任何进一步压缩不得删除或降级。

### 3.1 固定、版本化、用户批准的初始 Universe

首发必须使用配置化、版本化的固定名单，不得把名单散落硬编码在策略逻辑中。

至少保存：

```text
universe_version
market_id
raw_dex
raw_coin
asset_class
enabled
approved_by_user_at
```

首发不要求自动 Refresh、热更新或 Auto Apply；名单变更可以通过受控配置更新和服务重启完成。

### 3.2 针对所选市场的最小 Nautilus 数据适配门

NautilusTrader 继续作为第一候选，但验证必须缩小到用户实际选择的市场和首发所需数据。

固定时间盒：

```text
NAUTILUS_SELECTED_MARKET_DATA_FIT_TIMEBOX <= 4 HOURS
```

只验证：

- 所选 native perpetual；
- 所选 HIP-3 / builder perpetual（如初始名单包含）；
- raw DEX / coin / project market_id；
- price / size precision；
- closed 5m candle；
- fresh BBO；
- reconnect / resubscribe / backfill；
- stale or missing data fail closed。

不得为了通过该门而进行多日框架修复或维护大型 fork。

如果在时间盒内不能满足首发所选市场：

```text
SAFE STOP NAUTILUS PATH
→ USE OFFICIAL HYPERLIQUID API/SDK THIN DATA ADAPTER FOR INITIAL SHADOW RELEASE
→ KEEP NAUTILUS AS POST-LAUNCH REEVALUATION
```

### 3.3 Scanner 与三 Setup 完整语义

固定 Universe 内必须保留：

- Scanner WATCH；
- Scanner SETUP_READY；
- Candidate 与 Formal Event 分离；
- SWEEP_RECLAIM；
- BREAKOUT MICRO FAST；
- state-driven BREAKOUT STANDARD；
- RANGE_EDGE_REJECTION；
- Long / Short 对称语义；
- Formal Event 的事实状态终止；
- 禁止用固定时间或固定 K 线数终止正式 STANDARD。

不得为了提速删除某个 Setup、把 WATCH 当正式信号，或把 Scanner 窗口反向覆盖正式策略状态。

### 3.4 资产无关核心合同

必须保留：

```text
MarketIdentity
ClosedBar / MarketSnapshot
MarketEvent
StrategyState
StrategyDecision
PlanDraft / TradeIntent
ShadowOrder
Annotation
OutcomeRecord
```

Strategy Kernel 不得直接依赖 Nautilus、Hummingbot、Discord、数据库 session、账户或真实订单类型。

### 3.5 完整 Shadow 产品结果

所有固定 Universe 内的完整 Formal Setup 必须生成：

- direction；
- setup family；
- ideal entry zone；
- planned entry；
- chase limit；
- structural stop；
- TP1 / TP2（如存在）；
- gross R / cost / net R；
- liquidity / execution warning；
- 1% / 2% 参考数量和名义金额；
- `NOT_SUBMITTED` ShadowOrder；
- T/S/R；
- 30/60/120m Outcome；
- 导出与完整性检查。

不得因为首发 Universe 较小而降低每个市场的结果完整度。

### 3.6 为延期研究保留不可重建证据

相关聚类可以延后计算，但输入不得丢失。

首发必须：

- 为固定 Universe 启动时取得足够的闭合 5m 历史，目标覆盖相关研究需要的最近 14 日；
- 持续保存固定 Universe 的闭合 5m 时间轴或可审计的等价证据；
- 为 Formal Signal 保存确认前数据身份、Candle Data Hash 和版本；
- Formal Signal 后优先保存 1m 路径，用于 Stop/TP 顺序和 Outcome；
- 保存 market_id、setup、side、confirmed_at、strategy/parameter/scanner version。

在相关聚类功能完成前，任何报告必须标记：

```text
RAW_SAMPLE_COUNT_ONLY
INDEPENDENCE_NOT_ADJUSTED
```

不得把 Raw ShadowOrder Count 描述为独立策略样本数量。

### 3.7 数据正确性、恢复与最小遥测

必须保留：

- closed-candle 因果语义；
- 15m / 1h 从统一闭合 5m 时间轴本地聚合；
- missing / duplicate / conflicting / out-of-order bar 检测；
- fresh BBO；
- reconnect / resubscribe / REST backfill；
- idempotent state / evidence commit；
- API request / 429 / timeout；
- WS disconnect / reconnect；
- CPU / memory；
- SQLite commit latency；
- full-cycle latency。

这些遥测直接进入首发 Runtime，不单独建设通用容量平台。

### 3.8 通知、故障隔离与回滚

必须保留：

```text
SINGLE_ACTIVE_NOTIFICATION_AUTHORITY
NEW_SYSTEM FAILURE DOES NOT AFFECT SING-BOX
LEGACY ETH CODE / CONFIG / ROLLBACK MATERIAL PRESERVED
```

旧 ETH 服务可以停止，但不得删除回滚材料或侵入式迁移旧 `runtime.db`。

### 3.9 部署前强制阻断

以下不是延期任务，仍是下一次生产部署前强制完成项：

```text
FIRST_LAUNCH_RECONNECT_BUDGET_RESET
TRADER_ASSIST_OFF_HOST_BACKUP_AND_RECOVERY_VERIFICATION
FULL CI
INDEPENDENT REVIEW
ROLLBACK READINESS
PRODUCTION SMOKE
```

Lightsail 快照在主机外备份、下载验证和恢复演练完成前不得删除。

---

## 4. 进一步压缩后明确不进入首发的内容

### 4.1 不建设独立完整 Capacity Harness

首发不单独建设长期 Benchmark 平台、通用 Backend 插件系统或全市场压测服务。

首发 Runtime 只嵌入可复用遥测。上线后完整 Gate A 可以增加一个有界自动扩张 Runner，复用这些遥测与数据模型。

### 4.2 不建设自动 Universe Refresh

首发使用静态、版本化、用户批准的名单。

延期：

- global refresh scheduler；
- validate / diff；
- candidate Universe；
- atomic apply；
- hot reload；
- auto apply；
- turnover policy。

### 4.3 不计算完整市场质量分布

首发只对固定名单执行最低运行健康检查：

- active market；
- valid identity / metadata；
- price / size precision；
- usable closed history；
- fresh BBO；
- no sustained 429；
- no unresolved missing/conflicting data；
- runtime resource stability。

延期完整 Spread、Depth、Slippage、Return Concentration、Large-jump Reversal、Zero-volume、Mark/Oracle、Session Calendar 和跨抵押资产美元换算资格体系。

### 4.4 不计算相关事件簇

首发不实现：

- Pairwise correlation matrix；
- Setup Research Cluster；
- Exposure Cluster；
- Cluster-normalized metrics；
- Leader-only sensitivity；
- Cluster-normalized drawdown。

但必须保存第 3.6 节规定的输入，并禁止把 Raw 数量解释成独立样本。

### 4.5 不验证完整未来执行生命周期

首发不验证：

```text
TradeIntent
→ Approval
→ Account Risk
→ Accepted
→ Partial Fill
→ Filled
→ Position
→ Exit
```

但 `PlanDraft / TradeIntent` 必须保持执行无关，未来不得因增加半自动执行而重写 Scanner、Strategy Kernel 或 Evidence Identity。

### 4.6 不寻找 Nautilus 精确最大容量

首发只验证固定 Universe 可以稳定运行。

不得声称：

```text
SELECTED_FRAMEWORK_MAX_CAPACITY = N
```

只允许声称：

```text
FIXED_INITIAL_UNIVERSE_HEALTH = PASS / FAIL
```

### 4.7 不做非必要扩展

首发不做：

- Hummingbot；
- Freqtrade；
- 自动交易；
-账户 / 私钥 /签名；
-实时动态退出引擎；
-组合资金仲裁；
-多 Venue；
-第四 Setup；
-Range STANDARD；
-OI / funding 作为 Setup 硬触发；
-复杂 Dashboard；
-完整 Event Sourcing 平台；
-旧 ETH Schema 迁移；
-旧 ETH 运行时永久下线。

---

## 5. 路线 B 的风险与控制措施

### 5.1 容量上限未知

风险：无法知道目标服务器和 API 的完整市场极限。

控制：

- 初始名单保持小规模；
-上线前固定名单健康测试；
-嵌入 API、WS、资源和 SQLite 遥测；
-禁止在完整 Gate A 前自行扩大 Universe；
-上线后优先执行完整容量测试。

### 5.2 策略样本范围较窄

风险：不能代表所有 Hyperliquid 市场。

控制：

-明确将结果解释为固定市场前向验证；
-优先覆盖用户未来真实关注市场；
-不宣称完成全市场泛化；
-完整容量与质量测试后再扩大范围。

### 5.3 市场质量门槛未冻结

风险：首发名单不是自动质量模型选出的市场。

控制：

-名单由用户明确批准；
-执行最低运行健康门；
-所有输出保留流动性和执行警告；
-仍然没有真实交易权限；
-质量分布返回后再冻结正式资格门槛。

### 5.4 相关信号暂未归组

风险：同步市场信号会夸大样本量。

控制：

-保存完整 5m 输入；
-Raw 报告明确标记未进行独立性调整；
-不得以 Raw Count 作为主要策略证据；
-上线后补算相关 Cluster。

### 5.5 Nautilus 长期执行能力未验证

风险：未来半自动执行可能需要额外适配或改换引擎。

控制：

-首发只使用公共数据和 Shadow；
-保持项目 MarketSnapshot / TradeIntent / Evidence 合同独立；
-完整 Sandbox Execution Fit 在半自动开发前完成；
-出现重要缺口时才触发 Hummingbot 专项研究。

---

## 6. 延期任务总登记

以下任务状态均为 `DEFERRED_NOT_CANCELLED`。

### P1：固定 Universe 上线后优先完成

#### `RB-D01 FULL_RAW_API_SERVER_CAPACITY_SPIKE`

内容：

- 全市场 metadata/context；
- 8/16/32/64/128/... 自动扩张；
- 首次失败与边界收敛；
- Profile A 增量 Bootstrap；
- Profile B/C/D 30/75 分钟综合负载；
- 429、WS、CPU、内存、延迟和 SQLite 边界；
- `RAW_API_SERVER_SAFE_CAPACITY`。

触发：固定 Universe 首发稳定后立即排入优先队列。

#### `RB-D02 FULL_MARKET_QUALITY_DISTRIBUTION_AND_ELIGIBILITY`

内容：

- Day Notional / OI；
- Spread；
- 10/20bps Weak Depth；
- Depth Balance；
- History / Completeness；
- Return Distribution；
- Top-5 Concentration；
- Large-jump Reversal；
- Zero-volume；
- Mark/Oracle；
- Session Calendar；
- Collateral USD Conversion；
- 24 市场质量校准样本；
-精确质量门槛和有序合格名单。

依赖：`RB-D01` 的市场和容量数据。

#### `RB-D03 SELECTED_FRAMEWORK_CAPACITY_CONFIRMATION`

内容：

- 使用选定框架和计划扩大后的市场数量；
- 测试计划数量加安全余量；
- 失败时有限收敛；
- 得到 `SELECTED_FRAMEWORK_CAPACITY_AT_LEAST`。

依赖：质量合格有序名单和 Nautilus 数据适配结论。

#### `RB-D04 VERSIONED_UNIVERSE_REFRESH_AND_EXPANSION`

内容：

- periodic global snapshot；
- validate / diff；
- versioned candidate；
- atomic apply；
- hot reload on next closed 5m；
-前两次人工 Review；
- turnover 记录；
-后续 7/14 天周期裁决；
- Auto Apply 安全门。

依赖：`RB-D01`、`RB-D02`、`RB-D03`。

#### `RB-D05 CORRELATED_SIGNAL_CLUSTERING_AND_NORMALIZED_RESEARCH`

内容：

- 14 日 5m Pearson correlation；
- Setup Research Cluster；
- Exposure Cluster；
- Complete-linkage；
- Cluster Identity；
- Raw / Cluster-normalized / Leader-only；
- Cluster-normalized drawdown；
- Cluster Compression Ratio；
- Correlation Unknown。

依赖：首发保存的 5m 数据、ShadowOrder 和 Outcome。

### P2：进入半自动或完整 V0 前完成

#### `RB-D06 NAUTILUS_FULL_SANDBOX_EXECUTION_FIT`

内容：

- Approval Fixture；
- Account Risk Adapter；
- order accepted / rejected；
- partial fill / fill；
- position lifecycle；
- exit；
- reconnect and reconciliation；
-启动恢复；
- TradeIntent 到订单映射。

触发：开始任何真实账户、Testnet 或半自动实现之前。

#### `RB-D07 SEMI_AUTOMATIC_EXECUTION_AND_RECONCILIATION`

内容：

-账户与私钥边界；
- Human Approval；
- execution_valid_until；
- BBO / chase / risk recheck；
- protective stop；
- order / fill / position reconciliation；
- manual override detection；
- duplicate order protection；
- exchange as final truth。

当前无交易所写权限。

#### `RB-D08 DYNAMIC_POSITION_MANAGEMENT_AND_EXIT_ENGINE`

内容：

- HOLD；
- TIGHTEN_STOP；
- BREAK_EVEN / PROFIT_LOCK；
- PARTIAL_EXIT；
- FULL_EXIT；
-结构跟踪；
-趋势衰减和反转；
-分段退出与重新入场；
-人工确认后执行。

当前仅保留 Entry、Initial Stop、Reference R、结构目标和离线路径 Outcome。

#### `RB-D09 LIVE_EXPOSURE_CLUSTER_RISK_GATE`

内容：

- `ONE_NEW_POSITION_PER_EXPOSURE_CLUSTER`；
-或经过另行冻结的共享 Cluster 风险预算；
-组合相关风险与现有仓位检查。

触发：任何半自动或自动真实交易之前。

#### `RB-D10 LEGACY_ETH_RUNTIME_RETIREMENT`

内容：

- ETH data parity；
-新系统信号链通过；
-多资产前向验证接受；
-Evidence 完整；
-故障隔离；
-回滚测试；
-用户 Cutover 授权；
-旧服务永久下线或归档。

### P3：条件触发或长期 Backlog

#### `RB-D11 HUMMINGBOT_SPECIALIZED_EXECUTION_SPIKE`

仅当 Nautilus 出现明确且重要的执行缺口时触发。不得并行建设两个订单或仓位权威。

#### `RB-D12 FREQTRADE_OR_LONG_TERM_BACKTEST_REEVALUATION`

仅当：

-前向样本过慢；
-需要大量参数比较；
-需要罕见历史行情；
-准备自动交易或扩大资金；
-组合风险验证需要；
-真实样本等待成本不可接受；

时重新评估。

#### `RB-D13 FUTURE_STRATEGY_EXPANSION`

包括：

-第四 Setup；
-Range STANDARD；
-OI / funding 作为硬触发；
-大规模参数优化；
-新的外部策略机制。

必须由新证据触发，不得在首发前增加。

#### `RB-D14 MULTI_VENUE_AND_PORTFOLIO_CAPITAL_ARBITRATION`

包括多交易所、组合级资金分配、组合回撤与资本竞争。当前不是 First Launch 范围。

#### `RB-D15 FULL_EVENT_SOURCING_OR_COMPLEX_DASHBOARD`

只有成熟外部工具能够明显降低总成本、且实际规模证明需要时才重新评估。

#### `RB-D16 FULL_HOST_QUALIFICATION_AUTOMATION`

保持最低优先级。普通低频部署继续使用现有命令、检查表和临时任务包；不得恢复或继续修补历史失败的复杂自动化路线。

#### `RB-D17 SCHEDULED_BACKUP_AUTOMATION_BEYOND_MINIMUM_GATE`

下一次部署前仍必须完成最小主机外备份与恢复验证。更完整的定时、保留、告警和长期自动化可在最低闭环通过后单独排期。

#### `RB-D18 SYSTEMD_RESTART_POLICY_ENHANCEMENT`

`Restart=on-failure` 只能作为独立增强评估，不得替代 reconnect-budget 源码修复。

---

## 7. 上线后建议执行顺序

```text
1. 固定 Universe Shadow 稳定性与证据完整性 Review
2. RB-D01 完整 API / 服务器容量测试
3. RB-D02 质量门槛和有序合格名单
4. RB-D03 选定框架容量确认
5. RB-D04 Universe Refresh 与扩大范围
6. RB-D05 相关 Cluster 与归一化统计
7. 根据前向证据迭代策略
8. 在真实执行前完成 RB-D06 / D07 / D09
9. 根据证据和用户授权研究动态退出与旧 ETH 下线
```

该顺序允许部分独立研究并行，但不得跨越账户、交易所写入或用户授权门禁。

---

## 8. 当前首发范围摘要

```text
KEEP_NOW:
- user-selected versioned fixed Universe
- selected-market Nautilus data fit with fast fallback
- Scanner
- all three Setup families and required modes
- MarketIdentity / MarketSnapshot / Strategy Kernel
- PlanDraft / TradeIntent
- NOT_SUBMITTED ShadowOrder
- complete signal fields and reference sizing
- T/S/R
- 30/60/120m Outcome
- evidence / export / completeness
- raw 5m preservation for future correlation
- 1m path for formal Outcome
- reconnect / backfill / fail closed
- minimum runtime telemetry
- Discord with single notification authority
- reconnect-budget source fix
- off-host backup and recovery gate
- CI / independent Review / rollback / smoke

DEFER:
- full capacity boundary
- full market quality eligibility
- dynamic Universe Refresh
- correlation clusters and normalized metrics
- exact Nautilus capacity boundary
- full Nautilus Sandbox execution lifecycle
- Hummingbot / Freqtrade
- semi-auto / auto execution
- dynamic exit engine
- portfolio and multi-venue systems
- old ETH permanent retirement
```

---

## 9. 权限边界

本文不授权：

-代码修改；
-依赖安装；
-AWS 操作；
-服务停止或启动；
-部署；
-permit 修改；
-账户访问；
-私钥；
-签名；
-交易所写入；
-自动下单；
-PR Mark Ready 或 Merge；
-删除 Lightsail 快照。

产品窗口和策略窗口同步确认后，由 Engineering Optimization 重新形成精确工作包，再由 Project Control 唯一派发。