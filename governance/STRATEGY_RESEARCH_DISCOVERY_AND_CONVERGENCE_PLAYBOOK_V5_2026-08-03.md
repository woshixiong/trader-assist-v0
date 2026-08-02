# Strategy Research Discovery and Convergence Playbook V5

**记录 ID：** `TA-STRATEGY-RESEARCH-DISCOVERY-CONVERGENCE-PLAYBOOK-2026-08-03-V5`  
**日期：** `2026-08-03`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `MANDATORY FUTURE RESEARCH METHOD / NON-EXECUTABLE / NON-AUTHORIZING`  
**优先级：** 本文件取代与其冲突的 V1/V2/V3/V4；旧版本中不冲突内容继续有效。  
**适用范围：** 策略、Setup、Scanner、影子验证、人工复核、参数迭代，以及项目中适合小批量验证的开发工作。  
**权限边界：** 不授权代码修改、工程派发、部署、账户访问、交易所写入或自动交易。

---

## 1. 核心方法：小批量、快速前向验证、证据驱动迭代

项目默认采用：

```text
SMALL_BATCH_CHANGE
→ MINIMUM_CORRECTNESS_GATE
→ HUMAN_CONTROLLED_FORWARD_VALIDATION
→ COMPLETE_EVIDENCE_COLLECTION
→ EVIDENCE_REVIEW
→ LIMITED_VERSIONED_REVISION
→ RAPID_REDEPLOYMENT
→ REPEAT
```

核心目标不是在部署前通过无限研究和工程投入追求一次性完美，而是：

1. 用最小安全代价尽快暴露真实问题；
2. 保持人工最终交易权限和快速回滚；
3. 使用真实市场中的前向证据，而不是只依赖代理历史数据；
4. 每轮只修改有明确证据支持的少量问题；
5. 把可复用的证据、标注、Outcome 和部署流程建设成稳定闭环；
6. 防止单一技术难点演化为无时间上限的研发循环。

```text
RAPID_ITERATION = CORE_PROJECT_METHOD
SMALL_STEPS = REQUIRED
REAL_EVIDENCE_BEFORE_LARGE_REWRITE = REQUIRED
UNBOUNDED_PREDEPLOYMENT_PERFECTIONISM = PROHIBITED
```

---

## 2. 适用前提与安全边界

前向优先方法只在下列边界成立时使用：

```text
HUMAN_FINAL_DECISION = YES
MANUAL_EXECUTION = YES
AUTO_TRADE = NO
EXCHANGE_WRITE_AUTHORITY = ABSENT
SHADOW_ORDER = NOT_SUBMITTED
ROLLBACK = AVAILABLE
EVIDENCE_RETENTION = REQUIRED
```

当未来出现以下任一情况时，完整历史验证、样本外验证和更严格发布门禁必须重新成为部署前条件：

- 自动下单或系统拥有交易所写权限；
- 人工无法逐笔阻断风险；
- 资金规模或风险暴露显著增加；
- 多策略组合、共享资金或仓位仲裁进入生产；
- 策略变更可能自动扩大风险；
- 无法快速回滚；
- 证据链、数据质量或 Outcome 无法完整审计。

---

## 3. 上线前验证与策略有效性证明必须分离

上线前最小验证只回答：

```text
CAN_THE_CODE_EXECUTE_THE_FROZEN_SEMANTICS_CORRECTLY?
```

必须检查：

- 只使用已闭合并已收到的数据；
- 关键状态能够正确确认、继续、失效和取代；
- 同一事件不会重复发出正式信号；
- 新独立事件和趋势分段可以重新进入；
- Entry、Stop、Chase、Target Feasibility 和 ShadowOrder 一致；
- 数据损坏时 fail closed；
- 生产旧版本可回滚；
- 一小段近期数据 Smoke 不出现明显信号洪水或长期沉默的代码缺陷。

上线前最小验证不回答：

```text
IS_THE_STRATEGY_PROFITABLE?
ARE_THE_PARAMETERS_OPTIMAL?
WILL_LIVE_RESULTS_MATCH_HISTORY?
```

这些只能通过历史研究、长期前向证据和真实人工复核逐步回答。

---

## 4. 前向验证不是“实盘回测”

正式术语：

```text
SHADOW_FORWARD_VALIDATION
或
HUMAN_CONTROLLED_FORWARD_TEST
```

它的价值在于：

- 使用真实 Hyperliquid 市场与真实事件顺序；
- 使用当时实际可见的数据；
- 检验 Scanner、Setup、通知、人工判断和 Outcome 的完整路径；
- 获得人类交易员对信号逻辑、入场质量、结构冲突和风险收益的实时反馈；
- 逐步覆盖更多行情状态。

它不能单独证明稳定正期望，也不能把几天或少量样本解释为充分统计结论。

---

## 5. 不预设固定复核日期或样本量

上线前不得根据尚未观察到的 Scanner 运行情况，硬性规定：

- 上线后第几天必须优化；
- 必须等到固定数量才允许查看；
- 每轮一定持续相同时间。

正确流程：

```text
RUN
→ OBSERVE Scanner throughput and evidence quality
→ USER REPORTS CURRENT SAMPLE VOLUME AND QUALITY
→ JOINTLY DECIDE WHETHER REVIEW IS USEFUL
```

复核触发应综合：

- 是否出现明确、重复的策略问题；
- 是否有足够样本支持该具体问题；
- 是否覆盖了相关 Setup、方向和波动状态；
- 数据回收是否完整；
- 修改是否能够被限制在少量变量；
- 当前问题是否影响继续收集有效样本。

如果发现明显的机器语义错误、信号洪水、严重漏报或数据链缺失，可以立即停止等待并修复，不必等待统计样本。

---

## 6. 完整证据优先于只保存人工选择

