# 系统架构与实施约束

## 当前运行架构（2.0.0，2026-11-08）

```text
Agent → 短连接 CLI ─┐
                  ├→ 一个 Python 本机 HTTP 服务 → Store → Vault / SQLite
浏览器 WebUI ──────┘       导入、提案、审核提交、查询、知识、Prompt
```

同一个 HTTPServer 串行处理请求，单一 Store 连接统一正式写入；SQLite 显式 BEGIN IMMEDIATE，DELETE/FULL/外键/busy timeout=5000。写操作保留幂等 operation_id；文件就绪与 SQLite 提交仍是独立阶段，失败保留原图和恢复信息。CLI 不持有数据库连接，默认不运行额外守护进程，不注册系统服务。

`config.py` 合并命令行、环境变量、JSON 配置；`VaultLock` 在打开 Store 前使用 Windows msvcrt 或 POSIX flock 获取操作系统锁，崩溃由系统释放，不用 PID 文件当互斥证据。`data/service.json` 仅保存当前端口/会话/PID/根路径，是可替换运行状态；原图和权威记录仍用相对路径/稳定 ID。

HTTP 仅绑定 127.0.0.1 / localhost；每次服务随机令牌。CLI 读取所选 Vault 服务记录并使用 bearer 短连接；浏览器由 avds open 建立 HttpOnly / SameSite=Strict 会话。Host 和浏览器 Origin 必须匹配实际本机端口，配合 CSP、无跨域许可、不记令牌访问日志。此令牌防外站访问，不提供 Agent/用户身份隔离。

Agent 与 WebUI 开放同一完整业务命令。审核要求 `confirmed:true` 和具体提案修订/摘要/目标绑定；确认不是密码或可信身份凭证。服务内部执行 approval/commit 协议，不开放独立任意提交接口。取消旧 Reviewer 二进制摘要校验与 Touch ID。未审核内容继续隔离于正式索引，原图、状态模型、候选依赖和变更版本要求不变。

浏览器通过 `/api/import` 流式上传到暂时接收文件，再经同一 `import.stage` 校验复制进持久 staging；请求结束清理上传临时文件，不删除用户原文件或已持久原图。媒体从稳定 ID 获取并复验哈希，不接受任意媒体路径。

平台差异集中 `platform.py`：macOS 系统解码；Windows PowerShell/System.Drawing 原生 PNG/JPEG 解码；macOS 有 helper 时 auto Apple Vision，Windows 返回 CAPABILITY_UNAVAILABLE。无第三方生产依赖。Windows 文件 fsync + 同卷 replace，无法用标准库同步目录句柄，不能宣称目录持久化与 POSIX 完全等价。

以下为旧版细分规格。涉及独立 Reviewer、可信进程身份隔离、Unix Socket、Touch ID 或 WebUI 只读的段落已被本节覆盖；数据模型、独立状态、原图保护、版本/hash绑定、查询与恢复协议继续适用。旧运行组件不参与当前安装链路。

本文件是文档规格。逻辑实体与状态以用户提供的 V0.3～V0.5 决策级补充及后续修订为依据；具体列类型、索引、传输实现由 Codex 后续确定。不得将规格当作已实现系统。

## 角色与数据流

```text
用户自然语言 → Agent → 受控导入/提案/查询接口
                        ↓
                持久待审核资料与提案
                        ↓
用户 → 独立本地 Reviewer → 可信审批通道 → Core
                                            ↓
                               文件就绪 + SQLite 事务
                                            ↓
                              已批准正式资产与派生索引
```

Agent 负责理解、分析、起草、查询规划与按需解释。Reviewer 负责展示最终被审批的图片与草案并接收用户动作。Core 校验输入、审批、版本和权限，统一正式写入、状态转换、索引维护和恢复。

采用 VARP：Agent-First、Review Before Commit、Trusted Approval、Auditable & Recoverable。本地 CLI 是 Agent 首选接口，未来可适配 MCP，不同时开发多套适配。Core 接口分为 Agent 可调用的提案/只读能力与受信组件内部的 approval.record、commit.execute。Agent 可以请求打开审核器，不能模拟用户批准。Agent 可写源码与测试数据，不应可写生产数据库、对象、正式元数据或审批凭据；真实 Vault 不作为普通源码工作区。

## 必须验证的信任边界

