#!/bin/bash
# Double-click this file to start the Scout Advancement Tool. It opens in your web browser.
cd "$(dirname "$0")" || exit 1

PY=/usr/bin/python3
[ -x "$PY" ] || PY="$(command -v python3)"
if [ -z "$PY" ]; then
  echo "Python 3 was not found. macOS will offer to install the Command Line Developer Tools; accept, then double-click this file again."
  xcode-select --install 2>/dev/null
  read -r -p "Press Return to close."
  exit 1
fi

# The PDF library (reportlab) lives in app/vendor. Install or repair it if it can't be imported.
if ! "$PY" -c "import sys; sys.path.insert(0, 'app/vendor'); import reportlab" 2>/dev/null; then
  echo "One-time setup: installing the PDF library (needs internet)..."
  if ! "$PY" -m pip install --quiet --disable-pip-version-check --upgrade --target app/vendor "reportlab==4.2.5"; then
    echo "Setup failed. Check your internet connection and double-click Start Scout Tool again."
    read -r -p "Press Return to close."
    exit 1
  fi
fi

"$PY" app/server.py || read -r -p "Press Return to close."
