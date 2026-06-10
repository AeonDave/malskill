# Image Geolocation and OSINT Media Triage

Load when the artifact is an image, video, or media file and the objective is to determine location, identity, or timestamps from visual and metadata evidence.

---

## Triage order

```
1. Metadata (EXIF, XMP, GPS coords) — instant win when available
2. Reverse image search — find originals or context
3. Visual anchor analysis — buildings, text, vegetation, terrain, shadows
4. Map verification — satellite, Street View, OSM query
5. Independent confirmation — second source before asserting location
```

---

## Step 1 — Metadata extraction

```bash
exiftool image.jpg
exiftool -GPS* image.jpg           # GPS fields only
exiftool -GPSLatitude -GPSLongitude -DateTimeOriginal image.jpg

# Convert DMS to decimal manually or via python:
#   lat  = dd + mm/60 + ss/3600
#   sign = -1 if S or W

# Also check:
#   MakeNote / CameraModel → device
#   Software → editing tool (removes GPS sometimes)
#   CreateDate vs ModifyDate → timestamp integrity
```

For videos: `exiftool video.mp4 | grep -i "gps\|location\|creat\|date"`

---

## Step 2 — Reverse image search

| Tool | Best for |
|---|---|
| Google Lens (lens.google.com) | General; recognises landmarks and objects |
| Yandex Images | Strongest for faces, post-Soviet locations |
| TinEye (tineye.com) | Exact duplicate detection; timestamped index |
| Bing Visual Search | Often indexes images Google misses |

**Workflow:**
1. Upload the full image first.
2. If no match: crop to the most distinctive element (building facade, sign, terrain feature) and search again.
3. Check the earliest indexed date on TinEye to verify origin or detect manipulation.

---

## Step 3 — Visual anchor analysis

Extract anchors in this priority:

**Text (highest priority):**
- Street signs, business names, shop logos → OCR + language → country/city
- Licence plates → format → country/region
- Arabic, Cyrillic, CJK, Latin → narrows down region immediately

**Built environment:**
- Architectural style (concrete block, colonial, Nordic wood, brutalist) → era + region
- Electrical infrastructure (poles, insulators, street lamps) → country-specific profiles
- Road markings, traffic light position, left/right-hand traffic

**Natural environment:**
- Vegetation: tropical palms vs. deciduous vs. conifers vs. arid/sparse
- Terrain and soil color: red laterite (West Africa, SE Asia), beige sand (Sahel), volcanic black
- Mountain silhouette → cross-reference with known ranges

**Weather/light:**
- Shadow angle + length → compass heading + approximate latitude band + time of day
- `SunCalc.org` / `ShadowMap.app`: input rough coordinates + date/time → verify shadow matches photo
- Snow, monsoon rain, dry cracked earth → seasonal window

---

## Step 4 — Map verification

Once you have a candidate area:

```bash
# Google Maps / Google Earth Pro
# 1. Satellite view → match rooftop pattern, road layout, vegetation density
# 2. Street View → pan around the location, look for exact building/sign match
# 3. Historical imagery slider → date the change if the landmark changed

# OpenStreetMap Overpass Turbo (overpass-turbo.eu)
# Example: find mosques in a 1 km radius
node["amenity"="place_of_worship"]["religion"="muslim"](around:1000,<lat>,<lon>);
out;

# Mapillary / KartaView — crowdsourced street-level imagery
# Useful for locations without Google Street View coverage
```

**Satellite interpretation tips:**
- Road width and layout → highway vs. local vs. dirt track
- Shadow direction → north/south orientation of photo
- Compound/building shape patterns → village style, industrial vs. residential

---

## Step 5 — Independent confirmation

Do not assert a location until you have at least two independent anchors:
- Text anchor + terrain match
- Street View photo that shows the same building with the same signage
- Satellite rooftop that matches the shadow angle in the photo
- Mapillary/KartaView showing the same infrastructure

Confidence labels:
- **Confirmed**: visual match from at least two independent sources, one of which is a current or archived photo
- **High confidence**: one strong visual match + terrain consistency
- **Candidate**: single match; needs further verification

---

## Extra tools for specialist scenarios

| Scenario | Tool / approach |
|---|---|
| Face/person identification | PimEyes, FaceCheck.id (authorized use only) |
| Aircraft in image | FlightAware, ADS-B Exchange (cross-reference tail number) |
| Ship/vessel | MarineTraffic (cross-reference flag, hull color, markings) |
| Broadcast/stream geolocation | Examine on-screen clocks, channel logos, language |
| Shadows → coordinates | SunCalc + known date/time to back-compute latitude band |
| Building style → country | Geoguessr-style visual guides; compare against Google Earth drives |

---

## Pitfalls

- Trusting metadata without checking if GPS coordinates match visual anchors (metadata can be spoofed or wrong).
- Assuming the reverse-image match is the original photo (it may be a re-upload of the same modified image).
- Declaring a location from a single anchor without any independent verification.
- Ignoring text in the scene — it is the fastest anchor and analysts frequently skip it.
- Confusing current Street View date with the photo date — check "historical imagery" in Google Earth.
