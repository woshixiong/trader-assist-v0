# First Launch Session Momentum Breakout Scanner Lite 条件性计划

**记录 ID：** `TA-FIRST-LAUNCH-SESSION-MOMENTUM-BREAKOUT-SCANNER-LITE-2026-08-01-R1`  
**日期：** 2026-08-01  
**仓库：** `woshixiong/trader-assist-v0`  
**状态：** `CONDITIONAL PLAN / NON-EXECUTABLE / PRE-IMPLEMENTATION`  
**关联：** PR #52、First Launch 三 Setup 同日最小上线计划  
**权限边界：** 本文不授权代码修改、依赖安装、部署、自动切换资产、账户访问、签名、交易所写入或自动下单。

---

## 1. 用户目标与阶段定位

当前 ETH 可能长时间缺少满足量化门槛的信号，导致：

1. 无法快速区分“系统异常”与“市场确实没有符合规则的机会”；
2. 缺少足够真实信号去结合人工判断、Signal Evidence Lite 和后续 Outcome 验证三个 Setup；
3. 人工通过新闻寻找异动标的通常发现过晚，容易错过突破及回踩阶段。

因此记录一个最小候选发现工具：

```text
SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE
```

其定位是：

```text
全市场只读候选发现
→ 时段异动与相对强度筛选
→ 结构突破筛选
→ 回踩状态观察
→ Top-N 推荐给人类
→ 现有 Breakout Setup 才拥有最终策略判断权
```

扫描器不是第四个 Setup，不拥有交易权限，不直接产生自动订单。

---

## 2. 当前阶段裁决

```text
SCANNER_QUALITY_TARGET = 5_TO_6_OF_10
SCANNER_ROLE = CANDIDATE_DISCOVERY_ONLY
FINAL_SIGNAL_AUTHORITY = EXISTING_THREE_SETUP_ENGINE
HUMAN_FINAL_DECISION = REQUIRED
AUTOMATIC_TRADE = NO
AUTOMATIC_ASSET_SWITCH = NO
CURRENT_ETH_RUNTIME_MUTATION = NO_BY_DEFAULT
```

本任务可以作为 First Launch 三 Setup 上线窗口的**条件性附加项**，但不得阻断或扩大三 Setup 核心关键路径。

### 2.1 同窗口纳入条件

只有全部满足时，才允许 Project Control 考虑将最小扫描器纳入同一上线窗口：

1. 作为独立只读 CLI/旁路脚本实现；
2. 不修改 ETH-only 策略运行时、Risk Kernel、数据库 schema 或现有服务权限；
3. 只复用公共 Hyperliquid 数据和现有通知运输；
4. 不自动切换 active asset；
5. 不自动下单；
6. 修改文件数量小且边界清楚；
7. 工程 Spike 后的剩余实现与测试预计不超过 4 小时；
8. 三 Setup 核心上线已经完成或不存在进度风险。

任一条件不满足：

```text
SCHEDULE = IMMEDIATE_PRE_V0_MINI_RELEASE
TARGET = 0.5_TO_1_WORKING_DAY_AFTER_THREE_SETUP
```

---

## 3. 为什么采用独立旁路脚本

当前 First Launch 生产代码从订阅 identity、K线校验、数据对象、runtime scope 到持久化均明确绑定 ETH。直接把全市场扫描和资产切换嵌入现有 runtime，会扩大：

- 数据 authority；
- 多资产类型和精度；
- 订阅协议；
- health/readiness；
- 策略与风险边界；
- 数据库存储和产品行为。

最小方案应为：

```text
Hyperliquid public API
→ 独立 Scanner Lite
→ JSON/CSV 审计结果
→ 可选 Discord 候选提醒
→ 人工打开盘面确认
```

不得把 Scanner Lite 伪装成完整多资产生产系统。

---

## 4. V0.1 扫描流程

### 4.1 时间窗口

第一版只保留：

```text
ASIA_WINDOW = 07:00-08:00 Asia/Shanghai
US_OPEN_WINDOW = 09:30-10:30 America/New_York
MANUAL_SCAN = ENABLED
```

`America/New_York` 必须用于自动处理夏令时；禁止把美股开盘永久硬编码为固定北京时间。

### 4.2 两阶段数据获取

