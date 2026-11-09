# 项目文档

根目录 [README.md](../README.md) 是面向使用者的项目入口；本目录保存当前有效的产品、架构和维护资料。

| 文档 | 职责 |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统边界、运行组件、数据流与可靠性设计 |
| [MODULES.md](MODULES.md) | 源码模块、职责、设计意图和依赖方向 |
| [REQUIREMENTS.md](REQUIREMENTS.md) | 当前版本必须满足的产品与工程需求 |
| [CONTRACTS.md](CONTRACTS.md) | CLI、HTTP、命令、状态与错误契约 |
| [DECISIONS.md](DECISIONS.md) | 仍然有效且影响后续实现的技术与产品决定 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发环境、必要回归、发布验收与维护规则 |
| [PROGRESS.md](PROGRESS.md) | 已完成事项、检查证据、限制和下一步状态 |
| [SOURCE-COVERAGE.md](SOURCE-COVERAGE.md) | 权威来源优先级、历史覆盖关系与事实边界 |

`diagrams/` 保存可编辑的 Excalidraw 源图，`assets/` 保存 README 和文档引用的导出图。修改架构图时必须同步更新两者。

`history/` 仅用于追溯旧版本，不是当前实现依据。待办事项统一记录在根目录 [TODO.md](../TODO.md)，不在进度、实施和 README 中维护第二份待办列表。
