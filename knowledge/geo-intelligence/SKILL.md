---
name: geo-intelligence
description: "Geolocate or chronolocate a photo, screenshot, video frame or street-level/GeoGuessr image: which country, city, street, camera position and heading, and when it was taken. Use for any 'where is this / where was this taken / when was this taken' request, OSINT location checks, image verification, and puzzle rounds. Gut call first, then metadata, OCR, text-to-country, reverse image search, world-prior models, a candidate board with evidence rules, OpenStreetMap, satellite, terrain, sun and street-level sweeps, ending in coordinates with an error radius and tiered confidence. Also 这是哪 / 在哪拍的 / 图寻 / 网络迷踪, \"c'est où ?\", \"¿dónde es esto?\", \"وين هادي\"."
license: MIT
compatibility: "Python 3.10+, uv, curl; exiftool and ffmpeg recommended. Network for OSM, tiles, panoramas and reverse image search (local Chrome or Playwright Chromium). Optional local ML models (~6 GB) for prior, detect, calib, sweep and match. Windows, macOS, Linux."
metadata:
  author: AeonDave
  version: "1.0"
  category: knowledge
---

# Geo Intelligence

Find where (and when) an image was taken, to the finest level the evidence supports, and prove it: every claim points at a clue, the command that tested it and the file it produced. Output is one best answer with coordinates, error radius, heading, tiered confidence, alternatives with the test that separates them, and an evidence image.

Two halves work together: the player's eye (read soil, light, road paint, poles, plates, script, architecture in seconds and commit to a ranked guess) and the investigator's discipline (text, search, maps, street-level imagery and geometry; never claim more than the files show). Your own knowledge of the world is the first instrument, the web is the second, the scripts make you faster and measure what eyes cannot.

`${CLAUDE_SKILL_DIR}` is this skill's folder. Claude Code substitutes it; other agents `export CLAUDE_SKILL_DIR=<absolute path>` first. Inside `references/`, `scripts/x.py` means `${CLAUDE_SKILL_DIR}/scripts/x.py`. Run every script with `uv run` (each declares its dependencies).

## Scope and authorization

