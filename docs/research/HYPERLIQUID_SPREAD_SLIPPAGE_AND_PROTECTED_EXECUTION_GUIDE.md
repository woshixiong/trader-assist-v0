# Hyperliquid 点差、滑点与受保护执行指南

> **文档类型**：工程研究与未来执行设计参考（G0 文档）  
> **最后核验日期**：2026-08-03  
> **适用范围**：Hyperliquid 永续合约，包括核心加密市场与 HIP-3 商品/指数市场（例如 `xyz:GOLD`、`xyz:SILVER`、`xyz:SP500` 等，具体市场名称和可用性必须在运行时核验）  
> **非授权声明**：本文不授权创建钱包、保存私钥、签名、发送订单、修改仓位或启用 Testnet/Mainnet 执行。任何自动或半自动执行都必须经过独立的执行权限、安全审查、测试网、影子运行、有限资金灰度和 Mainnet 授权。

---

## 1. 核心结论

Hyperliquid 没有必要依赖一个“全局最大点差”按钮来控制执行质量。更可靠的做法是把执行保护拆成多个独立门禁：

1. **订单簿新鲜度门禁**：数据过期即拒绝下单；
2. **最大点差门禁**：买一/卖一价差超过阈值即拒绝下单；
3. **订单簿深度与 VWAP 模拟**：在下单前计算目标仓位会吃到哪些档位；
4. **最大预期滑点门禁**：预估平均成交价偏离最佳报价过大即拒绝或缩小仓位；
5. **明确的最差成交价**：使用 IOC 限价单，而不是无边界追价；
6. **部分成交策略**：未成交部分取消，不自动追价；
7. **成交后核验**：核对订单状态、实际成交、仓位和保护单；
8. **CLOID、`expiresAfter` 与 dead-man switch**：防止重复订单、陈旧请求和失联挂单；
9. **失败关闭**：任何数据、账户、签名、订单状态或保护状态不确定时，不增加风险。

Hyperliquid 官方 Python SDK 中的所谓“市价单”，本质上是一个带价格边界的激进 IOC 限价单。当前 SDK 默认最大滑点为 **5%**，并以中间价为基准生成最远限价。这个默认值只能视为防止无限穿透订单簿的最后边界，不适合作为黄金、白银、股指等市场的日常执行标准。

Hyperliquid 的 Market TP/SL 当前默认允许 **10%** 的滑点容忍度。对于流动性较薄的 HIP-3 市场，这是非常宽的保护范围。生产系统必须明确区分：

- **保证退出优先**：Stop Market，允许更大滑点；
- **价格边界优先**：Stop Limit，但存在无法成交的风险。

最稳妥的入场执行模式通常是：

```text
读取最新 L2 订单簿
→ 验证订单簿新鲜度与结构
→ 检查 spread_bps
→ 模拟目标仓位的 VWAP、最差价和可成交数量
→ 检查预计滑点与总成本
→ 以模拟得到的最差订单簿价位作为 IOC 限价
→ 未成交部分立即取消
→ 核验 fills / order status / position
→ 挂出 reduce-only 保护单
```

---

## 2. 必须区分的执行概念

### 2.1 最佳买卖价与中间价

设：

- `best_bid`：买一价；
- `best_ask`：卖一价；
- `mid`：中间价。

```text
mid = (best_bid + best_ask) / 2
```

### 2.2 点差（Spread）

绝对点差：

```text
spread_abs = best_ask - best_bid
```

基点点差：

```text
spread_bps = (best_ask - best_bid) / mid × 10,000
```

`1 bps = 0.01%`。

点差是交易者立即买入再卖出时天然承担的市场摩擦。即使仓位很小，不会对市场造成冲击，点差仍然存在。

### 2.3 预期滑点（Expected Slippage）

买单相对卖一价：

```text
buy_slippage_bps = (expected_vwap - best_ask) / best_ask × 10,000
```

卖单相对买一价：

```text
sell_slippage_bps = (best_bid - expected_vwap) / best_bid × 10,000
```

这里的滑点主要描述订单因跨越多个订单簿档位而产生的价格影响。

### 2.4 中间价成本（Cost from Mid）

对买单：

```text
cost_from_mid_bps = (expected_vwap - mid) / mid × 10,000
```

对卖单：

```text
cost_from_mid_bps = (mid - expected_vwap) / mid × 10,000
```

这个指标同时包含半个点差和吃单产生的价格影响，更适合比较不同市场的实际入场成本。

### 2.5 实际滑点（Realized Slippage）

实际滑点应在成交后计算：

```text
realized_slippage_bps =
    direction_adjusted(actual_fill_vwap - decision_reference_price)
    / decision_reference_price × 10,000
```

`decision_reference_price` 必须在发送订单前冻结，并记录时间戳。不能事后选择一个更有利的参考价格。

### 2.6 总交易成本

日内交易至少应记录：

```text
总成本 ≈ 点差成本 + 价格冲击 + 交易手续费 + 资金费率 + 失败重试成本
```

对于短时间持仓，资金费率可能较小；对于跨多个结算周期的持仓，资金费率可能成为主要成本。

---

