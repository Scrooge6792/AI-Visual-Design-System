# 模块与设计意图

本文说明当前源码模块为什么存在、负责什么，以及不应该承担什么。系统级边界与数据流见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 入口层

| 模块 | 职责与意图 | 边界 |
| --- | --- | --- |
| `avds` / `avds.cmd` | 用户可发现的精简入口，转发版本、服务、状态和配置命令 | 不开放业务写入、完整维护命令或任意扩展命令 |
| `src/avds/user_cli.py` | 实现用户快捷命令筛选与 `config show/get/set` | 不复制完整 CLI 的业务路由 |
| `bin/avds` | 项目内完整 Agent CLI 启动器 | 只作为客户端，不直接读写 SQLite |
| `src/avds/cli.py` | 完整生命周期与业务命令客户端，负责参数和 JSON 输入输出 | 正式业务写入必须发送给服务 |

精简入口与完整 Agent CLI 有意分层：普通用户只看到稳定的日常命令，Agent 和维护者仍可调用完整契约。

## 服务与界面层

| 模块 | 职责与意图 | 边界 |
| --- | --- | --- |
| `src/avds/server.py` | 唯一长期运行进程；HTTP 生命周期、服务发现、命令路由、会话和单 Vault 锁 | 不实现第二套业务规则 |
| `src/avds/web.py` | WebUI 静态资源、同源检查、上传和稳定 ID 媒体读取 | 不接受任意本机路径，不绕过 Store |
| `src/avds/web_assets/` | 浏览器中的完整导入、提案、审核、检索和预览界面 | 不保存权威业务状态，不单独启动前端服务器 |
| `src/avds/commands.py` | 公开命令目录与帮助文本 | 不成为独立执行层 |

Agent 和 WebUI 必须调用相同业务命令，以避免出现两套审批、状态或搜索语义。

## 业务与数据层

| 模块 | 职责与意图 | 边界 |
| --- | --- | --- |
| `src/avds/store.py` | 数据模型、状态转换、提案审核、正式提交、搜索、幂等和恢复 | 不把文件操作与 SQLite 描述为一个原子事务 |
| `src/avds/schema.sql` | SQLite 权威结构、索引和约束 | 不保存用户环境配置 |
| `src/avds/schemas/` | 资产、概念、知识和 Prompt 提案的 JSON Schema | Schema 通过不等于提案已审核或提交 |
| `src/avds/jsonschema.py` | 当前所需的确定性 Schema 校验 | 不执行模板代码或任意表达式 |
| `src/avds/util.py` | 哈希、安全相对路径、规范化 JSON 等无状态工具 | 不承载业务状态机 |
| `src/avds/errors.py` | 稳定错误结构和代码 | 不隐藏底层失败原因 |

`Store` 是唯一正式写入入口。Asset、Proposal、Operation 和 Queue 保持独立状态；未审核内容不能进入正式搜索。

## 配置与平台层

| 模块 | 职责与意图 | 边界 |
| --- | --- | --- |
| `src/avds/config.py` | 配置优先级、默认路径、Vault 解析和跨平台文件锁 | 配置不是权限隔离机制 |
| `src/avds/platform.py` | macOS/Windows 图像解码、持久化差异与视觉能力适配 | Core 不直接依赖 `sips`、PowerShell、Swift 或 Unix 专用 API |
| `vision/main.swift` | macOS Apple Vision Feature Print helper | 按需短暂运行，不成为第二个常驻服务，不产生正式标签 |

平台差异集中在适配模块。Windows 不使用 Apple Vision，也不自动回退到云端或付费服务。

## 安装、测试与文档

| 目录 | 意图 |
| --- | --- |
| `scripts/` | 项目内安装和可选 Vision 构建，不注册系统服务 |
| `tests/` | 只覆盖正确性、安全与恢复所需的 Store、服务和 CLI 回归 |
| `docs/` | 当前有效的需求、架构、契约、决策、开发和状态资料 |
| `docs/history/` | 只读历史依据，不参与当前实现决策 |

新增模块前，应先判断职责能否归入现有层；只有出现独立且稳定的责任边界时才创建新模块，避免按单个功能碎片化文件。
