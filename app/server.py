#!/usr/bin/env python3
"""Scout Advancement Tool -- a small local web app (runs only on this Mac, at 127.0.0.1)."""
import json
import re
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parent
CONFIG_FILE = ROOT / "config.json"  # local only (gitignored); see config.example.json


def data_root():
    """Where the CSV, settings and Reports live: config.json "data_dir", else ~/Documents/Scout Advancement Data."""
    if CONFIG_FILE.exists():
        d = json.loads(CONFIG_FILE.read_text(encoding="utf-8")).get("data_dir", "").strip()
        if d:
            return Path(d).expanduser()
    return Path.home() / "Documents" / "Scout Advancement Data"


DATA_ROOT = data_root()
DATA = DATA_ROOT / "Data"
REPORTS = DATA_ROOT / "Reports"
SETTINGS_FILE = DATA / "settings.json"
CSV_FILE = DATA / "current.csv"
CSV_META = DATA / "current_meta.json"
PORT = 8765

sys.path.insert(0, str(APP / "vendor"))  # reportlab is installed here by the launcher
sys.path.insert(0, str(APP))
import advancement  # noqa: E402

DEFAULT_SETTINGS = {
    "categories": {},
    "title": "",
    "hide_done_individual": False,
    "legend": {
        "D": "Discussion item. We cover it together at an indoor meeting (library session).",
        "O": "Outdoor item. Done during a hike, campout, or other outdoor activity.",
        "C": "Coordinated. The scout and an adult leader plan ahead to make it happen (for example, serving as patrol cook on a campout).",
        "S": "On your own. Work on it at home, then show or discuss it with an Assistant Scoutmaster.",
        "N": "N/A for meetings. Completed through regular troop activities (outings, service, Scoutmaster conference, board of review).",
    },
}


def load_settings():
    s = json.loads(json.dumps(DEFAULT_SETTINGS))
    if SETTINGS_FILE.exists():
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        for k, v in saved.items():
            if isinstance(v, dict) and isinstance(s.get(k), dict):
                s[k].update(v)
            else:
                s[k] = v
    if not s["categories"]:  # first run: start from the troop's default categories in requirements.json
        s["categories"] = advancement.suggestions()
    return s


def save_settings(s):
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


def title_from_filename(fn):
    # ReportBuilder_Troop0004B_Swordsmen_First_Class_20261103.csv -> Troop0004B Swordsmen First Class
    stem = re.sub(r"\.csv$", "", fn, flags=re.I)
    stem = re.sub(r"^ReportBuilder_", "", stem, flags=re.I)
    stem = re.sub(r"_\d{8}$", "", stem)
    return stem.replace("_", " ").strip() or "Advancement Report"


def load_csv():
    if not CSV_FILE.exists():
        return None, None
    meta = json.loads(CSV_META.read_text(encoding="utf-8")) if CSV_META.exists() else {}
    parsed = advancement.parse_csv(CSV_FILE.read_text(encoding="utf-8"))
    return parsed, meta


def state():
    settings = load_settings()
    parsed, meta = load_csv()
    return {
        "sections": advancement.SECTIONS,
        "source": advancement.REQUIREMENTS["source"],
        "suggestions": advancement.suggestions(),
        "settings": settings,
        "csv": None if parsed is None else {
            "filename": meta.get("filename", "current.csv"),
            "loaded_at": meta.get("loaded_at", ""),
            "scouts": advancement.build_scouts(parsed),
        },
        "reports_dir": str(REPORTS),
    }


def safe_name(s):
    return re.sub(r'[/:\\*?"<>|]+', "-", s).strip() or "Report"


