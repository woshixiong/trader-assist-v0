# First Launch 三 Setup 工程可行性、因果 Runner 与回测集成审查

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-ENGINEERING-FEASIBILITY-2026-07-31-R1`  
**日期：** `2026-07-31`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**审查基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**状态：** `ENGINEERING FEASIBILITY AND ROUTE FREEZE / NON-EXECUTABLE / NON-DEPLOYMENT`

本文是现有工程优化窗口对三 Setup 统一量化、有限优化和联合因果回测的长期工程审查结论。本文只冻结工程事实、工具边界、文件范围、兼容性、测试与停止条件；不定义策略参数，不派发执行任务，不授权生产修改、部署、重启、Mark Ready、merge、账户访问、签名或交易所写入。

---

## 1. REVIEW_STATUS

```text
REVIEW_STATUS = PASS_WITH_MANDATORY_CORRECTIONS
RESEARCH_ENGINEERING_ROUTE = FEASIBLE
PRODUCTION_STRATEGY_PATCH = NOT_AUTHORIZED
CURRENT_STANDARD_PROGRESSION = FAIL_CURRENT_RUNTIME_PATH
V0_1_EXACT_BASELINE = REQUIRED
V0_1_INSTRUMENTED_PARITY = REQUIRED
ARCHITECTURE_CHANGE = NONE
DATABASE_SCHEMA_CHANGE = NO
NEW_PRODUCTION_SERVICE = NO
NEW_PRODUCTION_DEPENDENCY = NO
EXCHANGE_WRITE_AUTHORITY = ABSENT
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```

总体裁决：

1. 当前生产策略可以在 runtime 外作为纯判定权威复用，但必须保留其对象 issuance、证据和 hash 约束，不能把 pandas 行或普通 dataclass 直接传给 `evaluate_signal`。
2. 可以建设一个很小的本地因果 runner，并通过文件边界把标准化最终信号交给 Freqtrade 做数据管理、交易模拟和统计。
3. 不需要自研撮合、资金曲线、数据平台或通用回测框架。
4. 当前生产 STANDARD PREPARE 不存在可见的后续闭合 5m K 线推进路径。这是现有 v0.1 runtime 缺陷，必须单独闭合，不能隐藏在三 Setup 优化 patch 中。
5. 研究工作可以继续，但任何生产策略实现必须等待：`STANDARD defect closure + exact parity + joint replay + independent review`。

---

## 2. LIVE_AND_CODE_FACTS

### 2.1 GitHub 与治理事实

审查时 Draft PR #52：

```text
BASE_BRANCH = main
BASE_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
HEAD_BRANCH = agent/v0-strategy-predevelopment-analysis-r1
HEAD_BEFORE_THIS_RECORD = 4423048d0f6e1f5daf39386f45fb7c80017692ec
DRAFT = YES
MERGED = NO
```

PR #52 已固定：

- 三个 Setup 的研究范围；
- FAST 与 STANDARD 均进入研究；
- `V0_1_EXACT_BASELINE` 与 `V0_1_INSTRUMENTED_PARITY`；
- limited local causal runner；
- Freqtrade 主工具路线；
- Backtesting.py 可选第二引擎；
- no architecture/schema/production authority expansion；
- exact SHA + 配置 + SQLite 一致性备份的最低回滚。

### 2.2 当前策略事实

`strategy.py` 当前固定：

```text
STRATEGY_VERSION = ETH-LDAR-v0.1
CONFIGURATION_VERSION = 1
TRADE_PLAN_VERSION = 3
SetupFamily = SWEEP_RECLAIM | BREAKOUT_RETEST
```

当前 `evaluate_signal(snapshot)`：

- 只接受由市场数据权威签发的 `StrategySnapshot`；
- 要求至少 64 根闭合 5m 和 20 根闭合 15m；
- 按固定顺序检查四个候选：Sweep Long、Sweep Short、Breakout Long、Breakout Short；
- 返回第一个 matched candidate；
- FAST 返回 `StrategyOutput`；
- 非 FAST 返回 `PreparedSetup`；
- `decided_setup_ids` 默认空集。

当前 first-match 最终输出不证明后续候选谓词为 false，因此不能用生产最终输出直接回答 overlap、duplicate、opposite candidate 或 suppression。

### 2.3 StrategySnapshot 与时间事实

`EthMarketData.strategy_snapshot(evaluated_at)` 是唯一正式签发入口。它只纳入：

```text
candle.close_time_ms <= evaluated_at
AND candle.evidence.received_at <= evaluated_at
```

READY 还要求：

- 64 根连续 5m；
- 20 根连续 15m；
- metadata 可用；
- activeAssetCtx 可用且不陈旧；
- candles 不陈旧；
- 无 gap、conflict、invalid 或 disconnected。

因此历史 runner 不能直接实例化 `StrategySnapshot`。它必须经现有 parser、`EthMarketData.accept_*` 和 `strategy_snapshot()` 构造因果权威对象。

### 2.4 Runtime、数据库与权限事实

当前 runtime：

- 每个新闭合 5m identity 调用一次 `evaluate_signal(snapshot)`；
- manual execution required；
- `NOT_SUBMITTED`；
- 无账户、私钥、签名或交易所写权限。

SQLite user version 1 只包含：

- `runtime_sessions`；
- `publication_bundles`；
- `notification_outbox`；
- `health_events`。

publication bundle 已以 canonical JSON 保存 strategy output、volatility、overlay、TradePlan、Operator Review Card、ShadowOrder 和 notification payload。三 Setup 研究及最低生产候选均不需要 schema migration。

生产服务此刻的 READY/PID/session 动态值不由本窗口重新读取；总控在任何后续生产执行前必须重新做只读身份门禁。

---

## 3. CURRENT_STRATEGY_REUSE_MAP

| 当前能力 | 研究复用方式 | 权威级别 | 限制 |
|---|---|---|---|
| `Candle` parser 与 evidence | 历史 OHLCV 逐条转成现有 raw envelope，再由 parser 签发 | 必须复用 | 禁止普通 dataclass 构造 |
| `EthMarketData` | 按时间推进、去重、gap/conflict、snapshot | 必须复用 | runner 不复制一套数据权威 |
| `StrategySnapshot` | 每个闭合 5m cutoff 调用 `strategy_snapshot()` | 必须复用 | 必须满足 context/metadata quality |
| `_features()` / ATR / boundary / 15m bias | 通过生产 `evaluate_signal()` 间接调用 | 生产语义权威 | 研究 instrumentation 不得替代最终判定 |
| `evaluate_signal()` | `V0_1_EXACT_BASELINE` 最终候选来源 | 生产语义权威 | first-match 隐藏 raw candidates |
| `PreparedSetup` / `advance_prepare()` | intended STANDARD 研究与缺陷测试 | 规则权威 | 当前 runtime 调用路径不完整 |
| `lifecycle_state()` | expiry/invalidation 参考 | 可复用 | runtime 未枚举全部 retained IDs |
| `StrategyOutput` / geometry | exact v0.1 输出、Entry/Chase/Stop | 必须复用 | 新参数由策略优化窗口冻结 |
| `TradePlan` | exact baseline 风险与 TP1/TP2 | 必须复用 | 研究候选不能伪装成生产已签发对象 |
| `Outcome` | 生产人工成交与结果证据兼容性 | 兼容性权威 | 当前校验绑定全局 strategy version |
| `InMemorySignalLifecycle` | 可用于 deterministic fixture 与 defect reproduction | 有限复用 | 无公开 retained-ID enumeration；不直接成为通用研究框架 |
| notification/systemd/ta-status/transport | 不进入研究 | 禁止接入 | 与回测目标无关 |

### 3.1 OHLCV-only 历史数据的 context bridge

生产 snapshot 的 READY 需要 activeAssetCtx 与 metadata，但当前两个 Setup 的硬触发不读取 OI/funding/metadata。对没有历史 context 的 proxy 数据，允许一个明确标记的研究桥接：

```text
CONTEXT_MODE = OHLCV_ONLY_RESEARCH_BRIDGE
mark/mid = cutoff 时点的因果价格
OI/funding = manifest 中声明的 neutral placeholder
metadata = manifest 中冻结的 symbol precision
source_id = research-only
```

该 bridge 只用于满足现有 snapshot authority，不得被描述为真实 OI/funding 证据。必须做 metamorphic test：在多个合法但不同的 context 值下，当前 v0.1 最终 strategy output 完全相同。若未来 evaluator 开始读取这些字段，bridge 自动失效并停止。

---

## 4. STANDARD_PROGRESSION_FINDING

```text
STANDARD_PROGRESSION_FINDING = FAIL
FAILURE_CLASS = EXISTING_V0_1_RUNTIME_INTEGRATION_DEFECT
STRATEGY_RULE_FUNCTION = PRESENT
LIFECYCLE_ADVANCE_FUNCTION = PRESENT
LATER_CANDLE_RUNTIME_INVOCATION = ABSENT
```

当前代码事实：

1. `advance_prepare(setup, later_snapshot)` 能以更晚闭合 5m candle 生成 STANDARD output。
2. `InMemorySignalLifecycle.advance(setup_id, snapshot)` 能推进已保留 PREPARE。
3. public runtime 在 `evaluate_signal()` 返回一个新 `PreparedSetup` 后，立即用同一个 snapshot 调用一次 `advance()`。
4. 此后没有看到每根新 5m K 线枚举并推进 retained PREPARE 的路径。
5. runtime 测试未覆盖“真实后续闭合 5m K 线推进已保留 PREPARE”。

同一 snapshot 的立即 advance 不是正确的后续 K 线推进；STANDARD output 自身还要求 decision trigger 严格晚于 setup trigger。

因此必须区分：

```text
V0_1_EXACT_BASELINE:
复现 ac649 当前实际 runtime 行为，包括 STANDARD 缺陷。

