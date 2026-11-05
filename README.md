# Scout Advancement Tool

A small Mac app for planning Scouts BSA advancement from Scout rank through First Class, plus Totin' Chip and Firem'n Chit. It reads the Report Builder CSV export from [advancements.scouting.org](https://advancements.scouting.org), lets you sort every requirement by how the troop will cover it, and prints PDF progress reports.

## What it does

- **Categorize requirements.** Shows the full official wording of every requirement. You tag each one as:
  - **Discuss**: covered together at an indoor meeting (library session)
  - **Outdoor**: done during a hike, campout, or other outdoor activity
  - **Coordinated**: the scout and an adult leader plan ahead to make it happen (for example, serving as patrol cook on a campout)
  - **On Own**: the scout works on it at home, then shows or discusses it with an ASM
  - **N/A**: happens through the regular troop program (outings, service, Scoutmaster conference, board of review)

  A new install starts with the troop's default categories (stored as `suggest` in `app/requirements.json`). You can change the tags at any time. Each requirement also shows which scouts still need it.
- **Scout progress.** Shows each scout's rank and chit status and how many items they have left in each category.
- **PDF reports.** Each run creates a folder named with the date and time (for example, `Reports/2026-11-03 16-44-31/`) containing:
  - one all-scouts grid, styled after the advancements.scouting.org report
  - a "remaining by type" grid: every requirement at least one scout still needs, grouped into Discuss, Outdoor, Coordinated, On Own, and N/A
  - one PDF per scout, to email to the scout and parents

  Each report starts at the scout's first unfinished rank. The PDFs show short requirement labels plus a legend; the full wording appears only in the app.

## Getting started

1. Double-click **`Start Scout Tool.command`**. The first run installs the PDF library ([reportlab](https://www.reportlab.com/)) into `app/vendor/`. That needs internet access and only happens once.
2. The app opens in your web browser. Leave the Terminal window open while you use it. Click **Quit** in the app when you're done.
3. Click **Load CSV…** and pick a Report Builder export.

macOS's built-in Python 3 (from the Command Line Developer Tools) is all you need.

### Launchpad / Spotlight app (optional)

Run `tools/install_app.sh` once to build **Scout Advancement Tool.app** in `~/Applications`. After that the tool shows up in Launchpad and Spotlight.

- The app runs in the background with no Terminal window. Click **Quit** in the browser page to stop it.
- It's only a launcher. It runs the code in this repo, so re-run the script only if the repo moves.
- The first time it opens, macOS asks to let it access the drive the repo is on. Click **Allow**.
- Problems are logged to `~/Library/Logs/Scout Advancement Tool.log`.

It uses a small compiled launcher (`tools/launcher.c`) rather than a shell script, so that macOS asks for drive access on behalf of the app instead of silently refusing.

## Where your data lives

Scout data and reports are kept **outside this repo**. The location is set in `config.json`, which git ignores:

```json
{ "data_dir": "/Volumes/ALindeman/ai scratch/scout-advancement-tool" }
```

To set this up on another Mac, copy `config.example.json` to `config.json` and edit the path. Without a `config.json`, the app uses `~/Documents/Scout Advancement Data`. That folder holds:

- `Data/current.csv`: the last CSV you loaded
- `Data/settings.json`: your requirement categories, report title, and legend wording
- `Reports/<date time>/`: the generated PDFs

## How the CSV is read

- A rank counts as **finished** when the report shows it as *Approved* or *Awarded*.
- A rank missing from the CSV (for example, Scout) is assumed finished if a later rank is present.
- Rows for other ranks or awards are ignored.
- Totin' Chip and Firem'n Chit are tracked as a whole. If either Totin' Chip version is approved, the chit counts as earned.

Requirement text comes from the official Scouts BSA rank requirements (effective Jan. 1, 2024) and the scouting.org Awards Central pages. It is stored in `app/requirements.json`.

## Files

| Path | Purpose |
| --- | --- |
| `Start Scout Tool.command` | Double-click launcher |
| `app/server.py` | Local web server (127.0.0.1 only) and API |
| `app/index.html` | The app's interface |
| `app/advancement.py` | CSV parsing and progress logic |
| `app/pdf_report.py` | PDF generation |
| `app/requirements.json` | Requirement wording, short labels, suggested categories |
| `tools/install_app.sh` | Builds the Launchpad app in `~/Applications` |
| `tools/launcher.c`, `tools/make_icon.swift` | The app's launcher and icon |
