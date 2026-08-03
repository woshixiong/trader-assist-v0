# First Launch 高相关信号聚类、回测与执行暴露治理 R1

**记录 ID：** `TA-FIRST-LAUNCH-CORRELATED-SIGNAL-CLUSTERING-EXPOSURE-R1-2026-08-04`  
**日期：** `2026-08-04`  
**状态：** `CURRENT RESEARCH STATISTICS / FUTURE EXECUTION RISK AUTHORITY / NON-EXECUTABLE / NON-AUTHORIZING`  
**关联：** Machine Strategy R1/R1.1、Universe/Capacity R1、Forward Validation R1、Multi-Asset Architecture R1、PR #52  
**目的：** 防止多个高度同步市场把同一共同行情重复记为多个独立策略证据；同时为未来半自动和自动交易保留相关风险暴露控制。

---

## 1. 核心问题

多个加密资产以及部分跨资产永续市场可能在同一共同市场行情中：

- 同方向移动；
- 在相近时间触发同一或不同 Setup；
- 同时成功；
- 同时失败；
- 形成多个外观独立、实质高度相关的 ShadowOrder。

如果把这些结果全部当作独立样本，会：

- 夸大样本数量；
- 夸大成功或失败证据；
- 低估估计误差；
- 扭曲 Hit Rate、Mean R、回撤和置信度；
- 在未来自动交易中形成重复方向暴露和集中风险。

固定原则：

```text
KEEP_ALL_MARKET_LEVEL_EVIDENCE = YES
TREAT_ALL_CORRELATED_SIGNALS_AS_INDEPENDENT = NO
CLUSTER_NORMALIZED_RESEARCH = REQUIRED
FUTURE_CORRELATED_EXPOSURE_CONTROL = REQUIRED
```

---

## 2. 不删除任何合格正式信号

所有 `Research Approved Universe` 中的合格正式信号继续：

```text
FORMAL_SETUP_CONFIRMED
→ StrategyDecision
→ PlanDraft
→ NOT_SUBMITTED ShadowOrder
→ T/S/R
→ Outcome
```

不得因为相关性：

- 删除 ShadowOrder；
- 停止 Outcome；
- 丢弃某个市场的执行质量证据；
- 只保留 BTC/ETH；
- 改写原始策略结果。

相关性只改变：

- 独立样本数量解释；
- 聚合统计权重；
- Discord 完整卡片优先级；
- 未来组合风险与执行授权。

---

## 3. 相关性输入合同

使用：

```text
5m simple close-to-close return
return_t = close_t / close_t-1 - 1
```

相关性观察窗口：

```text
CORRELATION_LOOKBACK = 14 calendar days or valid overlapping open-market time
```

窗口结束时间必须严格早于或等于 Formal Signal `confirmed_at`；不得使用信号后的数据决定该信号所属 Cluster。

仅使用两个市场：

- 时间戳相同；
- 都是有效闭合 5m Bar；
- 连续且不跨缺口；
- 都处于可比较的开放市场时间；

的配对 Return。

最低配对观察数：

```text
MIN_PAIRED_RETURNS = 500
```

不足：

```text
CORRELATION_STATUS = INSUFFICIENT_DATA
```

相关系数：

```text
PEARSON_CORRELATION
PRIMARY_THRESHOLD = 0.80
SENSITIVITY_LOW = 0.70
SENSITIVITY_HIGH = 0.90
```

`0.80` 是 R1 主统计阈值；`0.70/0.90` 只用于敏感性报告。

必须保存：

- pairwise correlation；
- paired observation count；
- window start/end；
- source Candle identity/hash；
- calculation version。

---

## 4. 同步事件时间窗口

Formal Signal 按 `confirmed_at` 升序处理。

```text
CORRELATION_EVENT_WINDOW = 15 minutes
```

信号只有同时满足：

- 同方向；
- `confirmed_at <= event_start + 15 minutes`；

才可能属于同一个同步事件窗口。

窗口以第一条信号时间固定，不使用最后一条信号滚动延长，避免链式无限扩张。

超过窗口的新信号建立新的 Correlation Event。

---

## 5. 两类 Cluster

### 5.1 Setup Research Cluster

要求：

- 同一 Setup Family；
- 同一方向；
- 同一 15 分钟事件窗口；
- Cluster 内任意两成员相关系数均 `>= 0.80`。