def generate(body):
    import pdf_report  # imported lazily so the GUI still starts if reportlab is missing

    settings = load_settings()
    parsed, _ = load_csv()
    if parsed is None:
        raise ValueError("Load a CSV file first.")
    scouts = [s for s in advancement.build_scouts(parsed) if s["name"] in set(body.get("scouts", []))]
    if not scouts:
        raise ValueError("Pick at least one scout.")
    title = (body.get("title") or settings.get("title") or "Advancement Report").strip()
    now = datetime.now()
    folder = REPORTS / now.strftime("%Y-%m-%d %H-%M-%S")
    folder.mkdir(parents=True, exist_ok=True)
    opts = dict(title=title, generated=now, categories=settings["categories"], legend=settings["legend"])
    files = []
    if body.get("all", True):
        p = folder / f"All Scouts - {safe_name(title)}.pdf"
        pdf_report.all_scouts_pdf(p, scouts, **opts)
        files.append(p.name)
    if body.get("by_category", True):
        p = folder / f"Remaining by Type - {safe_name(title)}.pdf"
        pdf_report.by_category_pdf(p, scouts, **opts)
        files.append(p.name)
    if body.get("individual", True):
        for s in scouts:
            p = folder / f"{safe_name(s['name'])} - Trail to First Class.pdf"
            pdf_report.scout_pdf(p, s, hide_done=bool(body.get("hide_done")), **opts)
            files.append(p.name)
    subprocess.run(["open", str(folder)], check=False)
    return {"folder": str(folder), "folder_name": folder.name, "files": files}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, payload, ctype="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (APP / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/ping":
            self._send(200, {"app": "scout-advancement-tool"})
        elif self.path == "/api/state":
            try:
                self._send(200, state())
            except Exception as e:  # a bad saved CSV shouldn't brick the app
                self._send(500, {"error": str(e)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = self._body()
            if self.path == "/api/settings":
                s = load_settings()
                for k in ("title", "hide_done_individual"):
                    if k in body:
                        s[k] = body[k]
                if "legend" in body:
                    s["legend"].update({k: v for k, v in body["legend"].items() if k in advancement.CATEGORIES})
                if "categories" in body:
                    for k, v in body["categories"].items():
                        if v in advancement.CATEGORIES:
                            s["categories"][k] = v
                        else:
                            s["categories"].pop(k, None)
                save_settings(s)
                self._send(200, {"ok": True})
            elif self.path == "/api/upload":
                text, filename = body["text"], body.get("filename", "upload.csv")
                advancement.parse_csv(text)  # validate before replacing the current file
                DATA.mkdir(parents=True, exist_ok=True)
                CSV_FILE.write_text(text, encoding="utf-8")
                CSV_META.write_text(json.dumps({"filename": filename,
                                                "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M")}),
                                    encoding="utf-8")
                s = load_settings()
                s["title"] = title_from_filename(filename)
                save_settings(s)
                self._send(200, state())
            elif self.path == "/api/generate":
                self._send(200, generate(body))
            elif self.path == "/api/open-reports":
                REPORTS.mkdir(parents=True, exist_ok=True)
                subprocess.run(["open", str(body.get("folder") or REPORTS)], check=False)
                self._send(200, {"ok": True})
            elif self.path == "/api/quit":
                self._send(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(400, {"error": str(e)})


def already_running():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/ping", timeout=1) as r:
            return b"scout-advancement-tool" in r.read()
    except Exception:
        return False


def main():
    url = f"http://127.0.0.1:{PORT}/"
    if already_running():
        print("The tool is already running -- opening it in your browser.")
        webbrowser.open(url)
        return
    if not DATA_ROOT.parent.exists():  # e.g. the external drive holding the data isn't plugged in
        print(f"Can't find the data folder's location: {DATA_ROOT.parent}")
        print("If it's on an external drive, plug the drive in and try again. To use another folder, edit config.json.")
        sys.exit(1)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("Scout Advancement Tool is running at", url)
    print("Data and reports folder:", DATA_ROOT)
    print("Leave this window open while you use it. Click Quit in the app (or close this window) when done.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("Stopped. You can close this window.")


if __name__ == "__main__":
    main()
