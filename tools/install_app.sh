#!/bin/bash
# Builds "Scout Advancement Tool.app" in ~/Applications so the tool shows up in Launchpad and
# Spotlight. The app is just a launcher: it runs the code in this repo, so re-run this script
# only if the repo moves.
#
#   tools/install_app.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Applications/Scout Advancement Tool.app"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "→ App icon"
ICONSET="$WORK/AppIcon.iconset"; mkdir -p "$ICONSET"
swift "$REPO/tools/make_icon.swift" "$WORK/icon.png" 2>/dev/null
for s in 16 32 128 256 512; do
  sips -z $s $s "$WORK/icon.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$WORK/icon.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$WORK/AppIcon.icns"

echo "→ App bundle"
STAGE="$WORK/Scout Advancement Tool.app"
mkdir -p "$STAGE/Contents/MacOS" "$STAGE/Contents/Resources"
cp "$WORK/AppIcon.icns" "$STAGE/Contents/Resources/"
cat > "$STAGE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Scout Advancement Tool</string>
  <key>CFBundleDisplayName</key><string>Scout Advancement Tool</string>
  <key>CFBundleIdentifier</key><string>com.alindeman.scoutadvancement</string>
  <key>CFBundleExecutable</key><string>scout-advancement</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <!-- no window of its own: the tool runs in the browser, and Quit in the page stops it -->
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST

cat > "$STAGE/Contents/Resources/launch.sh" <<LAUNCHER
#!/bin/bash
# Starts the Scout Advancement Tool in the background and opens it in the browser.
REPO="$REPO"
LOG="\$HOME/Library/Logs/Scout Advancement Tool.log"
alert() { osascript -e "display alert \"Scout Advancement Tool\" message \"\$1\" as critical" >/dev/null 2>&1; }

if [ ! -f "\$REPO/app/server.py" ]; then
  alert "Can't find the tool at \$REPO. If it's on an external drive, plug the drive in and try again."
  exit 1
fi
if ! cd "\$REPO" 2>/dev/null || ! ls app/server.py >/dev/null 2>&1; then
  alert "macOS blocked access to the drive with the tool on it. Open System Settings → Privacy & Security → Files & Folders, turn on Removable Volumes for Scout Advancement Tool, then open the app again."
  exit 1
fi
PY=/usr/bin/python3
[ -x "\$PY" ] || PY="\$(command -v python3)"

if ! "\$PY" -c "import sys; sys.path.insert(0, 'app/vendor'); import reportlab" 2>/dev/null; then
  osascript -e 'display notification "Installing the PDF library (one time only)…" with title "Scout Advancement Tool"' >/dev/null 2>&1
  if ! "\$PY" -m pip install --quiet --disable-pip-version-check --upgrade --target app/vendor "reportlab==4.2.5" >>"\$LOG" 2>&1; then
    alert "Couldn't install the PDF library. Check your internet connection and try again."
    exit 1
  fi
fi

echo "--- \$(date) ---" >>"\$LOG"
if ! "\$PY" app/server.py >>"\$LOG" 2>&1; then
  alert "The tool stopped with a problem: \$(tail -n 2 "\$LOG" | tr -d '"' | tr '\n' ' ') (Details: ~/Library/Logs/Scout Advancement Tool.log)"
  exit 1
fi
LAUNCHER
chmod +x "$STAGE/Contents/Resources/launch.sh"
# A compiled launcher (not the script itself) so macOS asks for drive access as this app
clang -O2 -o "$STAGE/Contents/MacOS/scout-advancement" "$REPO/tools/launcher.c" \
  -DSCRIPT="\"$APP/Contents/Resources/launch.sh\""
# Ad-hoc signature gives the app a stable identity for its permissions
codesign --force --sign - --identifier com.alindeman.scoutadvancement "$STAGE" 2>/dev/null

mkdir -p "$HOME/Applications"
rm -rf "$APP"
mv "$STAGE" "$APP"
# Tell Launchpad/Spotlight about it right away
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true

echo "✓ Done. Open \"Scout Advancement Tool\" from Launchpad or Spotlight (⌘-Space)."
