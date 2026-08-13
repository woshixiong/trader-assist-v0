# First Launch Correlated Peer Opportunity Selection & Rotation Research Contract R1

**记录 ID：** `TA-FIRST-LAUNCH-CORRELATED-PEER-OPPORTUNITY-RESEARCH-CONTRACT-R1-2026-08-14`  
**日期：** `2026-08-14`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联：** Draft PR `#52` / Strategy Research Issue `#83`  
**状态：** `FROZEN RESEARCH CONTRACT / POST-LIVE SHADOW / NON-EXECUTABLE / NON-AUTHORIZING`

---

## 1. 研究目标

本合同冻结一个可因果回放、可用 First Live Shadow 数据验证的多资产研究框架，用于回答：

> 当多个高度相关市场同时或先后出现有效三 Setup 机会时，系统是否能在不增加共同风险暴露的前提下，选择或重新选择更优的交易表达，并显著降低 `SELECTION_REGRET`？

本研究不预设 Leader 一定延续，也不预设 Laggard 一定补涨；必须由 Historical / Shadow / Forward evidence 决定。

---

## 2. 当前 Strategy Authority 不变

唯一能够产生交易机会的 Formal Setup 仍然只有：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST (MICRO_FAST + STANDARD)
RANGE_EDGE_REJECTION
```

冻结：

```text
MULTI_ASSET_LAYER_CAN_CREATE_SIGNAL = NO
MULTI_ASSET_LAYER_CAN_OVERRIDE_SETUP_DIRECTION = NO
NEW_FORMAL_SETUP = NO
CURRENT_RELEASE_STRATEGY_CHANGE = NO
AUTO_TRADE_NOW = NO
```

多资产层只允许在已经存在的、因果合格的 Formal Opportunities 之间做：

```text
SELECT
ALLOCATE
RESELECT
ROTATE (RESEARCH ONLY)
REBALANCE (RESEARCH ONLY)
```

---

## 3. 研究证据链

第一阶段优先复用现有证据：

```text
ScannerEvidence
→ Candidate / CandidateTransition
→ StrategyEvaluation / MarketEvent
→ FormalSignal
→ PlanRecord
→ ShadowOrder (NOT_SUBMITTED)
→ canonical 1m Outcome evidence
→ Human T/S/R when available
→ Correlation / Exposure Cluster research views
```

当前 Shadow 证据可以支持第一阶段的真实 forward evaluation，包括：

- Formal signal identity / Setup / mode / side；
- planned entry / stop / TP / reference sizing；
- causal Scanner 15m / 30m / 60m cross-sectional metrics；
- 30m / 60m / 120m MFE / MAE；
- 1R / 1.5R / 2R hit；
- TP / Stop path；
- same-1m ambiguity handling；
- Exposure Cluster；
- T/S/R labels when present。

重要：

```text
SHADOW_ORDER_ALONE = INSUFFICIENT
FULL_EVIDENCE_CHAIN = REQUIRED
```

对于不能因果重建的价格路径，不允许填补或猜测；必须标为：

```text
INCOMPLETE
AMBIGUOUS
NOT_RECONSTRUCTABLE
```

---

## 4. Exposure Cluster Authority

研究继续服从：

`FIRST_LAUNCH_CORRELATED_SIGNAL_CLUSTERING_BACKTEST_AND_EXECUTION_EXPOSURE_GOVERNANCE_R1_2026-08-04.md`

主研究 Cluster 使用现有 causal correlation authority：

```text
RETURN = causal closed-5m simple return
LOOKBACK = 14 calendar days / overlapping open-market evidence
MIN_PAIRED_RETURNS = 500
PRIMARY_CORRELATION_THRESHOLD = 0.80
SENSITIVITY = 0.70 / 0.90
EVENT_WINDOW = fixed 15m from first Formal Signal
CLUSTERING = deterministic complete-link
```

同方向相关机会视为一个 Exposure Cluster 风险问题，不能把多个相关市场当成完全独立风险。

但 C1 / C2 的初始选择集合必须进一步满足：

```text
SAME CLOSED-5M DECISION BOUNDARY
```

不得因为之后 15 分钟内又出现其它 Formal Signal，就回头假设第一时刻已经知道这些信号。

---

## 5. Shared Cluster Risk — 1 CRU

研究统一使用：

```text
1 CRU = 1 CLUSTER RISK UNIT
```

`1 CRU` 表示一个 Exposure Cluster 在一个 policy 中允许承担的总计划止损风险单位。

它不是账户真实百分比，不冻结未来账户必须使用 1% 或 2%。

冻结：

```text
TOTAL_ACTIVE_CLUSTER_PLANNED_RISK <= 1.00 CRU
```

### 单表达策略

```text
C0 / C2 / C3 selected leg / C4 selected leg
= 1.00 CRU to one market
```

### Basket / 多表达策略

Primary research allocation：

```text
EQUAL_PLANNED_RISK
```

若 k 个同组资产同时持有：

```text
risk_i = 1 / k CRU
```

`EQUAL_NOTIONAL` 仅作为 sensitivity baseline，不是首选风险口径。

三个高相关市场不能分别获得三个完整单笔风险预算。

---

## 6. Eligible Opportunity

任何 C0–C5 policy 只能使用在该决策时刻已经因果成立的机会。

必须同时满足：

```text
FORMAL_SIGNAL_EXISTS = YES
PLAN_EXISTS = YES
PLAN_IS_CAUSAL = YES
MARKET_IS_EXECUTION_ELIGIBLE_UNDER_RETAINED_GATES = YES
```

不得把：

```text
WATCH
future SETUP_READY
later Formal Signal
future price outcome
future cluster membership
```

提前作为当前选择依据。

---

## 7. Ranking Input Contract

本 R1 冻结允许研究的输入特征集合，但**不冻结最终权重、阈值或 ML 模型**。

任何 ranking variation 必须在 evaluation sample 之前预注册；不得看完结果再修改权重。

### A. Setup / Plan

- Setup family；
- Setup mode；
- entry quality；
- planned risk distance；
- net R to structural target；
- chase distance / chase utilization；
- remaining chase room / extension state。

### B. Relative Strength

- 15m return；
- 30m return；
- 60m return；
- ATR-normalized move；
- relative-universe return；
- relative-BTC return（适用时）。

### C. Cluster-Relative Strength

第一版默认研究一个最简单、透明的 peer residual：

```text
PEER_RESIDUAL_RETURN_i,h
= RETURN_i,h - MEDIAN(RETURN_eligible_peer,h)
```

其中 `h ∈ {15m, 30m, 60m}`，全部只能使用 decision boundary 之前已关闭的数据。

若有效 peer 数量不足，则该 feature = `UNAVAILABLE`，不得伪造。

### D. Rank Persistence

可研究：

- 15m / 30m / 60m rank consistency；
- leader duration / persistence；
- one-bar spike vs multi-window leadership。

不得把单根 K 线临时领先直接解释为稳定 Leader。

### E. Trend / Pullback Quality

- directional efficiency；
- relative volume；
- pullback depth；
- recovery / reacceleration quality；
- impact retention / giveback（有证据时）。

### F. Execution Quality

- spread；
- depth；
- observed / modeled slippage；
- fee / cost model；
- BBO/L2 freshness；
- venue / underlying pricing regime where relevant。

### G. Context

- time-of-day activity context；
- session / boundary context；
- EventContext / scheduled boundary attribution if available。

时间和 Event 仍然只是 Context，不可独立产生 Long/Short。

冻结：

```text
STRONGEST_PAST_RETURN != BEST_NEW_TRADE
```

---

## 8. C0–C5 因果 Policy Contract

### C0 — FIRST_VALID / HOLD BASELINE

目的：最低复杂度对照组。

规则：

1. 在一个 Exposure Cluster 事件中，取最早 causally eligible Formal Opportunity；
2. 分配 1.00 CRU；
3. 不根据后来的 peer leadership 做切换；
4. 后续按研究用的现有 Plan / Outcome 规则评价。

若多个市场在完全相同 closed-5m boundary 同时成为 eligible，research-only tie-break：

```text
market_id lexical ASC
```

该 tie-break 仅保证 deterministic，不代表经济优先级。

---

### C1 — SAME-BOUNDARY SHARED-RISK BASKET

目的：测试“不猜 Leader，平均承担同主题机会”是否降低 Selection Error。

规则：

1. 只考虑同一个 closed-5m boundary 已经同时存在的 eligible Formal Opportunities；
2. 必须属于同方向 Exposure Cluster；
3. k 个成员共享 1.00 CRU；
4. Primary = equal planned risk，`1/k CRU` each；
5. equal notional / volatility-adjusted 只作 sensitivity；
6. 之后出现的新 peer 不能 retroactively 加入原始 Basket。

---

### C2 — INITIAL BEST-OF-CLUSTER

目的：测试初始机会选择是否具有预测价值。

规则：

1. 只在同 closed-5m boundary 的 eligible peers 中选择；
2. 使用**预注册、纯因果** Opportunity Ranking；
3. rank #1 获得 1.00 CRU；
4. score 完全相同时用 `market_id lexical ASC` tie-break；
5. 不允许用任何后续 Outcome 参与 rank。

如果 ranking contract 在该样本开始前没有冻结，则 C2 observation 不得进入正式 OOS winner evaluation。

---

### C3 — RESET-POINT RESELECTION

目的：测试用户观察到的“第一段行情结束后，第二段不自动重买原资产，而重新选择当前更优 peer”。

为隔离 C3 的增量价值，第一段初始选择默认采用 C0 的 FIRST_VALID，而不是同时叠加 C2。

#### RESET_POINT_V1 — Research-only deterministic definition

第一阶段使用最小、可从当前 Shadow 证据重建的 Reset：

```text
RESET_POINT_V1
= current selected research leg obtains a causally reconstructable
  first definitive TP1-or-STOP path resolution
  under the existing Outcome ambiguity rule
