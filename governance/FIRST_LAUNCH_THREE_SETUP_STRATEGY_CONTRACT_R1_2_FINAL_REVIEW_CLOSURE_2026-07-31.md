# First Launch 三 Setup 策略合同 R1.2 最终审查闭合

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-STRATEGY-CONTRACT-R1-2-FINAL-2026-07-31`  
**日期：** `2026-07-31`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**前序合同：** R1 + R1.1  
**状态：** `FINAL STRATEGY CONTRACT CLOSURE / NON-EXECUTABLE / NON-DEPLOYMENT`

本文是策略优化进入产品与工程阶段前的最终一致性审查。本文只关闭 R1/R1.1 中仍可能造成产品解释、工程实现或回测结果分叉的交界定义；不新增 Setup、指标、参数网格或 sensitivity，不修改六个预注册 candidate ID 与核心数值阈值。

权威顺序：

```text
R1.2 > R1.1 > R1
```

本文未修改的内容继续由 R1/R1.1 管辖。本文不授权代码修改、回测执行、依赖安装、任务派发、部署、重启、Mark Ready、merge、账户访问、签名、交易所写入或自动下单。

---

## 1. FINAL_REVIEW_STATUS

```text
R1_ECONOMIC_MODEL = PASS
R1_1_PRECISION_MODEL = PASS_WITH_FINAL_EDGE_CLOSURES
R1_2_FINAL_AMBIGUITIES_CLOSED = YES

STRATEGY_DESIGN_OPTIMIZATION = COMPLETE_R1_2_FINAL
BACKTEST_INPUT_CONTRACT = COMPLETE_R1_2_FINAL
PRODUCT_REVIEW_CAN_PROCEED = YES
ENGINEERING_FINAL_ROUTE_REQUIRES_PRODUCT_FREEZE = YES

BACKTEST_EXECUTED = NO
PERFORMANCE_IMPROVEMENT_PROVEN = NO
PRODUCTION_PATCH_AUTHORIZED = NO
```

---

## 2. VOLATILITY_AND_ENVIRONMENT_AUTHORITY

R1 的 Range predicate 曾把 `volatility_regime = NORMAL` 写入环境条件；R1.1 又明确 volatility 是 current-event safety overlay，而非 `ENV_PRE` 结构输入。现最终冻结：

```text
ENV_PRE / ENV_DECISION classification
= only structural, causal inputs defined by R1.1

VOLATILITY_ELIGIBILITY
= separate event-time safety overlay
```

因此：

- Range 可以被结构性分类为 `RANGE`，不因当前 volatility label 改写为其他环境；
- `RANGE_EDGE_REJECTION` 只有在 current event volatility 为 `NORMAL` 时 actionable；
- LOW/HIGH/EXTREME 下的 Range raw evidence仍可记录，但 final eligibility 为 false；
- Sweep/Breakout 继续使用生产同语义 LOW/HIGH/EXTREME overlay；
- volatility 不得反向改变 `ENV_PRE` 的历史结构分类。

---

## 3. RANGE OPPOSITE-EDGE QUALITY

R1 的全局 `Q2` 定义要求 latest reaction age `<=12`，但 Range opposite edge 又允许 age `<=18`。为了避免逻辑冗余和实现分叉，现定义 Range 专用对侧质量：

```text
RANGE_CANDIDATE_EDGE_PRIMARY:
reaction_clusters >= 2
AND latest_reaction_age <= 12

RANGE_OPPOSITE_EDGE_PRIMARY:
reaction_clusters >= 2
AND latest_reaction_age <= 18

