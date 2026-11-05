# Scout Advancement Tool

A small local Mac app for planning Scouts BSA advancement (Scout → First Class, plus Totin' Chip and Firem'n Chit). It reads a Report Builder CSV export from advancements.scouting.org, lets the user tag each requirement by how the troop covers it, and generates PDF progress reports. See `README.md` for the user-facing description.

## Stack

- **Python 3.9+, standard library only.** It targets macOS's built-in `/usr/bin/python3` (3.9.6 on this Mac), so don't use syntax or stdlib features newer than 3.9 (no `match`, no `X | Y` type unions at runtime, etc.).
- **One third-party dependency: `reportlab==4.2.5`**, used only for PDFs. It's installed into `app/vendor/` (gitignored) with `pip --target`, not into a venv or the system. `server.py` puts `app/vendor` on `sys.path`.
- **Frontend: a single `app/index.html`** with inline JS/CSS, no build step and no framework.
- There is no package manager, no build, no test suite, and no linter config.

## Layout

| Path | What it is |
| --- | --- |
| `app/server.py` | `http.server` web app on `127.0.0.1:8765`. Serves `index.html` and a JSON API (`/api/state`, `/api/settings`, `/api/upload`, `/api/generate`, `/api/open-reports`, `/api/quit`, `/api/ping`). Also resolves the data folder from `config.json`. |
| `app/advancement.py` | CSV parsing (`parse_csv`) and per-scout progress (`build_scouts`, `is_needed`). Rank codes: `S`, `TF`, `2C`, `1C`; chits `TOTIN`, `FIREMN`. Category codes: `D` Discuss, `O` Outdoor, `C` Coordinated, `S` On Own, `N` N/A. |
| `app/pdf_report.py` | reportlab PDFs: `all_scouts_pdf`, `by_category_pdf`, `scout_pdf`. Imported lazily so the UI still starts without reportlab. |
| `app/requirements.json` | Official requirement wording, short labels, and the default category (`default`) for each requirement, which new installs start from. This is data, so edit it carefully and keep the wording official. |
| `Start Scout Tool.command` | Double-click launcher: installs reportlab on first run, then runs the server. |
| `tools/install_app.sh` | Builds `~/Applications/Scout Advancement Tool.app` (uses `swift`, `sips`, `iconutil`, `clang`, `codesign`). |
| `tools/launcher.c`, `tools/make_icon.swift` | Native launcher binary and icon generator for that `.app`. |
| `config.example.json` | Template for the gitignored `config.json` (`data_dir`). |

## Commands

Run from the repo root.

```bash
# One-time: install the PDF library into app/vendor (needs internet)
/usr/bin/python3 -m pip install --target app/vendor "reportlab==4.2.5"

# Run the app (opens a browser tab at http://127.0.0.1:8765/)
/usr/bin/python3 app/server.py

# Run without opening a browser, e.g. for the preview pane or curl checks
/usr/bin/python3 app/server.py --no-browser

# Quick check: does everything compile?
/usr/bin/python3 -m py_compile app/*.py

# Smoke test the logic without the server
/usr/bin/python3 -c "import sys; sys.path.insert(0,'app'); import advancement; print(len(advancement.all_req_keys()))"

# Rebuild the Launchpad app (only after the repo moves or the launcher changes)
tools/install_app.sh

# Build a self-contained .app + .dmg for a GitHub Release -> dist/Scout-Advancement-Tool-<ver>.dmg
tools/build_release.sh 1.0.0
```

`build_release.sh` copies `app/` into the bundle along with per-chip copies of reportlab, Pillow, and chardet (`Contents/Resources/vendor-arm64`, `vendor-x86_64`) built for Python 3.9. It's ad-hoc signed only. Inside the bundle `config.json` is never found, so the bundled app always uses `~/Documents/Scout Advancement Data`. To test the built app with made-up data, run `Contents/MacOS/scout-advancement` with `HOME` set to a temp folder that has a `Documents/` subfolder. Release drafts: `gh release create vX.Y.Z dist/*.dmg --draft`. Never publish without the owner's OK.

Stop a running server with the app's **Quit** button or `curl -X POST http://127.0.0.1:8765/api/quit`. If port 8765 is already serving the tool, `server.py` just opens the browser and exits.

## Data and privacy

- Real scout data (names, advancement status) lives **outside the repo**, in `config.json`'s `data_dir` or else `~/Documents/Scout Advancement Data` (`Data/current.csv`, `Data/settings.json`, `Reports/<timestamp>/`).
- `.gitignore` excludes `config.json`, `Data/`, `Reports/`, `*.csv`, and `app/vendor/`. **Never commit CSVs, generated PDFs, or `config.json`**, and don't paste real scout names into commits, issues, or docs.
- For testing, write a small made-up CSV in a temp folder and point a temporary `config.json` at it rather than touching the real data folder. Restore or delete that `config.json` afterward.
- `/api/generate` and `/api/open-reports` call macOS `open` on the reports folder, so generating reports during testing pops up Finder windows.

## Conventions

- Keep it dependency-free beyond reportlab, and keep it working with a double-click on a stock Mac.
- Keep the server bound to `127.0.0.1`.
- User-facing text (UI, error messages, README) is plain and friendly, written for non-technical troop leaders.
- When changing the CSV interpretation rules or the categories, update the "How the CSV is read" and "What it does" sections of `README.md` to match.

## Project tracking

The owner (GitHub `LrngToFly`) tracks personal work in Jira project **KAN** ("Personal Projects") at alindeman51.atlassian.net.