## 3. Hyperliquid 的订单簿与订单类型

### 3.1 订单簿

Hyperliquid 使用链上中央限价订单簿，并按价格—时间优先级撮合。订单簿公开可查询，但公开不等于深度永远充足：

- 挂单可以在成交前撤销；
- 周末的传统资产永续可能缺少充分的外部套利锚；
- HIP-3 新市场的做市商数量和资本可能有限；
- 突发行情和连环强平时，订单簿可能瞬间变薄；
- 预言机价格、持仓上限或市场风控可能限制新增仓位。

### 3.2 `l2Book` 数据结构

REST Info API 或官方 Python SDK 的 `Info.l2_snapshot()` 返回：

```json
{
  "coin": "BTC",
  "time": 1754450974231,
  "levels": [
    [
      {"px": "113377.0", "sz": "7.6699", "n": 17}
    ],
    [
      {"px": "113397.0", "sz": "0.11543", "n": 3}
    ]
  ]
}
```

通常：

- `levels[0]`：买盘；
- `levels[1]`：卖盘；
- `px`：价格；
- `sz`：该价格档位的数量；
- `n`：该聚合档位内的订单数量；
- `time`：订单簿时间戳，毫秒。

执行系统不能只读取最优一档；必须从目标方向逐档累加，计算完整仓位的 VWAP 和最差成交价。

### 3.3 GTC、IOC、ALO

- **GTC**：未成交部分继续挂在订单簿；
- **IOC**：立即成交能够成交的部分，未成交部分立即取消；
- **ALO**：只允许增加流动性；若会立即成交则整单取消，相当于 Post-only。

对需要严格控制滑点的入场单，IOC 是最直接的工具：

```text
买入限价 = 可接受的最高价格
卖出限价 = 可接受的最低价格
TIF = IOC
```

成交不会穿过限价；代价是订单可能部分成交或完全不成交。

### 3.4 官方 SDK 的“市价单”

官方 Python SDK 当前实现逻辑：

```text
market_open / market_close
→ 读取 mid price
→ 按 slippage 参数生成激进限价
→ 提交 IOC 限价单
```

SDK 当前默认：

```python
DEFAULT_SLIPPAGE = 0.05  # 5%
```

这不是推荐的日常参数。对于黄金价格 4,000 美元，5% 相当于 200 美元价格范围，远大于正常执行应接受的范围。

更稳健的方法不是直接调用默认 `market_open()`，而是：

1. 自行读取订单簿；
2. 计算目标仓位的实际 VWAP；
3. 根据策略阈值决定是否允许下单；
4. 使用订单簿内的实际最差档位价格作为 IOC 限价。

---

## 4. 小资金是否仍然需要关注点差和滑点

小资金通常不会显著推动订单簿，但执行成本占账户风险预算的比例可能更高。

例如：

- 账户净值：500 USDC；
- 每笔风险：1%，即 5 USDC；
- 名义仓位：1,000 USDC；
- 入场综合成本：20 bps，即 2 USDC。

入场成本已经消耗了单笔风险预算的 40%。如果退出时再支付相近成本，策略的有效盈亏比会显著恶化。

因此，小资金的主要问题通常不是“能否成交”，而是：

- 最小名义价值与数量精度；
- 点差占止损距离的比例；
- Taker 手续费占预期利润的比例；
- 触发止损时的滑点；
- 频繁交易导致的成本累积；
- 杠杆过高导致可承受价格波动过小。

Hyperliquid 永续订单通常要求至少约 10 美元名义价值，但还必须满足资产数量精度和价格精度。运行时应以当前官方元数据和错误响应为准，不能将最低值硬编码为永久不变的协议事实。

---

## 5. 推荐的两层参数体系

研究、Scanner 和真实执行的阈值不应完全相同。

### 5.1 研究/候选层

研究层的目标是保留证据和候选，不一定立即下单。可以允许较宽阈值：

```text
RESEARCH_MAX_SPREAD_BPS
RESEARCH_MAX_ESTIMATED_SLIPPAGE_BPS
```

超过研究硬上限才拒绝保留为可交易候选；未达到执行标准的标的仍可保留为观察证据。

### 5.2 执行层

执行层必须更严格：

```text
EXECUTION_PREFERRED_SPREAD_BPS
EXECUTION_HARD_MAX_SPREAD_BPS
EXECUTION_HARD_MAX_VWAP_SLIPPAGE_BPS
EXECUTION_HARD_MAX_COST_FROM_MID_BPS
EXECUTION_MAX_BOOK_AGE_MS
EXECUTION_MIN_DEPTH_COVERAGE_RATIO
```

以下仅用于初始校准，不是固定生产参数：

| 市场类别 | 优选点差 | 硬点差上限 | 单向 VWAP 滑点上限 |
|---|---:|---:|---:|
| BTC/ETH 活跃时段 | ≤ 5 bps | 10–15 bps | 10–20 bps |
| GOLD/SP500 活跃时段 | ≤ 10 bps | 20–30 bps | 15–25 bps |
| SILVER/较薄 HIP-3 | ≤ 20 bps | 30–40 bps | 25–35 bps |
| 传统市场周末时段 | 默认不自动入场 | 人工复核 | 尽量仅限价 |

