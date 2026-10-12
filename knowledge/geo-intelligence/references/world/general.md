# Discriminators that work everywhere

- [Quick table](#quick-table)
- [Sun, shadows, satellite dishes](#sun-shadows-satellite-dishes)
- [Traffic and roads](#traffic-and-roads)
- [Plates](#plates)
- [Text, brands and buses](#text-brands-and-buses)
- [Nature](#nature)
- [Infrastructure](#infrastructure)
- [Buildings](#buildings)
- [Format changes that date a photo](#format-changes-that-date-a-photo)

Scope: clues that split the world before you know the region. Country-specific detail lives in the regional
files; entry format and rules: [index.md](index.md). Check items marked "(verify)" with a web search or a
`refsheet.py` comparison before you lean on them.

## Quick table

| Clue | First split it gives | Tool |
|---|---|---|
| Driving side | ~70 left-hand vs ~170 right-hand territories | `board.py apply --kind driving-side --value left` |
| Script and diacritics | language → a few countries | `textgeo.py` |
| Plate shape/colour | continent → country group | regional files, `refsheet.py` |
| Centre-line colour | the Americas (yellow) vs most of the rest (white) | regional files |
| Warning-sign shape | yellow diamonds vs red-bordered triangles | regional files |
| Sun / shadows / dishes | hemisphere and latitude band | `sun.py`, [sky.md](../sky.md) |
| Biome and soil | climate zone | your eye, satellite |
| Phone prefix, web domain | country | `clues.py lookup calling-code` |
| Street View car/camera | covered countries, generation | [streetview.md](streetview.md) |

## Sun, shadows, satellite dishes

### Where the sun is at midday
- Look for: the sun's side of the sky, the direction of shadows of vertical objects, which facades are lit around midday.
- Points to: north of the Tropic of Cancer the noon sun is due south; south of the Tropic of Capricorn it is due north; between the tropics it can be either side depending on the date.
- Strength: strong for the hemisphere once you know the camera heading and that it is near midday; medium otherwise.
- Counterexamples: morning/evening sun is far east/west, not south/north; a mirrored image flips everything; reflections from glass towers mimic sunlight.
- Verify: `sun.py locate/facing/compass` with whatever time information exists (EXIF, shop hours, shadows); [sky.md](../sky.md).
- Source: general knowledge (solar geometry).

### Satellite TV dishes
- Look for: the direction and the elevation of household dishes on many buildings.
- Points to: dishes aim at geostationary satellites over the equator, so they face roughly south in the northern hemisphere and roughly north in the southern; they tilt up steeply near the equator and lie lower toward the poles. A whole street aiming the same way gives the equator's direction.
- Strength: medium (strong for the hemisphere when many dishes agree).
- Counterexamples: dishes aimed at different satellites differ by tens of degrees in azimuth; offset-feed dishes look more upright than their real elevation angle.
- Verify: `sun.py dish --lat <lat> --sat <satellite longitude> --azimuth <deg>` works back to longitude ([sky.md §5](../sky.md#5-satellite-tv-dishes)).
- Source: general knowledge (orbital geometry).

## Traffic and roads

### Driving side
- Look for: which side moving traffic keeps to, the side parked cars face, the steering-wheel side of vehicles, which side of the road signs stand on, bus doors.
- Points to: left-hand traffic in the UK, Ireland, Malta, Cyprus, Japan, India, Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan, Thailand, Malaysia, Singapore, Indonesia, Brunei, Timor-Leste, Hong Kong, Macau, Australia, New Zealand, most of southern and eastern Africa (South Africa, Lesotho, Eswatini, Botswana, Namibia, Zimbabwe, Zambia, Malawi, Mozambique, Tanzania, Kenya, Uganda), Mauritius, Seychelles, Suriname, Guyana and many Caribbean islands; right-hand traffic almost everywhere else.
- Strength: strong (one clue removes a large part of the world).
- Counterexamples: mirrored images (check text); imported left-hand-drive cars in some LHT countries and vice versa; one-way streets; Gibraltar drives on the right while the UK drives on the left; mainland China drives on the right while Hong Kong and Macau drive on the left.
- Verify: `clues.py lookup driving-side left`, then `board.py apply --kind driving-side --value left`.
- Source: `assets/data/driving_side.json` (Wikipedia, curated).

### Centre and edge line colours
- Look for: the colour of the line separating opposite directions, and of edge lines.
- Points to: yellow centre lines are standard in the United States, Canada and Mexico and widespread in Latin America; most of Europe, Africa, the Middle East and Oceania use white. Notable non-American yellow uses: Norway (lines separating opposite traffic), Finland in imagery before about 2020–2023 (all permanent lines white since the June 2020 Road Traffic Act; see [europe.md](europe.md#yellow-centre-line)), South Korea (centre lines), Japan (yellow centre lines mark no-overtaking sections), New Zealand (yellow no-overtaking lines), yellow edge lines in South Africa and Ireland.
- Strength: medium (strong in combination with plates/signs).
- Counterexamples: temporary roadworks lines are yellow in several European countries; some Latin American roads use white centre lines (see [americas.md](americas.md)); faded paint changes apparent colour; parking-restriction kerb lines are not centre lines.
- Verify: `refsheet.py countries <A,B> --pitch -12` to see current paint; web search "<country> road markings".
- Source: general knowledge (verify per country); Finland: https://en.wikipedia.org/wiki/Road_surface_marking checked 2026-10.

### Kerb lines for parking rules
- Look for: single or double yellow lines along the kerb; painted kerbs (yellow, red-white, black-white).
- Points to: double yellow kerb lines are the UK/Irish parking restriction; painted kerbs are common in Spain (yellow), Latin America, South Africa, Southeast Asia, Israel and Australia, each with its own colours.
- Strength: weak to medium.
- Counterexamples: kerb paint conventions repeat across many countries.
- Verify: regional files; `refsheet.py … --pitch -15`.
- Source: general knowledge.

### Warning signs and stop signs
- Look for: the shape and background of warning signs; the word on the octagonal stop sign.
- Points to: yellow diamond warning signs (the US-style family) in the Americas, Australia, New Zealand, Ireland, Japan, Thailand, Malaysia, Indonesia and some others; red-bordered triangles (Vienna-convention family) across Europe, most of Asia, Africa and the Middle East, with a yellow background in Sweden, Finland, Norway, Iceland, Poland and Greece (verify for others). Stop-sign word: STOP in most countries; PARE in Brazil and much of South America and the Spanish Caribbean; ALTO in Mexico and Central America; ARRÊT in Quebec; 止まれ on an inverted red triangle in Japan; 정지 in Korea; หยุด in Thailand; قف in Arab countries; ایست in Iran.
- Strength: strong for the family, medium for the country.
- Counterexamples: imported or old signs; bilingual stop signs; Ireland's yellow diamonds vs the UK's triangles is a key UK/IE split.
- Verify: regional files; web search "<country> warning signs".
- Source: general knowledge (verify country lists).

## Plates

### Plate shape and the EU band
- Look for: the plate's proportions and colours, even when the characters are unreadable.
- Points to: long narrow plates → Europe (a blue band with stars and a country code on the left → an EU member, plus Norway-style national bands); about 2:1 plates → North America, also much of Latin America and Asia; 2:1 plates with kana → Japan (330 × 165 mm standard, 440 × 220 mm large); white plates with a blue top band → Mercosur format (Argentina, Brazil, Uruguay, Paraguay).
- Strength: medium (strong with colours).
- Counterexamples: Japanese plates share the North American 2:1 shape, so separate them by driving side and script; square plates on some European cars and most motorbikes; foreign cars near borders and on freight corridors; overexposure whitens colours.
- Verify: regional files; zoom the crop from `detect.py`.
- Source: general knowledge; Japanese sizes: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Japan checked 2026-10.

### Plate colours
- Look for: background colours front and rear.
- Points to: yellow front and rear → the Netherlands, Luxembourg, Israel, Colombia (private cars), (verify others); white front + yellow rear → United Kingdom, Cyprus, Kenya; black plates with white characters → Malaysia (and older plates in several Asian countries); Japanese kei cars → yellow; India → white private, yellow commercial, green electric.
- Strength: medium to strong.
- Counterexamples: commercial, diplomatic, temporary and old-format plates differ from private ones; formats change (Indonesia moved from black to white plates from 2022).
- Verify: web search "<country> license plate colours", regional files.
- Source: general knowledge (verify).

### Plate background and graphics in countries that issue plates by state/province
- Look for: when the characters can't be read: the plate's overall background colour, colour bands, central graphic (state or provincial flag), border colour.
- Points to: state/province level (US, Mexico, Canada, Brazil's old format, Australia, etc.).
- Strength: medium (filter to a few states against a chart of state plate designs; narrows by an order of magnitude in one step).
- Counterexamples: out-of-state vehicles crossing state lines (especially common on freight corridors and in border cities); old and new formats coexist, and reference charts go out of date; overexposure in strong light renders light-coloured graphics as white.
- Verify: web search a current plate chart for the candidate states.
- Source: general knowledge.

## Text, brands and buses

### Official bilingual or multilingual signs
- Look for: two languages with the same content on one official traffic sign or street-name sign.
- Points to: an officially multilingual admin area, not "near a country that speaks that language" (e.g., German–Italian bilingual signs in Italy → South Tyrol; Swedish–Finnish → coastal Finland; Welsh–English → Wales; Catalan/Basque/Galician–Spanish → those Spanish regions; Tifinagh–Arabic–French → Morocco).
- Strength: strong.
- Counterexamples: bilingual private shop signs don't count; foreign-language signs added for tourists don't count.
- Verify: `textgeo.py --text "<sign text>"`, web search the place names.
- Source: general knowledge (official-language laws of each area).

### Sub-brands and business lines of chain brands
- Look for: small marks on the sign besides the parent brand (truck tyre retreading, commercial-vehicle service, etc.).
- Points to: sub-brands have far fewer stores, so listing all their stores gives a candidate point list; also suggests a freight corridor or an industrial outskirt.
- Strength: weak alone; medium together with a store search.
- Counterexamples: store data on maps is incomplete; store locators can be several km off.
- Verify: `textgeo.py --text "<brand>"` (where the brand operates), opening press releases, `osm.py along` + street-level sampling ([search.md](../search.md)).
- Source: general knowledge (method).

### Ads for regional consumer goods
- Look for: drink, snack, telecom and bank brand ads on vehicles, kiosks and walls.
- Points to: the country or region where the brand mainly sells (telecom operators and banks are usually national).
- Strength: weak for consumer goods, medium for telecoms/banks.
- Counterexamples: multinational brands, imported brands, cross-border advertising.
- Verify: `textgeo.py --text "<brand>"`, web search.
- Source: general knowledge.

### Bus operator abbreviation + route number
- Look for: the operator name and route number at the top of the bus front and rear.
- Points to: city; route number → `osm.py route` gives the corridor to search along.
- Strength: strong to the city; with a route map, to one line.
- Counterexamples: second-hand imported buses keep their original livery and text; route numbers change.
- Verify: web search "<operator> <route>"; `osm.py route --area <city> --kind bus --ref <route> --out route.json`.
- Source: general knowledge.

### International phone prefix and web domain
- Look for: a phone number written with a country prefix (+33, 0033) on signs, vans and shopfronts; a country-code web domain (.de, .pl, .com.br, .co.za).
- Points to: the country that owns the calling code or domain.
- Strength: strong for an international prefix on local infrastructure; medium for a domain.
- Counterexamples: +1 covers the US, Canada and many Caribbean states, +7 Russia and Kazakhstan; businesses advertise foreign numbers near borders and in diaspora shops; .co, .tv, .me, .io and similar are sold worldwide; .com says nothing.
- Verify: `clues.py lookup calling-code +594`; web search the domain.
- Source: regulation (ITU E.164 country codes, IANA ccTLD list).

### Numbered road shields
- Look for: route numbers in shields or panels (US Interstate red-white-blue shields, European E-road green panels, national road-number formats).
- Points to: one specific road; add an exit number, kilometre marker or skyline landmark to fix the segment and direction.
- Strength: strong (to one road).
- Counterexamples: the same number exists in several states/countries; the sign can be tiny and easy to miss. Country shield styles: [americas.md](americas.md), [europe.md](europe.md).
- Verify: `osm.py find --area <region> '["highway"]["ref"="<number>"]'`; web search.
- Source: general knowledge.

## Nature

### Eucalyptus
- Look for: tall smooth-barked trees with peeling bark and sparse grey-green crowns, often in plantations.
- Points to: native to Australia, but planted on a large scale in Portugal, Galicia (Spain), Brazil, Uruguay, Argentina, Chile, South Africa, Ethiopia, Kenya, India, southern China and California.
- Strength: weak (it widens rather than narrows outside Australia).
- Counterexamples: everywhere listed above.
- Verify: combine with soil, roads, plates.
- Source: general knowledge.

### Red laterite soil
- Look for: deep red/orange bare soil on verges, tracks and building sites.
- Points to: tropical and subtropical weathered soils: much of sub-Saharan Africa, Brazil and Paraguay, parts of India and Southeast Asia, northern and inland Australia.
- Strength: weak to medium.
- Counterexamples: red soils also occur in the Mediterranean (terra rossa) and in the US South.
- Verify: satellite colour of fields around candidates (`tiles.py fetch --zoom 13`).
- Source: general knowledge.

### Biome signatures
- Look for: birch and spruce (boreal: Nordics, Baltics, Russia, Canada); cork and olive groves (Mediterranean); rice paddies (monsoon Asia, but also Italy's Po valley, Arkansas/California, southern Brazil); cacti and agave (Mexico, the US Southwest, Andes, dry Brazil, also planted in the Mediterranean); acacia savanna (East/Southern Africa, also parts of Australia); dense bamboo (East/Southeast Asia).
- Points to: climate zone, then the candidates within it.
- Strength: weak alone; strong for excluding whole climates.
- Counterexamples: planted ornamentals (palms on Mediterranean promenades, eucalyptus everywhere); altitude changes vegetation within one country.
- Verify: phenology must be paired with the month; satellite land cover around candidates.
- Source: general knowledge.

## Infrastructure

### Uniform streetlight and pole designs within an area
- Look for: streetlight pole colour, lamp head shape, pole material (wood, concrete, steel), cross-arms, insulators, transformer placement.
- Points to: utilities and municipalities procure uniform designs; neighbours often differ.
- Strength: weak for finding, medium for separating two candidates.
- Counterexamples: one manufacturer sells to many places; old and new designs coexist.
- Verify: `refsheet.py countries <A,B> --side right` or `refsheet.py regions "<CC>:<region>,<CC>:<region>"`.
- Source: general knowledge.

### Arched cross-arms on the French distribution grid (inherited standards)
- Look for: a cross-arm arching upward on top of a concrete or metal pole, three conductors hanging from suspension insulators; identical poles lined up into the distance.
- Points to: the French grid system: metropolitan France and the overseas departments that keep its standards; some former colonies have similar pole types. In general, a recognised national standard points to the home country + territories that keep its standards + some former colonies.
- Strength: medium.
- Counterexamples: neighbouring countries' border areas; former colonies that changed pole types; small distant arms look arched when they are not — zoom.
- Verify: `refsheet.py countries FR,<candidate>`; `clues.py lookup territories France`.
- Source: general knowledge (the French medium-voltage "nappe voûte" cross-arm).

### Stobie poles
- Look for: utility poles made of two steel I-beams with concrete filling between them.
- Points to: South Australia (Adelaide area), where they are standard; rarer elsewhere in Australia.
- Strength: strong for South Australia.
- Counterexamples: few; similar-looking concrete poles exist elsewhere.
- Verify: `refsheet.py regions "AU:South Australia,AU:Victoria"`.
- Source: general knowledge.

## Buildings

### Arch form: round or pointed
- Look for: whether door and window arches are round or pointed; biforate windows.
- Points to: round → Romanesque or Renaissance; pointed → Gothic. A city with few medieval remains but an "intact medieval courtyard" → think replicas (exhibition pavilions, mock-historic streets, film sets).
- Strength: weak (narrows building type and search terms).
- Counterexamples: replicas are common; reverse image search in a Chinese-language interface returns many modern Chinese red-brick buildings.
- Verify: web search with style words only after checking the form ([search.md §3](../search.md#3-descriptive-keyword-image-search)).
- Source: general knowledge (architectural history).

## Format changes that date a photo

A new format proves the photo is from that year or later; an old one only suggests earlier, because old and new
coexist for years. Details and sources are in the file named.

| Country | Change | Year | File |
|---|---|---|---|
| Argentina | Mercosur `AB 123 CD` (white on black `ABC 123` 1995–2016) | Apr 2016 | [americas.md](americas.md) |
| Brazil | Mercosur `ABC1D23` (grey `ABC-1234` before) | Sep 2018, all states by Jan 2020 | [americas.md](americas.md) |
| Bulgaria | euro replaces the lev | Jan 2026 | [europe.md](europe.md) |
| Chile | four letters + two digits (two letters + four digits 1985–2007) | 2007 | [americas.md](americas.md) |
| Croatia | euro | 2023 | [europe.md](europe.md) |
| Cyprus, north | white plates with a blue band (white/yellow with red border before) | 2018 | [europe.md](europe.md) |
| Finland | all permanent road lines white (yellow centre and barrier lines before) | Jun 2020, 3-year transition | [europe.md](europe.md) |
| France | SIV `AB-123-CD` plates | 2009 | [europe.md](europe.md) |
| India | BH series, not tied to a state | 2021 | [asia.md](asia.md) |
| Indonesia | private plates white (black before; both until about 2027) | Jun 2022 | [asia.md](asia.md) |
| Iraq | Latin-letter plates with an IRQ band | Apr 2022 Kurdistan, Jun 2024 rest | [africa-middle-east.md](africa-middle-east.md) |
| Israel | `123-45-678` (`12-345-67` 1980–2017) | Jul 2017 | [africa-middle-east.md](africa-middle-east.md) |
| Italy | `AB 123 CD`; blue bands at both ends from 1999 | 1994 | [europe.md](europe.md) |
| Japan | English "STOP" added to 止まれ signs | 2017 | [asia.md](asia.md) |
| Kyrgyzstan | region code at the left of the plate | Jul 2016 | [asia.md](asia.md) |
| Myanmar | Latin-character plates (Burmese script before) | Sep 2013 | [asia.md](asia.md) |
| New Zealand | `ABC123` (`AB1234` before) | Apr 2001 | [oceania.md](oceania.md) |
| North Macedonia | NMK plate band (MK before) | Feb 2019 | [europe.md](europe.md) |
| Paraguay | Mercosur `ABCD 123` | Jul 2019 | [americas.md](americas.md) |
| Philippines | region letter back on car plates (none on 2014–2017 car plates) | 2018 | [asia.md](asia.md) |
| Portugal | yellow year/month strip at the right (none after 2020) | 1998–2020 | [europe.md](europe.md) |
| Qatar | a letter added after the six digits | Dec 2025 | [africa-middle-east.md](africa-middle-east.md) |
| Senegal | `AA-123-BC` with a blue left band | 2019 | [africa-middle-east.md](africa-middle-east.md) |
| South Africa | KwaZulu-Natal ZN plates replace town codes | 2024–2025 | [africa-middle-east.md](africa-middle-east.md) |
| South Korea | 3-digit class number; holographic band from Jul 2020; light-green high-value corporate plates from 2024 | Sep 2019 | [asia.md](asia.md) |
| Spain | `1234 BCD`, no province code (province codes before) | Sep 2000 | [europe.md](europe.md) |
| Sri Lanka | province code dropped from new plates | 2023–2025 | [asia.md](asia.md) |
| Sweden | `ABC 12A` added to `ABC 123` | 2019 | [europe.md](europe.md) |
| Uganda | digital plates `UA 123AB` | Jan 2025 | [africa-middle-east.md](africa-middle-east.md) |
| United Kingdom | `AB12 CDE` with an age identifier | Sep 2001 | [europe.md](europe.md) |
| United Kingdom | UK identifier replaces GB | Sep 2021 | [europe.md](europe.md) |
| United States | front plate dropped: Ohio 2020, Alaska 2022 | 2020, 2022 | [americas.md](americas.md) |
| Uruguay | Mercosur `ABC 1234` (mandatory 2016) | 2015 | [americas.md](americas.md) |
| Google Street View | Gen 4 camera | Aug 2017 | [streetview.md](streetview.md) |
| Google Street View | small cam published | late 2024 | [streetview.md](streetview.md) |
| Google Street View | India road coverage; Germany nationwide | Jul 2022; Jul 2023 | [streetview.md](streetview.md) |