STANDARD_INTENDED_REFERENCE:
研究层按现有 advance_prepare 规则，在后续闭合 K 线上推进 retained PREPARE。
```

`STANDARD_INTENDED_REFERENCE` 不能被称为 v0.1 exact baseline。

后续生产开发前，总控必须单独派发 `CURRENT_STANDARD_PROGRESSION_DEFECT_CLOSURE`：

- 先写 deterministic failing runtime test；
- 只修既有两个 Setup 的后续 PREPARE 推进；
- 不加入 Range 参数；
- 不修改 candle authority、transport、DB schema 或通知；
- 独立 Reviewer 验证 v0.1 FAST 输出不变；
- 该修复通过后，再作为三 Setup intended STANDARD 的基线。

---

## 5. LIMITED_RUNNER_DESIGN

### 5.1 职责边界

允许的 runner 只负责：

```text
ordered bar clock
5m/15m causal alignment
existing parser issuance
EthMarketData ingestion
StrategySnapshot issuance
V0_1_EXACT_BASELINE
V0_1_INSTRUMENTED_PARITY
retained PREPARE state advancement
raw candidate enumeration
final arbitration replay
simple market-event grouping
canonical export
```

明确不负责：

```text
fill engine
matching engine
portfolio accounting
equity curve
fee engine
drawdown statistics
charts
parameter optimizer
data downloader
production persistence
notification
exchange access
```

### 5.2 每个 5m cutoff 的处理顺序

```text
1. ingest newly available 5m / 15m observations
2. reject gaps, duplicate conflicts, non-causal observations
3. issue StrategySnapshot at exact cutoff
4. run V0_1_EXACT_BASELINE through production evaluator/runtime-compatible path
5. run research raw-candidate instrumentation
6. apply exact v0.1 first-match arbitration for parity mode
7. compare normalized final outputs byte-for-byte/field-for-field
8. in intended modes, advance retained PREPARE before admitting a new event
9. export raw/final candidate and lineage records
```

### 5.3 V0_1_EXACT_BASELINE

必须使用冻结 SHA `ac649...` 的代码和调用顺序：

- 不修改 `strategy.py`；
- 不枚举隐藏候选来改变结果；
- 不修复 STANDARD；
- 不加入 Environment State；
- 不加入 Range；
- 输出是 current v0.1 comparator。

### 5.4 V0_1_INSTRUMENTED_PARITY

允许一个 research-only candidate enumerator 精确复刻当前四个 candidate predicate，但它只能用于诊断：

- 记录全部 raw candidates；
- 按同一固定顺序选择 first match；
- 与生产 `evaluate_signal()` 的 normalized final output 对比；
- 每个 bar 必须 100% parity；
- instrumentation 不得签发生产 `StrategyOutput`；
- instrumentation 不得成为未来生产策略权威。

若 full dataset 任一 bar parity 不一致：

```text
V0_1_PARITY = FAIL
ALL_OPTIMIZATION_RESULTS = INVALID
STOP
```

---

## 6. FREQTRADE_INTEGRATION_ROUTE

### 6.1 最薄边界

采用文件/进程边界，不让 Freqtrade 定义 Trader Assist Setup：

```text
Trader Assist limited causal runner
→ canonical signal manifest
→ Freqtrade signal adapter
→ Freqtrade backtesting/statistics/export
→ result mapper joined by immutable candidate/event IDs
```

Freqtrade adapter：

- 读取已冻结的 final signal manifest；
- 只按 exact timestamp、side、candidate ID 映射 entry；
- 读取 runner 已输出的 entry zone、Chase Limit、stop、targets、expiry；
- 不在 pandas 中重算 Sweep/Breakout/Range；
- 用 `enter_tag` / immutable IDs 保持 Setup、FAST/STANDARD 和 market-event lineage；
- 主 timeframe 为 5m；
- 1m 只用于 `--timeframe-detail` 和交易路径；
- 15m 只由原生 runner 参与策略判定。

### 6.2 Freqtrade 负责的能力

- Binance/Bybit 等支持交易所的数据下载与增量更新；
- 1m/5m/15m 数据格式管理；
- fee、entry/exit、SL/TP 和 trade simulation；
- `--timeframe-detail 1m`；
- signal/trade export；
- 收益、回撤和分组统计；
- rejected signal 分析；
- `lookahead-analysis`；
- `recursive-analysis`；
- 简单公开基准。

### 6.3 Hyperliquid 限制

Freqtrade 官方文档明确说明：Hyperliquid API 不提供足以构成正确历史数据的长期历史下载，因此不能把 `freqtrade download-data --exchange hyperliquid` 作为 exact venue 数据路线。

固定双轨：

```text
HYPERLIQUID_EXACT_RECENT_EVIDENCE:
由 Trader Assist 已有 capture、公开只读 API 或独立只读采集获得，随后规范化为 Freqtrade 可读文件。