- Locate places, objects, events and public imagery. When the subject is a private individual, a private residence or a minor and the request carries no stated purpose or authorization, ask once what it is for before continuing; with a stated purpose (verification, assessment, puzzle, the user's own photo) proceed without asking.
- Otherwise work end to end without questions: reverse image search, web search, maps, OSM and street-level lookups are pre-approved. Resolve ambiguity by judgment, record the assumption in `report.md`, continue. A blocked service (CAPTCHA, rate limit) is skipped and noted, never retried unchanged.
- Keep API keys and tokens out of saved files and command lines.

## Session and speed

Each photo, or set of photos of one scene (`--image` repeated), gets its own archive, created before any analysis (details: `references/workflow.md`):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py start --image "/abs/path/photo.jpg" --viewer   # prints the folder, opens the live page
cd "<that folder>"                                                                                # every output lives here
```

`--viewer` opens `http://127.0.0.1:8765/` in the user's browser: a globe that turns and zooms to the leading candidate, the board, every new file and `report.md`, refreshed every 2 s (`references/workflow.md` "Live view"). Keep it truthful: `uv run ${CLAUDE_SKILL_DIR}/scripts/viewer.py say "<what you are doing now>"` at every step change (one line each); candidates reach the globe only with coordinates (`board.py add --bbox` or `--from pois.json`; countries are placed automatically). `start` creates `board.json` (never run `board.py init` again) and `recon.py`, run from the session folder, ingests its text and prior signals into it (status-capped), so the board is never empty; your own clues and evidence go on top. Until the first candidate is on the board the globe shows the gut call read from `report.md`; from then on it follows the board, so in quick mode too, once the country is settled, `board.py country <cc>` (one line: it adds the country candidate and settles the level) keeps the page truthful. `match.py rank --out` puts its top views on the map by itself; after a decisive computation add what it proved: `viewer.py mark camera --lat … --lon … --heading … --fov …` (the view cone), `mark line --from … --bearing … --km …` (a sight line, a skyline bearing), `mark point` (an anchor), `mark image <file> --lat … --lon …` (a found photo).

Pick a speed and say which you used:
- **Quick** (default for game screenshots and casual "where is this"): gut call → recon → one to three decisive checks → answer. Minimum before `finish`: recon (its prior runs unless the models cannot load; a sign that already names the place is the one case for `--no-ml`), `board.py country <cc>` for the country you answer, and one check that leaves a file (`refsheet.py`, `gsv.py sheet --along`, `tiles.py sheet`, `match.py rank`); without such a file the answer is an unverified estimate and `finish` says so. It has a clock: about 10 minutes of tools, then the answer at the level reached with an honest radius; one more block of the same size only when a decisive test is already named. A wrong village after 40 minutes is worse than a right region after 8. Never ask the user whether to go on: when the clock runs out, `finish` with the level reached and name the next step in the answer.
- **Deep** (exact spot wanted, OSINT, a photo the user cares about, or quick checks disagree): the full funnel to the camera position with evidence images. Escalate whenever decisive checks contradict each other.
- **Strong data is a shortcut, not a reason to skip verification.** Read text that names a unique place (sign, shop, plate code, phone) and one gazetteer hit consistent with the scene → go straight to step 6 around it; skip the funnel, keep the one check that could still falsify it.

## Hard rules

Each rule exists because skipping it produced a wrong answer. Rules marked ★ are enforced by `board.py`.

1. **Gut first, written down.** A ranked shortlist with percentages goes into `report.md` before any tool runs, country names in English (the live view and the lookups resolve them).
2. **Never fabricate verification.** "Matched on street view", "measured", "±20 m" must correspond to commands run and files produced in this session; otherwise write "unverified estimate".
3. **The image wins.** EXIF, filenames, captions, IP labels and puzzle hints are hypotheses; when they conflict with the scene, believe the scene and say why.
4. **Models rank, evidence decides.** World prior, CLIP rankings, detector scores and reverse-search "AI overviews" order hypotheses (board status `model`, likelihood ratio ≤3); they never prove or exclude.
5. ★ **List the whole category before choosing.** "Left-hand traffic", "Cyrillic", "hill town", "IP in municipality X" each define a set: put the whole set on the board (`apply`, `children`, `ingest`, `geodata.py towns`) and let evidence rank it. Fame and population are not evidence.
6. ★ **Exclusion needs the same standard as confirmation.** Only read text or a computed result with a file excludes, and only over the extent the evidence covers (`exclude --covers lat,lon[:lat,lon]`; negative coordinates are accepted, the `--covers=lat,lon` form also works; the script rejects coverage below half). Observed and inferred clues only down-weight (`evidence --against`, ratios clamped). Third-party labels (a tree inventory species, a school-name match) only down-weight. "I did not see X" first needs `geo.py frame`. A computed result tests a clue only when linked (`clue … --status computed --resolves K3`); a finer candidate sits under the one that contains it (`add --parent`, `move`), and `check` fails on skipped levels.
7. ★ **One answer, no midpoints.** Report the top-ranked candidate; alternatives carry the test that separates them. Never average rival places.
8. **Precision needs two independent constraints.** Radius ≤100 m needs two of: sight-line intersection, alignment line, solved pose, ground-level match on ≥3 invariant features, a reverse-direction street-level match. Run `pose.py project` as a self-check before reporting a camera position.
9. **Once you have a unique anchor, close the loop** from it; do not drift back to generic features ("blue-green lake", "tropical park").
10. **Compute bearings before naming structures** (`sun.py compass`, `geo.py bearings`): which blob on the satellite is "the tower" is itself a hypothesis; try original/mirrored and sunrise/sunset templates before excluding.
11. **Self-consistency.** Redo each decisive judgment once with a different crop, query or tool; results tens of kilometres apart lower the tier.
12. **No Google Street View is not "no street level".** Probe every provider (`pano.py coverage`), then search the web in local languages for national, local and historical panorama sites and turn them into manifests (`references/streetlevel.md`).
13. **Sweep towns, don't sample them.** Once a source covers a candidate town, index every panorama and rank them all (`sweep.py`); a 15 % sample misses the answer 85 % of the time.
14. ★ **Scan order is share ÷ pages** (`board.py next`): small districts first, large ones last with a page cap; never scan candidates one by one while they are still inseparable.

## Flow

Skip steps the evidence already settled; every result goes on the board in deep mode.

### 1. Gut call (60 s, no tools)

Scan the full frame, then every edge and corner, coarse to fine, strongest exclusions first: sun/hemisphere, biome and soil, driving side and road paint, poles and street furniture, script and sign families, plate shapes, vehicles, roofs and walls, the image itself (phone vs street-view car vs drone vs scan; mirrored text; season). Checklist: `references/observe.md`. Replace the `<!-- fill … -->` line under `## Gut call (before tools)` in `report.md` with:

```
## Gut call (before tools)
1. Portugal 55% — calçada sidewalk, whitewash with yellow trim, EU plate shape
2. Spain 25% — similar roofs; no yellow curb paint
Region hunch: Alentejo
Would change my mind: a Spanish-language sign, Mercosur plate
```

### 2. Recon (one local command)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/recon.py original/<photo> --out-dir recon       # ~30–60 s after the first run
```

`recon.py` is the one local first-pass call; do not run its parts one by one first. Runs in parallel: deep metadata (`meta.py`), edge/corner crops + OCR with language detection + Yandex/Baidu reverse image search (`intake.py`), text → country signals (`textgeo.py`), object crops (`detect.py`), camera calibration (`calib.py`), world prior (`prior.py`). Read `recon/recon.md`, open the crops it lists at full size, then reconcile with the gut call: agreement → decisive checks; disagreement → find out why before moving on (OCR misread, unusual scene, misjudged feature). What each piece is worth: `references/models.md`. `--no-ml` for a readable street sign, `--skip calib` for a close-up. Video: extract keyframes first (`ffmpeg -i clip.mp4 -vf "select='gt(scene,0.3)'" -vsync vfr frames/%03d.jpg`).

### 3. Read everything, search the web (biggest lever)

A string read from a blurred crop is a set of readings, not a reading: resolve each one with every homonym listed (`poi.py <name> --limit 20`; `geodata.py search <name> --country XX --deep` for villages below the cities500 cut) and keep only the readings whose places are within about 15 km of each other; a name with no coherent neighbours is a misread (re-read the crop with `imgprep.py reveal`, try the other letters that fit the shapes), never a lead to chase. Every legible string is a query, in the local language, in quotes, with and without the suspected town: shop and street names, slogans, bus destinations, permit boards, taxi numbers. `textgeo.py` resolves phones (`--phone-pattern "6941 2?7788" --country GR` for unreadable digits), domains, postal codes, currency, brands (~19k, the `brands/` part of the OSM name-suggestion-index, with countries of operation) and place names (`--country XX --deep` for the national gazetteer). House numbers → `osm.py addr --area <town> --number 145` (`--number 214,226 --within 60` for two numbers on one street). Dark or flat text → `imgprep.py reveal` before calling it illegible. Issuing authorities at the bottom of signs often name the district.

Reverse image search runs every time: recon already did Yandex + Baidu on the original and crops; rerun on a tight crop of a distinctive object (`intake.py original/<photo> --box x0,y0,x1,y1 --out-dir rev_crop`); Google Lens, Bing Visual Search and TinEye through the user's browser when a browser tool exists (upload or `lens.google.com/uploadbyurl?url=…`). Read the whole result list before chasing the top hit: visual matches rank by look, the right place often sits at rank 10–20; open first the places two independent results name. A hit is the start of a trail (caption, album, map check), not a location. Where to search by object type: `references/search.md`.

### 4. Country (when 1–3 did not settle it)

Follow `references/country-funnel.md`: discriminators ordered by how much of the world they exclude (text → driving side → plate shape → road paint → sign family → sun/latitude → biome → infrastructure → architecture → vehicles → world prior), then look-alikes compared against real imagery, not memory:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py apply --kind driving-side --value left          # whole category on the board (observed: ranks, never excludes)
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py ingest recon/textgeo.json                       # text signals, capped by status
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py ingest recon/prior/prior.json                   # model status: ranks only
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py clue "red laterite, eucalyptus" --kind vegetation --status observed --file recon/intake/edges/e1.jpg
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py evidence --clue K5 --for Kenya:3 --for Uganda:3 --against "South Africa":0.5 --why "…"
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py rank && uv run ${CLAUDE_SKILL_DIR}/scripts/board.py next
uv run ${CLAUDE_SKILL_DIR}/scripts/refsheet.py countries KE,UG,TZ --n 6 --out ref.jpg       # real street-view rows per country
```

Then read the regional file in `references/world/` (strongest tells first, "commonly confused" at the end). Once a country is a candidate, `regions.py show <cc>` prints its card (lookup tables, preferred street-level script, map datum, discriminating tests); once settled, `board.py country <cc>` so `apply` and `next` use that country's tables and tips. Likelihood-ratio habits: observed shapes/colours 2–5, inferred 1.5–3, read text 5–20, computed geometry up to 50; record evidence against candidates too. Lookups: `clues.py lookup plate-code PA --country IT` (regional plate codes with the years in use for IT, ES, FR, DE, AT, CH, GR, TR, GB, MA), `lookup plate 粤B` / `lookup area-code 0755` (China, city level), `calling-code`, `driving-side`, `territories`, `coverage`; a lookup without `--country` searches every country table and returns all matches. Codes that resolve to an admin division go straight on the board: `board.py apply --kind plate --value 粤B --file <crop>`.

### 5. Region, town, neighbourhood

- Codes and languages: regional plate codes, area codes, postal codes, road-number prefixes, bilingual signage (`country-funnel.md` §4).
- Lists, then evidence: `board.py children "<country or region>"` adds every subdivision; `geodata.py towns <CC> --admin1 "<region>" --json > towns.json` lists every sizable town; `tiles.py sheet --points towns.json --zoom 15 --size 640` compares their fabric at one scale; `refsheet.py regions "ES:Andalusia,ES:Galicia"` and `refsheet.py towns --points towns.json --pitch -12` compare them on the ground (street furniture is bought per city).
- Named places in the text → `poi.py "<name>" --city <town>` (same-name hits all go on the board with `board.py add --from pois.json --level area`). A town read from a sign goes on the board with the clue that named it and the country declared, three lines: `board.py clue "Липецк on the sign" --kind text --status read --file <crop>`, `board.py add Lipetsk --level city --parent Russia` (the parent country is added if missing; bare city names are placed from GeoNames so the map follows), `board.py evidence --clue K<n> --for Lipetsk:20`; then `board.py country RU`, which settles the country level (rivals become superseded, not excluded). A finer candidate that carries evidence leaves the coarser rivals with nothing supported below them dormant (share 0, `rank` says "dormant", never excluded: they return if the finer one falls); a bare name below a candidate changes nothing.
- **Turn the rarest clue you are sure of into a filter** (`references/datasets.md`): house numbers, speed-limit signs, a school beside a playground (`osm.py addr/find/near`), a coloured bus lane, a street-tree species, hydrants (`opendata.py`), Overture Maps buildings and places where OSM is thin. Filter on the one attribute you are sure of, rank by the rest; `osm.py coverage` first, because sparse areas drop out silently.
- Cheap discriminating tests before any scan (`board.py next` names them): lookup tables → terrain (plain vs hill, `tiles.py fetch --zoom 13`) → vehicle livery → street fixtures → river/road-network templates.

### 6. Pinpoint (deep mode)

| What you have | Approach | Read |
|---|---|---|
| A unique anchor (building, statue, tower) | sight lines, alignment, tangents, camera height: `geo.py intersect/line`, `pose.py` | `geometry.md` |
| Mountains or skyline | `terrain.py view/ridge/scan/fit` render-and-compare; one sight line, then a second constraint; no EXIF → do not assume the main camera | `geometry.md` §7.4, `corridors.md` §4.3 |
| Shadows, sun in frame, lit faces, a dish | `sun.py locate/when/facing/compass/dish` | `sky.md` |
| A date, or "which day?" | `sun.py weather` (past cloud/sun/rain/snow, rank days); `tiles.py --source gibs:<date>` for that day's satellite pass | `sky.md` §6 |
| Route number, railway, power line, big river | `osm.py route/crossings/along/near/intersect` | `corridors.md` |
| Linear infrastructure + unidentified mountains, no text | `terrain.py scan --lines` → `ridge` → `fit` → `imgprep.py piers` → `geo.py spacing` | `corridors.md` §4.3, `geometry.md` §7.7 |
| Street layout, no anchor | `osm.py street-scan` → `tiles.py sheet` → street level | `corridors.md` §4.2 |
| Scene elements only (field + road + coast) | `sat_scan.py grid --bbox … --zoom 17 --query …` ranks cells; look at the top 20–30 only | `search.md` §7 |
| Recognisable facility class (track, silo, dam, plant) | `osm.py buildings/find` → `sat_scan.py points --preset …`; `gsv.py targets` → `match.py rank` | `search.md` |
| ≥4 known points in frame | `pose.py solve` (position, heading, height; `calib.py` FOV/pitch as start); `pose.py check --cands`; only Δchi² > 9 may exclude | `geometry.md` §10 |
| "X is not in the photo" | `geo.py frame` before excluding | `geometry.md` §11 |
| Candidate streets to check | `gsv.py sheet --points … --along/--headings`, `pano.py sheet` (any provider), `match.py rank` orders them | `verify.md` |
| One or a few candidate towns, no anchor | `pano.py list` every source → `sweep.py index` → `sweep.py rank --index t1 t2 …` → clusters → `sweep.py view` | `streetlevel.md` §4 |
| No Google coverage | `pano.py coverage`; local/historical panorama sites in local languages; Maps photo spheres, Mapillary, KartaView in the browser; a manifest | `streetlevel.md` §1–3 |
| Old photo (years to decades) | oldest street-level imagery per town, `tiles.py wayback`, full sweep (MegaLoc copes with decades), verify structure not inliers | `streetlevel.md` §5 |
| Motorway scene, shot from a vehicle | `osm.py along --line '["highway"="motorway"]'` → `gsv.py sheet --points … --along --offset 180`; match barriers, reflectors, dash pattern; from a moving platform, state the direction of travel | `corridors.md` |
| Mainland China | `baidu_pano.py` panoramas, `poi.py` (360 Maps), GCJ-02 ↔ WGS84 `geo.py convert` | `world/china.md`, `data-sources.md` |
| Plane window or drone | registration, seat side, sun heading, hydrology, `terrain.py view` from altitude | `aerial.md` |

Street level: compare **invariant** features (building outlines, window spacing, pole positions, curbs, ridgelines), never cars, signs or foliage; ≥2 unique features for road level, ≥3 plus two constraints for building level. Low SIFT inliers do not reject a candidate (season, old capture, sidewalk vs road); across years they are noise.

### 7. Verify, falsify, red-team

Before calling it (`references/verify.md`): never reject a road or area lead on how the landscape "should" look: render three panoramas along it (`osm.py geom` → `gsv.py sheet --points … --along`, one minute) and compare; memory of a region is not evidence, and a guide's spotlight is a lead worth that minute. Write 2–3 falsification conditions before looking at the candidate; run the bearing self-check (left/right order, near/far occlusion, heading vs sun); redo the decisive step with another crop or tool; for hard or high-stakes cases hand a fresh sub-agent only the photo and your answer and ask for the strongest reason it is wrong. Then:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py check                       # exclusions have files? unused clues? skipped levels?
uv run ${CLAUDE_SKILL_DIR}/scripts/board.py report --merge result.json  # main answer = top-ranked; alternatives, exclusions, unresolved clues
uv run ${CLAUDE_SKILL_DIR}/scripts/evidence.py spec.json --out evidence.jpg          # satellite + camera wedge + comparison panels
uv run ${CLAUDE_SKILL_DIR}/scripts/evidence.py match.json --out match.jpg --match    # colour-coded feature lines photo ↔ reference
```

### 8. Answer and archive

Rate each level separately and report the finest level rated medium or better:

| Level | High | Medium | Low |
|---|---|---|---|
| Country | read text, plates, phone, or a confirmed anchor | several independent visual clues agree | gut or a single clue |
| Region / city | regional code, named place, or reference sheets that clearly separate | consistent clues, alternatives unchecked | hunch |
| Area | a unique facility matches ≥3 top-down features, whole candidate area checked | most similar spot, candidates unchecked | inferred |
| Street | ground-level match on ≥2 unique features | layout fits + 1 feature; or, with no ground imagery at all, area high + bearing self-check passed (a satellite-only road claim needs a ≥z18 crop in the evidence image) | satellite layout only |
| Building / camera point | two independent constraints + ≥3-feature match | one of the two | estimate |
| Floor | two kinds of reference agree | one reference | do not give |

Fill `## Answer` in `report.md` first (finish refuses a placeholder), then lead the answer with the fixed format in `references/workflow.md` (bold place line, bold coordinates in DMS and decimal, one confidence/radius line, decisive clues, evidence image, analysis timestamp with links to the folder and `report.md`), in the user's language, source text verbatim with a translation. When only a city or region is settled, pin the best-supported specific area inside it snapped to a real road, never a midpoint between rivals; if nothing inside is better supported, the population-weighted centre (`geodata.py regions <CC>`) with an honest radius. Then:

```bash
cd .. && uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py finish "<session folder>" --country … --region … --city … --latitude … --longitude … --confidence high|medium|low [--radius-m <m> --heading <deg>]   # from outside the folder: the rename fails while a shell sits inside it
uv run ${CLAUDE_SKILL_DIR}/scripts/photo_session.py truth "<folder>" --latitude … --longitude … --country …   # when the real answer becomes known
uv run ${CLAUDE_SKILL_DIR}/scripts/viewer.py stop "<folder>"                                                       # after the answer, unless the user wants the page kept
```

`finish` is the only way to close a session: never edit `session.json` by hand. Prefer a road-snapped point inside the settled area with a radius that honestly covers the alternatives (rule 7, answer format); `finish` without `--latitude/--longitude` pins the country centre with a radius of at least 100 km, confidence low, and records that. It also counts the session's verification artifacts and warns when there are none. Give `--heading` whenever you know where the camera looked (the matched panorama's heading, the road bearing when the photo looks along the road, `sun.py compass`): the view cone on the map needs it. `finish`, `truth`, `viewer.py stop` and the page's Close button all save `viewer.html` beside the photos, the page as one offline file. Nothing you started may outlive the analysis: before `finish`, every background job (`match.py`, `sweep.py`, `gsv.py`, scans) has ended or been killed (on Windows an open process inside the folder blocks the rename); after the answer, `viewer.py stop`. The viewer also exits by itself after 30 minutes without a reader.

