# AI Visual Design System

当前源码版本：**1.0.0**。接口契约版本为 `1.0`，与应用发布版本分别演进。这是开始正式使用的首个应用版本。

本机视觉素材、知识与 Prompt 资料库。Python 单服务同时提供 Agent CLI 和浏览器界面：保存图片、起草提案、审核提交、持久稍后、搜索与预览都可从任一入口完成。默认只监听本机，不提供账号体系、云部署、数据同步或用户间交流。

2026-11-08 用户确认的新架构覆盖旧版 Unix Socket、独立 Reviewer 和 Touch ID 门禁。审核仍绑定具体提案版本、内容摘要、原图指纹与目标修订，并要求明确确认；**不再声称 Agent 与用户之间存在审批身份隔离**。`confirmed=true` 是工作流确认字段，不是身份凭据。

当前状态：**1.0.0 初版源码已经开发完成，并通过 macOS 自动化回归与本机 Apple Vision 检查**。尚未完成的发布验收是 Windows 10/11 实机验证，以及浏览器中的人工操作体验验收；因此不能表述为“所有目标平台均已验收完成”。

## 安装

需要 Python 3.11 或更新稳定版，且其 SQLite 包含 FTS5。运行时只用 Python 标准库和系统原生能力，没有第三方生产依赖、模型 API 或新增订阅。首次建立虚拟环境时，pip 可能需要联网获取 setuptools 构建工具。下面的安装只写当前源码目录的 `.venv` / `.build`，不注册开机服务，不改旧版受信安装或真实 Vault。

macOS，在取得源码后的项目目录执行：

```sh
sh scripts/install.sh
./bin/avds init --vault "$HOME/Pictures/MyVisualVault"
./bin/avds doctor
./avds config show
./avds serve --open
```

安装脚本使用 `python3`；需要指定解释器时设置 `AVDS_PYTHON=/完整路径/python3`。Apple Vision helper 会尝试使用已安装的 Xcode Command Line Tools 构建；没有 Swift 编译工具时普通资料管理仍可用。补装系统编译工具后运行 `sh scripts/build.sh` 并重启服务即可自动启用 Vision。不自动安装系统工具。

