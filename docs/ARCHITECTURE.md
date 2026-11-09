# 系统架构与实施约束

> 本文解释系统边界、运行组件与关键数据流；源码目录及各模块的设计意图见 [MODULES.md](MODULES.md)。架构图的可编辑源文件为 [diagrams/architecture.excalidraw](diagrams/architecture.excalidraw)。

当前版本：**1.0.0**。本文件只描述当前有效架构；旧版 Reviewer、Touch ID、Unix Socket 与分阶段方案已归档到 `docs/history/v1/`，不再约束当前实现。

## 总体架构

```text
桌面 Agent → avds CLI ─┐
                       ├→ 一个 Python 本机 HTTP 服务 → Store → SQLite + Vault
浏览器 WebUI ──────────┘       导入、提案、审核、检索、知识、Prompt
                                      │
                                      └→ macOS 可选 Apple Vision helper
```

- `avds serve` 是唯一长期运行服务，同时提供 JSON API、WebUI、媒体读取和业务提交。
- CLI 是短连接客户端；WebUI 不单独启动前端服务器。
- 单一 `Store` 串行处理 SQLite 写入，同一 Vault 由操作系统锁限制为一个服务实例。
- 服务只监听 `127.0.0.1` 或 `localhost`，不提供账号、远程访问、云部署或多用户协作。
- Agent 与 WebUI 使用同一业务接口，没有数据库旁路。

## 运行组件

| 组件 | 职责 |
| --- | --- |
| `src/avds/server.py` | 本机 HTTP 生命周期、命令路由、会话、单 Vault 锁 |
| `src/avds/web.py` | WebUI、同源检查、文件上传、稳定 ID 媒体读取 |
| 根目录 `avds` / `src/avds/user_cli.py` | 面向用户的精简快捷入口：版本、启动、状态与用户配置 |
| `bin/avds` / `src/avds/cli.py` | 项目内完整 Agent 客户端：init/doctor/open/stop 与全部业务命令 |
| `src/avds/store.py` | 数据模型、状态转换、事务、索引、幂等与恢复 |
| `src/avds/platform.py` | macOS/Windows 图像解码、持久化差异和 Vision 能力 |
| `vision/main.swift` | macOS Apple Vision Feature Print 可选 helper |

Apple Vision helper 只在需要时由 Python 服务启动短暂子进程，不是第二个常驻服务，也不需要用户手动启动。

## 配置与服务发现

配置优先级为：命令行 > 环境变量 > JSON 配置 > 默认值。可配置 Vault、host、port、是否打开浏览器和视觉提供者。

`data/service.json` 保存当前 URL、随机令牌、PID 和 Vault 路径，仅用于服务发现，可在重启时替换。`data/service.lock` 由 POSIX `flock` 或 Windows `msvcrt` 持有，崩溃后由系统释放，不依赖可伪造的 PID 文件判断互斥。

## Vault

```text
VisualAssetVault/
├── data/                  # SQLite、服务状态和锁
├── staging/               # 持久待审原图；deferred 不是缓存
├── objects/sha256/        # 内容寻址正式原图
├── knowledge/             # 已批准版本化 Markdown
├── prompts/               # 已批准版本化 JSON
└── cache/                 # 可重建索引、预览和 Feature Print
```

所有权威引用使用稳定 ID 或 Vault 内相对路径。源码、用户配置和真实 Vault 相互分离。缓存可以重建，不能成为唯一权威数据；拒绝、失败、归档或缓存清理不得删除原图。

## 逻辑数据模型

| 实体 | 作用 |
| --- | --- |
| files / assets / asset_sources | 原图指纹、稳定资产身份、来源与许可信息 |
| analysis_runs | Agent 分析正文、模型、Prompt 版本与执行位置；始终是草案证据 |
| concepts / concept_terms / concept_relations | 小规模受控词表、别名与明确层级/相关关系 |
| asset_concepts | 资产与概念多对多关系及观察/解释/用途性质 |
| change_proposals | 资产、概念、知识、Prompt 的版本化变更草案 |
| review_events | 明确确认动作及被确认的具体提案绑定 |
| operations | 幂等键、请求摘要、提交状态与稳定结果 |
| import_batches / review_queue_items | 批次、待审、稍后与恢复进度 |
| search_documents / FTS | 只从已批准内容重建的搜索派生数据 |
| visual_features | macOS 可重建 Feature Print 元数据，不是正式事实 |