LONG_HISTORY_PROXY_EVIDENCE:
由 Freqtrade 下载 Binance/Bybit ETH perpetual 历史数据。
```

两类结果必须分开报告，不得合并后声称是 Hyperliquid exact performance。

### 6.4 Bias check 边界

Freqtrade `lookahead-analysis` 与 `recursive-analysis` 必须运行，但它们主要检查 Freqtrade dataframe/indicator adapter。它们不能替代原生 runner 的逐 bar 因果性和 v0.1 parity。两层 Gate 都必须 PASS。

---

## 7. BACKTESTING_PY_TRIGGER_CONDITIONS

Backtesting.py 不作为默认第二引擎。只有以下任一条件成立才评估启用：

1. native candidate IDs 与 Freqtrade entry IDs 已完全对齐，但 trade path、stop/target 顺序仍存在无法解释的重大差异；
2. Freqtrade 的同 bar、partial exit、动态 stop 或 expiry 表达使结论可能从 GO 变为 REJECT/INCONCLUSIVE；
3. 需要一个独立逐 bar 实现验证特定 Setup 的 execution path；
4. 独立 Reviewer 明确要求第二引擎；
5. 产品或策略裁决依赖一项 Freqtrade 无法透明解释的执行假设。

在启用前必须先完成：

- same signal/event ID reconciliation；
- fee/spread/slippage/next-open 假设对齐；
- intra-bar ambiguity 分类；
- Freqtrade adapter bug 排除。

仅因总 PnL 不同不得直接引入第二引擎。

Backtesting.py 必须保持离线研究环境，不进入生产 package、systemd 或服务器运行依赖。

---

## 8. DATA_AND_TIME_PLAN

### 8.1 数据集分类

每个 dataset manifest 必须声明：

```text
EVIDENCE_CLASS = HYPERLIQUID_EXACT_RECENT_EVIDENCE
              | LONG_HISTORY_PROXY_EVIDENCE
