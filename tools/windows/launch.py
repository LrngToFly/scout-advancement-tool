"""Entry point for the packaged Windows app (built by .github/workflows/windows.yml).

The .exe has no console window, so output goes to a log file in
%LOCALAPPDATA%\\Scout Advancement Tool and problems are shown in a message box.
"""
import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Scout Advancement Tool"
LOG = LOG_DIR / "log.txt"


def alert(message):
    ctypes.windll.user32.MessageBoxW(None, message, "Scout Advancement Tool", 0x10)  # 0x10 = error icon


def last_lines(n=3):
    try:
        return " ".join(LOG.read_text(encoding="utf-8").strip().splitlines()[-n:])
    except OSError:
        return ""


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOG.exists() and LOG.stat().st_size > 1_000_000:
        LOG.unlink()
    sys.stdout = sys.stderr = open(LOG, "a", encoding="utf-8", buffering=1)
    print(f"--- {datetime.now()} ---")
    try:
        import server
        server.main()
    except SystemExit as e:
        if e.code:
            alert(f"The tool couldn't start. {last_lines(2)}\n\nDetails: {LOG}")
    except Exception:
        traceback.print_exc()
        alert(f"The tool stopped with a problem: {last_lines(1)}\n\nDetails: {LOG}")


if __name__ == "__main__":
    main()
