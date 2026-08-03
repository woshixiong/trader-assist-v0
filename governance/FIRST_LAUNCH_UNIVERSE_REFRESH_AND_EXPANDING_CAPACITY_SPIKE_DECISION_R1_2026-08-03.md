# First Launch Universe Refresh 与自动扩张容量实测决策 R1

**记录 ID：** `TA-FIRST-LAUNCH-UNIVERSE-REFRESH-EXPANDING-CAPACITY-SPIKE-R1-2026-08-03`  
**日期：** `2026-08-03`  
**状态：** `CURRENT SCANNER RESOURCE / UNIVERSE TEST AUTHORITY / NON-PRODUCTION / NON-DEPLOYMENT`  
**关联：** PR #52、Current Authority Index R1、Machine Strategy R1/R1.1、Multi-Asset Architecture R1、Scanner R3、Forward Validation R1  
**目的：** 关闭容量测试方法、周期性 Universe Refresh、影子样本边界、API 使用边界、Active Event 容量解释和下一步实测交付；最终 Universe 资格阈值仍须等待真实数据后冻结。

---

## 1. 当前阻塞项

当前不得继续凭估算冻结：

```text
FINAL_APPROVED_UNIVERSE_COUNT
FINAL_VOLUME_THRESHOLD_OR_RANK
FINAL_OI_THRESHOLD_OR_RANK
FINAL_DEPTH_THRESHOLD
FINAL_SPREAD_THRESHOLD
FINAL_PRICE_IRREGULARITY_THRESHOLD
MAX_ACTIVE_FORMAL_EVENTS
```

下一步唯一正确路径：

```text
CURRENT MARKET SNAPSHOT
→ ORDERED CAPACITY CANDIDATE POOL
→ EXPANDING REAL CAPACITY TEST
→ FIRST FAILURE
→ BOUNDARY CONVERGENCE
→ QUALITY DISTRIBUTION REVIEW
→ EXACT UNIVERSE ELIGIBILITY FREEZE
```

---

## 2. 撤销固定 Top-100 测试法

以下不再采用：

```text
CAPACITY_TEST_POOL = FIXED_TOP_100
FINAL_UNIVERSE = TOP_100
TEST_ONLY_25_50_75_100
```

成交量排名可用于形成容量候选池的稳定顺序，但 `100` 不再是测试终点、最终范围或产品目标。

固定采用自动扩张测试：

```text
N = 8
→ 16
→ 32
→ 64
→ 128
→ continue doubling while candidate pool remains and all gates pass
```

发生首次失败：

```text
LAST_FULL_PASS_N
FIRST_FAIL_N
→ binary search or ≤10-market step convergence
→ MEASURED_FAILURE_BOUNDARY
```

如果当前可用候选池全部通过：

```text
MEASURED_CAPACITY_AT_LEAST = candidate_pool_size
```

不得为证明更大数字而加入明显无研究价值的市场。

---

## 3. 容量候选池不等于 Approved Universe

容量候选池只用于负载测试，不产生正式 ShadowOrder、策略收益样本或 Discord 信号。

候选池形成：

1. 一次性读取全市场公共 metadata/context；
2. 仅保留 active、可形成 canonical market identity、mark/day volume/OI 有效的市场；
3. 按 24h notional volume 降序；
4. tie-break：OI notional 降序、DEX 字典序、coin 字典序；
5. 逐个扩张档位只对当前前缀获取所需 Candle/Book 数据；
6. 当前前缀中历史不足、数据异常或盘口无效的市场记录原因并从有效负载数中剔除，继续向后补足该档位。

容量实测的临时数据不得混入后续正式前向验证数据库。

---

## 4. 正式市场范围原则

正式日常系统只处理最终 `Approved Universe`。

用户不参与且不希望进入正式影子样本的市场：

- 低流动性；
- 低成交量或低 OI；
- 订单簿过薄；
- Spread 或价格冲击异常；
- 数据历史不足；
- 新上线且尚未证明质量；
- 波动路径异常、跳跃集中、无规律或疑似易被控盘；
- 不具备未来自动交易价值的非主流加密市场或薄弱 Builder/HIP-3 市场。

