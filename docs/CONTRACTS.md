# 2.0.0 接口契约

应用版本为 **2.0.0**，接口契约版本为 **1.0**。提案字段的权威结构位于 `src/avds/schemas/`；本文件描述传输、命令和状态约束。

## 传输

CLI：

```sh
avds <command> --json '<JSON 对象>'
avds <command> --json-file payload.json
```

HTTP：

```text
POST /api/command
Authorization: Bearer <service token>   # CLI
Cookie: avds_session=<service token>     # WebUI
```

请求为 `{ "command": "...", ...payload }`。

成功：

```json
{"ok":true,"result":{}}
```

失败：

```json
{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"..."}}
```

## 生命周期命令

| 命令 | 作用 |
| --- | --- |
| init | 创建配置和空 Vault；已有配置不覆盖 |
| doctor | 检查 Python、SQLite、FTS5、图像格式与 Vision 能力 |
| serve | 启动唯一长期服务 |
| status | 查询 SQLite PRAGMA、版本、URL 和能力 |
| open | 打开带本机会话的 WebUI |
| stop | 请求当前服务正常关闭 |
| commands | 列出公开业务命令 |

## 业务命令

| 分组 | 命令 |
| --- | --- |
| 导入与待审 | import.stage、queue.get、queue.preview、search.pending |
| 分析与提案 | analysis.record、proposal.create、proposal.revise、proposal.get、candidate.get |
| 审核 | review.list、review.get、review.action |
| 资产 | asset.get、asset.preview、search.assets、search.related、search.explain |
| 概念 | search.concepts |
| 知识 | knowledge.get、knowledge.search |
| Prompt | prompt.get、prompt.list、prompt.render |
| 视觉 | visual.index、visual.search |
| 维护 | search.rebuild、operations.recover |

不公开 asset.delete、反归档、concept.update/merge、approval.record、commit.execute 或任意 SQL。

## 导入

`import.stage` 必须提供唯一 `operation_id` 和本机普通文件 `source_path`，可提供 `batch_id` 与 source 元数据。网页使用 `POST /api/import` 上传原始文件体；可带 URL 编码 `X-File-Name`、`X-Batch-Id`、`X-Operation-Id`。

相同 operation_id 与相同正文返回原结果；同 ID 不同正文返回 IDEMPOTENCY_CONFLICT。网页上传使用稳定内部路径，响应丢失后可以重放同一操作。

## 提案

当前支持：

- asset.create / asset.update / asset.archive
- concept.create
- knowledge.create / update / archive
- prompt.create / update / archive

asset.create 绑定 queue_item_id 且 target_revision=0；update/archive 绑定正式对象 ID 和当前 target_revision。修订必须保持同一 proposal_id、操作和目标对象，revision 只能是当前版本的下一版。

提案正文经过对应 JSON Schema 校验后计算规范化 SHA-256。Schema 通过不代表已经审核或提交。

## 审核

所有动作要求非空 `operation_id` 与 `confirmed:true`。approve、request_changes、reject 还必须绑定实际 `review.get` 返回的：

```json
{
  "command": "review.action",
  "operation_id": "review_unique",
  "action": "approve",
  "confirmed": true,
  "proposal_id": "proposal_actual",
  "revision": 1,
  "proposal_hash": "sha256:actual",
  "file_hash": "sha256:actual-asset-only",
  "target_revision": 0
}
```

非资产提案不伪造 file_hash。哈希、revision、目标或文件指纹变化时返回错配错误，旧确认不能复用。`confirmed` 不证明调用者身份。

defer_current 绑定 queue_item_id；defer_remaining_batch 绑定 batch_id，不要求先存在分析或提案。

## 搜索

`search.assets` 只返回 active 资产，支持 must、should、must_not、filters、expand_narrower、expand_related 和 limit。`text` 等价于一个 must 文本条件。结果不会自动放宽约束。

`search.pending` 只返回 pending/in_review/deferred 队列基础信息。未审核提案正文通过 proposal/review 详情读取，不进入正式搜索。

## 媒体

asset.preview 与 queue.preview 返回稳定 ID、MIME、file_hash 和服务解析的只读语义路径。WebUI 使用 `/media?kind=asset|queue&id=...`，服务读取前复验哈希。接口不接受任意媒体路径，也不提供操作系统级身份隔离。

## Prompt 与 Vision

prompt.render 只接受正式 prompt_id 和已声明变量，返回确定性文本，不执行表达式。

visual.search 必须且只能提供 asset_id 或 queue_item_id。macOS helper 不可用或 Windows 平台返回 CAPABILITY_UNAVAILABLE；相似结果不写入正式标签、关系或知识。

## 主要错误码

| 错误码 | 含义 |
| --- | --- |
| VALIDATION_FAILED | 字段、JSON、Schema、操作或目标不合法 |
| CONFIRMATION_REQUIRED | 审核缺少显式 confirmed=true |
| IDEMPOTENCY_CONFLICT | 相同 operation_id 对应不同请求 |
| STALE_PROPOSAL | 提案 revision、摘要或目标已变化 |
| TARGET_REVISION_CONFLICT | 正式对象 revision 已变化 |
| HASH_MISMATCH | 原图、提案或媒体指纹不一致 |
| DEPENDENCY_UNRESOLVED | 候选概念尚未落实 |
| CAPABILITY_UNAVAILABLE | 当前平台或安装不提供该能力 |
| OPERATION_NOT_SUPPORTED | 当前版本明确不提供该操作 |
| RECOVERY_REQUIRED | 操作未完成，需要恢复或人工处理 |