独立进程不自动带来隔离。同一 macOS 用户下，普通文件权限通常不足以区分两个进程；单独给 Reviewer 加沙盒也不能自动阻止未受限 Agent 访问其数据。不能用“路径放到工作区外”代替安全证明。

Phase 0 应评估宿主对 Agent 的有效文件/工具限制、受信写入进程、受保护存储与本地 IPC 身份验证的组合。App Sandbox 是候选机制，不是既成方案。需要把生产运行身份、开发/更新权限、用户授予的文件访问权和 Agent 能使用的 UI 自动化能力一起纳入威胁模型。若 Agent 能修改正在运行的 Reviewer/Core、读取批准秘密或通过自动点击批准，则边界未成立。

不要求抵御用户主动解除权限或系统管理员攻击，但正常工作流中不能让 Agent 因自身输出获得批准权限。仅使用 App 提示词或可由 Agent 修改的配置不合格。无法在零新增成本和当前宿主约束下实现时，记录障碍并请用户决定产品边界，不暗中放宽。

## 目录与可迁移性

```text
AI-Visual-Design/
├── project/                 # 本交接包、未来源码与测试
└── VisualAssetVault/         # 独立的真实持久资产
    ├── data/                # SQLite 与必要版本元数据
    ├── staging/             # 持久待审核原图，deferred 不是缓存
    ├── objects/sha256/       # 内容寻址原图
    ├── knowledge/           # 未来实际存在的知识资料
    ├── prompts/             # 未来实际存在的 Prompt 资料
    └── cache/               # 可重建缩略图等
```

此树是组织建议，不要求 V1 创建空的未来模块。SQLite 是元数据权威来源；图片由对象文件保存。物理路径不按标签组织。同一哈希对象可复用，来源及逻辑关联单独记录。运行时 Vault 根路径可配置，但持久引用必须为 Vault 内相对路径或稳定 ID。缓存清理不能删除待审原图、审核记录或人工成果。

## 逻辑数据模型

| 实体 | 职责与约束 |
| --- | --- |
| files | 物理文件、SHA-256、相对路径、格式、尺寸；原内容不可变 |
| assets | 稳定身份、标题、状态与修订号；引用物理文件 |
| asset_sources | 来源 URL、原名、作者、版权、许可、导入时间和用户备注；同资产多来源 |
| asset_relations | 相似、衍生、系列等明确关系；不把相似图合并为相同文件 |
| analysis_runs | 分析正文、模型、Prompt 版本、时间、执行位置；未审核分析不是正式事实 |
| concepts | 标准概念身份、分面与定义，具稳定 ID |
| concept_terms | 首选、中英文名称、严格别名，避免重复概念 |
| concept_relations | broader/narrower/related；严格区分相关与同义 |
| concept_mappings | 外部映射的未来数据边界；V1 不建设大规模映射功能，也无需提前建空表 |
| concept_revisions | 保留已创建概念的初始版本与审核关联；复杂修订/合并治理后置 |
| asset_concepts | 资产与概念多对多关联，保留观察/解释/参考用途的性质 |
| change_proposals | V1 资产创建/更新/归档及 concept.create 草案；按对象/操作校验目标，版本、摘要、目标修订；物理删除后置 |
| review_events | 用户动作、最终逐项审批内容、修正记录；仅可信来源可记为批准 |
| operations | 操作 ID、请求摘要、恢复阶段、稳定结果；幂等 |
| import_batches | 批次标识、顺序、进度和统计 |
| review_queue_items | 批次项与持久审核队列状态，可无提案先 deferred |
| search_documents / FTS | 仅正式已批准内容的可重建派生文档 |

V0.3 的 tags/tag_aliases/asset_tags 已由 V0.4 的 concepts 体系取代，不能重复维护两套权威词表。早期 files 的内容寻址职责可内部命名为 blob，但逻辑映射必须明确。具体 SQL 表名、列类型和约束实现可按选定运行时确定。

十二个分面见 docs/REQUIREMENTS.md R05。概念可通过稳定 ID 关联独立 Markdown 知识、参考资产和 JSON Prompt 模块；V1 仅保留关联与可迁移存储边界，不实现完整知识库/配方引擎。

## 独立状态模型与动作

不能把资产、提案、操作和审核队列合成一个状态字段。

| 对象 | 状态 | 含义 |
| --- | --- | --- |
| Asset | staged / active / archived | 暂存、正式有效、归档；approved 不是资产状态 |
| Proposal | draft / in_review / approved / rejected / superseded | 草案、审核中、已批、拒绝、被新版本取代 |
| Operation | pending / committing / committed / failed | 提交与恢复进度；committed 不是提案状态 |
| Queue（后续补充实现建议） | pending / in_review / deferred / resolved | 独立追踪待审与稍后；不改变资产或提案的含义 |