Windows 10/11，在 PowerShell 的项目目录执行（安装好包含 `py` 启动器的 Python）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
.\.venv\Scripts\avds.exe init --vault "$env:USERPROFILE\Pictures\MyVisualVault"
.\.venv\Scripts\avds.exe doctor
.\avds.cmd config show
.\avds.cmd serve --open
```

Windows 使用系统 Windows PowerShell / System.Drawing 解码 PNG、JPEG，不使用 Apple Vision。macOS 使用系统图像解码器，支持 PNG、JPEG，以及系统实际可解码的 HEIC/WebP。不要仅改扩展名转换格式；无法解码时返回错误，原文件保留。

### 可选：配置全局 `avds` 命令

安装完成后，协助安装的 Agent **必须先询问用户是否需要配置全局 `avds` 命令**。只有用户明确批准后，才能修改用户环境；拒绝或没有明确答复时，macOS/Linux 继续使用项目根目录的 `./avds`，Windows 使用 `.\avds.cmd`。

获批后，Agent 应先检测操作系统、当前 shell 和现有 PATH，再采用对应的用户级配置：

- macOS/Linux：优先在已经位于 PATH 的 `~/.local/bin` 中创建指向项目根目录 `avds` 的符号链接；如果该目录不在 PATH，只向当前用户的 shell 配置加入一次，不重复追加。
- Windows：创建调用项目根目录 `avds.cmd` 的用户级命令包装器，并将其所在目录加入当前用户 PATH；默认不修改系统级 PATH。
- 不要求管理员权限，不写 `/usr/local/bin` 等系统目录；配置前检查是否存在同名命令，不能静默覆盖。
- 完成后在新 shell 环境验证 `command -v avds`/`Get-Command avds` 和 `avds --version`。项目被移动或删除后，应重新配置或移除失效入口。

根目录 `./avds` 是完整项目命令 `./bin/avds` 的精简快捷层；全局 `avds` 必须指向这个根目录快捷层，两者的行为和帮助完全一致。它们只提供版本、启动、状态和用户配置，不复制 Vault、不自动启动后台服务，也不改变配置优先级。配置完成后，可在任意目录运行 `avds serve --open`。

`serve` 是唯一长期运行的进程，保持这个终端开启。Agent CLI 每次请求结束即退出；浏览器无需单独启动 WebUI 服务。默认不后台运行、不自动启动。安装脚本不会执行 `init` 或打开真实库。

已有配置时 `init` 不覆盖；可编辑配置，或以 `--config 新路径` 初始化另一套配置。源码升级后重启同一服务即可。旧版用户应先由自己停止旧 Core / Reviewer，再让新版指向原 Vault；本次开发没有安装、更新、停止或迁移旧版运行实例。

## 配置与日常使用

默认配置文件为 `~/.avds/config.json`，示例：

```json
{
  "vault": "/your/path/VisualVault",
  "host": "127.0.0.1",
  "port": 8765,
  "open_browser": false,
  "visual_provider": "auto"
}
```

Windows JSON 路径使用 `C:/Users/yourname/Pictures/VisualVault` 或双反斜杠。优先级：命令行 > `AVDS_VAULT/HOST/PORT/OPEN_BROWSER/VISUAL_PROVIDER` 环境变量 > 配置文件 > 内置默认值。`--config` / `AVDS_CONFIG` 选择配置文件。`host` 仅接受 `127.0.0.1` 或 `localhost`；`port=0` 由系统分配。视觉提供者为 `auto`、`none` 或 `apple-vision`，Windows 中 Apple Vision 始终不可用。

根目录 `./avds` 与全局 `avds` 是面向普通用户的相同快捷入口：

```sh
./avds --version
./avds --help
./avds config show
./avds config get port
./avds config set port 8877
./avds config set vault "$HOME/Pictures/MyVisualVault"
./avds serve --open
./avds status
```

`config show` 打印配置文件位置以及 Vault、host、port、是否打开浏览器和视觉提供者；`config get` 查看单项，`config set` 一次只设置一个用户配置。端口冲突会报错，不偷偷更改端口。同一 Vault 仍只允许一个服务。服务在前台运行，回到服务终端按 `Control-C` 即可停止。

`./avds -h` 与 `./avds --help` 只打印上述核心命令及一句话用途说明；全局命令配置完成后可省略 `./`。完整业务命令仍保留在项目目录的 `./bin/avds`，供 Agent 和维护操作使用。

## Agent 与网页工作流

可直接要求 Agent：“保存这些图片，先全部稍后”“为这张图起草描述”“查看最终提案，我确认后批准”“搜索已批准的逆光素材”。Agent 与网页都通过同一服务调用业务操作，不直接执行 SQL。网页支持文件选择、提案表单、完整内容预览、逐项审核、退回修改、拒绝、两种稍后，以及全部公开操作接口。

CLI 统一返回 JSON。含中文、多行内容或 PowerShell 引号复杂时，优先将载荷存为 UTF-8 文件并传 `--json-file`：

```sh
./bin/avds import.stage --json-file import.json
./bin/avds proposal.create --json-file proposal.json
./bin/avds review.list
./bin/avds review.get --json-file selected-proposal.json
./bin/avds review.action --json-file confirmed-review.json
./bin/avds search.assets --json '{"text":"逆光"}'
```

导入参数使用 `source_path`、唯一 `operation_id` 和可选 `batch_id/source`。提案保存后，先读取展示最终版本再确认审核。审核须提交唯一 `operation_id`、`action`、`confirmed:true`、`proposal_id`、整数 `revision`、`proposal_hash`、`target_revision`，资产还需 `file_hash`。五项绑定来自服务返回，不能猜测；批准动作在同一服务内部提交。新版本必须重新审核；新概念先批准，再修订资产引用。`commands` 列出公开命令，详见 [契约](docs/CONTRACTS.md)。

正式检索只包含已审核有效内容；草案、待审图片与未批准知识均隔离。知识以版本化 Markdown 保存，Prompt 以版本化 JSON 保存，模板只替换已声明变量，不执行代码。Apple Vision 的视觉距离仅是排序信号，缓存可以重建，不自动生成正式标签。

## 数据、恢复与限制

所有必要资料位于一个 Vault，内部使用稳定 ID 和相对路径；原图按 SHA-256 寻址，不因拒绝、归档或错误删除。SQLite 使用 DELETE / FULL / 外键 / 5000ms busy timeout。文件复制与数据库事务是分开的，保留幂等操作与恢复记录。Windows 提供文件 fsync 和同卷替换，Python 标准接口不能同步目录句柄，不能声称与 macOS 目录 fsync 完全等价。

备份时完成当前操作并在服务终端按 `Control-C`（Agent 也可在项目目录执行 `./bin/avds stop`），确认服务终端已退出，再通过 Finder / 文件资源管理器复制或压缩**整个 Vault**。不要只复制数据库，也不要运行中复制。恢复时将配置指向新目录；服务记录是临时状态，重新启动会更新。不提供在线快照、复杂容灾或自动备份。

不提供物理删除、反归档、概念更新/合并、复合原子批准、任意模板代码、云服务或跨用户数据交换。现有 Agent 账号的分析能力和额度由用户环境决定，耗尽时可以保存稍后；不会自动调用付费 API。

本次必要检查在 macOS 临时 Vault 执行；Windows 原生环境尚未实机验证，现有 Windows 检查是平台适配模拟与静态检查。源码已为公开分发提供安装说明，尚未创建或发布 GitHub 仓库。

## 项目文件

[需求](docs/REQUIREMENTS.md) · [架构](ARCHITECTURE.md) · [决策](DECISIONS.md) · [实施](IMPLEMENTATION.md) · [接口契约](docs/CONTRACTS.md) · [进度](docs/PROGRESS.md) · [来源覆盖](docs/SOURCE-COVERAGE.md) · [历史资料说明](docs/history/README.md)

必要回归：`PYTHONPATH=src python3 -m unittest discover -s tests -v`。Windows PowerShell 使用 `$env:PYTHONPATH='src'; py -3 -m unittest discover -s tests -v`。测试只创建临时资料；有原生 Vision 才运行真实视觉比较。
