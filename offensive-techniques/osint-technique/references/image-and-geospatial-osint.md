# Image & Geospatial OSINT

Image and geospatial research reveals location, time, people, and context from visual media—images, videos, satellite imagery, and map data.

## Research Objectives

- **Geolocation**: Pinpoint location from image/video clues.
- **Chronolocation**: Determine time/date from shadows, celestial bodies, or metadata.
- **Content verification**: Is image authentic or manipulated?
- **Context discovery**: Landmarks, signs, buildings reveal location + time period.
- **Person tracking**: Movement patterns, frequent locations.

---

## Reverse Image Search

### General Purpose

- **Google Lens** (lens.google.com): Standard reverse image; finds matches + web pages containing the image.
- **TinEye** (tineye.com): Specialized reverse search; good for older images, copyright tracking.
- **Yandex Images** (yandex.com/images): Effective for Russian/Eastern European content.
- **Bing Image Search**: Alternative dataset.

### Face Search

- **PimEyes** (pimeyes.com): Facial search engine; upload face → returns matches across indexed sites.
- **FaceCheck** (facecheck.id): Similar; different dataset.
- **Google Face Search**: Experimental; limited public access.

---

## Geolocation Techniques

### Landmark Identification

- **Google Street View**, **Apple Maps**, **Yandex Maps**, **Baidu Maps**: Virtual street exploration.
- **Identify signs, buildings, architectural style, vegetation type, road markings**.
- **Manual comparison**: Match foreground features (signs, license plates) with maps.

### Geolocation Tools

- **Overpass Turbo** (overpass-turbo.eu): Advanced OpenStreetMap queries; search POIs (cafes, churches, monuments).
- **Mapillary** (mapillary.com): Crowdsourced street-level imagery; alternative to Google Street View.
- **KartaView** (kartaview.org): Community street-level imagery.

### Satellite Imagery

- **Google Earth Pro**: Historical imagery slider; view same location across years.
- **Sentinel Hub EO Browser** (apps.sentinel-hub.com/eo-browser): Sentinel + Landsat satellite data; multispectral analysis.
- **NASA Worldview**: NASA satellite imagery + false-color composites.
- **Zoom Earth** (zoom.earth): Live satellite + weather.
- **Wayback Imagery** (livingatlas.arcgis.com/wayback/): Historical satellite images.

---

## Chronolocation (Time Determination)

### Shadow Analysis

- **SunCalc** (suncalc.org): Input location + adjust date/time → shows sun position + shadow direction.
- **ShadeMap** (shademap.app): 3D shadow simulator; match shadow length + direction from image.
- **Bellingcat Shadow-Finder**: Specialized tool for shadow analysis.

### Celestial Bodies

- **Stellarium** (stellarium.org): Planetarium software; identify constellations, moon phase at specific time/location.
- **MoonCalc** (mooncalc.org): Moon position by date/location.
- **Method**: Match visible stars/constellations in image to simulate specific date + location.

### Satellite Imagery Timing

- **Sentinel Hub EO Browser**: Select satellite dataset + date range; spot infrastructure changes (building demolition, new roads, snow cover).
- **Google Earth Pro**: Historical slider → pinpoint image date by visible changes.

### Metadata

- **EXIF data** (timestamp, camera, GPS): Often embedded in images.
- **ExifTool** (exiftool.org): Command-line EXIF reader.
- **Jeffrey's EXIF Viewer** (web): Online EXIF reader.
- **Caveat**: EXIF can be spoofed or stripped; validate via visual clues.

---

## Video Analysis

### Platform-Specific

- **YouTube Data Viewer** (citizenevidence.amnestyusa.org): Extract upload date, thumbnail, description.
- **YouTube Geo Tag**: Extract geolocation data from video metadata.
- **Snap Map**: Public Snapchat stories reveal location + time.
- **TikTok / Instagram**: Posts often geotagged; check map feature.
- **Telegram**: Channel posting patterns, geolocation via metadata.

### Video Extraction

- **FFmpeg**: Extract frames at intervals or on visual change.
- **VLC Media Player**: Capture frames manually.
- **Analyze each frame** using image geolocation techniques.

### Metadata Extraction

- **MediaInfo** (mediaarea.net): Technical metadata (codecs, bitrate, duration, creation date).
- **ExifTool**: Metadata from video files.

---

## Image Forensics

### Authenticity Verification

- **Forensically** (29a.ch/photo-forensics/): Error Level Analysis, metadata examination, clone detection.
- **FotoForensics** (fotoforensics.com): Digital forensics tools.
- **Bellingcat Photo Checker** (photo-checker.bellingcat.com): AI-assisted deepfake detection.

### Deepfake Detection

- **Sensity AI** (sensity.ai): Deepfake detection.
- **Reality Defender** (realitydefender.com): AI-generated content detection.
- **Adobe Content Credentials Verify** (verify.contentauthenticity.org): C2PA verification; checks if content has been modified.

---

## Metadata in Documents

### Document Metadata

- **FOCA** (elevenpaths.com/labstools/foca): Batch extract metadata from documents (PDFs, Word, Excel).
- **Metagoofil** (edge-security.com/metagoofil.php): Extract metadata from public documents via Google dorking.
- **ExifTool**: Also works on office documents.
- **Value**: Author names, software versions, creation dates, server names, usernames.

---

## OSM & Infrastructure Mapping

### Open Street Map Queries

- **Overpass Turbo**: Query OSM for specific features (churches, surveillance cameras, hospitals, power lines).
- **Example**: Find all CCTV cameras in a city; find military installations; find prisons.

### Infrastructure Layering

- **Open Infrastructure Map** (openinframap.org): Global infrastructure networks (power lines, water, telecoms).
- **Windy** (windy.com): Live weather + wind patterns.

---

## Workflow: Geolocate an Image

1. **Metadata check**: Extract EXIF (ExifTool, online viewers).
2. **Reverse image search**: Google Lens, TinEye, Yandex.
3. **Landmark identification**: Analyze signs, buildings, architecture, vegetation, road markings.
4. **Street View**: Use Google/Yandex/Apple Maps to match foreground.
5. **Satellite validation**: Google Earth Pro or Sentinel Hub; compare visible infrastructure.
6. **Shadow analysis**: If outdoor, use SunCalc to narrow date + time.
7. **Celestial bodies**: If night scene with visible stars/moon, use Stellarium.
8. **Metadata forensics**: Check for modifications via Forensically or similar.
9. **Cross-check**: Ensure findings align (sun direction matches shadow, visible infrastructure matches satellite).
10. **Report**: Location (lat/long, address), confidence level, verification method, relevant screenshots.

---

## Workflow: Verify Video Authenticity

1. **Extract metadata**: MediaInfo, ExifTool.
2. **Extract key frames**: FFmpeg at regular intervals.
3. **Geolocate frames**: Apply image geolocation workflow.
4. **Check platform**: YouTube Data Viewer for upload metadata.
5. **Deepfake check**: Sensity AI, Reality Defender.
6. **Forensics**: Forensically for Error Level Analysis.
7. **Temporal**: Match timeline (shadows, weather, celestial).
8. **Report**: Authenticity assessment, location/time confirmation, confidence levels.

---

## Anti-Patterns

- **Assuming EXIF = accurate**: EXIF can be spoofed; validate via visual + satellite checks.
- **Single landmark = location**: Identical buildings exist in multiple places; require multiple independent clues.
- **Ignoring resolution + lighting**: High-resolution + specific lighting conditions narrow down location + time.
- **Assuming no metadata = authentic**: Removal of metadata does not prove manipulation; use image forensics.