## Special situations

- **Street View / game screenshots**: `references/world/streetview.md` (camera generation, car and mount tells, coverage, © year is the display year). Coverage is a prior: apply `board.py apply --kind coverage --value streetview` at default weight when the © Google watermark is visible; add `--status observed` when it only looks like Street View. Skip `calib.py`: horizon = centre row unless pitched, FOV ≈ the viewer's setting. The smear at the bottom is the blurred car, not a shadow.
- **Historical photos, scans, postcards**: world prior is useless; architecture, vehicles, text, archives, dating clues; old regional plates (`clues.py lookup plate-code` gives province and years); the oldest street-level imagery per town, `tiles.py wayback`, historical aerials (`data-sources.md`); sweep a black-and-white photo as it is, never colourised.
- **Indoor, close-up, product shots**: text, plugs and sockets, packaging, provenance, reverse search, metadata.
- **Puzzles (图寻 / 网络迷踪)**: setters pick obscure places; uniform priors, distrust fame; `world/china.md`.
- **No street-level coverage anywhere**: make sure first (`pano.py coverage`, local sites, photo spheres), then satellite scan + terrain + ground photos from news, encyclopedias, Commons geosearch (`verify.md` §4).

## Budget and stopping

- Quick mode stops when one decisive check confirms the gut call at the level asked for.
- Reverse search: three different crops or queries with nothing useful → back to the image.
- A lead unconfirmed after ~15 minutes: reread every saved result list and the places they name before widening.
- Look only at the machine's top results (top 30 satellite cells, top 10 `match.py` images, top 15–40 sweep hits and their clusters); widen only when all of them are wrong, but sweep a town completely before calling it a miss, then the next town.
- Street-level ranking is the expensive step (CPU: about 1 s per rendered view; a village at 4 headings is 10 minutes, five villages an hour). Let geometry name the spot first (sign arrows + road names + `osm.py` junction, `poi.py directions`), then rank only the panoramas within ~150 m of it at 8 headings (2 minutes); whole-village ranking is for deep mode or when geometry cannot narrow. A MegaLoc global score below ~0.3 across a whole village means the panorama is not in that set: change the set, not the thinning.
- Run `osm.py coverage` before enumerating with OSM; a "0 results" from a busy Overpass server is not absence (rerun, use a mirror or `--bbox`). Sparse OSM area → `sat_scan.py grid` on it, and state the coverage gap in the conclusion.
- A failed service blocks one route, not the investigation. Conclude when the requested level is supported, the user's budget is reached, or no feasible action can still separate the candidates; a count of unmatched areas is never a stop reason. Then state the settled level, actual search coverage, attempted routes, blockers and missing evidence. Never invent a coordinate or precision to finish.

