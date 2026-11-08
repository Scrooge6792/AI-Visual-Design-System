# Phase 0 技术可行性记录

更新：2026-11-07（Asia/Shanghai）。状态：**通过**。

## 已有证据

- 环境：macOS 26.7.2（arm64），Apple Swift 6.4.2，Xcode 27.2；未安装第三方依赖。
- SQLite：系统 CLI 为 3.54.1；应用探针实际链接 3.51.0。应用探针确认 FTS5、`journal_mode=DELETE`、`synchronous=FULL`、`foreign_keys=ON`、`busy_timeout=5000` 可用，“雪景”“逆光”两字查询均命中。
- 原生图像：AppKit 可生成/解码 PNG；V1 原型通过 `/usr/bin/sips` 检查真实格式与尺寸。Phase 0 测试图为 64×64 PNG、左蓝右黄，SHA-256 为 `5c417ee3774a35ab3b5ed9ecd22e60f5c88bde5e91bc9553b8e63a61a5eec379`。
- 账号视觉链路：Codex Desktop 现有账号工具读取该测试图，输出“左蓝、右黄、垂直二分”的结构化草案，并通过受控 CLI 写入测试 Vault 的 `analysis_runs` 与待审提案；未使用模型 API、未新增费用，未上传素材库。
- Touch ID：沙盒外 `LocalAuthentication` 检测 `deviceOwnerAuthenticationWithBiometrics=true`、Touch ID 类型可用。沙盒内同一探针无法连接认证服务，说明认证必须留在沙盒外受信 Reviewer。
- IPC/权限：Codex 沙盒不能连接或创建 Unix Socket，也不能直接写计划中的正式 Vault。沙盒外最小 Core 只暴露受控 JSON 命令；Reviewer 命令同时绑定已安装可执行文件的绝对路径与 SHA-256。Agent CLI 伪造相同批准载荷被明确拒绝为 `UNAUTHORIZED_REVIEW`。
- Reviewer：原生 AppKit Reviewer 已显示最终图片和提案；所有会改变审核状态的按钮都先要求 Touch ID。Agent 没有执行按钮动作，符合“正式批准必须来自用户”的边界。
- 最小数据验证：6 个标准库自动化测试通过，覆盖暂存幂等/冲突、跨重开稍后与只读原图、正式索引隔离、五项绑定错配、候选依赖阻断、旧批准失效、归档不删原图。

## 完成结果

1. 用户在 Reviewer 窗口点“批准”并完成 Touch ID；Core 记录可信 `review_event` 和 committed 操作，资产从 staged 变为 active，Agent 未执行 UI 动作。
2. 关闭 Core，将 `/tmp/avds-v1-test-vault` 复制到 `/tmp/avds-v1-test-vault-copy` 后重开；同一 asset_id 的详情、原图、相对对象路径和正式搜索均可用。
3. 在复制后的 Vault 重放原 `phase0-import-1` 请求，返回原 queue_item_id/asset_id/file_hash，没有重复建资产；错摘要和旧修订自动化测试均拒绝提交。
4. 加载修正版 Core 后，“蓝黄”两字查询通过正式文本子串回退命中已批准资产。

Phase 0 完成条件全部满足，可以进入 Phase 1。测试 Vault 仍位于 `/tmp`，不是用户真实 Vault。

## 已验证技术方向

- 标准库 Python Core/Agent CLI + 原生 Swift/AppKit Reviewer；SQLite 和 macOS 原生框架，无第三方生产依赖。
- Core 作为工作区外的受信进程持有 Vault 写权限；Agent 只调用安装后不可由工作区修改的受控 CLI。
- Reviewer 的可执行路径/摘要由 Core 固定校验，批准必须经过 Touch ID。安装或更新受信程序需要单独的用户授权，普通 Agent 请求不能替换它。

该方向不引入第三方生产依赖、云服务或新增费用。正式安装仍需保证受信运行文件位于 Agent 工作区外，且更新动作需要用户授权。
