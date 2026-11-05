# Scout Advancement Tool

A small local app (Mac, plus a packaged Windows build) for planning Scouts BSA advancement (Scout → First Class, plus Totin' Chip and Firem'n Chit). It reads a Report Builder CSV export from advancements.scouting.org, lets the user tag each requirement by how the troop covers it, and generates PDF progress reports. See `README.md` for the user-facing description.

## Stack

- **Python 3.9+, standard library only.** It targets macOS's built-in `/usr/bin/python3` (3.9.6 on this Mac), so don't use syntax or stdlib features newer than 3.9 (no `match`, no `X | Y` type unions at runtime, etc.).
- **One third-party dependency: `reportlab==4.2.5`**, used only for PDFs. It's installed into `app/vendor/` (gitignored) with `pip --target`, not into a venv or the system. `server.py` puts `app/vendor` on `sys.path`.
- **Frontend: a single `app/index.html`** with inline JS/CSS, no build step and no framework.
- There is no package manager and no linter config. The only build is packaging (`tools/build_release.sh` for the Mac DMG, GitHub Actions for Windows). The one test is `tools/smoke_test.py`, an end-to-end run with made-up scouts.
- The same `app/` code runs on Windows (Python 3.12 inside the PyInstaller .exe), so keep it cross-platform: use `reveal()` in `server.py` to open folders, not a direct `open` call.

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
| `tools/windows/` | Windows entry point (`launch.py`: log file + message boxes, since the .exe has no console), Inno Setup script (`installer.iss`), and `icon.ico`. |
| `.github/workflows/windows.yml` | Builds the Windows .exe, installer and portable zip on `windows-latest`, runs `smoke_test.py` against the source and the .exe, and attaches the installer and zip to a GitHub release when it's published. Runs on pushes that touch `app/` or the Windows files, or by hand from the Actions tab. |
| `.github/workflows/mac.yml` | Runs `build_release.sh` on `macos-latest`, mounts the .dmg, runs `smoke_test.py` through the app's real launcher and the Intel library under Rosetta, and attaches the .dmg to a published release. To save Mac minutes it runs only for releases, by hand, or on pushes that change the Mac build files. |
| `tools/smoke_test.py` | Starts the tool against a temp data folder on port 8799, loads a made-up CSV, generates every PDF, and quits. |
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

# End-to-end test with made-up scouts (temp data folder, port 8799; safe while the real app runs)
/usr/bin/python3 tools/smoke_test.py /usr/bin/python3 app/server.py

# Quick check: does everything compile?
/usr/bin/python3 -m py_compile app/*.py

# Smoke test the logic without the server
/usr/bin/python3 -c "import sys; sys.path.insert(0,'app'); import advancement; print(len(advancement.all_req_keys()))"

# Rebuild the Launchpad app (only after the repo moves or the launcher changes)
tools/install_app.sh

# Build a self-contained .app + .dmg for a GitHub Release -> dist/Scout-Advancement-Tool-<ver>.dmg
tools/build_release.sh 1.0.0
```

`build_release.sh` copies `app/` into the bundle along with per-chip copies of reportlab, Pillow, and chardet (`Contents/Resources/vendor-arm64`, `vendor-x86_64`) built for Python 3.9. It's ad-hoc signed only. Inside the bundle `config.json` is never found, so the bundled app always uses `~/Documents/Scout Advancement Data`. To test the built app with made-up data, run `Contents/MacOS/scout-advancement` with `HOME` set to a temp folder that has a `Documents/` subfolder. Releases: `gh release create vX.Y.Z --draft --generate-notes`. No local build is needed: publishing the release triggers both workflows, which test and then attach the .dmg, the Windows installer and the zip a few minutes later. Never publish without the owner's OK.

Stop a running server with the app's **Quit** button or `curl -X POST http://127.0.0.1:8765/api/quit`. If port 8765 is already serving the tool, `server.py` just opens the browser and exits.

## Data and privacy

- Real scout data (names, advancement status) lives **outside the repo**, in `config.json`'s `data_dir` or else `~/Documents/Scout Advancement Data` (`Data/current.csv`, `Data/settings.json`, `Reports/<timestamp>/`).
- `.gitignore` excludes `config.json`, `Data/`, `Reports/`, `*.csv`, and `app/vendor/`. **Never commit CSVs, generated PDFs, or `config.json`**, and don't paste real scout names into commits, issues, or docs.
- For testing, use `tools/smoke_test.py`, or set `SCOUT_TOOL_DATA` (data folder) and `SCOUT_TOOL_PORT` in the environment, so the real data folder and a running copy of the tool are never touched.
- `/api/generate` and `/api/open-reports` show the reports folder in Finder / File Explorer. Pass `"reveal": false` to `/api/generate` to skip that when testing.

## Conventions

- Keep it dependency-free beyond reportlab, and keep it working with a double-click on a stock Mac and from the Windows installer.
- Keep the server bound to `127.0.0.1`.
- User-facing text (UI, error messages, README) is plain and friendly, written for non-technical troop leaders.
- When changing the CSV interpretation rules or the categories, update the "How the CSV is read" and "What it does" sections of `README.md` to match.

## Project tracking

Users send bug reports and ideas through the Jira Service Management portal https://alindeman51.atlassian.net/servicedesk/customer/portal/1, which files them in the service space **SUP** ("Scout Advancement Tool Feedback", service desk ID 1, request types "Report a problem" and "Suggest an improvement"). Accepted work is tracked in the Jira space **SAT** ("Scout Advancement Tool") at https://alindeman51.atlassian.net/jira/software/projects/SAT/boards. It uses the work types **Bug** and **Feature** (plus Task for chores), and its releases match the GitHub release versions (for example `1.0.0`). Set a ticket's fix version to the release that ships it. When a GitHub release goes out, add the next version in Jira. The owner's other personal work is in the Jira space **KAN** ("Personal Projects") on the same site.