这些数值必须通过真实订单簿采样、影子订单、测试网和有限资金成交数据重新校准。不能因为某一时点深度良好就永久放宽阈值。

---

## 6. 标准入场执行流程

### 6.1 数据新鲜度

必须记录：

```text
book_exchange_time_ms
book_local_receive_time_ms
decision_time_ms
submit_time_ms
ack_time_ms
```

建议至少检查：

```text
now_ms - book_exchange_time_ms <= MAX_BOOK_AGE_MS
submit_time_ms - decision_time_ms <= MAX_DECISION_TO_SUBMIT_MS
```

WebSocket 断线、心跳失败、时间回退、数据时间戳异常或本地时钟漂移时，禁止新增风险。

### 6.2 订单簿结构验证

下单前必须满足：

```text
存在买盘和卖盘
best_bid > 0
best_ask > 0
best_bid < best_ask
价格和数量可解析
档位按正确方向排序
订单簿时间戳未倒退
```

### 6.3 点差门禁

```text
if spread_bps > hard_max_spread_bps:
    REJECT
```

点差门禁应在 VWAP 模拟前执行，因为一个非常宽的点差即使没有额外价格冲击，也可能已经不可接受。

### 6.4 深度与 VWAP 模拟

买单从卖盘第一档开始累加，卖单从买盘第一档开始累加。

必须输出：

```text
requested_size
fillable_size
coverage_ratio
expected_vwap
worst_book_price
best_quote
slippage_from_best_bps
cost_from_mid_bps
notional
```

若订单簿无法覆盖完整数量：

- 默认拒绝；或
- 按预先授权规则缩小仓位；
- 不允许在成交后临时决定无限追价。

### 6.5 价格边界

买单硬边界：

```text
hard_buy_limit = best_ask × (1 + max_slippage_bps / 10,000)
```

卖单硬边界：

```text
hard_sell_limit = best_bid × (1 - max_slippage_bps / 10,000)
```

更可靠的 IOC 限价是：

```text
limit_px = 模拟完成目标数量所需触及的最差真实订单簿价位
```

因为该价格已是协议当前认可的有效价格档位，可减少自行处理价格精度时的错误。

### 6.6 IOC 提交

```python
order_type = {"limit": {"tif": "Ioc"}}
```

行为要求：

- 可成交部分立即成交；
- 未成交部分取消；
- 不在订单簿上留下意外挂单；
- 不自动将剩余数量改成更激进价格；
- 任何重试都必须重新读取订单簿和重新计算。

### 6.7 部分成交政策

系统必须在下单前冻结一种政策：

**政策 A：不接受部分成交**

```text
若 coverage_ratio < 100%：下单前拒绝
若实际部分成交：立即停止追单，按已成交仓位重新建立风险与保护状态
```

**政策 B：允许部分成交**

```text
接受实际成交数量
剩余部分取消
不自动追价
重新计算止损数量和风险金额
```

不能假设 IOC 一定整笔成交。

### 6.8 成交后核验

必须核验：

- API 响应中每个状态；
- CLOID 对应订单状态；
- 用户 fills；
- 实际仓位方向和数量；
- 实际平均成交价；
- 手续费；
- 是否存在意外挂单；
- reduce-only TP/SL 的数量是否与真实仓位一致。

HTTP 200 或顶层 `status: ok` 不代表每个批量订单都成功。订单错误通常出现在逐项 `statuses` 中。

---

## 7. 出场、止损与保护单

### 7.1 Stop Market

优点：

- 更强调退出成功；
- 适合风险止损和紧急平仓。

风险：

- 触发后仍需要吃订单簿；
- 在薄市场中可能产生大幅滑点；
- Hyperliquid Market TP/SL 当前默认滑点容忍度为 10%。

### 7.2 Stop Limit

优点：

- 可以限制最差成交价格。

风险：

- 价格跳过限价时可能完全无法成交；
- 仓位继续暴露；
- 在快速行情中可能产生“止损已触发但仓位仍在”的危险状态。

### 7.3 推荐原则

- 常规入场：优先 IOC 限价；
- 非紧急止盈：可以使用 GTC/ALO 限价；
- 风险止损：根据市场流动性，在“保证退出”和“限制价格”之间明确选择；
- 所有保护单必须 `reduce_only=True`；
- 保护单数量必须来自实际成交仓位，而不是原始请求数量；
- 保护单缺失、拒绝或数量不匹配时，系统进入 `UNPROTECTED_POSITION` 并禁止新增风险；
- 不应把 10% 默认 TP/SL 容忍度当成执行标准。

---

## 8. API 架构与安全边界

### 8.1 接口分类

```text
POST /info       公共市场与账户读取
POST /exchange   签名后的订单/取消/杠杆等写操作
WebSocket        实时订单簿、成交、BBO、账户事件等
```

Mainnet WebSocket：

```text
wss://api.hyperliquid.xyz/ws
```

Testnet WebSocket：

```text
wss://api.hyperliquid-testnet.xyz/ws
```

### 8.2 API Wallet

官方文档也称其为 Agent Wallet。建议：

