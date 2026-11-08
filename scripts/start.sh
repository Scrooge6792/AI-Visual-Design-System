#!/bin/sh
set -eu
USER_HOME=${HOME:?HOME is required}
PLIST="$USER_HOME/Library/LaunchAgents/local.avds.core.plist"
DOMAIN="gui/$(/usr/bin/id -u)"
/bin/launchctl bootstrap "$DOMAIN" "$PLIST" 2>/dev/null || /bin/launchctl kickstart -k "$DOMAIN/local.avds.core"
echo "AI Visual Design Core 已启动"
