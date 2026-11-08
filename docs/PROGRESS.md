# 项目进度

更新：2026-11-08。

## 当前交付：2.0.0 跨平台单服务源码

- 授权：Python；一个长期运行本机 HTTP 服务；Agent / WebUI 完整入口；取消 Touch ID 和独立 Reviewer 身份门禁；macOS 自动可选 Vision，Windows 不使用；公开源码分发准备，不做数据同步或交流。
- 完成：配置（命令行 > 环境变量 > JSON）、Vault 操作系统锁、统一 init/doctor/serve/status/open/stop、HTTP 业务路由、CLI 短连接、同源会话/令牌/Host/CSP 防护、浏览器图片上传、提案表单/修订、最终内容预览与审核、全部公开操作界面。
- 完成：Windows 原生 PNG/JPEG 解码适配；macOS 图像解码 / Apple Vision 适配；平台能力探测；移除运行链路的 Unix Socket、libproc、Touch ID、launchd 和 Unix chmod 硬依赖。无新增第三方生产依赖。
- 正确性修复：旧 autocommit 连接中的 `with db` 没有显式开始事务；现使用 BEGIN IMMEDIATE，提交异常回滚审核/正式记录。新增失败注入检查。
- 修订修复：资产、知识/Prompt 与概念修订均保持原操作和目标身份；Schema 校验失败不会使旧版本失效。浏览器重复上传以稳定内部路径重放相同 operation_id，不因临时文件名变化而冲突。本机 HTTP 启动不做反向 DNS 查询。
- 保留：版本与哈希绑定、原图保护、持久稍后、正式索引隔离、知识/Prompt 审核与渲染、候选概念顺序提交、幂等与恢复、DELETE/FULL。
- 必要检查：20 个 Python 测试在 macOS 临时 Vault 全部通过，包含 HTTP 单服务/双入口审核、同源与 Host 拒绝、浏览器上传及幂等重放、提案修订目标锁定、配置优先级、Windows 适配模拟和实际 Apple Vision 比较。受限环境不能监听端口，HTTP/实际 Vision 检查在获准的本机测试进程运行。
- 限制：没有 Windows 实机，不能宣称 Windows 10/11 实际运行已验证。Windows 只支持系统可解码的 PNG/JPEG，不提供 Vision；Windows 不提供目录 fsync 的等价保证。新界面产品体验由用户验收。
- 静态检查：Python、前端 JavaScript、shell 语法和 git diff --check 通过。Playwright CLI 未在当前环境缓存，受限网络无法拉取；未执行真实浏览器点击流程，不将 HTTP 测试冒充浏览器验收。
- 生命周期冒烟：在独立临时目录实际运行 CLI init → doctor → serve → status → stop，全部成功；服务正常退出，运行状态文件已清理。
- 安装检查：`sh scripts/install.sh` 已在项目内创建隔离 `.venv`、完成 editable 安装并构建 Apple Vision helper；没有写入旧运行目录或真实 Vault。首次获取 setuptools 构建工具需要网络，运行时没有第三方生产依赖。
- 版本说明：Python 包、模块、CLI、服务状态与主文档统一为应用 2.0.0；JSON 接口契约独立保持 1.0，V0.8/V1 标记为历史来源和旧实现规格。
- 未执行：没有安装或更新旧受信运行目录、Reviewer App 或真实 Vault；没有停止旧运行实例；没有创建/发布 GitHub 仓库或做真实素材迁移。
- 下一步：用户按 README 在独立的新 Vault 试用；Windows 用户环境完成实际安装/原生解码验证后再记录结果；真实库升级需要用户单独授权。

## 历史

2026-11-07 的 V1 / Phase 0～3 及后续 Phase 4～6 曾使用受信 Core、独立 Reviewer、Touch ID 与只读 WebUI，已有安装和测试记录见 PHASE0.md。该审批与部署结构已由本次明确决策覆盖，旧结果不证明新版跨平台能力。来源材料继续保留；不再恢复“仅文档、尚未开发”的旧状态。
