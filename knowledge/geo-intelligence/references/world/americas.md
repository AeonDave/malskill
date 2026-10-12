# Americas clues

- [Quick table](#quick-table)
- [Region-wide patterns](#region-wide-patterns)
- [United States (US)](#united-states-us)
- [Canada (CA)](#canada-ca)
- [Mexico (MX)](#mexico-mx)
- [Guatemala (GT)](#guatemala-gt)
- [Belize (BZ)](#belize-bz)
- [El Salvador (SV)](#el-salvador-sv)
- [Honduras (HN)](#honduras-hn)
- [Nicaragua (NI)](#nicaragua-ni)
- [Costa Rica (CR)](#costa-rica-cr)
- [Panama (PA)](#panama-pa)
- [Cuba (CU)](#cuba-cu)
- [Haiti (HT)](#haiti-ht)
- [Dominican Republic (DO)](#dominican-republic-do)
- [Puerto Rico (PR)](#puerto-rico-pr)
- [US Virgin Islands (VI)](#us-virgin-islands-vi)
- [Jamaica (JM)](#jamaica-jm)
- [Bahamas (BS)](#bahamas-bs)
- [Trinidad and Tobago (TT)](#trinidad-and-tobago-tt)
- [Barbados (BB)](#barbados-bb)
- [Smaller English-speaking islands (AG, KN, DM, LC, VC, GD, AI, MS, VG, KY, TC)](#smaller-english-speaking-islands-ag-kn-dm-lc-vc-gd-ai-ms-vg-ky-tc)
- [Bermuda (BM)](#bermuda-bm)
- [Dutch islands (AW, CW, BQ, SX)](#dutch-islands-aw-cw-bq-sx)
- [French Antilles (GP, MQ, MF, BL)](#french-antilles-gp-mq-mf-bl)
- [Colombia (CO)](#colombia-co)
- [Venezuela (VE)](#venezuela-ve)
- [Guyana (GY), Suriname (SR), French Guiana (GF)](#guyana-gy-suriname-sr-french-guiana-gf)
- [Ecuador (EC)](#ecuador-ec)
- [Peru (PE)](#peru-pe)
- [Bolivia (BO)](#bolivia-bo)
- [Brazil (BR)](#brazil-br)
- [Paraguay (PY)](#paraguay-py)
- [Uruguay (UY)](#uruguay-uy)
- [Argentina (AR)](#argentina-ar)
- [Chile (CL)](#chile-cl)
- [Falklands (FK)](#falklands-fk)
- [Commonly confused](#commonly-confused)

Scope: the United States (to state level), Canada (to province level), Mexico, Central America, the Caribbean with its dependent territories, and South America with the Guianas and the Falklands.
Facts were checked against laws, plate and sign standards or the cited pages in 2026-10. "(typ.)" = typical of the regional norm, not verified for that country or state; "(unverified)" and "(single source)" stay weak. Formats change: read every "since YYYY" as a dating clue as well.
Street View coverage by country: [streetview.md](streetview.md) §3; coverage changes yearly, and `pano.py coverage <lat,lon> --radius 400` is the live check. No official road coverage in BZ, SV, HN, NI, CU, HT, BS, BB, TC, MQ, VE, GY, SR: expect phone or contributed photos and start from the quick table.
Hawaii, Easter Island and the Galápagos are entries in the United States, Chile and Ecuador sections.

## Quick table

L = left-hand traffic (bold), R = right. "—" = not documented here; sample it with `refsheet.py countries <ISO2> --n 6`.

| Country (ISO2) | Drive | Plate quick look | Centre / edge paint | Language tells | Other strong tells |
|---|---|---|---|---|---|
| United States (US) | R | 12×6 in, state name; 21 states rear-only | yellow / white | English; Spanish in SW, FL | "SPEED LIMIT" in mph; red-white-blue Interstate shield; state route shields |
| Canada (CA) | R | 12×6 in, province name; front plate only BC, MB, ON | yellow / white | English, French; syllabics in Nunavut | km/h speed signs; STOP/ARRÊT; postcode A1A 1A1 |
| Mexico (MX) | R | 12×6 in, state name, ABC-123-D | yellow / white | Spanish; Nahuatl, Maya names | ALTO; TOPE signs; "MEX" shield, D = toll road |
| Guatemala (GT) | R | P 123ABC (class letter first), "Centro América" | yellow (typ.) | Spanish; Mayan q', tz', k' | TÚMULO; painted ex-US school buses; +502 |
| Belize (BZ) | R | — | — | English (official), Kriol, Spanish | English text with right-hand traffic in Central America; +501 |
| El Salvador (SV) | R | 12×6 in, faint flag in background (2011–) | yellow (typ.) | Spanish | prices in US$; +503 |
| Honduras (HN) | R | blue top band, map of Honduras behind serial (2018–) | yellow (typ.) | Spanish | prices in L (lempira); +504 |
| Nicaragua (NI) | R | map of Nicaragua behind serial; region letters + digits | yellow (typ.) | Spanish | prices in C$; +505 |
| Costa Rica (CR) | R | black on white, 123456 or ABC-123 | yellow (typ.) | Spanish | landmark addresses ("200 m norte de…"); ₡; +506 |
| Panama (PA) | R | rear plate only, AB1234 (2013–) | yellow (typ.) | Spanish | US$ and B/.; taxis show the plate on their sides; +507 |
| Cuba (CU) | R | — | — | Spanish | red-rimmed triangular warning signs; PARE; 1950s US cars and Ladas |
| Haiti (HT) | R | — | — | French, Kreyòl (ò, è) | painted tap-tap pickups and buses; +509 |
| Dominican Rep. (DO) | R | 12×6 in, type letter + digits; often one plate | yellow (typ.) | Spanish | PARE; motoconchos; +1 809/829/849 |
| Puerto Rico (PR) | R | rear only, ABC 123, "Isla del Encanto" | yellow / white (MUTCD) | Spanish, English | US-design signs in Spanish; mph speeds, km distances; +1 787/939 |
| US Virgin Is. (VI) | **L** | US style | yellow / white (MUTCD) | English | left-hand traffic with US cars and US signs; +1 340 |
| Jamaica (JM) | **L** | private 1234 AB blue on white; red = public passenger | — | English, Patois | mostly right-hand-drive cars; +1 876/658 |
| Bahamas (BS) | **L** | — | — | English | left-hand traffic, mostly left-hand-drive cars; +1 242 |
| Trinidad & Tobago (TT) | **L** | P/H/T + series + number, often white on black | — | English | Hindu prayer flags, mosques; +1 868 |
| Barbados (BB) | **L** | — | — | English | coral-limestone terraces, sugarcane, chattel houses; +1 246 |
| Bermuda (BM) | **L** | long 520×110 mm, five digits | — | English | white stepped roofs; 35 km/h; +1 441 |
| Cayman Is. (KY) | **L** | — | — | English | +1 345 |
| Turks & Caicos (TC) | **L** | — | — | English | +1 649; US$ |
| British Virgin Is. (VG) | **L** | — | — | English | +1 284; US$ |
| Anguilla (AI) | **L** | — | — | English | +1 264; EC$ |
| Montserrat (MS) | **L** | — | — | English | +1 664; EC$ |
| Antigua & Barbuda (AG) | **L** | — | — | English | +1 268; EC$ |
| St Kitts & Nevis (KN) | **L** | — | — | English | +1 869; EC$ |
| Dominica (DM) | **L** | — | — | English, French Creole names | +1 767; EC$ |
| St Lucia (LC) | **L** | — | — | English, French Creole names | +1 758; EC$ |
| St Vincent & Gren. (VC) | **L** | — | — | English | +1 784; EC$ |
| Grenada (GD) | **L** | — | — | English | +1 473; EC$ |
| Aruba (AW) | R | — | — | Papiamento, Dutch | divi-divi trees, cactus scrub; +297 |
| Curaçao (CW) | R | A 12-34 style, black on white | — | Papiamentu ("Kaya" = street), Dutch | +599 9 |
| Bonaire (BQ) | R | — | — | Papiamentu, Dutch | US$ since 2011; +599 7 |
| Sint Maarten (SX) | R | — | — | English, Dutch | English signs with right-hand traffic; +1 721 |
| Saint-Martin (MF), St-Barthélemy (BL) | R | — | — | French | +590 |
| Guadeloupe (GP), Martinique (MQ) | R | French AA-123-AA, region band 971 / 972 | white / white | French, Creole | French signs and bollards; EUR; +590 / +596 |
| Colombia (CO) | R | yellow (private) ABC 123, municipality at bottom | yellow / white | Spanish | 60X landline codes; "Calle 10 # 5-20"; PARE |
| Venezuela (VE) | R | AB123CD, state name at bottom | white (unverified) | Spanish | mobiles 0412/0414/0424; PARE; +58 |
| Guyana (GY) | **L** | white on black, P/H/B/G + letters + number | — | English | left-hand traffic on the mainland; +592 |
| Suriname (SR) | **L** | black on yellow, P + letter + 4 digits | — | Dutch, Sranan Tongo | left-hand traffic on the mainland; +597 |
| French Guiana (GF) | R | French plate, region band 973 | white / white | French | EUR; +594 |
| Ecuador (EC) | R | ABC-1234, first letter = province | yellow / white | Spanish; Kichwa | prices in US$; E-numbered roads (E35); +593 |
| Peru (PE) | R | 12×6 in, "PERÚ" + flag; first letter = region | yellow / white | Spanish; Quechua, Aymara | mototaxis; PE-1N road codes; ROMPEMUELLE |
| Bolivia (BO) | R | blue on white "BOLIVIA", 1234ABC + department letter | yellow (typ.) | Spanish; Quechua, Aymara | Altiplano adobe; +591 |
| Brazil (BR) | R | Mercosur ABC1D23 (2018–); grey ABC-1234 + city band | yellow / white | Portuguese (ã, õ, ç, -ção) | SP-/MG- state road codes; LOMBADA; +55 |
| Paraguay (PY) | R | Mercosur ABCD 123 (2019–); red on white before | yellow (typ.) | Spanish, Guaraní (ẽ, ỹ, g̃, ') | red soil; PY01–PY22 route codes; +595 |
| Uruguay (UY) | R | Mercosur ABC 1234, first letter = department | white dashes + yellow solid | Spanish with voseo | ".gub.uy" sites; ANCAP fuel; +598 |
| Argentina (AR) | R | Mercosur AB 123 CD (2016–); black ABC 123 (1995–2016) | white dashes + yellow solid | Spanish with voseo ("respetá") | Malvinas signs; CPA postcode A1234AAA; +54 |
| Chile (CL) | R | white, 4 letters + 2 digits (2007–) or AB·1234; "CHILE" | white (yellow in snowy south) | Spanish; Mapudungun names | lettered regional road codes (G-25); LOMO DE TORO; +56 |
| Falklands (FK) | **L** | — | white (UK style) | English (British spelling) | treeless moorland, gravel roads; +500 |

## Region-wide patterns

### Sign families and the stop word
- Most of the hemisphere uses the US-derived family: yellow diamond warning signs, red octagon stop, white rectangular regulatory signs with words. The US, Puerto Rico and the US Virgin Islands follow the MUTCD itself; Canada uses a metric version; Latin American manuals follow a shared Inter-American model with Spanish or Portuguese text.
- European-style triangles and round regulatory signs: French territories (GF, GP, MQ, MF, BL, Saint-Pierre-et-Miquelon) and the Falklands. Cuba uses red-rimmed triangles with a yellow fill. Argentina mixes triangles with diamonds. Dutch islands, Suriname and the former British islands: sample before assuming either family (unverified).
- Stop word (strong when readable): STOP = US, English Canada, English-speaking Caribbean, Belize, Guyana (Haiti likely French-style STOP, unverified); ARRÊT = Quebec (bilingual STOP/ARRÊT in parts of New Brunswick, Manitoba and Alberta; Inuktitut added in Nunavut); ALTO = Mexico and the Spanish-speaking Central American countries; PARE = Cuba, Dominican Republic, Puerto Rico, all Spanish-speaking South America and Brazil. Source: https://en.wikipedia.org/wiki/Stop_sign (checked 2026-10).
- Units: miles and mph in the US and the US Virgin Islands; Puerto Rico posts speeds in mph but distances in km; Canada, Mexico and Latin America use km/h; Bermuda km/h; Belize and the other former British islands not checked (some use mph).

### Centre lines
- Yellow separates opposing traffic almost everywhere: US (MUTCD standard since 1971), Canada, Mexico, Brazil, Colombia, Ecuador, Peru; Central America, Bolivia and Paraguay (typ.).
- Exceptions: Chile uses white (yellow on snowy southern and mountain roads); Argentina and Uruguay use white dashes where overtaking is allowed and solid yellow where it is not, often both side by side; Venezuela reportedly white (unverified); French territories and the Falklands white. Source: https://en.wikipedia.org/wiki/Road_surface_marking (checked 2026-10).
- US and Canada: yellow also marks the left edge of divided highways; white marks the right edge and same-direction lanes.

### Plates
- Size families: North American 12×6 in (2:1) across the US, Canada, Mexico, most of Central America (checked: GT, SV, NI, PA), Puerto Rico, the Dominican Republic, Peru and Suriname; Mercosur 400×130 mm with a blue top band (Argentina, Brazil, Uruguay, Paraguay); European 520×110 mm (Bermuda, French territories).
- Mercosur serial patterns differ by country, so the format decides even when the band is unreadable: AR `LL NNN LL`, BR `LLL N L NN`, UY `LLL NNNN`, PY `LLLL NNN`.
- Colour standouts: yellow → Colombia (private), Suriname (all), Ecuador (motorcycles); black background → Guyana and many Trinidad cars (white characters), Argentina 1995–2016, Brazilian original collector cars (since 2022); grey with black characters → Brazil before Mercosur; dark orange → Chilean taxis.
- Rear plate only: 21 US states, all of Canada except BC, MB and ON, Puerto Rico, Panama, and many Dominican cars in practice.

### Driving side
- Left: Guyana, Suriname, the Falklands, and the islands USVI, BVI, Anguilla, Antigua and Barbuda, Bahamas, Barbados, Bermuda, Cayman, Dominica, Grenada, Jamaica, Montserrat, St Kitts and Nevis, St Lucia, St Vincent, Trinidad and Tobago, Turks and Caicos.
- Right: everything else, including Belize, Cuba, Hispaniola, Puerto Rico and the Dutch and French islands.
- Left-hand traffic with mostly left-hand-drive cars: USVI and the Bahamas (US imports); Jamaica is mostly right-hand drive. Verify with `clues.py lookup driving-side left`.

### Text and language
- Spanish: ñ, ¿ ¡, -ción. Portuguese (Brazil): ã õ ç, -ção/-ções, nh, lh. French: è ê ç, "rue", "chemin". Haitian and Antillean Creole: ò, "lekòl", "pou". Dutch: ij, "straat", "weg". Papiamentu (Curaçao, Bonaire) and Papiamento (Aruba) differ in spelling.
- English spelling: "center/color" in the US; "centre/colour" in Canada, the English-speaking Caribbean, Guyana, Bermuda and the Falklands.
- Indigenous writing: Inuktitut syllabics (Nunavut, Nunavik), Cherokee syllabary (Cherokee NC, Tahlequah OK), Hawaiian ʻokina and macrons, Navajo ł ą ę, Guaraní ẽ ỹ g̃ and the apostrophe "puso", Quechua and Aymara q' k' ch', Mayan q' tz' k' b', Nahuatl tl/tz with -tlán, -tepec, -co, Mapudungun place names (-hue, -co, -quén) in south-central Chile.
- Voseo imperatives on signs and ads ("respetá", "manejá", "tenés"): Argentina, Uruguay, Paraguay.
- Currency marks: R$ BR, S/ PE, Bs BO and VE, ₲ PY, Q GT, L HN, C$ NI, ₡ CR, B/. PA, RD$ DO, J$ JM, TT$ TT, BZ$ BZ, EC$ eastern islands; US$ alone in the US, PR, VI, EC, SV, BQ, VG, TC and alongside B/. in PA. A bare "$" is ambiguous (MX, AR, CL, CO, UY, CU).

### Poles and roadside furniture (weak)
- Wooden poles with crossarms and grey cylinder transformers: US, Canada, many US-influenced islands.
- Concrete poles dominate most of Latin America; Brazil commonly uses flat-faced "double-T" concrete poles (share unverified).
- French territories use mainland French bollards (white, black band, red reflector). No other bollard standard is distinctive enough to list.

### Climate, vegetation and soil bands
- Boreal (Alaska, most of Canada): spruce, birch, bog. Prairie and plains (US Great Plains, Canadian Prairies): flat grain fields, elevators, shelterbelts. Pampas (Argentina, Uruguay, Rio Grande do Sul): equally flat but with eucalyptus windbreaks.
- Deserts: Sonoran (saguaro: southern Arizona, Sonora), Mojave (Joshua tree), Chihuahuan (yucca, creosote: northern Mexico, west Texas, southern New Mexico), Great Basin sagebrush, Atacama and coastal Peru (bare), Patagonian steppe (tussock grass, wind).
- Mediterranean: coastal California and central Chile look alike (golden summer grass, oaks or sclerophyll, eucalyptus); separate them with plates, paint and language.
- Wet tropics: southern Mexico, Central America, the Caribbean, the Amazon, the Pacific coast of Colombia and Ecuador, Brazil's Atlantic Forest. Dry tropics: Yucatán scrub, Brazil's caatinga, the Caribbean coast of Colombia and Venezuela, the Gran Chaco.
- Andes: páramo grassland in Colombia and Ecuador, puna and Altiplano in Peru and Bolivia, eucalyptus groves in highland farmland.
- Soils: red latosols (São Paulo, Paraná, Mato Grosso do Sul, Goiás, Misiones, eastern Paraguay); red clay (US Piedmont); red dirt (Oklahoma, northwest Texas, Prince Edward Island); white limestone or sand (Florida, Bahamas, Yucatán, Bermuda); black volcanic (Central America, Ecuador, Hawaii).

## United States (US)

**Quick facts**
- Driving right. Plates 12×6 in with the state name; designs vary and many states offer several, so treat a design as a lookup, not a fact. Front plate required in 29 states and DC.
- Road paint and signs: MUTCD (yellow between opposing lanes, white edges); yellow diamonds; "SPEED LIMIT nn" in mph; green guide signs; red-white-blue Interstate shield; black-and-white US Route shield; state route marker set by each state; county routes often a blue pentagon with a yellow number.
- Poles: wooden, crossarms, pole-top transformer cans.
- Language: English; Spanish signage in parts of the Southwest, Florida and big cities; Hawaiian, Cherokee and Navajo text locally.
- Phone: +1 NPA NXX XXXX; the area code maps to a state. Postal: ZIP 5 digits (+4). TLD: .us is rare; agencies use .gov.

### States: lookups that reach a state
- Rear plate only: AL, AK (since 2022), AZ, AR, DE, FL, GA, IN, KS, KY, LA, MI, MS, NM, NC, OH (since 2020), OK, PA, SC, TN, WV. Rhode Island since 2026 exempts cars built without a front mount (single source).
- Route shields: unique emblem: CA green miner's spade, KS sunflower, UT beehive, WA George Washington profile, NH Old Man of the Mountain, NM Zia sun, PA keystone, MI diamond with "M", CO state-flag motif, OR rounded inverted triangle (single source). State outline: AL, AZ, AR, FL, GA, ID, LA, MO, NV, OH, OK; SD likely; ND replacing its older design with an outline; TN and SC embed an outline in a larger design. Plain circle (MUTCD default): DE, IA, KY, MS, NJ. Square or rectangle: TX, CT, MA, ME, RI ("RI" above the number); VT's newer markers are green with the state name.
- Lettered roads: Missouri supplemental routes (A, B, KK; letters reused county by county); Wisconsin county trunk highways (CTH Q, CTH JJ); Iowa county roads of one letter + 2–3 digits (A–J east–west, counted north to south; K–Z north–south, counted west to east); Texas Farm/Ranch-to-Market roads (FM, RM); Virginia secondary routes numbered 600 and up (general knowledge).
- Number parity: Interstates odd north–south, increasing west to east (I-5 Pacific, I-95 Atlantic), even east–west, increasing south to north (I-10 south, I-90/94 north). US Routes are the reverse (US 1 east coast, US 101 west coast; US 2 north, US 90 Gulf).
- 80 mph or more is posted only in ID, MT, NV, ND (since 2025), OK, SD, TX (85 on SH 130), UT, WY. Source: https://www.motor1.com/features/758994/states-with-80-mph-speed-limits-2025/ (checked 2026-10).
- Local practice: "Michigan left" U-turn crossovers (MI); jughandle turns (NJ); raised ceramic dots as lane lines (CA, being phased out since 2017; HI, NV, TX, FL and other low-snow states); Utah grid addresses; "Parish" (LA) and "Borough" (AK) as county equivalents.
- ZIP first digit: 0 New England, NJ, PR, VI; 1 NY, PA, DE; 2 DC, MD, VA, WV, NC, SC; 3 FL, GA, AL, TN, MS; 4 OH, MI, IN, KY; 5 WI, MN, IA, ND, SD, MT; 6 IL, MO, KS, NE; 7 TX, OK, AR, LA; 8 CO, WY, ID, UT, AZ, NM, NV; 9 CA, OR, WA, AK, HI.
- Area codes: look up the full code (`textgeo.py --text "<number>"`), e.g. 212/646/718 New York City, 213/310/323 Los Angeles, 312/773 Chicago, 305/786 Miami, 702 Las Vegas, 808 Hawaii, 907 Alaska. Overlays and mobile portability make it state-level evidence only.

### States: landscape and building regions
- New England: maple, birch and pine forest, fieldstone walls, white clapboard houses and steepled churches.
- Mid-Atlantic: brick row houses in older cities, stone farmhouses and bank barns in Pennsylvania.
- Southeast Piedmont: red clay cuts, pine plantations, kudzu, brick ranch houses, mobile homes.
- Atlantic and Gulf coastal plain: flat, live oaks with Spanish moss, palmetto, cypress swamps, houses on piers near the coast.
- Florida: flat sand, palms, stucco houses with tile roofs, canals, screened pool enclosures.
- Midwest Corn Belt: corn and soy on a one-mile road grid, black soil, red barns and silos.
- Great Plains: wheat, grassland, grain elevators, centre-pivot circles, few trees except farmstead shelterbelts.
- Texas: mesquite and live oak in the Hill Country, flat West Texas with oil pumpjacks, FM roads everywhere.
- Intermountain West: sagebrush basins, ponderosa pine, aspen; red-rock plateaus in UT, AZ, NM, CO.
- Southwest deserts: saguaro (Sonoran), Joshua trees (Mojave), flat-roofed stucco and adobe (Pueblo style in NM), gravel yards.
- California: golden summer hills, oaks, eucalyptus, palms in the south, stucco ranch houses, wide freeways.
- Pacific Northwest: Douglas fir and cedar, moss, wooden houses. Alaska: spruce and birch, gravel shoulders. Hawaii: volcanic rock, tropical plants, Hawaiian names.

### States: narrowing with no readable text
1. Confirm the US over Canada and Mexico (mph, no French, US-style plates; see "Commonly confused").
2. Front plates on several local cars → the 29 two-plate states; consistently absent → the 21 rear-only states.
3. Biome and terrain → the regions above; then soil colour and signature plants.
4. A glimpsed route-marker shape is enough even when the number is unreadable.
5. Sample two to four candidate states with `refsheet.py regions US:<state>,US:<state>` and test road geometry with `osm.py find|near`.

### Rear-only plates on local cars
- Look for: several local cars seen from the front with no front plate (not one car with an empty bracket)
- Points to: AL, AK, AZ, AR, DE, FL, GA, IN, KS, KY, LA, MI, MS, NM, NC, OH, OK, PA, SC, TN, WV; front plates on most local cars point to the other 29 states and DC
- Strength: medium (state law, but compliance and out-of-state cars vary)
- Counterexamples: non-compliance in two-plate states; Ohio (2020) and Alaska (2022) dropped front plates recently, so older imagery shows them; Rhode Island's 2026 exemption; dealer, rental and border-area traffic
- Verify: read a rear plate's state name; `refsheet.py regions US:<state>,US:<state>`
- Source: https://adn.com/politics/alaska-legislature/2022/08/22/alaska-drivers-only-need-single-license-plate-with-new-law and three consumer lists cross-checked (checked 2026-10)

### Interstate shield number
- Look for: the number on the red-white-blue Interstate shield (guide signs, reassurance markers, overpass signs); exit numbers and green mile markers nearby
- Points to: one Interstate (parity rules above); in most states exit numbers equal the mileage from the state's southern or western line, so an exit or mile marker fixes the segment and direction of travel
- Strength: strong (to one road)
- Counterexamples: long Interstates cross many states; three-digit spurs and loops (I-295, I-495) reuse one number in several states; some northeastern roads still number exits sequentially (New York Thruway); the shield is small and easy to miss in a wide frame
- Verify: `osm.py find --area <state> '["highway"="motorway"]["ref"~"I 95"]'`, then match the exit or mile marker on the map
- Source: general knowledge (Interstate numbering and MUTCD exit-numbering conventions)

### State route marker shape
- Look for: the marker of a state-numbered route (not the Interstate or US Route shield) on reassurance posts, guide signs or junction assemblies
- Points to: emblems and outlines name one state (list above); a plain circle → DE, IA, KY, MS, NJ; a plain square → TX or southern New England and Maine
- Strength: strong for emblems and outlines (each is that state's own design); weak for circles and squares
- Counterexamples: guide signs near borders show the neighbouring state's routes; older designs survive for years (ND, VT); county pentagons and city route signs look different
- Verify: `refsheet.py regions US:<state>` and compare markers; web search "<state> state route marker"
- Source: https://en.wikipedia.org/wiki/Highway_shield and https://brilliantmaps.com/highway-marker-shields/ (checked 2026-10); Michigan diamond general knowledge

### Lettered county and secondary roads
- Look for: route names or markers made of letters ("Route KK", "County Road Q", "CTH JJ"), letter + digits ("E41", "R38"), or "FM 1960", "RM 12"
- Points to: bare letters on state-style markers → Missouri; bare letters on county trunk markers → Wisconsin; one letter + 2–3 digits on blue pentagons → Iowa; FM/RM → Texas
- Strength: strong (each format belongs to one state's system)
- Counterexamples: Missouri and Wisconsin both use bare letters, so check the marker style; Michigan county roads also use letter + number (unverified); Iowa letters repeat in every county
- Verify: `osm.py find --area <state> '["highway"]["ref"~"<ref>"]'` in each candidate state; `textgeo.py --text "FM 1960"`
- Source: https://en.wikipedia.org/wiki/Missouri_supplemental_route, https://en.wikipedia.org/wiki/County_Trunk_Highways_(Wisconsin), https://iowahighways.org/highways/countyrd.html (checked 2026-10)

### Saguaro and Joshua tree
- Look for: saguaro (tall columnar cactus with upturned arms); Joshua tree (branching tree yucca with spiky leaf clusters)
- Points to: saguaro → Sonoran Desert (southern Arizona, Sonora, a sliver of southeastern California); Joshua tree → Mojave Desert (southeastern California, southern Nevada, northwestern Arizona, southwestern Utah)
- Strength: strong for the region (narrow native ranges)
- Counterexamples: landscaping in desert cities and resorts; cardón (Baja California, Sonora) and other columnar cacti resemble saguaro; other tree yuccas
- Verify: `refsheet.py regions US:Arizona,US:Nevada,MX:Sonora`
- Source: general knowledge

### Coordinate street names
- Look for: street signs that are grid coordinates: "400 South", "1300 E", "S 300 W"
- Points to: Utah (almost every town); also towns of the same founding tradition in southeastern Idaho and parts of Arizona and Nevada
- Strength: strong
- Counterexamples: Indiana and parts of neighbouring states name rural roads "County Road 400 N" on a distance grid; plain numbered streets ("5th Ave") exist everywhere
- Verify: `osm.py find --area Utah '["highway"]["name"="<street name>"]'`; `textgeo.py --text "400 S 300 W"`
- Source: general knowledge

### West Virginia fractional county routes
- Look for: a small circle holding a stacked fraction ("24/1") on route or street signs; a single number in a circle is a trunk county route
- Points to: West Virginia: the top number is the parent US, WV or county route, the bottom a serial
- Strength: strong (the state's own secondary-route numbering)
- Counterexamples: numbers are unique only within a county; spurs keep their number after the parent is renumbered; Virginia secondary routes are plain numbers from 600 up
- Verify: `osm.py find --area "West Virginia" '["type"="route"]["network"~"^US:WV:"]["ref"="24/1"]'` (route relations carry the fraction)
- Source: https://en.wikipedia.org/wiki/West_Virginia_State_Highway_System, https://wiki.openstreetmap.org/wiki/Tag:network%3DUS:WV:Mercer (checked 2026-10)

### Utility warning sign above a pole-number tag (Wisconsin, Upper Peninsula)
- Look for: on wooden poles about 1.5–1.8 m up, a white sign with an orange "WARNING" header and an orange diamond ("High Voltage Above. KEEP OFF!") directly above an embossed aluminium number tag; footer "We Energies | Wisconsin Public Service"
- Points to: Wisconsin and Michigan's Upper Peninsula (the sister utility serves the former Michigan customers)
- Strength: medium (the utilities' own sign; how many poles carry it rests on a community source)
- Counterexamples: other Wisconsin utilities and co-ops may differ (unverified); generic orange-header WARNING signs exist nationwide, so read the footer
- Verify: zoom on the footer (`imgprep.py zoom`); `refsheet.py regions "US:Wisconsin,US:Michigan" --side right`
- Source: https://www.we-energies.com/olb/23/2023-02-we-cc.pdf, https://www.wisconsinpublicservice.com/joint-use-management/ju-standards/pole-info.pdf (standard P5, 2016), https://www.wisconsinpublicservice.com/services/mi-electric, https://www.plonkit.net/united-states (community) (checked 2026-10)

### Coarse chip-seal surface
- Look for: rural asphalt coated with coarse stone chips (seal coat), a grainy "salt-and-pepper" texture
- Points to: Texas (seal coat is the state's routine rural resurfacing)
- Strength: weak (chip seal is common in many states and countries)
- Counterexamples: New Mexico, Oklahoma, Colorado, rural Illinois (community source); Australia and New Zealand
- Verify: combine with FM/RM road names and Texas plates
- Source: https://www.txdot.gov/manuals/mnt/scm/general_principles/general_principles-i1000087.html, https://www.plonkit.net/united-states (community) (checked 2026-10)

### Trans-Alaska Pipeline beside the road
- Look for: one large (1.2 m) pipe on H-shaped supports, zigzagging alongside the road
- Points to: Alaska: the Prudhoe Bay–Valdez line beside the Dalton (built as its supply road, mostly unpaved), Elliott and Richardson Highways
- Strength: strong (unique; about half of the line runs above ground)
- Counterexamples: the other half is buried, including most road crossings; elevated pipelines in Russian Arctic oilfields
- Verify: `osm.py find --area Alaska '["man_made"="pipeline"]["substance"="oil"]'`, then `osm.py near` the highway
- Source: https://en.wikipedia.org/wiki/Trans-Alaska_Pipeline_System, https://en.wikipedia.org/wiki/Dalton_Highway (checked 2026-10)

### Hawaii: Hawaiian names with US road furniture
- Look for: Hawaiian street and place names with the ʻokina (ʻ) and kahakō (macron) on MUTCD signs in mph; Interstate shields numbered H-1, H-2, H-3; plates black on white with a rainbow graphic and "HAWAIʻI" at the top (2025 series; the previous design also carried a rainbow); black lava and red volcanic soil with tropical planting
- Points to: Hawaii
- Strength: strong for Hawaiian text with US signs; medium for the landscape alone
- Counterexamples: Samoan and Tahitian also write the glottal stop but use s, t or r, which Hawaiian lacks (13 letters: a e i o u h k l m n p w ʻ); Hawaiian-named businesses on the mainland; American Samoa and Guam also mix US signs with Pacific languages ([oceania.md](oceania.md))
- Verify: `textgeo.py --text "<name>"`; `refsheet.py regions "US:Hawaii,US:California" --n 6`
- Source: plates: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Hawaii (checked 2026-10); orthography and H-routes: general knowledge

## Canada (CA)

**Quick facts**
- Driving right. Plates 12×6 in; front and rear only in BC, MB and ON; rear only elsewhere. Quebec "Je me souviens"; Ontario blue on white with a crown, "Yours to Discover"; Alberta "Wild Rose Country"; BC "Beautiful British Columbia"; Saskatchewan green on white, "Land of Living Skies"; NWT polar-bear-shaped plates (since 1970); Yukon gold-prospector graphic; Nunavut rectangular since 2012. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Canada (checked 2026-10).
- Paint as in the US (yellow centre, white edge). Signs MUTCD-like but metric: km/h speeds, km distances. Trans-Canada Highway: green shield with a white maple leaf.
- Language: English and French (é è ê ç à; "rue", "chemin", "sortie"); federal signs bilingual; syllabics in Nunavut and Nunavik.
- Phone: NANP (+1); classic area codes BC 604/250, AB 403/780, SK 306, MB 204, ON 416 (Toronto), 905, 613, 519, 705, 807, QC 514 (Montréal), 450, 418, 819, NB 506, NS/PE 902, NL 709, territories 867 (plus newer overlays).
- Postal: A1A 1A1; first letter: A NL, B NS, C PE, E NB, G/H/J QC (H = Montréal), K/L/M/N/P ON (M = Toronto), R MB, S SK, T AB, V BC, X NT/NU, Y YT. TLD .ca; Quebec government sites .gouv.qc.ca.
- Saint-Pierre-et-Miquelon, south of Newfoundland, is French: French-language European-style signs, +508.

### Provinces and territories
- Quebec: French-only signs, ARRÊT; Autoroute shields blue with a red top band; long narrow "rang" farm lots along "rang" roads; steep metal roofs; outside staircases in Montréal.
- Ontario: front plates; King's Highway shield topped by a crown with "ONTARIO"; 400-series freeways; "Concession", "Sideroad" and "Line" grid roads in the south; Canadian Shield granite, lakes and spruce in the north; bilingual signs around Ottawa and in the francophone northeast.
- New Brunswick: officially bilingual, STOP/ARRÊT; Acadian flags (tricolour with a gold star) on the north and east coasts.
- Nova Scotia, Prince Edward Island, Newfoundland and Labrador: rear plates; PEI red soil and rolling farmland; Gaelic street signs in parts of Cape Breton; Newfoundland barrens and brightly painted wooden houses.
- Manitoba: front plates; highway shield with a bison; flat Red River valley.
- Saskatchewan and Alberta: rear plates; Range Road and Township Road grid names; grain elevators and canola; Alberta adds Rocky Mountain foothills, pumpjacks and a black-on-white bullet-shaped highway shield.
- British Columbia: front plates; provincial shield white with a blue number under the provincial arms (single source); coastal rainforest, mountains, Fraser Valley farmland.
- Territories: gravel highways, permafrost; Nunavut is treeless.

### French-only signs and ARRÊT
- Look for: stop signs reading ARRÊT; French-only regulatory and guide signs ("Sortie", "Rang", "Chemin", "Est/Ouest")
- Points to: Quebec; bilingual STOP/ARRÊT → New Brunswick or francophone pockets of Ontario, Manitoba, Alberta
- Strength: strong (Quebec's language law makes French the language of public signs)
- Counterexamples: English-majority Quebec municipalities still post STOP; federal bilingual signs nationwide; French territories (Antilles, Guiana, Saint-Pierre) use French with European-style signs (and French EU plates in the Antilles and Guiana)
- Verify: `refsheet.py regions "CA:Quebec,CA:New Brunswick"`; `textgeo.py --text "<sign text>"`
- Source: https://en.wikipedia.org/wiki/Stop_sign (checked 2026-10)

### Range Road and Township Road names
- Look for: road-name signs "RGE RD 245", "TWP RD 532", "Range Road 12-2"
- Points to: Alberta (most rural municipal districts) and Saskatchewan; the number encodes the survey grid (in Saskatchewan the first digit is the meridian), so it reaches a few kilometres
- Strength: strong
- Counterexamples: Manitoba sits on the same survey grid but names roads differently; urban areas rename grid roads
- Verify: `osm.py find --area Alberta '["highway"]["name"="Range Road 245"]'` (repeat with Saskatchewan)
- Source: https://en.wikipedia.org/wiki/Range_road (checked 2026-10)

### Syllabic script
- Look for: hooked and triangular syllabic glyphs (ᐃᓄᒃᑎᑐᑦ) on stop signs, schools, stores
- Points to: Nunavut and Nunavik (northern Quebec); Cree syllabics in northern Quebec, Ontario and Manitoba communities
- Strength: strong
- Counterexamples: the Cherokee syllabary (NC, OK) looks Latin-like and is a different script; Inuit communities in the NWT and Labrador mostly write in Latin script
- Verify: `textgeo.py --text "ᓄᓇᕗᑦ"`
- Source: https://en.wikipedia.org/wiki/Stop_sign (checked 2026-10); general knowledge

### Ontario speed sign with a black bottom
- Look for: a "MAXIMUM" speed sign with a black bottom section or tab reading "BEGINS" or "km/h" in white
- Points to: Ontario (Ontario Traffic Manual tabs Rb-84t BEGINS and Rb-7t KM/H are white on black)
- Strength: medium (the provincial standard; its absence elsewhere rests on a community source)
- Counterexamples: BEGINS appears only at the start of a zone; km/h is mandatory on King's Highways, optional for municipalities; British Columbia shows km/h without black (community source)
- Verify: `refsheet.py regions "CA:Ontario,CA:British Columbia"`
- Source: https://safetymedia.com/content/pdf/Ontario-Traffic-Manual-Book-5-Regulatory-Signs.pdf (Ontario Traffic Manual Book 5, 2021), https://www.plonkit.net/canada (community) (checked 2026-10)

### Curved streetlight brackets (old City of Toronto)
- Look for: long two-piece curved brackets reaching well over the roadway, classically with round "acorn" lamps
- Points to: Toronto, mainly the pre-1998 old City; most lights elsewhere are plain arms with cobra heads
- Strength: medium (a preserved heritage design; single source)
- Counterexamples: curved arms exist in many cities; some old brackets now carry other lamps
- Verify: web search "Toronto acorn streetlight bracket"; `refsheet.py towns "43.65,-79.38:Toronto;43.59,-79.64:Mississauga"`
- Source: https://spacing.ca/toronto/?p=63878 (checked 2026-10)

### Green sign backs
- Look for: road signs whose reverse side is painted green instead of bare grey
- Points to: British Columbia (also seen on Prince Edward Island)
- Strength: weak (a single community source; not every sign)
- Counterexamples: Prince Edward Island; reason and period unverified
- Verify: `refsheet.py regions "CA:British Columbia,CA:Prince Edward Island"`
- Source: https://www.plonkit.net/canada (community; no ministry document found) (checked 2026-10)

### British Columbia plates
- Look for: blue characters on reflective white with a stylised provincial flag between the two character groups, "Beautiful British Columbia" slogan; serial `AB1 23C` (2014–2025) or `A12 3BC` (since August 2025)
- Points to: British Columbia
- Strength: strong when the format and the flag are both visible
- Counterexamples: out-of-province and Washington cars around Vancouver; older serial formats; specialty and personalised plates
- Verify: `refsheet.py regions "CA:British Columbia,US:Washington"`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_British_Columbia (checked 2026-10)

### Metro Vancouver residential streets
- Look for: dark green streetlight poles with curved arms on residential streets, a grass strip between sidewalk and roadway, shallow gutters
- Points to: residential Metro Vancouver (use together with plates)
- Strength: weak (single source)
- Counterexamples: Seattle- and Portland-area suburbs look very similar; grass strips are common across North American suburbs
- Verify: `refsheet.py towns "49.25,-123.10:Vancouver;47.61,-122.33:Seattle"`
- Source: (unverified)

## Mexico (MX)

**Quick facts**
- Driving right. Plates 12×6 in, issued by states with the state name, from one national serial space (letter series map to states); private `ABC-123-D`, `ABC-123-A` in several states since 2016; Mexico City uses its own pattern; plates marked "DELANTERA/TRASERA" since 2001. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Mexico (checked 2026-10).
- Yellow centre lines, white edges. Yellow diamonds; ALTO; TOPE (speed bump); federal shield "MEX" + number; "CUOTA" (toll) vs "LIBRE"; toll roads add D (15D). Concrete poles common.
- Language: Spanish; Nahuatl place names (-tlán, -tepec, -co, tl, tz) in the centre; Maya names (X-, Dz-, -chén) in Yucatán.
- Phone: +52, 10 digits since 2019; 55 Mexico City, 33 Guadalajara, 81 Monterrey; 3-digit codes elsewhere (664 Tijuana, 999 Mérida, 998 Cancún).
- Postal: 5 digits; first two = state (01–16 Mexico City, 44–49 Jalisco, 64–67 Nuevo León). TLD .mx (.com.mx, .gob.mx).

### States and regions
- Baja California and Sonora: Sonoran Desert, saguaro (Sonora) and cardón (both), coastal plains. Chihuahua, Coahuila, Durango, Zacatecas: Chihuahuan Desert scrub, yuccas; Mennonite farms around Cuauhtémoc (Chihuahua).
- Nuevo León and Tamaulipas: thorn scrub, Sierra Madre Oriental walls near Monterrey.
- Central plateau and Bajío (Jalisco, Guanajuato, Querétaro, Aguascalientes, San Luis Potosí): high dry plains, nopal and mesquite, blue-agave fields around Tequila (Jalisco).
- Mexico City basin (CDMX, State of Mexico, Puebla, Hidalgo, Tlaxcala, Morelos): volcano backdrops, dense self-built concrete housing; pink-and-white taxis in Mexico City (weak, fleets change).
- Gulf lowlands (Veracruz, Tabasco): humid green pasture, sugarcane. Pacific coast: Sinaloa irrigated farms, palms from Nayarit to Oaxaca.
- Southern highlands (Oaxaca, Chiapas): pine-oak mountains, indigenous languages on signs.
- Yucatán Peninsula (Yucatán, Campeche, Quintana Roo): flat limestone, low dry forest, thin red soil, no rivers, Maya place names.
- State plates and state highway markers differ by state: compare with `refsheet.py regions MX:<state>,MX:<state>`.

### TOPE signs
- Look for: yellow diamond signs reading TOPE or TOPES, painted humps
- Points to: Mexico
- Strength: medium (other countries use other words: túmulo in Guatemala and El Salvador, rompemuelle in Peru, lomo de toro in Chile, resalto in Colombia, rompevelocidades in Ecuador, lomo de burro in Argentina, lombada in Brazil)
- Counterexamples: "tope" also appears in product names and commercial text elsewhere; pictogram-only bump signs say nothing
- Verify: `refsheet.py countries MX,GT --n 6`
- Source: web search of national press in GT, PE, CL, CO (checked 2026-10); Mexico general knowledge

### Mexican state plates
- Look for: 12×6 in plate with a state name at the top and `ABC-123-D` or `ABC-123-A`; when the characters are unreadable, the rear plate's background colour and graphic placement
- Points to: Mexico; the printed state (and the letter series) reaches the state of registration; the design alone narrows to a few states against a current state plate chart (one chart showed near-white plates only for Mexico City and Nuevo León)
- Strength: strong for the country; medium for the state (cars travel and some owners register elsewhere); medium for a state read from design alone (single source) (verify)
- Counterexamples: US-plated cars near the border and in tourist areas; federal public-service plates are national; states redesign plates and old and new designs coexist; overexposure whitens coloured graphics
- Verify: `textgeo.py --text "<plate text>"`; web search "<letters> placas <estado>" or a current state plate chart
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Mexico (checked 2026-10); design chart (single source)

### Tubular steel transmission poles along urban roads
- Look for: tall single grey tubular steel poles with three tiers of curved cross-arms and long insulator strings beside a road, shorter distribution poles alongside
- Points to: a high-voltage line corridor; the roads such lines follow filter road segments inside a candidate city
- Strength: weak (narrows within a city; does not identify one)
- Counterexamples: tubular transmission poles are used in many countries; different voltages look alike; OSM power data can miss lines or voltage tags
- Verify: OpenInfraMap (https://openinframap.org) or `osm.py find --area <city> '["power"="line"]'`, then sample the roads the lines follow
- Source: general knowledge (method); pole description (unverified)

## Guatemala (GT)

**Quick facts**
- Driving right. Plates 12×6 in: class letter + 3 digits + 3 letters (P = private, C = commercial), "Centro América"; black on white since 2021, blue on white 1988–2021. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Guatemala (checked 2026-10).
- Yellow centre lines (typ.). ALTO; speed bumps called túmulos.
- Language: Spanish; Mayan languages (K'iche', Kaqchikel, Q'eqchi', Mam) with q', tz', k', b'.
- Phone +502, 8 digits. Postal 5 digits (01xxx Guatemala City). TLD .gt (.com.gt, .gob.gt). Currency quetzal (Q).
- Landscape: volcanic highlands with maize plots, Petén lowland forest in the north; brightly painted ex-US school buses on intercity routes.

### Class-letter plates
- Look for: a serial that begins with a single class letter, then digits, then letters (P 123ABC)
- Points to: Guatemala
- Strength: strong (national format)
- Counterexamples: Honduran plates also start with a class letter but have a blue top band and a map background; Salvadoran plates use letter prefixes too (unverified)
- Verify: `refsheet.py countries GT,HN,SV --n 6`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Guatemala (checked 2026-10)

## Belize (BZ)

**Quick facts**
- Driving right. English is the official language (Kriol and Spanish widely spoken); English signs with right-hand traffic separate it from its neighbours. Phone +501, 7 digits. TLD .bz. Currency BZ$. Mennonite farm settlements inland.

## El Salvador (SV)

**Quick facts**
- Driving right. Plates 12×6 in; the 2011 design shows the national flag faintly behind the serial. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_El_Salvador (checked 2026-10).
- Spanish; ALTO; túmulos. Prices in US$ (dollarized 2001). Phone +503, 8 digits (landlines start with 2). TLD .sv (.gob.sv). Densely settled volcanic country, small and steep.

## Honduras (HN)

**Quick facts**
- Driving right. Plates since 2018: white with a blue top band naming the country, "Centro América" at the bottom, map of Honduras behind the serial outlined in a class colour (green private, yellow commercial, blue government); class letter first (P = private). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Honduras (checked 2026-10).
- Spanish; ALTO. Phone +504, 8 digits. TLD .hn. Currency lempira (L). Pine-covered mountains inland, banana and oil-palm lowlands on the north coast.

## Nicaragua (NI)

**Quick facts**
- Driving right. Plates 12×6 in with a map of Nicaragua behind the serial; one or two letters identify the region (department letter list unverified). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Nicaragua (checked 2026-10).
- Spanish; ALTO. Phone +505, 8 digits. TLD .ni. Currency córdoba (C$). Lakes and volcanoes on the Pacific side; sparsely roaded Caribbean side.

## Costa Rica (CR)

**Quick facts**
- Driving right. Plates black on white; private cars numeric (123456) or `ABC-123` (2013 series). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Costa_Rica (checked 2026-10).
- Spanish; ALTO. Addresses written from landmarks ("100 m norte de la iglesia"). Phone +506, 8 digits. Postal 5 digits. TLD .cr (.go.cr). Currency colón (₡).
- Official Street View since 2025 ([streetview.md](streetview.md) §3).

### Red taxis with a yellow door triangle
- Look for: red taxis with a yellow triangle on the front doors; orange taxis serving the airport
- Points to: Costa Rica
- Strength: medium
- Counterexamples: red taxis exist elsewhere in Latin America; informal taxis and ride-hailing cars are unmarked; fleet rules change
- Verify: `refsheet.py countries CR,PA,GT --n 6`; web search "taxi rojo Costa Rica triángulo"
- Source: general knowledge (unverified)

## Panama (PA)

**Quick facts**
- Driving right. Rear plate only; `AB1234` since 2013 (`123456` before); plates were reissued every year until 2022, now every four years; taxis show their plate number in large decals on the sides. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Panama (checked 2026-10).
- Spanish; ALTO. Phone +507: landlines 7 digits, mobiles 8 digits starting with 6. TLD .pa (.gob.pa). Prices in US$ and balboa (B/.).

### Rear-only plates in Central America
- Look for: several local cars with no front plate in a Spanish-speaking, right-hand-traffic Central American setting
- Points to: Panama
- Strength: medium
- Counterexamples: many Dominican cars carry one plate; Puerto Rico is rear-only too but has US-style signs; unplated cars anywhere
- Verify: `refsheet.py countries PA,CR --n 6`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Panama (checked 2026-10)

## Cuba (CU)

**Quick facts**
- Driving right. Spanish; PARE; red-rimmed triangular warning signs with a yellow fill (an older circular stop sign also exists). 1950s American cars, Soviet-era Ladas, horse carts; political billboards. Phone +53. TLD .cu. No official Street View road coverage ([streetview.md](streetview.md) §3), so expect phone photos.

### Red-rimmed triangles with yellow fill
- Look for: triangular warning signs with a red border and an amber or yellow background, in a Spanish-speaking setting
- Points to: Cuba
- Strength: medium
- Counterexamples: Argentina mixes triangles with diamonds; French territories use white-backed triangles
- Verify: web search "señales de tránsito Cuba"; `refsheet.py countries CU,DO --n 6`
- Source: https://en.wikipedia.org/wiki/Warning_sign (checked 2026-10)

## Haiti (HT)

**Quick facts**
- Driving right. French and Haitian Creole (Kreyòl: ò, è, "lekòl", "pou", "ak"); hand-painted shop signs and decorated tap-tap pickups and buses. Phone +509, 8 digits. TLD .ht. Currency gourde (G). Steep deforested hills, concrete block houses.

## Dominican Republic (DO)

**Quick facts**
- Driving right. Plates 12×6 in; a letter before the digits marks the vehicle type (e.g. L pickup, G SUV); a 1994 decree introduced a single plate and many cars still carry only a rear plate despite a later two-plate rule. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_the_Dominican_Republic and https://elnuevodiario.com.do/video-aunque-la-ley-lo-prohibe-vehiculos-circulan-sin-placa-ante-mirada-indiferente-de-las-autoridades/ (checked 2026-10).
- Spanish; PARE; yellow centre lines (typ.). Motorcycle taxis (motoconchos), corner stores (colmados).
- Phone +1 809/829/849. Postal 5 digits. TLD .do (.gob.do). Currency RD$.

## Puerto Rico (PR)

**Quick facts**
- Driving right. Rear plate only (since 1976); `ABC 123`; current series (since 2023) black on white with a fort graphic and "Isla del Encanto". Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Puerto_Rico (checked 2026-10).
- MUTCD signs in Spanish (PARE, CEDA, DESVÍO); numbered "PR-" routes; US chains. Phone +1 787/939. ZIP 006xx–009xx. TLD .pr. US$.

### Spanish MUTCD signs with mph and km
- Look for: US-design signs in Spanish; speed limits in mph while distances and kilometre posts are in km
- Points to: Puerto Rico
- Strength: strong
- Counterexamples: the Dominican Republic also says PARE but uses its own sign designs and km/h; Spanish signs on the US mainland are usually bilingual
- Verify: `refsheet.py countries PR,DO --n 6`
- Source: https://www.topuertorico.org/reference/roadway.shtml (checked 2026-10)

## US Virgin Islands (VI)

**Quick facts**
- Driving left with mostly left-hand-drive US cars; MUTCD signs in English with mph; US-style plates. Phone +1 340. ZIP 008xx. TLD .vi. US$. Steep green hills, Danish colonial towns.

### US signs with traffic on the left
- Look for: MUTCD signs (yellow diamonds, "SPEED LIMIT" in mph) and US-style plates while traffic keeps left
- Points to: US Virgin Islands
- Strength: strong
- Counterexamples: the Bahamas also drives on the left with mostly left-hand-drive cars; BVI, Turks and Caicos and Cayman drive on the left with mixed fleets (unverified); check plates and sign wording
- Verify: `clues.py lookup driving-side left`; `refsheet.py countries VI,BS,VG --n 6`
- Source: driving-side table (Wikipedia-based) and calling-code table, checked 2026-10

## Jamaica (JM)

**Quick facts**
- Driving left; mostly right-hand-drive cars, many left-hand-drive trucks. Plates: private `1234 AB` blue on white (since 1987); public passenger red with white characters; commercial green; government yellow "JAMAICA GOVT"; rental "RENTAL". Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Jamaica (checked 2026-10).
- English and Patois. Phone +1 876/658. TLD .jm. Currency J$.

## Bahamas (BS)

**Quick facts**
- Driving left with mostly left-hand-drive cars (US imports). English. Flat limestone islands with Caribbean pine on the larger northern islands. Phone +1 242. TLD .bs. Currency B$.

## Trinidad and Tobago (TT)

**Quick facts**
- Driving left. Plates: class letter + series letters + number without leading zeros (P private, H hire incl. maxi taxis, T goods, R rental); white on black or black on white at the owner's choice. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Trinidad_and_Tobago (checked 2026-10).
- English; Hindu prayer flags (jhandi), mandirs and mosques alongside churches. Phone +1 868. TLD .tt. Currency TT$.

## Barbados (BB)

**Quick facts**
- Driving left. English. Coral-limestone terraces, sugarcane, small wooden chattel houses on blocks. Phone +1 246. TLD .bb. Currency Bds$.

## Smaller English-speaking islands (AG, KN, DM, LC, VC, GD, AI, MS, VG, KY, TC)

**Quick facts**
- All drive on the left and use English; the calling code is the fastest separator: +1 268 Antigua, 869 St Kitts and Nevis, 767 Dominica, 758 St Lucia, 784 St Vincent, 473 Grenada, 264 Anguilla, 664 Montserrat, 284 BVI, 345 Cayman, 649 Turks and Caicos.
- Currency: EC$ in AG, KN, DM, LC, VC, GD, AI, MS; US$ in BVI and Turks and Caicos; CI$ in Cayman. French Creole place names in Dominica and St Lucia. Verify with `clues.py lookup calling-code +1-<area code>`.

## Bermuda (BM)

**Quick facts**
- Driving left; general speed limit 35 km/h; one car per household and small cars. Plates in the long 520×110 mm size: private cars five black digits on white; taxis T1234. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Bermuda (checked 2026-10).
- English. Postcodes two letters + two digits (e.g. HM 12). Phone +1 441. TLD .bm.

### White stepped roofs
- Look for: bright white, stepped limestone roofs on pastel houses; narrow walled roads; traffic on the left
- Points to: Bermuda
- Strength: strong (rain-catchment roofs are the local building norm)
- Counterexamples: white or light roofs exist on other hot islands, but not this stepped catchment form on pastel houses
- Verify: `refsheet.py countries BM,BS --n 6`
- Source: general knowledge

## Dutch islands (AW, CW, BQ, SX)

**Quick facts**
- Driving right. Papiamentu (Curaçao, Bonaire: "bon bini" = welcome) and Papiamento (Aruba), Dutch, English; Sint Maarten is English-speaking with Dutch official text.
- Curaçao plates: prefix letter + `12-34`, black on white (A, B, D private). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Cura%C3%A7ao (checked 2026-10).
- Arid cactus scrub and wind-bent divi-divi trees on Aruba, Curaçao and Bonaire; Dutch-gabled colourful buildings in Willemstad.
- Phone: +297 Aruba, +599 9 Curaçao, +599 7 Bonaire, +1 721 Sint Maarten. Bonaire uses US$ (since 2011); Aruba the florin.

### Kaya or Caya street names
- Look for: street-name signs beginning "Kaya" or "Caya" (= street)
- Points to: Kaya → Curaçao or Bonaire (Papiamentu spelling); Caya → Aruba (Papiamento spelling)
- Strength: medium
- Counterexamples: Dutch street names ("straat", "weg") persist on all three islands; Sint Maarten uses English and Dutch
- Verify: `textgeo.py --text "Kaya <name>"`; `osm.py find --area Aruba '["highway"]["name"~"^Caya"]'`
- Source: general knowledge (unverified)

## French Antilles (GP, MQ, MF, BL)

**Quick facts**
- Driving right; mainland French signs, white road paint, French bollards; French and Creole.
- Plates: French `AA-123-AA` with the EU band on the left and a region band showing 971 (Guadeloupe) or 972 (Martinique). Saint-Martin and Saint-Barthélemy plates not checked.
- Phone +590 (Guadeloupe, Saint-Martin, Saint-Barthélemy), +596 (Martinique); mobiles 0690/0696. Postcodes 971xx, 972xx (97150 Saint-Martin, 97133 Saint-Barthélemy). EUR.

### French plates with a 97x region band
- Look for: long white EU plate `AA-123-AA` whose right band shows 971, 972 or 973
- Points to: 971 Guadeloupe, 972 Martinique, 973 French Guiana
- Strength: strong for French overseas departments; medium for which one (owners choose the band, usually local)
- Counterexamples: cars shipped from mainland France keep two-digit department bands; 974 and 976 are Indian Ocean departments
- Verify: `clues.py lookup territories France`
- Source: general knowledge (French plate system since 2009)

## Colombia (CO)

**Quick facts**
- Driving right. Plates `ABC 123`: private black on yellow with the issuing municipality embossed at the bottom; public service black on white; official white on green; motorcycles `ABC 12D`. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Colombia (checked 2026-10).
- Yellow centre lines, white edges; PARE; speed bumps "resalto". National routes numbered (Ruta 25, Ruta 45).
- Phone +57: since 2021 landlines are 60 + region digit + 7 digits (601 Bogotá/Cundinamarca, 602 Valle/Cauca/Nariño, 604 Antioquia/Córdoba/Chocó, 605 Caribbean coast, 606 coffee region, 607 Santanderes/Arauca, 608 rest); mobiles start with 3. Source: https://bogota.gov.co/mi-ciudad/habitat/cual-es-el-nuevo-indicativo-para-marcar-bogota (checked 2026-10).
- Postal 6 digits; first two = department code (11 Bogotá, 05 Antioquia, 76 Valle, 08 Atlántico). TLD .co (.gov.co). Currency peso ($).

### Departments and regions
- Andes: Bogotá savanna (cool, eucalyptus, flower greenhouses); Antioquia (steep, brick towns); coffee region (Caldas, Risaralda, Quindío: coffee, plantains, guadua bamboo); Santanderes (dry canyons); Nariño (high páramo near Ecuador).
- Caribbean coast: flat, hot, cattle, Barranquilla and Cartagena. Pacific coast: rainforest, few roads. Llanos (Meta, Casanare): flat grassland, oil palm.

### Yellow plates with a town name
- Look for: yellow plate `ABC 123` with a municipality name embossed along the bottom
- Points to: Colombia; the town is the registration office
- Strength: strong for the country; medium for the place (owners often register in small offices near big cities)
- Counterexamples: Suriname plates are yellow too (left-hand traffic, Dutch); Ecuadorian motorcycle plates are yellow
- Verify: `textgeo.py --text "<town name>"`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Colombia (checked 2026-10)

### Calle and Carrera addresses with "#"
- Look for: addresses like "Cra. 7 # 32-16", "Calle 72 No. 10-34", abbreviations Cl, Cra, Tv, Dg
- Points to: Colombia (after "#" come the nearest cross street and the metres from that corner)
- Strength: strong
- Counterexamples: some Venezuelan Andean cities also name streets Calle and Carrera
- Verify: `textgeo.py --text "Cra 7 # 32-16"`; `osm.py find --area <city> '["highway"]["name"="Carrera 7"]'`
- Source: general knowledge

## Venezuela (VE)

**Quick facts**
- Driving right. Plates `AB123CD` since 2008; "República Bolivariana de Venezuela" in blue at the top, a faint flag behind the serial, the state at the bottom (the last letter also codes the state). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Venezuela (checked 2026-10).
- Centre lines reportedly white (unverified). PARE. Phone +58: 0212 Caracas; mobiles 0412, 0414, 0416, 0424, 0426. Postal 4 digits (1010 Caracas). TLD .ve (.gob.ve). No official Street View road coverage, only a few official panoramas ([streetview.md](streetview.md) §3).

## Guyana (GY), Suriname (SR), French Guiana (GF)

**Quick facts**
- Guyana: driving left; English; plates white on black, class letter (P private, H hire, B bus, G goods) + series letters + number (no leading zero); wooden houses on stilts, flat sugar-cane coast with sea wall; Hindu prayer flags and mosques. Phone +592, 7 digits. TLD .gy. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Guyana (checked 2026-10).
- Suriname: driving left; Dutch, Sranan Tongo, Sarnami, Javanese ("straat", "weg"); plates black on yellow, two letters (first always P) + four digits. Phone +597. TLD .sr. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Suriname (checked 2026-10).
- French Guiana: driving right; mainland French signs, white paint and bollards; French plates with the 973 band. Phone +594 (0594 fixed, 0694 mobile). Postcodes 973xx. EUR. Rainforest and red laterite verges.

### Left-hand traffic on the South American mainland
- Look for: traffic on the left in a continental, tropical setting
- Points to: Guyana (English, white-on-black plates) or Suriname (Dutch, black-on-yellow plates)
- Strength: strong
- Counterexamples: French Guiana next door drives on the right; Caribbean islands; the Falklands are cold and treeless
- Verify: `clues.py lookup driving-side left`; `refsheet.py countries GY,SR --n 6`
- Source: driving-side table and the plate pages above (checked 2026-10)

## Ecuador (EC)

**Quick facts**
- Driving right. Plates `ABC-1234` (since 2012; `ABC-123` older); first letter = province; private black on white, commercial (taxis, buses) orange or an orange top band, government gold, motorcycles black on yellow. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Ecuador (checked 2026-10).
- Yellow centre lines, white edges; PARE; speed bumps "rompevelocidades". National roads numbered E35 (Andean Pan-American), E25, E15 (coast), E45 (Amazon).
- Spanish; Kichwa place names. Phone +593: 02 Pichincha (Quito), 04 Guayas (Guayaquil), 07 south (Cuenca, Loja, Machala); mobiles 09. Postal 6 digits. TLD .ec (.gob.ec). US$ since 2000.
- Regions: Sierra (eucalyptus, cool basins, volcanoes), Costa (bananas, cacao, shrimp ponds, bamboo stilt houses), Oriente (Amazon), Galápagos.

### Province letter on Ecuadorian plates
- Look for: three letters + four digits on a white plate
- Points to: A Azuay, B Bolívar, C Carchi, E Esmeraldas, G Guayas, H Chimborazo, I Imbabura, J Santo Domingo, K Sucumbíos, L Loja, M Manabí, N Napo, O El Oro, P Pichincha, Q Orellana, R Los Ríos, S Pastaza, T Tungurahua, U Cañar, V Morona Santiago, W Galápagos, X Cotopaxi, Y Santa Elena, Z Zamora-Chinchipe
- Strength: strong for the country; medium for the province
- Counterexamples: Pichincha and Guayas cars everywhere; rental fleets
- Verify: `refsheet.py regions EC:Pichincha,EC:Guayas`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Ecuador (checked 2026-10)

### Galápagos: W plates on lava islands
- Look for: Ecuadorian plates starting with W; black lava, tree-sized Opuntia cactus and grey leafless scrub in the lowlands; few cars on short island road networks
- Points to: Galápagos (Ecuador)
- Strength: strong with a W plate; medium for the landscape alone
- Counterexamples: cars shipped from the mainland keep their province letter; other volcanic islands (Canaries, Hawaii) also show black lava with cactus, so check plates and Spanish signs
- Verify: plate letter per the entry above; `pano.py coverage -0.74,-90.31 --radius 2000`
- Source: W = Galápagos per the plate page above; landscape: general knowledge (unverified)

## Peru (PE)

**Quick facts**
- Driving right. Plates 12×6 in (since 2010): "PERÚ" at the top, flag at the upper left, `ABC-123`, `AB1-234` or `A1B-234`; first letter = region; older plates black on yellow (1995–2009). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Peru (checked 2026-10).
- Yellow centre lines, white edges; PARE; ROMPEMUELLE (also "giba"); three-wheeled mototaxis common in towns and outer Lima.
- Road codes: national PE-1N/PE-1S (Pan-American), PE-3N/PE-3S (Andean); departmental two-letter department code + 100–499 (AR Arequipa, CU Cusco, LM Lima, LI La Libertad, LA Lambayeque); local (vecinal) roads 500 and up. Source: https://wiki.openstreetmap.org/wiki/ES:Per%C3%BA/Rutas_de_carretera (checked 2026-10).
- Spanish; Quechua, and Aymara around Puno. Phone +51: Lima 01 + 7 digits; regions 2-digit (44 La Libertad, 54 Arequipa, 74 Lambayeque, 84 Cusco); mobiles 9 digits starting with 9. Postal 5 digits (Lima 15xxx). TLD .pe (.gob.pe). Currency sol (S/).
- Regions: Costa (bare desert, irrigated valleys, unfinished brick houses with rebar), Sierra (terraces, eucalyptus, adobe with tile or tin roofs), Selva (Amazon lowlands, wooden houses).

### Region letter on Peruvian plates
- Look for: the first character of a "PERÚ" plate
- Points to: A–D and F Lima; H Áncash; K/M Amazonas, Cajamarca, Lambayeque; L Loreto; P Piura, Tumbes; S San Martín; T La Libertad; U Ucayali; V Arequipa; W Huánuco, Junín, Pasco; X Apurímac, Cusco, Madre de Dios; Y Ayacucho, Huancavelica, Ica; Z Moquegua, Puno, Tacna
- Strength: strong for the country; medium for the region
- Counterexamples: Lima-registered buses, trucks and rentals everywhere; pre-2010 yellow plates follow an older scheme
- Verify: `refsheet.py regions PE:Arequipa,PE:Cuzco`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Peru (checked 2026-10)

## Bolivia (BO)

**Quick facts**
- Driving right. Plates blue on white, "BOLIVIA" at the top, `1234ABC` (since 1999) with a boxed department letter (entry below).
- Yellow centre lines (typ.); PARE. Spanish, Quechua, Aymara.
- Phone +591: 2 La Paz/Oruro/Potosí, 3 Santa Cruz/Beni/Pando, 4 Cochabamba/Chuquisaca/Tarija; mobiles 8 digits starting with 6 or 7. No postal codes in common use. TLD .bo (.gob.bo). Currency boliviano (Bs).
- Regions: Altiplano (treeless, adobe, cold), valleys (Cochabamba, Sucre, Tarija vineyards), lowlands (Santa Cruz soy, Mennonite colonies, Beni wetlands).

### Department letter on Bolivian plates
- Look for: a blue-on-white "BOLIVIA" plate `1234ABC` with a small boxed letter
- Points to: the department of registration: L La Paz, S Santa Cruz, C Cochabamba, O Oruro, P Potosí, H Chuquisaca, T Tarija, B Beni, N Pando; box white = private, red = public service, yellow = government
- Strength: strong for the country; medium for the department
- Counterexamples: La Paz and Santa Cruz cars travel nationwide; Mercosur plates not in general use (status unverified)
- Verify: `refsheet.py regions "BO:La Paz,BO:Santa Cruz"`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Bolivia (checked 2026-10)

### Wiphala beside the national flag
- Look for: the seven-colour chequered Wiphala flown next to the red-yellow-green tricolour on public buildings, schools and plazas
- Points to: Bolivia (the Wiphala is a state symbol under the 2009 constitution)
- Strength: medium
- Counterexamples: Andean indigenous movements fly it in Peru, Ecuador and northwestern Argentina; Cusco's city flag is a horizontal rainbow, not chequered
- Verify: `refsheet.py countries BO,PE --n 6`
- Source: general knowledge (Constitution of Bolivia 2009, Article 6) (unverified)

## Brazil (BR)

**Quick facts**
- Driving right; front and rear plates. Grey plates `ABC-1234` (1990–2018) with a metal band "UF - MUNICÍPIO" naming the registration city; white on red = paid transport. Mercosur since September 2018 (Rio de Janeiro first; all states by January 2020): `ABC1D23`, "BRASIL" on the blue band; character colour = category (black private, red commercial, blue official, green experimental/manufacturers, gold diplomatic); original collector cars got black plates in 2022. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Brazil and https://www.legisweb.com.br/legislacao/?id=424889 (checked 2026-10).
- Yellow centre lines, white edges; PARE; yellow diamonds; LOMBADA (speed bump).
- Portuguese: ã õ ç, -ção, nh, lh; "Rua", "Avenida", "Rodovia", "Prefeitura Municipal de <city>".
- Phone +55; 2-digit DDD codes (list below); mobiles 9 digits starting with 9. Postal CEP `00000-000`. TLD .br (.com.br; state governments as <uf>.gov.br).

### States
- DDD first digit: 1x São Paulo; 21/22/24 Rio de Janeiro, 27/28 Espírito Santo; 3x Minas Gerais; 41–46 Paraná, 47–49 Santa Catarina; 51/53/54/55 Rio Grande do Sul; 61 Federal District, 62/64 Goiás, 63 Tocantins, 65/66 Mato Grosso, 67 Mato Grosso do Sul, 68 Acre, 69 Rondônia; 71/73/74/75/77 Bahia, 79 Sergipe; 81/87 Pernambuco, 82 Alagoas, 83 Paraíba, 84 Rio Grande do Norte, 85/88 Ceará, 86/89 Piauí; 91/93/94 Pará, 92/97 Amazonas, 95 Roraima, 96 Amapá, 98/99 Maranhão.
- CEP first digit: 0 Greater São Paulo; 1 rest of SP; 2 RJ, ES; 3 MG; 4 BA, SE; 5 PE, AL, PB, RN; 6 CE, PI, MA, PA, AP, AM, RR, AC; 7 DF, GO, TO, MT, MS, RO; 8 PR, SC; 9 RS.
- Plates: grey-plate letter series were allocated by state (e.g. AAA–BEZ Paraná, BFA–GKI São Paulo, JDP–JKR Federal District, JKS–JSZ Bahia; full table by web search). Converted Mercosur plates keep the letters (only the 5th character changes, 0→A … 9→J), so the first three letters still give the state of first registration. Early Mercosur plates (2018–2019) showed a state flag and city coat of arms; these were dropped, and a bill to restore city and state names was still in Congress in 2026.
- South (RS, SC, PR): cooler; Araucaria pines on the highlands; Pampa grassland in southern RS; German and Italian town names and timber-framed houses (Blumenau, Pomerode region); red soil in northern PR.
- Southeast (SP, RJ, MG, ES): sugarcane and orange groves on red soil in interior SP; steep coastal ranges with Atlantic Forest; hilly Minas with orange-red soil and colonial towns; hillside favelas in big cities.
- Centre-West (GO, MT, MS, DF): flat soy and corn on red soil, cerrado scrub, long straight roads.
- Northeast: sugarcane and coconut palms on the coast; grey-green thorny caatinga inland; round concrete cisterns beside rural houses.
- North (PA, AM, AC, RO, RR, AP, TO): Amazon forest, river towns of wooden stilt houses, red dirt roads through cattle pasture along the deforestation arc.

### Grey plates with a city band
- Look for: grey plate with black `ABC-1234` and a top strip "SP - CAMPINAS" style
- Points to: Brazil; the strip names the state and municipality of registration
- Strength: strong, but fading: replaced from 2018–2020 and swapped on ownership transfer
- Counterexamples: cars registered elsewhere; older imagery
- Verify: `textgeo.py --text "SP - CAMPINAS"`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Brazil (checked 2026-10)

### State road prefix
- Look for: markers or kilometre posts "SP-330", "MG-050", "RS-020", "PR-445"; federal "BR-116"
- Points to: the state whose two-letter code is the prefix. Federal BR numbers: first digit 0 radial from Brasília, 1 north–south, 2 east–west, 3 diagonal, 4 link
- Strength: strong for the state
- Counterexamples: signs near state borders announce the neighbouring state's roads; Peru also writes "PE-" routes (PE-1N)
- Verify: `osm.py find --area "São Paulo" '["highway"]["ref"="SP-330"]'`
- Source: general knowledge (federal numbering standard)

### Round cisterns beside rural houses
- Look for: squat round concrete water tanks, often whitewashed, one beside each small rural house; dry thorny scrub
- Points to: semi-arid Northeast Brazil (interior BA, PE, PB, RN, CE, PI, AL, SE, northern MG)
- Strength: medium (single source)
- Counterexamples: tanks exist in other dry regions; blue plastic water tanks are nationwide
- Verify: `refsheet.py regions BR:Ceará,BR:Pernambuco,BR:Bahia`
- Source: general knowledge (federal rural cistern programme)

## Paraguay (PY)

**Quick facts**
- Driving right. Mercosur since July 2019: cars `ABCD 123`, motorcycles `123 ABCD`. Before (2000–2019): red characters, three letters + three digits, "PARAGUAY" at the top. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Paraguay (checked 2026-10).
- Yellow centre lines (typ.); PARE. National routes renamed PY01–PY22 in 2019 (PY02 Asunción–Ciudad del Este). Source: https://www.abc.com.py/nacionales/2019/09/10/conoce-las-nuevas-rutas-nacionales/ (checked 2026-10).
- Spanish and Guaraní (co-official; entry below). Phone +595: 021 Asunción, 061 Ciudad del Este, 071 Encarnación; mobiles 09xx. TLD .py (.gov.py). Currency guaraní (₲).
- Regions: east of the Paraguay River red soil, soy and Portuguese-speaking Brazilian settlers near the Brazilian border; the Chaco to the west flat thorn forest with German-speaking Mennonite towns.
- Official Street View since November 2025 ([streetview.md](streetview.md) §3).

### Guaraní orthography
- Look for: nasal vowels with a tilde (ã ẽ ĩ õ ũ ỹ), g̃ and the apostrophe-like puso inside words ("Mba'e", "tetã") on signs, murals and public notices beside Spanish
- Points to: Paraguay (Guaraní is co-official and widely written)
- Strength: medium
- Counterexamples: Corrientes (Argentina) made Guaraní co-official; Guaraní communities in the Bolivian Chaco and Mato Grosso do Sul (Brazil); Tupi-Guarani place names across Brazil are written without these letters
- Verify: `textgeo.py --text "<word>"`; `refsheet.py countries PY,AR,BO --n 6`
- Source: general knowledge (unverified)

## Uruguay (UY)

**Quick facts**
- Driving right. Mercosur plates since 2015 (mandatory 2016): `ABC 1234`, first letter = department. Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Uruguay (checked 2026-10).
- Centre lines as in Argentina (white dashes, yellow solid); PARE. Spanish with voseo. Government sites end in .gub.uy.
- Phone +598, 8 digits: 2 Montevideo, 4 interior; mobiles 09. Postal 5 digits. TLD .uy. ANCAP fuel stations. Rolling grassland, eucalyptus and pine plantations, butiá palms in Rocha; the border towns Rivera and Artigas mix with Brazil.

### First letter of Uruguayan plates
- Look for: Mercosur plate "URUGUAY" with `LLL NNNN`
- Points to: A Canelones, B Maldonado, C Rocha, D Treinta y Tres, E Cerro Largo, F Rivera, G Artigas, H Salto, I Paysandú, J Río Negro, K Soriano, L Colonia, M San José, N Flores, O Florida, P Lavalleja, Q Durazno, R Tacuarembó, S Montevideo
- Strength: strong for the country; medium for the department
- Counterexamples: Montevideo cars everywhere; rentals; Brazilian cars at the northern border
- Verify: `refsheet.py regions UY:Montevideo,UY:Maldonado`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Uruguay (checked 2026-10)

## Argentina (AR)

**Quick facts**
- Driving right. Mercosur since April 2016: `AB 123 CD`. 1995–2016: white characters on black, `ABC 123`, "ARGENTINA" in light blue on a white frame. Before 1995 the first letter named the province (rare now). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Argentina (checked 2026-10).
- Centre lines: white dashes where passing is allowed, solid yellow where not; PARE; mostly diamond warning signs with some triangles; "lomo de burro". National routes "RN" with a shield; provincial routes "RP" with each province's marker.
- Spanish with voseo ("respetá las señales"); Welsh names in Chubut (Trelew, Gaiman).
- Phone +54: 11 Buenos Aires area, 221 La Plata, 223 Mar del Plata, 261 Mendoza, 299 Neuquén, 341 Rosario, 351 Córdoba, 381 Tucumán, 387 Salta; mobiles +54 9 (locally "15"). TLD .ar (.com.ar, .gob.ar). YPF fuel stations.
- CPA postcode `A1234AAA`; the first letter is the province: A Salta, B Buenos Aires province, C City of Buenos Aires, D San Luis, E Entre Ríos, F La Rioja, G Santiago del Estero, H Chaco, J San Juan, K Catamarca, L La Pampa, M Mendoza, N Misiones, P Formosa, Q Neuquén, R Río Negro, S Santa Fe, T Tucumán, U Chubut, V Tierra del Fuego, W Corrientes, X Córdoba, Y Jujuy, Z Santa Cruz.

### Provinces and regions
- Pampas (Buenos Aires, Santa Fe, eastern Córdoba, La Pampa, Entre Ríos): dead flat, soy, wheat, cattle, eucalyptus windbreaks, white grain bags in fields.
- Northeast (Misiones, Corrientes, Chaco, Formosa): red soil, subtropical forest, yerba mate in Misiones; wetlands and palms in Corrientes; Guaraní co-official in Corrientes.
- Northwest (Jujuy, Salta, Tucumán, Catamarca, La Rioja): dry coloured valleys, cardón cacti, adobe; sugarcane in the Tucumán lowlands.
- Cuyo (Mendoza, San Juan, San Luis): irrigated vineyards with poplar rows and roadside irrigation ditches, Andes backdrop.
- Patagonia (Neuquén, Río Negro, Chubut, Santa Cruz, Tierra del Fuego): windswept steppe, poplar windbreaks around farms, lakes and forest along the Andes.

### Malvinas signs and murals
- Look for: "Las Malvinas son argentinas" signs, island outlines painted on walls, streets and monuments named for the 1982 war
- Points to: Argentina
- Strength: strong (nationwide public messaging)
- Counterexamples: the Falklands themselves are English-speaking; isolated mentions abroad
- Verify: `refsheet.py countries AR,UY,CL --n 6`
- Source: general knowledge

### White dashes with yellow solid lines
- Look for: centre markings mixing colours: white dashes where passing is allowed, solid yellow where it is not, yellow and white side by side where one direction may pass
- Points to: Argentina or Uruguay
- Strength: medium (single source)
- Counterexamples: Chile is mostly white; individual provinces and new works may paint all-yellow (unverified)
- Verify: `refsheet.py countries AR,UY,CL --n 6`
- Source: https://en.wikipedia.org/wiki/Road_surface_marking (checked 2026-10)

## Chile (CL)

**Quick facts**
- Driving right. Plates white with black characters and "CHILE" at the bottom: four letters (no vowels) + two digits since 2007, two letters + four digits 1985–2007; a front/rear indicator on the left since 2014; basic taxis dark orange, shared taxis (colectivos) yellow, electric vehicles green (since 2026, single source). Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Chile (checked 2026-10).
- Centre lines white (yellow on snowy southern and mountain roads) (verify); PARE; "lomo de toro". Spanish; Mapudungun place names in Araucanía and Los Ríos.
- Phone +56: 2 Santiago, other regions 2-digit codes (32 Valparaíso, 41 Concepción, 55 Antofagasta); mobiles 9. Postal 7 digits. TLD .cl (.gob.cl). Copec fuel stations.

### Regions
- Far north (Arica to Antofagasta): bare Atacama, mining roads, coastal cliffs. Norte Chico (Atacama, Coquimbo): semi-arid cactus scrub, irrigated valleys.
- Centre (Valparaíso, Santiago, O'Higgins, Maule): Mediterranean, vineyards, poplars, eucalyptus, adobe farmhouses with tile roofs, Andes wall to the east.
- South (Ñuble to Los Lagos): pine and eucalyptus plantations, green pasture, volcanoes, wooden houses with shingles (Chiloé).
- Far south (Aysén, Magallanes): gravel Carretera Austral, fjords, Patagonian steppe.

### Lettered regional road codes
- Look for: road numbers like "G-25", "F-30-E", "U-55" (national routes are plain numbers: 5, 68, 60-CH)
- Points to: letter = province group, north to south: A Arica-Tarapacá, B Antofagasta, C Atacama, D Coquimbo, E/F Valparaíso, G Santiago Metropolitan (and San Antonio province), H/I O'Higgins, J–M Maule, N Ñuble, O–Q Biobío, R/S Araucanía, T Los Ríos, U/V/W Los Lagos (W Chiloé), X Aysén, Y Magallanes
- Strength: strong for the region
- Counterexamples: R appears on both sides of the Biobío–Araucanía line; roads keep their code across provincial borders
- Verify: `osm.py find --area Chile '["highway"]["ref"="G-25"]'`; web search the regional road map
- Source: https://en.wikipedia.org/wiki/List_of_highways_in_Chile and road-role resolutions in Chile's official gazette (checked 2026-10)

### Chilean plates
- Look for: white plate with four consonants + two digits (or two letters + four digits), "CHILE" at the bottom, no blue band
- Points to: Chile
- Strength: strong (national format)
- Counterexamples: Argentine Mercosur plates have a blue band; older Argentine plates are black; Peruvian plates carry a "PERÚ" header
- Verify: `refsheet.py countries CL,AR,PE --n 6`
- Source: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Chile (checked 2026-10)

### Easter Island (Rapa Nui): Chilean plates on a Polynesian island
- Look for: Chilean plates and Spanish signs on a small, mostly treeless volcanic island of grassland; Rapa Nui place names (Hanga Roa, Rano Raraku, Anakena); moai on stone platforms (ahu)
- Points to: Easter Island (Chile)
- Strength: strong for moai or Rapa Nui names with Chilean plates; medium for the landscape alone
- Counterexamples: moai replicas stand elsewhere; grassy volcanic islands in the Atlantic (Azores) and Polynesian names on other Pacific islands, which lack Chilean plates
- Verify: `textgeo.py --text "<name>"`; `pano.py coverage -27.15,-109.43 --radius 2000`
- Source: general knowledge (unverified)

## Falklands (FK)

**Quick facts**
- Driving left. English with British spelling, UK-style signs. Treeless peat moorland, white gravel "camp" roads, sheep, Land Rovers; Stanley houses with bright metal roofs. Phone +500, 5 digits. Postcode FIQQ 1ZZ. TLD .fk. Currency Falkland pound.

## Commonly confused

- **US vs Canada:** paint and sign shapes match. Decide with units (mph vs km/h, miles vs km), French text, the jurisdiction name on plates, postal codes (5 digits vs A1A 1A1), "center" vs "centre", Trans-Canada maple leaf or Ontario crown shields.
- **Northern US states vs Canada:** along the land border a front plate is required from Washington to Maine except Michigan (Alaska dropped it in 2022; Ohio and Pennsylvania on Lake Erie are rear-only), while in Canada only BC, MB and ON require one. A rear-only car near the border therefore points to Michigan, Alaska, Ohio/Pennsylvania, Quebec, Alberta, Saskatchewan or Atlantic Canada. The speed-sign unit is decisive.
- **Mexico vs Guatemala:** Mexican plates print a state and read `ABC-123-D`; Guatemalan ones start with a class letter (P 123ABC). TOPE vs TÚMULO; 10-digit vs 8-digit phone numbers; $ vs Q. Maya text occurs on both sides of the border.
- **Argentina vs Uruguay:** same paint and voseo. Plates decide (`AB 123 CD` or black `ABC 123` vs `ABC 1234` with department letter); Malvinas messages, YPF and .gob.ar vs ANCAP and .gub.uy; Uruguay is gentler and greener with more eucalyptus.
- **Argentina vs Chile:** Chile's plates have no blue band and read four letters + two digits; Chilean centre lines are mostly white (verify); lettered road codes (G-25) vs RN/RP shields; lomo de toro vs lomo de burro; voseo appears in Argentine signage, not Chilean.
- **Chile vs Peru:** Chilean white centre lines (verify) vs Peruvian yellow; "PERÚ" plate header and region letters; mototaxis and painted political slogans in Peru; ROMPEMUELLE vs LOMO DE TORO; PE-1N vs letter-number codes; S/ vs $.
- **Colombia / Ecuador / Peru:** private plates yellow (CO) vs white three letters + four digits (EC) vs "PERÚ" header (PE); landline codes 60X (CO) vs 0X (EC) vs 01 or 2-digit (PE); prices $ vs US$ vs S/; route codes Ruta 25 vs E35 vs PE-1N; resalto vs rompevelocidades vs rompemuelle.
- **Brazil vs other Mercosur countries:** Portuguese text (ã, ç, -ção), "BRASIL" band and `LLL N L NN` serials, grey plates with city bands, yellow centre lines (Argentina and Uruguay mix white and yellow), state road prefixes.
- **Paraguay vs Bolivia (Chaco and Santa Cruz lowlands look alike):** plates decide (Mercosur `ABCD 123` or red-on-white "PARAGUAY" vs blue-on-white "BOLIVIA" with a department box); Guaraní vs Quechua/Aymara; ₲ vs Bs; +595 vs +591.
- **Caribbean left vs right:** left = USVI, BVI, Anguilla, Antigua, Bahamas, Barbados, Bermuda, Cayman, Dominica, Grenada, Jamaica, Montserrat, St Kitts, St Lucia, St Vincent, Trinidad, Turks and Caicos. Right = Cuba, Haiti, Dominican Republic, Puerto Rico, the Dutch and French islands. English-speaking right-hand exceptions: Sint Maarten and Belize; US-style left-hand exception: USVI.
- **Puerto Rico vs Dominican Republic:** PR has MUTCD signs in Spanish, mph speeds with km distances, US-style rear-only "PUERTO RICO" plates, US chains, +1 787/939; DR has its own sign designs, km/h, "República Dominicana" plates, RD$, motoconchos, +1 809/829/849.
- **Guyana vs Suriname:** both drive on the left with Hindu flags and wooden houses; English vs Dutch text, white-on-black vs black-on-yellow plates, +592 vs +597.
- **California vs central Chile:** same Mediterranean look; US plates, yellow centre lines and English vs Chilean plates, white lines and Spanish.
- **Brazil vs Portugal:** Brazil's yellow centre lines, yellow diamond warnings and Mercosur or grey plates vs Portugal's white lines, European triangles and EU plates.
- **Southwestern US vs northern Mexico:** same desert and paint; STOP vs ALTO, mph vs km/h, US vs Mexican state plates, TOPE signs and painted wall ads in Mexico.
- **Costa Rica vs Panama:** plates on both ends and ₡ prices in Costa Rica; rear-only `AB1234` plates, side plate decals on taxis and US$ prices in Panama.
- **Guatemala / Honduras / El Salvador / Nicaragua:** plates decide: class letter + digits + letters with "Centro América" (GT); blue top band and a map of Honduras behind the serial (HN); faint flag behind the serial (SV); a map of Nicaragua behind region letters + digits (NI). Prices Q vs L vs US$ vs C$; +502 vs +504 vs +503 vs +505.
- **Bolivia vs Peru on the Altiplano:** blue-on-white "BOLIVIA" plates with a department box vs "PERÚ" header plates with a region letter; the Wiphala beside the tricolour on Bolivian public buildings; Bs vs S/; +591 vs +51.
- **Dominican Republic vs Haiti (one island):** Spanish, PARE, type-letter plates, RD$ and +1 809/829/849 vs French and Kreyòl (ò, è), painted tap-taps, gourde and +509.
- **Uruguay vs southern Brazil (Rio Grande do Sul):** same pampa and Mercosur plates; the band reads URUGUAY with `ABC 1234` vs BRASIL with `ABC1D23`; Spanish voseo vs Portuguese (ã, ç); ANCAP and .gub.uy vs +55 DDD 51/53/54/55 and CEP 9xxxx; Uruguay mixes white dashes with yellow solid lines, Brazil uses yellow centre lines.
- **Jamaica vs Bahamas:** both drive on the left; Jamaican cars are mostly right-hand drive, Bahamian ones mostly left-hand-drive US imports; blue-on-white `1234 AB` private plates in Jamaica; J$ vs B$; +1 876/658 vs +1 242.
- **Aruba vs Curaçao vs Bonaire:** Caya (Aruba) vs Kaya (Curaçao, Bonaire) street names; US$ prices on Bonaire; +297 vs +599 9 vs +599 7.
