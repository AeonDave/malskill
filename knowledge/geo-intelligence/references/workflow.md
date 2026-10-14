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
- Device: `GEOINT_DEVICE=auto|cuda|xpu|mps|cpu` overrides the picker (auto: cuda, ROCm included, → xpu → mps → cpu).
  Linux NVIDIA (driver 580+) and Apple `mps` work in each script's own environment. Windows NVIDIA, AMD (Windows and
  Linux) and Intel Arc: `uv run scripts/doctor.py --gpu` once builds a GPU torch environment in `<shared cache>/gpu`
  (1–7 GB download, 4–16 GB on disk, smoke-tested on the GPU with the most compute units; `--gpu remove` deletes it);
  prior, detect, match, sweep and sat_scan then rerun themselves there, calib and aidet stay on the CPU. Until it
  exists those scripts print the command once per run when a GPU is found. `GEOINT_DEVICE=cpu` or a script's
  `--device cpu` skips it. The local models (~6 GB, `doctor.py --models`) live in `~/.cache/huggingface`
  and `~/.cache/torch`.
- Proxy: `GEO_PROXY=<url>|direct` routes every script.
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
- Video: `meta.py original/<clip>` first (frames lose the clip's GPS and time); then `mkdir frames`, the length in
  seconds `S` from `ffprobe -v error -show_entries format=duration -of csv=p=0 original/<clip>`, and
  `ffmpeg -i original/<clip> -vf fps=60/S -frames:v 60 frames/%03d.jpg` (60 frames spread over the whole clip, whatever
  its length); skim them and run recon on the clearest frame.

## Live view

`photo_session.py start --viewer` (or `viewer.py serve <session> --open`, any time later) serves the session on
`http://127.0.0.1:<random free port>/` (`--viewer-port` / `--port` force one), prints the URL, stores it as
`viewer_url` in `session.json` and opens it in the default browser. The
page re-reads the folder every 2 s and shows, for the user watching:

- the globe: countries on the board are highlighted by share; the top-ranked open candidate at the finest level is
  the focus and the globe turns and zooms to it, handing over to imagery tiles (Esri World Imagery; `--tiles osm` for
  OpenStreetMap) when the extent is small; after `finish`, the answer with its radius and camera heading; after
  `finish --generated`, "Generated image: no real place" with its basis, a red "generated" badge on Answer, and no
  globe target;
  after `truth`, the real spot in teal with a dashed line to the answer and the error in km; the wheel, the + and −
  buttons and dragging move the map by hand, "Follow" hands it back to the analysis; every text is selectable;
  "Close viewer" stops the server without touching the analysis;
- map layers: the top views of every `match.py rank` (position, heading, score, the saved view on click; a strong
  top match also writes a camera mark with its view cone),
  the panoramas of every `*.index.json` as the Coverage layer (off by default; switching a layer on flies the view to
  its points, one ring with the count when they are too close to tell apart; Follow returns to the analysis; a dot's
  card shows id, provider, date, road and a link that opens the panorama), and your marks: `viewer.py mark camera` (point +
  view cone; its card opens Google Street View at that position and heading), `mark line` (sight line, skyline bearing), `mark point` (anchor), `mark image <file>` (a found photo
  at its position), `mark area <file.geojson>` (any GeoJSON: Polygon, MultiPolygon, closed or open LineString,
  MultiLineString; the first 500 features, the rest dropped and reported; points skipped and reported; rings with a
  faint fill, lines plain, dashed when level or layer < 0; a name once the feature is large enough to read and does not
  overlap another; `--level L` gives features without a level tag that level; level chips, `all` then each level sorted,
  beside the layer buttons show one level plus the features without a level; display only); buttons toggle the layers, a click opens the marker's card. Images named ridge/fit/overlay/
  evidence/match/sheet/pose get their own gallery in the panel. The leading location, answer and located cards link to Google Maps;
  match cards also open nearby Street View while retaining the saved photo. `terrain.py fit --sheet` adds a Skyline card (the
  top three synthetic skylines stacked over the photo with score, heading and focal, summit names with `--peaks`);
- the panel: "Now" (the last `viewer.py say` line; under it, before `finish`, one muted line when
  `recon/aidet/aidet.json` p_ai ≥ its threshold: "Detector 0.91 generated-like: a ranking, not a verdict", replaced by
  "Operator: real, continue" once `photo_session.py not-generated` recorded the operator's word), candidates per level with shares, verified counts and exclusions,
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

Every analysis begins with the lightweight Quick phase; transitions are in SKILL.md "Session and speed".
Quick has no fixed duration. With an explicit Quick request, stop before heavy analysis and use the operator
reason for required checks skipped. Otherwise continue into Deep automatically whenever a feasible route
can still locate or refine the position; a certain country or city alone does not end that search. Keep the
same session. Every 15 minutes reread saved result lists before widening, and try to name the junction from
text and road geometry before a whole-town ranking.

Long tools are bounded, never awaited open-ended: `terrain.py fit` stops at `--budget-min` (20 min) with a partial
ranking. While scoring it rewrites fit.json at most every 30 s and after the last cluster (`status` running, with the
writing `pid` and `updated_at`), so a kill loses the clusters scored since the last save (fit prints `saved N/M`). A
`running` file whose `pid` no longer runs (`Get-Process -Id <pid>`, `ps -p <pid>`) is a dead run: continue its
`unscored_clusters` with `--select` and a new `--out`; while the pid runs, never start a second fit. `scan` prints
what its cluster count will cost. Start them in the background, read the partial result at the stop, and decide
from it.

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
city or road) has left no file — `photo_session.py checks <session>` lists them. Another geometry that pins the
place waives a missing check with a note: an `evidence*`/`match*` image (by name), a `pose.py` output (by content,
any file name: a `solve` solution or a `check` table; its input spec never), or a rank file whose top views (rows
with a saved view, else the first 10) include one within 150 m of the answer with ≥10 inliers or global score ≥0.25.
When rank files exist but none qualifies, the refusal names the strongest view (file, rank, distance, inliers,
score, its saved image) and the exits: open that view and answer there only if it shows the same fixed structures
as the photo; otherwise run the check, or skip it. `--skip-check <name>:"<reason>"` and
`--accept-unverified "<reason>"` close anyway and are recorded (`result.checks`, `result.accepted_unverified`);
before 25 minutes only when the operator stopped or redirected the analysis (the reason then starts with
`operator asked:`, an article allowed; said, confirmed or requested, or the operator's language such as
`l'utente ha chiesto:`, also count), afterwards for any stated reason. While verification files exist,
`--accept-unverified` is never refused: its reason is recorded (the agent judged the answer unverified) and `finish`
prints that it was.

Use the real values (those are only syntax). Without `--latitude/--longitude` the pin is the country centre with a
≥100 km radius and confidence low (`result.coordinate_source` says so); `result.verification_artifacts` counts the
rank, sheet, evidence, terrain, pose and mark files, plus fit outputs, street rankings and panorama sheet indexes
recognised by content; recon's first pass (its outputs beside any `recon.json`, or under `recon/` mid-run) and
detect.py sheets never count; `finish` warns when it is zero. `result.supporting_artifacts` counts the files that
support the answer's location: the pins above, tested at the answer (a `pose.py` solve only with its camera within
150 m), a `sweep.py` ranking whose first 10 rows hold one within 150 m with `sim_full` ≥0.25, and a fit output whose
leading cluster's tie stretch (`tie.bbox`, else its best camera) lies within one grid step of the pin. A check that
ran and matched nothing is verification, not support: when verification files exist but none supports, `finish`
closes and warns "no check supports this location", naming the next action (an `evidence.py --match` image against
the sheet cell or sweep view that shows the place, or `terrain.py fit --at <answer>` for a skyline; otherwise say so,
or `--accept-unverified "<reason>"`); the viewer's answer card reads "unverified estimate" at zero support or whenever
`accepted_unverified` is set. `finish` echoes what it stored in one `Stored result:` line (the city is `city_or_nearest_locality`). Add `--radius-m <m>` and
`--heading <deg>` when the answer has them, and `--taken <YYYY | YYYY-MM | YYYY-MM-DD[THH:MM] | A..B>` with
`--taken-confidence` and `--taken-basis` (use `unknown` when the capture date is undetermined; omitting `--taken` is refused); `session.json` stores both in the result and the `report.md` footer prints them. The folder becomes
`YYYY-MM-DD_HH-mm-ss-microseconds±HHMM__country__region__city`; `session.json` records the completion time and
result; `report.md` gets the final path and timestamps appended. Use the printed paths from then on.

