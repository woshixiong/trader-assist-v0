# First Launch WebSocket 重连预算错误累计修复：下一次部署强制阻断项

**记录 ID：** `FIRST_LAUNCH_RECONNECT_BUDGET_RESET`  
**日期：** `2026-08-02`  
**仓库：** `woshixiong/trader-assist-v0`  
**当前生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d`  
**优先级：** `P1_PRODUCTION_RELIABILITY`  
**发布门禁：** `NEXT_DEPLOYMENT_BLOCKER`  
**状态：** `PLANNING_ONLY / NON-EXECUTABLE / MUST_FIX_BEFORE_NEXT_PRODUCTION_DEPLOYMENT`

本文固定一个已经通过生产日志确认的运行时可靠性缺陷。当前服务已通过一次人工受控重启恢复为 READY，因此不进行生产服务器直改，也不单独安排立即 hotfix 部署；但下一次生产上线不得继续携带该缺陷。

本文不授权代码修改、测试执行、分支创建、PR、merge、部署、重启、permit 修改、账户访问、签名、交易所写入或自动下单。最终任务仍由 Project Control 单独派发。

---

## 1. 当前处理决定

```text
PRODUCTION_HOT_EDIT = NO
IMMEDIATE_STANDALONE_HOTFIX_DEPLOYMENT = NO
CURRENT_SERVICE_RECOVERED_BY_CONTROLLED_RESTART = YES
NEXT_DEPLOYMENT_SOURCE_FIX_REQUIRED = YES
NEXT_DEPLOYMENT_BLOCKER = YES
```

固定要求：

1. 当前不直接修改生产服务器源码；
2. 当前不单独进行一次 hotfix 部署；
3. 修复与下一次功能上线合并部署；
4. 修复必须保持独立可验证，不能被 Three Setup 或 Scanner 功能差异掩盖；
5. 下一次上线前必须完成源码修复、事故回归测试、完整 CI、独立 Review 和合并；
6. 人工重启仅是修复部署前的临时恢复手段，不构成缺陷关闭；
7. 不得扩大为新连接管理框架。

---

## 2. 生产运行边界

```text
MODE = RESTRICTED_PUBLIC_LIVE_SHADOW
SCOPE = ETH_ONLY
PUBLIC_ENDPOINTS_ONLY = TRUE
MANUAL_EXECUTION_REQUIRED = TRUE
SUBMISSION_STATUS = NOT_SUBMITTED
EXCHANGE_WRITE_AUTHORITY = ABSENT
```

本任务不得改变信号、TradePlan、风险、人工执行或交易权限。

---

## 3. 事故事实

生产服务曾进入：

```text
NOT_READY | SERVICE_INACTIVE | IGNORE_SYSTEM_SIGNALS
```

systemd 证据：

```text
ActiveState=failed
SubState=failed
Result=exit-code
ExecMainCode=1
ExecMainStatus=1
MainPID=0
NRestarts=0
```

服务退出前连续运行约 17 小时 57 分钟。已排除：

- OOM；
- 磁盘空间不足；
- 部署 SHA 错误；
- 工作树污染；
- activation permit 缺失；
- 环境或风险配置错误；
- Discord credential 缺失；
- 残留重复进程；
- candle confirmation conflict；
- 服务器崩溃。

诊断时：

```text
ACTIVATION_PERMIT=PRESENT
DEPLOYED_SHA=ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
DEPLOYED_WORKTREE=CLEAN
NO_RESIDUAL_RUNTIME_PROCESS
NO_OOM_EVENT
FILESYSTEM_USAGE≈33%
```

退出前最后一组 5m、15m candle 正常 finalized。

最终日志：

```text
2026-08-01T00:02:42.691178Z ERROR websocket: ConnectionClosedOK
2026-08-01T00:02:42.691178Z EVENT disconnect
2026-08-01T00:02:42.691807Z EVENT reconnect-attempt
2026-08-01T00:02:42.692193Z EVENT reconnect-budget-exhausted
```

`reconnect-attempt` 与 `reconnect-budget-exhausted` 相差不到 1 毫秒，说明程序没有真正进行一次新的连接尝试，而是在进入重连路径时发现历史预算已经耗尽。

同一进程此前已有至少 6 次成功重连；第 7 次普通断线错误触发预算耗尽。因此事故不是连续 6 次恢复失败，而是：

```text
6 次已经成功恢复的独立历史断线
+
第 7 次普通断线
=
错误触发生命周期累计预算耗尽
```

当前 systemd 单元为 `Restart=no`，应用退出后不会自动拉起，最终表现为 SERVICE_INACTIVE。

---

## 4. 根因与冻结语义

主要相关文件：

```text
src/trader_assist_v0/runtime/first_launch_public_runtime.py
```

当前默认延迟：

```python
_DEFAULT_RECONNECT_DELAYS = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0)
```

当前 `_reconnect_attempt` 在每次断线进入 `begin_reconnect()` 时递增，但成功完成恢复并重新进入 READY 后没有清零，导致它实际累计整个进程生命周期的断线次数。

错误语义：

```text
整个进程生命周期最多允许 6 次断线
```

必须冻结为：

```text
_reconnect_attempt = 连续未成功恢复 READY 的重连尝试次数
```

正确状态机：

```text
READY
→ disconnect
→ reconnect_attempt = 1
→ recovery failure
→ reconnect_attempt = 2
→ ...
→ complete recovery to READY
→ reconnect_attempt = 0

