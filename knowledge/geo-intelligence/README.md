# geo-intelligence

An agent skill for geolocating and chronolocating images: photos, screenshots, video frames and street-level / GeoGuessr-style rounds. Given an image, the agent works out country, region, city, street, camera position and heading, and when the picture was taken, and proves it with files produced in the session. The deliverable is one best answer with coordinates, an error radius, tiered confidence, when the photo was taken (year, season, date, time of day, as far as the evidence goes), alternatives with the test that separates them, and an evidence image.

The skill follows the [AgentSkills specification](https://agentskills.io/specification): `SKILL.md` is the method the agent reads, `references/` are deep dives loaded on demand, `scripts/` are command-line tools the agent runs, `assets/data/` are offline lookup tables.

- [How it works](#how-it-works)
- [Layout](#layout)
- [Requirements](#requirements)
- [Installing the skill](#installing-the-skill)
- [Using it](#using-it)
- [Scripts](#scripts)
- [Configuration](#configuration)
- [Testing](#testing)

## How it works

The method combines a player's eye with an investigator's discipline. The agent commits to a ranked gut call before any tool runs, then uses tools to confirm, refute and refine it. Every claim must point at a clue, the command that tested it and the file it produced; anything else is reported as an unverified estimate.

1. **Session.** `photo_session.py start` creates one timestamped archive per photo; every crop, board, cache and evidence image lives there.
2. **Gut call and plan.** A ranked shortlist with percentages, plus a plan of the 1–3 most selective fixed features and the route that tests each, is written to `report.md` from the image alone (checklist in `references/observe.md`); an operator pointer ("watch the skyline") becomes the plan's first line.
3. **Recon.** `recon.py` runs the whole local first pass in parallel: metadata, edge/corner crops, OCR with language detection, Yandex + Baidu reverse image search, text-to-country signals, object crops, camera calibration and a world-prior model. It writes one summary page.
4. **Read and search.** Every legible string becomes a web query; phones, domains, postal codes, brands and place names are resolved offline (`textgeo.py`) and against OpenStreetMap (`osm.py`, `poi.py`, `gazetteer.py`). Reverse image search runs on the original and on tight crops.
5. **Country funnel.** Discriminators are applied in order of how much of the world they exclude (text, driving side, plate shape, road paint, sign family, sun, biome, infrastructure, architecture). Candidates and clues go on a **candidate board** (`board.py`) that enforces the evidence rules: whole categories are listed before choosing, model scores only rank, exclusion needs a file and stated coverage, finer candidates nest under coarser ones, one answer and never a midpoint.
6. **Region and town.** Plate codes, area codes, bilingual signage, subdivision lists, GeoNames town lists, reference sheets of real street-level imagery per candidate, and dataset filters (OSM tags, addresses, open-data portals, Overture).
7. **Pinpoint.** Sight-line intersection and camera pose from known points (`geo.py`, `pose.py`), skyline render-and-compare against elevation data (`terrain.py`; the best three synthetic skylines over the photo with summit names become the live page's Skyline card), sun, shadow and dish geometry (`sun.py`), terrain and building shadow maps with lit/shaded point checks and time sweeps (`terrain.py shade`), route and crossing queries (`osm.py`), CLIP-ranked satellite scans (`sat_scan.py`), panorama discovery from eleven street-level providers (`pano.py`, `gsv.py`, `baidu_pano.py`), whole-town panorama sweeps (`sweep.py`) and feature matching (`match.py`).
8. **Verify and answer.** Falsification conditions, a bearing self-check, redoing the decisive step with another crop or tool, `board.py check` and `report`, an evidence image, then `photo_session.py finish`. `finish` is a gate: it refuses an answer with no verification file, and a mountain, lake, street or road photo (recon's scene tags) closes only once its own check (skyline fit or street ranking) has left a file, or another geometry pins the answer (an evidence or match image, a `pose.py` solution, a fair ranked view within 150 m). Every refusal names the exits: run the check, or close with a recorded reason (`--skip-check`, `--accept-unverified`), before 25 minutes only when the operator stopped or redirected the analysis. Confidence is rated per level (country, region, area, street, building) and the answer is given at the finest level rated medium or better. When the truth becomes known, `photo_session.py truth` scores the session. A generated image closes with no place (`finish --generated`) only on evidence: a file that declares generated content, an AI-gallery copy the agent saved and confirmed, or the operator's word; the AI-image score (`aidet.py`) only ranks, and the operator's "it is real" (`not-generated`) or a file that pins a real place outranks a declaration.

The rules behind each step, and the commands to run, are in `SKILL.md`. The regional clue library (`references/world/`) covers Europe, the Americas, Asia, Oceania, Africa and the Middle East, mainland China and Street View camera generations.

## Layout

```
geo-intelligence/
├── SKILL.md                 # the method: rules, flow, toolbox, runtime notes
├── README.md                # this file
├── references/              # deep dives loaded on demand (see "Resources" in SKILL.md)
│   ├── workflow.md          # archive layout, report.md, answer format, scoring
│   ├── observe.md           # image-reading checklist
│   ├── country-funnel.md    # discriminator order, look-alike separation
│   ├── search.md            # reverse and keyword image search
│   ├── datasets.md          # clue -> dataset filter recipes
│   ├── streetlevel.md       # coverage ladder, providers, manifests, town sweeps
│   ├── geometry.md          # FOV, bearings, sight lines, skylines, camera pose
│   ├── sky.md               # sun, shadows, dishes, date and weather
│   ├── corridors.md         # roads, railways, power lines, rivers
│   ├── aerial.md            # plane-window and drone photos
│   ├── verify.md            # falsification, red team, final checklist
│   ├── models.md            # what each local model is good for
│   ├── data-sources.md      # endpoints, coordinate systems, imagery archives, licences
│   └── world/               # clue library by region + streetview.md
├── scripts/                 # 38 CLIs, run with `uv run`
│   ├── geolib/              # shared package: HTTP, browser, panoramas, MegaLoc, caches, CLI helpers
│   └── tests/               # offline regression suites
└── assets/
    ├── data/                # lookup tables + regions/<cc>/ data packs (index.md lists sources)
    └── viewer/              # the live page (HTML, CSS, JS, Natural Earth outlines) served by viewer.py
```

## Requirements

- Python 3.10 or newer and [uv](https://docs.astral.sh/uv/). Every script declares its own dependencies in a PEP 723 header, so `uv run` installs what it needs on first use.
- `curl` (bundled with Windows 10+, macOS and most Linux distributions).
- Network access for OpenStreetMap, map tiles, panoramas, GeoNames and reverse image search.
- Recommended: `exiftool` for full metadata (a pure-Python fallback exists), `ffmpeg` for video frames.
- Reverse image search drives a browser: local Chrome, or Playwright Chromium via `uvx playwright install chromium`.
- Optional local models (about 6 GB, downloaded on first use into the Hugging Face and Torch caches) for the world prior, object detection, camera calibration, CLIP ranking and MegaLoc sweeps. Everything else works without them.
- GPU: Linux NVIDIA (driver 580+) and Apple Silicon (`mps`) work out of the box. Windows NVIDIA, AMD (Windows and Linux) and Intel Arc run `uv run scripts/doctor.py --gpu` once: it builds a GPU torch environment (1–7 GB download, 4–16 GB on disk) that the model scripts then hand off to. `GEOINT_DEVICE=cpu` forces the CPU, which is sufficient for the whole method.

Windows, macOS and Linux are supported. Windows and Linux are tested with the regression suites on every change.

## Installing the skill

Skills are plain folders. Copy this directory into the place your agent reads skills from, or use the repository installers from the repository root:

```bash
# Interactive installer (choose skills, destination, layout)
./install.sh                      # Bash
pwsh -File ./install.ps1          # PowerShell 7

# Plain copy
cp -r knowledge/geo-intelligence ~/.agents/skills/
```

Claude Code sets `${CLAUDE_SKILL_DIR}` to the installed folder. Other agents should export `CLAUDE_SKILL_DIR=<absolute path to geo-intelligence>` before running commands from `SKILL.md`, because every reference writes script paths as `${CLAUDE_SKILL_DIR}/scripts/x.py`.

Check the environment once:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/doctor.py              # local tools, data, caches, browser, writable dirs
uv run ${CLAUDE_SKILL_DIR}/scripts/doctor.py --network    # known-answer probes of the core services
uv run ${CLAUDE_SKILL_DIR}/scripts/doctor.py --models     # pre-download the local models
```

## Using it

With the skill installed, an agent picks it up for any request of the form "where is this", "where was this taken", "when was this taken", OSINT location checks, image verification or puzzle rounds, in several languages. Attach the image and ask. Every search starts with the lightweight Quick phase; the operator can stop, redirect or limit the analysis at any moment:

- **Quick**: read the image, plan by selectivity, run recon and the useful lightweight routes. It has no fixed duration. If the user explicitly requests Quick, stop before heavy analysis and report the supported location or what remains unknown. Otherwise a request to find the position continues automatically into Deep when needed; a certain country or city alone is not a stopping point while finer work remains.
- **Deep**: pursue the remaining useful routes in the same session, including broader terrain fits, panorama indexing and satellite scans. Continue until the requested position or level is supported, an explicit operator limit is reached, or no feasible route remains. Detailed transitions, verification and honest unresolved results: SKILL.md "Session and speed".

The same tools can be run by hand. A minimal manual session:

```bash
# 1. archive the photo (prints the session folder; run everything from inside it)
#    --viewer also opens the live page (random free port, URL printed and stored in session.json): a globe that narrows to the answer plus the activity panel
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py start --image "/abs/path/photo.jpg" --viewer   # repeat --image for several photos of one scene; --beside = session next to the photo
cd "<printed folder>"
uv run ${CLAUDE_SKILL_DIR}/scripts/viewer.py say "Reading the road sign"      # one line per step for the panel
#    start also creates board.json; recon.py feeds its text and prior signals into it

# 2. first pass: metadata, crops, OCR, reverse search, text signals, detector, calibration, world prior
uv run ${CLAUDE_SKILL_DIR}/scripts/recon.py original/photo.jpg --out-dir recon
#    read recon/recon.md and open the crops it lists

# 3. candidate board: categories, evidence, ranking, next cheapest test
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py apply --kind driving-side --value left
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py ingest recon/textgeo.json
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py clue "red laterite, eucalyptus" --kind vegetation --status observed --file recon/intake/edges/e1.jpg
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py evidence --clue K1 --for Kenya:3 --for Uganda:3 --why "soil and trees"
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py rank
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py next

# 4. pinpoint with whatever the scene offers; each script's --help lists the exact flags
uv run ${CLAUDE_SKILL_DIR}/scripts/gsv.py --help          # Street View panoramas near a point or in an area
uv run ${CLAUDE_SKILL_DIR}/scripts/match.py --help        # rank panoramas against the photo
uv run ${CLAUDE_SKILL_DIR}/scripts/sun.py --help          # shadows, lit faces, time, date, dishes
uv run ${CLAUDE_SKILL_DIR}/scripts/terrain.py shade --help   # terrain and building shadows at a time; which times leave given points lit or shaded
uv run ${CLAUDE_SKILL_DIR}/scripts/terrain.py --help      # skylines, ridges, scans, fit

# 5. verify, report, archive
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py check
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py report --merge result.json
uv run ${CLAUDE_SKILL_DIR}/scripts/evidence.py spec.json --out evidence.jpg
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py finish "$PWD" --country Kenya --region Nakuru --city Naivasha \
    --latitude -0.7172 --longitude 36.4310 --confidence medium --radius-m 400 --heading 215 --taken 2021-07..2021-09 --taken-confidence low

# later, when the real answer is known
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py truth "<session folder>" --latitude -0.7150 --longitude 36.4290 --country Kenya
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py scoreboard
```

Every script prints its usage with `--help`, and the docstring at the top of each file documents its subcommands with examples. Session folders default to `~/geoint-photos/` and are renamed on finish to `<timestamp>__country__region__city`.

### The live view

`viewer.py` serves one session on `127.0.0.1` and refreshes every 2 seconds. The globe (drawn from bundled Natural Earth outlines) highlights the countries on the board, turns to the leading candidate and zooms in as the board narrows, switching to Esri World Imagery tiles (`--tiles osm` for OpenStreetMap) for small extents, and ends on the answer with its radius and camera heading (and the recorded truth once `photo_session.py truth` has run). Wheel, buttons and dragging move the map by hand, "Follow" returns it to the analysis, "Close viewer" stops the server (so does `viewer.py stop`, and it exits by itself after 30 idle minutes); `finish`, `truth`, `stop` and Close leave `viewer.html` beside the photos, the page as one offline file. Map layers show the top street-level matches with their saved views, the panoramas searched, and the agent's marks (`viewer.py mark`: camera point with view cone, sight lines, anchors, found images); a click opens the marker's card. `viewer.py mark area <file.geojson> --level L` draws `osm.py geom` outlines in 2D (a building footprint, indoor rooms and corridors), dashed below ground, with level chips that show one floor at a time; it is display only. The panel shows what the analysis is doing now (`viewer.py say` lines), the candidates per level with shares and exclusions, every new file with thumbnails, and the rendered report. It reads files only and serves nothing outside the session folder.

## Scripts

All scripts live in `scripts/` and are run with `uv run ${CLAUDE_SKILL_DIR}/scripts/<name>`.

| Area | Scripts | What they do |
|---|---|---|
| Session | `photo_session.py`, `viewer.py` | `start` (`--viewer`), `finish` (`--generated`), `not-generated`, `checks`, `truth` (`--generated`), `scoreboard`, `list --status pending`; live page in the browser (`serve`, `say`, `mark`, `state`, `export`, `stop`) |
| First pass | `recon.py`, `meta.py`, `intake.py`, `ocr.py`, `imgprep.py`, `revimg.py`, `textgeo.py`, `aidet.py` | one-command recon; metadata incl. GPS, time zone, AI-provenance flags; AI-image score, a ranking; crops and OCR; `zoom`, `reveal`, `piers`; Yandex and Baidu reverse search, keyword image search on each country's engines; text to scripts, languages, phones, domains, postal codes, brands, places |
| Candidates | `board.py`, `clues.py`, `regions.py`, `geodata.py`, `refsheet.py` | candidate board with evidence rules; plate-code, area-code, calling-code, driving-side, territory and coverage lookups; country cards and data-pack lint; GeoNames towns and regions; real street-view reference rows per country, region or town |
| Models | `prior.py`, `detect.py`, `calib.py` | StreetCLIP + GeoCLIP world prior; OWLv2 object crops; GeoCalib FOV, pitch, roll, horizon |
| Maps and data | `osm.py`, `poi.py`, `gazetteer.py`, `opendata.py` | Overpass queries (`find`, `addr`, `near`, `crossings`, `route`, `along`, `intersect`, `street-scan`, `buildings`, `coverage`, `geom`); Nominatim search, reverse, routing, time zone; admin hierarchies; Socrata open-data portals |
| Imagery | `tiles.py`, `sat_scan.py`, `evidence.py` | satellite and map mosaics (Google, hybrid, Esri, Bing, Esri Wayback, Sentinel-2, NASA GIBS), sheets, marks, pixel to lat/lon; CLIP-ranked satellite scans; evidence and match images |
| Street level | `pano.py`, `gsv.py`, `baidu_pano.py`, `sweep.py`, `match.py` | coverage, listing, rendering and sheets across Google, Apple, Bing, Yandex, Naver, Kakao, Mapy, Já, KartaView, Panoramax, Mapillary and your own manifests; Baidu panoramas; whole-town MegaLoc sweeps with clusters; MegaLoc, DINOv2, CLIP and SIFT ranking |
| Geometry | `geo.py`, `pose.py`, `sun.py`, `terrain.py` | bearings, destinations, sight-line intersection, FOV and frame checks, WGS84/GCJ-02/BD-09 conversion, pier spacing; camera pose from known points with self-check; sun position, shadow and lit-face solving, time and date, dish pointing, past weather; elevation, viewsheds, skyline rendering, ridge extraction, scans and skyline fitting |
| Maintenance | `bench.py`, `refresh.py`, `doctor.py`, `sources_check.py` | street-view test sets with hidden truth and scoring; refresh of the lookup tables from their sources; environment check; live known-answer probes of every external endpoint |

`geolib/` is the shared package behind them: HTTP with proxy and retries (`net.py`), browser launch (`browser.py`), panorama providers and manifests (`pano.py`, `streetlevel.py`, `coverage.py`), MegaLoc descriptors (`megaloc.py`), cache paths (`paths.py`), geodesy (`geomath.py`), argument helpers and the torch device (`cli.py`) and the GPU hand-off (`accel.py`).

## Configuration

Everything is optional; defaults work out of the box.

| Variable | Purpose |
|---|---|
| `GEOINT_PHOTOS` | Root for session archives (default `~/geoint-photos/`; `--root` overrides per call, `start --beside` uses the photo's own folder) |
| `GEOINT_TZ` | IANA time zone for session timestamps (default: the machine's zone) |
| `GEOINT_CACHE` | Shared cache for GeoNames, panorama indexes, descriptors (default `~/.cache/geoint`, on Windows `%LOCALAPPDATA%\geoint`) |
| `GEOINT_DEVICE` | `auto` (default), `cuda`, `xpu`, `mps` or `cpu` for the local models; `cpu` also skips the GPU environment |
| `GEO_PROXY` | Proxy URL for every script, or `direct` to bypass system proxies |
| `GEO_OVERPASS_URL` | Comma-separated Overpass instances to try before the public mirrors |
| `GEO_REGIONS` | Extra region-pack directories (`os.pathsep`-separated); a pack there overrides a bundled one |
| `MAPILLARY_TOKEN` | Free client token enabling the Mapillary provider in `pano.py` |
| `HF_HOME`, `TORCH_HOME` | Standard model cache locations honoured by the model scripts |

A `config.local.json` next to `SKILL.md` can set `photos_root` and `timezone` instead of the environment. Per-session caches (OSM, elevation, tiles) live in `.geo-cache/` inside each session folder.

## Testing

Offline regression suites, no network or models needed:

```bash
cd ${CLAUDE_SKILL_DIR}
for t in scripts/tests/test_*.py; do uv run "$t" || exit 1; done
```

Live checks of the external services the scripts depend on (run when a tool returns nothing where coverage is known, or before a long scan):

```bash
uv run scripts/sources_check.py                 # every known-answer probe
uv run scripts/sources_check.py --only nominatim,overpass --json sources.json
uv run scripts/sources_check.py --no-models     # skip model downloads
```

Repository validators (from the repository root): `python scripts/quick_validate.py knowledge/geo-intelligence`, `python scripts/sweep_skills.py knowledge/geo-intelligence`, `python scripts/check_changed_files.py`.