- 主钱包只用于授权；
- 每个独立交易进程使用单独 API Wallet；
- 查询账户状态时传入主账户或子账户地址，不要传 API Wallet 地址；
- 私钥只能从秘密管理系统注入，不写入代码、配置仓库、日志或异常；
- 不重用已经注销/过期的 API Wallet 地址；
- 不同子账户或并行进程使用不同签名钱包，避免 nonce 冲突；
- 交易系统不应持有主钱包私钥。

### 8.3 Nonce

Hyperliquid 按签名者管理 nonce。自动化系统必须：

- 使用原子计数器；
- 保证同一签名者的 nonce 唯一；
- 必要时快进到当前毫秒时间；
- 避免多个未经协调的进程共享同一 API Wallet；
- 不把“请求超时”解释为“请求一定未执行”。

官方建议可以将订单和取消请求以约 0.1 秒节奏批处理，并将 ALO 与 IOC/GTC 分开批处理。

### 8.4 CLOID

CLOID 是可选的 128-bit 十六进制客户端订单 ID。建议用于：

- 幂等关联；
- 订单提交与状态查询；
- 重启恢复；
- 审计；
- 取消指定订单。

CLOID 必须与不可变的 OrderIntent 绑定，不能在不同意图之间复用。

### 8.5 `expiresAfter`

`expiresAfter` 可以让过期请求被拒绝，适用于防止网络延迟后陈旧订单突然生效。

实践建议：

- 以服务器时间和延迟分布校准；
- 不设置得过短，以免正常请求频繁失败；
- 请求过期后不得原样重试，必须重新读取市场和重新决策；
- 当前官方文档提示，因过期 `expiresAfter` 被拒绝的动作会消耗更高的地址速率权重，必须监控。

### 8.6 Dead-man switch

`scheduleCancel` 可以安排未来时间取消全部开放订单：

- 时间必须至少在当前时间 5 秒之后；
- 到期后取消所有开放订单；
- 当前每天最多触发 10 次，UTC 00:00 重置；
- 不传时间可取消已安排的 dead-man switch。

典型模式：

```text
每隔固定周期刷新 scheduleCancel
若进程、网络或心跳中断
→ 不再刷新
→ 到期自动取消开放挂单
```

注意：dead-man switch 取消的是挂单，不等于自动平仓，也不保证现有仓位得到保护。

### 8.7 WebSocket 心跳

当前官方文档说明：连接在 60 秒内没有发送消息可能被关闭。低频订阅必须发送：

```json
{"method": "ping"}
```

并处理：

```json
{"channel": "pong"}
```

断线重连后必须重新订阅，并在恢复交易前重新获取完整订单簿快照和账户状态。

### 8.8 速率限制

当前官方文档给出的 IP 聚合 REST 权重上限为每分钟 1,200；`l2Book` 等请求具有特定权重。速率限制可能更新，因此生产系统应：

- 运行时读取官方文档版本或配置快照；
- 对 429 和网络错误退避；
- 优先使用 WebSocket 获取实时订单簿；
- 不用高频 REST 轮询替代正常流式订阅；
- 监控用户级请求额度；
- 批量请求前计算权重。

---

## 9. Python：只读订单簿指标与 VWAP 模拟

下面代码不签名、不下单，可以作为离线研究、测试网前置检查或影子执行基础。

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable
import time

from hyperliquid.info import Info
from hyperliquid.utils import constants


D = Decimal
BPS = D("10000")


@dataclass(frozen=True)
class BookMetrics:
    coin: str
    exchange_time_ms: int
    age_ms: int
    best_bid: Decimal
    best_ask: Decimal
    mid: Decimal
    spread_abs: Decimal
    spread_bps: Decimal


@dataclass(frozen=True)
class FillEstimate:
    requested_size: Decimal
    filled_size: Decimal
    coverage_ratio: Decimal
    vwap: Decimal | None
    worst_price: Decimal | None
    notional: Decimal
    slippage_from_best_bps: Decimal | None
    cost_from_mid_bps: Decimal | None


def to_decimal(value: Any) -> Decimal:
    try:
        result = D(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"non-finite decimal value: {value!r}")
    return result


def validate_and_measure_book(book: dict[str, Any]) -> BookMetrics:
    levels = book.get("levels")
    if not isinstance(levels, list) or len(levels) != 2:
        raise ValueError("invalid L2 book: expected [bids, asks]")

    bids, asks = levels
    if not bids or not asks:
        raise ValueError("invalid L2 book: one side is empty")

    best_bid = to_decimal(bids[0]["px"])
    best_ask = to_decimal(asks[0]["px"])
    if best_bid <= 0 or best_ask <= 0 or best_bid >= best_ask:
        raise ValueError("crossed or invalid L2 book")

    exchange_time_ms = int(book["time"])
    now_ms = int(time.time() * 1000)
    age_ms = max(0, now_ms - exchange_time_ms)
    mid = (best_bid + best_ask) / D("2")
    spread_abs = best_ask - best_bid
    spread_bps = spread_abs / mid * BPS

    return BookMetrics(
        coin=str(book["coin"]),
        exchange_time_ms=exchange_time_ms,
        age_ms=age_ms,
        best_bid=best_bid,
        best_ask=best_ask,
        mid=mid,
        spread_abs=spread_abs,
        spread_bps=spread_bps,
    )