Running `finish` again on a completed session is the correction path (an operator's correction, a heading or date found
later): every gate runs as before, so pass the full flags again. The first `completed_at` stays; the replaced result goes to
`session.json` `result_history` as `{replaced_at, result}`, plus `truth_metrics` (its own score) when a truth was recorded;
the footer gains `Amended: <time>` after `Analysis completed:`; the folder name follows the new answer (place or
`--generated`, either way). The truth is rescored against the new answer, so `truth`, report.md's Ground truth block, the
scoreboard and the viewer always score the current answer.

`finish "<folder>" --generated "<basis>"` closes a generated image with no real place: no place flag (with one, or
with `--skip-check`/`--accept-unverified`, it exits 2), folder `<timestamp>__generated-image`, `result.outcome`
`generated`, coordinates null, `result.generated` = {basis, score, model, skipped, override}. The basis is the term
`recon/meta/meta.md` declares, a session file you saved that shows the generation (named by path), or the operator's
words starting the basis (`operator asked: …`); a detector score, or an aidet.py record wherever it is saved, is
refused. While meta declares generation (trainedAlgorithmicMedia or algorithmicMedia as the only source type), a place
`finish` is refused unless a file pins the place (evidence or match image, `pose.py` output, near fair ranked view: it
then prints a Note) or `photo_session.py not-generated "<folder>" "operator asked: it is real, continue"` recorded the
operator's word (`generated_override` in `session.json`; the reason starts with `operator asked:`). Once recorded, or
while a file pins the place (the same pins as above; a ranked view is tested against the finished answer), the declared
term alone no longer closes as generated: new operator words or a saved file do. The detector score never refuses
anything.

