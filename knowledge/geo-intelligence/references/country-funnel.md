# The country funnel: from the whole world to one country, then a region

Use this when SKILL.md Steps 1–3 (gut call, recon, reading and searching) did not settle the country, or to
double-check a gut call before going deeper. Apply the clues that exclude the most of the world first, keep
every survivor on the board, and only then argue about style.

## 1. Order of discriminators (strongest exclusion first)

| Order | Clue | Typically removes | Tool / reference |
|---|---|---|---|
| 1 | Readable text: language, alphabet, diacritics, phone, domain, currency, postal code, brand | most of the world in one step | `textgeo.py`, web search, `languages` section below |
| 2 | Driving side (from moving/parked cars, signs on the "wrong" side) | ~70 left-hand vs ~170 right-hand territories | `board.py apply --kind driving-side --value left` |
| 3 | Plate shape and colours (EU band, yellow rear/both, Mercosur blue top band, US 2:1, Japanese small plates) | continents → a handful of countries | `world/*.md`, `refsheet.py` |
| 4 | Road paint: yellow vs white centre line, edge-line colour, dashed patterns | Americas vs elsewhere; some Nordic/Asian/African cases | `world/general.md` |
| 5 | Sign families: Vienna-convention (red-ringed circles, red triangles) vs MUTCD-style (yellow diamonds), sign backs, chevrons | the Americas/Australia vs Europe/Asia/Africa; then country styles | `world/general.md`, regional files |
| 6 | Hemisphere and latitude from the sun and shadows (time optional) | half the world; latitude bands | `sun.py locate`, `sky.md` |
| 7 | Biome, soil, terrain, climate | deserts vs tropics vs boreal; red soils | your eye, `world/*.md`, z13 satellite per candidate |
| 8 | Infrastructure styles: poles, insulators, bollards, guardrails, kilometre markers, curbs | separates neighbours | `refsheet.py countries A,B,C` |
| 9 | Architecture, roofs, fences, water tanks, religious buildings | separates neighbours/regions | regional files, reference sheets |
| 10 | Vehicles, liveries, mailboxes, bus stops, shop formats | separates neighbours/regions | web search, reference sheets |
| 11 | World prior (StreetCLIP + GeoCLIP) | orders the survivors when clues run out | `prior.py` (status model) |

Rules of thumb:
- One strong clue beats twenty weak ones; but one misread strong clue (mirrored image, imported car, foreign
  shop) beats nothing — check strong clues twice (zoom, second crop, mirror test).
- Negative clues count only if the thing would be visible: "no yellow centre line" on a road with no centre line
  at all says nothing.
- Border areas, tourist zones, diaspora shops, ports and freight corridors mix countries' features.
- Old and new conventions coexist for years (old plates, repainted lines): note both, use them for dating.

## 2. Putting it on the board

```bash
uv run scripts/board.py apply --kind driving-side --value right          # adds every RHT country, observed (LR 5) vs LHT ones (not excluded)
uv run scripts/board.py ingest recon/textgeo.json                         # one clue per text signal, capped by status
uv run scripts/board.py ingest recon/prior/prior.json                     # status model: ranks only, never verified
uv run scripts/board.py clue "Mercosur plate, blue band on top" --kind plate --status observed --file detect/03_plate.jpg
uv run scripts/board.py evidence --clue K7 --for Argentina:4 --for Brazil:4 --for Uruguay:4 --for Paraguay:4 --why "Mercosur format"
uv run scripts/board.py rank
uv run scripts/board.py next        # tells you whether candidates are separable and which cheap test to run next
```

Likelihood-ratio habits: observed shapes/colours 2–5, inferred 1.5–3, read text 5–20 (a phone number +351 ≈ 20,
a language with several countries ≈ 5–10), computed geometry up to 50. Record evidence *against* candidates
too ("no Cyrillic anywhere on a busy street" is evidence against Russia at ~0.5, not an exclusion).

## 3. Separating look-alikes

