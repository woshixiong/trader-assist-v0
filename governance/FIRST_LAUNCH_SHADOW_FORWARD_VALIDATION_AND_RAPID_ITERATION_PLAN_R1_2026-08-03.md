# First Launch 影子前向验证与快速迭代计划 R1

**记录 ID：** `TA-FIRST-LAUNCH-SHADOW-FORWARD-VALIDATION-RAPID-ITERATION-R1-2026-08-03`  
**日期：** `2026-08-03`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `PLANNING / PRODUCT-ENGINEERING ACCEPTANCE INPUT / NON-EXECUTABLE`  
**策略方法权威：** `STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V5_2026-08-03.md`  
**权限边界：** 本文件不授权代码修改、部署、重启、账户访问、签名、交易所写入或自动交易。

---

## 1. 当前决策

当前 First Launch 不再把完整三轮历史回测和长期回测平台建设作为本次上线硬前置条件。

采用：

```text
STRATEGY RESEARCH OPTIMIZATION
→ MINIMUM PREDEPLOYMENT CORRECTNESS VALIDATION
→ SCANNER + EVIDENCE + SHADOW PIPELINE
→ HUMAN-CONTROLLED DEPLOYMENT
→ SHADOW FORWARD VALIDATION
→ EVIDENCE-TRIGGERED STRATEGY REVIEW
→ LIMITED REVISION
→ RAPID REDEPLOYMENT
→ REPEAT
```

该路线的目标是用真实市场、完整证据和人工最终判断进行多轮低风险试错，而不是在第一次部署前追求一次性完美。

---

## 2. 阶段解释

### 阶段一：策略研究优化

由 Strategy Optimization 完成最多 1～2 轮上线前研究审查，冻结一个机器可执行、没有明显逻辑矛盾的候选。

输出：

- 策略版本；
- 参数版本；
- Setup 状态和失效语义；
- Entry、Stop、Chase、Target Feasibility；
- 不允许工程自行推断的事项；
- 已知未验证风险。

该阶段不宣称参数最优或策略已证明盈利。

### 阶段二：最小上线前正确性验证

这是代码和策略语义的安全门禁，不是完整收益回测。

最低验证：

1. 每个上线 Setup/方向/Mode 的正向 Fixture；
2. 关键拒绝和失效 Fixture；
3. closed-and-received-only；
4. 无 lookahead；
5. STANDARD 慢回踩可跨越旧固定窗口；
6. 同一事件去重；
7. 新独立趋势段可重新入场；
8. Entry、Stop、Target 和 ShadowOrder 一致；
9. 小段近期数据 Smoke；
10. 旧生产版本可回滚。

预估：

```text
MINIMUM_CORRECTNESS_VALIDATION = 4～8 person-hours
EXPECTED_ELAPSED = approximately 0.5～1 workday
```

若工程发现需要建设通用 Replay 平台才能完成，必须停止并缩减；本阶段只允许最小 Fixture 和短样本验证。

### 阶段三：Scanner、证据与影子闭环

阶段三包含两部分：

```text
PREDEPLOYMENT IMPLEMENTATION
+
POSTDEPLOYMENT DATA GENERATION
```

上线前必须实现最小闭环；实际数据只会在上线后产生。

Scanner 上线后持续扫描 Hyperliquid eligible perpetuals，保存所有 WATCH、SETUP_READY 和正式 Signal 证据。人类只需对 SETUP_READY 或正式 Signal 进行 T/S/R 快速标注。

阶段三不是使用上线前历史数据，也不是要求提前预测样本数量。

### 阶段四：影子前向验证

上线后不预设固定第几天复核，也不预设一定要达到某个数量。

用户根据实际 Scanner 运行情况持续反馈：

- 候选数量；
- SETUP_READY 数量；
- 正式 Signal 数量；
- 数据是否完整；
- 明显误报、漏报或结构问题；
- 人工交易经验反馈。

Strategy Optimization 根据实际证据判断是否已经值得进入下一轮优化。

### 阶段五：证据触发的有限优化

不预设具体修改方案。

只有数据出现后，才决定：

- 是否需要修改；
- 修改哪些 Setup；
- 是参数问题、语义问题还是工程问题；
- 是否只需继续收集；
- 是否需要快速回滚。

每轮尽量只处理一个主要问题集和少量变量。

---

## 3. 当前数据回收能力审查

### 3.1 已有能力

当前生产基础已具备：

- 正式 actionable `StrategyOutput`；
- `TradePlan`；
- `OperatorReviewCard`；
- `NOT_SUBMITTED ShadowOrder`；
- SQLite `publication_bundles`；
- Notification Outbox；
- T/S/R 人工决策 Journal；
- 手工实际成交导入和离线 Outcome 基础。