```

重要：

- 这只是 Research Reset，不是生产自动平仓规则；
- `+120m` Outcome horizon 绝不是持仓时间上限；
- 若 TP1 / Stop 的先后无法因果确定，则该 Reset observation 标记 incomplete / ambiguous；
- 如果未来系统拥有更正式的 Position Management terminal/de-risk evidence，可另行升级 Reset contract，但不得静默替换 R1。

Reset 后：

1. 只允许选择 Reset 时间之后的新 closed-5m Formal Opportunity；
2. 在当时 eligible peers 中重新 ranking；
3. rank #1 获得新的 1.00 CRU research leg；
4. 不默认重新进入原资产。

---

### C4 — ACTIVE ROTATION

目的：测试机器是否值得在 A 尚未完成正常研究 leg 时，主动把风险转移到 B。

这是第二阶段高级 policy，不允许先于 C0–C3 证明必要性。

最低因果条件：

```text
A research leg still active
AND B has a fresh eligible Formal Opportunity
AND B ranking advantage is persistent
AND B score advantage exceeds a pre-registered SWITCHING_HURDLE
AND required A-exit/B-entry path and costs are causally reconstructable
```

动作：

```text
A risk -> 0 CRU
B risk -> 1 CRU
```

`SWITCHING_HURDLE`、最小 persistence 等数值参数**本 R1 不冻结**；必须使用 train/validation data 预先选定，然后在 untouched OOS / Forward sample 检验。

若切换时 A 的 causal exit price 或 B 的 executable entry 不能可靠重建：

```text
C4_OBSERVATION = INCOMPLETE
```

不得使用 hindsight close / best price 填补。

---

### C5 — SEQUENTIAL ADD / SHARED-RISK REBALANCE

目的：测试保留 A、同时加入 B 是否优于单表达或 Rotation。

规则：

1. A 已持有 research allocation；
2. B 后来产生 fresh eligible Formal Opportunity；
3. A+B 必须仍属于同方向 Exposure Cluster；
4. 总风险不得超过 1.00 CRU；
5. Primary version 使用 equal planned-risk rebalance。

两资产示例：

```text
before:
A = 1.00 CRU