## Toolbox (`uv run ${CLAUDE_SKILL_DIR}/scripts/<name>`)

| Script | Use it for |
|---|---|
| `photo_session.py` | archive `start/finish`, `truth`, `scoreboard`, `list --status pending` to resume |
| `viewer.py` | live page for the user: `serve <session> --open`, `say "<step>"` (what you are doing), `mark camera|line|point|image` (what the map shows), `state`, `stop`; `photo_session.py start --viewer` starts it |
| `recon.py` | the whole local first pass in one command |
| `meta.py` | metadata (exiftool or pure-Python fallback), GPS incl. XMP/video/DJI, UTC offset → countries on that date, filename/platform hints, embedded previews, motion-photo video, AI-provenance flags |
| `intake.py`, `ocr.py`, `imgprep.py`, `revimg.py` | crops, variants, OCR (auto language), `zoom`, `reveal`, `piers`; Yandex + Baidu reverse image search, Chinese keyword image search |
| `textgeo.py` | text → scripts, letters, language, phones (`--phone-pattern`), domains, postal codes, currency, regional words, brands, places |
| `geodata.py` | country facts, aliases, GeoNames search/reverse/sample, `towns`, `regions`, national gazetteers |
| `clues.py`, `regions.py` | lookups: plate codes with eras, China plates/area codes/admin, calling codes, driving side, territories, coverage; `regions.py list/show <cc>` country cards and lint of the data packs in `assets/data/regions/` |
| `board.py` | candidates, clues (`--resolves`), evidence (capped by status), exclusions with coverage, `children`, `apply`, `ingest`, `retract`, `move`, `country`, `urban`, `falsify`, `rank/next/check/report` |
| `prior.py`, `detect.py`, `calib.py` | StreetCLIP + GeoCLIP world prior (ranking only), OWLv2 object crops, GeoCalib FOV/pitch/roll/horizon |
| `refsheet.py` | real street-view rows per candidate country, region or town, side by side |
| `pano.py` | every scriptable street-level provider (Google, Apple, Bing, Yandex, Naver, Kakao, Mapy, Já, KartaView, Panoramax, Mapillary) and your own manifests: `coverage/list/render/sheet` |
| `sweep.py` | index every panorama of one or more towns, MegaLoc rank, clusters, `view` reproduces the photo |
| `gsv.py`, `baidu_pano.py`, `match.py` | Google and Baidu discovery, history, rendering, sheets; MegaLoc/DINOv2/CLIP + SIFT ranking |
| `osm.py`, `poi.py`, `gazetteer.py` | Overpass queries (`find/addr/near/crossings/route/along/intersect/street-scan/buildings/coverage/geom`), place names and nearby POIs by category, routing distance and timezone, admin hierarchies |
| `opendata.py` | city open-data portals (Socrata catalogue, any CSV/GeoJSON): `search/columns/get --points/points` |
| `tiles.py`, `sat_scan.py`, `evidence.py` | satellite/map mosaics (Google, hybrid, Esri, Bing, Esri Wayback since 2014, Sentinel-2 by year, NASA GIBS daily), `sheet`, `mark`, `wayback`, `px2ll`; CLIP-ranked satellite scans; evidence and match images |
| `terrain.py`, `sun.py`, `geo.py`, `pose.py` | skylines and scans, sun/shadows/weather, bearings/frames/conversions/spacing, camera pose |
| `bench.py`, `refresh.py` | street-view test sets with hidden truth, model-only baseline, scoring; maintainer refresh of the lookup tables from their sources |
| `doctor.py`, `sources_check.py` | environment and model check; live known-answer probes of every external endpoint (run when a tool returns nothing or before a long scan) |