RANGE_OPPOSITE_EDGE_SENSITIVITY:
reaction_clusters >= 1
AND latest_reaction_age <= 18
```

产品显示仍可映射为：

```text
candidate edge = Q2+
opposite edge = VERIFIED_18B 或 SINGLE_REACTION_18B
```

不得把 `age=13...18` 的对侧边界错误标为全局 Q2。

---

## 4. STANDARD TARGET-FEASIBILITY TIMING

STANDARD 存在两个不同决策时点：PREPARE 创建和最终确认。现冻结：

### 4.1 PREPARE 时冻结

```text
boundary
A_EVENT_at_prepare
entry zone
chase limit
structural stop
level-quality evidence
environment/transition evidence
structural obstacle candidate set
selected structural obstacle or NO_KNOWN_STRUCTURAL_OBSTACLE
prepare trigger identity/hash
```

PREPARE 时使用 prepare cutoff 的 `decision_reference_price` 计算：

```text
prepare_planned_entry
prepare_target_feasibility
```

`prepare_target_feasibility = FAIL` 时不得建立 PREPARE。

### 4.2 Confirmation 时最终重算

后续第 1–3 根闭合 5m 满足 confirmation predicate 后，使用 confirmation cutoff 的 current `ContextSummary.reference_price`，在冻结 entry zone 内按生产方向性 rounding 计算：

```text
final_planned_entry
```

然后使用：

```text
final_planned_entry
frozen structural stop
frozen selected structural obstacle
confirmation-time cost reserve
```

重新计算 `final_target_feasibility`。只有：

```text
PASS
OR Breakout-specific NO_KNOWN_STRUCTURAL_OBSTACLE
```

才能产生 STANDARD output。

不得在 confirmation 时漂移 boundary、ATR、stop、entry zone 或重新搜索/替换 structural obstacle。PREPARE 阶段通过不代表 confirmation 阶段自动通过。

---

## 5. EXECUTION ACCOUNTING CLOSURES

主回测的 TP/stop/time-exit accounting 最终固定：

```text
entry fill = 100% quantity
TP1 hit = exit 50% original quantity
TP2 hit = exit remaining 50%
TP1 then stop = stop exits remaining 50%
TP1 then TIME_EXIT_24H = time exit closes remaining 50%
stop before TP1 = stop exits 100%
TIME_EXIT_24H before any target = time exit exits 100%
```

- 原 structural stop 在 TP1 后不移动；
- 每个 entry/exit tranche 独立计 fee 和 adverse execution offset；
- funding 只按各 funding timestamp 当时仍开放的剩余数量计收；
- realized R 必须同时以 planned risk 与 actual-entry risk 两种口径报告；
- partial exit 不得被错误计成两笔独立 market event 或两笔独立 trade。

---

## 6. FUNDING EVIDENCE POLICY

```text
HYPERLIQUID_EXACT_RECENT_EVIDENCE:
use timestamp-aligned Hyperliquid historical funding