B becomes eligible:
A = 0.50 CRU
B = 0.50 CRU
```

三资产时：

```text
A = 1/3 CRU
B = 1/3 CRU
C = 1/3 CRU
```

这不是允许 `A 1 CRU + B 1 CRU` 的重复主题暴露。

若 rebalance 所需 causal prices 不完整，则该 observation = incomplete。

---

## 9. 必须同时测试的竞争假设

```text
H1 = LEADER_CONTINUATION
H2 = LAGGARD_CATCH_UP
```

不得事先把任意一条写成 Production Rule。

研究至少输出：

- first-leg leader 下一阶段继续领先的频率；
- laggard 下一阶段反超的频率；
- leader continuation 的 Net R / MFE / MAE；
- laggard catch-up 的 Net R / MFE / MAE；
- 不同 Setup / Cluster / Session / Event regime 下的条件差异。

---

## 10. Forward Outcome / Selection Regret

对于每一个相同决策时刻、相同 eligible peer set，定义 horizon-specific：

```text
NET_R_i,H = causal cost-adjusted research return of eligible market i at horizon H
H ∈ {30m, 60m, 120m}
```

则：

```text
SELECTION_REGRET_H
= max(NET_R_i,H among causally eligible peers)
  - NET_R_chosen,H
```

`SELECTION_REGRET` 只能用于事后评价，禁止成为实时 hindsight input。

同时保留：

```text
MFE_REGRET_H
= max(MFE_R_i,H) - MFE_R_chosen,H
```

以便识别“方向正确但选择了振幅较弱的表达”。

---

## 11. Portfolio Return Reconstruction

不能直接把当前 Correlation Engine 的 `leader` 当成 C2/C3 opportunity leader；当前 leader 是执行/流动性排序，不是 future alpha ranking。

也不能直接把粗粒度 `outcome_r` 当成 C0–C5 最终 portfolio return。

Primary policy return 应尽可能从以下 evidence 重建：

```text
Plan entry / stop / TP
+ canonical 1m path
+ versioned fee / slippage cost assumptions
+ causally available execution evidence
```

对于当前已有 plan path：

- TP-first / Stop-first 可作为 plan-aligned outcome；
- same-1m ambiguity 服从现有 conservative authority；
- unresolved path 不得因为 +120m 到期强制视为退出。

固定 30/60/120m mark-to-market / MFE / MAE 是研究 horizon，不是持仓上限。

---

## 12. Primary Metrics

第一阶段最少输出：

```text
1. Cluster Net R after cost
2. Paired ΔNetR vs C0
3. SELECTION_REGRET_30 / 60 / 120
4. TOP1_FORWARD_CAPTURE_RATE
5. RANK_IC / Spearman rank relation
6. MFE_R / MAE_R
7. Tail MAE / worst cluster loss
8. Cluster drawdown
9. Turnover
10. Fee / spread / slippage cost
11. Leader-continuation vs laggard-catch-up outcome
12. Incomplete / ambiguous reconstruction rate
```

不允许只看总利润。

---

## 13. Paired / Cluster-Normalized Evaluation

所有 policy 比较尽量在同一个 Exposure Cluster event 上做 paired comparison：

```text
DELTA_NET_R_policy,event
= NET_R_policy,event - NET_R_C0,event
```

禁止把同一宏观/行业行情产生的多个高度相关 market-level signals 当成独立样本重复计权。

Primary inference unit：

```text
EXPOSURE_CLUSTER_EVENT
```

Raw market-level 结果仍保留做审计。

---

## 14. Winner / Promotion Standard

### A. RESEARCH_LEADER

可在第一批 Live Shadow 数据后暂时评为 `RESEARCH_LEADER`，但不得因此直接进入自动执行。

至少要求：

```text
paired mean ΔNetR after cost > 0
AND paired median ΔNetR >= 0
AND result is not driven by one isolated cluster / market episode
AND tail MAE / drawdown does not show an obvious material deterioration
```

并同时报告 Selection Regret、turnover 和 incomplete rate。

### B. PROMOTION_ELIGIBLE

要进入未来 Strategy / Engineering implementation review，必须更严格：

```text
OOS / Forward paired advantage remains positive
transaction costs included
cluster-normalized inference used
risk/tail behavior acceptable
result reasonably stable across more than one market/regime slice
no material lookahead / reconstruction defect
```

如果同一次研究尝试大量 ranking variants，必须记录 trial count，并优先使用 walk-forward / held-out OOS；必要时报告 Deflated Sharpe / multiple-testing sensitivity。

### C. Complexity Tie-break

当两个 policy 的 OOS 经济表现相近时：

```text
LOWER TURNOVER
LOWER ENGINEERING COMPLEXITY
LOWER RESTART / EXECUTION SURFACE
```

优先。

因此：

```text
IF C3 ≈ C4
THEN PREFER C3
```

除非 C4 证明有明显、成本后仍存在的增量价值。

---

## 15. 实验顺序

### Stage 1 — First Live Shadow 之后优先跑

```text
C0 FIRST_VALID
vs
C1 SAME-BOUNDARY EQUAL-RISK BASKET
vs
C2 INITIAL BEST-OF-CLUSTER
vs
C3 RESET-POINT RESELECTION
```

原因：

- 当前 evidence 适配度最高；
- 因果规则最清晰；
- engineering cost 最低；
- 足以回答“市场选择错误是否造成显著收益损失”。

### Stage 2 — 只有 Stage 1 显示明显机会成本后再跑

```text
C4 ACTIVE ROTATION
C5 SEQUENTIAL ADD / REBALANCE
```

不得因为理论上更灵活而提前建设高频 Rotation engine。

---

## 16. First Post-Live Trigger

当 First Live Shadow 已积累可用的 multi-asset Formal + Outcome 样本后，必须执行：

```text
MULTI_ASSET_RETURN_AND_SELECTION_REGRET_EVALUATION
```

流程：

```text
FIRST LIVE SHADOW
→ sufficient complete multi-asset Formal / Outcome evidence
→ run C0-C3 bounded offline horse race
→ compute Selection Regret / Rank IC / Cluster Net R
→ Strategy Review
→ decide whether C1 / C2 / C3 deserves implementation
→ only then consider C4 / C5
```

该 TODO 已同时登记在 Strategy Research Issue `#83`。

