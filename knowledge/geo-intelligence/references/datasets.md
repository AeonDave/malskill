# Clue → database filter: from a whole city to a short list

SKILL.md Steps 5–6. Once the city or region is known, the fastest route to the street is rarely scanning: it is
turning one clue from the photo into a query against a dataset that already lists every instance of it with
coordinates, then checking the short list. A whole city becomes 5–200 points; street level settles the rest.

## 1. The recipe

1. **Check coverage first**: `osm.py coverage --areas <A>,<B> --filter '<feature>'`. An area with sparse data
   drops out of every query silently; fill it from Overture Maps or open data, or run `sat_scan.py grid` on it
   (`search.md` §7), and state the coverage gap in the conclusion.
2. **Pick the rarest clue you are sure of.** A tree species that is uncommon in that city gives a handful of
   candidates; a ubiquitous one gives tens of thousands. Rarity first, certainty second: a coloured bus lane, a
   posted speed limit, a house number, a school beside a playground, a harbour inside one province.
3. **Filter on the one attribute you are sure of; rank by the rest.** Datasets are incomplete and stale: a
   missing tag, a guessed attribute, a value recorded years ago can each drop the true answer. Use further
   attributes to order the list, not to cut it (SKILL.md hard rule 6).
4. **Plot and look at the list as a whole** (`tiles.py sheet --points …`), drop what the photo rules out with
   computed or visible evidence (wrong street width, flat where the photo climbs, deep shade where the photo is
   sunny), then check the survivors at street level with three or four deal-breakers written down first
   (`gsv.py sheet`, `pano.py sheet`; historical captures near the photo's date).
5. **A miss over the whole list is information**: the clue was misread, the dataset is incomplete there
   (`osm.py coverage`), or the city is wrong. Re-read the clue (`imgprep.py reveal`) before widening.

## 2. Which clue, which dataset

| Clue in the photo | Dataset | Command |
|---|---|---|
| A house number (door, gate, mailbox, bin) | OSM addresses | `osm.py addr --area <town> --number 145` |
| Two numbers close together on one street | OSM addresses | `osm.py addr --area <region> --number 214,226 --within 60` |
| No OSM addresses in the area | property / address sites | web search the number and town in quotes, `site:` the country's main property portal or the national address register; check listing photos and street level |
| No OSM buildings or places in the area | Overture Maps (buildings, places, road segments, addresses; monthly releases) | `uvx overturemaps download --bbox W,S,E,N -f geojson --type building -o ov.geojson` (or `place`, `segment`, `address`) → `opendata.py points ov.geojson --out ov.json` → `tiles.py sheet --points ov.json` |
| A speed-limit sign | OSM `maxspeed` | `osm.py find --area <city> '["maxspeed"="30 mph"]'` (values as tagged: `"50"`, `"30 mph"`) |
| A school with a playground, a church on a square, a pharmacy at a junction | OSM co-occurrence | `osm.py near --area <city> --a '["amenity"="school"]' --b '["leisure"="playground"]' --within 80` |
| An N-storey block next to a bus stop | OSM co-occurrence | `osm.py near --area <city> --a '["building:levels"="5"]' --b '["highway"="bus_stop"]' --within 50` |
| A harbour, marina, quay in a province | OSM | `osm.py find --area <province> '["leisure"="marina"]'` (+ `["harbour"]`, `["man_made"="pier"]`) |
| A shop name, partly readable | OSM names | `osm.py find --area <city> '["name"~"BAKER",i]'`; if the text could be mirrored, try both readings; local business directories |
| Bus-lane colour/type/width, street-tree species, hydrants, benches, street lights, parking rules | city open data | `opendata.py search …` → `columns` → `get … --points` (§3) |
| Street width (crossing bars, lane count) | design manual + open data | bars × (bar + gap) ≈ crossing width; calibrate on a known crossing in the same city with a map measure; filter a width column with `--range` (`geometry.md` §3) |
| Railway beside a highway, river crossings, power-line crossings | OSM lines | `osm.py intersect / crossings / near` (`corridors.md`) |

### Inside a venue

Once the venue is known, shop, unit, gate and exit names on signs are filters: `osm.py geom '["name"~"<sign>",i]'
--bbox <venue>` and read `level` and `ref` where OSM maps the inside; otherwise the venue's own floor directory, or a
map's level picker read by eye (Google Maps on the web; the national map apps where Google is thin), citing URL and
level. A hit on the photo's level puts the camera beside that shopfront (tenants change: the photo's date must fit);
a miss says nothing against the venue; a radius ≤100 m still needs SKILL.md hard rule 8. A Google 360 inside the
venue renders by its id (`streetlevel.md` §1, the browser rung) and is compared like any reference; its position is
the uploader's. Draw the plan: `osm.py geom` → `viewer.py mark area <file> --level <L>`.

## 3. City open data with `opendata.py`

Thousands of city, county and state portals publish their assets with coordinates. Socrata hosts a large share
of North American and European ones (New York, Chicago, Los Angeles, Seattle, many states and EU cities); its
catalogue is searchable in one call.

```bash
uv run scripts/opendata.py search "street tree census" --domain data.cityofnewyork.us     # which datasets exist
uv run scripts/opendata.py columns data.cityofnewyork.us uvpi-gqnh                         # fields + a sample row
uv run scripts/opendata.py get data.cityofnewyork.us uvpi-gqnh --eq spc_common=sassafras --eq boroname=Manhattan \
    --points --name-field address --out trees.json                                         # 17 trees in the borough
uv run scripts/tiles.py sheet --points trees.json --zoom 18 --out trees_sheet.jpg
```

- `--eq col=value` (repeatable), `--range col:lo:hi`, `--where <raw SoQL>` for anything else; `--name-field`
  names each point by a useful column (street, address, species). Lines and polygons become one point each
  (midpoint / centre); exports with an empty geometry fall back to their latitude/longitude columns.
- The same pattern works for any asset class a portal lists: `opendata.py search "bus lanes"`, `"hydrants"`,
  `"street lights"`, `"benches"`, `"parking signs"` on the city's domain.
- **Not on Socrata?** Many cities run ArcGIS Hub or CKAN portals: find the dataset in the browser (web search
  `"<city>" open data <asset>`), copy its CSV or GeoJSON export link, then
  `opendata.py points "<url>" --name-field <col> --out pts.json`.
- Datasets record the present (or a past vintage): a lane repainted, a tree felled, a hydrant replaced. For an
  older photo, look for older vintages (New York publishes its 1995, 2005 and 2015 tree censuses), prefer the
  assets that persist (trees already large then, street geometry), and check historical street-level captures.
- Street trees in detail (species vs cultivar, odd/even sides, field of view across the street): `search.md` §5.

## 4. Common mistakes

- Filtering on a guess and losing the answer to one wrong or missing tag.
- Choosing a common clue (a ubiquitous tree, a standard hydrant) and drowning in candidates; find a rarer one.
- Treating "0 results" as absence: OSM coverage varies by town (`osm.py coverage`), open data by city.
- Checking candidates one by one without a deal-breaker list: write the 3–4 features that must match first.
