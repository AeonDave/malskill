#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "pillow-heif", "tzdata", "cbor2>=6.1.5,<7"]
# ///
"""Deep metadata and file forensics for one photo or video (uses exiftool; falls back to Pillow).

Finds what plain EXIF readers miss:
  GPS from EXIF, XMP, QuickTime/Android video atoms and DJI drone XMP (incl. gimbal/flight heading, altitude)
  capture time with its UTC offset — from OffsetTime*, or derived from GPS UTC time vs local time —
  and every country whose time zones had that offset on that date (DST-aware); videos: QuickTime CreationDate
  (carries its offset) before CreateDate, which is flagged as container time of unknown zone
  camera/maker-note location hints (camera "home/destination city" time-zone settings, IPTC/XMP city and country)
  editing and provenance (software, edit history, C2PA / content credentials); the IPTC source type split into
  "file declares generated content" and "AI-edited real photo" (provenance.generated in the JSON)
  embedded thumbnails/previews that differ from the main image (the uncropped original may be inside)
  filename patterns (WhatsApp, WeChat, KakaoTalk, LINE, Telegram, Viber, stock-photo IDs, screenshots
  and the OS language of the screenshot name) and JPEG recompression hints

  meta.py photo.jpg --out-dir meta/        → meta/meta.json, meta/meta.md, meta/thumb_*.jpg
  meta.py photo.jpg                        → print the summary
  meta.py a.jpg b.heic --json              → one compact JSON digest per file (GPS + GCJ-02, time, optics)

Without exiftool a pure-Python fallback reads EXIF, GPS, XMP (incl. DJI XMP fields), video ISO 6709 location and the
source type, from its own property only, in XMP (a PNG's too) and C2PA manifests (JPEG APP11, PNG caBX); a brotli-compressed
or remote manifest needs exiftool or c2patool. The output then carries a one-line notice of what needs exiftool (large previews,
maker notes, QuickTime atoms).
Optics: focal_35mm and the 4:3 field of view feed geo.py range / terrain.py; GCJ-02 is added for points in China.
Social apps (WeChat, WhatsApp, QQ) strip metadata on forwarding; screenshots carry none. Empty output means nothing.

Metadata is evidence about the file, not proof about the scene: it can be stripped, edited or carried
over from another photo. When it conflicts with the image, the image wins.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geo  # noqa: E402  (GCJ-02 conversion, field of view from the 35 mm focal)

ZONE_DIR = Path("/usr/share/zoneinfo")          # system tz database on Linux/macOS, tried after zoneinfo.TZPATH

FILENAME_PATTERNS = [
    (r"^IMG-\d{8}-WA\d+", "WhatsApp (Android) — recompressed, metadata stripped; date = received/sent date"),
    (r"^VID-\d{8}-WA\d+", "WhatsApp video (Android)"),
    (r"^WhatsApp (Image|Video) \d{4}-\d{2}-\d{2} at ", "WhatsApp desktop/web export"),
    (r"^mmexport(\d{13})", "WeChat export (mainly China users); the number is the export time in ms"),
    (r"^微信图片_\d{14}", "WeChat for Windows (China)"),
    (r"^wx_camera_(\d{13})", "WeChat in-app camera (China)"),
    (r"^KakaoTalk_\d{8}_\d+", "KakaoTalk (South Korea)"),
    (r"^(LINE_ALBUM_|LINE_P\d|line_\d+)", "LINE (Japan, Taiwan, Thailand)"),
    (r"^viber_image_\d{4}-\d{2}-\d{2}", "Viber (popular in Eastern Europe, the Balkans, the Philippines)"),
    (r"^photo_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", "Telegram desktop export"),
    (r"^signal-\d{4}-\d{2}-\d{2}", "Signal"),
    (r"^FB_IMG_(\d{13})", "Facebook app save; number = save time in ms"),
    (r"^received_\d+", "Facebook Messenger"),
    (r"^\d+_\d+_\d+_[no]\.(jpe?g|webp)$", "Facebook/Instagram CDN filename"),
    (r"^Snapchat-\d+", "Snapchat"),
    (r"^PXL_\d{8}_\d{9}", "Google Pixel camera"),
    (r"^IMG_E?\d{4}\.(HEIC|JPG|JPEG|PNG|MOV)$", "iPhone camera roll (IMG_E = edited)"),
    (r"^\d{8}_\d{6}", "Samsung / Android camera"),
    (r"^IMG_\d{8}_\d{6}", "Android camera (many brands)"),
    (r"^DJI_\d{4}", "DJI drone — aerial branch; check DJI XMP for heading and altitude"),
    (r"^(GOPR|GP|GX|GH)\d{4,6}", "GoPro action camera"),
    (r"^DSC[_F]?\d{4}", "Dedicated camera (Sony/Nikon/Fujifilm style)"),
    (r"^(shutterstock|iStock|AdobeStock|GettyImages|dreamstime|depositphotos|123rf|alamy)[_-]?\d+", "Stock photo: search the ID on the agency site — captions name the place"),
    (r"-unsplash\.(jpe?g|png)$", "Unsplash stock photo: the photographer page often names the place"),
    (r"^pexels-", "Pexels stock photo"),
    (r"^Screenshot_\d{8}-\d{6}_(.+)\.", "Android screenshot; the suffix is the app that was open"),
]
SCREENSHOT_LANG = [
    (r"^Screen ?[Ss]hot", "en"), (r"^Captura de pantalla", "es"), (r"^Capture d.écran", "fr"), (r"^Bildschirmfoto", "de"),
    (r"^Schermata", "it"), (r"^Captura de Tela", "pt-BR"), (r"^Captura de ecrã", "pt-PT"), (r"^Schermafbeelding", "nl"),
    (r"^Skärmavbild", "sv"), (r"^Skjermbilde", "no"), (r"^Skærmbillede", "da"), (r"^Näyttökuva", "fi"),
    (r"^Zrzut ekranu", "pl"), (r"^Snímek obrazovky", "cs"), (r"^Képernyőfotó", "hu"), (r"^Ekran Resmi", "tr"),
    (r"^Снимок экрана", "ru"), (r"^Знімок екрана", "uk"), (r"^Στιγμιότυπο", "el"), (r"^スクリーンショット", "ja"),
    (r"^스크린샷", "ko"), (r"^(屏幕截图|截屏|截圖|螢幕截圖)", "zh"), (r"^ภาพหน้าจอ", "th"), (r"^Ảnh chụp màn hình", "vi"),
    (r"^Tangkapan Layar", "id"), (r"^لقطة شاشة", "ar"), (r"^צילום מסך", "he"),
]
LOCATION_KEY = re.compile(r"(City|Country|State|Province|Sublocation|Sub-location|Location|HomeTown|Destination|"
                          r"TimeZoneCity|TimeZone|DaylightSavings|Region|Landmark)", re.I)
SKIP_KEYS = re.compile(r"(ThumbnailImage|PreviewImage|JpgFromRaw|OtherImage|DataDump|MakerNoteUnknown|ICC_Profile:|"
                       r"Directory|FileName|SourceFile|FileAccessDate|FileInodeChangeDate|FileModifyDate|FilePermissions)")


# ------------------------------------------------------------------ exiftool

def exiftool(path: Path) -> dict:
    if not shutil.which("exiftool"):
        return {}
    r = subprocess.run(["exiftool", "-j", "-G1", "-a", "-n", "-u", "-ee", "-api", "LargeFileSupport=1", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout)[0]
    except Exception:  # noqa: BLE001
        return {}


# exiftool tag names for Pillow's EXIF names, so digest() reads both backends the same way (None = skip the tag)
_EXIFTOOL_NAMES = {"DateTime": "ModifyDate", "DateTimeDigitized": "CreateDate", "FocalLengthIn35mmFilm": "FocalLengthIn35mmFormat",
                   "SubsecTimeOriginal": "SubSecTimeOriginal", "SubsecTime": "SubSecTime", "ExifOffset": None, "GPSInfo": None,
                   "MakerNote": None, "UserComment": None, "PrintImageMatching": None, "ComponentsConfiguration": None}
# generator names seen in Software / CreatorTool / HistorySoftwareAgent of AI-made images
AI_GENERATOR = re.compile(r"midjourney|\bdall[\s·•.\-]?e\b|stable[\s-]?diffusion|\bfirefly\b|\bgoogle\s+imagen\b|\bimagen\s*[0-9]|\bflux\b|\bleonardo\b|\bideogram\b", re.I)
# IPTC digital source type (cv.iptc.org/newscodes/digitalsourcetype): read only from the property, never from a URI quoted
# in a comment or description. XMP: Iptc4xmpExt:DigitalSourceType under any prefix bound to the IPTC Extension namespace.
XMP_SOURCE = "{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}DigitalSourceType"
RDF_RESOURCE = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
GENERATED_TYPES = {"trainedAlgorithmicMedia", "algorithmicMedia"}
SOURCE_UNREAD = ("C2PA present, source type unread (brotli-compressed, remote or none recorded: "
                 "exiftool or c2patool shows the manifest)")
PROV_TAG = re.compile(r"(DigitalSourceType|C2PA|JUMBF|Manifest|Claim|Credential|History|DocumentAncestors|OriginalDocumentID|"
                      r"Software|CreatorTool|ProcessingSoftware|(?i:provenance))")
FALLBACK_NOTICE = ("exiftool not found: Pillow fallback read EXIF, GPS, XMP and video ISO 6709 location only; "
                   "large embedded previews, maker notes, QuickTime atoms and full DJI metadata need exiftool")
_XMP_PACKET = re.compile(rb"<x:xmpmeta.*?</x:xmpmeta>", re.S)
_XMP_ATTR = re.compile(rb'([A-Za-z][\w.-]*):([A-Za-z][\w.-]*)="([^"]{0,500})"')
_XMP_ELEM = re.compile(rb"<([A-Za-z][\w.-]*):([A-Za-z][\w.-]*)>([^<]{1,500})</\1:\2>")
_ISO6709 = re.compile(rb"([+-]\d{1,2}\.\d{2,})([+-]\d{1,3}\.\d{2,})([+-]\d+(?:\.\d+)?)?/")
_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".3gp", ".3g2", ".qt"}
CONTAINER_CLOCK = "container time, zone unknown (UTC per the QuickTime spec, local on many action cams, dashcams and drones)"


def _plain(v):
    """JSON-friendly EXIF value: rationals -> float, tuples -> lists, short ASCII bytes decoded, blobs dropped."""
    if v is None:                             # an absent tag, never the string "None"
        return None
    if isinstance(v, bytes):
        s = v.rstrip(b"\x00")
        return s.decode("ascii", "replace") if len(s) <= 64 and all(32 <= b < 127 for b in s) else None
    if isinstance(v, tuple):
        out = [_plain(x) for x in v]
        return None if any(x is None for x in out) else out
    if isinstance(v, str):
        return v.strip("\x00 ")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    try:
        return float(v)                       # IFDRational
    except (TypeError, ValueError, ZeroDivisionError):
        return str(v)[:200]


def _dms(v, ref) -> float | None:
    try:
        d, m, s = (float(x) for x in v)
    except (TypeError, ValueError):
        return None
    val = d + m / 60 + s / 3600
    return -val if str(ref).upper().startswith(("S", "W")) else val


def _xmp_coord(s: str) -> float | None:
    """XMP GPS 'DD,MM.mmmmN' / 'DD,MM,SSN' / signed decimal -> signed degrees."""
    s = s.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)(?:,(\d+(?:\.\d+)?))?([NSEW])", s, re.I)
    if m:
        val = float(m.group(1)) + float(m.group(2)) / 60 + float(m.group(3) or 0) / 3600
        return -val if m.group(4).upper() in "SW" else val
    try:
        return float(s)
    except ValueError:
        return None


def _rational(s: str) -> float | str:
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*", s)
    if m and float(m.group(2)):
        return float(m.group(1)) / float(m.group(2))
    try:
        return float(s)
    except ValueError:
        return s


def _scan_bytes(path: Path, limit: int = 8 << 20) -> bytes:
    """Whole file when small, else head + tail (XMP sits near the start of photos, moov/udta often at the end of videos)."""
    size = path.stat().st_size
    with open(path, "rb") as fh:
        if size <= 2 * limit:
            return fh.read()
        head = fh.read(limit)
        fh.seek(size - limit)
        return head + fh.read(limit)


def _terms(*values) -> list[str]:
    """IPTC terms of DigitalSourceType values: the last segment of the vocabulary URI, or a bare term."""
    return list(dict.fromkeys(t for v in values if (t := str(v).strip().rstrip("/").rsplit("/", 1)[-1]).isalpha()))


def _xmp_terms(blob: bytes) -> list[str]:
    """Source types of the XMP packets in blob: element text, rdf:resource or attribute of XMP_SOURCE. A packet that is not
    well-formed XML yields none (its namespaces cannot be resolved)."""
    values = []
    for packet in _XMP_PACKET.findall(blob):
        try:
            root = ET.fromstring(packet.decode("utf-8", "replace"))    # starts at x:xmpmeta: no DTD, no entity expansion
        except ET.ParseError:
            continue
        values += [el.get(XMP_SOURCE) for el in root.iter()]
        values += [el.get(RDF_RESOURCE) or el.text for el in root.iter(XMP_SOURCE)]
    return _terms(*(v for v in values if v))


def _jumbf_payloads(store: bytes, depth: int = 0):
    """CBOR/JSON content boxes of a JUMBF tree; unsupported or truncated boxes yield no properties."""
    if depth > 32:
        return
    at = 0
    while at + 8 <= len(store):
        size, kind, header = int.from_bytes(store[at:at + 4], "big"), store[at + 4:at + 8], 8
        if size == 1:
            if at + 16 > len(store):
                return
            size, header = int.from_bytes(store[at + 8:at + 16], "big"), 16
        elif size == 0:
            size = len(store) - at
        if size < header or at + size > len(store):
            return
        payload = store[at + header:at + size]
        if kind == b"jumb":
            yield from _jumbf_payloads(payload, depth + 1)
        elif kind in (b"cbor", b"json"):
            yield kind, payload
        at += size


def _c2pa_properties(store: bytes) -> tuple[list[str], list[str]]:
    """Own properties of decoded C2PA assertion maps; descriptions and opaque byte strings are never parsed as assertions."""
    import cbor2
    values, actions = [], []

    def visit(node, depth=0):
        if depth > 64:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "@context":          # JSON-LD maps property names to namespaces; these are not metadata values
                    continue
                tag = key.rsplit(":", 1)[-1].lower() if isinstance(key, str) else ""
                if tag == "digitalsourcetype" and isinstance(value, str):
                    values.append(value)
                elif tag == "action" and isinstance(value, str):
                    actions.append(value)
                visit(value, depth + 1)
        elif isinstance(node, (list, tuple)):
            for item in node:
                visit(item, depth + 1)
        elif isinstance(node, cbor2.CBORTag):
            visit(node.value, depth + 1)

    for kind, payload in _jumbf_payloads(store):
        try:
            if kind == b"cbor":
                stream = io.BytesIO(payload)
                node = cbor2.load(stream, max_depth=64, allow_indefinite=False, allow_duplicate_keys=False)
                if stream.tell() != len(payload):
                    continue
            else:
                node = json.loads(payload)
            visit(node)
        except (cbor2.CBORDecodeError, ValueError, RecursionError):
            continue
    return _terms(*values), list(dict.fromkeys(actions))


def _xmp_tags(blob: bytes) -> dict:
    """Simple XMP properties as exiftool-style 'XMP-<prefix>:<Name>' keys (GPS converted to signed degrees); the source type
    comes from _xmp_terms alone, so a same-named property of another namespace is not read as one."""
    out: dict = {}
    for packet in _XMP_PACKET.findall(blob):
        for rx in (_XMP_ATTR, _XMP_ELEM):
            for pre, name, val in rx.findall(packet):
                pre_s, name_s = pre.decode("ascii", "replace"), name.decode("ascii", "replace")
                if pre_s in ("xmlns", "x", "rdf", "xml", "stEvt", "stRef") or "digitalsourcetype" in name_s.lower():
                    continue
                v = val.decode("utf-8", "replace").strip()
                if not v:
                    continue
                if name_s.lower() in ("gpslatitude", "gpslongitude"):
                    v = _xmp_coord(v)
                    if v is None:
                        continue
                elif pre_s == "drone-dji" or name_s in ("GPSAltitude", "GPSImgDirection", "GPSDestBearing", "GPSSpeed", "GPSHPositioningError"):
                    v = _rational(v)
                out.setdefault(f"XMP-{pre_s}:{name_s}", v)
    terms = _xmp_terms(blob)
    if terms:
        out["XMP-Iptc4xmpExt:DigitalSourceType"] = "; ".join(terms)
    return out


def _jpeg_segments(head: bytes):
    """(marker, payload) of the JPEG marker segments before the scan data (stops at SOS)."""
    if not head.startswith(b"\xff\xd8"):
        return
    i = 2
    while i + 4 <= len(head) and head[i] == 0xFF:
        marker, seg_len = head[i + 1], int.from_bytes(head[i + 2:i + 4], "big")
        if marker == 0xDA:
            break
        yield marker, head[i + 4:i + 2 + seg_len]
        i += 2 + seg_len


def _app1_thumbnail(path: Path) -> bytes | None:
    """EXIF IFD1 JPEG thumbnail from the APP1 segment of a JPEG (exiftool's ThumbnailImage)."""
    with open(path, "rb") as fh:
        head = fh.read(256 << 10)
    for marker, seg in _jpeg_segments(head):
        if marker == 0xE1 and seg.startswith(b"Exif\x00\x00"):
            s = seg.find(b"\xff\xd8\xff", 6)
            e = seg.rfind(b"\xff\xd9")
            return seg[s:e + 2] if s != -1 and e > s else None
    return None


def _jumbf(blob: bytes) -> dict:
    """C2PA content credentials (JUMBF, ISO 19566-5) without exiftool: presence, IPTC source types, an opened ingredient.
    JPEG spreads the store over APP11 segments (CI 'JP', box instance, packet sequence, then the box, whose header every
    continuation segment repeats): rejoined per box instance, so a URI cut at a segment boundary reads whole. PNG (caBX),
    ISO BMFF and WebP keep it in one piece. A brotli-compressed ('brob') or remote manifest yields no term."""
    if blob.startswith(b"\xff\xd8"):
        boxes: dict[int, list[tuple[int, bytes]]] = {}
        for marker, seg in _jpeg_segments(blob):
            if marker == 0xEB and seg.startswith(b"JP") and len(seg) > 16:
                boxes.setdefault(int.from_bytes(seg[2:4], "big"), []).append((int.from_bytes(seg[4:8], "big"), seg[8:]))
        n = sum(len(v) for v in boxes.values())
        store = b"".join(body if i == 0 else body[16 if body[:4] == b"\x00\x00\x00\x01" else 8:]   # LBox 1: 8-byte XLBox follows
                         for en in sorted(boxes) for i, (_, body) in enumerate(sorted(boxes[en])))
        where = f"{n} APP11 segment(s)"
    else:
        m = re.search(rb"jumb.{4}jumd", blob, re.S)      # superbox, then its description box: no chance match in pixel data
        n, store, where = (1, blob[m.start() - 4:], "JUMBF box") if m and m.start() >= 4 else (0, b"", "")
    if not n:
        return {}
    out = {"JUMBF:Manifest": f"C2PA/JUMBF manifest present ({where}{', label c2pa' if b'c2pa' in store else ''})"}
    terms, actions = _c2pa_properties(store)
    if terms:
        out["JUMBF:DigitalSourceType"] = "; ".join(terms)
    if "c2pa.opened" in actions:
        out["JUMBF:Actions"] = "c2pa.opened"
    return out


def pillow_fallback(path: Path) -> dict:
    """EXIF/GPS/XMP via Pillow and byte scans when exiftool is missing; keys mimic exiftool -G1 -n output."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    from PIL import ExifTags, Image
    out: dict = {}
    try:
        blob = _scan_bytes(path)
    except OSError as e:
        return {"error": str(e)}
    out.update(_xmp_tags(blob))               # first, so EXIF keys added later win in find() lookups
    out.update(_jumbf(blob))
    if path.suffix.lower() in _VIDEO_EXT:
        m = _ISO6709.search(blob)
        if m:
            out["QuickTime:GPSCoordinates"] = " ".join(x.decode() for x in m.groups() if x)
    try:
        with Image.open(path) as im:           # sub-IFDs are parsed while the file is still open
            ex = im.getexif()
            exif_ifd, gps_ifd = dict(ex.get_ifd(0x8769)), dict(ex.get_ifd(0x8825))
            try:                               # PNG text chunks, compressed ones decompressed, those after the image data too
                text = dict(im.text) if im.format == "PNG" else {}
            except OSError:                    # truncated file: the text is lost, the EXIF read above still counts
                text = {}
    except Exception as e:  # noqa: BLE001 - videos and unknown formats land here
        if not out:
            out["error"] = str(e)
        return out
    xmp = text.get("XML:com.adobe.xmp")      # a PNG declares the source type in its XMP packet (or caBX, read above)
    png_terms = _xmp_terms(xmp.encode("utf-8", "ignore")) if isinstance(xmp, str) else []
    if png_terms:
        out["PNG:DigitalSourceType"] = "; ".join(png_terms)
    try:
        for group, items in (("IFD0", ex.items()), ("ExifIFD", exif_ifd.items())):
            for k, v in items:
                name = ExifTags.TAGS.get(k, f"Tag0x{k:04x}")
                name = _EXIFTOOL_NAMES.get(name, name)
                val = _plain(v) if name else None
                if val not in (None, "", []):
                    out[f"{group}:{name}"] = val
        g = {ExifTags.GPSTAGS.get(k, f"Tag0x{k:04x}"): v for k, v in gps_ifd.items()}
        for name, v in g.items():
            if name in ("GPSLatitude", "GPSLongitude", "GPSTimeStamp", "GPSAltitude"):
                continue
            val = _plain(v)
            if val not in (None, "", []):
                out[f"GPS:{name}"] = val
        lat, lon = _dms(g.get("GPSLatitude"), g.get("GPSLatitudeRef", "N")), _dms(g.get("GPSLongitude"), g.get("GPSLongitudeRef", "E"))
        if lat is not None and lon is not None:
            out["GPS:GPSLatitude"], out["GPS:GPSLongitude"] = lat, lon
        if "GPSAltitude" in g:
            alt = float(g["GPSAltitude"])
            out["GPS:GPSAltitude"] = -alt if g.get("GPSAltitudeRef") in (1, b"\x01", "1") else alt
        ts = _plain(g.get("GPSTimeStamp"))
        if ts:
            h, mi, s = (float(x) for x in ts)
            out["GPS:GPSTimeStamp"] = f"{int(h):02d}:{int(mi):02d}:{int(s):02d}"
            if g.get("GPSDateStamp"):
                out["Composite:GPSDateTime"] = f"{str(g['GPSDateStamp']).strip()} {out['GPS:GPSTimeStamp']}Z"
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def find(d: dict, *names: str):
    """First value whose tag name (after the group) matches one of names, case-insensitive."""
    low = {k.split(":", 1)[-1].lower(): k for k in d}
    for n in names:
        k = low.get(n.lower())
        if k is not None and d[k] not in ("", None):
            return d[k], k
    return None, None


def source_type(raw: dict) -> tuple[dict, str | None]:
    """provenance.generated, the contract photo_session.py finish and the viewer read, plus its warning line.
    declared: trainedAlgorithmicMedia/algorithmicMedia is the only source type and no ingredient was opened. composite:
    an AI composite term (compositeCapture merges real captures and is not one): an AI-edited real photo, never generated.
    Generation named beside other sources or on an opened ingredient is neither: the ingredient may be real or generated."""
    exiftool_raw = "ExifTool:ExifToolVersion" in raw
    found: dict[str, str] = {}
    for k, v in raw.items():
        group, _, tag = k.rpartition(":")
        if "digitalsourcetype" not in tag.lower():
            continue
        src = "exiftool" if exiftool_raw else group if group in ("JUMBF", "PNG") else "XMP"
        for term in _terms(*(v if isinstance(v, list) else str(v).split(";"))):
            found.setdefault(term, src)
    terms = list(found)
    opened = any("c2pa.opened" in (v if isinstance(v, list) else [v])
                 for k, v in raw.items() if (group := k.rpartition(":")[0]) in ("JUMBF", "CBOR", "JSON")
                 and ((tag := k.rpartition(":")[2]) == "Actions" or tag.endswith("Action")))
    comp = [s for s in terms if s.startswith("composite") and s != "compositeCapture"]
    gen = [s for s in terms if s in GENERATED_TYPES]
    declared = bool(gen) and len(gen) == len(terms) and not opened
    term = (comp or gen or terms or [None])[0]
    if declared:
        note = f"File declares generated content ({term})"
    elif comp:
        note = f"AI-edited real photo ({term}): edited regions are not evidence"
    elif gen:
        note = (f"Generated content named beside other sources ({', '.join(terms)}{' + c2pa.opened ingredient' if opened else ''}): "
                "not a declaration; possible generated image, unconfirmed")
    else:
        note = None
    return {"declared": declared, "term": term, "composite": bool(comp), "source": found.get(term)}, note


def all_matching(d: dict, rx: re.Pattern) -> dict:
    return {k: v for k, v in d.items() if rx.search(k.split(":", 1)[-1]) and not SKIP_KEYS.search(k)
            and not isinstance(v, (dict, list)) and str(v).strip() not in ("", "0", "Unknown")}


# ------------------------------------------------------------------ time

def parse_dt(s) -> datetime | None:
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?", s)
    if not m:
        return None
    y, mo, d, h, mi, se, tz = m.groups()
    try:
        dt = datetime(int(y), int(mo), int(d), int(h), int(mi), int(se))
    except ValueError:
        return None
    if tz:
        if tz == "Z":
            return dt.replace(tzinfo=timezone.utc)
        sign = 1 if tz[0] == "+" else -1
        hh, mm = int(tz[1:3]), int(tz[-2:])
        return dt.replace(tzinfo=timezone(sign * timedelta(hours=hh, minutes=mm)))
    return dt


def parse_offset(s) -> int | None:
    if s is None:
        return None
    m = re.fullmatch(r"\s*([+-])(\d{1,2}):?(\d{2})\s*", str(s))
    if not m:
        return None
    return (1 if m.group(1) == "+" else -1) * (int(m.group(2)) * 60 + int(m.group(3)))


def _zone_tab_text() -> str | None:
    """zone1970.tab (or zone.tab) from the system tz database, else from the tzdata wheel (Windows has no system copy)."""
    import zoneinfo
    for root in [*map(Path, zoneinfo.TZPATH), ZONE_DIR]:
        for name in ("zone1970.tab", "zone.tab"):
            f = root / name
            if f.is_file():
                return f.read_text(encoding="utf-8")
    try:
        from importlib.resources import files
        base = files("tzdata").joinpath("zoneinfo")
        for name in ("zone1970.tab", "zone.tab"):
            if base.joinpath(name).is_file():
                return base.joinpath(name).read_text(encoding="utf-8")
    except (ImportError, OSError):
        pass
    return None


def zones() -> list[tuple[list[str], str]]:
    text = _zone_tab_text()
    if text is None:
        return []
    out = []
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            out.append((parts[0].split(","), parts[2]))
    return out


def countries_for_offset(minutes: int, local: datetime | None) -> dict[str, list[str]]:
    """ISO2 → zones whose UTC offset equals minutes at that local date (DST-aware)."""
    when = (local or datetime(2024, 1, 15, 12)).replace(tzinfo=None)
    out: dict[str, list[str]] = {}
    for ccs, zname in zones():
        try:
            off = ZoneInfo(zname).utcoffset(when)
        except Exception:  # noqa: BLE001
            continue
        if off is not None and int(off.total_seconds() // 60) == minutes:
            for cc in ccs:
                out.setdefault(cc, []).append(zname)
    return out


# ------------------------------------------------------------------ jpeg

IJG_LUMA = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29,
            51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92, 49, 64, 78, 87, 103, 121,
            120, 101, 72, 92, 95, 98, 112, 100, 103, 99]


def jpeg_info(path: Path) -> dict:
    try:
        from PIL import Image
        im = Image.open(path)
    except Exception:  # noqa: BLE001
        return {}
    with im:                                   # release the handle: Windows cannot delete a file that is still open
        return _jpeg_info(im)


def _jpeg_info(im) -> dict:
    info = {"format": im.format, "size": list(im.size), "mode": im.mode}
    if im.format == "JPEG":
        q = getattr(im, "quantization", None) or {}
        if 0 in q:
            t = list(q[0])
            # estimate IJG quality from the mean ratio to the standard luminance table (zigzag order is irrelevant for the mean)
            ratio = sum(t) / sum(IJG_LUMA)
            scale = ratio * 100
            quality = (200 - scale) / 2 if scale <= 100 else 5000 / scale
            info["jpeg_quality_estimate"] = int(max(1, min(100, round(quality))))
        info["progressive"] = bool(im.info.get("progressive") or im.info.get("progression"))
        try:
            from PIL import JpegImagePlugin
            info["subsampling"] = {0: "4:4:4", 1: "4:2:2", 2: "4:2:0"}.get(JpegImagePlugin.get_sampling(im), "?")
        except Exception:  # noqa: BLE001
            pass
    w, h = im.size
    longest = max(w, h)
    hints = []
    if longest in (1600, 2560):
        hints.append("long side 1600/2560 px: typical of WhatsApp recompression")
    if longest == 2048:
        hints.append("long side 2048 px: typical of Facebook/Messenger")
    if longest == 1280:
        hints.append("long side 1280 px: typical of Telegram (compressed) and older WeChat")
    if w == 1080:
        hints.append("width 1080 px: typical of Instagram")
    if info.get("jpeg_quality_estimate", 100) < 80:
        hints.append("JPEG quality < 80: recompressed by an app or platform, metadata likely stripped")
    if w * 9 == h * 16 or w * 16 == h * 9 or abs(w / h - 9 / 19.5) < 0.01 or abs(h / w - 9 / 19.5) < 0.01:
        hints.append("screen aspect ratio (16:9 or ~19.5:9): may be a screenshot or video frame")
    info["platform_hints"] = hints
    return info


# ------------------------------------------------------------------ thumbnails

def _preview_blobs(path: Path):
    """(tag, bytes) of embedded previews: every exiftool preview tag, else the APP1 thumbnail only."""
    if not shutil.which("exiftool"):
        try:
            data = _app1_thumbnail(path)
        except OSError:
            data = None
        if data:
            yield "ThumbnailImage", data
        return
    for tag in ("ThumbnailImage", "PreviewImage", "JpgFromRaw", "OtherImage"):
        yield tag, subprocess.run(["exiftool", "-b", f"-{tag}", str(path)], capture_output=True).stdout


def extract_previews(path: Path, out_dir: Path, main_size: list[int] | None) -> list[dict]:
    res = []
    for tag, data in _preview_blobs(path):
        if len(data) < 500:
            continue
        p = out_dir / f"thumb_{tag}.jpg"
        p.write_bytes(data)
        rec = {"tag": tag, "file": p.name, "bytes": len(data)}
        try:
            from PIL import Image
            with Image.open(p) as im:
                rec["size"] = list(im.size)
            if main_size:
                ar_main = main_size[0] / main_size[1]
                ar_t = rec["size"][0] / rec["size"][1]
                if abs(ar_main - ar_t) > 0.03 and abs(ar_main - 1 / ar_t) > 0.03:
                    rec["note"] = ("aspect ratio differs from the main image: the main image was cropped or edited after capture; "
                                   "this preview may show the original framing — open it")
        except Exception:  # noqa: BLE001
            pass
        res.append(rec)
    return res


def extract_motion(path: Path, out_dir: Path) -> list[dict]:
    """Pull the embedded video out of a motion photo (Google/Samsung/Pixel JPEGs carry an MP4 after the still): more
    frames and slightly different angles than the single frame, and it is not always stripped on sharing."""
    res = []
    if shutil.which("exiftool"):
        for tag in ("EmbeddedVideoFile", "MotionPhotoVideo", "MicroVideo", "EmbeddedVideo"):
            r = subprocess.run(["exiftool", "-b", f"-{tag}", str(path)], capture_output=True)
            if len(r.stdout) > 2000:
                p = out_dir / f"motion_{tag}.mp4"
                p.write_bytes(r.stdout)
                res.append({"tag": tag, "file": p.name, "bytes": len(r.stdout),
                            "note": "embedded video — extract frames with ffmpeg and run recon on the clearest"})
                return res
    data = path.read_bytes()                                   # byte-scan: an MP4 'ftyp' box appended after the primary image
    i = data.find(b"ftyp")
    while i != -1:
        start = i - 4
        if start > 1000 and int.from_bytes(data[start:start + 4], "big") >= 8 and data[i + 4:i + 8].isalnum():
            mp4 = data[start:]
            if len(mp4) > 2000:
                p = out_dir / "motion_trailer.mp4"
                p.write_bytes(mp4)
                res.append({"tag": "trailer-scan", "file": p.name, "bytes": len(mp4), "offset": start,
                            "note": "video appended after the image — extract frames with ffmpeg and run recon on the clearest"})
                break
        i = data.find(b"ftyp", i + 4)
    return res


# ------------------------------------------------------------------ digest

def digest(path: Path, raw: dict) -> dict:
    d: dict = {"file": path.name, "bytes": path.stat().st_size,
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    d["image"] = jpeg_info(path)
    # filename
    fn = []
    for rx, label in FILENAME_PATTERNS:
        m = re.search(rx, path.name, re.I)
        if m:
            rec = {"pattern": label}
            if m.groups() and m.group(1) and m.group(1).isdigit() and len(m.group(1)) == 13:
                rec["epoch_ms_utc"] = datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).isoformat()
            elif m.groups() and m.group(1) and "screenshot" in label.lower():
                rec["app"] = m.group(1)
            fn.append(rec)
    for rx, lang in SCREENSHOT_LANG:
        if re.search(rx, path.name):
            fn.append({"pattern": f"screenshot named in the OS language “{lang}” (device language, a weak country hint)"})
    d["filename_hints"] = fn
    # camera
    cam = {}
    for k in ("Make", "Model", "LensModel", "Software", "HostComputer", "CreatorTool", "HistorySoftwareAgent"):
        v, _ = find(raw, k)
        if v:
            cam[k] = str(v)
    d["camera"] = cam
    # GPS
    gps = {}
    lat, klat = find(raw, "GPSLatitude")
    lon, _ = find(raw, "GPSLongitude")
    if lat is None:
        pos, _ = find(raw, "GPSPosition", "GPSCoordinates", "Location", "LocationISO6709")
        if pos:
            m = re.findall(r"[+-]?\d+(?:\.\d+)?", str(pos))
            if len(m) >= 2:
                lat, lon = float(m[0]), float(m[1])
    if lat is not None and lon is not None:
        try:
            lat, lon = float(lat), float(lon)
            ref_lat, _ = find(raw, "GPSLatitudeRef")
            ref_lon, _ = find(raw, "GPSLongitudeRef")
            if str(ref_lat).upper().startswith("S") and lat > 0:
                lat = -lat
            if str(ref_lon).upper().startswith("W") and lon > 0:
                lon = -lon
            if not (lat == 0 and lon == 0):
                gps = {"lat": round(lat, 7), "lon": round(lon, 7), "source_tag": klat or "position"}
        except (TypeError, ValueError):
            pass
    for k, name in (("GPSAltitude", "altitude_m"), ("GPSImgDirection", "image_direction_deg"),
                    ("GPSImgDirectionRef", "direction_ref"), ("GPSHPositioningError", "h_error_m"),
                    ("GPSSpeed", "speed"), ("GPSProcessingMethod", "method"), ("GPSDestBearing", "dest_bearing_deg"),
                    ("AbsoluteAltitude", "dji_absolute_altitude_m"), ("RelativeAltitude", "dji_relative_altitude_m"),
                    ("GimbalYawDegree", "dji_gimbal_yaw_deg"), ("GimbalPitchDegree", "dji_gimbal_pitch_deg"),
                    ("FlightYawDegree", "dji_flight_yaw_deg"), ("CameraElevationAngle", "camera_elevation_deg")):
        v, _ = find(raw, k)
        if v not in (None, ""):
            gps[name] = v
    if gps.get("lat") is not None and not geo._out_of_china(gps["lat"], gps["lon"]):
        gps["gcj02"] = [round(x, 7) for x in geo.convert(gps["lat"], gps["lon"], "wgs", "gcj")]   # Amap / Tencent / Baidu input
    d["gps"] = gps
    # optics: feed focal_35mm to geo.py range / terrain.py instead of guessing the zoom
    opt = {}
    fl, _ = find(raw, "FocalLength")
    f35, k35 = find(raw, "FocalLengthIn35mmFormat", "FocalLengthIn35mmFilm", "FocalLength35efl")
    try:
        if fl is not None:
            opt["focal_mm"] = round(float(str(fl).split()[0]), 2)
        if f35 is not None and float(str(f35).split()[0]) > 0:
            opt["focal_35mm"] = round(float(str(f35).split()[0]), 1)
            opt["focal_35mm_source"] = k35
            lf, sf = geo.fov_from_equiv_focal(opt["focal_35mm"])
            opt["fov_4x3_long_short_deg"] = [round(lf, 1), round(sf, 1)]
    except (TypeError, ValueError):
        pass
    d["optics"] = opt
    # time
    t = {}
    for k in ("DateTimeOriginal", "CreateDate", "ModifyDate", "OffsetTimeOriginal", "OffsetTime", "OffsetTimeDigitized",
              "SubSecTimeOriginal", "GPSDateStamp", "GPSTimeStamp", "GPSDateTime", "DateCreated", "CreationDate",
              "MediaCreateDate", "TimeZone", "TimeZoneOffset", "TimeZoneCity", "DaylightSavings"):
        v, _ = find(raw, k)
        if v not in (None, ""):
            t[k] = str(v)
    # Videos: Keys CreationDate carries its UTC offset; the movie-header CreateDate has none and its zone depends on the camera.
    quicktime = path.suffix.lower() in _VIDEO_EXT or "QuickTime:CreateDate" in raw
    order = (("DateTimeOriginal", "CreationDate", "CreateDate", "DateCreated") if quicktime
             else ("DateTimeOriginal", "CreateDate", "DateCreated", "CreationDate"))
    used = next((k for k in order if t.get(k)), None)
    container = quicktime and used == "CreateDate"
    local = parse_dt(t[used]) if used else None
    offset = parse_offset(t.get("OffsetTimeOriginal") or t.get("OffsetTime"))
    how = "OffsetTime tag" if offset is not None else None
    if offset is None and local is not None and local.tzinfo is not None:
        offset, how = int(local.utcoffset().total_seconds() // 60), "offset inside the date string"
    if offset is None and local is not None and t.get("GPSDateTime"):
        utc = parse_dt(t["GPSDateTime"])
        if utc is not None:
            delta = (local.replace(tzinfo=None) - utc.replace(tzinfo=None)).total_seconds() / 60
            rounded = int(round(delta / 15.0) * 15)
            # container time equal to GPS UTC is a UTC container or a UTC+0 clock: undecidable, so no offset
            if abs(delta - rounded) <= 3 and abs(rounded) <= 14 * 60 and not (container and rounded == 0):
                offset, how = rounded, ("container time minus GPS UTC time (the camera clock ran on local time)" if container
                                        else "local capture time minus GPS UTC time")
    if container and offset is None and local is not None:
        t["clock"] = CONTAINER_CLOCK
    if offset is not None:
        cc_zones = countries_for_offset(offset, local)
        sign = "+" if offset >= 0 else "-"
        t["utc_offset"] = f"{sign}{abs(offset) // 60:02d}:{abs(offset) % 60:02d}"
        t["utc_offset_source"] = how
        t["countries_with_this_offset_on_that_date"] = sorted(cc_zones)
        lo, hi = offset / 60 * 15 - 7.5, offset / 60 * 15 + 7.5
        ew = lambda x: f"{abs(x):.1f}°{'E' if x >= 0 else 'W'}"  # noqa: E731
        t["nominal_longitude_band"] = (f"{ew(lo)} to {ew(hi)} "
                                       "(political zones stretch far from this: China, Spain, western Russia, Argentina)")
    d["time"] = t
    # location-ish text and maker-note settings
    d["location_text"] = {k: v for k, v in all_matching(raw, LOCATION_KEY).items()
                          if not k.startswith(("Composite:", "System:")) and "GPS" not in k}
    # editing / provenance
    prov = {}
    for k, v in raw.items():
        tag = k.split(":", 1)[-1]
        if isinstance(v, list) and "DigitalSourceType" in tag:
            v = "; ".join(map(str, v))                          # exiftool: one value per C2PA action
        if PROV_TAG.search(tag) and not isinstance(v, (dict, list)):
            prov[k] = str(v)[:200]
    generated, note = source_type(raw)
    warnings = [note] if note else []
    if generated["term"] is None and (any(k.split(":", 1)[0] in ("JUMBF", "C2PA") for k in raw) or find(raw, "Provenance")[0]):
        prov["C2PA"] = SOURCE_UNREAD                           # a manifest without a readable source type is not a verdict
    generators = sorted({m.group(0) for k, v in prov.items() if re.search(r"Software|CreatorTool", k.split(":", 1)[-1])
                         for m in [AI_GENERATOR.search(v)] if m})
    if generators:
        warnings.append(f"software field names a generative model ({', '.join(generators)})")
    if warnings:
        prov["WARNING"] = "; ".join(warnings)
    prov["generated"] = generated
    d["provenance"] = prov
    d["has_exif"] = any(k.startswith(("ExifIFD:", "IFD0:", "GPS:")) for k in raw)
    return d


def to_md(d: dict, previews: list[dict]) -> str:
    L = [f"# Metadata: {d['file']}", ""]
    if d.get("notice"):
        L += [f"Notice: {d['notice']}.", ""]
    L.append("Metadata describes the file, not necessarily the scene: check it against the image; the image wins.")
    L.append("")
    g = d.get("gps") or {}
    if g.get("lat") is not None:
        L.append(f"- **GPS** {g['lat']}, {g['lon']} (tag {g.get('source_tag')})"
                 + (f", error ±{g['h_error_m']} m" if g.get("h_error_m") else "")
                 + (f", image direction {g['image_direction_deg']}° ({g.get('direction_ref', '?')})" if g.get("image_direction_deg") is not None else ""))
        if g.get("gcj02"):
            L.append(f"  GCJ-02 (Amap/Tencent input): {g['gcj02'][0]}, {g['gcj02'][1]}")
        L.append("  Treat as a hypothesis: verify with the scene (street view, satellite) before reporting it.")
    extra = {k: v for k, v in g.items() if k not in ("lat", "lon", "source_tag", "h_error_m", "image_direction_deg", "direction_ref", "gcj02")}
    if extra:
        L.append(f"- GPS/drone extras: {json.dumps(extra, ensure_ascii=False)}")
    if not g:
        L.append("- No GPS.")
    t = d.get("time") or {}
    if t:
        L.append(f"- **Time**: {', '.join(f'{k}={v}' for k, v in t.items() if k not in ('countries_with_this_offset_on_that_date', 'nominal_longitude_band', 'clock'))}")
        if t.get("clock"):
            L.append(f"  CreateDate is {t['clock']}: neither local time nor UTC is proven and the date may shift by one near midnight; "
                     "fix the zone from the sun (sun.py), a clock in the scene or a GPS track.")
        if t.get("countries_with_this_offset_on_that_date"):
            ccs = t["countries_with_this_offset_on_that_date"]
            L.append(f"  UTC offset {t['utc_offset']} ({t['utc_offset_source']}) was used on that date in {len(ccs)} countries/territories: "
                     f"{', '.join(ccs[:60])}{' …' if len(ccs) > 60 else ''}. Nominal longitude band {t['nominal_longitude_band']}.")
            L.append("  Caveat: phones set the offset of the network/home zone; travellers and wrong clocks happen.")
    else:
        L.append("- No capture time.")
    if d.get("camera"):
        L.append(f"- **Camera/software**: {json.dumps(d['camera'], ensure_ascii=False)}")
    o = d.get("optics") or {}
    if o:
        # build each part only when its key exists: an f-string on a missing key raises before the list multiplication can drop it
        parts = []
        if "focal_mm" in o:
            parts.append(f"focal {o['focal_mm']} mm")
        if "focal_35mm" in o:
            parts.append(f"35 mm equivalent {o['focal_35mm']} mm")
        if "fov_4x3_long_short_deg" in o:
            parts.append(f"field of view {o['fov_4x3_long_short_deg'][0]}° x {o['fov_4x3_long_short_deg'][1]}° (4:3, long x short side)")
        L.append("- **Optics**: " + ", ".join(parts))
    if d.get("location_text"):
        L.append(f"- **Location fields / camera zone settings**: {json.dumps(d['location_text'], ensure_ascii=False)[:800]}")
    if d.get("filename_hints"):
        for h in d["filename_hints"]:
            L.append(f"- **Filename**: {h['pattern']}" + (f" (UTC {h['epoch_ms_utc']})" if h.get("epoch_ms_utc") else "")
                     + (f" — app: {h['app']}" if h.get("app") else ""))
    im = d.get("image") or {}
    if im:
        L.append(f"- **Image**: {im.get('format')} {im.get('size')}"
                 + (f", JPEG quality ≈{im['jpeg_quality_estimate']}" if im.get("jpeg_quality_estimate") else "")
                 + (f", subsampling {im['subsampling']}" if im.get("subsampling") else ""))
        for h in im.get("platform_hints", []):
            L.append(f"  - {h}")
    p = d.get("provenance") or {}
    if p.get("WARNING"):
        L.append(f"- **WARNING**: {p['WARNING']}")
    tags = {k: v for k, v in p.items() if k not in ("WARNING", "generated")}
    if tags:
        L.append(f"- Provenance/editing tags: {json.dumps(tags, ensure_ascii=False)[:600]}")
    if previews:
        for pv in previews:
            L.append(f"- Embedded {pv['tag']} {pv.get('size')} → `{pv['file']}`" + (f" — {pv['note']}" if pv.get("note") else ""))
    if not d.get("has_exif"):
        L.append("- No EXIF block: typical of messaging apps, social networks, screenshots and re-saved images. Absence proves nothing.")
    return "\n".join(L) + "\n"


def analyse(path: Path, out_dir: Path | None, no_previews: bool, quiet: bool = False) -> tuple[dict, list[dict], dict]:
    raw = exiftool(path)
    backend = "exiftool"
    if not raw:
        raw, backend = pillow_fallback(path), "pillow (install exiftool for maker notes, XMP, video atoms)"
    d = digest(path, raw)
    d["backend"] = backend
    if backend != "exiftool" and not shutil.which("exiftool"):
        d["notice"] = FALLBACK_NOTICE
    previews = []
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        if not no_previews:
            previews = extract_previews(path, out_dir, d["image"].get("size"))
            motion = extract_motion(path, out_dir)
            if motion:
                d["motion_video"] = motion
                if not quiet:
                    for mv in motion:
                        print(f"motion photo: extracted {mv['file']} ({mv['bytes']} bytes) — {mv['note']}")
        d["previews"] = previews
    return d, previews, raw


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", type=Path, nargs="+", help="photo or video; several only without --out-dir")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--no-previews", action="store_true")
    ap.add_argument("--json", action="store_true", help="print the digest as one compact JSON line per file (no markdown)")
    args = ap.parse_args()
    if args.out_dir and len(args.photo) > 1:
        ap.error("--out-dir takes one photo; run once per photo")
    for photo in args.photo:
        path = photo.expanduser().resolve()
        if args.json:
            try:
                d, _, _ = analyse(path, args.out_dir, args.no_previews, quiet=True)
            except Exception as e:  # noqa: BLE001 - one JSON line per input even when a file fails
                d = {"file": str(photo), "error": str(e)}
            print(json.dumps(d, ensure_ascii=False, default=str))
            continue
        d, previews, raw = analyse(path, args.out_dir, args.no_previews)
        if args.out_dir:
            raw_clean = {k: v for k, v in raw.items() if not SKIP_KEYS.search(k) or k.startswith("File:")}
            (args.out_dir / "meta.json").write_text(json.dumps({"digest": d, "raw": raw_clean}, ensure_ascii=False, indent=1, default=str),
                                                    encoding="utf-8")
        md = to_md(d, previews)
        if args.out_dir:
            (args.out_dir / "meta.md").write_text(md, encoding="utf-8")
        print(md)
        if args.out_dir:
            print(f"-> {args.out_dir / 'meta.md'}, {args.out_dir / 'meta.json'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