正式发布包已经能够绑定：

```text
signal_id
setup_id
plan_id
shadow_order_id
strategy_version
configuration_version
entry
chase_limit
stop
tp1
tp2
risk
volatility evidence
notification identity
```

### 3.2 当前不足

现有生产持久化主要覆盖正式 actionable Signal/TradePlan，并不自动覆盖：

- Scanner 全部 WATCH；
- SETUP_READY 但未形成正式 Plan 的候选；
- 被拒绝候选和拒绝原因；
- point-in-time Universe；
- Scanner 排名、流动性和事件路径；
- 每个候选的 30/60/120m MFE/MAE；
- WATCH 到 SETUP_READY 的转换；
- 大批量统一导出；
- 候选、人工标签、Outcome 的完整性统计。

现有 T/S/R Journal 面向正式 actionable Plan，不能单独承担全 Scanner 候选研究数据集。

因此：

```text
CURRENT_PIPELINE_COMPLETE_FOR_SCANNER_FORWARD_RESEARCH = NO
MINIMUM_EVIDENCE_GAP_MUST_BE_CLOSED_BEFORE_DEPLOYMENT = YES
```

---

## 4. 上线前必须补齐的最小数据合同

### 4.1 Scan 级

```text
scan_id
scan_time
scanner_version
parameter_version
release_sha
universe_snapshot_hash
eligible_count
rejected_count
market_data_freshness
runtime_status
```

### 4.2 Candidate 级

```text
candidate_id
scan_id
asset
dex
asset_class
direction
state
alert_level
setup_family_if_known
market_event_id
scanner_score_components
rank
HTF labels
volatility_state
liquidity fields
prior level / zone
breakout / retest / sweep path
chase status
rejection_reason
linked_signal_id
linked_plan_id
created_at
updated_at
```

所有 WATCH、SETUP_READY 和重要拒绝候选均需保存；Top-N 只限制通知，不得删除后台证据。

### 4.3 人工标记级

```text
annotation_id
candidate_id_or_signal_id
decision = T | S | R
reason_code optional
short_note optional
annotated_at
strategy_version
release_sha
```

WATCH 不要求逐条标注。

### 4.4 Outcome 级

最低自动生成：

```text
30m_MFE_MAE
60m_MFE_MAE
120m_MFE_MAE
ATR_normalized_MFE_MAE
1R_1_5R_2R_hit_if_plan_exists
stop_hit_if_plan_exists
time_to_retest
time_to_1R
return_inside_range
failed_breakout
path_maturity_status
```

### 4.5 完整性级

每次导出必须同时报告：

```text
expected_candidate_count
persisted_candidate_count
candidate_persistence_rate
setup_ready_count
formal_signal_count
annotation_coverage
matured_outcome_count
pending_outcome_count
missing_link_count
duplicate_identity_count
export_manifest_hash
```

没有完整性报告的导出不能用于正式策略结论。

---

## 5. 推荐存储与导出方式

第一版不建设复杂研究平台。

推荐复用当前 SQLite，并增加最小表或等价 append-only JSONL：

```text
scanner_scans
scanner_candidates
candidate_transitions
human_annotations
candidate_outcomes
```

最低导出命令应生成一个版本化数据包：

```text
manifest.json
scans.csv
candidates.csv
transitions.jsonl
annotations.csv
outcomes.csv
formal_publication_links.csv
completeness_report.json
```

导出数据包必须绑定：

```text
release_sha
scanner_version
strategy_version
parameter_version
start_time
end_time
database_checksum
export_hash
```

不得依赖人工从 Discord 复制信号作为主要数据来源。

---

## 6. 人工标注负担控制

默认只标注：

- `SETUP_READY`；
- 正式 Signal；
- 用户认为明显重要但未升级的少量 WATCH。

不要求对全部 WATCH 逐条操作。

T/S/R 必须是一键操作，原因码可选。系统自动记录所有能够自动获得的市场、结构、流动性、版本和 Outcome 字段。

当 SETUP_READY 数量过大时，产品必须支持：

- 批量保持未标记；
- 按状态和时间筛选；
- 后续补标；
- 不标记不影响自动 Outcome；
- 标注覆盖率单独报告。

因此大量 Scanner 候选本身不会阻止完整数据回收；真正不可持续的是要求人类逐条标记全部 WATCH，此方案明确禁止该做法。

---

## 7. 一次性上线前增量工作量

以下不含 Scanner 主逻辑本身，只指影子证据闭环的增量：

```text
candidate persistence and identity = 2～4 person-hours
human T/S/R linkage = 1～3 person-hours
automatic 30/60/120m outcome = 2～4 person-hours
versioned export and completeness report = 2～4 person-hours
tests and smoke = 2～4 person-hours
```

