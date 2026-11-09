# 当前决策登记

本文只登记仍然有效且会影响后续实现的产品与技术决定。

版本：**1.0.0**。本文件只列当前有效决定。旧 V0.8/V1 决策和覆盖关系保存在 `docs/history/v1/DECISIONS.md`，发生冲突时以本文件和用户最新要求为准。

| ID | 当前决定 | 影响 |
| --- | --- | --- |
| D01 | Python 单一本机 HTTP 服务，一次启动 | `avds serve` 同时承载 API、WebUI、Store 和 SQLite；不再运行独立 Core/WebUI/Reviewer 服务 |
| D02 | Agent 与 WebUI 都是完整入口 | 两者都可导入、提案、审核、提交、检索、管理知识与 Prompt |
| D03 | 取消 Touch ID 和独立 Reviewer 门禁 | `confirmed=true` 是流程确认而非身份凭据；不宣称 Agent 无法自批 |
| D04 | 保留提案五项绑定和版本重审 | 防止错版本、错素材、错目标和批准后静默修改 |
| D05 | 服务统一正式写入 | Agent/WebUI 不执行任意 SQL，approval.record/commit.execute 不公开 |
| D06 | SQLite 为权威元数据存储 | DELETE、FULL、外键、5000ms busy timeout；正式事务显式 BEGIN IMMEDIATE |
| D07 | 原图内容寻址且不可变 | SHA-256 去重；拒绝、失败、归档、稍后和缓存清理都不删除原图 |
| D08 | Asset/Proposal/Operation/Queue 独立状态 | 提案获批不等于提交完成，草案不覆盖旧正式版本 |
| D09 | 两种稍后持久化 | 单项稍后及当前批次剩余稍后均跨会话恢复，不要求先分析 |
| D10 | concepts 模型为唯一权威词表 | 十二分面、多标签、多用途；新概念先提交，资产再修订复审 |
| D11 | 正式/待审索引隔离 | 未审核标签、文本、知识和 Prompt 不进入正式搜索或重建索引 |
| D12 | 知识 Markdown、Prompt JSON 版本化 | 均走提案/审核；Prompt 只做声明变量替换，不执行代码 |
| D13 | 配置可覆盖 | 命令行 > 环境变量 > JSON > 默认；Vault、host、port、浏览器、Vision 可配置 |
| D14 | 同一 Vault 单服务 | 使用操作系统文件锁；不同 Vault 可运行不同端口 |
| D15 | macOS 可选自动 Apple Vision | helper 可用时启用；派生特征可重建，不产生正式事实 |
| D16 | Windows 不使用 Apple Vision | 首版图像解码限 PNG/JPEG；不使用云端或付费自动回退 |
| D17 | 公开源码、数据私有 | GitHub 只发布代码与说明，不包含配置、Vault、素材、账号或同步服务 |
| D18 | 默认前台运行 | 不注册 launchd、Windows Service 或开机启动；CLI 是短连接客户端 |
| D19 | 零新增费用 | 不新增付费 API、云服务、服务器、存储或硬件 |
| D20 | 当前不做高风险扩展 | 物理删除、反归档、概念合并、复杂治理、多人协作和任意模板执行后置 |
| D21 | 用户快捷入口与完整 Agent CLI 分层 | 根目录/全局 `avds` 完全一致且只暴露常用命令；项目内 `./bin/avds` 保留完整业务能力 |

## 已验证事实

- macOS：25 项 Python 测试通过，包含快捷/完整 CLI 分层、用户配置、HTTP 双入口、审核绑定、正式索引隔离、上传重放、事务失败回滚和真实 Apple Vision。
- 安装：项目内 `.venv` editable 安装、Vision helper 构建和 init → doctor → serve → status → stop 生命周期通过。
- 静态检查：Python、JavaScript、shell 与 `git diff --check` 通过。

## 尚未验证

- Windows 10/11 实机安装、SQLite/FTS5、PowerShell/System.Drawing 解码和完整生命周期。
- 真实浏览器点击及视觉体验；HTTP 路由已有自动化测试，但不能替代产品验收。
- 旧受信安装与真实 Vault 的升级迁移；当前源码没有修改它们。

## 决策权限

常规 Python、SQLite 表/索引、标准库实现和不改变架构的重构可自主进行。重要框架、数据库/存储/审批/检索路线替换、供应商绑定、费用、许可、数据所有权、隐私或权限边界变化，必须先调查并取得用户确认。
