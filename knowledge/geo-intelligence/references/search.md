# Search: reverse image search, keyword image search, social media search

- [1. Reverse image search](#1-reverse-image-search)
- [2. Choose where to search by object type](#2-choose-where-to-search-by-object-type)
- [3. Descriptive keyword image search](#3-descriptive-keyword-image-search)
- [4. Social media and check-in spot search](#4-social-media-and-check-in-spot-search)
- [5. Open data (use when clearly effective)](#5-open-data-use-when-clearly-effective)
- [6. Building-class scan (every church / mosque / station in a region)](#6-building-class-scan-every-church--mosque--station-in-a-region)
- [7. Satellite scan (sat_scan.py)](#7-satellite-scan-sat_scanpy)
- [Common mistakes](#common-mistakes)

SKILL.md Step 3, in parallel with lookup-table clues. It is the cheapest high-yield step. All engines below are pre-approved: run them without asking.

## 1. Reverse image search

```bash
# Make variants first: tight crop of a distinctive object / horizontal flip / grayscale enhancement / color-cast removal; rectify rephotographed material first
uv run scripts/imgprep.py variants photo.jpg --box 300,120,900,760 --out-dir v/
uv run scripts/imgprep.py variants photo.jpg --persp 312,140,880,95,905,770,290,720 --box ... --out-dir v/
# Baidu image search + Yandex; each image gets a result screenshot and JSON
uv run scripts/revimg.py photo.jpg v/*.jpg --out-dir rev/
```

**Always open the result screenshots and look**: extracted text is only an aid; the scenes in similar images and the titles of source posts matter more. Baidu's similar images are also saved as a numbered contact sheet `<name>_baidu_similar.jpg` (the top-left cell is the query image; number i corresponds to the source page of JSON `similar[i]`). Look at it first: for near-duplicate photos of the same object or scene, the source page (Dianping, Douyin, Xiaohongshu) often gives the shop name or location tag directly.

**How to use place-name labels**: Baidu image search's "图中可能是…" ("the image may show…"), Yandex labels and the Lens AI overview are all candidates; count votes separately by level:
- City level: count which city each crop and each engine named. The same city named by two different crops is more credible than "two contradictory specific places"; specific places that don't agree don't cancel the city they jointly point to.
- Place level: when a label is the name of a residential compound, housing development, hotel or organization, get its coordinates with `poi.py` and check; this often gets you to the area in one step:

```bash
uv run scripts/poi.py "<compound name>" --city <city> --out pois.json      # list every same-name point in the city (360 Maps + OSM, WGS84)
uv run scripts/poi.py "<compound name>"                                    # no city: which cities nationwide have a same-name point
uv run scripts/tiles.py sheet --points pois.json --zoom 18 --out pois_sheet.jpg
```

- When a label is the specific name of a common facility such as a school or residential compound, first open the "图片来源" ("image source") thumbnails to see whether it's the same place (one call): names on images of playgrounds or housing are mostly assembled by voting over similar images; if it isn't the same place, downgrade it to weak and don't bother getting coordinates.
- **Facility-type words** in generic labels ("grain drying complex", "cement plant", "greenhouse", "feed mill", "sugar mill", "concrete batching plant") are useful: use them to look up where that industry is concentrated, for category inference and candidate areas.
- When the label is generic ("blocks of housing", "city street", "school playground"), treat it only as weak evidence; if the whole image + one tight crop, one round in each of two engines, give only generic labels, stop; don't keep trying variants.

| Situation | What to do |
|---|---|
| The whole image finds nothing | Box only the most distinctive object (statue, building, ornament); remove the sky and background buildings |
| Stock photos may have been taken from the other side | Flip horizontally and search again; a flipped query can hit where the original found nothing |
| Rephotographed material, oblique shots | Perspective-rectify, remove glare |
| Old photos with a yellow or purple cast | Remove the color cast or convert to grayscale |
| One engine has no results | Switch engines: Baidu is best for Chinese web pages, Weibo, Baijiahao and scenic-area content; Yandex fills in building and street scenes and foreign content |
| The search UI language biases results | Google Lens with a Chinese UI favors similar buildings on Chinese sites; for foreign scenes switch to English or the local language |

**Google Lens**: from a script it hits a CAPTCHA, so no script does it. Use a browser-control tool that drives
the owner's own Chrome (for example Claude in
Chrome): open `https://lens.google.com/` (or Google Images → camera icon), upload the original or a tight
crop with the tool's file-upload action, wait for results, then save the page text and a full-page screenshot
into `rev/lens_<crop>.txt|png` in the session folder. If Google shows a CAPTCHA or a sign-in wall, skip Lens for
this photo and note it in the report. For an image that is already public online,
`https://lens.google.com/uploadbyurl?url=<urlencoded image URL>` searches without uploading anything. Lens is
often stronger than Baidu and Yandex, but keep its two result blocks apart:
- "Exact matches / pages that include this image": provenance evidence; usable.
- "AI Overview": forces a place name out of similar-looking photos; a different crop of the same image can yield two places a dozen or so km apart. Treat it only as a candidate; it must be verified back at SKILL.md Steps 6 and 8.
- AI Mode (same browser; same skip-and-note on CAPTCHA, sign-in or region), only for outdoor scenes with place-specific content and only when no exact match, read sign or pinning artifact already places the photo: upload the original or a tight crop with a neutral prompt that names no candidate ('Where was this photo taken? Up to three candidates, each with the visible clues'); save `rev/aimode_<crop>.txt|png`. Place names are status `model`; together with the Lens AI Overview they are ONE Google vote and ONE board clue (both names on it when they differ). Re-check each cited clue on the crop; drop what you cannot see.

**Bing Visual Search** and **TinEye** (through the same browser tool): Bing sometimes finds social-media copies
the others miss; TinEye is the tool for finding the oldest, largest or uncropped copy of a photo, which often
carries the original caption, date and place.

Without a browser tool, Lens is unavailable: note in the report that it was not tried, and lean harder on crops, keyword image search and the scripted engines.

### Read the whole list before the top hit

Engines rank visual matches by how alike they look, not by whether they show the same place. Lookalikes (the
same standard design, the same paint scheme, the same chain's fit-out, the same builder's catalogue) crowd the top;
the actual place often sits further down, and a lookalike can absorb an hour of checking.

1. Save the full list from every engine and crop (page text and a screenshot in `rev/`), then write every place
   it names into a candidate table: venue, business, street, town, and the company that built, supplied or
   designed the object when a result names one.
2. Open first, ahead of rank:
   - a place named by **two independent results**: its own page and a builder's, supplier's or architect's
     project page; two unrelated posters; two engines or two different crops;
   - a place whose **name matches text in the photo**: a word, initials, a logo, even a single letter on a badge,
     banner or sign. A fragment on a wall or a uniform is often the place's own brand.
3. Check each named place against two or three fixed features (structure, layout, roof line, skyline, terrain)
   and drop it with a written reason before going deep on any one.
4. Stalled for about 15 minutes on one lead? Return to the saved lists and the table before searching wider.

### Keyword image search on the local engines

General web search tools rarely index a country's local web (blogs, cafés, local news); its own engines do.
`--country` picks them; `--text-engines a,b` overrides the pick. All queries go in one call (repeat `--query`): a
blocked engine is skipped only within a call, and file numbers restart at `q01` with each call, so a later call takes a
new `--out-dir`:

```bash
uv run scripts/revimg.py --query "<town> <noun>" --query "<town> <noun> <colour>" --country XX --out-dir q/
```

| `--country` | Engines | Notes |
|---|---|---|
| KR | `naverimg`, `daumimg` | |
| JP | `yahoojpimg`, `yandeximg`, `googleimg` | Yahoo! JAPAN is not served in the EEA and the UK |
| CN | `baiduimg`, `sogouimg` | `--text-engines bing` gives Bing China web results (title + link) |
| RU, BY, KZ | `yandeximg`, `googleimg` | |
| any other, none | `bingimg`, `yandeximg` | |

- Each engine saves `qNN_<engine>.png` and, when the page loads a second batch, `qNN_<engine>_2.png`: open both, the
  matching photo often sits below the first rows.
- Bing (`bingimg`, `bing`) in a headless browser shows its "no results" page for most CJK queries and now and then for
  any query; the run reports it as an error, not as nothing found. Yandex answers CJK and Cyrillic queries; it gives one
  page (its next page asks for a CAPTCHA).
- A CAPTCHA, consent or region-block page (`googleimg` from a headless browser, usually) is reported as blocked, never
  bypassed, and that engine is skipped for the rest of the run: use the other engines, `--proxy` with an exit in that
  country, or the engine in your own browser tool.
- Chinese example: `--query "蓝色拱形顶棚 人行天桥" --query "<city> 出租车 颜色" --country CN` (blue arched canopy
  footbridge; <city> taxi color). Baidu web search pops up a verification challenge, so it isn't done.

### After a hit

- **Look at the rest of the set**: the hit post is often a set of images, and the later images often show plates, road signs or shop names. First use shared fixed objects (streetlights, walls, chimneys) to confirm that the photos in the set and the puzzle image are the same place.
- **The candidate's background doesn't match**: it may be a replica, an identical installation, or another branch of the same chain. Once you have the proper name, search another round for "<proper name> 复制品 / replica / 同款" (复制品 = replica, 同款 = same model); the official introduction where the original stands often says where the replicas are.
- **The hit is only a "similar scene"**: use it as a clue (city, scenic-area name), not as a conclusion; go back to SKILL.md Steps 6 and 8 to verify.
- **Date ceiling**: for an exact copy of this photo (not a similar scene), write its oldest fixed date (post/upload timestamp or archive capture, not a page's 'updated' date) and URL in `## When` as 'taken on or before <date>' — never the capture date; it is the Ceiling rung (SKILL step 7).
- **For news images, first judge whether it's a real photo**: many news sites illustrate articles with stock images, illustrations or even generated images; before comparing facades, check whether it is this place.

## 2. Choose where to search by object type

| Object | Where to search |
|---|---|
| Scenic-area buildings, viral check-in spots | Douyin, Xiaohongshu, Weibo keyword and image search; official scenic-area accounts post videos from the same angle |
| Statues, small park features, foreign attractions | User photos on travel review sites (Tripadvisor, Ctrip reviews); Google Lens |
| New residential developments, commercial complexes | Housing-development albums on property sites (Anjuke, Fang.com, Loupan.com, etc.): the "周边配套" (nearby amenities) and "实景图" (real photos) sections; page all the way to the signboard |
| Old buildings, historic sites | Local culture-and-tourism and protected-heritage-site pages; stock image sites (Visual China Group, Getty, Alamy), whose captions carry place names and years |
| Ordinary streets and residential areas | Image search adds little; prioritize geometry and infrastructure; when even the city isn't fixed, sample one page of arterial-road street view per candidate city and compare municipal fixtures (`baidu_pano.py sample`) |
| Sub-brand stores of chain brands (truck service, refurbishment, specialty stores) | **Search opening press releases first** ("开业 / inaugura / abre / opens + sub-brand + state or city"; 开业 = opens), trade media often give the street address; treat the official store locator only as a candidate pool: it doesn't tag sub-brands, and its coordinates may be off by several km → `osm.py along` on the located street → `gsv.py sheet --along` / `baidu_pano.py sample` to find the frontage |
| Several chain shops seen together (a mall, a station, a high street) | Each brand's official store list; keep the venue or street on every list; the lists' unit numbers lead into the venue's floor plan (`datasets.md` "Inside a venue") |
| Built or installed objects (bridges, towers, stadium roofs, sports and play structures, sculptures, shop fit-outs) | The builder's, manufacturer's or architect's project/reference list (often a PDF naming every installation and its town) and the operator's catalogue of its assets (a motorway company's bridges, a chain's branches, a park service's facilities); a results page from such a list also counts as an independent result for the place it names |
| Nameless facilities found on satellite imagery (plants, warehouses, farms, mines) | Search the web and news for the facility-type word in the local language + nearby place names, and compare the accompanying photos with the facade; once you find the name, search images another round |
| Vehicle livery (bus, taxi, school bus) | `revimg.py --query "<city> <color description> 公交" --country CN` (query in Chinese: <city> <color description> bus), and read route signs and company names from the result images; first resolve any place name you read to a district (county) with `poi.py` before using it; don't treat a vehicle from district A as a clue for district B |

## 3. Descriptive keyword image search

Suits objects that "you can't name, but have a rare shape" (a fountain, a clock tower, a canopy).

1. Start short on the country's engines ([Keyword image search on the local engines](#keyword-image-search-on-the-local-engines)), all queries in one call: the settled town + the object's noun (`<town> 钟楼`, clock tower), then one attribute per further `--query` (`<town> 钟楼 金色球`, golden ball; `<town> 天桥 蓝色`, blue footbridge). Long phrases that mix the object with the foreground rarely match.
2. Then a version **without** the place name, in the local language and in English. Finding nothing with place names is normal: replicas and obscure places have few photos online, while there is more material on the original and on similar objects.
3. If you can't count the shapes, use broad words; don't write a wrong count.
4. Use style words (Romanesque, Gothic, Hui-style) only after checking the form: if the arches are pointed, it isn't Romanesque.

## 4. Social media and check-in spot search

- Viral scenery (cherry-blossom streets, ginkgo avenues, influencer walls, check-in cafés): search `<city> + <scenery>` on Douyin, Xiaohongshu and Weibo, **in both Chinese and English** (English posts about popular foreign streets often include the street name).
- Other posts from the same place give more angles (houses, steps, chimneys) and even location tags.
- Locals' photos of the same mountains or the same river: look in the candidate township's "同城" (local) feed or its place page; these feeds follow the location the platform thinks you are in.
- A city usually has only a dozen or so popular check-in streets; find the list first, then check them one by one.

## 5. Open data (use when clearly effective)

- **City street-tree data** (species, trunk diameter, height class, address number, coordinates): many cities abroad have open datasets (e.g., Vancouver's `public-trees` on `opendata.vancouver.ca`; its `exports/csv` returns the whole city in one request). Suited to photos with "a row of some kind of tree + residential street, no text": it narrows the whole city to a few dozen street segments. Method:
  1. **Pull all species**, not just the target species: later you need to judge "are there trees across the street", and pulling only Prunus would make an opposite side planted with other trees look empty.
  2. **Use cultivar and trunk diameter only to sort, never to filter**: the cultivar in the municipal inventory may not match the actual tree (pale pink blossoms in the photo where the inventory lists a white-flowered cultivar), and the trunk diameter may have been measured years ago. Cultivars of the same genus with similar flower color all go in as candidates; exclusion can only rely on invariant features in street view.
  3. **Use odd/even address numbers to fix which side of the street the trees are on**: comparing the coordinates of odd- and even-numbered trees on the same street tells you (in Vancouver, odd numbers are on the north side of east–west Avenues and the west side of north–south Streets; east–west Streets follow the Avenue rule). Then filter with "which side you're standing on, which way you're facing" from the shadows.
  4. **Compute the across-the-street constraint from the field of view**: a portrait phone's horizontal FOV is about 50°, so the grass strip across the street (10–20 m sideways) enters the frame only beyond about 25 m ahead; "no trees across the street" constrains only about 25–50 m ahead, not close by.
  5. Group the filtered trees into street segments: `opendata.py group --points trees.json --cell 80 --min 3 --out segments.json` (cells of 80 m with ≥3 matching trees become one named point each); add them to the board in one go with `board.py add --from segments.json --level road`; when you drop one, write `evidence --against` with a comparison image (SKILL.md hard rule 6).
  6. For street view, first pick historical captures from the same season as the photo (`gsv.py near` to see the history, `sheet --date <year>`) and compare facades, retaining walls and lamp-post positions; in summer captures tree crowns and bloom differ a lot, so don't skip a segment because "the trees look small".
- Local government and media reports: after locating, look up the name, size and year built of unusual man-made objects in the frame (scenic spots, towers, statues).

## 6. Building-class scan (every church / mosque / station in a region)

Use for an unnamed building of a recognizable class seen from the street. Narrow to a city or a smaller justified
bbox first, and check `osm.py coverage` before enumerating:

```bash
uv run scripts/osm.py find --bbox <s,w,n,e> '["building"="church"]' --out targets.json        # or ["amenity"="place_of_worship"]["religion"="muslim"], ["railway"="station"] …
uv run scripts/gsv.py targets --points targets.json --per 2 --out targets.index.json --sheet first.jpg
uv run scripts/match.py rank --query photo.jpg --query-box <building part> --items targets.index.json --render gsv --refine sift --top 10 --out r.json --sheet r.jpg
```

- `targets` keeps up to `--per` official panoramas per target, 12–70 m away and ≥15 m apart by default, each
  facing the building. Coverage tiles are cached and shared by workers.
- Keep each index within `match.py`'s default 400-view limit (at most 200 targets with `--per 2`). It loads all
  candidate images into memory; raising `--max-candidates` to a country-wide view count can exhaust memory.
  Narrow the bbox or split the point list before scanning, and save each batch's results separately; SIFT
  refinement within separate batches is not a global ranking.
- Compare multiple views of shortlisted targets. Repetitive brickwork can produce false SIFT matches; confirm
  ≥3 invariant features (`verify.md` §2).
- Empty coverage does not exclude a target: the coverage layer can omit panoramas that
  `gsv.py near <lat,lon> --radius 130` finds. Check shortlisted targets with `near`, including historical
  captures when appropriate.

## 7. Satellite scan (sat_scan.py)

SKILL.md Step 6, "scene elements only" (field + road + coast, a track, silos, a dam) and the fallback when OSM
is thin. `sat_scan.py` scores satellite cells or points with CLIP zero-shot and ranks them; you look at the top
20–30 instead of paging through contact sheets.

```bash
uv run scripts/sat_scan.py presets                                                                   # preset names and prompts
uv run scripts/sat_scan.py grid --bbox <s,w,n,e> --zoom 17 --cell 320 --preset track --top 30 --out ranked.json --sheet top.jpg --heat heat.jpg
uv run scripts/sat_scan.py grid --bbox <s,w,n,e> --zoom 17 --query "aerial view of a village on a river bend with a bridge and a white church" --neg "aerial view of farmland" --out r.json --sheet r.jpg
uv run scripts/sat_scan.py grid --bbox <s,w,n,e> --preset factory --seeds factories.json --seed-radius 500 --multi-scale --out r.json --sheet r.jpg
uv run scripts/sat_scan.py points --points big_buildings.json --zoom 17 --preset silo --out r.json --sheet r.jpg   # from osm.py buildings / poi.py
```

- **Write the scene as one English query, don't hand-pick spots**: describe the whole top-down scene in one
  sentence (`--query`, repeatable; `--neg` for the look-alikes that crowd the top); let the ranking choose where
  to look. Picking cells by eye on a mosaic is the slow, biased version of the same step.
- **Grid beats points when OSM tags are incomplete**: `points` only sees what `osm.py buildings`/`poi.py` listed;
  `grid` sees every cell. Use `--seeds` to bias toward POIs without depending on them; `--multi-scale` for
  targets smaller than a cell; `--heat` to see whether the score concentrates or is flat (flat = wrong prompt or
  wrong area).
- **Top-down feature template** before looking at results: write what the scene must show from above — the
  road's shape and junctions, water edges, the building footprint and roof colour, open ground, tree lines,
  the angle between them and the camera direction (`sun.py compass` when the sun is in frame). Judge every
  thumbnail against the template, not against "looks similar".
- **Imagery has a date**: a cell can score low because the building did not exist when the tiles were taken;
  for a new feature run `tiles.py wayback <lat,lon> --out wb.jpg` on the shortlist and compare releases.
- **Failed top 30**: before widening, `board.py check` and reread the down-weighted candidates and the
  falsification conditions (one of them may have killed the truth); then switch preset or prompt, or rerun the
  shortlist at `--zoom 18`; only then widen the bbox. Scores order cells, they never exclude.

## Common mistakes

- Using only one engine and searching only the whole image; after a failure, not changing the image or the engine.
- Opening the first visual match and spending the session on it, while a lower result named the same place twice or matched a letter or logo in the photo.
- Turning the "object category" from an AI or image recognition directly into a location ("boat-shaped sculpture → tourist city"); this jump counts only as weak evidence.
- Getting carried off by the "most famous similar place" the search turns up and forgetting to come back and check bearings and details.
- Two engines each point at a different city, and you draw a big circle around the midpoint of the two and call it done: instead run a discriminating test and pick one as the main answer (SKILL.md hard rule 7).
- Image search gave a residential compound or housing-development name, and you didn't get its coordinates.