1. Write the two or three candidates and what would separate them (from the "Commonly confused" sections of
   the regional files, or from your own knowledge).
2. Pull current imagery instead of trusting memory:
   ```bash
   uv run scripts/refsheet.py countries AR,UY --n 8 --side right --out ref.jpg     # roadside: poles, curbs, fences
   uv run scripts/refsheet.py countries AR,UY --n 8 --pitch -12 --out ref_paint.jpg # road paint and surface
   uv run scripts/refsheet.py regions "BR:Santa Catarina,BR:Rio Grande do Sul" --n 6
   ```
3. Search the web for the specific convention ("Uruguay license plate colour 2024", "<country> bollard") and
   prefer official or recent sources over memorised metas.
4. Record the decision as evidence with the sheet as the file. If two candidates remain inseparable, say so,
   pick the better-supported one, and name the test that would decide.

## 4. Region and town

- **Codes**: regional plate codes (letters/numbers per province or district in DE, FR, IT, ES, PL, RU, TR, RO,
  BR, MX, ZA, CN, …), area codes and phone geocoding (`textgeo.py`), postal codes, road-number prefixes.
- **Language variants and regional languages**: Catalan/Basque/Galician in Spain, Welsh in Wales, Swedish on
  Finnish coastal signs, Hungarian in southern Slovakia, French/German/Italian in Switzerland, Tamil vs Sinhala in
  Sri Lanka, regional Indian scripts, Uyghur/Tibetan/Mongolian scripts in China, Tifinagh in Morocco.
- **Lists**: `board.py children "<country>"` puts every first-level region on the board; `prior.py` ranks
  regions for the top countries; `refsheet.py regions …` compares them on the ground.
- **Gradients**: vegetation and climate (coast vs interior, north vs south, altitude), soil colour, architecture
  (roof pitch and material, building age), agriculture (crops, field shapes), religious buildings.
- **Named things**: any place, school, church, company or street name → `poi.py`, `geodata.py search`,
  `textgeo.py --country XX --deep` (full national gazetteer), and web search with the region name.

## 5. Scripts and letters at a glance

`textgeo.py` encodes these; this is the human version.

| You see | Points to |
|---|---|
| Thai / Lao / Khmer / Burmese / Sinhala / Thaana / Georgian / Armenian / Ethiopic / Hangul / Kana | TH / LA / KH / MM / LK / MV / GE / AM / ET–ER / KR / JP |
| Greek | GR, CY |
| Hebrew | IL (trilingual signs with Arabic and English) |
| Tifinagh on official signs | MA (Algeria rarely) |
| Devanagari | IN (Hindi belt, Maharashtra), NP |
| Bengali | BD, IN (West Bengal, Tripura, Assam) |
| Tamil | IN (Tamil Nadu), LK (north/east and trilingual signs), SG, MY |
| Other Indic scripts | IN: Gurmukhi Punjab, Gujarati, Oriya Odisha, Telugu AP/Telangana, Kannada Karnataka, Malayalam Kerala |
| Cyrillic with і ї є ґ | UA; ў → BY; ђ ћ → RS; ѓ ќ ѕ → MK; ә ғ қ ң ө ұ ү һ → KZ (some also KG, MN, TJ) |
| Arabic script with پ چ ژ گ | IR, AF, PK; ٹ ڈ ڑ ں ے → PK (Urdu); Persian digits ۴۵۶ → IR/AF/PK |
| Simplified Chinese | CN (also SG, MY); traditional → TW, HK, MO; 駅 図 県 気 売 → JP |
| Latin: ő ű / ł ś ź / ř ů ě / ľ ĺ / ș ț / ğ ı / ß / å æ ø / ð þ / ñ / ã õ / ë / ė į ų / ā ē ķ ļ ņ | HU / PL / CZ / SK / RO / TR (AZ) / DE-AT / Nordic / IS (FO) / Spanish-speaking / PT-BR / AL / LT / LV |
| Vietnamese stacked diacritics (ơ ư ạ ố ữ …) | VN |
