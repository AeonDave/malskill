# Oceania clues: Australia, New Zealand and the Pacific islands

- [Quick table](#quick-table)
- [Region-wide patterns](#region-wide-patterns)
- [Australia (AU)](#australia-au)
- [New Zealand (NZ)](#new-zealand-nz)
- [Papua New Guinea (PG)](#papua-new-guinea-pg)
- [Fiji (FJ)](#fiji-fj)
- [Samoa (WS)](#samoa-ws)
- [Tonga (TO)](#tonga-to)
- [Vanuatu (VU)](#vanuatu-vu)
- [Solomon Islands (SB)](#solomon-islands-sb)
- [New Caledonia (NC)](#new-caledonia-nc)
- [French Polynesia (PF)](#french-polynesia-pf)
- [Guam (GU)](#guam-gu)
- [Northern Mariana Islands (MP)](#northern-mariana-islands-mp)
- [American Samoa (AS)](#american-samoa-as)
- [Other Pacific islands (brief)](#other-pacific-islands-brief)
- [Commonly confused](#commonly-confused)

Scope: Australia (state level), New Zealand, Papua New Guinea, Fiji, Samoa, Tonga, Vanuatu, Solomon Islands, New Caledonia, French Polynesia, Guam, Northern Mariana Islands, American Samoa, and other Pacific islands briefly. Hawaii, Easter Island and the Galápagos are in [americas.md](americas.md); Indonesian Papua is in [asia.md](asia.md).
Facts were checked 2026-10 where a source is named. Pacific plate and paint details are thinly documented, so many cells say "unverified"; use driving side, language and codes there instead.

## Quick table

| Country (ISO2) | Drive | Plates, quick look | Road paint (centre / edge) | Script / language | Other strong tells |
|---|---|---|---|---|---|
| Australia (AU) | L | colour + state name: NSW black on yellow; VIC, WA, TAS, ACT blue on white; QLD maroon on white; SA black on white; NT ochre on white | white / white; yellow edge = no stopping | English | guide posts with red reflectors on the left; eucalypts; animal warning diamonds |
| New Zealand (NZ) | L | black on white ABC123, no region | white, solid yellow = no passing / white | English + te reo Māori | red State Highway shields; white-left / yellow-right edge-post reflectors |
| Papua New Guinea (PG) | L | (unverified) | often unpainted (unverified) | English, Tok Pisin, Hiri Motu | betel-nut stalls; highland gardens |
| Fiji (FJ) | L | black on reflective white, AB-123, FIJI insert | (unverified) | English, Fijian, Fiji Hindi | cane railway on west Viti Levu; Hindu temples |
| Samoa (WS) | L since 2009 | (unverified) | (unverified) | Samoan, English | open oval fale; many left-hand-drive cars |
| Tonga (TO) | L | (unverified) | (unverified) | Tongan, English | flat coral island; many churches |
| Vanuatu (VU) | R | (unverified) | (unverified) | Bislama, English, French | right-hand traffic inside Melanesia |
| Solomon Islands (SB) | L | (unverified) | (unverified) | English, Pijin | rainforest; stilt villages |
| New Caledonia (NC) | R | 6 digits + NC, old French layout | (unverified) | French | French signs; red laterite mining slopes |
| French Polynesia (PF) | R | 6 digits + P, old French layout | (unverified) | French + Tahitian | French signs; steep peaks and lagoons |
| Guam (GU) | R | US style, "Tano Y Chamorro" (2009+) | yellow / white (US style) | English + Chamorro (å, ñ) | US signs in mph; Japanese and Korean tourist signs |
| Northern Mariana Is. (MP) | R | US style, "HAFA ADAI", C.N.M.I.-U.S.A. | US style (unverified) | English, Chamorro, Carolinian | latte-stone route markers |
| American Samoa (AS) | R | US style, "Motu O Fiafiaga", 4 digits | US style (unverified) | Samoan + English | fale houses beside US-style roads |

## Region-wide patterns

### Driving side
- Left: AU, NZ, PG, FJ, WS (since 7 September 2009), TO, SB, KI, TV, NR, CK, NU, NF. Right: VU, the French territories (NC, PF, WF), the US territories (GU, MP, AS) and the US-associated states (PW, MH, FM).
- Mismatches: Samoa still has many left-hand-drive cars from before the switch; Palau drives on the right with many right-hand-drive imports.
- Check with `clues.py lookup driving-side right`; list dependencies with `clues.py lookup territories France` (or `United States`, `New Zealand`).

### Plates
- Australia: colour scheme and state name or slogan differ by state (strong for state of registration).
- New Zealand: one national design, no regional coding.
- French territories keep the pre-2009 French layout (6 digits + NC or P); US territories use US-size plates with the territory name and a slogan; Fiji black on white.

### Road paint, posts and sign families
- White centre lines: AU (double white = no overtaking) and NZ (with solid yellow no-passing lines); French territories French style (unverified per territory).
- Yellow centre lines: US territories (Guam; American Samoa and CNMI unverified).
- Edge posts: AU white posts with red reflectors on the left of the road and white on the right; NZ white reflectors on the left and yellow on the right.
- Sign families: AU and NZ yellow diamonds, GIVE WAY, km/h; US territories yellow diamonds, YIELD, mph, MUTCD shields; French territories red-bordered triangles and "Cédez le passage".

### Vegetation and landform (weak without a month)
- Australia: eucalypts nearly everywhere; red soil, spinifex and mulga inland; palms, pandanus and termite mounds in the tropical north; temperate rainforest and button grass in Tasmania.
- New Zealand: very green pasture with sheep and cattle, Pinus radiata plantations, native bush with tree ferns, cabbage trees and flax, snowy Southern Alps.
- High (volcanic) Pacific islands: steep green peaks, rainforest, a coastal ring road. Low islands (atolls): flat strips with only coconut and pandanus, causeways between islets.

### Street View coverage
- Official road coverage: AU, NZ, GU, MP, AS and the Pitcairn Islands; Vanuatu has one island only; none in FJ, PG, WS, SB; Tonga has contributed panoramas only. Canonical list: [streetview.md](streetview.md) §3 (as of 2026-10).
- Coverage changes yearly; `pano.py coverage <lat,lon> --radius 400` is the live check.

### Pacific orthographies (text decides fast; check with `textgeo.py --text "<string>"`)

| Language | Letters and look | Where |
|---|---|---|
| Māori | wh, ng, macrons ā ē ī ō ū; no s, l, f | New Zealand |
| Samoan | g = ng sound, s, l, f, ʻ, macrons; k and h mostly in loanwords | Samoa, American Samoa |
| Tongan | h, k, ng, ʻ | Tonga |
| Tahitian | ʻ and many vowels; no k, g, l, s | French Polynesia |
| Hawaiian | only a e i o u h k l m n p w ʻ, macrons | Hawaii ([americas.md](americas.md)) |
| Fijian | c = th, q = ngg, b = mb, d = nd, g = ng | Fiji |
| Chamorro | å, ñ, ch | Guam, Northern Mariana Islands |
| English-based creoles | Tok Pisin "bilong", "haus", "lukaut"; Bislama "blong"; Pijin similar | PNG; Vanuatu; Solomon Islands |

## Australia (AU)

Quick facts
- Drive left.
- Standard plates (characters on background): NSW black on yellow, "NEW SOUTH WALES", AB·12·CD; VIC blue on white, "VICTORIA – THE EDUCATION STATE", 1AB·2CD; QLD maroon on white, "QUEENSLAND – SUNSHINE STATE", 123·AB4 (series since September 2020; older 123·ABC); SA black on white, "SOUTH AUSTRALIA", S123·ABC; WA blue on white, "WESTERN AUSTRALIA", 1ABC·234; TAS blue on white, "Tasmania – Explore the possibilities", A 12 BC; NT ochre on white, "NT OUTBACK AUSTRALIA", CA·12·BC; ACT blue on white, "CANBERRA – THE NATION'S CAPITAL" or "THE BUSH CAPITAL", YAB·12C. Optional slimline, personalised, premium and older-slogan plates are common.
- Road paint: white centre, lane and edge lines; double white = no overtaking; continuous yellow edge line = no stopping (Australian Road Rules r169, https://classic.austlii.edu.au/au/legis/vic/consol_reg/rsrr2017208/s169.html checked 2026-10); yellow lines also in snowfields and beside tram tracks.
- Signs: yellow diamond warnings (kangaroo, wombat, koala, cattle); GIVE WAY; green guide signs; alphanumeric route markers (M, A, B, C) everywhere except Western Australia.
- Guide posts: white with red reflectors on the left side of the road and white on the right.
- Phone +61: 02 NSW and ACT; 03 VIC and TAS; 07 QLD; 08 SA, WA, NT; mobiles 04.
- Postcodes 4 digits: 08xx NT; 2xxx NSW (ACT 2600-2618 and 2900-2920); 3xxx VIC; 4xxx QLD; 5xxx SA; 6xxx WA; 7xxx TAS. TLD .au.

### State plate colours and names
- Look for: character and background colour, state name or slogan line, serial pattern
- Points to: state or territory of registration (quick facts above)
- Strength: strong for registration (each state issues its own design); medium for location (interstate travel, caravans on long highways)
- Counterexamples: optional designs (white NSW premium plates, custom colours, personalised plates); older slogans still on the road; fleet and rental cars registered in another state
- Verify: `refsheet.py regions AU:New South Wales,AU:Victoria,AU:Queensland`; several local cars agree
- Source: en.wikipedia.org/wiki/Vehicle_registration_plates_of_Australia checked 2026-10

### Stobie poles
- Look for: utility poles made of two steel I-beams with concrete between them
- Points to: South Australia (Adelaide and SA country towns)
- Strength: strong (SA's standard pole type; widely documented)
- Counterexamples: occasional examples outside SA (unverified); SA also has wooden and concrete poles, so their absence does not exclude SA
- Verify: `refsheet.py regions AU:South Australia,AU:Victoria`
- Source: general knowledge

### Alphanumeric route markers vs numbered shields
- Look for: markers such as M1, A32, B23, C512, or shields (green-gold National Highway, white National Route, blue State Route)
- Points to: alphanumeric = every state except WA (TAS since 1979, VIC and SA in the 1990s, NSW and ACT in 2013, QLD and NT partly); shields only = Western Australia; blue metropolitan shields survive in Melbourne
- Strength: medium
- Counterexamples: old signs survive after conversion; Queensland mixes both; NT converts as signs are replaced
- Verify: `osm.py near` for the road ref at the candidate point
- Source: en.wikipedia.org/wiki/Highways_in_Australia checked 2026-10

### Guide-post reflector colours
- Look for: white roadside posts; reflector colour on the left side of the road vs the right
- Points to: Australia (red left, white right) rather than New Zealand (white left, yellow right)
- Strength: medium
- Counterexamples: missing or replaced reflectors; private-road posts
- Verify: `refsheet.py countries AU,NZ --n 6`
- Source: transport.tas.gov.au guidepost specification and dit.sa.gov.au Part R81 checked 2026-10 (AS 1742.2 convention)

### Queenslander houses
- Look for: timber houses raised on stumps, wide verandas, corrugated iron roofs, lattice under the floor
- Points to: Queensland, also northern New South Wales
- Strength: medium
- Counterexamples: raised houses in the NT Top End and on floodplains elsewhere
- Verify: `refsheet.py regions AU:Queensland,AU:New South Wales`
- Source: general knowledge

### Red No Stopping signs
- Look for: a "NO STOPPING" kerbside sign with white lettering on a red panel with a thin white border
- Points to: New South Wales (sign R5-400); other states use the white R5-35 sign (red ring and slash over a black S)
- Strength: strong (a statewide sign type)
- Counterexamples: the ACT has white No Stopping signs with text (community source); NSW No Parking signs are white, so read the wording; whether older white NSW versions survive: unverified
- Verify: `refsheet.py regions "AU:New South Wales,AU:Victoria" --n 6 --side left`
- Source: https://en.wikipedia.org/wiki/Road_signs_in_Australia (R5-400 "used in New South Wales", R5-35), https://commons.wikimedia.org/wiki/File:Australia_road_sign_R5-400.svg, https://www.mynrma.com.au/open-road/advice-and-how-to/road-safety/parking-signs-explained, https://www.plonkit.net/australia (community) (checked 2026-10)

### Yellow sign posts
- Look for: regulatory, warning and guide signs mounted on bright yellow posts, round or flat
- Points to: Western Australia (Main Roads WA signs)
- Strength: strong (yellow posts mark Main Roads WA signs)
- Counterexamples: South Australian bus-stop posts are yellow (community source); WA council street-name and directional signs use other posts; replaced or faded posts
- Verify: `refsheet.py regions "AU:Western Australia,AU:South Australia" --n 6 --side left`
- Source: https://www.mundaring.wa.gov.au/plan-build/streets-verges-and-roads/road-maintenance-lighting-and-signs.aspx ("all signs with yellow posts are MRWA responsibility"), https://www.plonkit.net/australia (community) (checked 2026-10)

### Black pole-number strips
- Look for: a timber pole with a black-painted strip about 2.7 m up carrying a vertical or diagonal column of silver numerals, sometimes with a B or W prefix
- Points to: South East Queensland (Brisbane; the community source adds the Gold Coast and Sunshine Coast), not the whole state
- Strength: medium (an official specification exists for Brisbane City Council poles; the wider area rests on a community source)
- Counterexamples: Ergon poles elsewhere in Queensland carry a number about 2.4 m up, appearance unverified; NZ poles carry black number stickers (community source)
- Verify: `refsheet.py towns "-27.47,153.03:Brisbane;-28.00,153.43:Gold Coast;-19.26,146.82:Townsville" --side left --pitch 5`
- Source: https://docs.brisbane.qld.gov.au/standard-drawings/Minor-Amendment-N/11000/230602_bsd-11006_a_pol-numbering_timber-poles_details_sheet-2-o-2.pdf (BSD-11006, 2023: aluminium numerals on black paint), https://southburnett.com.au/news2/2014/01/23/ergon-reminder-to-check-poles/, https://www.plonkit.net/australia (community) (checked 2026-10)

### Regions inside Australia
- New South Wales: black on yellow plates, 02, 2xxx; M/A/B routes since 2013; sandstone around Sydney, red-brick houses with terracotta roofs; inland wheat-sheep belt; red outback in the far west.
- ACT: Canberra plates, 02, 26xx and 29xx; planned suburbs, many roundabouts, native trees in verges.
- Victoria: "Education State" plates, 03, 3xxx; many C routes; Melbourne trams and hook-turn signs in the CBD; bluestone kerbs and lanes; green rolling farmland in the south.
- Tasmania: Tasmania plates, 03, 7xxx; A/B/C routes since 1979; cool and hilly, temperate rainforest, button grass.
- Queensland: maroon plates, 07, 4xxx; Queenslander houses; sugarcane and narrow cane railways on the tropical coast; leftover Metroad hexagons in Brisbane.
- South Australia: S-plates, 08, 5xxx; Stobie poles; dry mallee and wheat, stone cottages; R (ring) routes in Adelaide.
- Western Australia: blue on white plates, 08, 6xxx; no alphanumeric routes; sandy soils and limestone around Perth; wheatbelt; red Pilbara; boab trees in the Kimberley; Noongar place names ending in -up.
- Northern Territory: ochre plates, 08, 08xx; red centre with spinifex and desert oaks; Top End tropics with termite mounds and pandanus.

## New Zealand (NZ)

Quick facts
- Drive left.
- Plates: black characters on reflective white since November 1986; ABC123 (3 letters + up to 3 digits) since April 2001, AB1234 before; silver-on-black plates (1964-1986) still valid; optional black personalised plates with white characters since 2022 (https://www.1news.co.nz/2023/11/13/readability-issues-with-some-black-number-plates/ checked 2026-10); some personalised plates blue on white; no regional coding.
- Road paint: white dashed centre lines; solid yellow line = no passing; broken yellow kerb lines = no stopping.
- Edge marker posts: white reflectors on the left side of the road, yellow on the right.
- Signs: State Highway numbers on red shields; yellow diamond warnings; GIVE WAY; more and more Māori-English bilingual signs.
- Language: English and te reo Māori; Māori place names with wh, ng and macrons.
- Phone +64: 09 Auckland, Northland; 07 Waikato, Bay of Plenty; 06 Taranaki, Manawatū-Whanganui, Hawke's Bay, Gisborne, Wairarapa; 04 Wellington; 03 the whole South Island; mobiles 02x.
- Postcodes 4 digits. TLD .nz.

### Yellow no-passing lines
- Look for: a solid yellow line beside or instead of the white dashed centre line on a two-lane road
- Points to: New Zealand
- Strength: strong (national marking standard; Australia uses double white lines)
- Counterexamples: the Americas use yellow centre lines throughout (with right-hand traffic); Australian snowfields use yellow lines for contrast; temporary roadwork paint
- Verify: `refsheet.py countries NZ,AU --n 6`
- Source: en.wikipedia.org/wiki/Road_surface_marking checked 2026-10

### Red State Highway shield
- Look for: red shield with a white number on route and direction signs
- Points to: New Zealand State Highway network
- Strength: strong (national sign standard)
- Counterexamples: none in Australia; souvenirs and themed signs
- Verify: `osm.py near` for the SH ref at the candidate point
- Source: general knowledge

### Māori place names
- Look for: wh, ng and macrons in names on official signs (Whangārei, Taupō, Kaikōura); no s, l or f
- Points to: New Zealand; densest in the North Island
- Strength: strong for country when the name is on official signage
- Counterexamples: Cook Islands Māori and Hawaiian names look similar (Hawaiian has ʻokina, no wh or ng); Māori-named businesses in Australia
- Verify: `textgeo.py --text "<name>"`; `osm.py find` the name
- Source: general knowledge

### Edge-marker-post reflectors
- Look for: white reflectors on posts at the left edge, yellow on the right edge
- Points to: New Zealand rather than Australia (red left)
- Strength: medium
- Counterexamples: missing reflectors; older posts
- Verify: `refsheet.py countries NZ,AU --n 6`
- Source: nzta.govt.nz Traffic Control Devices Manual part 5 (delineation) checked 2026-10

### Red band on edge marker posts
- Look for: a white flexible edge post with a red band across its full width near the top: the face seen on the left side of the road shows red around a white reflector, the back seen on the right shows a solid red band with a yellow reflector
- Points to: New Zealand rather than Australia, where the red reflector does not span the post
- Strength: strong (one national post design)
- Counterexamples: posts with a green stripe in southern Canterbury and a black stripe around Wellington (community source); faded or missing bands
- Verify: `refsheet.py countries NZ,AU --n 6 --side left`
- Source: https://www.drivingtests.co.nz/resources/marking-the-edge-of-the-road-with-markers-and-cats-eyes/, https://www.plonkit.net/new-zealand (community) (checked 2026-10)

### Marlborough vineyards
- Look for: a flat valley floor covered in trellised vine rows between ranges on both sides
- Points to: Marlborough: the Wairau Valley around Blenheim and the Awatere Valley near Seddon
- Strength: medium (most of New Zealand's vineyard area lies here)
- Counterexamples: Hawke's Bay, Wairarapa, Central Otago, Nelson, North Canterbury and Gisborne also have vineyards
- Verify: `osm.py find '["landuse"="vineyard"]' --bbox -41.65,173.55,-41.40,174.10`; `refsheet.py regions "NZ:Marlborough,NZ:Hawke's Bay" --rural`
- Source: https://en.wikipedia.org/wiki/Marlborough_wine_region (checked 2026-10)

### Regions inside New Zealand
- Area code 03 means the South Island; 04 Wellington; 06 lower North Island east and west; 07 Waikato and Bay of Plenty; 09 Auckland and Northland.
- Postcode first digit: 0 Northland and north Auckland; 1-2 Auckland; 3 Waikato, Bay of Plenty; 4 Gisborne, Hawke's Bay, Taranaki, Whanganui, Manawatū; 5-6 Wellington region; 7 Nelson, Marlborough, West Coast, north Canterbury; 8 Canterbury; 9 Otago, Southland.
- North Island: subtropical Northland with kauri and pōhutukawa; Auckland volcanic cones and wooden villas; Bay of Plenty kiwifruit behind tall shelter hedges; geothermal steam and pine forest around Rotorua and Taupō; dry hills and vineyards in Hawke's Bay.
- South Island: flat Canterbury Plains with pine and macrocarpa shelter belts and irrigation pivots; wet rainforest on the West Coast; dry tussock and schist in Central Otago; flat Southland pasture; Southern Alps backdrop.

## Papua New Guinea (PG)

Quick facts
- Drive left. Plates and road paint (unverified).
- Languages: English, Tok Pisin (lukaut = look out, tambu = forbidden, haus, stoa, kaikai = food, bilong), Hiri Motu around Port Moresby.
- Phone +675. TLD .pg. Currency kina.
- Landscape: highland valleys with sweet-potato gardens and casuarina; lowland rainforest; dry savanna around Port Moresby; betel-nut sellers, red-stained ground, "no buai" signs (buai = betel nut).

### Tok Pisin text
- Look for: English-like words in creole spelling (bilong, haus, stoa, tambu, lukaut)
- Points to: Papua New Guinea
- Strength: medium (Bislama and Pijin are close relatives)
- Counterexamples: Vanuatu (Bislama "blong", right-hand traffic); Solomon Islands (Pijin)
- Verify: `textgeo.py --text "<string>"`
- Source: general knowledge

## Fiji (FJ)

Quick facts
- Drive left.
- Plates: black on reflective white, two letters + 3 digits (AB-123); newer aluminium plates carry a FIJI insert; government plates white on blue.
- Languages: English; iTaukei Fijian (Bula, Vinaka, koro = village); Fiji Hindi, with Devanagari on some temple and shop signs.
- Phone +679, 7 digits. TLD .fj. Currency Fijian dollar.
- Landscape: dry western Viti Levu with sugarcane and a narrow-gauge cane railway; wet eastern side around Suva; Hindu temples, mosques and churches side by side.

### Fijian spellings next to Indo-Fijian signage
- Look for: names using c, q, b, d the Fijian way (Nadi, Beqa, Lautoka); Indian shop names and Hindu temples next to Fijian villages
- Points to: Fiji
- Strength: medium
- Counterexamples: Indo-Fijian communities in New Zealand and Australia; Fijian words in church or rugby contexts abroad
- Verify: `textgeo.py --text "<string>"`
- Source: en.wikipedia.org/wiki/Vehicle_registration_plates_of_Fiji checked 2026-10 (plates); language general knowledge

## Samoa (WS)

Quick facts
- Drive left since 7 September 2009 (right before); many older left-hand-drive vehicles remain.
- Language: Samoan (Talofa, Faʻafetai, fale = house; g pronounced ng), English. Currency tālā. Phone +685. TLD .ws.
- Landscape and culture: open-sided oval fale with thatched or metal roofs in front of homes, large colourful churches, family graves in front yards, volcanic islands (Upolu, Savaiʻi).

## Tonga (TO)

Quick facts
- Drive left. Language: Tongan (Mālō e lelei; ʻ, h, k, ng), English. Currency paʻanga. Phone +676. TLD .to.
- Landscape: flat raised-coral Tongatapu, coconut plantations, many churches, free-roaming pigs.

## Vanuatu (VU)

Quick facts
- Drive right (Anglo-French condominium legacy).
- Languages: Bislama (blong, stoa, tabu), English and French; schools and some signs follow either colonial language.
- Phone +678. TLD .vu. Currency vatu.
- Landscape: volcanic islands and rainforest; Port Vila and Luganville are the only real towns.

## Solomon Islands (SB)

Quick facts
- Drive left. Languages: English, Pijin. Phone +677. TLD .sb. Currency Solomon Islands dollar.
- Landscape: rainforest, coastal villages with leaf-thatch stilt houses; Honiara strung along a coastal highway.

## New Caledonia (NC)

Quick facts
- Drive right; French collectivity.
- Plates: 6 digits + NC in the old French layout, European size (white characters on black per one source).
- Signs and markings French; language French, plus Kanak languages.
- Phone +687, 6 digits. Postcodes 988xx. TLD .nc. Currency CFP franc (shared with French Polynesia and Wallis and Futuna).
- Landscape: long mountainous Grande Terre; nickel mines with red laterite slopes and scrub; drier west coast with cattle and paperbark (niaouli) savanna; wetter east coast.

## French Polynesia (PF)

Quick facts
- Drive right.
- Plates: 6 digits + P in the old French layout (sources differ on yellow vs white backgrounds).
- Languages: French and Tahitian (Ia ora na, Māuruuru, fare = house).
- Phone +689, 8 digits. Postcodes 987xx. TLD .pf.
- Landscape: steep green volcanic peaks with one coastal ring road (Society Islands); flat coconut-covered atolls (Tuamotu).

## Guam (GU)

Quick facts
- Drive right; US territory.
- Plates: US size; slogan "Tano Y Chamorro" since February 2009 (older designs carried "Hafa Adai" or America's-day-begins wording).
- Road paint and signs: US style, yellow centre lines, white edge lines, MUTCD signs, speeds in mph.
- Languages: English and Chamorro (Håfa Adai, Hagåtña); Japanese and Korean tourist signage in the hotel district.
- Phone +1-671. ZIP 969xx. TLD .gu.
- Landscape: limestone plateau with military bases in the north, volcanic hills in the south, tangantangan scrub.

### Chamorro text on US-style roads
- Look for: å or ñ in place names (Hagåtña), Håfa Adai, together with US signs and yellow centre lines
- Points to: Guam or the Northern Mariana Islands
- Strength: strong for the pair; separate them by plates (Tano Y Chamorro vs HAFA ADAI), ZIP (969xx vs 9695x) and phone (+1-671 vs +1-670)
- Counterexamples: Chamorro diaspora in the US mainland and Hawaii
- Verify: `textgeo.py --text "<string>"`; `clues.py lookup calling-code +1-671`
- Source: en.wikipedia.org/wiki/Vehicle_registration_plates_of_Guam and en.wikipedia.org/wiki/Vehicle_registration_plates_of_the_Northern_Mariana_Islands checked 2026-10 (plates); language general knowledge

## Northern Mariana Islands (MP)

Quick facts
- Drive right; US commonwealth.
- Plates: "HAFA ADAI" slogan, seal in the centre, C.N.M.I.-U.S.A. along the bottom (design since 1989; 2005 series surface-printed).
- Languages: English, Chamorro, Carolinian; Chinese and Korean tourist signage on Saipan.
- Phone +1-670. ZIP 96950-96952. TLD .mp.

### Latte-stone route marker
- Look for: a route number over a white outline of a latte stone (a pillar topped by a cup-shaped capstone)
- Points to: Northern Mariana Islands
- Strength: medium
- Counterexamples: latte stones are a common motif on Guam too (seals, monuments, buildings); Guam's route markers use another shape (unverified)
- Verify: `refsheet.py countries MP,GU --n 6`
- Source: https://en.wikipedia.org/wiki/Latte_stone (CNMI highway shields) checked 2026-10

## American Samoa (AS)

Quick facts
- Drive right; US territory.
- Plates: "AMERICAN SAMOA" with the slogan "Motu O Fiafiaga", 4-digit serials and a Fatu Rock image (series since 2011).
- Language: Samoan and English; Samoan fale houses but US-style signs.
- Phone +1-684. ZIP 96799. TLD .as. Currency US dollar.

### Samoan houses with right-hand traffic
- Look for: open oval fale and Samoan text with traffic on the right and US-style signs
- Points to: American Samoa (Samoa has driven on the left since 2009)
- Strength: strong when the driving side is clear
- Counterexamples: photos of Samoa taken before September 2009 (right-hand traffic then)
- Verify: `clues.py lookup driving-side left`; `refsheet.py countries WS,AS --n 6`
- Source: en.wikipedia.org/wiki/Vehicle_registration_plates_of_American_Samoa checked 2026-10 (plates); driving side general knowledge

## Other Pacific islands (brief)

- Cook Islands (CK): left, NZ dollar, Cook Islands Māori, +682; one ring road around Rarotonga.
- Niue (NU): left, NZ dollar, +683. Tokelau (TK): atolls with almost no roads, NZ dollar, +690.
- Kiribati (KI): left, Australian dollar, +686; narrow atoll strip and causeways on Tarawa.
- Tuvalu (TV): left, Australian dollar, +688; a single narrow atoll road on Funafuti.
- Nauru (NR): left, Australian dollar, +674; one ring road around a mined phosphate plateau.
- Palau (PW): right with many right-hand-drive cars, US dollar, +680, ZIP 96939-96940.
- Marshall Islands (MH): right, US dollar, +692, ZIP 96960 and 96970. Federated States of Micronesia (FM): right, US dollar, +691, ZIP 9694x.
- Wallis and Futuna (WF): French, right, CFP franc, +681, postcodes 986xx.
- Norfolk Island (NF): Australian external territory, left, +672, postcode 2899.
- Pitcairn Islands (PN): British territory, one village on a steep volcanic island, quad bikes on unpaved or concrete tracks, NZ dollar; official Street View ([streetview.md](streetview.md) §3).

## Commonly confused

### Australia / New Zealand
- Plates: Australian plates show a state colour scheme and name or slogan; New Zealand plates are plain black on white ABC123.
- Centre lines: NZ solid yellow no-passing lines; AU double white lines.
- Edge posts: AU red reflectors on the left; NZ white on the left, yellow on the right.
- Route signs: NZ red SH shields; AU alphanumeric markers (or WA and QLD shields).
- Vegetation: eucalypts dominate even in wet Australian areas; NZ has pine plantations, tree ferns, cabbage trees, flax and very green pasture.
- Codes: +61 (02/03/07/08) vs +64 (03/04/06/07/09). Both use 4-digit postcodes, so a postcode alone does not decide.
- Place names: Māori (wh, ng, macrons) vs Aboriginal-derived names (Wagga Wagga, Woolloomooloo, -up endings in WA).

### Australian states
- Plates first; then phone group (02 NSW/ACT, 03 VIC/TAS, 07 QLD, 08 SA/WA/NT) and the postcode first digit.
- Routes: WA has no alphanumeric routes; Victoria has many C routes; Adelaide has R routes.
- Infrastructure: Stobie poles = SA; trams with hook turns = Melbourne; Queenslander houses = QLD.
- Landscape: Tasmania cool and hilly; NT and WA interior red; Top End tropical; Perth sandy.

### New Zealand / UK and Ireland look-alikes
- All drive on the left with green pastures and hedges.
- UK: red-bordered warning triangles, mph, yellow rear plates, no yellow centre lines.
- Ireland: yellow diamond warnings and km/h like NZ, but plates carry a county code and an EU band, signs are bilingual Irish-English, and yellow lines mark the road edge rather than no-passing zones.
- NZ: red SH shields, white plates front and rear, Māori names, tree ferns and cabbage trees, corrugated iron roofs.

### Pacific islands among themselves
- Driving side first: right = Vanuatu, French and US territories, Palau, Marshall Islands, FSM; left = PNG, Fiji, Samoa (since 2009), Tonga, Solomon Islands, Cook Islands, Kiribati, Tuvalu, Nauru.
- Then orthography (table above) and money: US dollar (US territories, PW, MH, FM), CFP franc (NC, PF, WF), NZ dollar (CK, NU, TK), Australian dollar (KI, TV, NR), own currencies elsewhere (Fijian dollar, tālā, paʻanga, vatu, kina, Solomon dollar).
- Signs: US style (yellow diamonds, YIELD, mph) vs French (red-bordered triangles, Cédez le passage) vs Commonwealth (GIVE WAY, km/h).
- Official-coverage games: only GU, MP, AS and Pitcairn have road coverage among the islands (Vanuatu one island), so official car imagery ranks Fiji, PNG, Samoa and the Solomons down.

### Samoa / American Samoa / Tonga
- Samoa drives left (since 2009); American Samoa drives right with US signs, ZIP 96799 and +1-684.
- Tongan text uses h and k (Mālō e lelei); Samoan uses g and s and rarely k (Talofa, Faʻafetai).

### Guam / Hawaii / Northern Mariana Islands
- Text: Chamorro å and ñ (Håfa Adai, Hagåtña) vs Hawaiian ʻokina and macrons with only 13 letters (no s, t, r).
- Codes: Guam +1-671, ZIP 969xx; CNMI +1-670, ZIP 9695x; Hawaii +1-808, ZIP 967xx-968xx.
- Plates: Guam "Tano Y Chamorro"; CNMI "HAFA ADAI"; Hawaii rainbow design ("Aloha State").
- Hawaii has Interstate shields (H-1, H-2, H-3); Guam and CNMI have only territorial routes; a latte-stone route marker means CNMI.

### New Caledonia / French Polynesia / Wallis and Futuna
- Plates 6 digits + NC vs + P; postcodes 988xx vs 987xx vs 986xx; phone +687 vs +689 vs +681.
- Landscape: New Caledonia long island with red mining scars, paperbark savanna and cattle; French Polynesia steep peaks and turquoise lagoons; Wallis and Futuna small with few roads.

### New Caledonia / Vanuatu
- Both drive on the right with French around. Bislama words (blong, stoa) → Vanuatu.
- New Caledonia: plates 6 digits + NC, +687, postcodes 988xx, CFP franc, red nickel-mining scars and paperbark savanna. Vanuatu: +678, vatu, volcanic rainforest, two real towns.

### Fiji / Vanuatu / Solomon Islands / PNG
- Vanuatu drives right; the others drive left.
- Text: Fijian spellings and Fiji Hindi vs Bislama (Vanuatu, with French), Pijin (Solomons), Tok Pisin (PNG).
- Fiji has Indo-Fijian shops and temples; PNG has betel-nut stalls and highland gardens.