## Runtime notes

- `doctor.py --network` on first use or after a failure; `doctor.py --models` pre-downloads the local models (~6 GB in `~/.cache/huggingface` and `~/.cache/torch`). Shared data caches live in `$GEOINT_CACHE` (default `~/.cache/geoint`; on Windows `%LOCALAPPDATA%\geoint`); per-photo caches in `.geo-cache/` inside the session folder; `GEO_PROXY=<url>|direct` routes every script.
- GPU: `GEOINT_DEVICE=cuda|mps|cpu|directml|auto` overrides the device picker; NVIDIA → CUDA automatically; AMD on Linux → install ROCm PyTorch wheels (they appear as `cuda`); AMD on Windows → `uv run --with torch-directml` plus `GEOINT_DEVICE=directml` (experimental, some transformers ops fall back to CPU); Apple → `mps`.
- Reverse image search uses local Chrome, falling back to Playwright Chromium (`uvx playwright install chromium`); if neither starts, `intake.py --no-rev` and say so. OCR: Apple Vision on macOS, RapidOCR elsewhere (RapidOCR ignores `--langs` and may drop Latin diacritics: confirm accented words on the crop). OCR does not read Greek, Hebrew, Georgian, Armenian, Indic scripts, Sinhala, Khmer, Lao, Burmese or Ethiopic: read those yourself and pass them to `textgeo.py --text`.
- Public Overpass servers throttle parallel queries: run them one at a time, long ones in the background. Province-wide queries can take minutes.
- Windows: no `timeout`; use PowerShell or run long jobs in the background. macOS: no `timeout` either; zsh does not word-split `$var` (use `bash -c`).
- Unofficial endpoints change (Google already retired one Street View lookup). When a source returns nothing where coverage is known, run `sources_check.py` to tell a broken endpoint from real absence, and update the `streetlevel` package first.