def estimate_fill(
    book: dict[str, Any],
    *,
    is_buy: bool,
    requested_size: Decimal,
) -> FillEstimate:
    if requested_size <= 0:
        raise ValueError("requested_size must be positive")

    metrics = validate_and_measure_book(book)
    bids, asks = book["levels"]
    side: Iterable[dict[str, Any]] = asks if is_buy else bids
    best_quote = metrics.best_ask if is_buy else metrics.best_bid

    remaining = requested_size
    filled = D("0")
    notional = D("0")
    worst_price: Decimal | None = None

    for level in side:
        px = to_decimal(level["px"])
        available = to_decimal(level["sz"])
        if px <= 0 or available <= 0:
            continue

        take = min(remaining, available)
        filled += take
        notional += take * px
        remaining -= take
        worst_price = px

        if remaining <= 0:
            break

    coverage_ratio = filled / requested_size
    if filled == 0:
        return FillEstimate(
            requested_size=requested_size,
            filled_size=filled,
            coverage_ratio=coverage_ratio,
            vwap=None,
            worst_price=None,
            notional=D("0"),
            slippage_from_best_bps=None,
            cost_from_mid_bps=None,
        )

    vwap = notional / filled
    if is_buy:
        slippage = (vwap - best_quote) / best_quote * BPS
        cost_from_mid = (vwap - metrics.mid) / metrics.mid * BPS
    else:
        slippage = (best_quote - vwap) / best_quote * BPS
        cost_from_mid = (metrics.mid - vwap) / metrics.mid * BPS

    return FillEstimate(
        requested_size=requested_size,
        filled_size=filled,
        coverage_ratio=coverage_ratio,
        vwap=vwap,
        worst_price=worst_price,
        notional=notional,
        slippage_from_best_bps=slippage,
        cost_from_mid_bps=cost_from_mid,
    )


# 核心市场示例：BTC
info = Info(constants.MAINNET_API_URL, skip_ws=True)
book = info.l2_snapshot("BTC")
metrics = validate_and_measure_book(book)
estimate = estimate_fill(book, is_buy=True, requested_size=D("0.001"))

print(metrics)
print(estimate)
```

HIP-3 DEX 示例需要在初始化时加载对应 DEX，并使用运行时返回的准确市场名。例如：

```python
info = Info(
    constants.MAINNET_API_URL,
    skip_ws=True,
    perp_dexs=["xyz"],
)
book = info.l2_snapshot("xyz:GOLD")
```

市场名称、DEX 名称、数量精度和可用性必须通过 `perpDexs`、`meta` 和 `metaAndAssetCtxs` 动态核验。

---

## 10. Python：执行前门禁

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ExecutionPolicy:
    max_book_age_ms: int
    max_spread_bps: Decimal
    max_vwap_slippage_bps: Decimal
    max_cost_from_mid_bps: Decimal
    require_full_coverage: bool = True


@dataclass(frozen=True)
class PretradeDecision:
    allowed: bool
    reason: str
    limit_price: Decimal | None
    expected_vwap: Decimal | None
    expected_notional: Decimal


def evaluate_pretrade(
    book: dict[str, Any],
    *,
    is_buy: bool,
    requested_size: Decimal,
    policy: ExecutionPolicy,
) -> PretradeDecision:
    metrics = validate_and_measure_book(book)
    if metrics.age_ms > policy.max_book_age_ms:
        return PretradeDecision(False, "STALE_BOOK", None, None, Decimal("0"))

    if metrics.spread_bps > policy.max_spread_bps:
        return PretradeDecision(False, "SPREAD_TOO_WIDE", None, None, Decimal("0"))

    estimate = estimate_fill(
        book,
        is_buy=is_buy,
        requested_size=requested_size,
    )

    if estimate.filled_size <= 0:
        return PretradeDecision(False, "NO_LIQUIDITY", None, None, Decimal("0"))

    if policy.require_full_coverage and estimate.coverage_ratio < Decimal("1"):
        return PretradeDecision(
            False,
            "INSUFFICIENT_DEPTH",
            None,
            estimate.vwap,
            estimate.notional,
        )

    assert estimate.slippage_from_best_bps is not None
    assert estimate.cost_from_mid_bps is not None
    assert estimate.worst_price is not None

    if estimate.slippage_from_best_bps > policy.max_vwap_slippage_bps:
        return PretradeDecision(
            False,
            "VWAP_SLIPPAGE_TOO_HIGH",
            None,
            estimate.vwap,
            estimate.notional,
        )

    if estimate.cost_from_mid_bps > policy.max_cost_from_mid_bps:
        return PretradeDecision(
            False,
            "TOTAL_ENTRY_COST_TOO_HIGH",
            None,
            estimate.vwap,
            estimate.notional,
        )

    # 使用真实订单簿最差档位作为 IOC 限价，避免穿透更差价格。
    return PretradeDecision(
        True,
        "ALLOW_PROTECTED_IOC",
        estimate.worst_price,
        estimate.vwap,
        estimate.notional,
    )
```