```text
阶段 A：全市场廉价预筛
- allPerpMetas / perpDexs / asset contexts
- allMids 或 allDexsAssetCtxs
- 记录时段开盘价并每 5 分钟更新
- 计算时段收益、横截面排名和相对强度

阶段 B：少量候选精筛
- 只为 Top 10-20 获取 5m/15m candles
- 只为最终 Top 3-5 获取 BBO/点差和更完整上下文
- 检查前高/前低突破、追价距离和回踩状态
```

不得持续为所有市场运行完整三 Setup。

### 4.3 候选状态

```text
MOVER_DETECTED
→ BREAKOUT_DETECTED
→ RETEST_PENDING
→ RETEST_TOUCHED
→ RETEST_CONFIRMED
→ READY_FOR_HUMAN_REVIEW
```

失败状态：

```text
REJECTED_DATA
REJECTED_LIQUIDITY
REJECTED_EXTREME_VOLATILITY
REJECTED_CHASE
INVALIDATED_BACK_INSIDE_RANGE
EXPIRED_NO_RETEST
EVENT_RISK_WATCH_ONLY
```

---

## 5. 5-6 分参数基线

以下为低复杂度、可配置的首轮基线，不宣称最优参数。

### 5.1 Universe 分层

#### Tier A：原生高流动性加密永续

- 可进入候选推荐；
- 完整人工复核后才允许人工交易；
- 仍由现有 Setup 规则给出最终计划。

#### Tier B：流动性合格的山寨币/小币种

- 第一阶段默认 `EXPERIMENTAL_SMALL_RISK`；
- 仅在 OI、成交量、点差和历史长度合格时进入；
- 人工交易建议使用 ETH 正常风险的 0.25-0.50 倍；
- 不允许因为止损存在就忽略滑点、跳价和操纵风险。

#### Tier C：HIP-3 股票、指数、商品等 TradFi 永续

- 第一版默认 `WATCH_ONLY` 或 `HUMAN_REVIEW_ONLY`；
- 必须单独标识 DEX、oracle/deployer、市场状态和事件风险；
- 财报、宏观数据和公司事件未知时不得显示为普通 crypto 候选；
- 不继承 ETH 参数和风险级别。

### 5.2 预筛过滤

候选必须满足：

- 市场未暂停，metadata 和价格完整；
- 有足够历史，不是刚上线市场；
- OI 与成交活跃度不处于 eligible universe 的最低层；
- 当前资金费、mark/mid 偏离和价格数据无明显异常；
- 对最终候选检查 BBO，点差不得明显恶化；
- HIP-3 资产若 oracle/deployer/市场状态不完整则拒绝。

第一版优先采用横截面分位数而不是长期硬编码美元门槛，以减少市场规模变化导致的频繁改参。

### 5.3 时段异动条件

```text
session_return = current_mid / session_open_mid - 1
relative_return = session_return - eligible_universe_median_return
normalized_move = abs(session_return) / ATR14_1H_PERCENT
```

首轮候选建议同时满足：

- 时段收益位于 eligible universe 上涨前 10% 或下跌前 10%；
- `normalized_move >= 0.8`；
- 相对市场中位数或 BTC benchmark 具有明确超额方向；
- 量能相对近期中位数放大，建议初始门槛约 `1.5x`；
- 不得只因绝对涨跌幅大而入选。

### 5.4 结构突破条件

使用扫描窗口开始前已存在的结构高点/低点，禁止使用未来形成的 level。

首轮规则：

- 5m closed candle 收盘突破 prior high / prior low；
- 突破距离至少达到 `max(0.10 × ATR14_5M, 2 × current_spread)`；
- 若当前价格已离突破位超过约 `1.5 × ATR14_5M`，标记 `REJECTED_CHASE`；
- 最终确认仍交给现有 `BREAKOUT_RETEST` Setup。

### 5.5 回踩条件

首轮观察窗口：突破后 `1-12` 根 5m candle。

初始回踩区：

```text
breakout_level ± 0.20 × ATR14_5M
```

失效：

- 5m 实体重新进入旧区间超过约 `0.25 × ATR14_5M`；
- 数据断线或候选超时；
- 点差、波动或价格偏离突然恶化；
- 当前价格已超过 Chase Limit。

确认：

