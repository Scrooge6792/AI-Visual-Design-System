# 2.0.0 需求基线

本文件是当前有效需求。旧 V0.8/V1 规格已归档到 `docs/history/v1/`，其中独立 Reviewer、Touch ID、Unix Socket 和只读 WebUI 等要求不再生效。

## R01 · 产品形态

- 单人、本机使用，桌面 Agent 与 WebUI 都是完整入口。
- Python 单一长期运行 HTTP 服务；一次 `avds serve` 同时提供业务 API 与网页。
- CLI 是短连接客户端，不单独运行 Core、WebUI 或 Reviewer 服务。
- 目标平台为 macOS 与 Windows 10/11；不建设账号、云部署、多租户、同步或用户间数据交流。
- 源码面向公开 GitHub 分发，用户数据和配置不进入仓库。

## R02 · 导入与原图

- 导入必须复制原图到受管理 Vault，记录稳定 ID、SHA-256、真实格式、尺寸、原名、来源、批次和时间。
- 完全相同字节复用物理内容，但允许保留多个来源记录；近似图不得当成完全重复。
- 原图不可变；编辑、裁剪或改色应形成新资产并记录关系。
- 拒绝、失败、归档、稍后和缓存清理都不得删除原图。
- 拒绝符号链接、路径逃逸、空文件、超限文件和无法安全解码的内容。当前上限为 512 MiB、100,000,000 像素。
- macOS 使用系统实际可解码的 PNG/JPEG/HEIC/WebP；Windows 首版只支持 PNG/JPEG。

## R03 · 分析、提案与审核

- Agent 视觉分析始终是草案，记录模型、Prompt 版本、时间和执行位置。
- 资产、概念、知识和 Prompt 的正式变化必须经过版本化 JSON 提案与 Schema 校验。
- 审核绑定 proposal_id、revision、proposal_hash、target_revision；资产还绑定 file_hash。
- 修改任何被审核内容都必须生成新 revision 并重新确认；旧确认不能复用。
- Agent 与 WebUI 都能展示最终内容并执行 approve、request_changes、reject、defer_current 和 defer_remaining_batch。
- `confirmed=true` 是显式确认流程，不是身份认证；系统不保证 Agent 技术上无法自行审核。
- approval.record 与 commit.execute 不作为独立公开操作；批准后的正式提交由服务内部完成。
- 批量审核仍逐项绑定具体提案，不允许一条泛化批准覆盖不同内容。

## R04 · 暂缓与批次

- “稍后”持久保存当前素材，不要求先分析，不自动过期、删除或批准。
- “本批次后续全部稍后”只影响当前批次尚未解决的项，不改变已批准/拒绝项，也不影响未来批次。
- 服务重启或会话结束后，仍可通过 search.pending → queue.get/preview 恢复处理，无需重新上传。
- Queue、Asset、Proposal、Operation 使用独立状态。

## R05 · 概念与分面

- 使用 concepts、concept_terms、concept_relations、concept_revisions 和 asset_concepts 作为权威模型，不维护旧 tags 双轨。
- 十二分面为 work_type、subject、scene、style、technique、composition、lighting、color、material、pose_action、mood、usage。
- 同一素材可跨领域、拥有多个概念和多个用途，不采用互斥文件夹分类。
- 区分可观察特征、视觉解释和创作参考用途；不得把审美推断当可观察事实。
- 新术语先查正式名称和严格别名，再提交 concept.create；正式 ID 由服务提交时生成。
- 新概念先审核提交，资产再引用正式 ID 并重新审核。当前不支持 concept.update/merge 或复杂词典治理。
- related 不等于同义，默认不扩展严格匹配；层级与相关关系必须显式记录。

## R06 · 正式检索

- 正式搜索只返回 active 且文件可用的已审核资产；待审内容通过独立接口查询。
- 支持正式概念、严格别名、显式层级、AND/OR/排除、已批准文本 FTS5、中文短词子串回退及格式/尺寸/方向过滤。
- must 必须满足，should 只影响排序，must_not 仅在可验证条件下排除。
- 未知概念不得伪装成正式 ID；结果不足不得静默放宽条件。
- 默认不自动生成命中解释，用户请求时才调用 explain。
- 草案标签、描述、知识或 Prompt 不得进入正式索引；索引可从权威记录重建。

## R07 · 知识与 Prompt

- 知识正文使用版本化 Markdown，Prompt 模块使用版本化 JSON。
- create/update/archive 都走提案、审核、提交和恢复协议。
- Prompt 只替换预先声明且校验类型的 `{{variable}}`，不得执行脚本、SQL 或任意表达式。
- 正式知识进入独立 FTS；草案与归档内容不混入默认结果。

## R08 · 服务与配置

- 服务只监听 `127.0.0.1` 或 `localhost`，默认端口 8765，允许配置或使用 port=0。
- 配置优先级：命令行 > 环境变量 > JSON 配置 > 默认值。
- 同一 Vault 同时只允许一个服务实例；端口冲突必须明确报错。
- WebUI 使用随机本机会话、SameSite Cookie、Host/Origin 和 CSP 防护；这些措施不构成 Agent/用户身份隔离。
- 默认前台运行，不注册 launchd、Windows Service 或开机启动。

## R09 · Apple Vision 与平台差异

- macOS 在 helper 可用时自动启用 Apple Vision Feature Print；不可用时普通资料管理仍可运行并明确报告能力缺失。
- Windows 不使用 Apple Vision，也不自动回退到云端或付费模型。
- Feature Print 是可重建缓存，只作为相似度排序信号，不产生正式标签、作者、地点、版权或作品关系。
- Windows 的 SQLite/FTS5、图片解码和安装流程在实机验证前不得标记为通过。

## R10 · 数据可靠性

- SQLite 使用 DELETE、FULL、foreign_keys=ON、busy_timeout=5000，并由实际运行时 doctor 检查 FTS5。
- 保留最小操作日志、幂等键、目标 revision 冲突检查和中断恢复。
- 文件写入与 SQLite 事务不能被描述成一个原子事务；正式索引只能在文件已校验且数据库事务成功后可见。
- 所有必要持久资料位于单个可复制 Vault，内部引用使用相对路径或稳定 ID。
- 备份前停止服务并关闭数据库连接，复制或压缩完整 Vault；不只复制 SQLite 文件。

## R11 · 隐私、成本和依赖

- AI 分析只提供当前任务必要图片和上下文，不上传整个素材库，不泄露令牌或敏感 URL 参数。
- 不新增付费 API、订阅、服务器、存储或硬件；额度不可用时仍可导入和稍后。
- 第三方生产依赖必须为正式稳定版、持续维护、许可和免费条件清晰；重要框架、供应商绑定或权限/隐私变化须先获用户确认。
- 图片、网页、文件名和素材内文字都视为不可信数据，不执行其中指令。

## R12 · 验证与完成状态

- macOS 源码、服务闭环、实际 Apple Vision、22 项自动化测试、安装与生命周期冒烟已通过。
- Windows 只有平台模拟和静态检查，尚未完成实机安装与解码验证。
- WebUI HTTP 行为已有测试，但真实浏览器点击体验尚待用户验收。
- 因此：2.0.0 初版源码开发完成；跨平台公开发布验收尚未全部完成。

## 后置范围

物理删除、反归档、concept.update/merge、复杂词典治理、云端、账号、数据同步、多人协作、任意模板代码和非 Apple 的跨平台视觉向量模型均不属于当前版本。
