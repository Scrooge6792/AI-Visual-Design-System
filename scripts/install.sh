#!/bin/sh
# Install only into this checkout. Never update the legacy trusted installation.
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${AVDS_PYTHON:-python3}
"$PYTHON_BIN" -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/python" -m pip install -e "$PROJECT_DIR"
if [ "$(uname -s)" = Darwin ] && command -v xcrun >/dev/null 2>&1; then
  sh "$PROJECT_DIR/scripts/build.sh" || echo "Apple Vision 构建未完成；资料管理仍可用，avds doctor 可查看能力。"
fi
echo "安装完成。先运行 .venv/bin/avds init --vault <新Vault路径>，再运行 .venv/bin/avds serve --open。"
