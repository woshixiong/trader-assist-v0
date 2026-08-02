# First Launch 当前发布：运维可靠性与灾难恢复阻断项总表

**日期：** `2026-08-02`  
**仓库：** `woshixiong/trader-assist-v0`  
**生产比较/最低回滚基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d`  
**状态：** `PLANNING_ONLY / NON-EXECUTABLE / DEPLOYMENT_CHECKLIST_AUTHORITY`

本文是本轮策略与 Scanner 更新最终进入生产部署前的运维问题统一索引。它不取代各专项合同，不授权实现或部署；其目的仅是保证 Project Control 在最终派发、集成、部署和回滚时不会遗漏任何已冻结运维任务。

---

## 1. 当前已登记运维工作流

### OPS-1 — WebSocket 重连预算错误累计修复

```text
TASK_ID = FIRST_LAUNCH_RECONNECT_BUDGET_RESET
CLASS = P1_PRODUCTION_RELIABILITY
GATE = PRE_DEPLOYMENT_BLOCKER
```

权威文件：

```text
governance/FIRST_LAUNCH_RECONNECT_BUDGET_RESET_NEXT_DEPLOYMENT_BLOCKER_2026-08-02.md
```

核心要求：

- 保留连续恢复失败的有界 fail-closed；
- 只有完整恢复并重新进入 READY 后才重置重连计数；
- 历史成功重连不得永久消耗未来独立事故预算；
- 人工重启和 systemd 自动重启都不能替代源码修复；
- 必须完成事故复现测试、连续失败预算测试、完整 CI 和独立 Review；
- 未通过不得形成可部署生产候选。

最低门禁：

```text
RECONNECT_BUDGET_RESET_TEST=PASS
CONSECUTIVE_FAILURE_BUDGET=PASS
SUCCESSFUL_READY_RESET=PASS
FULL_CI=PASS
PR_REVIEW=PASS
```

### OPS-2 — 主机外备份、恢复验证与 Lightsail 快照退役

```text
TASK_ID = TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT
CLASS = OPERATIONS_RELIABILITY / DISASTER_RECOVERY / COST_OPTIMIZATION
PRIORITY = P1_OPERATIONAL_READINESS
GATE = DEPLOYMENT_WORKFLOW_REQUIRED
```

权威文件：

```text
governance/TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT_NEXT_DEPLOYMENT_SCOPE_2026-08-02.md
```

核心要求：

- 源码、部署文件和环境从 GitHub exact SHA 重建；
- `runtime.db` 和必要生产配置建立主机外加密备份；
- 通知凭据从独立安全来源恢复，不写入普通 manifest；
- 使用 SQLite 一致性备份，不直接复制正在写入的数据库；
- 上传后必须重新下载、校验、解密、只读打开并执行 integrity check；
- 完成最小离线恢复演练和第二本地副本；
- 只有全部门禁通过后，Lightsail 快照才具有删除资格；
- 快照实际删除仍需单独授权。

关键状态：

```text
CURRENT_LIGHTSAIL_SNAPSHOT = 0619-predeploy-20260726T195309Z
IMMEDIATE_SNAPSHOT_DELETE = NO
OFF_HOST_BACKUP_REQUIRED = YES
POST_DEPLOY_RESTORE_VERIFICATION_REQUIRED = YES
```

---

## 2. 与功能发布的关系

本轮最终工作流包括：

```text
TRACK A = THREE SETUP MINIMUM RELEASE
TRACK B = SCANNER LITE R3
TRACK C = SHARED EVIDENCE / NOTIFICATION / DEPLOYMENT
TRACK D = RECONNECT BUDGET RESET
TRACK E = OFF-HOST BACKUP / DISASTER RECOVERY / SNAPSHOT RETIREMENT
```

Track D 和 Track E 均不得被策略或 Scanner 功能开发掩盖，也不得通过人工操作长期规避。

### Track D 时点

必须在最终生产 release candidate 形成和部署前全部闭合。

### Track E 时点

分为三个阶段：

```text
PRE_DEPLOYMENT:
- 备份实现、测试、配置和 runbook 完成
- 创建部署前一致性备份
- 本地完整性与加密上传通过

DEPLOYMENT:
- 按统一 exact SHA 部署
- 完成 READY 和非交易验收

POST_DEPLOYMENT:
- 创建部署后备份
- 重新下载验证
- 离线恢复演练
- 凭据恢复来源确认
- 第二本地副本确认
- 单独授权后删除 Lightsail 快照
```

因此，快照删除不是部署前门禁，但“可验证备份能力”和“部署前备份成功”是部署工作流的必需部分。

---

## 3. 最终部署前统一核对清单

Project Control 在派发最终部署前必须重新列出并逐项确认：

```text
[ ] Three Setup scope frozen
[ ] Scanner scope frozen
[ ] Reconnect budget source fix reviewed
[ ] Reconnect incident regression tests PASS
[ ] Consecutive failure fail-closed PASS
[ ] Full CI PASS
[ ] Backup implementation/tests PASS
[ ] Off-host destination and least-privilege credentials ready
[ ] Encryption and key recovery route confirmed
[ ] Pre-deployment consistent SQLite backup PASS
[ ] Pre-deployment manifest/checksum/encryption/upload PASS
[ ] Exact release SHA and rollback SHA frozen
[ ] Production configuration and DB backup inventory complete
```

部署后必须确认：

```text
[ ] Production READY
[ ] Worktree clean
[ ] Single process / expected services
[ ] No exchange write authority
[ ] Post-deployment backup PASS
[ ] Downloaded backup checksum PASS
[ ] Downloaded decrypt/read-only integrity PASS
[ ] Offline restore drill PASS
[ ] External credential recovery confirmed
[ ] Secondary local copy PASS
[ ] Snapshot deletion separately authorized
[ ] SnapshotUsage follow-up scheduled
```

---

## 4. 统一停止条件

以下任一成立，停止部署或停止快照删除：

- 重连修复测试不完整；
- reconnect fail-closed 被放宽；
- 完整 CI 未通过；
- 数据库备份不是一致性副本；
- integrity check 非 `ok`；
- 备份未加密；
- 上传后未重新下载验证；
- 凭据只有生产主机唯一副本；
- 解密密钥与备份放在同一位置；
- 无恢复 runbook；
- 无第二本地副本；
- 生产部署未 READY；
- 任何步骤要求交易所写权限；
- 任何方案扩大为高可用、第二常驻服务器、PostgreSQL、Kubernetes 或通用备份平台。

---

## 5. 当前权限边界

本文只登记待办和门禁。当前不授权：

- 修改代码；
- 创建实现分支或 PR；
- 安装依赖；
- 创建对象存储；
- 读取生产秘密；
- 执行备份或恢复；
- 重启、部署、merge 或 permit 修改；
- 删除 Lightsail 快照；
- 账户访问、签名或交易所写入。

最终执行由 Project Control 在策略优化和产品范围最终冻结后统一派发。
