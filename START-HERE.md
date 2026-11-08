# 后续 Agent 启动入口

先阅读 AGENTS.md、README.md、docs/SOURCE-COVERAGE.md，再读 docs/REQUIREMENTS.md、ARCHITECTURE.md、DECISIONS.md、IMPLEMENTATION.md、docs/CONTRACTS.md 和 docs/PROGRESS.md。

当前源码版本为 2.0.0、接口契约版本为 1.0。系统采用 Python 单一本机 HTTP 服务，CLI 和网页共用完整导入、提案、审核提交与搜索能力。2026-11-08 用户已批准移除 Touch ID、独立 Reviewer 门禁和 Unix Socket 架构。保留版本/hash绑定、明确确认、正式/待审隔离与原图保护，不声称身份隔离。

开发只用源码目录和临时 Vault，不更新旧版受信程序或真实 Vault。按用户后续明确要求修复；当前安装启动见 README。Windows 实机验证尚未完成，不自行发布 GitHub 仓库或迁移用户数据。