必须保存所有符合保留合同的：

```text
WATCH
SETUP_READY
FORMAL_SIGNAL
TRADE_PLAN
REJECTED_CANDIDATE_WITH_REASON
```

不得只保存人类最终选择交易的订单。

人工选择会产生选择偏差，因此研究必须同时保留：

- `TAKEN`；
- `SKIPPED`；
- `REJECTED`；
- 未标记但已自动生成 Outcome 的有效候选；
- 人工未执行的正式 Signal；
- Scanner WATCH 到 SETUP_READY 的转换路径。

WATCH 默认不要求逐条人工标注；SETUP_READY 和正式 Signal 才进入快速 T/S/R。

---

## 7. 人工标注必须极简、可解释、可追踪

最低标记：

```text
T = TAKEN
S = SKIPPED
R = REJECTED
```

可选原因码：

```text
1 = MARKET_CONTEXT
2 = LATE_OR_CHASE
3 = STRUCTURE_CONFLICT
4 = RISK_REWARD
5 = SIGNAL_LOGIC_ERROR
6 = LIQUIDITY_OR_EXECUTION
7 = OTHER_SHORT_NOTE
```

要求：

- 一次操作完成；
- 绑定不可变 Candidate/Signal/Plan ID；
- 允许稍后补充简短说明；
- 不要求人类逐项填写系统已经能够自动记录的数据；
- 不使用不可解释的单一信心分数替代原始理由。

---

## 8. 每轮迭代必须版本化

每轮至少记录：

```text
strategy_version
parameter_version
scanner_version
release_sha
deployment_time
change_hypothesis
changed_variables
unchanged_contracts
rollback_target
evidence_window_start
evidence_window_end
```

修改纪律：

- 优先参数和局部规则修改；
- 每个独立问题尽量只改 1～2 个变量；
- 不因为少量坏结果全面重写策略；
- 不把多个互不相关的策略假设塞入同一版本；
- 保留旧版本数据，禁止静默覆盖；
- 新旧版本结果必须可分离。

---

## 9. 每轮工作范围分级

### 9.1 参数或阈值调整

```text
EXPECTED_SCOPE = CONFIG_OR_SMALL_RULE_CHANGE
```

通常只需要：证据分析、参数冻结、测试更新、部署和 Smoke。

### 9.2 局部机器语义修改

例如确认路径、失效条件、Zone 选择或事件去重修改。

```text
EXPECTED_SCOPE = STRATEGY_KERNEL_LOCAL_CHANGE
```

需要新增确定性 Fixture 和回归测试，但不得顺便重构无关基础设施。

### 9.3 架构级问题

例如数据无法完整回收、Scanner 身份不稳定、Outcome 无法链接、状态无法恢复。

```text
EXPECTED_SCOPE = ENGINEERING_BLOCKER
```

必须单独立项和限时解决，不得伪装成普通参数迭代。

---

## 10. 防止无限工程循环

所有策略迭代和相关工程任务必须设置：

```text
EXACT_SCOPE
EXPECTED_OUTPUT
TIMEBOX
STOP_CONDITION
ROLLBACK_OR_FALLBACK
```

原则：

- 一个技术阻塞经过一次高质量诊断仍无法在限定窗口内解决，必须停止并返回路线裁决；
- 不允许连续多轮猜测性修复；
- 不允许为了一个边缘问题扩大为通用平台；
- 不允许在用户未授权时自动延长上线关键路径；
- 可以降级非核心功能，但不得静默破坏证据完整性、人工控制或数据安全。

---

## 11. 长期回测架构的定位

长期可复用回测架构仍然重要，但不再作为当前 First Launch 策略上线的前置条件。

当前只冻结方向：

```text
MATURE_ENGINE
+ ENGINE_AGNOSTIC_STRATEGY_KERNEL
+ THIN_ADAPTERS
+ PROJECT_SPECIFIC_EVIDENCE
+ MINIMAL_DETERMINISTIC_ORACLE
```

其详细选型、兼容性 Spike、开发范围和排期：

```text
DEFERRED_UNTIL_CURRENT_RELEASE_IS_DEPLOYED
```

届时必须重新基于最新策略、Scanner、前向数据和项目资源单独讨论，不得机械执行旧估算。

---

## 12. 默认策略研究目标继续有效

```text
CONTEXT_TIMEFRAME = 1h
PRIMARY_STRUCTURE_TIMEFRAME = 15m
EXECUTION_TIMEFRAME = 5m
MICRO_TIMEFRAME = 1m/3m OPTIONAL_PATH_EVIDENCE_ONLY
TRADING_HORIZON = INTRADAY
HOLDING_TIME = PATH_DEPENDENT_NOT_FIXED
ENTRY_AND_EXIT = MAY_SCALE
HUMAN_FINAL_AUTHORITY = CURRENTLY_YES
```

只根据已发生事实、HTF 标签不提前过滤、Range 不预测突破方向、数据质量与趋势方向分离等 V4 原则继续有效。

---

## 13. 当前固定流程

```text
DISCOVER_AND_CONVERGE
→ FREEZE_MINIMUM_EXECUTABLE_CANDIDATE
→ MINIMUM_CORRECTNESS_VALIDATION
→ DEPLOY_WITH_HUMAN_FINAL_AUTHORITY
→ SCANNER_AND_SHADOW_FORWARD_VALIDATION
→ COMPLETE_EXPORT_AND_REVIEW
→ LIMITED_VERSIONED_REVISION
→ RAPID_REDEPLOYMENT
→ REPEAT_AS_EVIDENCE_JUSTIFIES
```

长期历史回测和前向验证是互补证据，不是互相替代；但在当前人工最终控制、无交易所写权限的 First Launch 阶段，完整历史回测不再自动成为每次小版本上线的硬前置条件。
