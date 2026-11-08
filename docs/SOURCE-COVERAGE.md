# 来源与覆盖

原会话：[Visual Design System Arc](chatgpt-conversation://6aeee352-c7f8-83ec-87c7-4320ccfaf8f5)。首次读取返回最后五轮，无更早分页，已保存于 [可读取原文](SOURCE-EXCERPTS.md)。用户随后提供 [决策级补充材料](SOURCE-SUPPLEMENT.md)，正式补齐 V0.3～V0.5。这是依据完整讨论整理的结构化恢复，不是逐字聊天记录；不再需要早期逐字原文才能推进。

## 来源索引

| 来源 | 定位 | 内容 |
| --- | --- | --- |
| S0 | SOURCE-SUPPLEMENT.md（本轮用户附件） | V0.3～V0.5 决策恢复、后续修订、Stars 门槛和交接要求 |
| S1 | 2d2602b6-bcf2-4747-ad10-5f5e47788ee6 | 确认交接、当前不开发 |
| S2 | ff6dcd86-00c0-4d27-b229-76b181b65169 | WebUI 本机服务、三项可靠性、用户验收、阶段计划 |
| S3 | 15fa6f20-12be-43f9-b196-5b9ce539c218 | V0.7.1 Finder 备份与轻量存储 |
| S4 | 51359a7d-fc35-45bf-a1e9-09e4bc5fd1fb | 取消默认搜索解释、V0.7 安全存储 |
| S5 | 5e2d91af-3a24-4ba9-ab82-c33a6a6c36df | Reviewer、两种稍后、V0.6 检索 |
| S6 | 当前用户“交接包审查问题修订” | P0 三项闭环修复、P1 决策权限与 Phase 1 最小范围 |
| S7 | 2026-11-08 用户明确确认的跨平台方案 | Python 单一本机服务、两完整入口、取消 Touch ID/独立 Reviewer 门禁、可配置部署、macOS 可选自动 Vision、Windows 无 Vision、公开源码准备、不做同步或交流 |

## 覆盖矩阵

| 版本 | 有效决策 | 文档位置 |
| --- | --- | --- |
| V0.3 | Agent/Local-First、SQLite、原图本地复制、稳定 ID、哈希与不可变、多来源/关系、逻辑实体 | REQUIREMENTS R01～03；ARCHITECTURE |
| V0.4 | 十二分面、动态跨领域视图、concepts 词表、映射/修订、三类判断、事实证据、小词表、知识关联 | REQUIREMENTS R05；ARCHITECTURE；DECISIONS |
| V0.5 | VARP、JSON Schema、五项审批绑定、独立状态、CLI、可信内部工具、单项/批量/部分审核 | REQUIREMENTS R03/R07；ARCHITECTURE；CONTRACTS |
| V0.6 | FTS5、中文短词回退、严格约束、正式/待审隔离、批次恢复 | REQUIREMENTS R04/R06/R10；CONTRACTS |
| V0.7 | 内容寻址、事务恢复、安全、隐私、派生数据保护 | ARCHITECTURE；REQUIREMENTS R07/R08 |
| V0.7.1 | DELETE/FULL、Finder 复制、取消复杂备份、三项可靠性 | README；REQUIREMENTS R08；DECISIONS |
| V0.8 | 文档交接、Phase 0～3、必要测试、用户验收、零新增费用 | AGENTS；IMPLEMENTATION；START-HERE |
| V2.0.0 | Python 单服务、Agent/WebUI 双完整入口、取消 Touch ID 门禁、macOS 可选 Vision、Windows 无 Vision、公开源码安装准备 | S7；README；AGENTS；ARCHITECTURE；DECISIONS；PROGRESS |

旧包 G01～G03 来源完整性阻塞已解除。完整性指上述设计输入的有效决策覆盖，不声称拥有全部逐字聊天记录。

## 本轮审查修订依据

S6：用户在本会话提供的“交接包审查问题修订”，为本次定向修改的最新输入，覆盖旧接口不完整及权限/范围表述。涉及资产操作 Schema、新概念闭环、持久只读访问、技术决策权限和 Phase 1 最小范围。原补充材料和可读会话作为历史存档保持不变；实施以当前需求、架构、决策、计划、契约为准，不能从旧存档重新启用后置操作。

文件位置沿用既有体系：ARCHITECTURE.md、IMPLEMENTATION.md、DECISIONS.md 位于项目根，REQUIREMENTS.md 与 CONTRACTS.md 位于 docs/；不新建重复的 docs/ 同名规范。

## 优先顺序与事实边界

用户当前要求及补充材料为正式输入，明确后续修订覆盖早期建议。DECISIONS 记录覆盖关系。具体列类型、运行时和通信实现由未来 Codex 在边界内决定，不冒充历史决定。

历史 V1 已安装并有 Phase 0 证据；当前 S7 重构只更新源码、测试和文档，没有更新旧安装或真实 Vault。S7 覆盖旧身份隔离、Unix Socket 和只读 WebUI 结构；旧 Phase 0 结果不是新版 Windows 运行证明。当前实现与检查见 PROGRESS.md。原文中的技术版本、实际 Stars 和漏洞陈述不作为当前保证；Stars 门槛仍是准入政策。
