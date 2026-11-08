# AI Visual Design System V1

V0.8 Reviewed 交接包已于 2026-11-07（Asia/Shanghai）进入正式实施。Phase 0 已通过；V1 使用本地 SQLite、工作区外受信 Core、Touch ID Reviewer 与 Agent CLI，不引入第三方生产依赖或新增费用。

本包整合了用户提供的 V0.3～V0.5 决策级恢复材料，以及可读取的 V0.6～V0.7.1 和 V0.8 交接方案。十二个分面、受控词表、VARP、独立状态模型、批量审核及依赖门槛已补齐；后续明确修订优先。详见 [来源覆盖](docs/SOURCE-COVERAGE.md)。补充材料是结构化恢复，不是逐字聊天记录；技术可行性仍待未来 Phase 0 验证。

本版已按审查意见修正资产 create/update/archive Schema，补全候选概念审核与跨会话只读素材访问，收紧第三方决策权限及 Phase 1 范围。V1 物理删除、复合原子批准与复杂词典治理后置。修订记录见 [交付核对](DELIVERY-CHECK.md)。本版取代旧 docs.zip，文件体系和规范文档数量不增加。

## 项目目标

为单人 macOS 使用场景建立 Agent 优先的个人视觉资产系统：素材保存 → 可选 AI 分析与提案 → 独立本地 Reviewer 人工审核或稍后 → 可信 Core 正式入库 → Agent 检索。多年积累的原图、人工审核成果和知识属于核心资产。

源码保留在本项目目录；受信运行文件安装到 `~/Library/Application Support/AIVisualDesign` 与 `~/Applications/AVDS Reviewer.app`，默认 Vault 为 `~/Pictures/VisualAssetVault`。Agent 对这些位置没有直接写权限，只能使用受控 CLI；所有审核状态变化都由 Reviewer 请求 Touch ID。

## 文件导航

| 文件 | 用途 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 后续 Codex 的执行边界 |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | 需求、范围与行为规则 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 角色、存储、提交与检索架构 |
| [DECISIONS.md](DECISIONS.md) | 有效决策、覆盖关系与未决项 |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Phase 0～3、必要验证与完成条件 |
| [START-HERE.md](START-HERE.md) | 可复制到 Codex Desktop 的启动指令 |
| [docs/CONTRACTS.md](docs/CONTRACTS.md) | 提案、审核、查询和错误示例契约 |
| [docs/SOURCE-COVERAGE.md](docs/SOURCE-COVERAGE.md) | 来源覆盖与审查修订依据 |
| [docs/PROGRESS.md](docs/PROGRESS.md) | 后续会话的进度入口 |
| [docs/SOURCE-SUPPLEMENT.md](docs/SOURCE-SUPPLEMENT.md) | 用户提供的早期决策级补充材料 |

## 安装与运行

首次安装或升级（会重新构建、更新受信运行文件并启动 Core）：

```sh
sh scripts/install.sh
```

日常状态、启动、审核与停止：

```sh
"$HOME/Library/Application Support/AIVisualDesign/bin/avds" status
"$HOME/Library/Application Support/AIVisualDesign/bin/avds-start"
"$HOME/Library/Application Support/AIVisualDesign/bin/avds-review"
"$HOME/Library/Application Support/AIVisualDesign/bin/avds-web"
"$HOME/Library/Application Support/AIVisualDesign/bin/avds-stop"
```

通常无需手写 JSON：在本 Codex 项目中用自然语言要求 Agent 导入、记录分析、起草提案、查找待审项或搜索资产。Agent 调用安装后的只读/提案 CLI；批准、拒绝、退回修改、稍后与“本批次后续全部稍后”只能在 Reviewer 中完成，并要求 Touch ID。

CLI 是稳定 JSON 接口，形式为：

```sh
"$HOME/Library/Application Support/AIVisualDesign/bin/avds" <command> --json '<JSON 对象>'
```

主要命令：`import.stage`、`analysis.record`、`proposal.create/revise/get`、`queue.get/preview`、`asset.get/preview`、`candidate.get`、`search.pending/concepts/assets/related/explain`、`knowledge.get/search`、`prompt.get/list/render`、`visual.index/search`、`search.rebuild`、`operations.recover`。批准、拒绝、退回与两种稍后均不暴露给 Agent；`approval.record` 与 `commit.execute` 也只存在于受信组件内部。

## V1 已知限制

- 视觉分析依赖当前 Codex Desktop 账号能力和额度；额度不可用时仍可暂存与稍后，不自动切换付费 API。
- Reviewer 是原生 macOS 应用，正式审核要求已配置的 Touch ID；不提供聊天确认降级。
- 中文检索采用已批准术语、FTS5 和受控子串回退，没有高级中文分词。
- WebUI 只读，创建或修改知识、Prompt 与素材仍需 Agent 提案并在独立 Reviewer 中完成 Touch ID 审核。
- Apple Vision 相似距离只用于排序，不能解释为同一作品、同一作者或正式概念；系统升级后派生特征会重建。
- 仍不提供物理删除、反归档、概念更新/合并、复合原子批准、云部署或任意模板代码执行。
- 安装/升级会改变受信程序摘要，必须重新运行安装脚本并重启 Core；直接修改源码不会改变已安装运行版本。

## Finder 便携备份

结束导入、提交和其他数据库操作，关闭 Reviewer、Core 与全部数据库连接；在 Finder 中复制或压缩完整 VisualAssetVault，再保存到已有的其他存储设备。恢复时解压到新位置并重新选择该 Vault；内部引用不得依赖旧绝对路径。备份前若有崩溃留下的未完成操作，先恢复到稳定状态并正常关闭。

不开发备份 CLI、在线快照、自动恢复向导、备份保留策略或复杂容灾系统。不要只复制数据库而遗漏原图和持久待审核资料，也不要在数据库操作进行中复制。未来若切换 WAL，必须同步修订关闭和复制规则。
