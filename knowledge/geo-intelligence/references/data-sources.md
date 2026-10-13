# Scripts, data sources and coordinate systems

- [Script overview](#script-overview)
- [Coordinate systems (must be kept apart in China)](#coordinate-systems-must-be-kept-apart-in-china)
- [Satellite imagery](#satellite-imagery)
- [Street view and ground-level imagery](#street-view-and-ground-level-imagery)
- [Search](#search)
- [Place name → coordinates (China)](#place-name--coordinates-china)
- [Place name → coordinates (outside China)](#place-name--coordinates-outside-china)
- [Ground photos (when there's no street view)](#ground-photos-when-theres-no-street-view)
- [Thematic maps and structured data](#thematic-maps-and-structured-data)
- [Offline reference data](#offline-reference-data)
- [Time and weather](#time-and-weather)

## Script overview

Entry points live in `scripts/`. Private modules live in `scripts/geolib/`: `net.py` (HTTP routing), `browser.py`
(browser launch), `pano.py` (panorama manifests and renderer), `streetlevel.py` (street-level providers),
`megaloc.py` (place recognition). Lookup tables live in `assets/data/`.

| Script | What it does |
|---|--- |
| `doctor.py` | Environment checks, browser launch, optional endpoint probes; English fixes and JSON output |
| `sources_check.py` | Live known-answer probes of every external endpoint; run it when a tool returns nothing or before a long scan |
| `meta.py` | Deep metadata: GPS (EXIF/XMP/video/DJI), capture time, camera heading, UTC offset → countries on that date, filename/platform hints, embedded previews, provenance/AI flags ("File declares generated content" vs "AI-edited real photo"; `digest.provenance.generated` in the JSON). `meta.py <photo> [more photos] --json` prints one line per file plus optics (focal_35mm, 4:3 FOV) and GCJ-02 for points in China. Without exiftool it falls back to Pillow + XMP/ISO 6709 byte scans (the IPTC source type from its own property only: XMP, a PNG's XMP packet too, and C2PA manifests; a brotli-compressed or remote manifest needs exiftool or c2patool) and prints a one-line notice; embedded previews, video and DJI metadata need exiftool |
| `imgprep.py` | zoom (enlarge to read text) / edges (four edges, four corners) / variants (image-search variants) / grid (split into tiles) / `reveal` (eight brightness/contrast stretches of a dark or flat crop, to read a plate or sign lost in shadow) / `piers` (brightness profile along a given row to find pixel columns of evenly spaced structures; outputs a check image) |
| `revimg.py` | Baidu image search + Yandex reverse image search; `--query` keyword image search on the engines `--country` picks (`search.md` §1) |
| `geo.py` | Coordinate conversion, bearing and distance, camera geometry (`range --hfov a:b` distance range), `line` alignment line, `intersect` sight-line intersection, `frame` computes the frame and occlusion before excluding, `spacing` pixel columns of evenly spaced structures × known polyline → solve for camera position (optionally scored jointly with the skyline), `bearings` camera position → bearing, angular width and distance of each outline in a GeoJSON, and `far`, the farthest vertex (the radius round the pin that covers the whole feature) (use with `sun.py compass`: compute the bearing first, then identify the structure) |
| `poi.py` | Place names, residential compound names, housing development names, shop names → candidate coordinates (360 Maps + OSM Nominatim + Baidu suggestions; lists every same-name point nationwide); `nearby <lat,lon> --category <cat>` (44 OSM POI categories), `reverse` (coordinates → address), `distance` / `directions` (OSRM), `timezone` |
| `sun.py` | Sun position, shadow-length ratio, `locate` location band, `when` time, `street` street orientation, `facing` heading from lit faces, `compass` bearings from the sun in frame, `dish` satellite dish, `weather` past cloud/sun/rain/snow for a point (rank the days of a range); `terrain.py shade` terrain/building shadows at a time, point checks, time sweep |
| `osm.py` | Overpass: find / addr (house numbers; several must co-occur within N m) / near (co-occurrence) / crossings (line-to-point) / route (route corridor) / intersect (crossings of two kinds of lines; bends are only labeled, `--rank-near` ranks) / coverage (feature counts per admin area) / along (points along a line) / buildings (large footprints) / street-scan (street-view geometry template) / geom (export geometry) / raw |
| `tiles.py` | Satellite/map tile mosaic (Google satellite / hybrid / map, Esri imagery / street, Bing aerial, Esri Wayback releases since 2014, EOX Sentinel-2 by year, NASA GIBS by day), `mark` plots points + overlays GeoJSON lines + field-of-view wedge, `sheet` numbered thumbnails of candidate points (town-fabric comparisons), `wayback` every archived look of a point |
| `baidu_pano.py` | Baidu panoramas: near / info / scan / render / sheet (`--headings` to look around from one point, `--road` `--spread`) / sample (street view sampling of candidate cities) |
| `gsv.py` | Google Street View (outside China): near / render / sheet / area / targets (panoramas around each target point, rendered facing it, for `match.py rank --items`), no key; discovery finds official coverage only, `render <id>` also takes a user or business 360 id |
| `pano.py` | Street-level imagery from every scriptable provider in one manifest format (Google, Apple Look Around, Bing Streetside, Yandex, Naver, Kakao, Mapy, Já.is, KartaView, Panoramax, Mapillary with a token) plus manifests you write for sources you find: coverage / list / render / sheet; see `streetlevel.md` |
| `sweep.py` | Index every panorama of one or more towns (MegaLoc descriptors, cached) and rank them for a photo; clusters of top hits; `view` reproduces the photo's view |
| `pose.py` | Solve camera position from multiple points: lat/lon, height, heading, pitch, roll, field of view + error radius + per-point check; `check` scores discrete candidate camera positions; `project` projects map points back onto the photo |
| `terrain.py` | Elevation: view (synthesized mountain view; `--overlay` overlays the skyline on the photo, `--roll`) / profile (skyline) / elev / `ridge` reads ridgeline pixel points from the photo / `scan` filters a whole region along infrastructure lines for "flat nearby + mountain present" points and clusters them / `fit` batch skyline scoring of candidate camera positions (optional infrastructure-distance constraint; outputs overlays of the top N) |
| `evidence.py` | Evidence image: satellite image + camera-position wedge + comparison panels; `--match`: photo and reference side by side with colour-coded matching lines |
| `opendata.py` | City open-data portals (Socrata catalogue; any CSV/GeoJSON export or local file): find a dataset, list its fields, filter it, export candidate points |
| `intake.py` | Metadata, edge crops, variants, OCR and Baidu/Yandex reverse image search on the original and variants in one command (recon.py runs it; `--no-rev` skips the reverse search); outputs intake.md (tiered vote count, possible place names, results on an AI-image gallery host from `assets/data/ai_hosts.json`: open and compare, a host alone only down-weights) |
| `ocr.py` | Reads text in the photo (Apple Vision, falls back to RapidOCR): full image + zoomed + tiles, merged; text read only after zooming is marked in `pass` |
| `clues.py` | Lookup tables: license plate prefixes (China), regional plate codes with their eras (`plate-code`: IT ES FR DE AT CH GR TR GB MA), landline area codes, country calling codes, driving side, overseas territories, admin hierarchy; tables are in `assets/data/`, `update` re-fetches them |
| `board.py` | Candidate board: candidates, clues, evidence likelihood ratios, exclusions (require a computed file), ranking, scan cost, next step, pre-conclusion check, generates result.json fields |
| `gazetteer.py` | Admin-division gazetteer: lists all subdivisions (with bbox), built-up area extents, scan pages |
| `sat_scan.py` | CLIP zero-shot scoring and ranking of satellite grid cells/candidate points (sports fields, factory buildings, silos, dams…), top-N thumbnails + heatmap |
| `match.py` | Ranks the photo against candidate ground-level images: MegaLoc (default) / DINOv2 / CLIP global similarity + SIFT inlier re-ranking (same-era imagery only); candidates can be rendered on the fly from panorama ids |
| `recon.py` | The local first pass in one command: meta + intake (Yandex/Baidu reverse search included unless `--no-rev`) + textgeo + detect + calib + prior + aidet → recon.md |
| `textgeo.py` | Text → scripts, distinctive letters, language (lingua), phones (libphonenumber), domains, postal formats, currency, regional words, brands (name-suggestion-index), place names (GeoNames) |
| `geodata.py` | Country facts (`assets/data/countries.json`), GeoNames places: search, reverse geocode, population-weighted sampling, the biggest towns of a region or radius (`towns`), national gazetteers |
| `aidet.py` | AI-generated-image score of the original (pinned ONNX model, CPU): model status, never a verdict (`models.md`) |
| `prior.py` | StreetCLIP + GeoCLIP world prior on several crops, region ranking, consistent point guess, self-assessment |
| `detect.py` | OWLv2 open-vocabulary detection → numbered crops of signs, plates, poles, bollards, markings, vehicles |
| `calib.py` | GeoCalib: FOV, focal, pitch, roll, horizon line with uncertainties |
| `refsheet.py` | Street View sample rows per candidate country/region (side by side) |
| `bench.py` | Street View test sets with hidden truth, model-only baseline, scoring of predictions and sessions (`workflow.md`) |
| `photo_session.py` | Per-photo archive: start, finish, truth (scoring), scoreboard, list |

## Coordinate systems (must be kept apart in China)

| Code | Name | Who uses it |
|---|---|---|
| wgs | WGS84 | GPS, photo EXIF, Google satellite imagery, OpenStreetMap, elevation tiles |
| gcj | GCJ-02 | Amap (Gaode), Tencent, 360 Maps, Google's China road maps, **Google Earth's Chinese label layer in China** |
| bd | BD-09 | Baidu Maps lat/lon |
| bdmc | Baidu Mercator | `@x,y` in Baidu Maps URLs, the Baidu panorama API |

In China the same point differs by several hundred meters between WGS84 and GCJ-02. Conversion: `uv run scripts/geo.py convert --from X --to Y a b`.
- Amap links use gcj: `https://uri.amap.com/marker?position=<lon>,<lat>`; Google links use wgs.
- **Google Earth in China: the imagery is WGS84, the Chinese place-name labels are GCJ-02, and the two are offset by several hundred meters** (a dock's label can land on the river surface). Place points and read coordinates from the imagery.
- For coordinates read from Chinese map apps or websites, confirm the coordinate system before using them.

## Satellite imagery

| Source | Notes |
|---|---|
| Google satellite tiles | `mt1.google.com/vt/lyrs=s`, WGS84, sharp in China. `tiles.py` default |
| Esri World Imagery | Backup; older in some parts of China; has the Wayback historical archive |
| Google Earth desktop | Historical imagery timeline, tilted 3D (manual use); 3D models in China are old, newly built supertall buildings are often missing |

- The same place at different zoom levels may be imagery from different years and different tilt angles.
- Zoom 17 is about 1.1 m/pixel, for areas; zoom 19 is about 0.28 m/pixel, for single buildings; zoom 7–9 as the base map for `sun.py locate --mosaic`.
- One day's satellite pass (clouds, snow, smoke on a known date): `tiles.py --source gibs:<YYYY-MM-DD>` (NASA GIBS, ~250 m, zoom ≤ 9; `sky.md` §6).

### Historical aerial imagery (older than Esri Wayback's 2014)

For an old photo, the street, the plots and the trees as they were then. Browser tools, no script; open the
place, step back through the years, and compare structures the way `streetlevel.md` §5 describes.

| Where | Archive | Notes |
|---|---|---|
| Worldwide | USGS EarthExplorer (earthexplorer.usgs.gov) | Declassified CORONA spy-satellite frames 1960–1972 (metre-scale, much of Africa, the Middle East and Asia), US aerial photo single frames, Landsat since 1972 (30 m, land use only); free account to download |
| France | IGN Remonter le temps (remonterletemps.ign.fr) | Historical aerial photos and maps compared side by side with today; Géoportail (geoportail.gouv.fr) for the layers |
| Spain | CNIG Fototeca (fototeca.cnig.es) | Historical national flights, including the American flight of 1956–57 |
| Switzerland | map.geo.admin.ch (swisstopo) | Historical aerial images and the "journey through time" map series |
| United Kingdom | Britain from Above (britainfromabove.org.uk) | Aerofilms oblique aerials, mostly 1919–1953 |
| Netherlands | Topotijdreis (topotijdreis.nl) | Historical topographic maps year by year since 1815 (maps, not photos) |
| Belgium (Flanders) | Geopunt (geopunt.be) | Historical orthophoto series |
| Italy | Geoportale Nazionale (gn.mase.gov.it) | National orthophoto series since the late 1980s |

Elsewhere, search the national mapping agency or cadastre in the local language ("photographies aériennes
anciennes", "fotos aéreas históricas", "historische Luftbilder", "صور جوية قديمة") and the city's open-data portal.

## Street view and ground-level imagery

### Baidu panoramas (main source in China)

The endpoints are all at `https://mapsv0.bdimg.com/`, need no key, and must be accessed directly:

| Purpose | Parameters |
|---|---|
| Nearest panorama to a point | `?qt=qsdata&x=<bdmc x>&y=<bdmc y>` |
| Panorama info (date, location, all points along the road, historical versions) | `?qt=sdata&sid=<panoid>` |
| Render a perspective view by heading | `?qt=pr3d&panoid=<id>&heading=<compass angle>&pitch=<pitch>&fovy=<vertical FOV>&width=<≤1024>&height=<>` |

- heading is a compass bearing, 0 = due north, clockwise; a width over 1024 returns 404.
- Covers urban arterial roads and many roads inside industrial zones; almost nothing inside residential compounds. Captures are mostly from 2017–2019, so new buildings aren't visible.
- Place search on map.baidu.com triggers a captcha; don't try to get around it; use `poi.py` for place names.

### Other

| Source | Use | Known issues |
|---|---|---|
| Google Street View | Street view outside China, with historical dates; `gsv.py`, `refsheet.py` | Almost none in China. The old `GeoPhotoService.SingleImageSearch` endpoint answers "decommissioned" and the `streetviewpixels` thumbnail endpoint returns 403 to anonymous callers (checked 2026-10); discovery now uses Maps coverage tiles (`photometa/ac/v1`, zoom 17) and `photometa/v1` metadata via the `streetlevel` package, and views are rendered locally from the equirectangular panorama. Discovery skips user photospheres; `gsv.py render <id>` works on a user or business 360 id copied from a Google Maps URL (`!1s<id>`, up to the next `!`); a single upload often sits at the venue pin and publish_api tour nodes carry their own positions, so neither is a verified capture point until matched. A failed render exits non-zero and writes nothing |
| Apple Look Around, Yandex, Naver, Kakao, Bing Streetside, Mapy.cz, Já.is | Other street-level providers (better than Google in Korea, parts of Russia/Turkey/Czechia/Iceland, many US/European cities for Apple) | `pano.py --provider …` (`streetlevel.md` §2) |
| Mapillary, KartaView | Crowdsourced street view, rural roads outside China | Almost none in China |
| Tencent Street View | Backup in China | No script |
| Map POI photos, hotel/scenic-area photos online, tourist photos | Compare skylines and building shapes when there's no street view | Shooting angle can't be controlled |

**Google coverage changes every year.** Official coverage launched 2024–2026 in Oman (Dec 2024), Namibia
(June 2025), Nepal (Aug 2025), Paraguay and Cyprus (Nov 2025, first official), Georgia (June 2026, ~13,000 km)
and Kosovo (July 2026); Vietnam 2025 rests on a single source; Kuwait is listed as future. Treat any coverage
list, including this one, as of its date (2026-10): probe the point with `pano.py coverage` before ruling
Google in or out. Camera generations and coverage quirks:
[world/streetview.md](world/streetview.md).

## Search

| Source | Good at | How to use |
|---|---|---|
| Baidu image search | Chinese web pages, Weibo, Baijiahao, e-commerce, scenic areas; gives "图中可能是…" ("the image may show…") | `revimg.py` |
| Yandex Images | Buildings, street view, foreign content; gives tags and source sites | `revimg.py` |
| Google Lens | Recognizing "what this is" (species, car models, statues, attractions), often stronger than Baidu and Yandex | Requests from a server's egress IP get challenged for verification; when you have a browser-control tool, use it in the user's browser; the AI Overview will confidently report a place name based on similar images |
| Local image engines (Naver, Daum, Yahoo! JAPAN, Yandex, Baidu, Sogou, Bing, Google Images) | Keyword image search in the local language; they index the local web that general search tools miss | `revimg.py --query --country XX` (`search.md` §1) |
| Douyin, Xiaohongshu, Weibo | Influencer check-in spots, scenic areas' official accounts, same-city content | Web search or user assistance |
| Development photo albums on real-estate sites (Anjuke, Fang.com, Loupan.com, etc.) | New housing developments, commercial complexes; albums include signboards | Web search the development name |
| Travel review sites (Tripadvisor, Ctrip) | User photos of statues, parks, attractions | Web search |
| Stock photo libraries (VCG, Getty, Alamy) | Captions carry exact place names and dates | Web search |
| Local government and local media websites | Check the names and sizes of scenic areas, towers, statues | Web search |

## Place name → coordinates (China)

| Source | Notes |
|---|---|
| 360 Maps search `restapi.map.so.com/newapi` | No key; good coverage of residential compounds, housing developments, shops and organizations, with address and district; coordinates are GCJ-02 (`poi.py` already converts to WGS84); without a city it returns a list of cities nationwide that have same-name results |
| OpenStreetMap Nominatim | Named residential compounds, parks, roads; WGS84 |
| Baidu Maps search suggestions `map.baidu.com/su` | No key; only "city + district + name", no coordinates |
| Baidu Maps place search, Tencent and Amap APIs | Baidu needs a captcha, Tencent and Amap need keys; not used |

## Place name → coordinates (outside China)

- `poi.py "<address or place name>" --sources osm --country <two-letter country code>` (Nominatim, WGS84). When a street address isn't found, drop the house number and search only the street + district name.
- Around a candidate point: `poi.py nearby <lat,lon> --category <cat>` lists OSM POIs of one category; `poi.py reverse` turns coordinates into an address.

## Ground photos (when there's no street view)

| Source | Notes |
|---|---|
| Images from news, encyclopedias, company websites, blogs | First find a name for the facility (OSM name, nearby place name + the local-language word for the facility type), then search; rural factory buildings and abandoned facilities often have only this kind of ground photo |
| Wikimedia Commons search by coordinates | `commons.wikimedia.org/w/api.php?action=query&list=geosearch&gscoord=<lat>|<lon>&gsradius=10000&gsnamespace=6&format=json`, no key; remote areas often have only a few |
| Mapillary | Wide crowd-sourced coverage; `pano.py --provider mapillary` with a free client token (`MAPILLARY_TOKEN`), otherwise the web app in the browser |
| KartaView, Panoramax | `pano.py --provider kartaview|panoramax`, no key; patchy (Panoramax strongest in France) |
| Local and historical panorama sites | Found by web search in the local languages (`streetlevel.md` §1), turned into a manifest and swept |

## Thematic maps and structured data

| Source | Use | Known issues |
|---|---|---|
| OpenStreetMap Overpass | Feature co-occurrence, line-to-point, route corridors, line crossings, street-view templates, points along a road, large buildings | `osm.py`; public servers are often busy or rate-limited (the script retries on mirrors; a result with a remark gets a warning that it may be incomplete); **ranges of hundreds of kilometers with a name regex (`[~"name"~...]`) often time out**; drop the regex or query by sub-area; in Chinese counties and townships, buildings and parking are basically empty, and rivers often have only centerlines |
| Overture Maps | Buildings, places, road segments, addresses where OSM is thin; monthly releases | `uvx overturemaps download --bbox W,S,E,N -f geojson --type building\|place\|segment\|address -o out.geojson`, then `opendata.py points out.geojson --out pts.json` for `tiles.py sheet --points` (`datasets.md`) |
| Bellingcat OpenStreetMap Search (osm-search.bellingcat.com) | Preset feature co-occurrence in a small region, in the browser | Same OSM data as `osm.py near`; same coverage gaps |
| OpenRailwayMap (openrailwaymap.org) | Railway class, single/double track, electrification, stations | Viewed manually on the web; same data as OSM |
| OpenInfraMap (openinframap.org) | Power lines and voltage, substations | Viewed manually on the web; voltage may be untagged |
| AWS Terrain Tiles (Terrarium) | Global elevation, about 30 m | `terrain.py`; details smaller than a hundred meters are unreliable |
| ESA WorldCover (viewer.esa-worldcover.org/worldcover) | 10 m global land cover (tree cover, grassland, cropland, built-up, bare, water, wetland, mangrove): test a biome or land-use clue over a candidate region, find the cropland/forest edge seen in the photo | Browser viewer; 11 classes; fixed years (2020, 2021) |
| Google Dynamic World (dynamicworld.app) | 10 m land cover from Sentinel-2 scenes, 9 classes, dated per scene: cropland vs built-up vs water around the photo's date | Browser viewer; per-pixel probabilities, cloud gaps; not a survey |
| Indoor plans | Shops, units, rooms, corridors and levels inside a known venue | OSM `indoor`, `level`, `ref` and `shop` tags where mapped (`osm.py geom --bbox <venue>`); many venues have only an outline. Vendor indoor maps (Google Maps web level picker, national map apps) are view-only by eye, no API |
| City open data | Street trees (species, trunk diameter at breast height, location), etc. | Many foreign cities, few Chinese ones; `opendata.py` |

### Overpass endpoints

Free global instances:

| Endpoint | Notes |
|---|---|
| `https://overpass-api.de/api/interpreter` | Main instance; after HTTP 429 or 406, pause 30 s before retrying |
| `https://overpass.private.coffee/api/interpreter` | Formerly overpass.kumi.systems; no rate limit |
| `https://maps.mail.ru/osm/tools/overpass/api/interpreter` | Global mirror |

Paid or keyed instances exist (Geofabrik, FairwayMapper, Overspan, NextGIS, Mapsource), as do regional ones
(overpass.osm.ch for Switzerland; overpass.atownsend.org.uk for Britain and Ireland, IPv6-only). When a query
returns nothing or times out on every mirror, run `sources_check.py` before concluding the data is absent.
`osm.py` caches an empty reply (no elements, or a first count of 0) only after a second mirror confirms it; otherwise it
returns it uncached with the warning "not confirmed by a second mirror, so not cached": rerun once at most; still empty →
record "not found in OSM (unconfirmed)" and move on.

## Offline reference data

Downloaded once into the shared cache (`workflow.md`, Paths and settings).

| Source | Use | Licence |
|---|---|---|
| GeoNames `countryInfo.txt` (bundled as `assets/data/countries.json`) | names, ISO codes, TLDs, phone prefixes, postal formats, languages, neighbours | CC BY 4.0 |
| GeoNames `admin1CodesASCII.txt`, `cities500.zip`, `<CC>.zip` | region names; 236k populated places with alternate names; full national gazetteers on demand | CC BY 4.0 |
| OpenStreetMap name-suggestion-index (`nsi.min.json` via jsDelivr) | ~19k brands (the `brands/` part of the index; operators and transit networks are not indexed) and the countries/regions where they operate | BSD-3 / data ODbL-compatible |
| libphonenumber (`phonenumbers`) | phone number → country, region/city for many landlines, carrier | Apache-2.0 |
| lingua | offline language identification for short text | Apache-2.0 |
| Hugging Face / GitHub model weights | StreetCLIP, CLIP ViT-L/14 (GeoCLIP), OWLv2, GeoCalib, DINOv2, MegaLoc, CLIP B/32, the AI-image detector | see `models.md` |

## Time and weather

| Source | Use |
|---|---|
| `sun.py` (NOAA algorithm, within ≤0.02° of NREL SPA) | Sun position, shadows, bands, times, dishes |
| SunCalc (suncalc.org) | Manual cross-check of sun azimuth, elevation and shadow at a point and time; `sun.py pos` prints the link (`suncalc_url`) |
| PeakFinder (peakfinder.com) | Labelled mountain panorama from any point and heading, for the user's eyes; `terrain.py fit/view` print the link (`peakfinder_url`, parameters as documented by the community: lat, lng, azi, fov, ele); the offline counterpart is `terrain.py view --peaks` with OSM peak names |
| ShadeMap (shademap.app) | Terrain and building shadows on a map at a date and time, for the user's eyes; `sun.py pos` prints the link (`shademap_url`); offline counterpart `terrain.py shade` |
| Bellingcat Shadow Finder | Whole-earth search of where an object's shadow length fits a date and time; cross-check for `sun.py locate` |
| Historical daily weather (temperature, sun/rain) | `sun.py weather` (Open-Meteo ERA5 archive, no key): check "frozen", "sunny"; with a date, rank or test places; with a place, rank the days |
| Historical weather-satellite cloud imagery | `tiles.py --source gibs:<date>`: that day's MODIS/VIIRS pass; match a cloud bank, snow line or clear strip seen in the photo |
| Flightradar24, FlightAware | Flight history by registration; the paid tier can download KML/CSV tracks |