建议所有拒绝原因都持久化，作为后续容量评估和策略—执行归因证据。

---

## 11. Python：受保护 IOC 执行骨架（Testnet-only 示例）

> 以下代码是未来实现参考。默认 `DRY_RUN = True`，不得直接接入生产 Mainnet。

```python
from __future__ import annotations

import os
import secrets
from decimal import Decimal, ROUND_DOWN

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.types import Cloid


DRY_RUN = True
BASE_URL = constants.TESTNET_API_URL
DEXES = ["xyz"]  # 按实际测试网可用 DEX 调整


def floor_size(size: Decimal, sz_decimals: int) -> Decimal:
    quantum = Decimal("1").scaleb(-sz_decimals)
    return size.quantize(quantum, rounding=ROUND_DOWN)


def new_cloid() -> Cloid:
    return Cloid.from_str("0x" + secrets.token_hex(16))


def parse_first_order_status(response: dict) -> dict:
    if response.get("status") != "ok":
        raise RuntimeError(f"exchange request failed: {response!r}")

    statuses = (
        response.get("response", {})
        .get("data", {})
        .get("statuses", [])
    )
    if not statuses:
        raise RuntimeError(f"missing per-order status: {response!r}")

    status = statuses[0]
    if "error" in status:
        raise RuntimeError(f"order rejected: {status['error']}")
    return status


def protected_ioc_entry(
    *,
    coin: str,
    is_buy: bool,
    requested_size: Decimal,
    account_address: str,
    policy: ExecutionPolicy,
) -> dict:
    info = Info(BASE_URL, skip_ws=True, perp_dexs=DEXES)
    book = info.l2_snapshot(coin)

    # 从当前元数据读取数量精度，不永久硬编码。
    asset = info.name_to_asset(coin)
    sz_decimals = info.asset_to_sz_decimals[asset]
    size = floor_size(requested_size, sz_decimals)
    if size <= 0:
        raise ValueError("size rounds to zero")

    decision = evaluate_pretrade(
        book,
        is_buy=is_buy,
        requested_size=size,
        policy=policy,
    )
    if not decision.allowed or decision.limit_price is None:
        return {
            "status": "rejected_by_local_gate",
            "reason": decision.reason,
        }

    if DRY_RUN:
        return {
            "status": "dry_run",
            "coin": coin,
            "is_buy": is_buy,
            "size": str(size),
            "limit_price": str(decision.limit_price),
            "expected_vwap": str(decision.expected_vwap),
            "expected_notional": str(decision.expected_notional),
            "reason": decision.reason,
        }

    secret_key = os.environ.get("HL_API_WALLET_PRIVATE_KEY")
    if not secret_key:
        raise RuntimeError("missing API wallet private key")

    wallet = Account.from_key(secret_key)
    exchange = Exchange(
        wallet,
        BASE_URL,
        account_address=account_address,
        perp_dexs=DEXES,
    )

    # 陈旧请求保护；具体窗口必须根据延迟统计校准。
    # exchange.set_expires_after(int(time.time() * 1000) + 3000)

    cloid = new_cloid()
    response = exchange.order(
        coin,
        is_buy,
        float(size),
        float(decision.limit_price),
        {"limit": {"tif": "Ioc"}},
        reduce_only=False,
        cloid=cloid,
    )
    status = parse_first_order_status(response)

    # 必须继续通过 CLOID / fills / position 核验，不能只信首次响应。
    order_state = info.query_order_by_cloid(account_address, cloid)
    return {
        "status": "submitted",
        "cloid": cloid.to_raw(),
        "submit_status": status,
        "order_state": order_state,
    }
```

生产实现还必须补充：

- 当前账户净值与保证金核验；
- 仓位方向冲突检查；
- 最大仓位与最大风险检查；
- 最低名义金额检查；
- 当前用户 Maker/Taker 费率；
- funding 与持仓时间成本；
- 精确的请求/响应审计；
- 网络超时后的状态恢复；
- 部分成交后的保护单；
- kill switch 与 dead-man switch；
- 重启恢复和未知订单状态处理。

---

## 12. WebSocket 订单簿订阅骨架

```python
from hyperliquid.info import Info
from hyperliquid.utils import constants


def on_book(message: dict) -> None:
    # SDK 回调消息通常包含 channel/data；保持防御性解析。
    data = message.get("data", message)
    if not isinstance(data, dict):
        return

    try:
        metrics = validate_and_measure_book(data)
    except (KeyError, TypeError, ValueError):
        return

    print(metrics)


info = Info(
    constants.MAINNET_API_URL,
    skip_ws=False,
    perp_dexs=["xyz"],
)
subscription_id = info.subscribe(
    {"type": "l2Book", "coin": "xyz:GOLD"},
    on_book,
)
```

生产系统必须在 WebSocket 之外保留：

- 周期性 REST 快照校验；
- 序列/时间倒退检测；
- 断线重连与重新订阅；
- 心跳；
- 本地接收时间；
- 数据过期后的 fail-closed；
- 同一市场单一权威订单簿状态，避免多个异步任务互相覆盖。