## 独立状态

| 对象 | 状态 |
| --- | --- |
| Asset | staged / active / archived |
| Proposal | draft / in_review / approved / rejected / superseded |
| Operation | pending / committing / committed / failed |
| Queue | pending / in_review / deferred / resolved |

状态不能合并成单一字段。提案获批不等于正式提交完成；只有 Operation committed 且文件可用后，新资产或新修订才进入正式搜索。

## 提案与审核

Agent 与 WebUI 均可起草、展示和审核。审核必须绑定 `proposal_id + revision + proposal_hash + target_revision`，资产提案还绑定 `file_hash`。修改内容必须产生新 revision，旧确认不能复用。

`confirmed=true` 只是“调用入口已完成显式确认”的工作流字段，不是密码或身份凭据。系统不声称能阻止同一操作系统用户下的 Agent 自行调用审核接口；其目标是防止版本错配、静默变更和误提交。

新概念必须先独立提交并获得正式 `concept_id`，资产再替换候选引用、生成新提案并重新审核。当前不支持复合原子批准、concept.update/merge、物理删除或反归档。

## HTTP 与浏览器边界

- 每次服务启动生成随机令牌；CLI 使用 bearer，浏览器在 `avds serve --open` 时建立会话，Agent 也可从项目目录通过 `./bin/avds open` 重新打开。
- Host 和浏览器 Origin 必须匹配实际本机端口；应用 CSP、无跨域许可且不记录令牌。
- `/api/import` 接收文件后仍调用同一 `import.stage` 校验；上传临时文件不成为权威数据。
- `/media` 只接受稳定 asset/queue ID，服务解析相对路径并复验文件哈希，不接受任意文件路径。

这些措施防止普通外站误调用本机服务，不构成 Agent 与用户之间的身份隔离。

## 文件与数据库提交

SQLite 使用 `journal_mode=DELETE`、`synchronous=FULL`、`foreign_keys=ON`、`busy_timeout=5000`。正式变更使用显式 `BEGIN IMMEDIATE`，同时检查目标 revision。

文件系统和 SQLite 不是同一原子事务：

1. 校验提案绑定与幂等键。
2. 记录操作状态。
3. 安全写入并校验文件；不覆盖原图。
4. SQLite 单事务发布正式记录、审核关联和搜索文档。
5. 保存稳定结果；响应丢失时按 operation_id 返回原结果。

文件未就绪、摘要变化、目标 revision 冲突或哈希异常时不发布正式内容。Windows 能进行文件 fsync 和同卷 replace，但 Python 标准接口不能提供 POSIX 目录 fsync 的完全等价保证。

## 平台能力

| 能力 | macOS | Windows 10/11 |
| --- | --- | --- |
| Python/SQLite/FTS5 | 支持，启动时 doctor 检查 | 目标支持，尚待实机验证 |
| 图像解码 | 系统 sips：PNG/JPEG/HEIC/WebP（以实际系统为准） | Windows PowerShell/System.Drawing：PNG/JPEG |
| 视觉相似 | Apple Vision helper 可用时自动启用 | 不提供，返回 CAPABILITY_UNAVAILABLE |
| 服务方式 | 前台 `avds serve` | 前台 `avds serve` |

视觉距离只用于排序，不能自动写入标签、关系或知识。Feature Print 绑定引擎与系统信息，变化后重建。

## 当前边界

不提供云端、账号、同步、用户间数据交换、任意 SQL、模板代码执行、物理删除、反归档、概念合并或复杂词典治理。公开仓库只包含源码和说明，不包含用户配置、Vault 或素材。
