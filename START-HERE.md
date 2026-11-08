# Codex Desktop 启动指令

解压 ZIP，将本包根目录作为本地项目打开，确保主目录包含 AGENTS.md。真实 Vault 放在源码项目之外，具体受控访问在 Phase 0 验证。本文件保存指令不表示开始实施；用户实际发送实施请求后才执行。

## 启动 V1 实施（可直接粘贴）

> 请依据 V0.8 交接包实施 AI Visual Design System V1。先读 AGENTS.md、README.md、docs/SOURCE-COVERAGE.md、docs/REQUIREMENTS.md、ARCHITECTURE.md、DECISIONS.md、IMPLEMENTATION.md、docs/CONTRACTS.md 和 docs/PROGRESS.md。用户补充材料已恢复早期决策，不要再索要逐字聊天记录。先执行 Phase 0，仅用一次性测试资料验证现有账户额度内图片分析与提案、真实 Reviewer/Core 权限隔离、实际运行时 SQLite/FTS5、最小中断恢复和目录迁移；通过后依次推进 Phase 1 Core、Phase 2 Reviewer 与 Agent、Phase 3 搜索闭环。常规语言实现、SQLite 表/索引、合规小型免费依赖和内部优化自主决定；重要第三方/核心框架、供应商绑定、路线替换及成本/商业许可/数据所有权/隐私/安全/权限变化须先调查汇报并取得用户确认。已定选择不重复询问。若验证失败、成本变化或无法维持审批边界，停止受影响工作并具体报告，不降低要求。Agent-First、本地 CLI 优先、MCP 后置；JSON Schema 校验 VARP 提案，审批绑定五项，Asset/Proposal/Operation/待审队列状态分开。保留十二分面受控词表、批量/部分审核、稍后和本批次后续全部稍后。按操作区分创建/更新/归档，物理删除后置；新概念先提交，再刷新并审核资产。稳定 ID 的只读接口须支持跨会话继续分析暂缓原图，不重新上传。Phase 1 只做最小数据与接口，不做复杂词典治理/映射/合并或高级关系推理。采用 SQLite DELETE/FULL、原图不可变、持久暂缓、幂等与恢复、可复制 Vault；Finder 备份，不开发复杂备份。不得新增付费 API、云服务器或核心商业依赖，依赖遵守成熟度门槛。未来 WebUI、完整知识库、Prompt 配方引擎和向量检索不进 V1。只做必要测试，不安排冗余 AI 验收，体验由我验收。每阶段简短更新进度、决策与阻塞。完成 V1 后交付运行/关闭说明、用法与已知限制。

## 仅验证 Phase 0（可选的有限授权）

> 请读取全部 V0.8 文档，这次只授权 Phase 0 技术验证，不进入 Phase 1。仅用一次性测试资料验证现有账户内视觉分析与结构化提案、实际 SQLite/FTS5、Reviewer 真实权限隔离、最小恢复和迁移。不要接入真实重要素材。订阅不代表任意 API 免费，独立进程不等于隔离。遵守零新增费用、成熟依赖规则；常规细节自主决定，重要第三方/核心框架、供应商绑定或路线/费用/许可/数据/安全权限变化先调查汇报并取得用户确认。完成必要验证后更新 DECISIONS 和 docs/PROGRESS，简要交付证据、阻塞与下一步，不安排额外 AI 复核。

## 继续当前阶段

> 请读取 AGENTS.md、DECISIONS.md 与 docs/PROGRESS.md，继续已授权未完成的阶段，依据文档恢复上下文，不重复询问已有决定，不扩大 V1。新 Bug 或权限问题定向检查，必要时提出具体问题，更新进度与决策。

## 仅修改文档

> 这次只更新 V0.8 交接文档，不开发应用、不安装依赖、不启动服务。以 SOURCE-SUPPLEMENT 与后续明确修订为设计依据，同步需求、架构、决策、计划与契约，避免状态混用和审批绑定缺项。核对后重新打包。

## 官方说明来源

- [Projects and chats](https://learn.chatgpt.com/docs/projects)：本地项目连接文件夹，主目录影响项目说明的发现。
- [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)：使用 AGENTS.md 保存持久项目指令。

AGENTS.md 不能替代宿主或操作系统权限控制。上述来源只支撑项目组织方式，不保证账户集成、额度或隔离已成立。
