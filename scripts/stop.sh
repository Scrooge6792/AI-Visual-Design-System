#!/bin/sh
set -eu
DOMAIN="gui/$(/usr/bin/id -u)"
/bin/launchctl bootout "$DOMAIN/local.avds.core"
echo "AI Visual Design Core 已停止；现在可以关闭 Reviewer 并复制完整 Vault。"