- 触及回踩区；
- 未完成失效；
- 再次收于突破方向；
- 现有 Breakout Setup 认可。

### 5.6 推荐评分

Scanner score 只用于排序，不用于授权交易：

```text
25% 时段相对强度 / normalized move
25% 突破质量与追价距离
20% 成交量与 OI 健康度
20% 流动性与点差
10% 回踩状态
```

输出 Top 3-5，并显示所有拒绝或限制原因。

---

## 6. 研究依据与边界

研究与成熟案例提供以下支持：

1. Opening Range Breakout / intraday momentum 在部分市场和状态下存在可研究的持续性；
2. “Stocks in Play”或异常活跃标的筛选可能显著优于无筛选地交易全部标的；
3. 加密货币动量效应更常见于流动性较高的资产；
4. 突破后的回踩时机、回踩前最大延伸和回到 level 的方式可能与后续结果有关；
5. 加密市场虽然 24/7，但亚洲、欧洲和美国时段仍存在活动周期。

但现有证据不能证明本 Scanner 在 Hyperliquid 上自动具有正期望：

- ORB/突破结果对资产、时段和样本期敏感；
- 部分研究在分样本后显示稳定性下降；
- 股票、商品和 crypto 的微观结构不能直接互相移植；
- HIP-3 资产额外包含 deployer、oracle、halt/settlement 与事件风险；
- 多资产扫描会放大多重比较和偶然信号。

因此：

```text
MATHEMATICAL_SUPPORT = PLAUSIBLE_MECHANISM_NOT_PROVEN_EDGE
FIRST_LAUNCH_USE = HUMAN_ASSISTED_CANDIDATE_DISCOVERY
AUTO_TRADING_USE = PROHIBITED
```

---

## 7. 风险与控制

### 7.1 主要风险

- 多重比较导致每天总能找到“看起来最强”的偶然标的；
- 新闻/财报/宏观冲击使突破后立即反转；
- 山寨币盘口薄、滑点大、强平链和操纵风险高；
- HIP-3 oracle/deployer、暂停和结算机制与原生 crypto 不同；
- 在扫描窗口结束后才计算排名会产生“发现太晚”的操作风险；
- 不正确的时区和美国夏令时会造成窗口错位；
- API rate limit、断线和缺失 candle 会造成候选偏差；
- alert 过多会诱导追涨、频繁交易和风险升级；
- 相同市场因高度相关可能产生重复候选。

### 7.2 最低控制

- 每 5 分钟因果更新，不等待整个窗口结束后回填历史候选；
- 保存完整 point-in-time universe、排名和拒绝原因；
- Top-N 上限与 alert cooldown；
- `DO NOT CHASE` 和距离 level/ATR 必须显示；
- HIP-3 与小币种清晰标记风险级别；
- 数据不完整即 fail closed；
- Scanner 不改变风险预算，不创建订单；
- 人类必须重新看盘和确认现有 Setup。

---

## 8. 影子证据和统计验证

第一版必须保存：

- scan_id、session、universe snapshot；
- asset/dex/category；
- session open/current price；
- session_return、relative_return、normalized_move；
- OI、funding、volume、spread；
- prior level、breakout candle、retest state；
- score、rank、rejection reasons；
- 后续现有 Signal/TradePlan ID；
- 人工 `TAKEN / SKIPPED / REJECTED`；
- 后续 MFE/MAE、TP/Stop/Expiry 和真实成交结果（可得时）。

评估指标：

- 候选到 `RETEST_CONFIRMED` 的转化率；
- 经现有 Breakout Setup 批准的比例；
- 人工接受/拒绝原因；
- 成本后净 R；
- MFE、MAE、回踩时间和突破后最大延伸；
- crypto major / liquid alt / HIP-3 分组；
- Asia / US 时段分组；
- 与同资产无 Scanner 条件和随机 eligible 候选的基线比较。

参数纪律：

- First Launch 阶段不因少量结果频繁改参；
- 每个重要分组至少积累约 30 个候选后再做方向性调整；
- 进入自动交易研究前需要更大样本、样本外验证、成本和事件分层；
- 所有参数版本必须保留。

---

## 9. 工程工作量与排期

### 9.1 方案 A：极简手动 CLI

能力：