用途：

```text
评价单个 Setup 的独立证据数量和表现
```

### 5.2 Exposure Cluster

要求：

- 允许不同 Setup Family；
- 同一方向；
- 同一 15 分钟事件窗口；
- Cluster 内任意两成员相关系数均 `>= 0.80`。

用途：

```text
评价产品级共同市场暴露和未来执行集中风险
```

---

## 6. 确定性聚类算法

每个事件窗口内先按以下顺序排列信号：

1. `p10_weak_depth_10bps` 降序；
2. `p95_spread_bps` 升序；
3. Exchange-reported Day Notional 降序；
4. OI Notional 降序；
5. `market_id` 字典序。

第一条信号建立第一个 Cluster。

后续每条信号按 Cluster 建立顺序检查：

只有它与 Cluster 内每一个已有成员都满足：

```text
pairwise_correlation >= 0.80
```

才可加入该 Cluster。

可加入多个 Cluster 时，加入建立最早的 Cluster；没有合格 Cluster 时建立新 Cluster。

这属于 `complete-linkage` 语义，避免通过 A-B、B-C 相关而把 A-C 不相关的市场链式合并。

必要 Pair 数据不足时：

- 不加入已有 Cluster；
- 建立独立 Cluster；
- 标记 `CORRELATION_UNKNOWN`。

---

## 7. Cluster Identity 与不可回写

Setup Research Cluster ID：

```text
sha256(
  strategy_version
  + parameter_version
  + setup_family
  + direction
  + correlation_event_start_time
  + sorted(member_shadow_order_ids)
)
```

Exposure Cluster ID：

```text
sha256(
  strategy_version
  + parameter_version
  + direction
  + correlation_event_start_time
  + sorted(member_shadow_order_ids)
)
```

Cluster 建立后不得因未来行情回写。

迟到数据导致重新计算出现不同结果时：

```text
保留原 Cluster
记录 CORRELATION_RECOMPUTE_DIFFERENCE
不得静默覆盖历史研究样本
```

---

## 8. 回测、前向验证与回撤分析必须输出三套结果

### 8.1 Raw Market-level Metrics

每个 ShadowOrder 保留一条原始市场级结果。

用途：

- 比较不同市场适配性；
- 比较盘口、滑点和执行质量；
- 找出某个资产的系统性失败；
- 保留完整审计证据。

禁止把 Raw ShadowOrder Count 描述为独立样本数。

### 8.2 Cluster-normalized Metrics

作为整体策略效果的主要统计。

一个 Cluster 总权重固定为：

```text
1.0
```

若 Cluster 有 `k` 条 ShadowOrder：

```text
member_weight = 1 / k
CLUSTER_MEAN_R = sum(member_outcome_R) / k
CLUSTER_SUCCESS = CLUSTER_MEAN_R > 0
```

同时保存：

- cluster median R；
- best/worst R；
- mean MFE/MAE；
- member count；
- win/loss dispersion。

策略的 Hit Rate、Mean/Median R、MFE、MAE 和证据样本数量，应以 Cluster 为主要单位。

### 8.3 Leader-only Sensitivity

每个 Exposure Cluster 选择一条 Leader，排序与第 6 节相同。

只使用 Leader Outcome 计算：

```text
LEADER_ONLY_METRICS
```

用途：近似模拟未来只执行该共同行情中执行质量最好的一个市场。

Leader-only 是敏感性统计，不替代 Raw 或 Cluster-normalized 结果。

### 8.4 回撤分析

必须分别报告：

- Raw market-level equity curve / drawdown；
- Cluster-normalized equity curve / drawdown；
- Leader-only equity curve / drawdown。

主要策略风险判断不得只使用 Raw 曲线，因为同步失败会重复放大单一共同事件的回撤。

Cluster-normalized 回撤是研究主口径；Leader-only 回撤是未来单一代表市场执行的敏感性口径。

---

## 9. 必须报告的样本与压缩指标

每个 Strategy Version、Parameter Version、Setup 至少报告：

```text
RAW_SHADOW_ORDER_COUNT
SETUP_RESEARCH_CLUSTER_COUNT
EXPOSURE_CLUSTER_COUNT
CORRELATION_UNKNOWN_COUNT
CLUSTER_COMPRESSION_RATIO
```

