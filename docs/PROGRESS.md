# 项目进度

更新：2026-11-08。

- 当前交付：V0.8 reviewed 定向修订文档包。
- 来源：已整合用户 V0.3～V0.5 决策级补充与后续可读取会话；G01～G03 来源阻塞解除，不再要求早期逐字原文。
- 补齐：十二分面、三类判断、受控词表实体、VARP/JSON Schema、五项审批绑定、独立状态、CLI、批量/部分审核、Stars 门槛、成熟方案筛选。
- 修正：上一版混合状态已替换；tags 模型被 concepts 取代；运行文档不再设来源阻塞。
- 应用状态：V1 已实现并安装；无第三方生产依赖。受信运行目录为 `~/Library/Application Support/AIVisualDesign`，Reviewer 为 `~/Applications/AVDS Reviewer.app`，空的真实 Vault 为 `~/Pictures/VisualAssetVault`。
- Phase 0：已通过。SQLite/FTS5、原生图像、现有账号视觉草案、Touch ID 可信审批、Agent 伪造拒绝、幂等重放与 Vault 跨目录迁移均有实际证据；6 个最小自动化测试通过。详见 [PHASE0.md](PHASE0.md)。
- Phase 1：已完成。实现受管理暂存、真实格式/资源限制、路径与符号链接保护、SHA-256 去重与只读对象、SQLite 基础模型、独立状态、analysis_runs、版本化资产/概念提案、内置 Draft 2020-12 Schema 子集校验、concept.create/候选映射、create/update/archive、稳定 ID 详情/预览、幂等与最小恢复。
- Phase 2：已完成。原生 AppKit Reviewer 显示图片和最终 JSON，支持所选项逐项绑定的批量/部分批准、拒绝、退回修改、稍后和本批次后续全部稍后；所有状态变更要求 Touch ID，Agent 不能调用 review.action。Reviewer 更新使用稳定 operation ID 支持响应丢失重试。
- Phase 3：已完成。实现正式/待审隔离、概念及严格别名、显式层级展开、related 可选扩展、FTS5、中文短词子串回退、must/should/must_not、格式/尺寸/方向过滤、待审统计、关联查询、按需 explain 和索引重建。
- 必要检查：9 个 Python 标准库测试全部通过；Swift Reviewer 编译及 ad-hoc hardened runtime 签名通过；Phase 0 真实 Touch ID、伪造拒绝、迁移与幂等证据通过；正式 Core stop/start/status 与 Reviewer 连接通过。首次最终更新遇到遗留 Socket 导致 launchd error 5，已定位并修正安装脚本在服务退出后仅清理可重建 Socket；复测停止会自动移除 Socket并可正常重启。
- Phase 4 源码完成：本机只读 WebUI、随机会话令牌、Origin/CSP/SameSite 防护、素材灯箱、待审队列、知识/Prompt 书架与视觉相似入口；未增加前端框架。
- Phase 5 源码完成：知识 Markdown 和 Prompt JSON 的 create/update/archive 提案、Touch ID 审核提交、版本文件、知识 FTS、声明变量 Prompt 渲染与恢复路径。
- Phase 6 源码完成：Apple Vision Feature Print helper、active 资产派生索引、asset_id/queue_item_id 相似查询、系统构建绑定与自动重建；不联网、不写正式标签。
- 后续扩展必要检查：11 个本地测试全部通过（含沙盒外 Apple Vision）；Swift、Python 与前端 JavaScript 语法/构建通过。
- 受信安装：用户已明确批准，WebUI、知识/Prompt Core、Apple Vision helper 与新版 Reviewer 已安装，Core 已重启；正式 Vault 保持原位，未导入或删除素材。
- WebUI 检查：localhost 随机会话可访问，Core/空素材/空待审/空知识/空 Prompt 状态正确；实际布局呈现十二分面光谱轨、素材灯箱和检查器。唯一 favicon 404 已修复。
- 当前阻塞：无。
- 下一步：用户直接使用 WebUI、Agent 与 Reviewer；有真实素材后再由用户体验检索和审核流程，出现问题时专项修复。
- 本轮修订：分操作资产 Schema；候选概念查重/审核/顺序提交；稳定 ID 只读原图/预览与跨会话恢复；重要第三方先确认；Phase 1 最小化。物理删除、复合批准、复杂概念治理后置。
- 文档核对与简洁修订摘要：DELIVERY-CHECK.md；当前仍未开始应用开发或 Phase 0。

## 后续记录模板

每阶段仅记授权范围、完成项、关键决策、必要测试、阻塞、下一步。连续实施已授权时不增加阶段确认门槛；安全、费用或产品取舍变化需另行处理。