LONG_HISTORY_PROXY_EVIDENCE:
use timestamp-aligned funding from the same proxy venue and contract
```

任何持仓跨越 funding timestamp 时：

```text
funding_cashflow
= open_notional_at_funding_timestamp * signed_funding_rate
```

方向与支付/收取符号按来源 venue 的正式 perpetual funding 语义处理。

若数据集中存在跨 funding timestamp 的模拟持仓，但相应 funding 证据缺失、时间不对齐或来源不明：

```text
FUNDING_EVIDENCE = INCOMPLETE
AFFECTED_DECISION_UNIT = INCONCLUSIVE
```

不得静默按零 funding 处理，也不得用 Hyperliquid funding 代替 Binance/Bybit proxy funding。

---

## 7. MODE-LEVEL EVIDENCE_AND_GO_UNITS

为了防止 FAST 掩盖 STANDARD 或反之，最终最小经济准入单位为：

```text
setup_family × side × confirmation_mode
```

每个拟启用单元必须独立满足：

```text
independent proxy market events >= 30
net expectancy after all costs > 0
one-sided event-bootstrap 95% lower bound > 0
30s and 60s delay conclusion remains non-negative
concentration gate PASS
holding-rule gate PASS
funding evidence complete
```

因此：

- FAST 可单独 GO，而同 setup-side 的 STANDARD 为 INCONCLUSIVE/REJECT；
- STANDARD 可单独 GO，而 FAST 不启用；
- 只有 FAST 与 STANDARD 分别满足准入时，才允许联合为同一 setup-side policy；
- setup-side 汇总只用于上层解释，不能替代 mode-level Gate；
- 不足 30 个独立事件的 mode 只能 `INCONCLUSIVE`，不得与另一 mode 合并补样本。

---

## 8. EXACT_VS_PROXY_CONTRADICTION

对同一 `setup × side × mode`：

```text
PROXY_DIRECTION = sign(proxy net expectancy after primary costs)
EXACT_DIRECTION = sign(exact recent net expectancy after primary costs)
```

规则：

- exact recent independent events `>=30` 且与 proxy 符号相反：`INCONCLUSIVE_VENUE_CONTRADICTION`；
- exact recent events `<30` 且 point estimate 与 proxy 相反：`INCONCLUSIVE_EXACT_RECENT_SPARSE_CONFLICT`；
- exact recent events `<30` 且方向一致：只能作为支持性证据，不能单独满足统计 GO；
- exact recent 为零、无交易或数据不完整：`INCONCLUSIVE_EXACT_RECENT_INSUFFICIENT`；
- 不允许因 exact sample 较小而完全忽略方向相反的结果。

---

## 9. SIMPLER_POLICY_DOMINANCE

Combined policy 中“not dominated by a simpler eligible subset”最终定义为：

对任一只包含已单独 eligible 单元、且启用单元更少的 subset，若同时满足：

```text
subset net expectancy >= combined net expectancy
subset maximum drawdown <= combined maximum drawdown
subset longest losing streak <= combined longest losing streak
subset cost-stress disposition >= combined disposition
```

且至少一项严格更优，则 combined policy 被 simpler subset 支配：

```text
COMBINED_POLICY = REJECT_DOMINATED_BY_SIMPLER_SUBSET
```

若指标交叉、没有严格支配，则报告 Pareto trade-off，由策略、产品和工程联合裁决，不得仅凭总 PnL 选择更复杂组合。

---

## 10. FINAL ENGINEERING FIXTURES

R1.1 的 fixture 清单继续有效，并新增：

1. Range structural classification 与 volatility eligibility 分离；
2. Range opposite edge age 13–18 能通过 primary opposite verification，但不标全局 Q2；
3. STANDARD prepare reference 与 confirmation reference 不同；
4. final target feasibility 在 confirmation 时失败；
5. frozen obstacle 不在 confirmation 时重选；
6. TP1 后 stop 只关闭剩余 50%；
7. TP1 后 24h time exit 只关闭剩余 50%；
8. funding 按剩余 quantity 与来源 venue 计算；
9. FAST/Standard mode-level sample 不得 pooling；
10. exact/proxy sparse conflict classification；
11. combined policy simpler-subset dominance。

---

## 11. PRODUCT_UPDATE_AFTER_R1_2

产品窗口必须同步理解：

- Environment State 与 volatility eligibility 是两个字段，不能把 HIGH volatility 错显示为“非 Range 环境”；
- Range 对侧边界可使用 18-bar freshness，但不得错误展示为全局 Q2；
- STANDARD 的最终计划价格和 Target Feasibility 在 confirmation 时才最终确定；
- FAST 与 STANDARD 可以具有不同的研究准入结论，产品不得预设必须同时启用；
- funding、TP1/TP2 scale-out、TIME_EXIT_24H、exact/proxy conflict 和 simpler-subset dominance 主要属于研究与准入证据，不要求全部进入 First Launch 主信号卡；
- 当前产品仍是人工最终决定、人工下单、`NOT_SUBMITTED`。

---

## 12. FINAL_STATUS

```text
STRATEGY_CONTRACT_AUTHORITY = R1 + R1.1 + R1.2
STRATEGY_DESIGN_OPTIMIZATION = COMPLETE_R1_2_FINAL
IMPLEMENTATION_PRECISION = PASS
BACKTEST_DETERMINISM = CONTRACTUALLY_CLOSED
PRODUCT_INPUT = READY_FOR_UPDATE
ENGINEERING_INPUT = READY_AFTER_PRODUCT_FREEZE

NUMERIC_PRIMARY_CANDIDATES_CHANGED = NO
SENSITIVITY_COUNT_CHANGED = NO
NEW_INDICATOR = NO
NEW_PARAMETER_GRID = NO
ARCHITECTURE_CHANGE_REQUIRED = NO

BACKTEST_EXECUTED = NO
PERFORMANCE_IMPROVEMENT_PROVEN = NO
STANDARD_RUNTIME_DEFECT = STILL_BLOCKING_PRODUCTION
PRODUCTION_PATCH_AUTHORIZED = NO
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```