其中：

```text
CLUSTER_COMPRESSION_RATIO = EXPOSURE_CLUSTER_COUNT / RAW_SHADOW_ORDER_COUNT
```

该值越低，说明原始信号中的同步重复越严重。

不得只报告 Raw ShadowOrder Count。

---

## 10. Discord 展示边界

相关信号全部保存，但完整即时卡片可优先显示 Exposure Cluster Leader。

同 Cluster 其他成员进入：

```text
CORRELATED_SIGNAL_SUMMARY
```

摘要至少保留：市场、方向、Setup、Entry、Stop、TP、net R、ShadowOrder ID 和 Cluster ID。

Discord 去重不得改变：

- ShadowOrder；
- Outcome；
- T/S/R；
- Research Statistics；
- Evidence Export。

---

## 11. 未来半自动与自动交易风险控制

当前仍固定：

```text
AUTO_TRADE = NO
EXCHANGE_WRITE_AUTHORITY = ABSENT
```

但未来任何能够创建真实暴露的系统必须读取 Exposure Cluster。

至少必须采用以下一种机制：

```text
A. ONE_NEW_POSITION_PER_EXPOSURE_CLUSTER

或

B. SHARED_RISK_BUDGET_PER_EXPOSURE_CLUSTER
```

在组合风险引擎正式冻结前，默认未来安全路线：

```text
ONE_NEW_POSITION_PER_EXPOSURE_CLUSTER
```

也就是说，同一 Exposure Cluster 中同时出现多个合格信号时，只允许执行质量最高且通过全部风险门禁的一个新仓位；其他信号保留研究证据但不增加重复真实风险。

未来如采用共享风险预算，必须明确：

- Cluster 总风险上限；
- 已占用风险；
- 新订单剩余风险；
- 并发预留；
- 部分成交；
- 未知 ACK；
- 撤单待确认；
- 重启恢复；
- 跨市场同方向净暴露。

不得把多个高度相关市场分别按完整单笔风险预算独立下单。

---

## 12. 数据与 Schema 预留

未来 Evidence Schema 至少预留：

- `setup_research_cluster_id`；
- `exposure_cluster_id`；
- `cluster_member_count`；
- `cluster_leader_market_id`；
- `pairwise_correlation`；
- `paired_observation_count`；
- `correlation_status`；
- `correlation_data_hash`；
- `cluster_weight`；
- `correlation_version`。

Capacity Harness 本轮无需生成正式 ShadowOrder Cluster，但必须验证：

- 14 日 5m 数据是否可得；
- 500 个配对 Return 是否可满足；
- 非 24/7 市场重叠时段是否可计算；
- 相关矩阵的 CPU/内存成本；
- 输入和结果是否可确定性重现。

---

## 13. 当前与未来任务边界

当前 Capacity Harness：

- 收集相关性所需原始数据；
- 验证可得性与计算成本；
- 不实施正式策略聚类统计；
- 不实施自动交易风险控制。

新多资产 Shadow System：

- 实施 Cluster Evidence；
- 输出 Raw、Cluster-normalized 和 Leader-only 统计；
- 在前向验证、回测和回撤分析中使用。

未来半自动/自动交易阶段：

- Exposure Cluster 成为真实执行和组合风险门禁；
- 在获得独立策略、风险和工程授权前不得启用交易所写权限。

---

## 14. 最终固定状态

```text
KEEP_ALL_APPROVED_FORMAL_SIGNALS = YES
KEEP_ALL_APPROVED_SHADOW_ORDERS = YES
RAW_SIGNALS_ARE_INDEPENDENT_SAMPLES = NO
CLUSTER_NORMALIZED_PRIMARY_RESEARCH_METRICS = YES
LEADER_ONLY_SENSITIVITY = REQUIRED
CLUSTER_NORMALIZED_DRAWDOWN_REVIEW = REQUIRED
FUTURE_CORRELATED_EXPOSURE_GATE = REQUIRED
DEFAULT_FUTURE_EXECUTION_POLICY = ONE_NEW_POSITION_PER_EXPOSURE_CLUSTER
```

本文件不授权代码修改、依赖安装、部署、服务变更、账户访问、签名、交易所写入、自动下单、PR Mark Ready 或 Merge。