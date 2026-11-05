"""End-to-end check: start the tool, load a made-up CSV, generate every PDF, quit.

Uses a temporary data folder and its own port, so it never touches real scout data or a copy of
the tool that's already running.

    python tools/smoke_test.py python app/server.py                                   # from source
    python tools/smoke_test.py "dist/Scout Advancement Tool/Scout Advancement Tool.exe"  # Windows build
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"
SCOUTS = ["Alex Sample", "Blake Sample", "Casey Sample"]
# Rank status per scout. Scout rank is left out, as in real exports.
RANK_STATUS = {
    "Tenderfoot": ["Awarded", "Approved", "In Progress"],
    "Second Class": ["Approved", "In Progress", "Not Started"],
    "First Class": ["In Progress", "Not Started", "Not Started"],
}
CHITS = {"Totin' Chip": ["Approved", "Not Started", "Approved"],
         "Firem'n Chit (Scouts BSA)": ["Approved", "Not Started", "Not Started"]}


def fake_csv():
    """A small Report Builder-style CSV with made-up scouts."""
    sections = json.loads((REPO / "app" / "requirements.json").read_text(encoding="utf-8"))["sections"]
    reqs = {s["name"]: s["reqs"] for s in sections}
    lines = ['"",' + ",".join(f'"{n}"' for n in SCOUTS)]
    for rank, statuses in RANK_STATUS.items():
        lines.append(f'"{rank}",' + ",".join(f'"{s}"' for s in statuses))
        for i, r in enumerate(reqs[rank]):
            cells = ["Approved" if (i + j) % (j + 2) else "" for j in range(len(SCOUTS))]
            lines.append(f'"Req #{r["id"]}",' + ",".join(f'"{c}"' for c in cells))
    for chit, statuses in CHITS.items():
        lines.append(f'"{chit}",' + ",".join(f'"{s}"' for s in statuses))
    return "\n".join(lines) + "\n"


def call(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    cmd = sys.argv[1:] or [sys.executable, str(REPO / "app" / "server.py")]
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, SCOUT_TOOL_DATA=tmp, SCOUT_TOOL_PORT=str(PORT))
        proc = subprocess.Popen(cmd + ["--no-browser"], env=env)
        try:
            for _ in range(60):
                try:
                    call("/api/ping")
                    break
                except OSError:
                    if proc.poll() is not None:
                        sys.exit(f"The tool exited early with code {proc.returncode}")
                    time.sleep(0.5)
            else:
                sys.exit("The tool didn't start within 30 seconds")

            st = call("/api/upload", {"filename": "ReportBuilder_Test_Troop_20260101.csv", "text": fake_csv()})
            assert [s["name"] for s in st["csv"]["scouts"]] == SCOUTS, st["csv"]["scouts"]
            assert len(st["settings"]["categories"]) == len(st["defaults"]) == 121, "default categories missing"
            out = call("/api/generate", {"scouts": SCOUTS, "reveal": False})
            folder = Path(out["folder"])
            assert len(out["files"]) == 2 + len(SCOUTS), out["files"]
            for f in out["files"]:
                head = (folder / f).read_bytes()[:5]
                assert head == b"%PDF-", f"{f} isn't a PDF"
            print("OK:", ", ".join(out["files"]))
            call("/api/quit", {})
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    main()