---

## 17. 成熟外部研究的对照意义

本框架吸收但不机械复制以下成熟研究方向：

- **Moskowitz & Grinblatt (1999)** — Industry Momentum：支持将行业/主题共同动量作为研究对象；
- **Lo & MacKinlay (1989/1990)** — Cross-security lead-lag / cross-autocovariance：支持研究相关资产的信息领先与滞后；
- **Hou (2007)** — Intra-industry information diffusion：支持行业内部 Leader / Laggard 传播假设；
- **Heston, Korajczyk & Sadka (2010)** — Intraday continuation and short-horizon reversal：支持同时测试 continuation 与 reversal，而不是只押一个方向；
- **Gatev, Goetzmann & Rouwenhorst (2006)** — Pairs Trading：支持相关资产偏离/收敛作为竞争假设，但不直接授权本系统做 pairs trade；
- **Blitz, Huij & Martens (2011)** — Residual Momentum：支持剥离共同因素后研究 residual strength；
- **DeMiguel, Garlappi & Uppal (2009)** — 1/N benchmark：支持简单平均风险分配作为强 baseline，但不证明日内 basket 有 alpha；
- **Novy-Marx & Velikov (2016)** — Transaction-cost mitigation / buy-hold spread：支持 Switching Hurdle / no-trade region 思想和避免无必要 churn。