市场准入标准按 `FUTURE_AUTOMATED_TRADING_GRADE` 设计。当前仍无交易所写权限和自动下单，但人工最终判断不得被用来补偿市场质量缺陷。

“山寨币”不得仅依赖币名或 `coin != BTC/ETH` 定义。最终应通过明确的 Volume/OI/Spread/Depth/Price-Regularity/History 指标与可选资产分类共同排除；所有最终条件必须是可编码数值。

---

## 5. 周期性 Universe Refresh

日常系统不得持续触碰全交易所所有市场。

固定流程：

```text
PERIODIC GLOBAL METADATA/CONTEXT SNAPSHOT
→ CHEAP RANK/PREFILTER
→ DEEP QUALITY CHECK ONLY FOR CANDIDATE PREFIX WITHIN MEASURED CAPACITY
→ VERSIONED CANDIDATE UNIVERSE
→ VALIDATE
→ DIFF
→ ATOMIC APPLY
→ NEXT CLOSED 5M BOUNDARY HOT RELOAD
```

Universe 外市场在两次 Refresh 之间：

```text
NO CANDLE SUBSCRIPTION
NO BBO/L2 SUBSCRIPTION
NO SCANNER
NO FORMAL EVENT
NO SHADOW ORDER
NO FORMAL OUTCOME SAMPLE
```

全市场 metadata/context 快照仍然必要，用于发现原范围外市场是否成长为新的高质量候选；它不等于对全市场抓 Candle、Book 或运行策略。

---

## 6. Refresh 不得要求重新部署

Universe 是版本化运行数据，不是源码常量。

目标接口：

```text
ta-universe refresh
ta-universe validate <version>
ta-universe diff <version>
ta-universe apply <version>
ta-universe rollback <version>
ta-universe status
```

每次更新不得要求：

- 修改 Python 源码；
- Git commit；
- 重跑完整 CI；
- 重新部署；
- 重启整个系统。

Apply 必须是原子版本切换；失败时继续使用上一有效 Universe。

---

## 7. Refresh 周期与用户参与

刷新间隔必须可配置：

```text
UNIVERSE_REFRESH_INTERVAL_DAYS
```

`7 days` 只是首轮候选，不是永久冻结参数。

前两次正式 Refresh：

```text
AUTO_REFRESH = YES
AUTO_APPLY = NO
```

系统自动抓取、计算、验证并生成 Diff；用户只需审阅新增/删除和批准 Apply，目标人工成本 `5–10 minutes`。

前两次稳定并得到授权后，可启用：

```text
AUTO_REFRESH = YES
AUTO_APPLY = YES
```

异常时：

```text
AUTO_APPLY = NO
KEEP_PREVIOUS_UNIVERSE = YES
NOTIFY_USER = YES
```

至少运行四次后，依据 `UNIVERSE_TURNOVER_RATE` 决定维持 7 天、延长至 14 天或保留手动紧急 Refresh。

---

## 8. API 与成本边界

本轮只使用 Hyperliquid 公共只读 API；不购买 API、不访问账户、不签名、不调用交易写接口。

测试当天必须重新核验官方：

- REST aggregate weight limit；
- 各 info 请求权重；
- candleSnapshot 增量权重；
- WebSocket connection/subscription/new-connection limits。

公开 API 当前主要风险是限流、数据陈旧和恢复失败，不是按请求付费。任何规则变化以测试当天官方文档和实际响应为准。

不得预先冻结 `480/720 weight` 等未经实测的运行阈值。

---

## 9. 四类容量必须分开测量

```text
A. GLOBAL_SNAPSHOT_COST
B. COLD_BOOTSTRAP_COST
C. STEADY_STATE_TRACKED_MARKET_CAPACITY
D. CANDIDATE_EVENT_OUTCOME_RECOVERY_STRESS_CAPACITY
```

