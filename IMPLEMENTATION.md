# 1.0.0 实施与维护计划

## 当前状态

1.0.0 是开始正式使用的首个应用版本，初版源码开发完成。macOS 单服务闭环、安装、生命周期和 Apple Vision 已验证；Windows 实机与真实浏览器产品体验仍是发布验收项。旧受信安装和真实 Vault 未更新。

## 已完成

1. Python HTTP 合并业务 API、WebUI、媒体读取和正式写入。
2. CLI 实现 init、doctor、serve、status、open、stop 及全部业务命令。
3. Agent/WebUI 双入口导入、提案、修订、审核、稍后、检索、知识与 Prompt。
4. 配置优先级、随机会话、Host/Origin/CSP、端口发现和 Vault 操作系统锁。
5. 资产/概念/知识/Prompt Schema、版本绑定、目标锁定、事务回滚、幂等和恢复。
6. macOS 系统解码与 Apple Vision；Windows PowerShell/System.Drawing PNG/JPEG 适配。
7. macOS shell 与 Windows PowerShell 项目内虚拟环境安装脚本。

## 当前代码布局

```text
avds / avds.cmd         根目录/全局共用的精简用户快捷入口
bin/avds                项目内完整 Agent 命令入口
src/avds/user_cli.py    用户快捷命令筛选与 config show/get/set
src/avds/               Python 服务、完整 CLI、Store、配置和平台适配
src/avds/web_assets/    单服务托管的 WebUI
src/avds/schemas/       当前提案 JSON Schema
vision/                 macOS 可选 Apple Vision helper
scripts/                安装与 Vision 构建
tests/                  Store 与单服务必要回归
docs/                   当前规范、进度与来源索引
docs/history/v1/        非现行历史资料
```

## 必要回归

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
node --check src/avds/web_assets/app.js
sh -n avds scripts/build.sh scripts/install.sh bin/avds
git diff --check
```

自动化测试应覆盖：

- 配置优先级、端口和同 Vault 重复服务拒绝。
- 导入、浏览器上传、相同 operation_id 重放和原图哈希。
- Agent/WebUI 共用审核、confirmed 要求、提案版本/目标绑定。
- 提交失败回滚、正式/草案索引隔离、旧批准失效。
- 稍后持久化、候选概念依赖、知识/Prompt 渲染。
- Windows 平台适配不得调用 Apple 工具；macOS 可用时运行真实 Vision 比较。

## 发布前剩余验收

### Windows 实机

在 Windows 10 和 Windows 11 至少各完成一次：

1. `scripts/install.ps1` 建立虚拟环境。
2. 项目内完整 CLI 的 `init` 与 `doctor`，确认 SQLite/FTS5。
3. PNG/JPEG 导入、提案、审核、正式搜索。
4. serve/status/open/stop 生命周期和端口覆盖。
5. 确认 visual.* 返回明确 CAPABILITY_UNAVAILABLE。

完成前不得在 README 或发布说明中写“Windows 已验证”。

### 浏览器产品体验

由用户在真实浏览器检查导入、待审、提案编辑、批准/退回/拒绝、素材灯箱、知识/Prompt 和 Vision 不可用提示。只有发现 Bug 或用户要求时补专项自动化，不组织大规模 AI 视觉评测。

### 旧版本迁移

仅在用户明确授权后：停止旧 Core/Reviewer、备份完整真实 Vault、用 1.0.0 指向副本做兼容检查，再决定正式迁移。不得直接覆盖旧安装或真实数据。

## 后续维护规则

- 每次改变行为、范围或平台支持时同步 README、AGENTS、REQUIREMENTS、ARCHITECTURE、DECISIONS、CONTRACTS 和 PROGRESS。
- 每阶段只记录完成项、必要检查、限制、下一步和新增决定。
- 不把 macOS 测试、平台模拟或 HTTP 测试写成 Windows/浏览器实机通过。
- 历史资料仅用于追溯，不从中恢复已被 1.0.0 覆盖的 Reviewer、Touch ID、Unix Socket 或只读 WebUI。
