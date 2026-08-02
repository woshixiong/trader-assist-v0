# Trader Assist 主机外备份与 Lightsail 快照退役：下一次部署运维工作流

**任务 ID：** `TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT`  
**日期：** `2026-08-02`  
**仓库：** `woshixiong/trader-assist-v0`  
**当前生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d`  
**分类：** `OPERATIONS_RELIABILITY / DISASTER_RECOVERY / COST_OPTIMIZATION`  
**优先级：** `P1_OPERATIONAL_READINESS`  
**状态：** `PLANNING_ONLY / NON-EXECUTABLE / NEXT_DEPLOYMENT_SCOPE`

本文固定下一次生产部署期间必须完成的最小灾难恢复与成本优化工作流。它不是策略功能，不修改交易逻辑，不授权当前执行、安装、上传、部署、快照删除、账户访问或秘密读取。所有实施仍由 Project Control 单独派发和授权。

---

## 1. 最终目标

不再长期依赖 Lightsail 整机快照。生产恢复模型调整为：

```text
CLEAN_HOST
+ GITHUB_EXACT_SHA_REBUILD
+ SECURE_CONFIGURATION_RESTORE
+ SECURE_CREDENTIAL_RESTORE
+ SQLITE_RESTORE
+ SUPERVISED_QUALIFICATION
```

当前 Lightsail 快照：

```text
0619-predeploy-20260726T195309Z
```

不得立即删除。只有新的主机外加密备份、重新下载验证、离线恢复演练和凭据恢复来源全部通过后，才具备删除资格。

---

## 2. 恢复资产分类

### A. 从 GitHub 精确重建，不进入数据备份

```text
/opt/trader-assist-v0
/opt/trader-assist-v0/src
/opt/trader-assist-v0/scripts
/opt/trader-assist-v0/deploy
/opt/trader-assist-v0/bin
/opt/trader-assist-v0/venv
```

恢复必须使用：

```text
EXACT_40_CHARACTER_SHA
DETACHED_CHECKOUT
CLEAN_WORKTREE
HASHED_RUNTIME_DEPENDENCY_INSTALL
```

不得依赖浮动 branch、main 或缩写 SHA。

### B. 必须主机外备份的数据

```text
/var/lib/trader-assist-v0/runtime.db
```

该数据库属于不可从 GitHub 重建的生产运行数据权威。未来 Scanner、T/S/R、Outcome 和研究证据若进入同一或独立持久化，也必须在实施时纳入资产清单。

### C. 必须备份的生产配置

至少核验：

```text
/etc/trader-assist-v0/public.env
/etc/trader-assist-v0/risk-configuration.json
```

同时只读检查 `/etc/trader-assist-v0` 中其他实际生产使用且无法从模板恢复的非秘密配置。禁止打包整个 `/etc`，禁止备份 sing-box、缓存、临时目录或可重建文件。

### D. 凭据

当前通知凭据：

```text
/etc/trader-assist-v0/credentials/notification.json
```

凭据优先从独立安全来源恢复。普通 manifest 只记录恢复方法和确认状态，不记录秘密值。不得把真实凭据、解密密钥或对象存储 secret 提交到 GitHub、日志、Discord 或未加密备份中。

---

## 3. 最小技术方向

### SQLite 一致性备份

默认优先评估 Python 标准库 SQLite Backup API：

```python
source_connection.backup(destination_connection)
```

理由：无第三方 Python 依赖、可以在主服务运行时获得一致副本、适合后续自动化。若仓库实际 journal mode、锁行为或权限证明该路线不安全，再退回受控短暂停服复制。禁止直接 `cp` 正在写入的数据库并宣称可靠。

### 主机外存储

优先评估：

```text
PRIMARY_OFF_HOST_STORAGE = CLOUDFLARE_R2_OR_EQUIVALENT_THIRD_PARTY_OBJECT_STORAGE
SECONDARY_COPY = LOCAL_MAC_OR_EXTERNAL_DISK
```

最终存储选择必须满足私有 bucket、最小权限、生命周期管理、稳定上传/下载和与 Lightsail 不同的故障边界。AWS S3 只有在明确接受同 AWS 账户风险边界后才可选择。

### 加密

使用成熟文件级加密工具，优先评估 `age` 或等价成熟方案。禁止自研加密。解密密钥不得只保存在生产服务器，不得与备份对象存放在同一位置，不得通过 shell history 或明文命令参数泄露。

### 自动化

最小脚本职责：

```text
consistent SQLite backup
→ integrity check
→ collect minimum configuration
→ manifest + SHA256SUMS
→ package
→ encrypt
→ upload
→ explicit PASS/FAIL
→ clear temporary plaintext
```

可采用 systemd timer 或最低成本 cron；优先与现有 systemd 运维模式一致。备份失败不得影响交易主运行时。

---

## 4. 建议备份包

```text
trader-assist-backup-<UTC_TIMESTAMP>/
├── runtime.db
├── public.env
├── risk-configuration.json
├── manifest.json
└── SHA256SUMS
```

最终加密对象示例：

```text
trader-assist-backup-<UTC_TIMESTAMP>.tar.gz.age
```

manifest 至少记录：

```text
backup_format_version
backup_created_at_utc
repository
deployed_sha
database_source_path
database_filename
database_size_bytes
database_sha256
database_integrity_check
public_env_sha256
risk_configuration_sha256
service_name
python_version
backup_method
encryption_method
storage_destination_class
restore_instructions_version
database_page_count
database_schema_version
database_user_version
service_active_before_backup
service_active_after_backup
ta_status_after_backup
```

manifest 禁止记录任何 secret、token、webhook URL、authorization header、私钥、对象存储密钥或解密密钥。

---

## 5. 必须验证的闭环

上传成功不等于备份成功。必须完成：

```text
CREATE_BACKUP
→ LOCAL_INTEGRITY_CHECK
→ ENCRYPT
→ UPLOAD
→ DOWNLOAD_AS_NEW_FILE
→ CHECKSUM_VERIFY
→ DECRYPT
→ OPEN_READ_ONLY
→ PRAGMA_INTEGRITY_CHECK
→ PASS
```

数据库门禁：

```sql
PRAGMA quick_check;
PRAGMA integrity_check;
```

预期均为 `ok`。还必须在临时目录完成最小离线恢复演练：解密、校验 SHA、只读打开数据库、核对关键表结构、核对配置文件和 manifest，不连接生产进程，不写生产数据库。

---

## 6. 保留策略与初始目标

建议初始策略：

```text
DAILY_BACKUP_RETENTION = 7
WEEKLY_BACKUP_RETENTION = 4
PRE_DEPLOYMENT_BACKUP = REQUIRED
POST_DEPLOYMENT_VERIFIED_BACKUP = REQUIRED
RPO <= 24_HOURS
RTO <= 2_HOURS
```

部署前后保留点不得被普通每日保留策略立即删除。

---

## 7. 与下一次部署的整合顺序

```text
1. 核验 exact release candidate 和恢复资产
2. 创建部署前 SQLite 一致性备份
3. 本地 integrity/checksum 验证
4. 加密并上传主机外存储
5. 完成正式生产部署
6. 完成生产 READY 与非交易验收
7. 创建部署后数据库和配置备份
8. 上传后重新下载新副本
9. checksum、解密、只读打开和 integrity_check
10. 完成离线恢复演练
11. 确认凭据存在独立主机外恢复来源
12. 确认 Mac 或外部磁盘第二副本
13. 确认恢复 runbook 可执行
14. 单独申请 Lightsail 快照删除授权
15. 删除快照后核对 SnapshotUsage 后续停止增长
```

该工作流横跨部署前和部署后。备份实现和部署前备份属于部署准备；快照删除只允许在部署后完整验证通过后进行。

---

## 8. Lightsail 快照删除强制门禁

只有以下全部通过，才允许：

```text
SQLITE_CONSISTENT_BACKUP=PASS
SQLITE_INTEGRITY_CHECK=PASS
CONFIGURATION_BACKUP=PASS
MANIFEST_CREATED=PASS
CHECKSUM_CREATED=PASS
BACKUP_ENCRYPTED=PASS
OFF_HOST_UPLOAD=PASS
OFF_HOST_DOWNLOAD=PASS
DOWNLOADED_CHECKSUM_VERIFY=PASS
DOWNLOADED_DECRYPT=PASS
DOWNLOADED_DATABASE_OPEN_READONLY=PASS
DOWNLOADED_INTEGRITY_CHECK=PASS
EXTERNAL_CREDENTIAL_RECOVERY_SOURCE=CONFIRMED
SECONDARY_LOCAL_COPY=PASS
RESTORE_RUNBOOK=PASS
```

否则：

```text
LIGHTSAIL_SNAPSHOT_DELETE=PROHIBITED
```

全部通过后：

```text
LIGHTSAIL_SNAPSHOT_DELETE=ELIGIBLE
```

实际删除仍需用户或 Project Control 单独授权。

---

## 9. 最小代码与文档范围预期

预计评估：

```text
1 个独立备份脚本
1 个聚焦测试文件
1 个对象存储配置模板或说明
1 个简短恢复 runbook
可选 1 个 systemd service/timer
```

尽量不修改主交易 runtime。禁止数据库 schema 重构、PostgreSQL、常驻备用服务器、HA、Kubernetes、Docker 平台、多云编排、Dashboard、自动故障切换或自动交易恢复。

---

## 10. 测试与发布门禁

至少覆盖：

- SQLite 一致性备份成功；
- 源数据库不被修改；
- integrity check；
- 损坏备份失败；
- manifest SHA 正确；
- 配置缺失 fail closed；
- secrets 不进入 manifest；
- 明文临时文件清理；
- 上传失败不删除上一份成功备份；
- 下载后 checksum 验证；
- 解密失败不得误报成功；
- 备份失败不影响主 runtime；
- retention 不误删部署前后保留点；
- 无网络时本地备份逻辑可测试。

最终门禁：

```text
OFF_HOST_BACKUP_DESIGN=PASS
SQLITE_BACKUP_IMPLEMENTATION=PASS
SQLITE_INTEGRITY_VALIDATION=PASS
CONFIGURATION_BACKUP=PASS
BACKUP_ENCRYPTION=PASS
OFF_HOST_UPLOAD=PASS
OFF_HOST_DOWNLOAD_VERIFY=PASS
RESTORE_TEST=PASS
EXTERNAL_CREDENTIAL_RECOVERY=CONFIRMED
SECONDARY_COPY=PASS
RESTORE_RUNBOOK=PASS
FULL_CI=PASS
PRODUCTION_POST_DEPLOY_BACKUP=PASS
```

---

## 11. 当前禁止事项

本文不授权：

- 立即删除 Lightsail 快照；
- 当前生产主机改动；
- 创建对象存储资源；
- 读取或迁移真实秘密；
- 运行备份、恢复或部署；
- 修改策略、Scanner、TradePlan 或数据库 schema；
- 创建实现 PR；
- merge、permit、重启或交易权限变更。

最终任务仍由 Project Control 在统一部署规划中派发。