---

## 13. 手续费与成本查询

手续费按用户滚动交易量分级，不能永久硬编码。官方 SDK 提供：

```python
fees = info.user_fees(account_address)
maker_rate = Decimal(fees["userAddRate"])
taker_rate = Decimal(fees["userCrossRate"])
```

预估 Taker 手续费：

```text
estimated_taker_fee = expected_notional × userCrossRate
```

执行门禁可增加：

```text
entry_cost_bps = cost_from_mid_bps + taker_fee_bps
expected_round_trip_cost_bps =
    entry_cost_bps
    + estimated_exit_cost_bps
    + exit_taker_fee_bps
    + expected_funding_bps
```

不要只比较 Maker/Taker 费率。为了获得 Maker 费率而挂得过远，可能产生更严重的未成交、错失或逆向选择成本。

---

## 14. 最佳实践案例

### 案例 A：小额黄金入场

条件：

```text
账户净值：500 USDC
目标名义仓位：500 USDC
市场：xyz:GOLD
策略止损预算：5 USDC
```

执行要求：

1. 点差 ≤ 10 bps；
2. 订单簿年龄 ≤ 1 秒；
3. 目标仓位完整覆盖；
4. VWAP 滑点 ≤ 10–15 bps；
5. 总入场成本不超过风险预算的一定比例；
6. IOC 限价；
7. 未成交部分取消；
8. 实际成交后重新计算止损数量。

即使 500 USDC 不会显著冲击市场，若往返成本为 30 bps，成本约 1.50 USDC，已经占 5 USDC 风险预算的 30%。

### 案例 B：订单簿突然变薄

```text
决策时 spread = 6 bps
预估 VWAP 滑点 = 8 bps
发送前复核 spread = 28 bps
```

正确行为：

```text
拒绝下单
记录 MARKET_CHANGED_BEFORE_SUBMIT
重新等待新的策略/执行条件
```

错误行为：沿用旧订单簿结果继续提交。

### 案例 C：IOC 部分成交

```text
请求买入 2.0 单位
实际成交 1.2 单位
剩余 0.8 单位取消
```

正确行为：

1. 不自动追价；
2. 查询实际 fills；
3. 确认真实仓位为 1.2；
4. 按 1.2 重算止损和风险；
5. 创建 1.2 的 reduce-only 保护单；
6. 将该交易标记为 `PARTIAL_FILL_ACCEPTED` 或按政策平掉。

### 案例 D：止损限价未成交

```text
Stop trigger = 4,000
Limit = 3,996
市场从 4,001 跳到 3,990
```

结果：Stop Limit 可能已触发但无法成交。系统必须：

- 识别 `TRIGGERED_NOT_FILLED`；
- 禁止新增风险；
- 根据预先批准的紧急政策改用更激进 reduce-only IOC；
- 不能静默等待。

### 案例 E：周末传统资产永续

周末黄金/股指永续虽然可以交易，但传统现货和期货市场关闭，外部套利路径可能减弱。默认建议：

- 自动入场关闭；
- 仅人工复核；
- 更严格的点差和深度门禁；
- 降低名义仓位；
- 禁止使用宽滑点市价单；
- 记录周末与工作日独立的执行统计。

### 案例 F：API 超时

发送订单后客户端超时，不代表订单未执行。正确行为：

1. 不立即使用新 CLOID 重发；
2. 使用原 CLOID 查询订单状态；
3. 查询 fills 和仓位；
4. 只有在状态明确为未执行且市场仍满足条件时，才能创建新 OrderIntent；
5. 未知状态时 fail-closed。

---

## 15. 必须保存的执行证据

每次允许、拒绝和成交都应保存：

```text
policy_version
strategy_signal_id
order_intent_id
cloid
coin / dex / asset_class
book_exchange_time_ms
book_receive_time_ms
decision_time_ms
submit_time_ms
ack_time_ms
best_bid / best_ask / mid
spread_abs / spread_bps
requested_size / requested_notional
full L2 snapshot hash or immutable reference
expected_vwap
expected_worst_price
expected_slippage_bps
expected_cost_from_mid_bps
maker/taker fee rate snapshot
funding snapshot
local gate result and reason
submitted limit price and TIF
exchange response
filled size / fill VWAP / realized slippage
fees
post-trade position
protection order IDs and states
manual authorization identity and timestamp
```

没有这些证据，无法区分：

- 策略失效；
- 市场条件变化；
- 订单簿深度不足；
- 执行系统错误；
- API 延迟；
- 经纪成本；
- 人工操作偏差。

---

## 16. 测试与上线门禁

建议按以下顺序推进：

### 阶段 0：文档与纯函数

- 点差、VWAP、滑点和成本函数；
- 边界条件单元测试；
- 无网络、无钱包、无签名。

### 阶段 1：历史 L2 重放

- 使用历史订单簿快照；
- 验证门禁拒绝率；
- 校准各资产阈值；
- 评估目标仓位与深度关系。

### 阶段 2：实时只读影子执行

- 实时读取订单簿；
- 生成“本应提交”的 IOC 订单；
- 不发送任何订单；
- 保存预期 VWAP 和后续市场价格；
- 统计数据新鲜度与信号到下单延迟。

