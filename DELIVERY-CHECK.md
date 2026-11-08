# 审查修订摘要与交付核对

本文件是 V0.8 文档交付历史。当前源码版本为 2.0.0；2026-11-08 跨平台单服务实现、授权覆盖关系和检查见 README.md、DECISIONS.md 与 docs/PROGRESS.md。下文旧 Reviewer/Touch ID 或“未实施”状态不代表当前版本。

本轮基于现有 V0.8 文档定向修订，未从零规划，未增加规范文件。归档文件名为 AI-Visual-Design-System-V0.8-reviewed.zip。

## 修复内容与涉及文件

| 问题 | 本次修订 | 涉及文件 |
| --- | --- | --- |
| P0 资产目标不完整 | create 必须 queue_item_id；update/archive 必须 asset_id 与正式目标修订，字段互斥；oneOf 区分必填及 changes；归档保留数据、退出默认搜索 | docs/CONTRACTS.md、ARCHITECTURE.md、docs/REQUIREMENTS.md、IMPLEMENTATION.md、DECISIONS.md |
| P0 新概念流程未闭合 | 查概念/别名去重→候选提案→人工审核字段与关系→Core 提交分配稳定 ID→资产替换候选引用、修订后再审；失败保留原图/草案 | docs/CONTRACTS.md、ARCHITECTURE.md、docs/REQUIREMENTS.md、IMPLEMENTATION.md、AGENTS.md、DECISIONS.md |
| P0 跨会话素材读取缺失 | asset.get/preview、queue.get/preview；只读受控句柄、路径与权限校验、有效期/重取、明确错误；稍后资源重启后无需重新上传 | docs/CONTRACTS.md、ARCHITECTURE.md、IMPLEMENTATION.md、docs/REQUIREMENTS.md、AGENTS.md |
| P1 技术决策权限 | 普通实现/合规小依赖自主；重要第三方/核心框架、路线替换、供应商绑定、费用/商业许可、数据/隐私/安全/权限变化及需求降级，先调查汇报并获用户确认 | AGENTS.md、IMPLEMENTATION.md、DECISIONS.md、docs/REQUIREMENTS.md、START-HERE.md |
| P1 Phase 1 偏大 | 限定基础存储/模型/概念关联/来源分析/提案/变更/可靠性和必要接口，长期实体不自动成为首版任务 | IMPLEMENTATION.md、ARCHITECTURE.md、docs/REQUIREMENTS.md、START-HERE.md |

README.md、docs/SOURCE-COVERAGE.md、docs/PROGRESS.md 同步状态与来源。历史 SOURCE-EXCERPTS.md、SOURCE-SUPPLEMENT.md 保持原样，以当前规范及 S6 最新修订为实施依据。沿用根目录 ARCHITECTURE.md/IMPLEMENTATION.md/DECISIONS.md，不另建 docs/ 同名副本。

## 明确后置

V1 不暴露 asset.delete、物理删除或反归档；不做一次批准同时原子创建概念与资产，也不暴露 concept.update/merge。概念先批准并提交、再审核资产是 V1 最小闭环。

复杂词典关系治理、大规模外部映射/概念合并迁移、高级资产关系推理、知识自动维护、Prompt 引擎、向量/以图搜图、WebUI、复杂备份/快照/容灾仍后置。基本别名、显式层级和新概念受审创建属于首版基础，不扩展为治理平台。

## Phase 0 与决策权限

Phase 0 尚未执行，账户内视觉分析、真实权限隔离、SQLite/FTS5、只读内容交付和恢复迁移均待验证。目前没有必须马上由用户确认的具体新组件；若调查发现需要重要第三方应用或核心框架，先提交选项与成本/许可/安全影响并取得确认，不能以“常规实现”先采用。既定 SQLite、Reviewer 路线与合规普通小依赖不重复确认。

## 文档级检查结果

- 13 份 Markdown 文档，六份核心文件、启动指令及契约体系齐全，没有新增规范文件。
- 15 个 JSON 块可解析；2 份 Schema 的所用关键字结构与基本约束已检查。57 个正反例通过，覆盖 create/update/archive 目标、缺失字段、归档状态/原因、候选绑定、非法术语分面/关系与后置操作拒绝。
- 审批示例与提案的对应目标、修订、文件哈希及操作一致；候选引用与概念审批摘要一致；十二分面保留。
- 内部文件链接与代码围栏检查通过。约束检查为本机文档检查器对所用 Schema 关键字的基本核对，不宣称完整标准认证或应用实现已通过。
- 跨文档核对保留 14 项既定约束：Agent/Local-First、SQLite/受管理原图、独立可信 Reviewer、两种稍后范围、持久待审与索引隔离、多标签/多用途/跨领域、标签关键词全文优先、按需解释、未来本机 WebUI、Finder 全 Vault 备份、事务/原图不可变/迁移、零新增费用、用户体验验收与必要测试、当前仅文档。
- 打包核对只含 Markdown、数量与内容对应、ZIP 完整性和逐文件摘要一致；文档检查脚本不进入交接包。

未编写或执行应用源码、未创建数据库/Vault、未安装应用依赖、未运行项目或 Phase 0。本次只完成交接文档定向修订。