### A. Global Snapshot

测量一次全市场 metadata/context 的请求、权重、时间和结果完整性。

### B. Cold Bootstrap

对每档 N 获取最低可运行历史，记录请求、权重、时间、429、超时、缺失、重复和冲突。不得每轮重复下载完整历史。

### C. Steady State

每档 N 运行市场级共享缓存、闭合 5m、15m/1h 本地聚合、Scanner 代表计算、临时 SQLite 写入。

### D. Stress

模拟大量候选、BBO、机器策略状态、Shadow Outcome、断线重连、REST 补数和只读导出。

---

## 10. Market 共享缓存与 Active Event

Active Event 不得单独发起 Candle/BBO 请求。

正确模型：

```text
ONE MARKET DATA CACHE
→ ALL SETUPS / SIDES / EVENTS FOR THAT MARKET
```

容量主要单位为：

```text
TRACKED_APPROVED_MARKETS
```

而不是预设的 Active Event 数量。

继续保留机器策略边界：

```text
per market_id × setup_family × side
max one active unconfirmed Event
```

Stress Profile 必须模拟每个市场达到合同允许的最大活动状态。如果本地状态计算实测仍形成独立瓶颈，再依据真实数据决定是否需要 Event 上限；当前不得写死 12、24 或其他数字。

---

## 11. 容量测试必须在目标服务器或等价环境

测试必须与当前生产服务隔离：

- `/tmp` 独立 Harness；
- 独立临时 SQLite；
- 不修改生产仓库 Worktree；
- 不写 `runtime.db` 或正式 evidence DB；
- 不部署；
- 不重启/停止生产；
- 不修改 systemd/permit；
- 不安装依赖，缺依赖即 Safe Stop；
- 无账户、私钥、签名和交易写路径。

测试前后必须检查生产 SHA、service state、MainPID、NRestarts 和 `ta-status`。

---

## 12. 自动扩张 Profile

每个 N 至少运行：

```text
PROFILE_A = COLD_BOOTSTRAP
PROFILE_B = STEADY_STATE
PROFILE_C = CANDIDATE_HEAVY_MAX_LOCAL_STATE
PROFILE_D = OUTCOME_RECOVERY_AND_EXPORT
```

扩张序列：

```text
8 → 16 → 32 → 64 → 128 → ...
```

每档通过全部 Profile 才算 `FULL_PASS`。

快速定位档：

```text
warmup 10m
measurement 20m
```

边界候选档：

```text
warmup 15m
measurement 60m
at least 2 forced reconnect/recovery cycles
```

如果生产保护门禁触发，立即停止。

---

## 13. 测试指标与 Gate

必须记录：

- REST request/weight/minute/peak/429/backfill；
- WebSocket connections/subscriptions/message rate/disconnect/reconnect；
- missing/duplicate/out-of-order closed bars；
- close-to-cache、aggregation、Scanner、Kernel、DB commit、full-cycle latency；
- CPU p50/p95/max；
- memory start/end/max/growth；
- SQLite latency/locked/busy；
- disk usage/write rate；
- production service health。

每档最低 Gate：

```text
NO_429 = PASS
NO_CLOSED_BAR_LOSS = PASS
NO_DUPLICATE_STATE_COMMIT = PASS
NO_OUT_OF_ORDER_STATE_CORRUPTION = PASS
RECONNECT_AND_BACKFILL = PASS
TEMP_DB_INTEGRITY = PASS
MEMORY_STABLE = PASS
PRODUCTION_SERVICE_UNAFFECTED = PASS
```

建议性能门禁：

```text
all-market 5m processing p95 <= 30s
SQLite commit p95 <= 100ms
CPU p95 <= 70%
no linear memory growth
```

如实测表明某门禁需要修正，必须返回原始数据和理由，不得静默降低标准。

---

## 14. 安全容量

必须返回：

