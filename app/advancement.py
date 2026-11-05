"""Requirement data + parsing of advancements.scouting.org Report Builder CSV exports."""
import csv
import io
import json
import re
from pathlib import Path

RANKS = ["S", "TF", "2C", "1C"]
CHITS = ["TOTIN", "FIREMN"]
CATEGORIES = ["D", "O", "C", "S", "N"]
DONE = {"approved", "awarded"}
# Higher in this list wins when a rank has several status rows (e.g. "Tenderfoot" and "Tenderfoot v2022").
STATUS_ORDER = ["awarded", "approved", "completed", "in progress", "started", "not started", ""]

REQUIREMENTS = json.loads((Path(__file__).parent / "requirements.json").read_text(encoding="utf-8"))
SECTIONS = REQUIREMENTS["sections"]
SECTION_BY_CODE = {s["code"]: s for s in SECTIONS}


def req_key(code, req_id):
    return f"{code}-{req_id}"


def all_req_keys():
    return [req_key(s["code"], r["id"]) for s in SECTIONS for r in s["reqs"]]


def default_categories():
    return {req_key(s["code"], r["id"]): r["default"] for s in SECTIONS for r in s["reqs"]}


def section_for(label):
    """Map a non-requirement row label from the CSV to one of our section codes (or None to ignore)."""
    l = label.lower().strip()
    if "totin" in l:
        return "TOTIN"
    if "firem" in l:
        return "FIREMN"
    if l.startswith("first class"):
        return "1C"
    if l.startswith("second class"):
        return "2C"
    if l.startswith("tenderfoot"):
        return "TF"
    if re.match(r"^scout( rank)?( v\d+)?$", l):
        return "S"
    return None  # Star, Life, merit badges, etc. -- rows are skipped


def parse_csv(text):
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if not rows or len(rows[0]) < 2:
        raise ValueError("The file is empty or has no scout columns.")
    cols = [(i, n.strip()) for i, n in enumerate(rows[0]) if i > 0 and n.strip()]
    if not cols:
        raise ValueError("No scout names found in the first row.")

    found = {}
    cur = None
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        label = row[0].strip()
        cells = {name: (row[i].strip() if i < len(row) else "") for i, name in cols}
        m = re.match(r"^req\s*#\s*(\w+)", label, re.I)
        if m:
            if cur:
                found[cur]["reqs"][m.group(1).lower()] = cells
            continue
        cur = section_for(label)
        if cur:
            sec = found.setdefault(cur, {"status": {n: [] for _, n in cols}, "reqs": {}})
            for n, v in cells.items():
                sec["status"][n].append(v)

    if not found:
        raise ValueError(
            "This doesn't look like a Report Builder export from advancements.scouting.org "
            "(no Scout, Tenderfoot, Second Class, First Class, Totin' Chip or Firem'n Chit rows found)."
        )
    return {"scouts": [n for _, n in cols], "found": found}


def _best_status(values):
    vals = [v.strip().lower() for v in values]
    for s in STATUS_ORDER:
        if s in vals:
            return s
    return vals[0] if vals else ""


def _cell_state(value):
    v = value.strip().lower()
    if v in DONE:
        return "done"
    if v and v != "not started":
        return "partial"
    return "open"


def build_scouts(parsed):
    """Per-scout view: rank statuses, which rank to start from, and the state of every requirement.

    Requirement states: done, partial (started / awaiting approval), open, rankdone (whole rank already
    complete), unknown (chit not present in the CSV).
    """
    found = parsed["found"]
    out = []
    for name in parsed["scouts"]:
        ranks = {}
        for idx, code in enumerate(RANKS + CHITS):
            sec = found.get(code)
            if sec is None:
                if code in RANKS:
                    # A rank left out of the report (e.g. Scout) is assumed finished if a later rank is present.
                    later = RANKS[RANKS.index(code) + 1:]
                    assumed = any(c in found for c in later)
                    ranks[code] = {"status": "Complete" if assumed else "Not in CSV",
                                   "done": assumed, "missing": True}
                else:
                    ranks[code] = {"status": "Not in CSV", "done": False, "missing": True}
                continue
            statuses = sec["status"][name]
            best = _best_status(statuses)
            ranks[code] = {
                "status": best.title() if best else "Not Started",
                "done": any(s.strip().lower() in DONE for s in statuses),
                "missing": False,
            }

        start = next((i for i, c in enumerate(RANKS) if not ranks[c]["done"]), len(RANKS))

        reqs = {}
        for s in SECTIONS:
            code = s["code"]
            for r in s["reqs"]:
                key = req_key(code, r["id"])
                rk = ranks[code]
                if code in CHITS:
                    if rk["done"]:
                        reqs[key] = "done"
                    elif rk["missing"]:
                        reqs[key] = "unknown"
                    else:
                        reqs[key] = _cell_state(rk["status"])
                elif rk["done"]:
                    reqs[key] = "rankdone"
                elif rk["missing"]:
                    reqs[key] = "open"
                else:
                    reqs[key] = _cell_state(found[code]["reqs"].get(r["id"], {}).get(name, ""))

        out.append({
            "name": name,
            "ranks": ranks,
            "start": start,
            "start_name": SECTION_BY_CODE[RANKS[start]]["name"] if start < len(RANKS) else None,
            "reqs": reqs,
        })
    return out


def is_needed(state):
    return state not in ("done", "rankdone")