- 手动启动并运行一个时段；
- 全市场 allMids/asset context 预筛；
- Top 候选 candle/BBO 精筛；
- 终端 + JSON/CSV 输出；
- 不发通知、不新增服务。

估算：

```text
ENGINEERING = 3_TO_5_HOURS
TEST_AND_DRY_RUN = 1_TO_2_HOURS
TOTAL = 4_TO_7_HOURS
```

### 9.2 方案 B：可用 Scanner Lite

在方案 A 基础上增加：

- Asia / US 定时窗口；
- 自动夏令时；
- 状态跟踪与回踩提醒；
- Discord 候选通知；
- append-only 结果存储；
- 最小部署和状态检查。

估算：

```text
ENGINEERING = 5_TO_8_HOURS
TEST_DEPLOY_SMOKE = 2_TO_4_HOURS
TOTAL = 7_TO_12_HOURS
```

### 9.3 方案 C：直接集成当前生产 runtime

需要解除 ETH-only 类型、订阅、数据 authority、health、持久化和产品边界。

```text
ESTIMATE = GREATER_THAN_1_WORKING_DAY
RISK = HIGH
CURRENT_RECOMMENDATION = REJECT
```

---

## 10. 推荐初步排期

```text
PRIMARY_THREE_SETUP_RELEASE = UNCHANGED

SCANNER_S0_RESEARCH_AND_SCOPE = COMPLETE_BY_THIS_RECORD

SCANNER_S1_ENGINEERING_SPIKE = 1_TO_2_HOURS
- 确认公共 API 获取路径
- 确认旁路文件范围
- 确认通知复用
- 输出 exact estimate

IF REMAINING_IMPLEMENTATION <= 4 HOURS
AND THREE_SETUP_RELEASE_NOT_AT_RISK:
    ALLOW_CONDITIONAL_SAME_WINDOW_CLI
ELSE:
    SCHEDULE_IMMEDIATE_PRE_V0_MINI_RELEASE
    TARGET_ELAPSED = 0.5_TO_1_WORKING_DAY
```

推荐默认裁决：

```text
SAME_WINDOW = CONDITIONAL_NOT_DEFAULT
PREFERRED_RELEASE = IMMEDIATE_AFTER_THREE_SETUP_BEFORE_V0
PREFERRED_PRODUCT = OPTION_B_SCANNER_LITE
```

理由：方案 B 才能真正解决“及时发现突破并等待回踩”的用户问题；只做一次性手动 CLI 价值有限，但可以作为 Spike 或临时工具。

---

## 11. 需要工程优化和产品优化后续确认

### Engineering Optimization

只读评估：

- 可复用 Hyperliquid HTTP/WebSocket helper；
- 是否需要新依赖；
- exact file scope；
- API rate-limit 预算；
- session baseline 和 reconnect；
- JSON/CSV 或现有 SQLite 最小持久化；
- Discord dispatcher 是否可安全复用；
- 方案 A/B 的实际时间。

### Product Optimization

确认：

- Top 3-5 候选卡片；
- risk/category 标识；
- `DO NOT CHASE`；
- MOVER/BREAKOUT/RETEST 状态；
- 通知频率和 cooldown；
- 人工 T/S/R；
- HIP-3、小币种的显著警告；
- 不增加复杂 dashboard。

Project Control 在两个窗口输出一致后才可派发。

---

## 12. 最终冻结字段

```text
TASK = SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE
QUALITY_TARGET = 5_TO_6_OF_10
ROLE = CANDIDATE_DISCOVERY
FINAL_SIGNAL_AUTHORITY = THREE_SETUP_ENGINE
HUMAN_FINAL_DECISION = YES
NATIVE_CRYPTO = ELIGIBLE_WITH_LIQUIDITY_FILTER
LIQUID_ALT = EXPERIMENTAL_SMALL_RISK
HIP3_TRADFI = WATCH_OR_HUMAN_REVIEW_ONLY
AUTO_TRADE = NO
AUTO_ASSET_SWITCH = NO
CURRENT_ETH_RUNTIME_INTEGRATION = NO
SAME_WINDOW = CONDITIONAL_ONLY
DEFAULT_SCHEDULE = IMMEDIATE_PRE_V0_MINI_RELEASE
TARGET_TIME = 0.5_TO_1_WORKING_DAY
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```