新文件对应 staged 资产和 pending 队列，可不分析直接 deferred。开始分析/审核时创建 draft 或 in_review 提案。用户要求修改产生新 revision；旧提案版本 superseded，旧批准不可复用。可信批准使 Proposal=approved，但只有 Operation=committed 且文件可用后，新增 Asset 才成为 active 并进入正式检索。拒绝只关闭提案、解决本次队列，不删除原图；可以以后创建新提案再审。

正式资产修订期间，旧批准版本仍可检索，新草案不可见；提交成功后原子切换至新修订。archived 通过审核变更，不在默认 active 搜索中。V1 只实现归档，不暴露 asset.delete、物理删除或反归档；未来删除需独立定义权限、额外用户确认与引用保护，不能借归档、拒绝或失败擦除原图。

批量审核可集中改标签、批准部分项或要求重分析，但每项都绑定 proposal_id、revision、proposal_hash、file_hash、target_revision。批次按钮不得生成一条无逐项内容的泛化批准。

批量暂缓明确当前批次的未审核集合并记录逐项结果，不能把已批准或已拒绝项降为 deferred。再次执行同一请求返回同一结果；未来批次仍正常审核。队列状态必须持久化并可按批次继续。

## V1 实现边界

必须实现：受管理持久原图和 SHA-256 去重，SQLite 基础模型、来源/分析/提案/审核，十二分面下的小规模受控概念、多标签和多用途关联，资产创建/必要元数据更新/归档、基本术语别名与少量显式层级关系、事务/幂等/恢复，以及 Reviewer、Agent 和检索所需接口。逻辑实体表列举长期模型，不等于 Phase 1 必须做完所有模块。

可预留关联边界但后置完整功能：复杂专业术语关系治理、大规模 Getty AAT/外部词典映射、概念更新/合并及批量迁移、高级资产关系推理、知识自动维护、Prompt 配方引擎、向量/以图搜图、WebUI、复杂备份/快照/容灾。现有显式关系可存储/读取，不能借此开展自动关系推理或引入新服务。详见 IMPLEMENTATION.md。

## 新概念到资产关联

Agent 先查首选名称和严格别名，并结合分面/定义检查重复；未找到可复用词条才提交 concept.create。Core 分配持久 candidate_id 与版本化提案，候选名称/定义/分面/中英文/别名/关系与重复候选由 Reviewer 审核。关系只指向已批准概念，V1 仅做必要冲突/循环检查。正式 concept_id 只有在可信批准后的词典事务成功时才由 Core 分配；提交时再查重，幂等重试不重复建词。

候选与正式词条逻辑隔离，可保存在 change_proposals 中，不要求单独候选服务。asset 草案通过 candidate_concept_refs 固定候选提案修订/摘要，不把 candidate_id 放进 concept_ids。Core 只允许引用全部已落实为正式 ID 的最终资产版本进入审批/提交。概念提交后的 candidate→concept 映射持久保存，可由 candidate.get 重读；Agent 替换引用并生成资产新修订，再交 Reviewer 确认，不能重写旧批准。

V1 不支持单个批准动作原子创建概念与资产；同一审核会话中先概念提交，后资产刷新/审批。概念拒绝或失败时保留资产草案和原图，明确依赖未解决，需修订候选、选择现有词条或经用户修改后移除候选。概念成功但资产失败时，合法词条保留可复用，资产按日志重试；无半成品资产对正式索引可见。concept.update/merge 与复合原子审批后置。完整契约见 docs/CONTRACTS.md。

## 稳定 ID 与受控只读访问

asset.get 返回正式已批准详情，asset.preview 返回原图或安全预览的只读句柄；queue.get 返回持久待审详情并标注未审核草案，queue.preview 提供待审原图/预览。由 Core 将 Vault 内稳定 ID 解析为相对路径，校验访问权限、路径穿越/符号链接逃逸、存在性、格式、资源上限和登记指纹，不把正式库写权限授予 Agent。

Agent 可用受控内容句柄或只读导出副本分析图片，不能持有正式库可写路径/凭据。句柄交付机制在 Phase 0 验证；会话或服务结束导致临时句柄失效时，凭持久 asset_id/queue_item_id 重新获取，不能依赖旧缓存路径。缺失/不支持/越权或哈希异常返回明确错误，不伪造预览。

