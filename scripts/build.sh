#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD="$ROOT/.build"
APP="$BUILD/AVDS Reviewer.app"
mkdir -p "$BUILD/module-cache" "$APP/Contents/MacOS"
xcrun swiftc -module-cache-path "$BUILD/module-cache" "$ROOT/reviewer/main.swift" \
  -framework AppKit -framework LocalAuthentication -o "$APP/Contents/MacOS/AVDSReviewer"
xcrun swiftc -module-cache-path "$BUILD/module-cache" "$ROOT/vision/main.swift" \
  -framework Vision -o "$BUILD/avds-vision"
cp "$ROOT/reviewer/Info.plist" "$APP/Contents/Info.plist"
codesign --force --sign - --options runtime --timestamp=none "$APP"
chmod +x "$ROOT/bin/avds" "$ROOT/bin/avds-core" "$ROOT/bin/avds-review" "$ROOT/bin/avds-web" "$ROOT/scripts/install.sh" "$ROOT/scripts/start.sh" "$ROOT/scripts/stop.sh"
echo "$APP"
