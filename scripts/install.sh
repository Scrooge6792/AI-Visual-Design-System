#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
USER_HOME=${HOME:?HOME is required}
RUNTIME="$USER_HOME/Library/Application Support/AIVisualDesign"
APP="$USER_HOME/Applications/AVDS Reviewer.app"
VAULT=${1:-"$USER_HOME/Pictures/VisualAssetVault"}
SOCKET="$RUNTIME/core.sock"
PLIST="$USER_HOME/Library/LaunchAgents/local.avds.core.plist"

sh "$ROOT/scripts/build.sh"
mkdir -p "$RUNTIME/bin" "$RUNTIME/logs" "$USER_HOME/Applications" "$USER_HOME/Library/LaunchAgents"
/usr/bin/ditto "$ROOT/src" "$RUNTIME/src"
/usr/bin/install -m 0555 "$ROOT/bin/avds" "$RUNTIME/bin/avds"
/usr/bin/install -m 0555 "$ROOT/bin/avds-review" "$RUNTIME/bin/avds-review"
/usr/bin/install -m 0555 "$ROOT/bin/avds-web" "$RUNTIME/bin/avds-web"
/usr/bin/install -m 0555 "$ROOT/.build/avds-vision" "$RUNTIME/bin/avds-vision"
/usr/bin/install -m 0555 "$ROOT/scripts/start.sh" "$RUNTIME/bin/avds-start"
/usr/bin/install -m 0555 "$ROOT/scripts/stop.sh" "$RUNTIME/bin/avds-stop"
/usr/bin/ditto "$ROOT/.build/AVDS Reviewer.app" "$APP"
REVIEWER="$APP/Contents/MacOS/AVDSReviewer"
REVIEWER_HASH=$(/usr/bin/shasum -a 256 "$REVIEWER" | /usr/bin/awk '{print $1}')
/usr/bin/python3 "$ROOT/scripts/render_launch_agent.py" "$RUNTIME" "$VAULT" "$REVIEWER" "$REVIEWER_HASH" "$SOCKET" "$PLIST"
/bin/launchctl bootout "gui/$(/usr/bin/id -u)/local.avds.core" 2>/dev/null || true
attempt=0
while /bin/launchctl print "gui/$(/usr/bin/id -u)/local.avds.core" >/dev/null 2>&1 && test "$attempt" -lt 20; do
  /bin/sleep 0.1
  attempt=$((attempt + 1))
done
if test -S "$SOCKET"; then
  /bin/rm -f "$SOCKET"
fi
if ! /bin/launchctl bootstrap "gui/$(/usr/bin/id -u)" "$PLIST"; then
  /bin/sleep 0.5
  /bin/launchctl bootstrap "gui/$(/usr/bin/id -u)" "$PLIST"
fi
/bin/launchctl enable "gui/$(/usr/bin/id -u)/local.avds.core"
echo "runtime=$RUNTIME"
echo "vault=$VAULT"
echo "reviewer=$APP"
echo "cli=$RUNTIME/bin/avds"