批量导入→本批次剩余全部稍后→退出→数日后 search.pending 找批次→queue.get/preview 重新读取→分析/新提案→独立审批，是 V1 必须成立的恢复流程；不需要重新上传、旧聊天上下文或人工整理物理目录。未审核分析仅在待审/提案详情中显示，不混入 asset.get 或正式索引。

## 数据库与文件提交协议

SQLite 配置目标：journal_mode=DELETE、synchronous=FULL、foreign_keys=ON、busy_timeout=5000。外键等连接级配置需每连接生效；实际返回值和运行时能力需检查。

建议最小提交阶段：

1. 验证可信批准绑定的 proposal_id、revision、proposal_hash、file_hash、target_revision，以及请求幂等键。asset.create 检查 queue_item_id 与 target_revision=0；update/archive 检查 asset_id 的当前正式修订等于 target_revision≥1，并在写事务内再次比较，防止覆盖并发修订。概念创建按候选对象的独立审批契约校验，不伪造原图哈希。相同键不同请求应冲突，不复用旧结果。
2. 持久记录 pending 操作及恢复所需信息。
3. 将对象安全写入受管理位置，校验内容和可读性；同哈希复用，不覆盖原图。处理必要的文件和目录持久化。
4. SQLite 单事务更新正式资产、标签、审批关联、搜索文档及操作提交结果。只有文件已验证、事务成功，正式检索才可见。
5. 标记完成并返回稳定结果。清理必须在确认无引用和无恢复需求后进行，不能盲删对象。

SQLite 事务不能覆盖外部文件系统。跨卷复制、磁盘满、文件同步失败、崩溃与重复调用都需要明确处理；重命名成功不等于整个业务提交原子完成。

| 中断点 | 最小恢复行为 |
| --- | --- |
| 文件未写完 | 不发布正式资产，保留完整暂存与恢复记录 |
| 对象就绪，数据库未提交 | 按原批准重验后继续；审批失效则保留待处理 |
| 数据库已提交，响应丢失 | 按操作 ID 返回既有结果，不重复产生资产 |
| 哈希/提案版本/目标资产修订变化 | 终止正式提交，刷新目标与最终草案后重新审核 |
| 缺文件或对象损坏 | 返回明确异常，不假装搜索结果可用 |
| 索引失配 | 从已批准权威记录重建，草案不得混入 |

恢复是日常可靠性，不是被取消的容灾系统。必要日志保持精简，不引入分布式事务平台。

## 查询与索引

Agent → 标准概念解析 → 结构化 Query → Core 验证 → 参数化 SQL/受控 FTS 表达式 → 结果。参数化 SQL 之外，还需正确处理 MATCH 自身的语法，不能把任意用户文本当 FTS 操作符执行。

别名等价、层级展开用明确关系，related 默认不扩大严格条件。FTS 搜索已批准标题、描述与设计价值；短中文词走术语/子串回退。正式文本更新和派生搜索文档更新处于同一受控事务；外部内容 FTS 若使用触发器，需覆盖全部更新路径且支持重建。

待审搜索只有专用基础信息查询，草案详情明确标注未确认。Core 保留按需 explain 所需匹配信息，不要求默认生成说明段落。未来本机 WebUI 只接同一接口，不能另开直接数据库写入口。

## 后续扩展架构

WebUI 由临时本机 HTTP 进程提供，浏览器只访问随机令牌建立的本机会话。服务端维护只读命令白名单，并经 Core Unix Socket 查询；媒体仍由稳定 asset_id/queue_item_id 解析并复验哈希，浏览器不能提交 Reviewer 动作。

知识与 Prompt 沿用 VARP：Agent 起草 `knowledge.*` / `prompt.*` 版本化 JSON 提案，Reviewer 展示最终正文并要求 Touch ID，Core 提交后才写入 `knowledge/` Markdown、`prompts/` JSON 与正式 FTS。模板渲染器只识别 `{{variable}}`，变量必须预先声明并校验类型。

视觉相似检索由受信 Core 调用 Apple Vision helper，派生 Feature Print 存入 `cache/featureprints/`，SQLite 只记录引擎修订、系统构建和相对路径。缓存可重建，不是权威数据；正式搜索对象仍限 active 资产，待审图片只能作为查询图，不能因相似度自动进入正式索引。