next independent incident:
READY
→ disconnect
→ reconnect_attempt = 1
```

连续恢复失败达到当前预算后，仍必须 fail closed 并产生：

```text
RECONNECT_BUDGET_EXHAUSTED
```

不得改成无限重连，不得增加预算代替修复。

---

## 5. 允许清零的唯一时点

只有以下恢复链全部成功后才允许清零：

1. 已经进入 reconnect 路径；
2. HTTP public snapshot recovery 成功；
3. 5m candle snapshot 成功；
4. 15m candle snapshot 成功；
5. metadata 成功；
6. WebSocket 建立成功；
7. 三个精确订阅已发送；
8. 三个 subscription acknowledgement 全部验证；
9. 行情上下文达到数据质量要求；
10. 健康状态成功转换为 `RuntimeHealthState.READY`；
11. READY status snapshot 成功发布；
12. 不存在状态发布或持久化异常。

禁止在以下位置清零：

- `mark_disconnected()`；
- `begin_reconnect()` 开始前或内部；
- TCP/TLS/WebSocket 对象创建成功时；
- HTTP snapshot 部分成功时；
- 部分 acknowledgement 时；
- 任意一条 activeAssetCtx 到达时；
- 仅依据日志 `reconnect-success` 时；
- 尚未恢复 READY 权威时。

否则会让持续失败不断重新获得完整预算，破坏 fail-closed。

---

## 6. 推荐最小源码修复

优先核对单一权威位置：

```text
RestrictedPublicRuntime._try_promote_to_ready()
```

推荐原则：

```python
if snapshot.quality.state is DataQualityState.READY:
    if self._health_state is not RuntimeHealthState.READY:
        self._transition_health(
            to=RuntimeHealthState.READY,
            reason="ready-authority",
            now=now,
        )
        if self._reconnect_attempt > 0:
            self._reconnect_attempt = 0
