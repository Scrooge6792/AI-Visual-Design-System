# AVDS 安装手册

本文是供 Agent 执行和供用户审查的安装操作手册。项目介绍与日常使用见 [README.md](README.md)。

## 1. 安装边界

- 只修改当前源码目录中的 `.venv`、`.build` 等安装产物，以及用户明确选择的配置位置和新 Vault。
- 不覆盖同名 `avds` 命令，不默认修改 PATH，不要求管理员权限，不注册系统服务或开机启动。
- 不停止、更新或迁移旧版 Core、Reviewer、旧受信安装或真实 Vault；这些操作需要用户另行明确授权。
- Vault 必须位于源码目录之外。测试使用临时 Vault，完成后不得将其作为用户真实资料库。
- 用户配置、Vault、素材、运行状态和本机私有文件不得提交到 Git；项目内临时配置应使用 `.avds/` 或 `*.avds.local.json` 等已忽略位置。

## 2. 获取源码

如果当前目录还不是本项目，先确认目标父目录不存在同名项目，再执行：

```sh
git clone https://github.com/Scrooge6792/AI-Visual-Design-System.git
cd AI-Visual-Design-System
```

如果目录已经存在，不要覆盖或重新克隆；先核对 `README.md`、`AGENTS.md` 和 Git 远程地址。

## 3. 安装前检查

1. 识别操作系统和当前 shell。
2. 确认 Python 3.11 或更新稳定版可用。
3. 检查是否已经存在 `avds` 同名命令；只记录结果，不覆盖。
4. 检查工作区是否已有用户配置、Vault 或未提交内容，不删除或改写它们。
5. macOS 如有 Swift 编译工具则构建 Apple Vision helper；缺失时普通资料管理仍可安装，但必须明确报告 Vision 不可用。
6. 运行时没有第三方生产依赖；首次创建虚拟环境时，pip 仍可能需要联网取得 `setuptools` 构建工具。网络不可用时保留原错误并向用户报告，不改用付费服务或未知安装源。

## 4. macOS 安装

在项目根目录执行：

```sh
sh scripts/install.sh
```

脚本默认使用 `python3`。需要指定解释器时：

```sh
AVDS_PYTHON=/完整路径/python3 sh scripts/install.sh
```

安装脚本创建项目内 `.venv`，并在能力可用时构建 `.build/avds-vision`。它不会创建真实 Vault、打开浏览器或修改全局命令。

选择一个位于项目目录之外的新 Vault，然后验证：

```sh
./avds config set vault "$HOME/Pictures/MyVisualVault"
./avds --version
./bin/avds doctor
./avds config show
./avds serve
```

保持服务终端运行，在另一个终端执行：

```sh
./avds status
```

确认成功后回到服务终端按 `Control-C` 停止。需要打开浏览器时重新执行 `./avds serve --open`。

## 5. Windows 10/11 安装

在 Windows PowerShell 的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

选择一个位于项目目录之外的新 Vault，然后验证：

```powershell
.\avds.cmd config set vault "$env:USERPROFILE\Pictures\MyVisualVault"
.\avds.cmd --version
.\.venv\Scripts\avds.exe doctor
.\avds.cmd config show
.\avds.cmd serve
```

保持服务窗口运行，在另一个 PowerShell 窗口执行：

```powershell
.\avds.cmd status
```

确认成功后回到服务窗口按 `Control-C` 停止。需要打开浏览器时重新执行 `.\avds.cmd serve --open`。

Windows 使用 PowerShell/System.Drawing 解码 PNG、JPEG，不使用 Apple Vision。Windows 10/11 尚未完成项目记录中的实机验收，安装 Agent 必须如实记录实际检查结果，不能用静态检查代替实机通过。

## 6. 全局 `avds` 命令

完成项目内安装后，Agent 必须询问用户是否需要配置全局 `avds`。没有明确同意时到此停止。

用户同意后：

1. 检查当前操作系统、shell、PATH 和已有同名命令。
2. 全局命令必须指向项目根目录的 `avds` / `avds.cmd`，不能指向完整业务 CLI。
3. macOS/Linux 优先使用已经在 PATH 中的用户级 `~/.local/bin`；Windows 使用用户级命令目录和用户 PATH。
4. 不写系统目录，不修改系统级 PATH，不要求管理员权限，不静默覆盖同名命令。
5. 在新 shell 中验证 `command -v avds` / `Get-Command avds` 和 `avds --version`。
6. 报告实际入口位置以及项目移动或删除后如何移除失效入口。

全局快捷入口只暴露版本、`serve`、`status` 和 `config show/get/set`。完整业务命令继续由项目内 `./bin/avds` 或 Python entry point 提供。

## 7. 配置和首次启动

默认用户配置位于 `~/.avds/config.json`，优先级为：命令行 > 环境变量 > 配置文件 > 内置默认值。首次试用不需要执行 `init`；`config set vault` 保存选择，第一次 `serve` 自动创建 Vault、SQLite 和必要目录。

可配置项包括 Vault、host、port、是否打开浏览器和视觉提供者。服务只接受 `127.0.0.1` 或 `localhost`，默认前台运行。同一 Vault 同时只允许一个服务。

## 8. 完成报告

安装 Agent 应向用户报告：

- 实际操作系统、Python 与 SQLite/FTS5 检查结果。
- 安装目录、配置文件位置和测试 Vault 位置。
- `avds --version`、doctor、serve 和 status 是否通过。
- Apple Vision 或 Windows 图像能力的实际状态。
- 未完成、跳过或只能静态检查的项目。
- 是否尚待用户决定配置全局 `avds`。

遇到错误时保留原始错误信息，不删除用户文件，不通过迁移真实数据来尝试修复安装。
