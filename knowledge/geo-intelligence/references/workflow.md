# Workflow: one archive per photo, autonomy, report, answer, scoring

- [Paths and settings](#paths-and-settings)
- [Start: one timestamped archive per photograph](#start-one-timestamped-archive-per-photograph)
- [Live view](#live-view)
- [Clock](#clock)
- [Autonomy](#autonomy)
- [report.md](#reportmd)
- [Finish](#finish)
- [Answer format](#answer-format)
- [Learning from results](#learning-from-results)
- [Scoring and test sets](#scoring-and-test-sets)
- [Troubleshooting](#troubleshooting)

These defaults apply whenever this skill runs, from any project folder.

## Paths and settings

- Scripts: `scripts/x.py` in every reference means `${CLAUDE_SKILL_DIR}/scripts/x.py`. Run each with `uv run`
  (each script declares its dependencies).
- Archive root: `--root`, else `$GEOINT_PHOTOS`, else `photos_root` in `config.local.json` next to `SKILL.md`,
  else `~/geoint-photos/`. `start --beside` ignores the root and creates the session next to the first photo
  (`scoreboard` and `list` then need `--root <that folder>`).
- Archive time zone: `$GEOINT_TZ`, else `timezone` in `config.local.json`, else this computer's (set an IANA name such as `Europe/Rome`; otherwise the footer shows the OS's local zone name).
- Shared cache (GeoNames, panorama indexes, sweep descriptors, Wayback list, test-set panoramas):
  `$GEOINT_CACHE`, else `~/.cache/geoint` (on Windows without `~/.cache`, `%LOCALAPPDATA%/geoint`).
- Per-session cache (OSM, elevation tiles, Street View tiles): `.geo-cache/` in the session folder.

## Start: one timestamped archive per photograph

```bash
uv run scripts/photo_session.py start --image "/absolute/path/to/photo.jpg"
```

- The folder name is the exact analysis start time to microseconds with its UTC offset: the analysis time,
  not the capture time.
- One session per scene: several photos of the same place share a session (`--image` repeated; the first is the
  reference `original`, the others are listed in `session.json` `originals`); photos of different places get
  separate sessions and boards.
- The untouched original is copied to `original/` with its SHA-256. If the attachment bytes cannot be read,
  omit `--image`, describe the source in `original/source.txt`, and say that the original was not saved.
  Never substitute a different image.
- `cd` into the session folder and run every tool from there, with absolute script paths and the saved
  original, so crops, OCR, boards, caches and evidence all stay with that photo. Use session-relative paths
  inside boards and evidence specs (they must survive the rename). Finish background commands before renaming.
- `start` also writes an empty `board.json`; `recon.py` run from the session folder ingests `textgeo.json` and
  `prior/prior.json` into it, so the first candidates and clues are there before any manual `board.py` call.
- Interrupted? `photo_session.py list --status pending` shows sessions to resume; never start over silently.

## Live view

`photo_session.py start --viewer` (or `viewer.py serve <session> --open`, any time later) serves the session on
`http://127.0.0.1:<random free port>/` (`--viewer-port` / `--port` force one), prints the URL, stores it as
`viewer_url` in `session.json` and opens it in the default browser. The
page re-reads the folder every 2 s and shows, for the user watching:

- the globe: countries on the board are highlighted by share; the top-ranked open candidate at the finest level is
  the focus and the globe turns and zooms to it, handing over to imagery tiles (Esri World Imagery; `--tiles osm` for
  OpenStreetMap) when the extent is small; after `finish`, the answer with its radius and camera heading;
  after `truth`, the real spot in teal with a dashed line to the answer and the error in km; the wheel, the + and −
  buttons and dragging move the map by hand, "Follow" hands it back to the analysis; every text is selectable;
  "Close viewer" stops the server without touching the analysis;
- map layers: the top views of every `match.py rank` (position, heading, score, the saved view on click; a strong
  top match also writes a camera mark with its view cone),
  the panoramas of every `*.index.json` as the Coverage layer (off by default; switching a layer on flies the view to
  its points, one ring with the count when they are too close to tell apart; Follow returns to the analysis; a dot's
  card shows id, provider, date, road and a link that opens the panorama), and your marks: `viewer.py mark camera` (point +
  view cone), `mark line` (sight line, skyline bearing), `mark point` (anchor), `mark image <file>` (a found photo
  at its position); buttons toggle the layers, a click opens the marker's card. Images named ridge/fit/overlay/
  evidence/match/sheet/pose get their own gallery in the panel; `terrain.py fit --sheet` adds a Skyline card (the
  top three synthetic skylines stacked over the photo with score, heading and focal, summit names with `--peaks`);
- the panel: "Now" (the last `viewer.py say` line), candidates per level with shares, verified counts and exclusions,
  the activity feed (`say` lines, `board.py` log, every new file with thumbnails that open full size), `report.md` and
  `recon/recon.md` rendered.

Habits that keep it honest and useful:
- `uv run scripts/viewer.py say "Ranking Koilada panoramas against the photo"` at every step change; without it the
  "Now" line falls back to the latest board entry or file.
- Before any `board.py` call the page shows the gut call countries parsed from `report.md` (numbered lines
  `1. Country NN% — why`, English names); after it, the board alone. Quick mode: `board.py country <cc>` as soon
  as the country is settled (it adds the country candidate too), so the page follows the analysis.
- Candidates below country level appear on the globe only with coordinates: `board.py add --bbox s,w,n,e`,
  `--from pois.json` / `osm.py geom` output, or `board.py scan-bbox <name> --bbox …` later; a candidate without
  them is shown on its nearest ancestor that has some.
- The server reads files only; it binds 127.0.0.1 and serves nothing outside the session folder. It keeps serving
  after `finish` renames the folder.
- Several sessions at once: every viewer takes a random free port (`start --viewer`, `viewer.py serve`), prints
  the URL and records it as `viewer_url` in `session.json`; `viewer.py stop <session>` reads it and refuses to stop
  another session's viewer (only `--force` does).
- Snapshot: `finish`, `truth`, `stop` and Close write `<session>/viewer.html`, the same page with state, outlines,
  styles and script inlined and file links relative: it opens from the folder without a server (tiles need the
  network); `viewer.py export <session>` refreshes it by hand.
- Stopping: the page's Close button, `viewer.py stop <session>` (port from `session.json`, else `--port`), Ctrl+C in
  its terminal; it also exits by itself after `--idle-minutes` (30) without a request. The server lingers 3.5 s so the
  open page receives the final state (Done after `finish`) and the snapshot path, then the page stops polling. Stop
  after the answer, never before `finish`, unless the user wants the page kept; and end every background job before
  `finish`: on Windows a process with an open file or working directory inside the folder blocks the rename.

## Clock

Every analysis starts in Quick mode: about 10 minutes of tools after the gut call, then answer at the level reached;
one more block only with a decisive test already named. Deep mode is entered only on the user's request or when the
Quick answer is unsatisfactory (requested level not reached, decisive checks in contradiction, a single supporting
clue), and it continues the same session. Deep mode: no fixed clock, but every 15 minutes reread the saved result lists before
Long tools are bounded, never awaited open-ended: `terrain.py fit` stops at `--budget-min` (20 min) with a partial
ranking and the `--select` list to continue; `scan` prints what its cluster count will cost. Start them in the
background, read the partial result at the stop, and decide from it.
widening, and never start a whole-town ranking without first trying to name the junction from text and road geometry.
When the clock runs out, report the settled level, the radius it supports and the test that would have separated the
remaining candidates, and `finish`: never stop to ask whether to continue (autonomy), offer the next step in the answer.

## Autonomy

- Work end to end without asking the user anything. Reverse image search (uploading the photo and crops to
  Yandex, Baidu, Google Lens, Bing, TinEye), web search, maps, OpenStreetMap, GeoNames and Street View lookups
  are all pre-approved for every photo analysed with this skill.
- Ambiguity is resolved by judgment, not by questions: choose the most reasonable reading, record the
  assumption in `report.md`, continue. A blocked service (CAPTCHA, rate limit) is skipped and noted.
- Keep secrets (API keys, tokens) out of saved files, command lines and shell history.

## report.md

`start` creates a skeleton (gut call, evidence, answer, when, alternatives, exclusions); `finish` refuses while the
gut call, answer or when section is still a placeholder. Write it as you go, in the user's language, keeping source
text verbatim with a translation. It contains: the gut call (written before tools), observations, decisive
clues with the files that show them, commands actually run, sources with links, the chosen location and
coordinates (WGS84; GCJ-02 too for mainland China), confidence per level and the radius it is based on,
alternatives with the test that would separate them, excluded candidates and why, and clues not yet explained.

## Finish

```bash
cd ..   # out of the session folder first: Windows refuses to rename a folder that any shell or process sits in
uv run scripts/photo_session.py finish "/absolute/session/path" --country "Country" \
  --region "Region" --city "City or nearest locality" --latitude 49.1675 --longitude 20.0675 --confidence medium \
  --heading 215 --taken 2019-06..2019-09 --taken-confidence medium --taken-basis "full foliage, 2018 panorama lacks the kiosk"
```

`--heading` and `--taken` are required; `unknown` is a valid value for either, and the answer then says why. With no
verification artifact in the session, `finish` refuses before 25 minutes have passed (run the decisive check or go
Deep); it also refuses while a check required by recon's scene tags (skyline for mountains or water, street for a
city or road) has left no file — `photo_session.py checks <session>` lists them; `--skip-check <name>:"<reason>"`
is allowed early only for a user stop; `--accept-unverified "<reason>"` closes anyway and records the reason (`result.accepted_unverified`).

```bash
```

Use the real values (those are only syntax). Without `--latitude/--longitude` the pin is the country centre with a
≥100 km radius and confidence low (`result.coordinate_source` says so); `result.verification_artifacts` counts the
rank, sheet, evidence, terrain, pose and mark files, and `finish` warns when it is zero. Add `--radius-m <m>` and
`--heading <deg>` when the answer has them, and `--taken <YYYY | YYYY-MM | YYYY-MM-DD[THH:MM] | A..B>` with
`--taken-confidence` and `--taken-basis` (the session records them; without `--taken`, `finish` warns); `session.json` stores both in the result and the `report.md` footer prints them. The folder becomes
`YYYY-MM-DD_HH-mm-ss-microseconds±HHMM__country__region__city`; `session.json` records the completion time and
result; `report.md` gets the final path and timestamps appended. Use the printed paths from then on.

## Answer format

Lead with exactly:

**Country: … | Region: … | City / nearest locality: …**

**Coordinates: 38°34'14.4"N 7°54'30.1"W (38.570667, -7.908361)**

**Taken: 2019-06..2019-09, afternoon ~15:00 local (medium: full foliage, sun 55°, the kiosk absent from the 2018 panorama)**

The place line also carries the camera heading, the direction of travel (moving platform) and the capture time
when they are known. In mainland China add a second coordinate line in the local datum (`GCJ-02: … | BD-09: …`
from `geo.py convert`), because map apps there take those, not WGS84.

Then: one confidence/accuracy line (what level is settled, what radius, what it rests on; an unverified
estimate is called an estimate); the decisive clues in a few bullets; the evidence image when there is one
(show `evidence.jpg` with the answer without being asked); an **Alternatives / Excluded / Unused clues** block
taken from `result.json` (`board.py report --merge`: each alternative with the test that separates it, each
exclusion with its file, each clue not yet explained); and last, the exact analysis timestamp with clickable
absolute links to the renamed folder and its `report.md`.

Language: tool output, report headings and labels stay English; the answer is written in the user's language;
translate high/medium/low and keep the English word in parentheses, e.g. "alta (high)".

## Learning from results

When the true location becomes known (the user says so, a puzzle answer, a game reveal):

```bash
uv run scripts/photo_session.py truth "<final folder>" --latitude … --longitude … --country "…" --region "…" --source "owner"
```

Then add whatever decided or misled the case to the matching `world/<region>.md` file, in the entry format of
[world/index.md](world/index.md). A misleading clue goes in as a counterexample to the entry that misled you.
A decisive street-level source also goes into [streetlevel.md](streetlevel.md).

## Scoring and test sets

`truth --taken YYYY-MM-DD[THH:MM]` scores the when line too: `taken_hit` (the true date inside the answered
range), `taken_error_days` (distance outside it) and `scoreboard` `taken_hit_rate`.

**Scoreboard over real sessions** (every session with a recorded truth):

```bash
uv run scripts/photo_session.py scoreboard --write     # <archive root>/scoreboard.md and scoreboard.json
uv run scripts/bench.py sessions                        # the same metrics computed by bench.py
```

It reports median error, the share of answers within 1 / 25 / 200 / 750 / 2500 km, country hit rate,
approximate world-map game score (5000·e^(−d/1492.7 km)), and calibration: how often "high", "medium" and
"low" confidence were actually right. If "high" is often wrong, tighten the confidence rules. Compare the gut
call in each report with the truth too: it shows what the tools add.

**Repeatable test sets** (GeoGuessr-style rounds with hidden truth):

```bash
uv run scripts/bench.py make-streetview --n 40 --seed 2 --out bench/sv40-seed2
uv run scripts/bench.py prior bench/sv40-seed2 --out bench/sv40-seed2/preds_prior.json      # model-only baseline
uv run scripts/bench.py score bench/sv40-seed2/preds_prior.json --truth bench/sv40-seed2/truth.json
```

- Each round: a random covered country, a random town in it (population-weighted), the nearest official
  Street View panorama within ~1 km, a random heading, 1280×800 at 90° FOV. Never show `truth.json` to the
  solver.
- To evaluate the full skill, give a fresh agent with the skill only `images/NNNN.jpg`, collect its answers as
  `{"NNNN": {"lat": …, "lon": …, "country": "XX"}}`, then `bench.py score`. Use the same seed to compare versions.
- The skill must beat the model-only baseline clearly on country and region; if it does not, find which step
  loses the information.

**Component benchmarks** (each prints its own metrics; keep the figures out of the docs):

- `bench.py match --panos <json> --radius 150 --n 8`: renders one historical capture per site as the query,
  ranks the panoramas within the radius with `match.py rank`, prints the truth rank per case.
- `bench.py satscan --cells sat.json --truth tracks.json`: recall@N and median rank of `sat_scan.py` cells
  against OSM-tagged truth.
- `bench.py terrain --n 8 --seed <n>`: synthetic skylines with and without roll; median position error of
  `terrain.py fit` untilted vs tilted.

**What to log when a case goes wrong**: which clue misled (add it as a counterexample in `world/`), which tool
output was wrong (command, file, and what the scene shows instead, in `report.md`), and whether the gut call
was better than the final answer (then find which step overrode a good instinct).

## Troubleshooting

| Symptom | Action |
|---|---|
| `uv` or `curl` not found | Install them (`doctor.py` prints the per-OS command); every script runs through `uv run`, and `geodata.py`/`doctor.py` download and probe with `curl` |
| Browser fails to start (Chrome and Playwright Chromium) | `intake.py … --no-rev` (or `recon.py --no-rev`); say in the report that reverse search was skipped |
| CAPTCHA, 403 or 429 from Yandex or Baidu | The result screenshot is saved in `rev/`; skip that engine for this photo, note it in the report, try it later in the user's browser; never retry unchanged |
| Timeouts, empty answers from a service with known coverage | `doctor.py --network`, then `sources_check.py` to tell a broken endpoint from real absence |
| Model download or load fails | Check free disk (~6 GB) and the Hugging Face cache (`~/.cache/huggingface`, `HF_HOME`); `doctor.py --models` re-downloads; `GEO_PROXY` if the download is blocked |
| A step was skipped (`--no-rev`, `--no-ml`, blocked engine) | A skipped step is not "no match": the report says "not run", never "nothing found" |
| Overpass 406 / 429 | The script backs off 30 s and retries on mirrors automatically; run one query at a time, long ones in the background |
| Google Street View thumbnails return 403 | Discovery uses coverage tiles, not the thumbnail endpoint; update the `streetlevel` package (`uv run --refresh-package streetlevel scripts/gsv.py …`) before blaming coverage |