VENUE
MARKET_TYPE
SYMBOL
TIMEZONE = UTC
TIMEFRAMES = 1m | 5m | 15m
RAW_SOURCE
RAW_HASHES
NORMALIZED_HASHES
START
END
GAPS
DUPLICATES
CONFLICTS
DOWNLOAD_OR_CAPTURE_TOOL_VERSION
NORMALIZATION_VERSION
```

大型历史数据不提交 Git；Git 只保存 schema、manifest、hash、命令和小型 deterministic fixtures。

### 8.2 因果时间语义

在每个 5m decision cutoff：

- 只使用已经闭合并已到达的 5m；
- 只使用 `15m.close_time <= 5m decision cutoff` 的 15m；
- 不用正在形成的 15m；
- 1m 不参与信号判定；
- context/metadata evidence 的 `received_at` 必须不晚于 cutoff；
- 每个 source event 必须有 deterministic sequence 与 hash；
- 缺失、重复冲突或跨时区歧义 fail closed。

### 8.3 Execution time

策略窗口后续冻结人工延迟模型；工程层必须支持：

- candidate time；
- confirmation time；
- earliest executable time；
- fee/slippage；
- 1m 路径；
- 无 1m 时 `AMBIGUOUS_PATH` + conservative assumption。

不得用触发 K 线内未来 high/low 为同一 K 线的信号决定成交。

---

## 9. RAW_CANDIDATE_TECHNICAL_SCHEMA

建议 canonical JSON schema v1：

```text
schema_version
run_id
baseline_sha
strategy_version
strategy_contract_id
mode
venue
evidence_class
market_type
symbol
decision_time
candidate_time
confirmation_time
evaluation_cutoff
source_5m_identities
source_5m_hashes
source_15m_identities
source_15m_hashes
environment_state
setup_family
side
confirmation_mode
raw_candidate_id
production_setup_id_or_null
market_event_id
parent_candidate_id_or_null
boundary
atr
named_predicate_values
raw_eligible
final_selected
state
invalidation_reason_or_null
expiry_time_or_null
entry_low_or_null
entry_high_or_null
chase_limit_or_null
stop_or_null
tp1_or_null
tp2_or_null
overlap_candidate_ids
suppressed_by_or_null
opposite_candidate_ids
ambiguous_path
canonical_hash
```

约束：

- `raw_candidate_id` 是研究身份，不冒充 production `setup_id`；
- `named_predicate_values` 必须保留数值和布尔判定，不能只给 matched=true；
- raw candidate 不保存收益或资金曲线；
- final trade 结果由 Freqtrade result 通过 immutable ID join；
- schema 变更必须版本化。

### 9.1 Market-event grouping schema

```text
market_event_schema_version
market_event_id
venue
evidence_class
symbol
first_candidate_time
last_candidate_time
boundary_lineage
candidate_ids
setup_families
sides
confirmation_modes
same_direction_duplicate_ids
opposite_candidate_ids
selected_candidate_id_or_null
suppression_reasons
grouping_rule_id
canonical_hash
```

只允许预先冻结的简单确定性分组：同一 symbol、同一边界 lineage、有限时间窗、有限 ATR 距离。不得引入机器学习聚类或看完收益后调整 grouping。

---

## 10. EXPECTED_FILE_SCOPE

### 10.1 第一阶段：研究基础设施

预计只新增隔离研究文件：

```text
research/first_launch_three_setup/README.md
research/first_launch_three_setup/contracts/
research/first_launch_three_setup/causal_runner.py
research/first_launch_three_setup/snapshot_adapter.py
research/first_launch_three_setup/raw_candidates.py
research/first_launch_three_setup/event_grouping.py
research/first_launch_three_setup/schemas.py
research/first_launch_three_setup/freqtrade_adapter/TraderAssistSignalReplay.py
research/first_launch_three_setup/environment/tool-versions.lock
research/first_launch_three_setup/manifests/*.example.json
scripts/run_first_launch_three_setup_research.py
tests/research/test_v0_1_exact_baseline.py
tests/research/test_v0_1_instrumented_parity.py
tests/research/test_snapshot_causality.py
tests/research/test_raw_candidate_schema.py
tests/research/test_event_grouping.py
tests/research/test_freqtrade_mapping.py
```

实际路径由总控在执行任务中冻结，但原则不变：研究代码不进入生产 package，不接触 runtime/transport/store。

### 10.2 单独 STANDARD defect closure

仅在总控单独派发并由独立 Reviewer 审查时，最小可能修改：

```text
src/trader_assist_v0/runtime/first_launch_operator_assist.py
src/trader_assist_v0/runtime/first_launch_public_runtime.py
tests/test_first_launch_operator_assist.py
tests/test_first_launch_public_runtime.py
```

不得顺便修改策略参数、Range、candle authority、transport、notification 或 DB schema。

### 10.3 最终 production candidate

只有联合回测和产品/策略裁决 GO 后才重新冻结。当前不得预先生成 production patch。

---

## 11. DEPENDENCY_AND_LICENSE_DECISION

```text
PROJECT_RUNTIME_DEPENDENCY_CHANGE = NO
PROJECT_DEV_DEPENDENCY_CHANGE = NO
ISOLATED_RESEARCH_DEPENDENCY = YES
FREQTRADE = GPL-3.0 / PRIMARY_RESEARCH_TOOL
BACKTESTING.PY = AGPL-3.0 / OPTIONAL_SECOND_ENGINE
```

执行原则：

- 不修改当前 `pyproject.toml` 的生产或 dev dependency；
- Freqtrade 使用独立 venv/conda 环境，并在 task 开始时冻结 exact version、Python version、lock/hash；
- Backtesting.py 只在触发条件成立时创建独立环境；
- 适配通过 canonical files，避免将 Freqtrade/Backtesting.py import 到生产 package；
- 不 vendor 第三方源码；
- 不把第三方策略代码复制进 proprietary core；
- 若未来分发包含 GPL/AGPL 代码的组合包、修改版或服务，必须先做独立许可证审查；本文件不替代法律意见。

官方来源：

- Freqtrade documentation: https://www.freqtrade.io/en/stable/
- Freqtrade repository/license: https://github.com/freqtrade/freqtrade
- Hyperliquid history limitation: https://github.com/freqtrade/freqtrade/blob/develop/docs/exchanges.md
- Backtesting.py documentation: https://kernc.github.io/backtesting.py/doc/backtesting/
- Backtesting.py repository/license: https://github.com/kernc/backtesting.py

---

## 12. TEST_AND_REVIEW_PLAN

### 12.1 Native runner tests

必须包括：

1. parser-issued Candle only；
2. direct/fake StrategySnapshot rejected；
3. 64x5m / 20x15m warmup；
4. 15m future candle excluded；
5. exact close/received-at cutoff；
6. gap/duplicate/conflict fail closed；
7. context bridge metamorphic invariance；
8. all four current raw predicate paths；
9. current first-match order；
10. full dataset exact baseline determinism；
11. instrumented parity 100%；
12. raw overlap visible；
13. candidate IDs deterministic；
14. market-event grouping deterministic；
15. proxy/exact evidence never mixed；
16. no network, account, DB or production path access。

### 12.2 STANDARD tests

必须独立覆盖：

- current same-snapshot behavior；
- retained PREPARE on next closed 5m；
- confirmation on later candle；
- expiry；
- invalidation；
- duplicate decision；
- multiple retained setup IDs；
- FAST output unaffected；
- reconnect/process lifecycle policy explicitly documented。

### 12.3 Freqtrade adapter tests

- one native final signal maps to exactly one Freqtrade entry；
- raw unselected candidate never enters；
- Setup/side/FAST-STANDARD/event ID preserved；
- no pandas recomputation of strategy predicates；
- 1m detail affects execution only；
- explicit fee config；
- signal/trade export joins back to native IDs；
- rejected/chase/expiry visibility；
- lookahead-analysis PASS；
- recursive-analysis PASS；
- no cached result substitution。

### 12.4 Independent Reviewer

Reviewer 必须核验：

- exact base/head；
- file scope；
- no production dependency/schema/transport changes；
- baseline uses real production evaluator；
- instrumentation diagnostics-only；
- parity 100%；
- causal 5m/15m alignment；
- all raw candidates exported；
- Freqtrade mapping event-level reconciliation；
- data class separation；
- license/process boundary；
- mixed-version and rollback tests；
- unit tests 未冒充历史回测。

Writer 不得自证最终 PASS。

---

## 13. VERSION_COMPATIBILITY_AND_MINIMUM_ROLLBACK_PLAN

### 13.1 Research 阶段

- 不修改 `STRATEGY_VERSION`；
- 不修改 `TRADE_PLAN_VERSION`；
- 不修改 SQLite schema；
- Range 和优化候选使用 `strategy_contract_id` / `research_candidate_id`；
- 不生成伪生产 setup_id。

### 13.2 未来 production candidate 的版本风险

当前全局 `STRATEGY_VERSION` 被用于：

- setup_id；
- TradePlan authority；
- signal_id；
- Outcome serialized validation；
- mixed-version history interpretation。

因此禁止简单把全局常量从 v0.1 改为 vNext。未来最低兼容路线必须：

1. 根据 record 中嵌入的 `strategy_version` 做 version-aware hash/semantic dispatch；
2. 保持 v0.1 setup_id、signal_id 和历史 JSON 字节级解释不变；
3. 新输出使用新 strategy version；
4. TradePlan v3 在 serialized shape 不变时继续使用；
5. database user_version 保持 1；
6. v0.1/vNext mixed rows 可读取；
7. pending v0.1 notifications 可继续交付；
8. current runtime startup 不因旧行失败；
9. Outcome 能验证嵌入版本，而不是只读取当前全局常量。

若无法在无 schema migration 下闭合，停止并重新评估，不得在 48 小时范围内强行上线。

### 13.3 最低回滚准备

```text
ROLLBACK_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
ROLLBACK_STRATEGY = ETH-LDAR-v0.1
DATABASE_SCHEMA_CHANGE = NO
```

部署前保存：

- exact repository SHA 与部署包；
- current risk/public configuration 的 hash 与受控备份；
- systemd unit/drop-ins；
- activation permit presence/hash，不读取敏感内容；
- READY / MainPID / NRestarts / session baseline；
- SQLite consistent backup；
- restore old SHA/config/unit/database 的命令。

SQLite 备份应使用 SQLite Online Backup API、Python `sqlite3.Connection.backup()` 或等价一致性方法；不要把 live WAL 数据库的裸 `cp` 当作首选证据级备份。

回滚顺序：

1. 归档升级期间日志和新证据；
2. 恢复 exact old SHA、配置和 unit；
3. 若 mixed-version rows 使 old SHA 不兼容，恢复 pre-deployment SQLite backup；
4. 重新核验 service、READY、PID/session、candle finalization、strategy evaluation、notification；
5. 确认 exchange-write authority 仍 absent。

---

## 14. STOP_CONDITIONS

出现任一条件立即停止，不进入生产 patch：

- `V0_1_EXACT_BASELINE` 无法稳定复现；
- `V0_1_INSTRUMENTED_PARITY < 100%`；
- 必须绕过 issuance 才能构造 StrategySnapshot；
- context bridge 影响 v0.1 策略输出；
- STANDARD defect 未独立闭合；
- raw candidate 与 final candidate 无法通过 immutable ID 对齐；
- Freqtrade mapping 无法事件级解释；
- Hyperliquid proxy 被误报为 exact evidence；
- 数据存在未解释 gap/conflict/timezone drift；
- 1m future path 泄漏到 5m signal；
- 需要修改 candle authority、WebSocket/HTTP、reconnect、ta-status、systemd 或 notification；
- 需要 DB schema migration、新生产服务或新生产依赖；
- 研究依赖进入生产 package；
- GPL/AGPL 边界无法保持；
- 每个 Setup 超过一个 primary + 一个有经济理由的 sensitivity；
- 看完收益后修改冻结参数而不登记新 trial；
- mixed-version history、pending notification 或 rollback compatibility FAIL；
- exact SHA/config/SQLite 回滚路径无法证明；
- 两轮 bounded repair 仍不能闭合同一根因。

---

## 15. INPUT_FOR_PRODUCT_FUNCTION_PLANNING

工程侧向产品功能规划窗口提供以下固定输入：

1. 当前 live v0.1 的 STANDARD 后续推进路径为 FAIL；在缺陷闭合前，不得把 STANDARD 描述为已经可靠工作的生产能力。
2. 研究报告必须明确区分：
   - `V0_1_EXACT_BASELINE`；
   - `STANDARD_INTENDED_REFERENCE`；
   - candidate contract；
   - final combined policy。
3. raw candidate、suppression、opposite candidate 和 event lineage 是研究证据，不要求本轮进入生产 UI。
4. 产品不得把 Binance/Bybit proxy 结果表述为 Hyperliquid exact result。
5. 无 1m 或同 bar 路径不清时必须显示 `AMBIGUOUS_PATH`，不能伪造精确成交顺序。
6. FAST/STANDARD 的产品取舍必须等待分别报告，不得预先取消任一模式。
7. 若 Freqtrade 与第二引擎分歧足以改变准入结论，产品状态应为 `INCONCLUSIVE`，而不是择优采用。
8. 本轮仍是人工最终决策、`NOT_SUBMITTED`；不增加自动交易控制面。

---

## 16. INPUT_FOR_PROJECT_CONTROL

工程侧建议总控后续按以下依赖关系冻结任务，但具体派发仍由总控决定：

```text
A. receive frozen three-Setup contracts from Strategy Optimization
B. freeze dataset manifests, exact/proxy evidence classes and tool versions
C. build V0_1_EXACT_BASELINE
D. build V0_1_INSTRUMENTED_PARITY and require 100%
E. independently reproduce and close current STANDARD progression defect
F. implement isolated candidates and ALL_RAW_CANDIDATES_NO_ARBITRATION
G. run COMBINED_EXACT_POLICY in native runner
H. pass canonical final signals into isolated Freqtrade adapter
I. run fee/path/statistics + lookahead-analysis + recursive-analysis
J. invoke Backtesting.py only if trigger conditions are met
K. independent Reviewer
L. Strategy Optimization + Product Function Planning joint decision
M. only after GO, freeze a new minimum production-candidate task
N. separate CI, merge, deployment and production acceptance authorizations
```

总控每个任务必须冻结：

- exact base SHA；
- exact file scope；
- no-production-authority statement；
- expected artifacts/hashes；
- local gates；
- independent review；
- stop conditions；
- maximum repair count。

本工程优化窗口完成本技术路线后等待总控统一派发，不直接向 Codex、数据准备、Reviewer、CI 或部署窗口派发任务。

---

## 17. 最终工程裁决

```text
CURRENT_STRATEGY_REUSE = PASS_WITH_ISSUANCE_ADAPTER
STRATEGY_SNAPSHOT_CAUSAL_CONSTRUCTION = FEASIBLE
STANDARD_PROGRESSION = FAIL_CURRENT_RUNTIME_PATH
RAW_CANDIDATE_INSTRUMENTATION = FEASIBLE_WITH_100_PERCENT_PARITY_GATE
LIMITED_LOCAL_RUNNER = APPROVED_IN_RESEARCH_SCOPE
FREQTRADE_ROUTE = APPROVED_AS_EXTERNAL_SIMULATION_AND_STATISTICS_TOOL
BACKTESTING_PY = OPTIONAL_TRIGGERED_ONLY
DATABASE_SCHEMA_CHANGE = NO
PRODUCTION_ARCHITECTURE_CHANGE = NONE
RESEARCH_CAN_PROCEED = YES
PRODUCTION_PATCH_CAN_PROCEED = NO
NEXT_AUTHORITY = PROJECT_CONTROL_AFTER_ALL_UPPER_LAYER_GITHUB_OUTPUTS_ARE_FROZEN
```