### 阶段 3：Testnet

- 独立 API Wallet；
- CLOID；
- `expiresAfter`；
- 部分成交处理；
- 断线恢复；
- dead-man switch；
- TP/SL 失败场景。

### 阶段 4：Mainnet 影子 + 人工手动下单对照

- 自动系统只计算，不签名；
- 人工在前端下单；
- 对比预估和真实成交；
- 校准滑点与手续费模型。

### 阶段 5：有限资金、人类确认的自动执行

- 独立小资金子账户；
- 隔离保证金；
- 单标的、单策略；
- 固定每日最大亏损；
- 逐单人工确认不可变 OrderIntent；
- 自动保护、kill switch、审计。

### 阶段 6：扩大范围

仅在以下证据充分后扩大：

- 数据稳定；
- 订单状态恢复稳定；
- 保护单成功率达标；
- 实际滑点分布稳定；
- 最差成交和异常场景可控；
- 安全审查通过；
- 生产授权明确。

自主入场不应从人类确认执行自动推导获得授权。

---

## 17. 关键失败状态

建议统一失败码：

```text
STALE_BOOK
EMPTY_BOOK_SIDE
CROSSED_BOOK
SPREAD_TOO_WIDE
INSUFFICIENT_DEPTH
VWAP_SLIPPAGE_TOO_HIGH
TOTAL_ENTRY_COST_TOO_HIGH
MARKET_CHANGED_BEFORE_SUBMIT
SIZE_ROUNDS_TO_ZERO
MIN_NOTIONAL_NOT_MET
INVALID_PRICE_PRECISION
INVALID_SIZE_PRECISION
RATE_LIMITED
EXPIRES_AFTER_REJECTED
NONCE_CONFLICT
ORDER_REJECTED
ORDER_STATE_UNKNOWN
PARTIAL_FILL_UNRESOLVED
POSITION_MISMATCH
PROTECTION_ORDER_REJECTED
UNPROTECTED_POSITION
WEBSOCKET_STALE
DEAD_MAN_NOT_ARMED
KILL_SWITCH_ACTIVE
```

所有未知状态都必须映射为阻止新增风险，而不是自动重试。

---

## 18. 实施时不得遗漏的边界

1. **点差阈值不等于滑点阈值**；两者必须同时存在。
2. **SDK 默认滑点不是策略参数**；必须显式传入或使用自建 IOC 限价。
3. **最优价深度不等于整单深度**；必须计算完整 VWAP。
4. **限价保护成交价格，但不保证成交**。
5. **市价止损提高退出概率，但不保证价格**。
6. **部分成交会改变真实风险和保护数量**。
7. **请求超时不代表订单失败**。
8. **API Wallet 地址不能替代主账户地址查询账户状态**。
9. **多个进程共享签名钱包会增加 nonce 冲突风险**。
10. **HIP-3 市场必须动态读取 DEX、资产元数据、预言机和市场状态**。
11. **周末传统资产永续需要独立风控策略**。
12. **任何执行代码进入仓库不等于获得执行授权**。

---

## 19. 官方资料

以下资料在 2026-08-03 核验：

- Hyperliquid API 总览：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api>
- Info endpoint：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint>
- Exchange endpoint：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint>
- WebSocket：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket>
- WebSocket subscriptions：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions>
- WebSocket heartbeat：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/timeouts-and-heartbeats>
- Rate limits：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits>
- Nonces and API wallets：<https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/nonces-and-api-wallets>
- Order book：<https://hyperliquid.gitbook.io/hyperliquid-docs/trading/order-book>
- TP/SL：<https://hyperliquid.gitbook.io/hyperliquid-docs/trading/take-profit-and-stop-loss-orders-tp-sl>
- Fees：<https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees>
- Risks：<https://hyperliquid.gitbook.io/hyperliquid-docs/risks>
- 官方 Python SDK：<https://github.com/hyperliquid-dex/hyperliquid-python-sdk>
- SDK `Exchange` 实现：<https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/exchange.py>
- SDK `Info` 实现：<https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/info.py>
- SDK TP/SL 示例：<https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/examples/basic_tpsl.py>
- SDK CLOID 示例：<https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/examples/basic_order_with_cloid.py>

---

## 20. 最终工程原则

未来半自动或自动执行系统应固定以下原则：

```text
策略决定是否值得交易；
执行层决定当前是否可以安全成交；
风险层决定允许成交多少；
人类授权决定是否允许发送不可变订单意图；
交易所响应与成交证据决定真实仓位；
真实仓位决定保护单数量；
任何不确定性都阻止新增风险。
```

Hyperliquid 的优势是订单簿透明、仓位颗粒度细、IOC/ALO/CLOID/API 能力完整。其主要执行风险不是“看不到深度”，而是薄市场、瞬时撤单、数据陈旧、宽默认滑点、部分成交、订单状态不确定、API Wallet/nonce 管理和保护单失败。

因此，最佳实践不是寻找一个单独的“最大点差设置”，而是建立一套可审计、可重放、失败关闭的受保护执行管线。
