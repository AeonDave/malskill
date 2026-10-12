# Google Street View and game screenshots

- [Quick table](#quick-table)
- [1. Is it Google Street View at all?](#1-is-it-google-street-view-at-all)
- [2. Camera generations and mounts](#2-camera-generations-and-mounts)
- [3. Coverage as of 2026-10](#3-coverage-as-of-2026-10)
- [4. Vehicle and mount tells by country](#4-vehicle-and-mount-tells-by-country)
- [5. Dating a Street View capture](#5-dating-a-street-view-capture)
- [6. Practical method: heading, roads, sun](#6-practical-method-heading-roads-sun)
- [7. Commonly confused](#7-commonly-confused)

Scope: read this only when the image is a Google Street View capture (a Google Maps screenshot or an embedded
panorama) or a GeoGuessr-style screenshot. It covers what the
imagery itself says (provider, camera, vehicle, coverage, capture date), not the scenery; take scenery to the
regional files. Facts are as of 2026-10. Google refreshes coverage all the time: old and new imagery coexist for
years, and every "only in X" below can expire. Entry format and rules: [index.md](index.md). These tells only rank
candidates; excluding one needs read text or a computed result (for example `gsv.py near` finding no official
panorama where the camera must have stood).

## Quick table

| Tell | Points to | Strength | § |
|---|---|---|---|
| Footer "Image capture: <Mon YYYY>" | capture month; the "© <year> Google" beside it is the year the page was shown | strong (date) | 1, 5 |
| A person or company credited; footer "Images may be subject to copyright." | contributed panorama: coverage, camera and car tells do not apply | strong (provider) | 1 |
| Whole vehicle visible, unblurred | third-party coverage (a "blue line" that is not Google's) | medium | 1 |
| Round blur over the car and another round blur in the sky, low resolution | Gen 2, roughly 2008–2011 | medium | 2 |
| Crisp detail, vivid to oversaturated colour, car blur often bluish | Gen 4, captured August 2017 or later | medium | 2 |
| Soft detail, flat colour, greyish sky, car-shaped blur | Gen 3, from about 2009 to the late 2010s | medium | 2 |
| Gen 4 quality, round blur with a small bump at the front | small cam, published from late 2024 | medium | 2 |
| Low resolution with a wide round blur over the car | low-cost camera: India first; Nigeria, Cambodia, Lebanon, Ecuador, Nepal, Vietnam; a 2025 batch in Europe | medium | 2 |
| Viewpoint clearly lower than usual, large car blur | low cam: Japan, Switzerland, Liechtenstein; Sri Lanka (Gen 4) | medium | 2 |
| Backpack, operator or nothing below; footpath | Trekker (official, off-road) | strong (not a road) | 2 |
| Black tape on the right end of the front roof-rack bar | Ghana, Gen 3 | strong when visible | 4 |
| Pickup cab and bed below the camera, police car behind | Nigeria | medium | 4 |
| Snorkel on the Google vehicle | Kenya (Gen 3 and 4), Mongolia (Gen 4) | medium | 4 |
| Roof rack and both mirrors visible, late-autumn light | Kyrgyzstan | medium (single source) | 4 |
| Many whole house fronts blurred | Germany | weak to medium | 4 |
| Scenery of a country without official coverage | rank it down in official-coverage games | medium | 3 |

## 1. Is it Google Street View at all?

### Google Maps Street View interface
- Look for: a card at top left with the place or road name, a month and year, and "See more dates"; a footer with "Image capture: <Mon YYYY>", "© <year> Google", Terms, Privacy and "Report a problem"; the compass and zoom buttons at bottom right; white arrows on the road carrying street names.
- Points to: Google Street View, with the capture month printed.
- Strength: strong (provider and capture month).
- Counterexamples: the country name next to Terms is not the panorama's country, so place it by coordinates; the © year is the year the page was served (§5); the viewer may have opened an older capture through "See more dates".
- Verify: `gsv.py near <lat,lon> --radius 50` at a candidate; its `date` and `history` must contain the printed month.
- Source: https://support.google.com/maps/answer/3093484 checked 2026-10; Google Maps page observed 2026-10; card and arrow layout: general knowledge.

### Game or embedded viewer
- Look for: a panorama with no address card and no dates; a game overlay (round counter, score, guess minimap, a compass with a red north tip); sometimes a small Google logo or terms link.
- Points to: Street View served through Google's embed. Games hide dates and street names on purpose, and map makers can pin any capture, including old ones, so do not assume the newest capture.
- Strength: medium (provider); no information on the date.
- Counterexamples: other geography games and clones may use other imagery; confirm with the camera and vehicle tells (§2, §4) before treating it as Google.
- Verify: generation and vehicle first, then `gsv.py near <lat,lon> --radius 50` at the candidates.
- Source: general knowledge.

### Panorama geometry, blurring and seams
- Look for: a perspective crop of a 360° panorama (verticals stay straight; at zero pitch the horizon sits mid-frame); faces and plates blurred by software; on request, whole houses or cars blurred; stitching seams where neighbouring sensors meet (a kerb, wire or pole that jumps, a half-ghosted vehicle), most often near the bottom. Community catalogues call distinctive seams and glitches "rifts".
- Points to: a street-level panorama service rather than an ordinary photo, which keeps faces, shows depth of field and carries camera EXIF.
- Strength: medium.
- Counterexamples: Apple Look Around and other services blur too; phone panoramas and photospheres have seams; the software misses some faces. Per-camera flare and lens-artefact patterns exist but no reliable source documents them by generation (unverified); use them only to match a screenshot to one specific capture.
- Verify: read the corners for interface text and tilt down to the vehicle (next entry).
- Source: https://geohints.com/meta/rifts checked 2026-10; face and plate blurring per the India and Cyprus launch reports (https://cyprus-mail.com/2025/11/04/google-street-view-now-covers-more-of-the-island) checked 2026-10.

### What sits at the bottom of the frame
- Look for: tilt down. A car-shaped blur (Gen 3, Gen 4); a wide round blur (Gen 2, the low-cost camera, small cam); parts of the vehicle (antenna, roof rack, snorkel, bonnet, pickup bed); a backpack, the operator or nothing (Trekker); the whole vehicle unblurred (third-party coverage).
- Points to: platform and generation (§2) and country-specific vehicles (§4).
- Strength: medium.
- Counterexamples: a screenshot cropped above the horizon hides all of it; steep roads change how high the camera seems.
- Verify: `refsheet.py countries <ISO2,ISO2> --n 6` (add `--pitch -60` to look down at the vehicles of each candidate country).
- Source: https://www.plonkit.net/beginners-guide and https://geohints.com/meta/cameraGens checked 2026-10.

### Contributed panoramas versus official coverage
- Look for: a person or company named where Google would be; footer "Images may be subject to copyright." instead of "© <year> Google"; a lone 360° scene (a blue dot on the map) or a sequence with the whole vehicle in view (a blue line); phone-style stitching; in a shared link, a panorama id starting `CIHM`, `CIAB`, `CAoS` or `AF1Q`.
- Points to: an upload by a user or company, which can be anywhere, including countries with no official coverage. Camera generations, car tells and coverage priors do not apply.
- Strength: strong (provider type).
- Counterexamples: Google's own Trekker, boat and indoor captures are official but off-road; some coverage was captured by contractors for Google (India 2022, Namibia 2025) and is treated as official.
- Verify: `gsv.py near <lat,lon> --radius 50` lists official panoramas only, so a contributed one never appears in it.
- Source: panorama metadata checked 2026-10 (contributed captures carry a personal uploader, a date to the day and lower width); https://support.google.com/maps/answer/10443241 and the Plonkit beginner guide checked 2026-10.

### Other street-level services

| Service | Coverage | Tells in a still |
|---|---|---|
| Apple Look Around | since 2019; about 36 countries and 82 areas by May 2025: parts of the US, Canada, Mexico (from Aug 2025), most of Western, Central and Northern Europe, Israel, Japan, Taiwan, Hong Kong, Singapore, Australia, New Zealand. Apple's image-collection page lists where its vehicles and backpacks survey now; a survey does not mean published imagery | Apple Maps interface and "Look Around" label; no Google footer; reviews note no capture-history view like Google's; lidar-equipped cars, backpacks in some cities |
| Yandex Panoramas | Russia, Türkiye, Kazakhstan, Uzbekistan, Armenia (selected cities, per Yandex help); Wikipedia adds Belarus and Ukraine | Yandex Maps interface, usually Russian or Turkish |
| Baidu, Tencent | mainland China | Chinese interface; see [china.md](china.md) |
| Kakao, Naver | most of South Korea, refreshed often; Kakao (formerly Daum) Roadview shows past captures by month back to about 2008 | Korean interface; Google's own Korean road imagery has no Gen 4 (GeoHints) |
| Bing Streetside | US cities, parts of Canada, the UK, France and Spain (Germany withdrawn 2012) | Bing interface; current availability unclear |
| Mapillary, KartaView | crowdsourced, worldwide | mostly flat dashcam or phone frames, often with windscreen, dashboard or bonnet (general knowledge) |
| Mapy.com panoramas | Czechia | Czech interface |

Source: https://en.wikipedia.org/wiki/List_of_street_view_services, https://en.wikipedia.org/wiki/Look_Around_(Apple), https://maps.apple.com/imagecollection/, https://yandex.com.tr/support/m-maps/en/panoramas checked 2026-10; Kakao past captures: kakaocorp.com service history (Roadview beta May 2008, past-photo view December 2009), found by web search 2026-10; current depth (unverified).

## 2. Camera generations and mounts

"Gen 1–4" are community names, not Google's. Start dates: Gen 1 = launch (May 2007); Gen 2 = Wikipedia ties the mid-2008 France launch to "second generation" cameras; Gen 3 = about 2009 (the August 2017 camera was called the "first major upgrade in eight years"); Gen 4 = the August 2017 camera. End dates are estimates. No source checked in 2026-10 uses "Gen 5"; the newest community categories are small cam and the low-cost camera.

| Type | Period (approx.) | Look | Found in (GeoHints, 2026-10) |
|---|---|---|---|
| Gen 1 | 2007 to c.2009 | very low resolution | remnants in AU, CA, FR, IT, JP, MX, MC, NZ, US; most game maps leave it out |
| Gen 2 | c.2008–2011 | low resolution; round blur over the car and another in the sky | 43 early-launch countries: much of Western and Northern Europe, US, CA, MX, BR, ZA, AU, NZ, JP, KR, TW, HK, MO, SG, IL, RU |
| Gen 3 | c.2009 to late 2010s, later in places | much sharper; flat colour, greyish sky; car-shaped blur, nothing in the sky | about 110 countries |
| Gen 4 | Aug 2017 onward | sharpest; vivid colour; car blur often bluish | about 80 countries |
| Small cam | published from late 2024 | Gen 4 quality; round blur with a small front bump (ladybug shape); mounted lower than Gen 4 | about 40, including every 2025–2026 launch in Europe and Paraguay |
| Low-cost camera ("shitcam", "bad cam") | 2020s | low resolution; wide round blur over the car | 35: India's main camera; NG, KH, EC, NP, VN, BD, LK, ST; a 2025 batch across Europe; also listed for the US |
| Low cam (mount) | any period | camera visibly lower; bigger car blur; no sky blur | all of JP, CH, LI; Gen 4 in LK; patches in AT, FR, DE, IT, LB |
| Trekker (backpack) | 2012 onward | camera on a backpack mast; operator or small blur below | trails, parks, old towns, heritage sites |

### Gen 2: two round blurs
- Look for: signs unreadable beyond a short distance; a wide round blur over the car and a matching round blur straight up.
- Points to: a capture from roughly 2008–2011 in one of about 43 early-launch countries.
- Strength: medium for "old imagery"; weak for the country.
- Counterexamples: low cam has a large car blur but nothing in the sky; the low-cost camera is equally soft with a wide car blur but is described without a sky blur.
- Verify: `gsv.py near <lat,lon> --radius 50`: a 2008–2011 date should appear in `history`.
- Source: https://www.plonkit.net/beginners-guide and https://geohints.com/meta/cameraGens checked 2026-10.

### Gen 3 versus Gen 4
- Look for: Gen 4 renders distant signs crisply and colours punchily, sometimes oversaturated; Gen 3 is softer, with flat colour and a sky that looks grey even in sun; the Gen 4 car blur often has a blue cast (single source).
- Points to: Gen 4 means a capture from August 2017 or later. Gen 3 usually means 2009–2019; the two overlapped, and metadata suggests Gen 3 was still in use in late 2017 and 2018 in places (UK, Australia).
- Strength: medium (date); weak (country).
- Counterexamples: overcast or winter Gen 4 looks dull; game compression and small screenshots hide sharpness; small cam has Gen 4 quality.
- Verify: `refsheet.py countries <ISO2,ISO2> --n 6` and compare colour and sharpness; `gsv.py near <lat,lon> --radius 50` for dates. In panorama metadata a 16384 px width flags Gen 4-class imagery; 13312 px decides nothing.
- Source: https://9to5google.com/2017/09/05/google-steet-view-cars-camera-upgrade/ ("higher resolution and punchier colors", capturing since August 2017) checked 2026-10; Plonkit beginner guide; GeoHints camera page (blue cast); panorama width: metadata checked 2026-10.

### Small cam
- Look for: Gen 4-like detail; a round car blur with a small protrusion at the front; a slightly lower vantage than Gen 4; sometimes a blur that blends into the road surface.
- Points to: a capture published late 2024 or later. The 2025–2026 launches in Europe (Bosnia and Herzegovina, Cyprus, Georgia, Kosovo), Paraguay's 2025 launch and the 2026 Balkan refresh (Albania, Montenegro, North Macedonia, Serbia) appear in GeoHints' list; Nepal and Vietnam (2025) appear under the low-cost camera instead. Parts of the car show in places: an antenna in South Africa, the front of the car in Hawaii (single source).
- Strength: medium (date); weak (country).
- Counterexamples: Gen 2 and low-cost blurs are round too but come with low resolution; low cam sits lower still.
- Verify: `gsv.py near <lat,lon> --radius 50` should list a 2024-or-later capture.
- Source: Plonkit beginner guide (shape, mount, car parts; single source); GeoHints camera page (countries) checked 2026-10. Google announced a compact roof-rack camera under 15 lb on 2022-05-24, with full rollout planned for 2023 (https://blog.google/products/maps/street-view-15-new-features/); that it is the "small cam" is likely but unconfirmed.

### Low-cost camera ("shitcam", "bad cam")
- Look for: resolution close to Gen 2 or worse, smeared detail, a wide round blur over the vehicle; some Nigerian captures from 2023–2025 are so poor that large vehicles show through the blur.
- Points to: India above all (coverage since July 2022, captured by the local partners Genesys and Tech Mahindra under licence); also Nigeria, Cambodia, Lebanon, Ecuador, Nepal, Vietnam, Bangladesh, Sri Lanka, São Tomé and Príncipe; a summer-2025 batch across much of Europe; GeoHints also lists the US.
- Strength: medium (India first; check driving side and script).
- Counterexamples: Gen 2 also blurs the sky; a screenshot downscaled by a game or messaging app looks low resolution too.
- Verify: `refsheet.py countries IN,BD,NP --n 6`.
- Source: Plonkit beginner guide and https://www.plonkit.net/nigeria checked 2026-10; GeoHints camera page; https://simonwillison.net/2025/Apr/26/geoguessr/ (a competitive player singles out India's camera); India partners: Google India blog and TechCrunch, July 2022, found by web search 2026-10.

### Low cam
- Look for: a lower viewpoint than usual (crops, walls and parked vans tower over the camera; you cannot see over garden walls), a larger car blur, no sky blur.
- Points to: Japan, Switzerland, Liechtenstein (all coverage); Sri Lanka (Gen 4); patches in Austria, France, Germany, Italy and Lebanon. Background: standard car cameras sit about 2.5 m up; in 2009 Google reshot Japan with cameras about 40 cm lower after privacy complaints; a 2012 Swiss Federal Supreme Court ruling barred views over garden walls and hedges.
- Strength: medium.
- Counterexamples: looking uphill on a steep road makes a normal camera seem low, and downhill hides a low one; pickup- or truck-mounted coverage also sits lower and is recognised by the vehicle instead; Gen 2's big blur is not low cam (Gen 2 also blurs the sky).
- Verify: `refsheet.py countries JP,CH,LI --n 6` against the screenshot.
- Source: Plonkit beginner guide; GeoHints camera page; https://gigazine.net/gsc_news/en/20090513_google_street_view_japan; https://www.theregister.com/2012/06/12/google_streetview_unfair_and_excessive_processing/; camera height: https://petapixel.com/2012/10/15/a-glimpse-of-googles-fleet-of-camera-equipped-street-view-cars (all checked 2026-10).

### Trekker, boats, trikes and indoor scenes
- Look for: no car blur; a backpack, the operator's shoulders or a small blur below; footpaths, stairs, squares, beaches, trails; water all round (boat); a snow track (snowmobile); park paths (trike); museum or shop interiors, often single tripod scenes.
- Points to: official off-road imagery (Trekker since 2012; the earlier R5 camera also rode a trike and a snowmobile). In countries with landmark-only coverage (Egypt, Pakistan, mainland China tourist sites, Mali, Tanzania) it is usually all there is.
- Strength: strong that the camera was not on a road; weak for the country.
- Counterexamples: pedestrianised city streets; contributed 360° walking sequences look similar but credit a person; Oman's first road coverage was shot with Trekkers mounted on pickup trucks, so Trekker hardware alone does not mean off-road.
- Verify: `gsv.py near <lat,lon> --radius 50` returns Trekker panoramas, which are official.
- Source: https://www.trekview.org/blog/history-of-google-street-view-cameras/ checked 2026-10; Oman: https://blog.google/intl/en-mena/product-updates/explore-get-answers/google-street-view-is-coming-to-oman/ checked 2026-10; GeoHints lists Trekker imagery in every generation (Gen 4 Trekker in 54 countries); tripod and partner indoor captures per the Wikipedia coverage timeline, checked 2026-10.

### Generation as a country filter
- Look for: a confident generation call (above).
- Points to: per GeoHints (2026-10), no Gen 3 road imagery in Bosnia and Herzegovina, Costa Rica, Georgia, Kosovo, Liechtenstein, Namibia, Oman, Panama, Qatar, Rwanda (Rwanda was the first Gen 4-only country, 2022). No standard Gen 4 in Andorra, Belarus, Bhutan, Botswana, Cambodia, Curaçao, Dominican Republic, Eswatini, Guatemala, Jordan, Kyrgyzstan, Laos, Lesotho, Madagascar, South Korea, Tunisia, Uganda, Ukraine. Example (derived): Gen 4 in an East African scene favours Kenya or Rwanda over Uganda, and Tanzania has no road coverage.
- Strength: weak (ranking only).
- Counterexamples: the lists lag refreshes; small-cam or low-cost captures can arrive where standard Gen 4 never did (Albania, Montenegro and North Macedonia in 2026).
- Verify: `refsheet.py countries <ISO2,ISO2> --n 6` shows current imagery and capture dates per country.
- Source: https://geohints.com/meta/cameraGens checked 2026-10 (single source); Rwanda: https://en.wikipedia.org/wiki/Coverage_of_Google_Street_View checked 2026-10.

## 3. Coverage as of 2026-10

Coverage changes yearly. `pano.py coverage <lat,lon> --radius 400` is the live check (who has imagery at a point, with dates); `gsv.py near` checks Google official panoramas only.

| Region | Official road coverage | Limited (landmarks, one city, Trekker) | No official road coverage (not exhaustive) |
|---|---|---|---|
| Europe and Caucasus | every EU state (Cyprus last, Nov 2025); UK, Iceland, Norway, Switzerland, Liechtenstein (2024), Andorra, Monaco, San Marino, Gibraltar, Isle of Man, Jersey, Faroe Islands, Svalbard, Åland, Akrotiri and Dhekelia; Albania, Bosnia and Herzegovina (Nov 2025), Kosovo (Jul 2026), Montenegro, North Macedonia, Serbia; Ukraine, Russia, Turkey, Georgia (Jun 2026) | Belarus (central Minsk) | Moldova, Azerbaijan; Armenia (unofficial only) |
| Asia | Japan, South Korea, Taiwan, Hong Kong, Macau, Mongolia, Kazakhstan, Kyrgyzstan; Philippines, Indonesia (gaps in Aceh and Papua), Malaysia, Singapore, Thailand, Cambodia, Laos, Vietnam (2025, see note); India (2022), Bangladesh, Sri Lanka, Nepal (Aug 2025), Bhutan; Israel, Palestine (West Bank), Jordan, Lebanon, UAE, Qatar, Oman (Dec 2024); Christmas Island, Cocos (Keeling) Islands | mainland China (a few tourist sites), Pakistan (landmarks), Afghanistan (a few Kabul buildings), Iraq (one museum) | Myanmar, North Korea, Iran, Saudi Arabia, Kuwait (listed as future), Bahrain, Yemen, Syria, Uzbekistan, Tajikistan, Turkmenistan, Brunei; Timor-Leste and Maldives (underwater only) |
| Africa | South Africa, Botswana, Eswatini, Lesotho, Namibia (Jun 2025), Kenya, Uganda, Rwanda, Nigeria, Ghana, Senegal, Tunisia, São Tomé and Príncipe (2024), Réunion | Egypt (landmarks), Madagascar (some towns), Mali (heritage sites), Tanzania (landmarks) | Morocco, Algeria, Libya, Sudan, Ethiopia, DR Congo, Angola, Mozambique, Zambia, Malawi, Cameroon, Côte d'Ivoire; Zimbabwe (unofficial only) |
| Americas | USA, Puerto Rico, US Virgin Islands, Canada, Bermuda, Greenland, Mexico, Guatemala, Costa Rica (2025), Panama (2023), Dominican Republic (mainly around its two largest cities), Curaçao; Colombia, Ecuador, Peru, Bolivia, Chile, Argentina, Uruguay, Brazil, Paraguay (Nov 2025) | Falkland Islands (three islands) | Venezuela, Cuba, Haiti, Honduras, Nicaragua, Guyana, Suriname; Belize (underwater only); El Salvador, Bahamas, Barbados, Turks and Caicos, Martinique (unofficial only) |
| Oceania | Australia, New Zealand, Guam, Northern Mariana Islands, American Samoa, Pitcairn Islands | Vanuatu (one island) | Fiji, Papua New Guinea, Samoa, Solomon Islands; Tonga (unofficial only) |
| Antarctica | none | a few sites | — |

Source: https://en.wikipedia.org/wiki/Coverage_of_Google_Street_View read 2026-10, with launches confirmed in the
news: Liechtenstein (Wikipedia, Oct 2024); Oman phase one (Google MENA blog, 2024-12-12: about 36,000 km);
Namibia (4 June 2025, more than 21,000 km, captured by the local contractor LEFA:
https://thebrief.com.na/2025/06/21000km-of-namibia-now-visible-on-google-street-view/); Nepal (Google blog,
2025-08-15); Cyprus, its first official coverage (Cyprus Mail, 2025-11-04); Bosnia and Herzegovina (Google blog and
FENA, Nov 2025); Paraguay (La Nación, 2025-11-24); Georgia (2026-06-22, about 13,000 km, with the Ministry of Economy
and Sustainable Development and GITA: https://info.imedi.ge/en/society/10049/google-officially-launches-street-view-in-georgia);
Kosovo (2026-07-31, captured July 2025 to May 2026:
https://blog.google/products-and-platforms/products/maps/google-street-view-kosovo/,
https://www.koha.net/en/tech/google-lanson-street-view-ne-kosove). Kuwait: no launch found by 2026-10 (unverified).
All checked 2026-10. Vietnam: Wikipedia lists
road coverage from June 2025, and Vietnamese press confirms only that Google cars were scheduled there through
2025; older Vietnamese imagery was largely contributed (single source for the launch). Germany had road
imagery for only about 20 large cities (older captures, published 2010) until the July 2023 nationwide release.
GeoHints also records a few official panoramas in otherwise uncovered countries (Gambia, Nicaragua, Guyana,
Venezuela, Syria).

### Using coverage as a prior
- Look for: official imagery (Google UI, a Google car blur, Trekker) in a game map that uses official coverage.
- Points to: a covered country. Rank uncovered look-alikes down, for example Morocco toward Tunisia; Ethiopia or Tanzania toward Kenya, Uganda or Rwanda; Venezuela toward Colombia; Myanmar toward Thailand, Laos or Cambodia; Saudi Arabia toward the UAE, Qatar, Oman or Jordan; Iran toward Turkey; Pakistan toward India; Moldova toward Romania or Ukraine; Zambia, Zimbabwe or Mozambique toward Botswana, Namibia, Eswatini or South Africa; Honduras or Nicaragua toward Guatemala, Costa Rica or Panama (derived from the table).
- Strength: medium for official-only game maps; weak for a Google Maps screenshot (it may be contributed); nothing for an ordinary photo.
- Counterexamples: maps built on unofficial coverage; the fragments above; landmark-only sites; notes written before the 2025–2026 launches (Bosnia and Herzegovina, Cyprus, Paraguay, Nepal, Georgia, Kosovo) are stale.
- Verify: `gsv.py near <lat,lon> --radius 50` at the candidate; `refsheet.py countries <ISO2,ISO2> --n 6` (rows with empty cells mean no coverage near the sampled towns).
- Source: coverage sources above; Plonkit beginner guide on unofficial coverage, checked 2026-10.

## 4. Vehicle and mount tells by country

Visible parts of the Google vehicle are the most fragile tells: a refresh replaces the car and the old imagery
together. Check the capture date before leaning on any of these.

### Ghana: taped roof rack (Gen 3)
- Look for: looking down, a roof rack whose front bar has black tape at its right end; the bonnet with a Street View wrap (a red rectangle) is often visible. Plonkit describes three tape variants by region (intact in the south-west, peeling in the east and north, two white spots north of Kumasi and west of Tamale). Gen 4 instead: a grey or white pickup with an antenna at the front, mostly blurred.
- Points to: Ghana.
- Strength: strong when the taped bar is clearly visible.
- Counterexamples: national-park roads were covered with other cars; Gen 4 pickup imagery has replaced the taped car around Accra and Kumasi (Wikipedia says most of it by 2026), so a missing tape proves nothing.
- Verify: `refsheet.py countries GH,NG,KE --n 6` (add `--pitch -60`); `gsv.py near <lat,lon> --radius 50` for the capture date.
- Source: https://www.plonkit.net/ghana checked 2026-10; https://en.wikipedia.org/wiki/GeoGuessr (cites The Verge, 2021) checked 2026-10; player tip lists found by web search 2026-10.

### Nigeria: visible pickup and a police escort
- Look for: the cab and bed of a pickup below the camera (with a roof rack in Gen 3), or one large blur over the whole pickup; a white or black police car following in many panoramas; much of the country in the low-cost camera.
- Points to: Nigeria.
- Strength: medium; strong together with the short green-tinted plates or state names.
- Counterexamples: follow cars occur elsewhere (see "Follow cars in general"); Ghana's Gen 4 also uses pickups; the poorest low-cost imagery also exists in Lebanon.
- Verify: `refsheet.py countries NG,GH --n 6 --pitch -60`.
- Source: https://www.plonkit.net/nigeria checked 2026-10; https://geohints.com/meta/followCars checked 2026-10 (Nigeria has the most catalogued follow cars).

### Kenya and Mongolia: snorkels
- Look for: a snorkel (raised air intake by the windscreen pillar) on the Google vehicle. Kenya Gen 3: roof rack plus snorkel; Kenya Gen 4: a pickup of varying colour, partly visible, sometimes with a snorkel; a grey Toyota SUV following on much of the coverage; national-park cars in grey or white, some with rubber bands on the rack.
- Points to: Kenya. In Gen 4 the only other snorkel country is Mongolia (single source).
- Strength: medium.
- Counterexamples: some Kenyan Gen 3 shows no car at all; a snorkelled 4x4 in traffic is not the Google car.
- Verify: `refsheet.py countries KE,UG,MN --n 6 --pitch -60`.
- Source: https://www.plonkit.net/kenya and Plonkit beginner guide checked 2026-10; GeoHints follow-car catalogue (Kenya examples).

### Kyrgyzstan: roof rack and mirrors
- Look for: a roof rack and both rear-view mirrors visible; autumn to early-winter light and vegetation (captured October to December).
- Points to: Kyrgyzstan (all its coverage, per the source).
- Strength: medium (single source).
- Counterexamples: other roof-rack cars (Ghana, Kenya and Nigeria Gen 3); Kazakh and Mongolian steppe looks alike.
- Verify: `refsheet.py countries KG,KZ,MN --n 6 --pitch -60`.
- Source: Plonkit beginner guide checked 2026-10 (car); capture months from Plonkit text quoted on a forum, 2026-03 (single source).

### Russia and South America: car colour
- Look for: Russia: a black car with a long antenna. South America, Gen 3: a black car with its rear visible (all of Argentina's Gen 3; also in Uruguay and Peru); white cars in Bolivia, Chile and Peru, with other white cars in Gen 4.
- Points to: the countries named.
- Strength: weak (single source; car colour alone is common).
- Counterexamples: "the white car" means one specific car in community talk, not any white car; refreshes replace these cars.
- Verify: `refsheet.py countries AR,UY,PE --n 6 --pitch -60`.
- Source: Plonkit beginner guide checked 2026-10 (single source).

### Follow cars in general
- Look for: the same vehicle at a near-constant distance behind or ahead across consecutive panoramas, often police or an SUV.
- Points to: most catalogued in Nigeria, then the United States (over a huge network), Tunisia and Kenya; a few each in Palestine, Costa Rica, Ireland, Israel, Jordan and others.
- Strength: weak alone; medium with the Nigerian police car.
- Counterexamples: ordinary traffic behind the car on one panorama; convoys on mountain roads.
- Verify: step back and forth through the panoramas, or compare `gsv.py sheet --at <lat,lon> --headings 0,90,180,270` at neighbouring points.
- Source: https://geohints.com/meta/followCars checked 2026-10 (single source; catalogue order, not frequency).

### Many blurred houses: Germany
- Look for: whole house fronts or buildings blurred, not just faces and plates, repeatedly along one street.
- Points to: Germany, where mass blurring requests preceded the 2010 city launch and returned after the 2023 nationwide imagery.
- Strength: weak to medium (one blurred house means nothing; many point to Germany).
- Counterexamples: anyone, anywhere can request a house blur.
- Verify: `refsheet.py countries DE,AT,PL --n 6`; a German rural road almost always means a 2022-or-later capture.
- Source: https://searchengineland.com/google-street-view-germany-blurry-houses-included-54632; https://www.theregister.com/2010/11/19/street_view_germany/; https://www.googlewatchblog.de/2024/03/google-maps-streetview-verpixelungen/ (all checked 2026-10).

## 5. Dating a Street View capture

### "Image capture" versus "© <year> Google"
- Look for: both strings in a Google Maps footer.
- Points to: "Image capture: <Mon YYYY>" is the capture month. "© <year> Google" is the year the page was served, not the capture year: it dates the screenshot and caps the capture year. Google Maps usually opens the newest capture, so the likeliest one is the newest capture dated in or before that year.
- Strength: strong ("Image capture"); weak (© year: an upper bound only).
- Counterexamples: the viewer may have opened an older capture via "See more dates"; captures published after the screenshot appear in today's history; older interfaces may have used another copyright year (unverified).
- Verify: `gsv.py near <lat,lon> --radius 50` → `date`, `history`, `dates_seen` and `copyright`; render one capture with `gsv.py sheet --at <lat,lon> --headings 0,90,180,270 --date YYYY-MM`.
- Source: panorama metadata checked 2026-10; https://support.google.com/maps/answer/3093484 checked 2026-10.

### Camera and vehicle as date bounds
- Look for: the generation (§2) and any dated vehicle (§4).
- Points to: Gen 4 → August 2017 or later; small cam → published late 2024 or later; Gen 2 → about 2008–2011; low-cost camera → 2020s; India road imagery → July 2022 or later; German rural roads → almost always 2022 or later.
- Strength: medium (bounds, not dates).
- Counterexamples: generation calls fail on dull or compressed screenshots; some bounds are publication dates, and capture can precede publication by months.
- Verify: `gsv.py near <lat,lon> --radius 50`: the matching capture must fall inside the bound.
- Source: §2 and §4 sources.

### Picking the capture by season, weather and sun
- Look for: leaf state, snow, crop stage, wet roads, cloud pattern, shadow length and direction.
- Points to: which capture in `history` the screenshot shows; a mismatch with every capture means another place. Coverage seasons help: Kyrgyzstan was captured October to December, Andorra mostly in autumn, Turkish Gen 4 snow is limited to a few areas such as around Erzurum, and Finnish Gen 3 snow only to the far north-west of Lapland (single source).
- Strength: medium.
- Counterexamples: phenology shifts with altitude and year; neighbouring panoramas of one drive can differ in cloud; the month is the capture month, not the publication month.
- Verify: `gsv.py sheet --at <lat,lon> --headings 0,90,180,270 --date YYYY-MM` for each listed capture; compare clouds and shadows.
- Source: general knowledge; coverage seasons from Plonkit text quoted on a forum, 2026-03 (single source).

## 6. Practical method: heading, roads, sun

### Heading from a compass or a URL
- Look for: Google Maps' compass at bottom right (it turns the view north when clicked); a game compass whose red tip marks north; a Google Maps URL of the form `@lat,lon,3a,<fov>y,<heading>h,<tilt>t`, which gives the camera position, the heading in degrees and the tilt (90 = level).
- Points to: the bearing of the view, then the bearing of the road, then roads with that orientation.
- Strength: strong when the compass or URL is legible.
- Counterexamples: a mirrored repost flips everything; a cropped or rotated minimap; zoom narrows the field of view, so do not read angles off the frame edges.
- Verify: `gsv.py sheet --at <lat,lon> --headings 0,90,180,270` at a candidate and match the view at the read heading.
- Source: https://support.google.com/maps/answer/3093484 checked 2026-10 (compass); URL form: general knowledge.

### Heading from road direction and the sun
- Look for: shadows of poles and of the Google car on the road; which side of the road the sun is on.
- Points to: outside the tropics the midday sun is due south (north) in the northern (southern) hemisphere; between the tropics it can be on either side. With the capture month from `history`, the sun's azimuth converts the shadow direction into a heading ([sky.md](../sky.md)).
- Strength: medium.
- Counterexamples: near noon in the tropics; overcast skies; morning and evening azimuths swing far east or west; HDR flare is not the sun.
- Verify: compute the sun azimuth for the candidate and capture month, then render that heading with `gsv.py sheet --at <lat,lon> --headings 0,90,180,270`.
- Source: general knowledge (solar geometry).

### Official coverage follows roads
- Look for: official car imagery (a car-shaped or round car blur).
- Points to: the camera stood on a road with coverage (Trekker: a path; boat: water). Snap candidates to roads; a run of linked panoramas lets you walk the line.
- Strength: strong (a constraint).
- Counterexamples: Trekker, boats and indoor scenes; contributed panoramas can be anywhere; coverage is replaced or withdrawn, and `gsv.py near` sees only current official panoramas.
- Verify: `gsv.py near <lat,lon> --radius 50`; no official panorama within about 50 m of a candidate is a computed result that rules it out for official car imagery.
- Source: general knowledge; `gsv.py` behaviour.

## 7. Commonly confused

- **Gen 3 vs Gen 4**: judge sharpness of distant text and colour together, not colour alone; overcast Gen 4 looks dull and bright Gen 3 can look fine. A bluish car blur (single source) and a 2017-or-later capture in `history` support Gen 4.
- **Gen 2 vs low cam**: Gen 2 also blurs the sky; low cam shows a genuinely low vantage. Check uphill and downhill before calling low cam.
- **Small cam vs Gen 2 or the low-cost camera**: all have round blurs, but small cam has Gen 4 resolution; the front bump is specific to small cam.
- **Low-cost camera vs a downscaled screenshot**: look at blur shape and colour noise, not only at softness; a sharp interface overlay on soft imagery points to the camera.
- **Trekker vs contributed walking sequence**: a credited person or company means contributed; Google's Trekker shows Google in the footer.
- **Official vs contributed panorama**: footer text, credited name and the vehicle (unblurred in third-party coverage) decide it (§1).
- **Google vs Apple Look Around**: the interface decides it; Look Around exists only in Apple's countries (§1) and offers no Google footer.
- **Google vs Yandex** in Russia, Türkiye, Kazakhstan: interface and attribution decide it. Google has only central Minsk in Belarus and nothing official in Uzbekistan or Armenia, so car panoramas from elsewhere there are Yandex (or contributed).
- **Google vs Kakao or Naver** in South Korea: Korean interface means a domestic service; Google's Korean road imagery is older.
- **Google vs Baidu or Tencent**: Hong Kong, Macau and Taiwan are Google; mainland China street imagery is Baidu or Tencent ([china.md](china.md)).
- **Follow car vs traffic**: a follow car keeps its distance across several panoramas.
- **Google vehicle vs local 4x4**: the Google vehicle sits in the nadir, attached to the camera position; a snorkelled vehicle elsewhere in the frame is just traffic.