## Resources

- `references/workflow.md` — archive layout, live view, autonomy defaults, `report.md` contents, answer format, scoring with `truth` and `scoreboard`, `bench.py` test sets. Read once per session.
- `references/observe.md` — image-reading checklist by exclusion power, platform and mirroring checks, negative clues. Load for the gut call and after recon.
- `references/country-funnel.md` — discriminator order, board habits, look-alike separation, region and town, scripts and letters table. Load when the country or region is open.
- `references/world/index.md` → `general.md`, `europe.md`, `americas.md`, `asia.md`, `oceania.md`, `africa-middle-east.md`, `china.md`, `streetview.md` — the clue library; load the file for the shortlist's region, `streetview.md` only for game or Street View screenshots.
- `references/search.md` — reverse and keyword image search, where to search by object type, social media, after a hit. Load when a text or object needs searching.
- `references/datasets.md` — clue → dataset filter recipes (OSM tags, addresses, open data, Overture). Load once a city is known and a rare clue exists.
- `references/streetlevel.md` — the coverage ladder, providers, manifests for sites you find, town sweeps, verifying across years. Load when a town is in play.
- `references/geometry.md` — FOV, horizon, distance, bearings, sight lines, skylines, pier spacing, heights, `pose.py`, `geo.py frame`. Load for any anchor or mountain pinpoint.
- `references/sky.md` — sun, shadows, lit faces, dishes, time and date, weather by day. Load when shadows, the sun or a date matter.
- `references/corridors.md` — route numbers, railways, power lines, rivers, co-occurrence and crossing queries, infrastructure × terrain scans. Load for linear infrastructure.
- `references/aerial.md` — plane-window and drone photos. Load for the aerial branch.
- `references/verify.md` — falsification, red team, invariant features, bearing self-check, confirming without street view, historical imagery, candidate tables, final checklist. Load before concluding.
- `references/models.md` — what each local model is good for and how to read it. Load when a model output surprises you.
- `references/data-sources.md` — endpoints, coordinate systems (WGS84/GCJ-02/BD-09), imagery sources, archives, licences, which script talks to which service. Load when a source fails or China is involved.
- `assets/data/` — lookup tables read by `clues.py`, `geodata.py`, `textgeo.py`, plus per-country data packs in `regions/<cc>/` (`region.json`, prefix tables, admin table, tests); `index.md` lists sources, dates and licences.
- `scripts/tests/` — regression suites (`uv run scripts/tests/test_tools.py` etc.); `scripts/sources_check.py` — live endpoint contract checks.
