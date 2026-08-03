# First Launch 多资产并行替代架构决策 R1

**记录 ID：** `TA-FIRST-LAUNCH-MULTI-ASSET-PARALLEL-REPLACEMENT-R1-2026-08-03`  
**日期：** `2026-08-03`  
**状态：** `CURRENT ARCHITECTURE DECISION / NON-EXECUTABLE / NON-AUTHORIZING`  
**关联：** PR #52、Current Authority Index R1、Strategy Package R1、Scanner R3、Playbook V5  

---

## 1. 决策

采用“小步快跑的并行替代”，不对现有 ETH 生产运行时做大规模侵入式泛化。

```text
CURRENT ETH RUNTIME
→ KEEP UNCHANGED AS FALLBACK / ROLLBACK / COMPARATOR

NEW UNIFIED MULTI_ASSET SYSTEM
→ SUPPORT ETH + ALL ELIGIBLE HYPERLIQUID PERPS
→ GENERATE THE SAME FULL SIGNAL FIELDS FOR EVERY ASSET
→ CREATE NOT_SUBMITTED SHADOW PLAN / SHADOW ORDER
→ HUMAN FINAL DECISION
→ COMPLETE EVIDENCE / T-S-R / OUTCOME / EXPORT
```

新系统稳定并完成前向验证后，再单独授权旧 ETH 运行时下线或归档。

---

## 2. 所有资产的产品结果必须一致

ETH 与非 ETH 不得在“信号完整度”上区分。

当完整三 Setup 条件成立时，每个资产都必须得到：

- market identity；
- direction；
- setup family；
- ideal entry zone；
- planned entry reference；
- chase limit；
- structural stop；
- TP1；
- TP2（如存在第二结构目标）；
- gross R；
- estimated cost R；
- net R；
- liquidity and execution warning；
- reference position size at 1% risk；
- reference position size at 2% risk；
- reference notional；
- `NOT_SUBMITTED` ShadowOrder；
- T/S/R；
- automatic Outcome；
- optional actual manual fill linkage。

差异只存在于市场元数据、价格精度、流动性和风险计算输入，不存在于策略权威和输出字段完整度。

---

## 3. 参考金额与实际账户权威

新系统不访问账户，不拥有下单权威，但仍必须给出可供人工判断的参考金额。

```text
REFERENCE_SHADOW_EQUITY_USD = 200
REFERENCE_RISK_PCT_LOW = 1.0
REFERENCE_RISK_PCT_HIGH = 2.0
REFERENCE_MAX_NOTIONAL_USD = 5000
```

参考数量按 Entry、Stop、费用、滑点、市场 size decimals 和可得的 market max leverage 计算，并明确标记：

```text
REFERENCE_SIZE_ONLY
NOT_ACCOUNT_AUTHORITATIVE
NOT_SUBMITTED
```

如果用户实际手工成交，实际 quantity、entry、fees、exit 和 PnL 进入独立实际成交字段，不得覆盖原 Shadow Plan。

---

## 4. 不采用字面复制两套策略逻辑

允许复制、移植和重写现有代码中有价值的实现模式，但不得形成长期并行维护的两套策略逻辑。

正确方式：

1. 冻结现有 ETH 模块，不修改其 Hash、Authority、RuntimeStore 和回滚语义；
2. 从现有实现中选择性复用：
   - strict parsing；
   - canonical hash；
   - closed-candle validation；
   - Decimal and precision handling；
   - risk math pattern；
   - SQLite transaction / unique identity pattern；
   - notification and idempotency pattern；
3. 在新的资产无关包中形成唯一的新策略核心；
4. 新系统同时评估 ETH 与非 ETH；
5. 旧 ETH 仅保留为冻结保底，不继续同步增加新策略能力。

禁止：

```text
LEGACY_ETH_STRATEGY_LOGIC
+
SEPARATE_NON_ETH_STRATEGY_LOGIC
```

因为两套逻辑会迅速分叉，增加重复开发和结果不可比。

---

## 5. 新系统最小分层

