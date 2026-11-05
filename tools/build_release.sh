#!/bin/bash
# Builds a self-contained "Scout Advancement Tool.app" and packages it as a .dmg for a GitHub
# Release. Unlike tools/install_app.sh, the app carries its own copy of app/ and the PDF library,
# so it doesn't need this repo on the Mac it runs on. It still uses macOS's /usr/bin/python3.
#
#   tools/build_release.sh 1.0.0      ->  dist/Scout-Advancement-Tool-1.0.0.dmg
#
# Needs internet (to download the PDF library) and the Command Line Developer Tools
# (clang, swift). The app is ad-hoc signed only, so people opening it the first time have to
# approve it in System Settings -> Privacy & Security.
set -euo pipefail

VERSION="${1:-1.0.0}"
VERSION="${VERSION#v}"
NAME="Scout Advancement Tool"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$REPO/dist"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Library versions. Pillow 11.3 is the last release with wheels for Python 3.9 (macOS's python3).
REPORTLAB="reportlab==4.2.5"
PILLOW="pillow==11.3.0"
CHARDET="chardet==5.2.0"
PYVER="3.9"

APP="$WORK/stage/$NAME.app"
RES="$APP/Contents/Resources"
mkdir -p "$APP/Contents/MacOS" "$RES"

echo "→ App icon"
ICONSET="$WORK/AppIcon.iconset"; mkdir -p "$ICONSET"
swift "$REPO/tools/make_icon.swift" "$WORK/icon.png" 2>/dev/null
for s in 16 32 128 256 512; do
  sips -z $s $s "$WORK/icon.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$WORK/icon.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$RES/AppIcon.icns"

echo "→ App code"
mkdir -p "$RES/app"
cp "$REPO/app/server.py" "$REPO/app/advancement.py" "$REPO/app/pdf_report.py" \
   "$REPO/app/index.html" "$REPO/app/requirements.json" "$RES/app/"

echo "→ PDF library (Apple silicon and Intel)"
# Pillow has compiled parts, so each Mac type gets its own copy; launch.sh picks the right one.
for pair in arm64:macosx_11_0_arm64 x86_64:macosx_10_10_x86_64; do
  arch="${pair%%:*}"; plat="${pair#*:}"
  /usr/bin/python3 -m pip install --quiet --disable-pip-version-check --no-compile \
    --target "$RES/vendor-$arch" --platform "$plat" --python-version "$PYVER" \
    --implementation cp --only-binary=:all: "$REPORTLAB" "$PILLOW" "$CHARDET"
  rm -rf "$RES/vendor-$arch/bin"
done
find "$RES" -name __pycache__ -type d -prune -exec rm -rf {} +

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>$NAME</string>
  <key>CFBundleDisplayName</key><string>$NAME</string>
  <key>CFBundleIdentifier</key><string>com.alindeman.scoutadvancement</string>
  <key>CFBundleExecutable</key><string>scout-advancement</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <!-- no window of its own: the tool runs in the browser, and Quit in the page stops it -->
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST

cat > "$RES/launch.sh" <<'LAUNCHER'
#!/bin/bash
# Starts the bundled Scout Advancement Tool in the background and opens it in the browser.
RES="$(cd "$(dirname "$0")" && pwd)"
LOG="$HOME/Library/Logs/Scout Advancement Tool.log"
SUPPORT="$HOME/Library/Application Support/Scout Advancement Tool"
alert() { osascript -e "display alert \"Scout Advancement Tool\" message \"$1\" as critical" >/dev/null 2>&1; }

# The app is read-only once it's in Applications, so Python must not write cache files into it.
export PYTHONDONTWRITEBYTECODE=1
PY=/usr/bin/python3

# On a Mac without the Command Line Developer Tools, /usr/bin/python3 only offers to install them.
if ! "$PY" -c "" >/dev/null 2>&1; then
  alert "This tool needs Python 3, which comes with Apple's free Command Line Developer Tools. If macOS offered to install them, click Install, wait for it to finish, then open Scout Advancement Tool again."
  exit 1
fi

# Use the PDF library built for this Mac's chip. If it doesn't load (for example, a future macOS
# with a newer Python), install a matching copy once into Application Support.
case "$("$PY" -c 'import platform; print(platform.machine())')" in
  arm64) VENDOR="$RES/vendor-arm64" ;;
  *)     VENDOR="$RES/vendor-x86_64" ;;
esac
if ! PYTHONPATH="$VENDOR" "$PY" -c "import reportlab.pdfgen.canvas, PIL.Image" >/dev/null 2>&1; then
  VENDOR="$SUPPORT/vendor"
  if ! PYTHONPATH="$VENDOR" "$PY" -c "import reportlab.pdfgen.canvas, PIL.Image" >/dev/null 2>&1; then
    osascript -e 'display notification "Installing the PDF library (one time only)…" with title "Scout Advancement Tool"' >/dev/null 2>&1
    mkdir -p "$SUPPORT"
    if ! "$PY" -m pip install --quiet --disable-pip-version-check --upgrade --target "$VENDOR" "reportlab==4.2.5" >>"$LOG" 2>&1; then
      alert "Couldn't install the PDF library. Check your internet connection and try again."
      exit 1
    fi
  fi
fi
export PYTHONPATH="$VENDOR"

echo "--- $(date) ---" >>"$LOG"
if ! "$PY" "$RES/app/server.py" >>"$LOG" 2>&1; then
  alert "The tool stopped with a problem: $(tail -n 2 "$LOG" | tr -d '"' | tr '\n' ' ') (Details: ~/Library/Logs/Scout Advancement Tool.log)"
  exit 1
fi
LAUNCHER
chmod +x "$RES/launch.sh"

echo "→ Launcher (Apple silicon + Intel)"
clang -O2 -arch arm64 -arch x86_64 -mmacosx-version-min=12.0 \
  -o "$APP/Contents/MacOS/scout-advancement" "$REPO/tools/launcher.c"

echo "→ Signing (ad-hoc)"
codesign --force --deep --sign - --identifier com.alindeman.scoutadvancement "$APP"
codesign --verify --deep --strict "$APP"

echo "→ Disk image"
ln -s /Applications "$WORK/stage/Applications"
mkdir -p "$DIST"
DMG="$DIST/Scout-Advancement-Tool-$VERSION.dmg"
rm -f "$DMG"
hdiutil create -quiet -volname "$NAME" -srcfolder "$WORK/stage" -ov -format UDZO "$DMG"

echo "✓ Built $DMG ($(du -h "$DMG" | cut -f1))"