合计预估：

```text
MINIMUM_FORWARD_EVIDENCE_PIPELINE = 9～19 person-hours
NORMAL_ELAPSED = approximately 1～2 workdays
```

如果 Scanner 本身已经以结构化 Candidate 对象和稳定 ID 输出，预计接近区间下限；如果只有通知文本、没有持久状态和稳定身份，接近上限。

必须设置硬停止：不得把该闭环扩展成 Dashboard、通用研究平台、完整 paper-trading 或自动撮合系统。

---

## 8. 第一次上线以后每轮迭代工作量

前提：候选持久化、T/S/R、Outcome 和导出闭环已经完成。

### 8.1 小型参数或阈值迭代

例如 Zone 宽度、确认阈值、Chase、Target Feasibility 或 Scanner 参数。

```text
data export and integrity check = 0.5～1.5 hours
analysis and strategy decision = 1.5～4 hours
config / local rule change = 0.5～2 hours
fixtures and regression = 1～2 hours
CI / review / deployment / smoke = 1～3 hours
TOTAL = 4.5～12.5 person-hours
EXPECTED_ELAPSED = approximately 0.5～1.5 workdays
```

### 8.2 局部策略语义迭代

例如 STANDARD 确认路径、Sweep 失效、Zone 选择、Supersession 或 Re-entry。

```text
data export and analysis = 2～5 hours
strategy semantics freeze = 1～3 hours
implementation = 2～6 hours
fixtures / regression / CI = 2～5 hours
deployment / smoke = 1～2 hours
TOTAL = 8～21 person-hours
EXPECTED_ELAPSED = approximately 1～3 workdays
```

### 8.3 架构或数据链问题

例如 Candidate 丢失、ID 不稳定、Outcome 无法关联、Scanner 状态无法恢复。

这不是普通策略迭代，必须单独工程立项。不得用普通一轮的时间估算掩盖。

---

## 9. 每轮是否需要再次开发

完成第一版闭环后：

- 数据导出：原则上不再开发，只运行固定命令；
- 自动 Outcome：原则上不再开发，只等待成熟并导出；
- 人工 T/S/R：原则上不再开发，只使用；
- 部署：复用固定发布与回滚流程；
- 策略分析：每轮都需要；
- 参数修改：每轮可能需要；
- 新语义 Fixture：只有修改相应语义时需要；
- 基础设施：不应每轮重复开发。

因此，多轮前向测试的单位成本应随闭环成熟而下降，而不是每轮重新从头开始。

---

## 10. 风险控制

### 10.1 资金风险

当前人工最终判断、手工下单和无交易所写权限使资金风险可被人工阻断，但不能据此忽略信息质量和操作风险。

### 10.2 研究偏差

必须防止：

- 只分析 TAKEN；
- 丢弃 SKIPPED/REJECTED；
- 只分析盈利信号；
- 不同版本数据混合；
- 未成熟 Outcome 被当作失败；
- 大量相关标的被当作独立样本；
- 人工反馈覆盖率不足却被当作完整结论。

### 10.3 快速迭代失控

快速迭代不等于频繁随意调参。

每轮必须有：

```text
ONE_PRIMARY_HYPOTHESIS
VERSIONED_CHANGE
UNCHANGED_BASELINE
ROLLBACK_TARGET
POSTDEPLOYMENT_OBSERVATION
```

---

## 11. 当前不预设的内容

当前不冻结：

- 上线后第几天必须复核；
- 每轮必须收集多少候选；
- 第二轮一定修改什么；
- 总共进行多少轮；
- 每个市场状态一定出现多少次。

这些由 Scanner 实际吞吐量、数据完整性和问题严重程度决定。

---

## 12. 长期回测架构待办

长期可复用回测架构仍保留为本轮部署后的高优先级专项：

```text
TASK = LONG_TERM_REUSABLE_BACKTEST_ARCHITECTURE
STATUS = DEFERRED_UNTIL_CURRENT_RELEASE_DEPLOYED
CURRENT_RESEARCH_DIRECTION =
MATURE_ENGINE
+ ENGINE_AGNOSTIC_STRATEGY_KERNEL
+ THIN_ADAPTERS
+ PROJECT_SPECIFIC_EVIDENCE
+ MINIMAL_DETERMINISTIC_ORACLE
```

届时重新讨论：

- NautilusTrader compatibility Spike；
- 数据目录和 Manifest；
- Strategy Kernel 接口；
- Backtest/Shadow/Live Adapter；
- 复用现有前向证据作为验收 Fixtures；
- 开发时间、依赖隔离和长期维护成本。

当前不继续扩大该议题，也不把它放入本次上线关键路径。