```text
Stage A: Cheap All-Market Discovery
→ metadata / mids / activity / rank

Stage B: Candidate Enrichment
→ closed 5m history / BBO / liquidity / structure-near-level

Stage C: Full Multi-Asset Strategy Evaluation
→ 1h context from closed 5m aggregation
→ 15m zones from closed 5m aggregation
→ 5m setup state
→ formal StrategyDecision
→ PlanDraft

Stage D: Shadow Plan and Evidence
→ NOT_SUBMITTED ShadowOrder
→ T/S/R
→ 30/60/120m Outcome
→ export and completeness report
```

Scanner `WATCH` 只保存 Candidate 和 forward Outcome。

Scanner `SETUP_READY` 只表示进入 Stage C，不等于正式策略成立。

只有 `FORMAL_SETUP_CONFIRMED` 才生成 Shadow TradePlan / ShadowOrder。

---

## 6. 新系统资产无关核心类型

最小公共类型：

```text
MarketIdentity
MarketMetadata
ClosedBar
MarketSnapshot
ZoneSnapshot
MarketEvent
StrategyState
StrategyDecision
PlanDraft
ShadowOrder
Annotation
OutcomeRecord
```

`MarketIdentity` 至少包含：

```text
venue
dex
coin
asset_class
tick_size
size_decimals
max_leverage_if_available
```

策略核心不得依赖：

- `Literal["ETH"]`；
- 旧 RuntimeStore；
- Discord；
- 账户余额；
- Hyperliquid 签名或订单类型；
- 生产 permit；
- 旧 TradePlan Authority 对象。

---

## 7. 数据与运行边界

- Signal generation 只使用已经闭合并收到的 5m 数据；
- 15m 和 1h 由统一闭合 5m 时间轴按 UTC 边界因果聚合；
- 正式 Shadow Plan 创建时使用新鲜 BBO；
- 正式 Shadow Plan 的后续路径优先保存 1m 数据，用于 Stop/TP 顺序和 Outcome；
- 普通 WATCH 的 30/60/120m Outcome 可以使用 5m 路径；
- Scanner、策略核心和证据库不得访问账户、签名或交易所写接口。

---

## 8. 持久化

建立统一多资产研究证据库，例如：

```text
shadow_evidence.db
```

保存 ETH 与所有非 ETH 的：

- scans；
- point-in-time universe；
- candidates；
- state transitions；
- formal strategy decisions；
- plan drafts；
- shadow orders；
- annotations；
- outcomes；
- version identities；
- links to legacy ETH signal/plan when both systems produce comparable events。

现有 `runtime.db` 不迁移、不改 Schema，继续服务旧 ETH 保底运行时。

---

## 9. 一次性工作压缩

本轮不做：

- 旧 RuntimeStore 多资产迁移；
- 旧 TradePlan Hash 版本重写；
- 旧 ETH Authority 泛化；
- 生产数据库跨 Schema 转换；
- 新旧系统双向对象转换；
- 多资产账户和组合风险系统；
- 自动交易；
- 长期回测平台；
- 大型消息或数据库基础设施。

必要的一次性工作仅包括：

- 新旧 ETH 同时运行时的明确标签；
- 最小 parity fixture；
- 独立 systemd / process failure boundary；
- rollback and cutover runbook；
- 未来旧 ETH 下线的条件记录。

---

## 10. 长期价值

以下新能力均为未来可复用资产：

- 统一 MarketIdentity；
- 资产无关 closed-bar model；
- 多资产 Strategy Kernel；
- Scanner Stage A/B/C；
- Candidate/Event ledger；
- PlanDraft and ShadowOrder；
- reference sizing；
- T/S/R；
- automatic Outcome；
- export and completeness；
- versioned forward-validation data。

未来新增 Setup、资产或参数时，不应重新建设上述基础能力。

---

## 11. 下线旧 ETH 运行时的条件

旧 ETH 运行时只有在以下条件全部满足后才可另行下线：

```text
NEW_SYSTEM_ETH_DATA_PARITY = PASS
NEW_SYSTEM_ETH_SIGNAL_PIPELINE = PASS
MULTI_ASSET_FORWARD_VALIDATION = ACCEPTED
EVIDENCE_COMPLETENESS = PASS
FAILURE_ISOLATION = PASS
ROLLBACK_TEST = PASS
USER_CUTOVER_AUTHORIZATION = YES
```

本文件不授权实施、部署、重启、切换或下线。