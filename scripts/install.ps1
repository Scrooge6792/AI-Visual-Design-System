$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
py -3 -m venv (Join-Path $ProjectDir '.venv')
if ($LASTEXITCODE -ne 0) { throw '需要 Python 3.11 或更新版本。' }
$PythonExe = Join-Path $ProjectDir '.venv\Scripts\python.exe'
& $PythonExe -m pip install -e $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '安装失败。请检查 Python 和网络。' }
Write-Host '安装完成。运行 .\avds.cmd config set vault <新Vault路径>，再运行 .\avds.cmd serve --open。'
Write-Host '如需在任意目录使用 avds，请先明确授权 Agent 按当前系统配置用户级全局命令。'