## Answer format

Lead with exactly:

**Country: … | Region: … | City / nearest locality: …**

**Coordinates: 38°34'14.4"N 7°54'30.1"W (38.570667, -7.908361)**

**Taken: 2019-06..2019-09, afternoon ~15:00 local (medium: full foliage, sun 55°, the kiosk absent from the 2018 panorama)**

The place line also carries the camera heading, the direction of travel (moving platform) and the capture time
when they are known. In mainland China add a second coordinate line in the local datum (`GCJ-02: … | BD-09: …`
from `geo.py convert`), because map apps there take those, not WGS84.

Radius floors: a skyline fit → at least half the span of the tied positions `fit` prints; a settled venue (building,
station, mall, campus, park whose OSM name matches the identified venue) → `osm.py geom` it with its named entrances
into one GeoJSON (`'["name"~"<venue>"]' --bbox <block>` usually catches both) and run `geo.py bearings --at <pin>
--geojson <file>`: the largest `far` (metres from the pin to the farthest vertex) is the floor; if the footprint may
be partial, never go below a round estimate. The venue floor applies while nothing places the camera inside it: a
shopfront or unit read in the frame and placed on the map sets the radius to the distance at which that sign is legible
(usually ≤150 m; ≤100 m still needs hard rule 8).

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

For an image that turns out to be generated: `uv run scripts/photo_session.py truth "<final folder>" --generated
--source "…"` (no coordinates).

Then add whatever decided or misled the case to the matching `world/<region>.md` file, in the entry format of
[world/index.md](world/index.md). A misleading clue goes in as a counterexample to the entry that misled you.
A decisive street-level source also goes into [streetlevel.md](streetlevel.md).

## Scoring and test sets

`truth --taken YYYY-MM-DD[THH:MM]` scores the when line too: `taken_hit` (the true date inside the answered
range), `taken_error_days` (distance outside it) and `scoreboard` `taken_hit_rate`.

`truth --generated` (no coordinates) records a generated image. Each truth records `outcome` (place|generated),
`outcome_hit` and `false_stop`: a generated answer against a place truth is a false stop, and a place answer against a
generated truth is a missed generation. Sessions without a distance (either side generated) stay out of the median,
the within-km shares, the mean game score and the calibration. `scoreboard` and `bench.py sessions` add
`generated: {called, confirmed, false_stops, missed}`, and `scoreboard.md` prints it as one line. `list` and the
scoreboard show such sessions as "generated image (no place)". A result or truth without `outcome` counts as a place.

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
