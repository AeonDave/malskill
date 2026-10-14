---
name: geo-intelligence
description: "Geolocate or chronolocate a photo, screenshot, video frame or street-level/GeoGuessr image: which country, city, street, camera position and heading, and when it was taken. Use for any 'where is this / where was this taken / when was this taken' request, OSINT location checks, image verification, and puzzle rounds. Also 这是哪 / 在哪拍的 / 图寻 / 网络迷踪, \"c'est où ?\", \"¿dónde es esto?\", \"وين هادي\"."
license: MIT
compatibility: "Python 3.10+, uv, curl; exiftool and ffmpeg recommended. Network for OSM, tiles, panoramas and reverse image search (local Chrome or Playwright Chromium). Optional local ML models (~6 GB) for prior, detect, calib, sweep and match. Windows, macOS, Linux."
metadata:
  author: AeonDave
  version: "1.0"
  category: knowledge
---

# Geo Intelligence

Find where and when an image was taken, to the finest level the evidence supports, and prove it. Your eye proposes, files prove: every claim points at a clue, the command that tested it and the file it produced. The answer is one place with coordinates, error radius, heading, a when line, confidence per level, alternatives with the test that separates them, and an evidence image.

Who does what:
- **You** read the image, decide which features locate it and in what order to test them, and judge among the machines' top results.
- **Scripts** perceive, rank and measure; open only their top few results.
- **`board.py` and `finish`** keep score and gate the close (rules marked ★, the required checks, the verdict). When they refuse or advise, do what they print.
- **The operator** outranks all three (Hard rules).

`${CLAUDE_SKILL_DIR}` is this skill's folder. Claude Code substitutes it; other agents `export CLAUDE_SKILL_DIR=<absolute path>` first. Inside `references/`, `scripts/x.py` means `${CLAUDE_SKILL_DIR}/scripts/x.py`. Run every script with `uv run`; read `<script> --help` before its first use instead of guessing flags or spec formats.

## Scope and authorization