这些研究只提供成熟框架和可检验假设；Hyperliquid / TradeXYZ / 当前三 Setup 的实际经济价值必须用本项目自己的 causal Shadow / OOS evidence 证明。

---

## 18. 当前冻结结论

```text
THREE_SETUP_AUTHORITY = UNCHANGED
MULTI_ASSET_RESEARCH_LAYER = YES
NEW_SETUP = NO
CURRENT_RELEASE_CHANGE = NO
AUTO_ROTATION_NOW = NO
AUTO_BASKET_NOW = NO

PRIMARY_RISK_NORMALIZATION = 1 CRU
PRIMARY_BASKET = EQUAL_PLANNED_RISK
PRIMARY_FIRST_STAGE = C0 vs C1 vs C2 vs C3
PRIMARY_NEXT_RESEARCH_CANDIDATE = C3 RESET-POINT RESELECTION
C4_ACTIVE_ROTATION = SECOND_STAGE_ONLY
C5_ADD_PEER = SECOND_STAGE_ONLY

SHADOW_DATA_CAN_START_EVALUATION = YES
POST_LIVE_MULTI_ASSET_RETURN_EVALUATION = REQUIRED
```

最终目的不是构建更复杂的系统，而是用真实 Forward / Shadow evidence 回答：

```text
IS SELECTION_REGRET ECONOMICALLY MATERIAL?
DOES A CAUSAL RANKING PREDICT FORWARD OPPORTUNITY QUALITY?
DOES C1/C2/C3 IMPROVE CLUSTER NET R AFTER COST?
IS ACTIVE ROTATION WORTH ITS EXTRA COMPLEXITY?
```

如果答案是否定的，则保持更简单的 C0 / 单 Cluster 风险政策；如果答案稳定为肯定，再进入下一轮 Strategy machine semantics freeze。

---

## 19. Authority Boundary

本文件是 Research Contract，不是生产执行授权。

它不授权：

- 当前 release 代码修改；
- 第四 Setup；
- 自动交易；
- 自动 Rotation；
- 自动 Basket；
- shared-risk production execution；
- account/private API；
- signing / wallet / key；
- exchange write；
- deployment；
- runtime mutation；
- Mark Ready；
- Merge。

任何未来 Production promotion 都必须：

```text
SHADOW / OOS EVIDENCE
→ STRATEGY REVIEW
→ PRODUCT / ENGINEERING SCOPE DECISION
→ NEW MACHINE CONTRACT FREEZE
→ IMPLEMENTATION / ACCEPTANCE
```
