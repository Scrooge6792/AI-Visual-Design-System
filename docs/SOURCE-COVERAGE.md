# 来源与有效性

## 当前权威来源

| 优先级 | 来源 | 作用 |
| --- | --- | --- |
| 1 | 用户当前明确要求 | 最高优先，覆盖所有旧决定 |
| 2 | AGENTS.md | 项目执行边界与不可自行改变的约束 |
| 3 | README、REQUIREMENTS、ARCHITECTURE、DECISIONS、IMPLEMENTATION、CONTRACTS、PROGRESS | 1.0.0 当前产品、实现和状态 |
| 4 | `src/`、`tests/`、`pyproject.toml`、`scripts/` | 实际行为与可验证证据 |
| 5 | `docs/history/v1/` | 仅用于追溯，不是当前规格 |

如果当前文档与源码不一致，应核实行为、修正文档并记录进度；不能用历史资料恢复已取消的 Touch ID、独立 Reviewer、Unix Socket、launchd 或 WebUI 只读限制。

## 1.0.0 决策来源

2026-11-08 用户明确确认：

- Python 单一长期运行本机 HTTP 服务，一次启动。
- Agent 与 WebUI 都是完整入口，导入和审核均可在 Agent 中完成。
- 取消 Touch ID 与独立 Reviewer 身份门禁。
- 端口、Vault 和视觉能力可配置，默认命令行前台运行。
- macOS 使用可用的 Apple Vision；Windows 不使用。
- 源码计划公开到 GitHub，其他用户由自己的 Agent 按说明安装；不做数据交流、账号或同步。

这些决定形成开始正式使用的应用 1.0.0，覆盖历史 V1 中相反的部署与审批结构，但保留原图保护、SQLite/Vault、提案版本、审核绑定、正式/待审隔离、幂等、恢复、十二分面和零新增费用等数据与产品要求。

## 历史资料目录

`docs/history/v1/` 保存：

- V0.8/V1 的需求、架构、决策、实施计划和契约。
- 旧 Phase 0 Touch ID/Reviewer/Unix Socket 验证记录。
- 原会话可读取摘录、用户补充决策材料和旧交付核对。

历史文件保持原文性质，可能包含已经失效的“仅文档”“尚未实施”“独立 Reviewer”“Touch ID”“只读 WebUI”等描述。后续 Agent 除非追溯来源，不需要读取它们；不得把其中状态当成当前事实。

## 当前事实边界

- 1.0.0 源码已实现并在 macOS 临时 Vault 通过 25 项测试、安装和生命周期冒烟。
- Windows 只有适配模拟和静态检查，没有实机通过证据。
- HTTP/WebUI 行为已有自动化测试，但真实浏览器点击体验尚待用户验收。
- 旧受信安装、Reviewer App 和真实 Vault 未被 1.0.0 更新或迁移。
- 尚未创建或发布公开 GitHub 仓库。