```

实现必须确认：

1. `_transition_health(...READY...)` 和 READY status publication 已成功；
2. 若转换或 status publication 抛出异常，计数不得清零；
3. 初始启动计数本来为 0，不产生副作用；
4. 已经 READY 时普通 context 更新不重复修改；
5. 不在 transport 和 runtime 同时维护两套计数；
6. 不引入新状态框架。

字段改名为 `_consecutive_reconnect_attempts` 或 `_reconnect_failure_streak` 仅属可选清晰度改善。若扩大文件或测试范围，保留原名并用注释和测试冻结语义。

---

## 7. 必须保留的现有行为

- 延迟序列不变；
- 最大连续尝试次数不变；
- 连续失败达到预算仍 fail closed；
- `RECONNECT_BUDGET_EXHAUSTED` 原因不变；
- 不吞掉真实连接异常；
- 不虚假报告 READY；
- 不绕过 status snapshot；
- 不放宽 candle authority；
- 不改任何策略或交易逻辑；
- 不改任何交易权限。

---

## 8. 必须增加的回归测试

主要测试文件：

```text
tests/test_first_launch_public_runtime.py
```

最低矩阵：

### A. 多次独立成功重连不耗尽预算

重复至少 7–8 次：

```text
READY
→ mark_disconnected
→ begin_reconnect
→ recover_public_snapshot
→ all acknowledgements
→ READY
```

每次断言：

```text
runtime.is_ready is True
runtime._reconnect_attempt == 0
```

不得触发 `RECONNECT_BUDGET_EXHAUSTED`。

### B. 连续失败仍耗尽预算

无任何一次恢复 READY，连续重连。达到预算后：

- `begin_reconnect()` 返回 `None`；
- runtime fail closed；
- 不再报告 READY；
- 原因保持 `RECONNECT_BUDGET_EXHAUSTED`。

### C. 失败若干次后成功重置

连续失败 3 次，第 4 次完整恢复 READY，计数必须为 0。下一次独立事故从 1 开始。

### D. 不完整恢复不得清零

覆盖：

- 只开始 reconnect；
- 只完成 HTTP snapshot；
- 只建立 WebSocket；
- 只完成 1/2 个 acknowledgement；
- acknowledgements 完成但质量未 READY；
- 建立后立即关闭；
- snapshot failure；
- acknowledgement timeout；
- public frame validation failure。

所有情况下计数保持大于 0。

### E. READY status publication 失败不得清零

模拟 WARMING → READY 过程中的 status publication 异常，异常继续传播，不能虚假 READY，计数不能提前清零。

### F. 初始启动不受影响

STOPPED → warmup → snapshots → acknowledgements → READY，计数保持 0。

### G. 普通 READY context 无副作用

READY 且计数为 0 时继续接收有效 context，状态和计数不变。

### H. Transport 级近生产循环

至少一个 transport 测试重复超过 6 次：

```text
ConnectionClosedOK
→ reconnect
→ complete READY recovery
```

transport 不退出。另保留连续 6 次均未进入 READY 的失败测试。

---

## 9. 测试和上线门禁

至少执行：

```bash
python -m compileall src scripts tests
python -m pytest -q tests/test_first_launch_public_runtime.py
python -m pytest -q tests/test_first_launch_status.py
python -m pytest -q
```

上线候选必须明确包含：

```text
RECONNECT_BUDGET_RESET_TEST = PASS
CONSECUTIVE_FAILURE_BUDGET = PASS
SUCCESSFUL_READY_RESET = PASS
FULL_CI = PASS
INDEPENDENT_REVIEW = PASS
```

任一不通过，不得上线。

---

## 10. Exact file scope

默认最小范围：

```text
MODIFY:
src/trader_assist_v0/runtime/first_launch_public_runtime.py
tests/test_first_launch_public_runtime.py
\OPTIONAL SMALL DOC UPDATE:
docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md
```

如状态工具已有对应固定文档，可在原 runbook 中增加两条短说明：

```text
Reconnect budget counts consecutive recovery attempts.
A successful transition back to READY resets the counter.
```

以及：

```text
sudo 非交互 shell 使用：
/opt/trader-assist-v0/bin/ta-status
```

不得为此新建连接框架、数据库 schema 或新服务。

---

## 11. 明确不属于本任务

不得修改：

- Three Setup、Scanner Lite；
- Sweep、Breakout、Range；
- candle confirmation B2；
- HTTP snapshot 范围；
- 5m/15m candle 数量；
- risk configuration；
- Discord credential；
-数据库 schema；
- TradePlan、ShadowOrder、T/S/R；
- automatic trading；
- ETH_ONLY；
-多资产 runtime；
-第三方连接框架。

本任务必须保持：

```text
一个生产可靠性缺陷
+
一个最小状态机修复
+
一组针对性回归测试
```

---

## 12. systemd 自动重启

应用层修复是必做项。`Restart=on-failure` 只允许作为独立可选增强评估，不得替代源码修复，也不得默认混入本任务。

如未来决定同时增加，必须单独证明：

- 哪些 exit code 可自动重启；
- 配置错误不会形成循环；
- permit 仍有效；
- 不绕过 fail-closed；
- 每小时重启有严格上限；
- 故障证据保留；
- 不破坏单进程合同。

默认：

```text
APPLICATION_FIX = REQUIRED
SYSTEMD_RESTART_ON_FAILURE = OPTIONAL_SEPARATE_DECISION
```

---

## 13. 修复前临时处置

生产已通过人工重启恢复。若修复部署前再次出现同类故障，应先核验日志和运行身份。只有再次明确出现 `reconnect-budget-exhausted`，且已排除部署身份、工作树、permit、配置、credential、OOM、磁盘和重复进程问题，才允许一次人工受控重启：

```bash
sudo systemctl restart trader-assist-v0-public.service
sleep 10
/opt/trader-assist-v0/bin/ta-status
```

不得设置无限循环重启脚本。

---

## 14. 与下一次上线的合并顺序

下一次上线计划必须显式加入独立可靠性 Lane：

```text
功能范围最终冻结
→ 基于届时权威 integration base 实施最小重连修复
→ 运行事故回归测试
→ 独立 Review
→ 合入统一 release candidate
→ 完整 CI
→ 生成 exact 40-char candidate SHA
→ 部署前专门检查 RECONNECT_BUDGET_RESET_TEST=PASS
→ 一次统一生产部署
```

分支建议：

```text
fix/first-launch-reconnect-budget-reset
```

但创建分支时必须使用届时权威的 integration base，不得盲目从旧生产 SHA 派生；必须先检查 Three Setup/Scanner 分支是否已修改相关 runtime 文件，避免覆盖。

本任务可以与策略和 Scanner 功能实现并行，但必须在最终 integration 和 deployment 前闭合。

---

## 15. 预计工作量

```text
源码修复与针对性测试：1.0–2.0 person-hours
独立 Review 与 bounded repair：0.5–1.0 person-hours
完整 CI 与 release gate：0.5–1.0 elapsed hours（可与其他 release CI 合并）
部署专项验收：0.25–0.5 hours
```

预计新增总工作量：

```text
2–4 person-hours
```

不应扩展为多日任务。

---

## 16. 部署后验收

必须确认：

```text
DEPLOYED_SHA=<authorized exact 40-char SHA>
DEPLOYED_WORKTREE=CLEAN
ACTIVATION_PERMIT=PRESENT
ActiveState=active
SubState=running
MainPID=<non-zero>
```

执行：

```bash
/opt/trader-assist-v0/bin/ta-status
```

预期：

```text
READY | CONTEXT_AGE=<15s | SIGNALS_MAY_BE_CONSIDERED
```

并确认：

- 单一 systemd 主进程；
- 无旧 runtime 残留；
- 无重复 Python 进程；
- 无配置、credential、status snapshot 或 candle conflict；
- 无异常 `reconnect-budget-exhausted`。

不要求在生产中人为制造多次断线。验证分三层：

1. CI 状态机证明超过 6 次独立成功重连不耗尽预算；
2. 部署 SHA 明确包含源码修复和事故回归测试；
3. 上线后自然观察多次 `reconnect-success` 后服务仍继续运行。

---

## 17. 最终验收定义

只有全部成立，才算彻底修复：

```text
SOURCE_FIX=PASS
REGRESSION_TEST=PASS
CONSECUTIVE_FAILURE_BUDGET=PASS
SUCCESSFUL_READY_RESET=PASS
FULL_CI=PASS
PR_REVIEW=PASS
MERGED_EXACT_SHA=PASS
PRODUCTION_DEPLOYMENT=PASS
PRODUCTION_READY=PASS
DEPLOYED_WORKTREE_CLEAN=PASS
```

以下都不算修复：

- 仅人工重启；
- 仅增加重连次数；
- 仅增加 systemd 自动重启；
- 仅修改生产服务器文件。

最终目标：

```text
保留连续失败的有界 fail-closed 保护，
同时消除成功重连被永久累计、最终导致正常服务退出的问题。
```
