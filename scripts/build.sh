#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$(uname -s)" != Darwin ]; then
  echo "Apple Vision 仅适用于 macOS；无需构建即可使用资料管理服务。"
  exit 0
fi
mkdir -p "$PROJECT_DIR/.build/module-cache"
xcrun swiftc -module-cache-path "$PROJECT_DIR/.build/module-cache" "$PROJECT_DIR/vision/main.swift" -framework Vision -o "$PROJECT_DIR/.build/avds-vision"
echo "Apple Vision helper 构建完成。"