- Locate places, objects, events and public imagery. When the subject is a private individual, a private residence or a minor and the request carries no stated purpose or authorization, ask once what it is for; with a stated purpose (verification, assessment, puzzle, the user's own photo) proceed without asking.
- Otherwise work end to end without questions: reverse image search, web search, maps, OSM and street-level lookups are pre-approved. Resolve ambiguity by judgment and record the assumption in `report.md`. A blocked service (CAPTCHA, rate limit) is skipped and noted, never retried unchanged.
- Keep API keys and tokens out of saved files and command lines.

## Session and speed

Each photo, or set of photos of one scene (`--image` repeated), gets its own archive before any analysis:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py start --image "/abs/path/photo.jpg" --viewer   # prints the folder; creates report.md and board.json; opens the live page
cd "<that folder>"                                                                                # every output lives here
```

- Several photos of one scene: one board; tag each clue `--file original/<photo>`; run each check on the photo that shows it best (skyline from the widest view, sun from the sharpest shadow); recon on another photo only with `--out-dir recon_<stem>`. `--beside` when the user wants the work next to the image.
- Live page: `viewer.py say "<what you are doing now>"` at every step change; `board.py country <cc>` as soon as the country is settled. Put a mapped lead on the board and mark its anchor immediately, labelled with its current evidence status. Once a working camera and heading have a basis, show its estimated cone with `viewer.py mark camera --lat … --lon … --heading … --fov …` and refine it during verification. When replacing a single working camera estimate, clear its old cone first (`viewer.py mark clear --kind camera`); retain multiple cones only for deliberate alternatives. Other marks: `workflow.md` "Live view". Marks are display only: the answer is what `finish` records.

Every search starts with Quick: the lightweight routes most likely to locate a clear image. Quick is a category of work, not a ten-minute deadline. An explicit Quick request limits the analysis to that phase; a normal request to find the location continues into Deep automatically when needed. Say which phase you are in; never ask "shall I go on?".

- **Quick**: gut call and plan → recon → the inexpensive, selective plan lines → `board.py country <cc>` once settled → `board.py check`. Use readable text, metadata, reverse search, maps, reference photos and small targeted comparisons as the frame warrants; there is no fixed count of checks. Large model downloads, broad panorama indexing, large terrain fits and bulk scans belong to Deep; judge cost from the actual inputs and cache, not the command's name. Never sweep around an unidentified lead (step 3).
- Before a verified close: recon (with its prior unless it cannot load or `models.md` says to ignore it for this image; use `--skip prior` and record why; `--no-ml` when a sign already names the place), `board.py country <cc>` for the answer, one check that leaves a file (`evidence.py --match`, `refsheet.py`, a panorama sheet, `match.py rank`, a `fit` run), and the scene checks in step 6. For an explicit Quick request, skip any step that requires heavy work with the operator reason below; missing verification makes the answer an unverified estimate.
- After a decisive result, run `board.py check`. Finish when the camera position, or the level the user explicitly requested, is settled by evidence (`Verdict: certain` plus step 9 confidence medium or better). Otherwise continue useful lightweight plan lines. When the next useful route would be heavy, or those lines are exhausted:
  1. The user explicitly requested Quick → stop before heavy work, report the supported level, what remains unknown and which Deep test would resolve it. For `finish`, record missing checks with `--skip-check <name>:"operator asked: Quick, stop before heavy analysis"` and, if needed, `--accept-unverified "operator asked: Quick, stop before heavy analysis"`. If no country is supportable, save the unresolved report and viewer snapshot and leave the session pending; never invent a place to satisfy `finish`.
  2. Otherwise, if any feasible route could separate candidates or place the answer finer → say "going Deep: <next test>" and continue in the same session. A certain country or city alone does not end a request to find the position while a finer route remains.
  3. No feasible route remains → conclude at the supported level and explain the missing evidence.
- **Deep**: continue down the plan in the same folder and board. Run a route only if a possible result could change the answer or its confidence (no sun table without measurable shadows, no panoramas that cannot see the spot); this never waives a check `finish` requires. When the plan is exhausted, add the step 6 routes the frame supports. Complete the When ladder and evidence image. Continue until the requested position is found, an explicit operator limit is reached, or no feasible action remains (the conclude rule below); elapsed Quick time is never a reason to stop.
- **Strong data is a shortcut, not a reason to skip verification.** Text that names a unique place (sign, shop, phone) with one consistent gazetteer hit → straight to step 6 around it; keep the one check that could still falsify it (a reference photo of the same view, the same shapes on satellite).

## Hard rules

The operator outranks every rule and gate below. A stop ("give me what you have"), an explicit Quick request, a redirect ("skip the skyline", "try Y first"), a budget or a format wish is followed at once, without argument, and recorded as the reason (`--accept-unverified "operator asked: …"`, `--skip-check <name>:"operator asked: …"`). The gates bind the agent, never the operator. A pointer ("watch the skyline", "the building at the back matters") becomes plan line A at once: it orders the work and proves nothing. An operator can be wrong too: a claim ("it is X", "north of Bergamo") is followed as a hypothesis, recorded with `board.py clue "operator: <words>" --kind hint --status inferred` and tested like any lead, never as verification; the answer says what was verified and what rests on the operator's word.

★ = enforced by `board.py`.

1. **Gut call and plan first, written down** (step 1), before any tool; country names in English (the live view and the lookups resolve them).
2. **Never fabricate verification.** "Matched on street view", "measured", "±20 m" must correspond to commands run and files produced in this session; otherwise write "unverified estimate".
3. **The image wins.** EXIF, filenames, captions, IP labels and puzzle hints are hypotheses; when they conflict with the scene, believe the scene and say why.
4. **Models rank, evidence decides.** World prior, CLIP rankings, detector scores, the AI-image score and search-engine AI answers (the pages they cite are trails) order hypotheses (board status `model`, likelihood ratio ≤3). They never prove, exclude, stop or close anything, and never overturn the gut call on their own: gut call Italy, prior Austria and no evidence either way is an undecided board, not an Austrian answer.
5. ★ **List the whole category before choosing.** "Left-hand traffic", "Cyrillic", "hill town", "IP in municipality X" each define a set: put the whole set on the board (`apply`, `children`, `ingest`, `geodata.py towns`) and let evidence rank it. Fame and population are not evidence.
6. ★ **Exclusion needs the same standard as confirmation.** Only read text or a computed result with a file excludes, and only over the extent the evidence covers (`exclude --covers`). Observed and inferred clues and third-party labels only down-weight (`evidence --against`). "I did not see X" first needs `geo.py frame`. Link a computed result to the clue it tests (`--resolves K3`); a finer candidate sits under the one that contains it (`add --parent`).
7. ★ **One answer, no midpoints.** Report the top-ranked candidate; alternatives carry the test that separates them. Never average rival places.
8. **Precision needs two independent constraints.** Radius ≤100 m needs two of: sight-line intersection, alignment line, solved pose, ground-level match on ≥3 invariant features, a reverse-direction street-level match. Validate a solved pose on independent points with `pose.py project`; for other camera constraints, run the bearing and side checks in `verify.md` §3.
9. **Once you have a unique anchor, close the loop from it**; do not drift back to generic features ("blue-green lake", "tropical park") or to look-alike places.
10. **Compute bearings before naming structures** (`sun.py compass`, `geo.py bearings`): which blob on the satellite is "the tower" is itself a hypothesis (`verify.md` §3).
11. **Self-consistency.** Redo each decisive judgment once with another crop, query, tool or photo (never a Quick minimum or gate); results tens of kilometres apart lower the tier.
12. **No Google Street View is not "no street level".** Probe every provider (`pano.py coverage`) and the local panorama sites (`streetlevel.md` §1–3).
13. **Sweep towns, don't sample them.** When geometry cannot narrow further, index and rank every panorama of the candidate town (`sweep.py`, `streetlevel.md` §4), when it fits the time ("Budget and stopping").
14. ★ **Scan order is share ÷ pages** (`board.py next`): small districts first, large ones last with a page cap; never scan candidates one by one while they are still inseparable.

## Flow

Skip what the evidence already settled. The plan decides which route runs first; steps 3–6 describe the routes.

### 1. Gut call and plan (2 minutes, no tools)

Fixed things locate (buildings, house numbers, signs, poles, curbs, pavement, trees); movable things (cars, vans, bikes, people, shop carts) only date the capture or hint at the country through livery and plates, never at the spot. Look at the whole frame, then every edge and corner, and look for the small things: a far sign, a plate, the building behind the wall (recon's crops and `imgprep.py zoom` show them after; revise the plan then). The eye goes to the biggest object; the smallest often locates. Background anchors constrain the camera: from a candidate camera position, one identified landmark gives a heading (`geo.py frame`); locating the camera requires independent geometry (rule 8). Plan the background as a line, not as scenery. Strongest exclusions first: sun and hemisphere, biome and soil, driving side and road paint, poles and street furniture, script and sign families, plates, roofs and walls, the image itself (phone, street-view car, drone, scan; mirrored text; season). Checklist: `references/observe.md`. Be honest with the percentages: `truth` scores them later.

Then the plan: the 1–3 fixed features that leave the smallest piece of the world, most selective first, each with what it can leave and the route that tests it. Narrowing power first, cost breaks ties; an operator pointer goes above everything. Default order:

| Feature in the frame | Can leave | Route |
|---|---|---|
| Text that names a place (sign, shop, phone, domain); two or more chain shops together | a point, a street or a venue | step 3 lookups (chains: the venue on every brand's store list, `search.md` §2), then step 6 around the place |
| A place you recognise (one place, not a pick among look-alikes), or a reverse-search near-duplicate | a spot | one reference (geotagged photo, panorama) compared on fixed features: `evidence.py --match` |
| A one-of-a-kind fixed thing (building, facade, monument, bridge, facility), however small | a spot, once identified | crop and identify it (step 3), then its step 6 row |
| A mountain skyline, a lake shore or coast under mountains | a stretch of road or shore | step 6 skyline rows |
| A route number, railway, power line, big river | a stretch of corridor | step 6 corridor rows |
| Street fabric, or a rare attribute you are sure of (house number, bus lane, tree species) | a town, then a street | steps 4–5, a dataset filter, then panoramas |
| A regional plate code | a region (cars travel) | step 4 lookups |
| Only style (biome, architecture, furniture) | a country or region | step 4 |

Sun and shadows give a heading, a time or a test of candidates, never the first route while a fixed feature can be tested; with a trusted capture time a measured shadow gives a band (`sun.py locate`), and a dish's azimuth a longitude (`sun.py dish`). With nothing fixed and selective in the frame (a private garden, a plain interior), write `Plan: none selective`: the answer will be coarse; verify the level the image supports (`refsheet.py countries` for the country, `refsheet.py regions` or `tiles.py sheet` for a region) and name what would pin it (the original file, a wider view).

Replace the `<!-- fill … -->` line under `## Gut call (before tools)` in `report.md` with (percentages only on the country lines):

```
## Gut call (before tools)
1. Portugal 55% — calçada sidewalk, whitewash with yellow trim, EU plate shape
2. Spain 25% — similar roofs; no yellow curb paint
Region hunch: Alentejo
Would change my mind: a Spanish-language sign, Mercosur plate
Plan:
A. shop sign top left, half legible → a street → step 3 reading set, then poi.py in the town
B. church tower behind the roofs → a spot → crop, reverse search, sight line
C. calçada pattern, yellow kerb paint → a town → refsheet.py towns
```

Keep the plan current under `## Evidence`, the gut call left as written: a place name recon reads, a near-duplicate hit or a new anchor found on the way moves up (below an operator pointer); a model prior never reorders it (rule 4); each line ends done with its file, or dropped with the reason.

### 2. Recon (one local command)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/recon.py original/<photo> --out-dir recon       # about 2 minutes on CPU: 10-minute timeout, or run it in the background
```

One command runs the whole first pass (metadata, edge and corner crops, OCR, reverse image search, text → country, object crops, camera calibration, world prior and scene tags, AI-image score) and ingests its signals into the board; never run its parts one by one first. No `recon/recon.md` means it has not finished. Read `recon.md`, open every crop it lists at full size, then reconcile with the gut call: agreement → run the plan; disagreement → find out why before moving on (OCR misread, unusual scene, wrong gut). `--skip calib` for a close-up. What each model output is worth: `references/models.md`.

### 3. Read everything, search the web (biggest lever)

- A string read from a blurred crop is a set of readings, not a reading: resolve each one with every homonym listed (`poi.py <name> --limit 20`; `geodata.py search <name> --country XX --deep` for villages below the cities500 cut) and keep only the readings whose places are within about 15 km of each other; a name with no coherent neighbours is a misread (re-read the crop with `imgprep.py reveal`, try the other letters that fit the shapes), never a lead to chase.
- Every legible string is a query, in the local language, in quotes, with and without the suspected town: shop and street names, slogans, bus destinations, permit boards. `textgeo.py` resolves phones (`--phone-pattern` for unreadable digits), domains, postal codes, currency, brands and place names; house numbers → `osm.py addr` (`datasets.md`). Dark or flat text → `imgprep.py reveal` before calling it illegible. Issuing authorities at the bottom of signs often name the district.
- Reverse search runs every time: recon did Yandex + Baidu on the original and its crops; with a browser tool, also Google Lens, Bing Visual Search and TinEye on the original (`search.md` §1).
- Identify an anchor before using it, in this order, and drop it only after all three: (1) tight crop → `intake.py original/<photo> --box x0,y0,x1,y1 --out-dir rev_crop` (only the crop is searched), and the browser engines on the crop; (2) `revimg.py --query "<settled town> <the distinctive part's noun>" --query "<…> <attribute>" --country XX --out-dir q` in the local language, all queries in one call: the 2–3-word one first (the town and the noun), then one attribute per further `--query` (a colour, a material, a second part), never a foreground feature; open both screenshots of each engine (`qNN_<engine>.png` and `_2.png`) for a photo of a matching object; your own web search complements it (engines per country: `search.md` §1); (3) map lists by class as leads. A common class (many chimneys, many churches) does not make the object common: the combination of its features is what is one of a kind. It is identified when a reference photo of it matches on ≥3 invariant features. A result that names a specific place is a named lead: put it on the board (`board.py add <name> --level area`), search its name for current photos (a thumbnail may predate a renovation), then look at it from the ground (a panorama sheet within ~150 m facing it); drop it only on that ground view, recorded with `evidence --against` and the file. An `osm.py find` class list is a set of unnamed leads (only what is mapped) that never identifies it: before any sweep around one, a z18 tile or a short panorama sheet must show its setting fits the frame; no fit → back to identifying the object.
- Read the whole result list before chasing the top hit: visual matches rank by look, the right place often sits at rank 10–20; open first the places two independent results name. A hit is the start of a trail (caption, album, map check), not a location; a page that names a place proves the name, not the view: pair it with one comparison file. Where to search by object type: `references/search.md`.

### 4. Country (when the plan's finer lines did not settle it)

Follow `references/country-funnel.md`: discriminators ordered by how much of the world they exclude, look-alikes compared against real imagery, not memory; then the region file in `references/world/`. Recon has already put its text and prior signals on the board.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py apply --kind driving-side --value left          # whole category on the board (observed: ranks, never excludes)
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py clue "red laterite, eucalyptus" --kind vegetation --status observed --file recon/intake/edges/e1.jpg
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py evidence --clue K5 --for Kenya:3 --for Uganda:3 --against "South Africa":0.5 --why "…"
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py rank && uv run ${CLAUDE_SKILL_DIR}/scripts/board.py next     # stuck → run the test next names
uv run ${CLAUDE_SKILL_DIR}/scripts/refsheet.py countries KE,UG,TZ --n 6 --out ref.jpg       # real street-view rows per country
```

Likelihood ratios: observed shapes and colours 2–5, inferred 1.5–3, read text 5–20, computed geometry up to 50; record evidence against candidates too. Codes: `clues.py lookup <kind> <value> [--country XX]`, kinds `plate-code` (regional codes with eras: IT ES FR DE AT CH GR TR GB MA), `plate` and `area-code` (China), `calling-code`, `driving-side`, `territories`, `coverage`; without `--country` every table is searched; a code that resolves to an admin division goes straight on the board (`board.py apply --kind plate --value 粤B --file <crop>`). A country on the board: `regions.py show <cc>` prints its card; once settled, `board.py country <cc>`.

### 5. Region, town, neighbourhood

- Lists, then evidence: `board.py children "<country or region>"`; `geodata.py towns <CC> --admin1 "<region>" --json > towns.json`; compare them at one scale (`tiles.py sheet --points towns.json --zoom 15 --size 640`) and on the ground (`refsheet.py regions "ES:Andalusia,ES:Galicia"`, `refsheet.py towns --points towns.json --pitch -12`: street furniture is bought per city).
- Named places → `poi.py "<name>" --city <town>`; every same-name hit goes on the board (`board.py add --from pois.json --level area`). A town read from a sign: `board.py clue "<text>" --kind text --status read --file <crop>`, `board.py add <Town> --level city --parent <Country>`, `board.py evidence --clue K<n> --for <Town>:20`, then `board.py country <cc>`.
- **Turn the rarest clue you are sure of into a filter** (`references/datasets.md`): filter on the one attribute you are sure of, rank by the rest; `osm.py coverage` first, because sparse areas drop out silently.
- Cheap discriminating tests before any scan (`board.py next` names them).

### 6. Pinpoint

Recon's `Scene:` line names the checks `finish` requires, whatever else you find: **skyline** for mountains or water without a city (a `terrain.py fit` or `view --overlay` output), **street** for a city or a road (a `match.py`/`sweep.py` ranking, a panorama sheet beside its `.index.json`; aerial or no street-level coverage: `evidence.py` on the `tiles.py` map with camera and heading); `ridge`, `scan`, `refsheet.py` and `tiles.py` sheets alone are not. `photo_session.py checks <session>` lists them and their status. They are a floor, not the plan: run them after line A unless line A leaves their file, long ones in the background. A file that shows the photo matched at the answer waives them with a note: a match image whose pairs show ≥3 invariant features against a reference of the same view, a `pose.py` solution, or a ranked view near the answer that `match.py` scores fair (`workflow.md` "Finish"). An evidence map must show the compared scene features and bearing check for the satellite-only route; a pin and cone alone illustrate a hypothesis (rule 2).

| What you have | Approach | Read |
|---|---|---|
| A unique anchor, identified (building, statue, tower) | sight lines, alignment, tangents, camera height: `geo.py intersect/line`, `pose.py` | `geometry.md` |
| Mountains or skyline | `terrain.py ridge` → `fit` (render and compare) `--at <candidate>`, or `--hits` from a scan (the shore chain, the linear-infrastructure row), then a second constraint; no EXIF → do not assume the main camera. `fit` prints the span of the positions that tie with the best: the answer goes on the road, shore or building inside that stretch, radius at least half the span | `geometry.md` §7.4 |
| Lake, coast or valley floor with a mountain skyline, no text | the shore chain below; one region at a time, the gut-call region first, `--bbox` no larger than about 2° × 2° (a whole mountain arc makes Overpass time out: split it) | `corridors.md` §4.3 |
| Shadows, sun in frame, lit faces, a dish | `sun.py locate/when/facing/compass/dish`; a mountain's shadow, or one side of a street in shade → `terrain.py shade --time … --check` | `sky.md` |
| Route number, railway, power line, big river | `osm.py route/crossings/along/near/intersect` | `corridors.md` |
| Linear infrastructure + unidentified mountains, no text | `terrain.py scan --lines` → `ridge` → `fit` → `imgprep.py piers` → `geo.py spacing` | `corridors.md` §4.3, `geometry.md` §7.7 |
| Street layout, no anchor | `osm.py street-scan` → `tiles.py sheet` → street level | `corridors.md` §4.2 |
| Scene elements only (field + road + coast) | `sat_scan.py grid --bbox … --zoom 17 --query …`; look at the top 20–30 cells only | `search.md` §7 |
| Recognisable facility class (track, silo, dam, plant) | `osm.py buildings/find` → `sat_scan.py points --preset …`; `gsv.py targets` → `match.py rank` | `search.md` |
| ≥3 known points in frame | `pose.py solve` (`calib.py` FOV/pitch as start); `pose.py check --cands`; only Δchi² > 9 may exclude | `geometry.md` §10 |
| "X is not in the photo" | `geo.py frame` before excluding | `geometry.md` §11 |
| Candidate streets to check | `gsv.py sheet --points … --along/--headings`, `pano.py sheet` (any provider); `match.py rank` orders them | `verify.md` |
| One or a few candidate towns, no anchor | `pano.py list` every source → `sweep.py index` → `sweep.py rank --index t1 t2 …` → clusters → `sweep.py view` | `streetlevel.md` §4 |
| No Google coverage | `pano.py coverage`; local and historical panorama sites in local languages; photo spheres, Mapillary, KartaView in the browser; a manifest | `streetlevel.md` §1–3 |
| Old photo (years to decades) | oldest street-level imagery per town, `tiles.py wayback`, full sweep; verify structure, not inliers | `streetlevel.md` §5 |
| Motorway scene, shot from a vehicle | `osm.py along --line '["highway"="motorway"]'` → `gsv.py sheet --points … --along --offset 180`; barriers, reflectors, dash pattern; state the direction of travel | `corridors.md` |
| Mainland China | `baidu_pano.py` panoramas, `poi.py` (360 Maps), GCJ-02 ↔ WGS84 `geo.py convert` | `world/china.md`, `data-sources.md` |
| Plane window or drone | registration, seat side, sun heading, hydrology, `terrain.py view` from altitude | `aerial.md` |
| Inside a known venue | shop, unit and gate names as filters on OSM indoor data | `datasets.md` "Inside a venue" |

The shore chain (the plain-oriented defaults reject every lake shore; a valley floor uses `'["waterway"="river"]'` and a larger `--cam-level`, since the camera stands above the river: `fit` warns when the level filter drops most positions):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/osm.py geom '["natural"="water"]["name"]["water"!~"^(river|canal|stream|ditch|drain|riverbank|oxbow)$"]' --bbox <region> --out lakes.geojson   # lakes, not river areas
uv run ${CLAUDE_SKILL_DIR}/scripts/terrain.py scan --lines lakes.geojson --near-radius 400 --near-flat 80 --flat-run 0 --max-low 2 --min-peak <half the photo's highest ridge angle> --out scan.json
uv run ${CLAUDE_SKILL_DIR}/scripts/terrain.py ridge original/<photo> --x0 <rock skyline start> --x1 <end> --hrow <far waterline row> --out ridge.json
uv run ${CLAUDE_SKILL_DIR}/scripts/terrain.py fit --hits scan.json --ridge ridge.json --cam-flat 10000 --cam-level 6 --radius 700 --grid 120 --zoom 12 --sheet top.jpg --out fit.json   # background
```

`fit` stops at `--budget-min` (20) with a partial ranking: read it at the stop, continue `unscored_clusters` with `--select` and a new `--out` only if the leaders are not separated (dead runs: `workflow.md` "Clock"), then run the `view … --overlay` command it prints; the shore and cliff shapes on satellite separate the survivors.

Street level: compare **invariant** features (building outlines, window spacing, pole positions, curbs, ridgelines), never cars, signs or foliage; ≥2 unique features for road level, ≥3 plus two constraints for building level. Low SIFT inliers do not reject a candidate (season, old capture, sidewalk vs road).

### 7. When (after where, always)

Climb the ladder as far as the evidence goes and record each rung in `## When` with its clue and file. "Not determinable" with the reason is a valid rung; "not asked" is not: the answer always carries a when line.

| Rung | How | Read |
|---|---|---|
| Metadata | `recon/meta/meta.md`: capture time, UTC offset and the countries that had it that day; a hypothesis (rule 3): screenshots, re-saves and games strip it | `meta.py` |
| Ceiling | earliest date this exact image (not another photo of the place) provably existed: its first post (+1 day for time zones), TinEye's earliest crawl, a Wayback snapshot containing it → `--taken ..YYYY-MM-DD`; a copy older than the claimed event = recycled photo | `search.md` "After a hit" |
| Year or range | what the photo shows that dated imagery lacks, and vice versa (`gsv.py` history, `tiles.py wayback`, `pano.py` dates); signs, shops and works with known dates; the newest vehicle, plate or sign format as a lower bound | `streetlevel.md` §5, `world/general.md` |
| Season | foliage, crops, snow, clothing, daylight length, sun too high or low for a season | `sky.md` §4 |
| Date | `sun.py when --dates` from shadow elevation and bearing; dated notices and events; `sun.py weather` ranks days, `tiles.py --source gibs:<date>` shows that day's satellite pass | `sky.md` §4, §6 |
| Time of day | `sun.py when --date` from shadows; `terrain.py shade --date … --lit … --shaded …`; clocks, shop hours, lights on | `sky.md` §4, §7 |

### 8. Verify, falsify, red-team

Before calling it (`references/verify.md`): never reject a road or area lead on how the landscape "should" look: render three panoramas along it (`osm.py geom` → `gsv.py sheet --points … --along`, one minute) and compare; memory of a region is not evidence. Write 2–3 falsification conditions before looking at the candidate; run the bearing self-check (left/right order, near/far occlusion, heading vs sun); redo the decisive step once (rule 11). For hard or high-stakes cases, hand a fresh sub-agent only the photo and your answer and ask for the strongest reason it is wrong. The `board.py check` verdict measures how well the candidates on the board are separated, not whether the answer is true.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py check                       # exclusions have files? unused clues? skipped levels? Verdict: certain or uncertain
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py report --merge result.json  # main answer = top-ranked; alternatives, exclusions, unresolved clues
uv run ${CLAUDE_SKILL_DIR}/scripts/evidence.py spec.json --out evidence.jpg          # satellite + camera wedge + comparison panels
uv run ${CLAUDE_SKILL_DIR}/scripts/evidence.py match.json --out match.jpg --match    # numbered feature pairs photo ↔ reference
```

### 9. Answer and archive

Rate each level separately and report the finest level rated medium or better:

| Level | High | Medium | Low |
|---|---|---|---|
| Country | read text, plates, phone, or a confirmed anchor | several independent visual clues agree | gut or a single clue |
| Region / city | regional code, named place, or reference sheets that clearly separate | consistent clues, alternatives unchecked | hunch |
| Area | a unique facility matches ≥3 top-down features, whole candidate area checked | most similar spot, candidates unchecked | inferred |
| Street | ground-level match on ≥2 unique features | layout fits + 1 feature; or, with no ground imagery at all, area high + bearing self-check passed (a satellite-only road claim needs a ≥z18 crop in the evidence image) | satellite layout only |
| Building / camera point | two independent constraints + ≥3-feature match | one of the two | estimate |
| Floor | two kinds of reference agree | one reference | do not give |
| When | metadata whose offset fits the place, or an imagery bracket of a year or less plus a sun date or time | one dated bracket, or sun time alone | season or era from looks only |

Fill `## Answer` and `## When` in `report.md` first (`finish` refuses a placeholder), then lead the answer with the format in `references/workflow.md` "Answer format", in the user's language, source text verbatim with a translation. When only a city or region is settled, pin the best-supported specific area inside it snapped to a real road, never a midpoint between rivals; if nothing inside is better supported, the frame still weighs: an urban street pins the area's largest town on a road, otherwise the population-weighted centre (`geodata.py regions <CC>`); either way the radius covers the whole settled area. Radius floors (fit tie span, a venue's footprint): `workflow.md` "Answer format".

```bash
cd .. && uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py finish "<session folder>" --country … --region … --city … --latitude … --longitude … --confidence high|medium|low --heading <deg|unknown> --taken <when|unknown> [--radius-m <m> --taken-confidence … --taken-basis "…"]   # from outside the folder: the rename fails while a shell sits inside it
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py truth "<folder>" --latitude … --longitude … --country …   # when the real answer becomes known
uv run ${CLAUDE_SKILL_DIR}/scripts/viewer.py stop "<folder>"                                                       # after finish, never before, unless the user wants the page kept
```

- `finish` is the only way to close a session: never edit `session.json` by hand. A correction after the close: update `report.md`, then run `finish` again with the full flags.
- A refusal names the next command and the exits (`--skip-check <name>:"<reason>"`, `--accept-unverified "<reason>"`): run the command, or take an exit with a real reason. Before 25 minutes only the operator's word is one (a reason starting "operator asked: …"), including an explicit Quick request; an agent-invented time budget never is. Gates, pins and what is recorded: `workflow.md` "Finish".
- `--heading` and `--taken` are mandatory. Heading sources, in order: a landmark identified in the frame (`geo.py frame --at <answer> --anchor <name>:<lat,lon>:px=<its pixel column> --width <photo width> --hfov 45:70`), a matched panorama, the road or corridor bearing when the photo looks along it (two opposite headings: take the one that puts the read shopfronts or house numbers on the side the map puts them), `sun.py compass`; write `unknown` only after none of them applied. A year that `## When` says dates or bounds the photo must be encoded (`2019`, `2015..`, `..2019`, `A..B`), never left as `unknown`; a reference panorama's, page's or file's own date is not the capture date; a season without a year stays `--taken unknown` with the season in `--taken-basis`.
- Nothing you started may outlive the analysis: before `finish`, every background job (`match.py`, `sweep.py`, `gsv.py`, scans) has ended or been killed (on Windows an open process inside the folder blocks the rename); after the answer, `viewer.py stop`.

## Special situations

- **Street View / game screenshots**: `references/world/streetview.md` (camera generation, car and mount tells, coverage, © year is the display year). © Google visible → `board.py apply --kind coverage --value streetview`; only looks like Street View → add `--status observed`. Skip `calib.py`: horizon = centre row unless pitched, FOV ≈ the viewer's setting. The smear at the bottom is the blurred car, not a shadow.
- **Historical photos, scans, postcards**: the world prior is useless; architecture, vehicles, text, archives; old regional plates (`clues.py lookup plate-code` gives province and years); the oldest street-level imagery per town, `tiles.py wayback`, historical aerials (`data-sources.md`); sweep a black-and-white photo as it is, never colourised.
- **Indoor, close-up, product shots**: text, plugs and sockets, packaging, provenance, reverse search, metadata. Inside a known venue, sign names are filters and the plan is drawn by level (`datasets.md` "Inside a venue").
- **Generated image?** Only evidence closes a session as generated: the file declares it (recon/meta "File declares generated content (<term>)"), an AI-gallery page from the reverse search that you opened, saved and confirmed on fixed features, or the operator → `finish "<session folder>" --generated "<term | saved file | operator words>"` (`workflow.md` "Finish"). A detector score of 0.65 or more, visual tells, or both give "possible generated image, unconfirmed": continue and say so in the report. "AI-edited real photo" is a real photo: continue; the edited regions are not evidence. A C2PA manifest alone, or none, proves nothing. The operator's "it is real, continue" is followed at once and recorded (`photo_session.py not-generated "<session folder>" "operator asked: …"`); a file that pins a real place wins too (rule 3).
- **Puzzles (图寻 / 网络迷踪)**: setters pick obscure places; uniform priors, distrust fame; `world/china.md`.
- **No street-level coverage anywhere**: make sure first (rule 12), then satellite scan, terrain and ground photos from news, encyclopedias, Commons geosearch (`verify.md` §4).
- **Video**: `meta.py` on the clip first (frames lose its GPS and time), then 60 frames spread over the whole clip (`workflow.md` "Start"); recon on the clearest frame.

## Budget and stopping

- Reverse search: three different crops or queries with nothing useful → back to the image.
- A lead unconfirmed after ~15 minutes: reread every saved result list and the places they name before widening.
- Look only at the machines' top results (top 30 satellite cells, top 10 `match.py` images, top 15–40 sweep hits and their clusters); widen only when all of them are wrong.
- Street-level ranking is the expensive step (about 1 s per rendered view on CPU: a village at 4 headings is 10 minutes, five villages an hour). Let geometry name the spot first (sign arrows, road names, `osm.py` junction, `poi.py directions`), then rank only the panoramas within ~150 m of it at 8 headings; a whole-town sweep only when geometry cannot narrow (rule 13) and the listing time plus the ETA `sweep.py index` prints after its first 16 panoramas (panoramas × measured s/panorama) fits the remaining time; kill the index when it does not, and identify the anchor instead (step 3: tight crop and a local-language description with the settled town) before concluding at city level. Low MegaLoc similarities prompt a check of the top views, headings, dates and coverage before changing the set; they do not prove absence (rule 4). `sweep.py`'s `score` is a relative z-score; its raw similarity is `sim_full`.
- `osm.py coverage` before enumerating with OSM; "0 results" from a busy Overpass server is not absence (rerun, use a mirror or `--bbox`). Sparse OSM area → `sat_scan.py grid` on it, and state the gap.
- A failed service blocks one route, not the investigation.
- Conclude when the result is certain at the camera position or at the level the user named, an explicit Quick request reaches the boundary before heavy work, the user's budget is reached, or no plan line and no feasible action can still separate the candidates or place the answer finer; a count of unmatched areas is never a stop reason. Then state the settled level, actual search coverage, attempted routes, blockers and what would settle the rest. Never invent a coordinate or precision to finish.

## Toolbox (`uv run ${CLAUDE_SKILL_DIR}/scripts/<name>`)

| Script | Use it for |
|---|---|
| `photo_session.py` | `start`, `checks`, `finish` (`--generated`), `not-generated`, `truth`, `scoreboard`, `list --status pending` to resume |
| `viewer.py` | live page: `serve <session> --open` (reopen), `say`, `mark camera/line/point/image/area`, `state`, `stop` |
| `recon.py` | the whole local first pass in one command |
| `meta.py` | metadata, GPS (XMP, video, DJI), UTC offset → countries, embedded previews, provenance flags |
| `intake.py`, `ocr.py`, `imgprep.py`, `revimg.py` | crops, OCR, `zoom`, `reveal`, `piers`; Yandex + Baidu reverse image search; `--query --country` local keyword image search |
| `textgeo.py` | text → script, language, phones, domains, postal codes, currency, brands, places |
| `geodata.py`, `gazetteer.py` | country facts, GeoNames search, `towns`, `regions`, national gazetteers, admin hierarchies |
| `clues.py`, `regions.py` | lookups (plate codes with eras, area codes, calling codes, driving side, territories, coverage); country cards |
| `board.py` | candidates, clues, evidence, exclusions; `children`, `apply`, `ingest`, `country`, `retract` (a clue recorded by mistake), `move`, `urban`, `falsify`, `rank/next/check/report` |
| `prior.py`, `detect.py`, `calib.py`, `aidet.py` | world prior and scene tags, object crops, FOV/pitch/horizon, AI-image score: all model status |
| `refsheet.py` | real street-view rows per country, region or town |
| `pano.py`, `gsv.py`, `baidu_pano.py` | street-level coverage, lists, history, renders and sheets for every provider and your own manifests |
| `sweep.py`, `match.py` | index and rank every panorama of a town; rank views against the photo |
| `osm.py`, `poi.py`, `opendata.py` | Overpass queries and geometries, place names and nearby POIs, city open data |
| `tiles.py`, `sat_scan.py`, `evidence.py` | satellite and map mosaics (Wayback, Sentinel-2, GIBS daily), CLIP-ranked satellite scans, evidence and match images |
| `terrain.py`, `sun.py`, `geo.py`, `pose.py` | skylines, scans and shade; sun, shadows and weather; bearings, frames, conversions; camera pose |
| `doctor.py`, `sources_check.py` | environment and models; live known-answer probes of every external endpoint |

## Runtime notes

- `doctor.py --network` on first use or after a failure; `doctor.py --models` pre-downloads the local models; `doctor.py --gpu` once, with the user's consent, when a script reports a GPU (1–7 GB download, 4–16 GB on disk). Device, caches and proxy: `workflow.md` "Paths and settings".
- Quote arguments with double quotes: an apostrophe inside single quotes (`'Oya's'`) breaks the command, and wrappers may show no error at all; a `say`, `clue` or `evidence` that printed nothing did not happen.
- Overpass: one query at a time, long ones in the background. Windows and macOS have no `timeout`: run long jobs in the background (zsh does not word-split `$var`: use `bash -c`).
- OCR misses whole scripts on some backends; `recon.md` and `textgeo.md` say when: read such text yourself and run `textgeo.py --text "…"`.
- A source that returns nothing where coverage is known: `sources_check.py` tells a broken endpoint from real absence.

## Resources

- `references/workflow.md` — archive layout, live view and marks, clock, `report.md`, finish gates and exits, answer format, scoring. Load before `finish` or when it refuses, when resuming a session, and for the answer format.
- `references/observe.md` — image-reading checklist by exclusion power, platform and mirroring checks, negative clues. Load for the gut call and after recon.
- `references/country-funnel.md` — discriminator order, board habits, look-alike separation, region and town, scripts and letters. Load when the country or region is open.
- `references/world/index.md` → `general.md`, `europe.md`, `americas.md`, `asia.md`, `oceania.md`, `africa-middle-east.md`, `china.md`, `streetview.md` — the clue library; load the file for the shortlist's region, `streetview.md` only for game or Street View screenshots.
- `references/search.md` — reverse and keyword image search, where to search by object type, social media, after a hit. Load when a text or an object needs searching.
- `references/datasets.md` — clue → dataset filter recipes (OSM tags, addresses, open data, Overture, inside a venue). Load once a city or venue is known and a rare clue exists.
- `references/streetlevel.md` — the coverage ladder, providers, manifests for sites you find, town sweeps, verifying across years. Load when a town is in play.
- `references/geometry.md` — FOV, horizon, distance, bearings, sight lines, skylines, pier spacing, heights, `pose.py`, `geo.py frame`. Load for any anchor or mountain pinpoint.
- `references/sky.md` — sun, shadows, lit faces, dishes, time and date, weather by day. Load when shadows, the sun or a date matter.
- `references/corridors.md` — route numbers, railways, power lines, rivers, crossings, infrastructure × terrain and shore scans. Load for linear infrastructure or a shore.
- `references/aerial.md` — plane-window and drone photos. Load for the aerial branch.
- `references/verify.md` — falsification, red team, invariant features, bearing self-check, confirming without street view, historical imagery, final checklist. Load before concluding.
- `references/models.md` — what each local model is good for, the AI-image score, OCR coverage. Load when a model output surprises you.
- `references/data-sources.md` — endpoints, coordinate systems (WGS84/GCJ-02/BD-09), imagery sources, archives, licences. Load when a source fails or China is involved.
- `assets/data/index.md` — sources, dates and licences of the offline lookup tables; `scripts/tests/` — regression suites.
