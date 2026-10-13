# Mainland China clues

- [Platform and metadata (all of it is a hypothesis to verify)](#platform-and-metadata-all-of-it-is-a-hypothesis-to-verify)
- [Text and plates](#text-and-plates)
- [Vehicles and traffic](#vehicles-and-traffic)
- [Infrastructure](#infrastructure)
- [Climate and phenology (must be paired with the month)](#climate-and-phenology-must-be-paired-with-the-month)
- [Terrain and water](#terrain-and-water)
- [Urban form](#urban-form)
- [Discriminating tests inside a city](#discriminating-tests-inside-a-city)
- [Street-level fingerprints between similar cities (procedure)](#street-level-fingerprints-between-similar-cities-procedure)
- [Searching and maps in China](#searching-and-maps-in-china)

Ordered by the layers in [observe.md](../observe.md): platform metadata → text and plates → vehicles and
traffic → infrastructure → climate and phenology → terrain and water → urban form. Entry format and rules:
[index.md](index.md). Lookups: `clues.py lookup plate|plate-prefix|area-code|admin`.

## Platform and metadata (all of it is a hypothesis to verify)

### IP location label on posts and comments
- Look for: the province shown next to posts and comments on Douyin, Xiaohongshu and Weibo (a country for users abroad), together with the posting date.
- Points to: the province the poster was in when posting, not where the photo was taken.
- Strength: weak; medium when the story is "shot today, posted today" and the watermark time matches the posting time.
- Counterexamples: posting while travelling, old photos, proxies; the IP label is where the uploader was, and the photo is often in a neighbouring province. A poster's "not in X" is itself a hypothesis. When the label conflicts with the image, keep matching areas in that province and its neighbours; never exclude a whole province on it.
- Verify: compare the posting time with the watermark or metadata time (`meta.py photo.jpg`); record it with `board.py evidence`, never `board.py exclude`.
- Source: general knowledge (platform feature).

### Timestamp watermark and metadata time
- Look for: a date-time watermark in a corner of the frame; the capture time in the file metadata; watermark-camera apps (今日水印相机, 马克水印相机 and similar, common on work check-in photos) that also stamp an address, weather or coordinates.
- Points to: month and time of capture for phenology and sun calculations; a stamped address names the place.
- Strength: medium for the time (camera settings can be wrong, metadata can be edited); strong for a stamped address once the scene agrees.
- Counterexamples: rephotographed images; metadata stripped by reposting; camera time zone not set; watermark text can be edited by hand.
- Verify: `meta.py photo.jpg` (time, GPS and its GCJ-02 form); test printed coordinates as both WGS84 and GCJ-02 (`geo.py convert --from gcj --to wgs <lat> <lon>`); feed the time to `sun.py`.
- Source: general knowledge; watermark-app behaviour (unverified).

## Text and plates

### Shop signs, street signs, organisation names
- Look for: place names on shop signs, company plaques and street-name signs; search the original text.
- Points to: province / city / street.
- Strength: strong for street-name signs and organisation names; medium for place names inside shop names.
- Counterexamples: chain brands; shops named after somewhere else (重庆火锅 Chongqing hotpot, 沙县小吃 Shaxian snacks).
- Verify: `poi.py "<name>" --city <city>` lists every same-name point; `clues.py lookup admin <district>` gives the parent chain.
- Source: general knowledge.

### Issuing authority at the bottom of signs
- Look for: small print on traffic, prohibition, notice and construction signs: 〇〇市公安局交警支队 (city traffic police detachment), 〇〇区城管 (district urban management), 〇〇街道办 (subdistrict office).
- Points to: city and district (county); often names the division directly.
- Strength: medium (reaches the district when legible).
- Counterexamples: an agency with cross-district jurisdiction is not the district you are in; blurry small print is easy to misread, so confirm with a second sign.
- Verify: `clues.py lookup admin <district name>` for the parent chain; `poi.py "<agency name>"` for its location.
- Source: general knowledge (method).

### Landline area codes
- Look for: landline numbers on signs, ads and construction notices.
- Points to: blocks by first digit: 010 Beijing; 02X municipalities and megacities (020 Guangzhou, 021 Shanghai, 022 Tianjin, 023 Chongqing, 024 Shenyang, 025 Nanjing, 027 Wuhan, 028 Chengdu, 029 Xi'an); 03 North China and the Central Plains (Hebei, Shanxi, Henan); 04 Northeast and Inner Mongolia; 05 East China (Jiangsu, Shandong, Anhui, Zhejiang, Fujian); 07 Central and South China (Hubei, Hunan, Guangdong, Guangxi, Jiangxi); 08 Southwest (Sichuan, Guizhou, Yunnan, Tibet); 09 Northwest (Shaanxi, Gansu, Ningxia, Qinghai, Xinjiang). The full code reaches the prefecture-level city.
- Strength: medium (a full code reaches the city).
- Counterexamples: judge the code length from the digit grouping first; 400/800 numbers and 11-digit mobile numbers map to no region; a company may print a head-office number; some blocks have exceptions (06XX codes belong to parts of Shandong, Guangdong and Yunnan), so the table decides.
- Verify: `clues.py lookup area-code 0817` (also accepts "0817-1234567" and "(020) 8888").
- Source: https://zh.wikipedia.org/zh-cn/中国大陆固定电话号码 (the `clues.py` table); block pattern: general knowledge.

### License plates
- Look for: the first character is the province abbreviation and the letter after it the prefecture-level city (A is usually the provincial capital; well-known others: 粤B Shenzhen, 鲁B Qingdao, 辽B Dalian, 闽D Xiamen). Background: blue small vehicles; yellow large vehicles; gradient green new-energy small vehicles; yellow-green new-energy large vehicles; black foreign-related vehicles and Hong Kong/Macau cross-border vehicles (粤Z); white police and military plates.
- Points to: province / prefecture-level city.
- Strength: strong when several vehicles on a local street agree; weak for a single vehicle or cars in parking lots, scenic areas, hotel entrances or expressway service areas.
- Counterexamples: out-of-town cars are common in big cities and tourist areas; freight corridors carry plates from everywhere; illegible plates in tourist car parks place nothing.
- Verify: `clues.py lookup plate 粤B` (prefecture); `clues.py lookup plate-prefix 渝` (province).
- Source: regulation (GA 36 plate standard); codes: https://zh.wikipedia.org/zh-cn/中华人民共和国民用机动车号牌 (the `clues.py` table).

## Vehicles and traffic

### Taxi colours
- Look for: the main body colour and scheme (green, yellow, blue and white, red).
- Points to: a city-level candidate list (green-family taxis are common in several Sichuan cities); build the list live, it changes over the years.
- Strength: weak (single source); medium together with bus livery and terrain.
- Counterexamples: one city often runs several colours and changes them by generation; Chongqing, Xi'an, Changzhi and other cities also run green-family taxis; ride-hailing cars do not count.
- Verify: `revimg.py --query "<城市> 出租车 颜色" --country CN --out-dir q/` for each candidate city.
- Source: general knowledge (single source).

### Bus livery (roof and body, readable even from above)
- Look for: roof colour, body colour, waistline stripe, rear-end pattern; zoomed top-down shots often leave only colour blocks, which still work.
- Points to: a city fingerprint (narrow to a few cities with taxis first, then separate them by bus livery). Inside a municipality or a large prefecture-level city it separates districts and counties: outlying districts run different bus companies with very different liveries.
- Strength: medium (can narrow a city to one or two districts); strong when route signs or company names are visible.
- Counterexamples: several liveries coexist and change by generation; ad wraps hide the base colours; cross-district routes run into other districts; absence from the first result pages proves nothing.
- Verify: confirm the urban-core livery first; if it does not match, `revimg.py --query "<城市> <颜色> 公交" --country CN --out-dir q/`, read district names from route signs and company names in the results, resolve each with `poi.py` before using it, then compare rear ends and waistlines district by district ([Discriminating tests inside a city](#discriminating-tests-inside-a-city)).
- Source: (unverified; two independent observations).

## Infrastructure

### Electrified railway: catenary masts on one side or both
- Look for: a row of poles beside the track with triangular cantilever arms holding two or three non-parallel wires (messenger and contact wire). Masts on one side only → usually single track; masts on both sides or portal frames across the tracks → double track.
- Points to: an electrified railway; single-track electrified lines are a small share, so this narrows a lot.
- Strength: medium.
- Counterexamples: from far away or low down, masts on the far side hide behind trees or embankments; stations, bridges and tunnels use other structures; "single track = old line" does not hold.
- Verify: list candidate lines and their track count ([corridors.md §2](../corridors.md#2-railways), OpenRailwayMap).
- Source: general knowledge (railway engineering).

### Bundled conductors per phase on transmission lines
- Look for: how many conductors form one bundle per phase under the cross-arm (with spacers between them).
- Points to: voltage: single conductor ≈ below 220 kV; 2 → 220–330 kV; 4 → 500 kV; 6 → 750 kV or ±800 kV DC; 8 → 1000 kV.
- Strength: weak alone; medium once intersected with railways, rivers or expressways.
- Counterexamples: special designs; the count is easy to get wrong at a distance; several circuits in one corridor overlap.
- Verify: [corridors.md §3](../corridors.md#3-power-lines); OpenInfraMap voltage layer.
- Source: general knowledge (Chinese grid practice).

### Combinations of special urban transport facilities
- Look for: cross-river passenger cableways (two or three closely parallel track ropes plus a haul rope, slanting from a riverside station to the far bank), road/rail-transit bridges (double-deck truss, rail on the lower deck), light rail running through a building, long urban escalators, high-speed rail viaducts.
- Points to: each facility maps to a set of cities; two or three in one frame intersect to very few (a cableway, a road/rail bridge and steep riverside mountains together leave one or two mountain river cities).
- Strength: medium (the combination can reach the city).
- Counterexamples: high-voltage lines over a river (tall towers, insulators, nearly horizontal), cable-stayed bridge stays (fanning from the tower top) and dock-crane cables pass for cableways; road/rail bridges in Wuhan, Nanjing and elsewhere are structurally similar but differ in colour and terrain.
- Verify: web search each facility type in each candidate city, never from memory ([corridors.md §4](../corridors.md#4-co-occurrence-queries-several-kinds-of-infrastructure-in-the-same-frame)).
- Source: general knowledge (method); facility lists change, check them live.

### Hu Hu Tong (户户通) small satellite dishes
- Look for: small dishes 35–60 cm across on rooftops in rural areas and urban villages.
- Points to: they aim at ChinaSat 9 (92.2°E), so the heading tracks longitude: southwest (about 215°–227°) in eastern cities, south or southeast in the west.
- Strength: medium (an accurate azimuth bounds the longitude).
- Counterexamples: large dishes at institutions and cable TV stations point at other satellites; on offset-feed dishes the face tilt is not the elevation angle.
- Verify: `sun.py dish --lat <lat> --sat 92.2 --azimuth <deg>` works back to longitude; table in [sky.md §5](../sky.md#5-satellite-tv-dishes).
- Source: orbital geometry ([sky.md §5](../sky.md#5-satellite-tv-dishes)).

## Climate and phenology (must be paired with the month)

### Evergreen broadleaf trees in winter photos
- Look for: in December–February photos, whether street trees, green belts and hillsides at the city edge are broadly green (camphor, glossy privet, osmanthus, banyan and similar).
- Points to: the subtropical evergreen broadleaf zone, roughly south of the Qinling–Huaihe line.
- Strength: medium with a reliable month (excludes half of China); weak without one.
- Counterexamples: northern cities plant evergreen pines, cypresses and Japanese spindle (mostly conifers or shrubs); the parts of northern provinces south of the Qinling stay green in winter (Longnan in Gansu, Hanzhong and Ankang in Shaanxi); high southern mountains drop leaves and hold snow.
- Verify: fix the month first (`meta.py photo.jpg`, watermark); compare winter-dated imagery of candidates (`tiles.py wayback <lat,lon> --zoom 15 --out wb.jpg`).
- Source: general knowledge (Qinling–Huaihe climate divide).

### Colour of mountains in winter (distant or aerial views)
- Look for: in winter distant or high-altitude views, whether mountains are uniformly grey-brown and bare or broadly green.
- Points to: grey-brown → temperate mountains north of the Qinling–Huaihe line; green → southern subtropical mountains.
- Strength: medium (separates north from south; does not reach the province).
- Counterexamples: conifer forests in the northern Greater Khingan and the Changbai Mountains stay dark green; the arid northwest is brown all year; high southern mountains also turn yellow in winter; useless for summer photos.
- Verify: fix the month first; `tiles.py wayback` for winter-dated tiles of the candidate ranges.
- Source: general knowledge.

### White water bodies seen from altitude
- Look for: in aerial or airplane-window photos, water surfaces that are uniformly white with no reflection.
- Points to: ice or snow on ice → regions with long stretches of sub-zero daily mean temperature in winter, roughly north of the Qinling–Huaihe line.
- Strength: weak (pair with season and mountain colour).
- Counterexamples: salt lakes and salt pans, dry lakebeds, sediment-laden water, sun glint, thin cloud; small southern ponds freeze briefly during cold waves.
- Verify: `sun.py weather --at <lat,lon> --dates <start>:<end>` for sub-zero spells at candidates; winter-dated tiles (`tiles.py wayback`).
- Source: general knowledge.

### Palms and coconut trees ("tropical China")
- Look for: rows of coconut palms, palm-family plants, tropical landscaping.
- Points to: list every candidate: Hainan, southern Guangdong (Leizhou Peninsula), southern Guangxi, southern Yunnan (valleys in Xishuangbanna, Dehong, Honghe), southern Taiwan; beyond that, Southeast Asia.
- Strength: weak (only draws the candidate set).
- Counterexamples: parks in Fujian, Sichuan, Shanghai and elsewhere plant palms. List every province with that biome before choosing: tropical China is not only the coast.
- Verify: plates and text first; then `baidu_pano.py sample --bbox <s,w,n,e> --n 24 --out <area>.jpg` for each tropical candidate.
- Source: general knowledge.

### Weeping willows and calm artificial water, nothing else
- Look for: weeping willows, mixed trees, water like an irrigation canal or fish pond; no mountains, towers, road signs or buildings.
- Points to: mainly the provinces of the Huang-Huai-Hai Plain (Henan, Hebei, Shandong, Anhui, Jiangsu).
- Strength: weak (a few provinces at best; such photos usually only give a range).
- Counterexamples: the Yangtze basin and irrigated northwestern oases also have willows and canals.
- Verify: look for any other layer (plates, text, poles) before narrowing; satellite land cover of candidates.
- Source: general knowledge (unverified).

### Fog and low cloud
- Look for: low visibility, a grey-white sky, distant mountains reduced to outlines.
- Points to: common in Sichuan Basin cities (Chongqing and others) in the winter half of the year.
- Strength: weak (only boosts; fixes neither the city nor the date).
- Counterexamples: smoggy winter days in North China and the Yangtze River Delta look the same; phone filters and backlight also grey a scene.
- Verify: `sun.py weather --at <lat,lon> --date YYYY-MM-DD` at candidates when the date is known.
- Source: general knowledge (Sichuan Basin climate).

## Terrain and water

### Mountains rising straight from the far bank of a big river, buildings stacked up the slopes
- Look for: a very wide river with mountains several hundred metres high within one or two km of the far bank; houses climbing the slope tier by tier.
- Points to: mountain river cities (central Chongqing, Yibin, Luzhou and other Sichuan–Chongqing and upper-Yangtze cities); excludes plains cities on the middle and lower Yangtze (Wuhan, Jiujiang, Nanjing, Wuhu).
- Strength: weak (excludes a large area; does not fix the city).
- Counterexamples: Yichang and other cities also face mountains across the river; fog makes distant mountains look closer, so check whether the mountain foot meets the built-up area.
- Verify: `terrain.py view --at <camera position> --heading <deg> --hfov 65 --out v.png --photo photo.jpg` at each candidate.
- Source: general knowledge.

### Mountain city at the confluence of two rivers
- Look for: a built-up area straddling the confluence of two rivers, surrounded by mountains.
- Points to: a common layout in Sichuan–Chongqing and the southwest (Chongqing, Yibin, Luzhou and others); separate cities by confluence angle, river islands, bridge positions and river width.
- Strength: weak (common layout).
- Counterexamples: islands and shorelines change with water level and construction; mind the date of the satellite imagery.
- Verify: template comparison in [corridors.md §6](../corridors.md#6-template-comparison-between-cities); date the tiles with `tiles.py wayback`.
- Source: general knowledge.

### Wide muddy yellow river with low, dense, branching gullies
- Look for: a river several hundred metres wide and earthy yellow; low hills on both banks cut by gullies into branching patterns, sparse vegetation, terraces on the slopes.
- Points to: the Loess Plateau reach of the middle Yellow River (around the Shanxi–Shaanxi gorge) and its tributaries in northern Shaanxi, western Shanxi and eastern Gansu.
- Strength: medium (reaches Loess Plateau plus Yellow River; flow direction and bank terrain give the reach).
- Counterexamples: in flood season the Yangtze and the Jinsha are also yellow, but their banks are plains and high gorges respectively; tributaries such as the Wuding and Yan rivers are as muddy but much narrower.
- Verify: [corridors.md §5](../corridors.md#5-large-rivers-identify-the-river--river-section--line-to-point) (river → section → point).
- Source: general knowledge.

### Blue-green Yellow River in a canyon
- Look for: a wide, clear blue-green river surface with no visible sediment, in a loess or red sandstone canyon.
- Points to: reservoirs of the upper Yellow River cascade (Liujiaxia, Yanguoxia, Bapanxia in Gansu; Lijiaxia in Qinghai; Qingtongxia in Ningxia; others).
- Strength: weak (reaches the "upper-river reservoir" class only).
- Counterexamples: season, light and drone filters all change water colour. Fame is not evidence: enumerate every reservoir of that class in the candidate area.
- Verify: `terrain.py view` from each reservoir's candidate viewpoints; [corridors.md §5](../corridors.md#5-large-rivers-identify-the-river--river-section--line-to-point).
- Source: general knowledge.

## Urban form

### No office clusters or supertall towers in the skyline
- Look for: a frame of residential high-rises only, with no glass-curtain-wall office clusters or supertall landmarks.
- Points to: the old town of a prefecture-level city or a county seat, not the core of a provincial capital.
- Strength: weak.
- Counterexamples: old districts of provincial capitals and suburban counties look the same; the photo shows one direction only; the photographer may stand on the tallest building in town.
- Verify: `baidu_pano.py sample --bbox <s,w,n,e> --n 24 --out <city>.jpg` of each candidate core.
- Source: general knowledge.

### Tile-clad factory buildings with rows of AC units next to new towers (Pearl River Delta)
- Look for: six- to eight-storey factory buildings clad in small square beige or yellow-green tiles, windows lined with AC units, new glass towers beside or behind them.
- Points to: industrial-zone redevelopment areas in Shenzhen, Dongguan and similar cities.
- Strength: weak (suggests the Pearl River Delta; does not fix the city).
- Counterexamples: old industrial areas in the Yangtze River Delta (Suzhou, Ningbo) have similar buildings; tile colour and AC density usually differ.
- Verify: `baidu_pano.py sample --bbox <s,w,n,e> --n 24 --out <area>.jpg` for Pearl River Delta and Yangtze River Delta candidates.
- Source: (unverified).

## Discriminating tests inside a city

Livery is the cheap test `board.py next` proposes when several districts of one city still fit:

- `revimg.py --query "<城市> <颜色> 公交" --country CN --out-dir q/` (query: <city> <colour> bus); read route signs and company names in the results.
- Resolve each place name to a district with `poi.py` before using it; a bus from district A is not a clue for district B.
- Compare the rear end and waistline stripe district by district.

## Street-level fingerprints between similar cities (procedure)

When several cities in one basin or province still fit, compare what each city procures uniformly (guardrails, streetlights, bus stops, kerbs, sign poles):

```bash
baidu_pano.py sample --bbox <city A built-up area s,w,n,e> --n 24 --out cityA.jpg
baidu_pano.py sample --bbox <city B built-up area s,w,n,e> --n 24 --out cityB.jpg
```

Working rules:
- Compare municipal fixtures only; never shop signs, trees or cars.
- The sample prints its capture years (`baidu_pano.py info <id>` for one point); fixtures get replaced, so drop one strength tier when sample and photo years are far apart.
- Record a fixture difference in this file only after it holds across three or more cities and two independent samples.

## Searching and maps in China

- Chinese keyword search (Baidu and Sogou Images, `--country CN`): [search.md, Keyword image search on the local engines](../search.md#keyword-image-search-on-the-local-engines). Where to search by object type (Douyin, Xiaohongshu, Weibo, Ctrip reviews, property-site albums): [search.md §2](../search.md#2-choose-where-to-search-by-object-type). Local feeds and check-in spots: [search.md §4](../search.md#4-social-media-and-check-in-spot-search).
- Street-level imagery is Baidu (`baidu_pano.py`); Google has only a few tourist sites ([streetview.md](streetview.md)).
- Chinese web maps use GCJ-02 (Amap, Tencent, 360 Maps) or BD-09 (Baidu): report WGS84 and GCJ-02 and convert with `geo.py convert` ([data-sources.md](../data-sources.md)).
