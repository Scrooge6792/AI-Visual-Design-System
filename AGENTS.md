# Codex 项目执行规则

## 沟通与阅读

- 使用中文沟通。
- 开始任务先读根目录 `README.md` 和 `docs/SOURCE-COVERAGE.md`。安装任务再完整阅读 `INSTALL.md`；修改产品行为前阅读相关需求、架构、决策、契约与进度文档。
- `docs/history/` 仅用于追溯，不是当前实现依据。用户当前明确要求优先于旧决定；不得从历史资料恢复已取消的 Touch ID、独立 Reviewer、Unix Socket、launchd 或只读 WebUI。

## 文件职责与结构

- `README.md` 是面向人的项目首页，只放项目介绍、简明架构、包含内容、使用方式、有序安装流程、可复制的安装 Prompt 和文档入口。
- `INSTALL.md` 是 Agent 安装操作手册，保存平台步骤、前置检查、验证、全局命令确认和安全边界；README 不复制完整安装细节。
- `AGENTS.md` 只保存执行规范、不可变约束、权限边界和文档职责，不放项目介绍、完整架构或操作教程。
- `TODO.md` 只保存尚未完成且可执行的事项；完成事实与证据写入 `docs/PROGRESS.md`，长期要求写入 `docs/REQUIREMENTS.md`。
- `docs/README.md` 是项目文档索引；模块意图写入 `docs/MODULES.md`，系统边界写入 `docs/ARCHITECTURE.md`，接口写入 `docs/CONTRACTS.md`，决定写入 `docs/DECISIONS.md`，开发维护写入 `docs/DEVELOPMENT.md`。
- 新的当前项目文档放入 `docs/`；根目录只保留用户入口、安装、Agent 约束和待办等仓库级文件。避免在多份文档维护同一正文，改动时更新对应权威文档及必要链接。
- 架构图必须用 Excalidraw 维护：可编辑源文件为 `docs/diagrams/architecture.excalidraw`，README 使用导出的 `docs/assets/architecture.svg`；架构变化时两者同步更新并检查渲染。

## 数据与安装安全

- 当前开发只修改源码和临时测试数据。不要写入旧受信安装或真实 Vault；安装、更新、停止旧实例或迁移数据仍需用户单独授权。
- 用户级配置、真实 Vault、素材、运行状态、令牌和本机私有文件不得进入版本库。默认把用户配置和 Vault 放在项目目录之外；项目内临时配置使用 `.avds/` 或 `*.avds.local.json` 等 `.gitignore` 已覆盖位置。
- 新增用户级自定义文件或新的本机运行产物时，同一轮更新 `.gitignore`；不要忽略应提交的示例、Schema、安装脚本或默认配置模板。
- 安装完成后必须询问用户是否配置全局 `avds`。只有明确批准后，才检查同名命令并配置用户级命令目录/PATH；不静默覆盖、不默认修改系统级 PATH、不要求管理员权限，并在新 shell 验证 `avds --version`。
- 根目录/全局 `avds` 必须保持相同，只暴露版本、`serve`、`status` 和 `config show/get/set`。完整生命周期和业务命令由项目内 `./bin/avds` 或 Python entry point 提供。

## 不可变产品约束

- 采用 Python 单一长期运行本机 HTTP 服务；Agent 与 WebUI 都是完整入口。服务只监听 `127.0.0.1` 或 `localhost`，一个 Vault 同时只允许一个服务，默认不注册系统服务。
- 业务统一通过服务写入；Agent/WebUI 不执行任意 SQL。审核保留 `proposal_id`、`revision`、`proposal_hash`、`file_hash`、`target_revision` 绑定，修改后必须生成新修订并重新审核。`confirmed=true` 是流程确认，不是身份凭据。
- 未审核事实不进入正式搜索。Asset、Proposal、Operation、Queue 状态分开；保留 JSON Schema、参数化查询、幂等、中断恢复、事务、原图哈希与不可变约束。不得把文件操作与 SQLite 描述为一个原子事务。
- “稍后”持久保留当前素材；“后续全部稍后”只影响当前批次未处理项，不等于批准。拒绝、失败、归档、稍后或缓存清理都不删除原图。
- 知识与 Prompt 保留版本化提案、审核、提交和检索；模板不执行代码。不提供物理删除、反归档、`concept.update/merge`、复合原子批准或复杂词典治理。
- macOS 自动使用已构建的 Apple Vision helper，缺失时明确报告不可用；Windows 不使用 Apple Vision。平台工具留在适配模块，Core 不硬依赖平台专用命令。

## 依赖、决策与验证

- 零新增付费依赖、API、云服务、服务器或硬件。账号额度不可用时保留稍后，不回退付费 API。
- 第三方生产依赖使用正式稳定版、持续维护且许可和免费条件清晰的项目。重要框架、数据库/存储/审批/检索路线、供应商绑定、费用、许可、隐私/权限变化或降低产品要求，先调查影响并取得用户确认。
- 用户自行进行产品体验验收；只做影响正确性、安全和恢复的必要测试，不组织额外 AI Reviewer 或大规模视觉评测。
- 没有 Windows 实机或真实浏览器证据时，只记录模拟、静态或 HTTP 检查，不能声称对应实机/体验通过。
- 每次迭代更新相关权威文档，并在 `docs/PROGRESS.md` 简短记录完成项、必要检查、限制和新增决定；未完成行动统一更新 `TODO.md`，PROGRESS 只链接过去，不复制待办清单。