```text
LAST_FULL_PASS_N
FIRST_FAIL_N
MEASURED_FAILURE_BOUNDARY
MEASURED_CAPACITY_AT_LEAST
API_HEADROOM
WS_HEADROOM
CPU_HEADROOM
MEMORY_HEADROOM
LATENCY_HEADROOM
```

最终运行 Universe 不能刚好等于压力边界。

默认安全规则：

```text
stress-tested capacity >= planned live market count × 1.25
```

如果工程实测证明 1.25 不合适，必须提出带数据的替代安全系数；不得取消恢复余量。

---

## 15. 最终 Universe 的冻结顺序

容量实测同时必须收集质量分布：

- 24h notional volume；
- OI quantity/notional；
- median/p95 spread；
- median/min depth within 10/20 bps；
- market age/history length；
- 7d 5m completeness；
- p95/p99/max absolute return；
- top-5 return concentration；
- jump reversal；
- mark/oracle deviation if available。

输出逐市场值和 P10/P25/P50/P75/P90/P95/P99/MAX。

然后由 Strategy Optimization 冻结精确的：

```text
MULTI_ASSET_UNIVERSE_ELIGIBILITY_R1
```

所有最终阈值必须是明确数值、百分位、排序和 tie-break，不得使用“靠前、较高、主流、深度较好、波动合理”等语言。

最终 Approved Universe：

```text
quality-eligible markets ordered by final quality rules
∩
measured safe capacity
```

不得通过降低安全或市场质量标准凑数量。

---

## 16. 影子样本边界

只有最终 Approved Universe 中的市场才可以成为正式研究样本。

```text
UNIVERSE_ELIGIBLE
AND FORMAL_SETUP_CONFIRMED
AND BBO_FRESH
AND LIQUIDITY_PASS
AND CHASE_PASS
AND TARGET_FEASIBILITY_PASS
AND REFERENCE_QUANTITY_VALID
→ SHADOW_ORDER_REQUIRED
→ OUTCOME_REQUIRED
→ RETENTION_REQUIRED
```

Universe 外市场不持续生成 Candidate；周期 Refresh 只保存资格快照、排名和拒绝原因。

容量测试 Harness 的临时状态不得进入正式策略收益统计。

---

## 17. 通知与旧新系统边界

仍然固定：

```text
TOP_N_LIMITS_NOTIFICATION_ONLY
ALL_APPROVED_FORMAL_SIGNALS_RETAINED = YES
ALL_APPROVED_FORMAL_SHADOW_ORDERS_RETAINED = YES
ALL_APPROVED_FORMAL_OUTCOMES_CONTINUE = YES
```

Discord 展示范围在最终 Universe 后再精确冻结；当前用户目标是少量最高质量市场获得完整优先卡片，其余 Approved Formal Signals 进入压缩摘要和后台研究。

新旧系统：

```text
PARALLEL_INSTALLED
SINGLE_ACTIVE_NOTIFICATION_AUTHORITY
```

正式切换后新系统是唯一通知来源；旧 ETH 服务停止/禁用但保留 exact SHA、配置、runtime.db 和恢复命令。

---

## 18. 当前状态

```text
CAPACITY_TEST_METHOD = CLOSED
FIXED_TOP_100_METHOD = SUPERSEDED
EXPANDING_TEST_AND_BOUNDARY_CONVERGENCE = REQUIRED
PERIODIC_UNIVERSE_REFRESH_ROUTE = CLOSED
REFRESH_REDEPLOYMENT_REQUIRED = NO
REFRESH_AUTOMATION_TARGET = CLOSED
FORMAL_SHADOW_SAMPLE_BOUNDARY = CLOSED
ACTIVE_EVENT_FIXED_CAP = NOT_AUTHORIZED
FINAL_UNIVERSE_ELIGIBILITY = OPEN_PENDING_MEASURED_DATA
READY_FOR_READ_ONLY_CAPACITY_SPIKE = YES
```

本文不授权生产代码修改、部署、重启、依赖安装、生产数据库写入、账户访问、签名、交易所写入、自动下单、PR Mark Ready 或 Merge。
