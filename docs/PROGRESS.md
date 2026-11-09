# 项目进度

更新：2026-11-09。

## 结论

**1.0.0 初版源码开发完成并开始正式使用。** macOS 单服务闭环、安装、生命周期和实际 Apple Vision 已验证；但 Windows 10/11 实机与真实浏览器产品体验尚未完成，因此不能称为“跨平台公开发布已全部验收”。

## 已完成

- Python 单一长期 HTTP 服务，一次启动；CLI 为短连接客户端，WebUI 由同一服务提供。
- Agent/WebUI 完整导入、分析记录、提案/修订、审核、拒绝/退回、两种稍后、检索、知识和 Prompt。
- 配置优先级、可配置端口/Vault、服务发现、同 Vault 操作系统锁、随机会话、Host/Origin/CSP。
- SQLite DELETE/FULL/外键/busy timeout、显式事务、幂等、恢复、正式/待审索引隔离。
- 资产/知识/Prompt/概念修订目标锁定；上传响应丢失后的相同 operation_id 重放。
- macOS 系统图像解码与可选自动 Apple Vision；Windows PNG/JPEG 原生适配及无 Vision 能力说明。
- macOS `install.sh`、Windows `install.ps1`、应用版本 1.0.0、契约版本 1.0。
- macOS 项目根目录提供 `./avds` 命令入口，不再要求记忆 `.venv/bin/avds` 路径。
- 安装说明要求 Agent 先询问是否配置全局 `avds`；获批后仅按系统配置用户级命令目录/PATH，并验证命令，不默认修改系统级 PATH。
- 根目录 `./avds` 与全局 `avds` 已统一为精简用户快捷层，帮助只显示版本、serve、status 和 config show/get/set；完整业务命令保留在 `./bin/avds`。
- 顶层帮助明确提示 `avds <command> -h`，配置帮助继续提示 `avds config <action> -h`；首次试用改为 config set → serve，不再要求 init。

## 必要检查

- 25 项 Python 测试通过：快捷/完整 CLI 分层、用户配置、HTTP 单服务、双入口审核、上传重放、提案绑定、事务失败回滚、索引隔离、Windows 适配模拟和真实 Apple Vision。
- init → doctor → serve → status → stop 临时 Vault 生命周期通过。
- 项目内 `.venv` editable 安装与 Vision helper 构建通过。
- Python、JavaScript、shell 语法和 `git diff --check` 通过。

## 本轮目录清理

- 当前规范只保留 1.0.0 有效内容；V0.8/旧 V1 材料集中到 `docs/history/v1/`。
- 删除不再参与运行或构建的 Reviewer App 源码、Phase 0 探针、launchd 生成器、旧 Core/Reviewer/Web 启动包装器和 start/stop 脚本。
- 清理可重建的旧 Reviewer/Phase 0 构建产物、旧页面快照、Python 缓存和 egg-info；保留并重建当前 Apple Vision helper。

## 当前限制

- Windows 10/11 尚未实机验证；只能称为目标支持，不能称为已通过。
- WebUI 真实浏览器点击和视觉体验由用户验收；HTTP 行为测试不等同产品体验。
- 旧受信安装、Reviewer App 和真实 Vault 未更新、停止或迁移。
- 公开 GitHub 仓库已创建：<https://github.com/Scrooge6792/AI-Visual-Design-System>；许可证尚未选择。

后续行动及优先级统一见根目录 [`TODO.md`](../TODO.md)。

## 2026-11-09 · GitHub 源码分发

- 用户明确要求将当前项目推送到 GitHub，并完成账号授权。
- 创建公开仓库 `Scrooge6792/AI-Visual-Design-System`，关联 `origin`，以 `main` 分支分发源码与提交历史。
- 必要检查：工作区原先干净；核对跟踪文件和历史对象，未包含 Vault、素材或运行配置，常见密钥格式检查未发现匹配；文档变更使用 `git diff --check` 检查。
- 本轮只涉及仓库分发与说明，不改变运行行为，不重复运行产品测试；Windows 实机和浏览器人工验收仍未完成。
- 未选择法律许可，未更新安装、迁移真实数据或创建版本发布包。下一步仍为现有产品验收。

## 2026-11-09 · 文档职责整理

- 根目录 README 调整为面向使用者的项目入口，保留有序安装流程和可直接复制给 Agent 的安装 Prompt。
- 新增根目录 `INSTALL.md` 和 `TODO.md`，分别作为 Agent 安装操作手册和唯一未完成事项清单；删除重复的 `START-HERE.md`。
- 当前架构、决策和开发文档统一移入 `docs/`，新增文档索引及模块设计意图说明。
- 使用 Excalidraw 绘制架构图，同时保存可编辑源文件与 README 引用的 SVG 导出图。
- 精简并重组 `AGENTS.md`，加入文件职责、架构图维护和用户级文件忽略规则；`.gitignore` 补充用户配置及常见本机 Vault 目录。
- 本轮只调整文档与图，不改变运行行为；检查范围为链接、Markdown、Excalidraw 导出和 `git diff --check`，不重复运行产品测试。
