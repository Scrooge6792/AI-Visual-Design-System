# 项目进度

更新：2026-11-08。

## 结论

**2.0.0 初版源码开发完成。** macOS 单服务闭环、安装、生命周期和实际 Apple Vision 已验证；但 Windows 10/11 实机与真实浏览器产品体验尚未完成，因此不能称为“跨平台公开发布已全部验收”。

## 已完成

- Python 单一长期 HTTP 服务，一次启动；CLI 为短连接客户端，WebUI 由同一服务提供。
- Agent/WebUI 完整导入、分析记录、提案/修订、审核、拒绝/退回、两种稍后、检索、知识和 Prompt。
- 配置优先级、可配置端口/Vault、服务发现、同 Vault 操作系统锁、随机会话、Host/Origin/CSP。
- SQLite DELETE/FULL/外键/busy timeout、显式事务、幂等、恢复、正式/待审索引隔离。
- 资产/知识/Prompt/概念修订目标锁定；上传响应丢失后的相同 operation_id 重放。
- macOS 系统图像解码与可选自动 Apple Vision；Windows PNG/JPEG 原生适配及无 Vision 能力说明。
- macOS `install.sh`、Windows `install.ps1`、应用版本 2.0.0、契约版本 1.0。
- macOS 项目根目录提供 `./avds` 命令入口，不再要求记忆 `.venv/bin/avds` 路径。
- 安装说明要求 Agent 先询问是否配置全局 `avds`；获批后仅按系统配置用户级命令目录/PATH，并验证命令，不默认修改系统级 PATH。
- `avds -h` / `avds --help` 提供完整命令、公共参数和逐项一句话用途说明，服务端与 CLI 共用命令目录以防漂移。

## 必要检查

- 22 项 Python 测试通过：CLI 帮助、HTTP 单服务、双入口审核、上传重放、提案绑定、事务失败回滚、索引隔离、配置、Windows 适配模拟和真实 Apple Vision。
- init → doctor → serve → status → stop 临时 Vault 生命周期通过。
- 项目内 `.venv` editable 安装与 Vision helper 构建通过。
- Python、JavaScript、shell 语法和 `git diff --check` 通过。

## 本轮目录清理

- 当前规范只保留 2.0.0 有效内容；V0.8/V1 材料集中到 `docs/history/v1/`。
- 删除不再参与运行或构建的 Reviewer App 源码、Phase 0 探针、launchd 生成器、旧 Core/Reviewer/Web 启动包装器和 start/stop 脚本。
- 清理可重建的旧 Reviewer/Phase 0 构建产物、旧页面快照、Python 缓存和 egg-info；保留并重建当前 Apple Vision helper。

## 限制与下一步

- Windows 10/11 尚未实机验证；只能称为目标支持，不能称为已通过。
- WebUI 真实浏览器点击和视觉体验由用户验收；HTTP 行为测试不等同产品体验。
- 旧受信安装、Reviewer App 和真实 Vault 未更新、停止或迁移。
- 公开 GitHub 仓库尚未创建；许可证也尚未选择。

下一步优先级：Windows 实机安装/导入闭环 → 用户浏览器体验 → 用户授权后评估旧 Vault 迁移 → 准备 GitHub 发布。
