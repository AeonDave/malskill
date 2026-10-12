#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tzdata"]
# ///
"""Check geoint setup without uploading photos.

  uv run scripts/doctor.py                   local tools, data, caches, browser, writable directory
  uv run scripts/doctor.py --network         also run known-answer probes of the core services (sources_check.py subset)
  uv run scripts/doctor.py --models          also load each local model once (downloads ~6.2 GB on first run)
  uv run scripts/doctor.py --json            machine-readable results on stdout

--network runs `sources_check.py --only <core subset>` (full list: uv run scripts/sources_check.py); without uv it
falls back to plain reachability probes. Neither uploads photos nor checks coverage or model inference.
Exit codes: 0 = no failed checks (warnings may remain); 1 = at least one failed check.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geolib.browser import launch_browser  # noqa: E402
from geolib.net import PROXY_HELP, curl_args, resolve_proxy  # noqa: E402
from geolib.paths import DATA_DIR, cache_root  # noqa: E402
import regions  # noqa: E402

# Core probes run by --network (sources_check.py keys); the rest stay in the full sources_check run.
NETWORK_SUBSET = ("nominatim-search", "overpass", "google-sat", "esri", "esri-wayback", "terrarium", "open-meteo",
                  "geonames-info", "gsv-coverage", "osrm-driving")
GEOLIB_MODULES = ("net", "paths", "browser", "cli", "geomath", "coverage", "pano", "streetlevel", "megaloc")
# Known-answer Street View check on the coverage tiles gsv.py uses: the z17 tile at
# Shibuya crossing must list official panoramas. An HTTP 200 alone proves nothing: a changed endpoint still answers.
STREET_VIEW_POINT = (35.6595, 139.7005)

SERVICES = {
    "Baidu image search": "https://graph.baidu.com/pcpage/index?tpl_from=pc",
    "Baidu panoramas": "https://mapsv0.bdimg.com/?qt=qsdata&x=0&y=0",
    "Yandex Images": "https://yandex.com/images/",
    "Google satellite tiles": "https://mt1.google.com/vt/lyrs=s&x=0&y=0&z=0",
    # Street View discovery: coverage tile around Times Square (the old SingleImageSearch endpoint is decommissioned)
    "Google Street View coverage": "https://www.google.com/maps/photometa/ac/v1?pb=!1m1!1smaps_sv.tactile!6m3!1i38598!2i49258!3i17!8b1",
    "Overpass": "https://overpass-api.de/api/status",
    "Nominatim": "https://nominatim.openstreetmap.org/status",
    "Elevation tiles": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/0/0/0.png",
    "GeoNames dumps": "https://download.geonames.org/export/dump/countryInfo.txt",
    "Brand index (jsDelivr)": "https://cdn.jsdelivr.net/npm/name-suggestion-index@8.0.20260918/package.json",
    "Hugging Face": "https://huggingface.co/",
    "GitHub releases (GeoCalib)": "https://github.com/cvg/GeoCalib/releases",
    "Panoramax (OSM France instance)": "https://panoramax.openstreetmap.fr/api/",
    "Esri Wayback (historical imagery)": "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json",
    "EOX Sentinel-2 cloudless": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/0/0/0.jpg",
    "NASA GIBS daily imagery": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-07-16/GoogleMapsCompatible_Level9/0/0/0.jpg",
    "Open-Meteo weather archive": "https://archive-api.open-meteo.com/v1/archive?latitude=0&longitude=0&start_date=2024-07-16&end_date=2024-07-16&hourly=cloud_cover",
    "Socrata open-data catalogue": "https://api.us.socrata.com/api/catalog/v1?q=trees&limit=1",
}
MODEL_CACHES = {
    "StreetCLIP (prior.py)": "models--geolocal--StreetCLIP",
    "CLIP ViT-L/14 (prior.py GeoCLIP backbone)": "models--openai--clip-vit-large-patch14",
    "OWLv2 (detect.py)": "models--google--owlv2-base-patch16-ensemble",
    "MegaLoc (sweep.py, match.py)": "models--gberton--MegaLoc",
}


def check(name: str, status: str, detail: str, fix: str = "") -> dict:
    return {"name": name, "status": status, "detail": detail, "fix": fix}


def probe(item: tuple[str, str], proxy: str | None) -> dict:
    name, url = item
    try:
        result = subprocess.run(
            ["curl", "-q", "-sSL", "--max-time", "12", *curl_args(proxy),
             "-A", "geo-intelligence-doctor/1.0 (+https://github.com/AeonDave/malskill)", "-o", os.devnull, "-w", "%{http_code}", url],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        code = result.stdout.strip()
        if result.returncode:
            return check(name, "FAIL", f"Connection failed (curl exit {result.returncode}).",
                         "Check DNS, TLS certificates and network access.")
        if code.isdigit() and 200 <= int(code) < 400:
            return check(name, "PASS", f"HTTP {code}; reachable (a live operation can still be blocked or rate-limited).")
        return check(name, "WARN", f"HTTP {code}; server reached, but service access was not confirmed.",
                     "Retry later or inspect the service in a browser. HTTP 403/429 may mean a challenge or rate limit.")
    except (OSError, subprocess.TimeoutExpired):
        return check(name, "FAIL", "Probe could not complete within its time limit.", "Check curl and network access, then retry.")


async def browser_check(proxy: str | None) -> dict:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser, name = await launch_browser(p, proxy)
            try:
                page = await browser.new_page()
                await page.goto("about:blank")
                return check("Reverse-search browser", "PASS", f"{name} launched successfully.")
            finally:
                await browser.close()
    except Exception as exc:
        return check("Reverse-search browser", "WARN", str(exc),
                     "Install Chrome or run `uvx playwright install chromium`. Until then, use intake.py --no-rev.")


def diagnose(network: bool, proxy: str | None) -> dict:
    rows = [check("Python", "PASS" if sys.version_info >= (3, 10) else "FAIL",
                  platform.python_version(), "Use Python 3.10 or later." if sys.version_info < (3, 10) else "")]
    for tool in ("uv", "curl"):
        found = (os.environ.get("UV") or shutil.which("uv")) if tool == "uv" else shutil.which(tool)
        try:
            result = subprocess.run([found or tool, "--version"], capture_output=True, timeout=5)
            ok = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
        rows.append(check(tool, "PASS" if ok else "FAIL", "Available." if ok else "Not runnable.",
                          "" if ok else f"Install {tool} and reopen your terminal so it is on PATH."))
    try:
        with tempfile.TemporaryFile(dir=Path.cwd()) as file:
            file.write(b"geoint")
        rows.append(check("Working directory", "PASS", "Writable; reports and .geo-cache can be created here."))
    except OSError:
        rows.append(check("Working directory", "FAIL", "Cannot write here.", "Run from a writable folder."))
    data = DATA_DIR
    names = ("calling_codes", "driving_side", "territories", "countries", "country_names", "plate_codes", "text_signals",
             "streetview_coverage")
    bad = []
    for name in names:
        try:
            json.loads((data / f"{name}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            bad.append(name)
    rows.append(check("Lookup tables", "FAIL" if bad else "PASS", "Missing or invalid: " + ", ".join(bad) if bad else f"All {len(names)} tables are readable.",
                      "Reinstall the complete skill folder (including assets/data/)." if bad else ""))
    # A broken region pack only disables that country's lookups and tips; it never fails the core
    for code, pack in sorted(regions.packs().items()):
        try:
            errs, _ = regions.lint(pack)
        except regions.PACK_ERRORS as exc:
            errs = [str(exc)]
        rows.append(check(f"Region pack {code.lower()}", "WARN" if errs else "PASS",
                          "; ".join(errs[:2]) if errs else f"{pack.get('name', code)}: lookups {', '.join(pack.get('lookups') or {}) or 'none'}.",
                          f"`regions.py lint {code.lower()}` lists every problem; reinstall assets/data/regions/{code.lower()}/ or remove it." if errs else ""))
    route = "configured proxy" if resolve_proxy(proxy) else "direct"
    rows.append(check("Service connection", "PASS", f"Using {route}."))
    rows.append(asyncio.run(browser_check(proxy)))
    rows.append(geolib_check())
    rows.append(tz_check())
    rows.append(ocr_check())
    installers = {"darwin": {"exiftool": "brew install exiftool", "ffmpeg": "brew install ffmpeg"},
                  "win32": {"exiftool": "winget install --id OliverBetz.ExifTool -e", "ffmpeg": "winget install --id Gyan.FFmpeg -e"}}
    for tool, why in (("exiftool", "meta.py falls back to Pillow; maker notes, large previews, QuickTime atoms and full DJI metadata"),
                      ("ffmpeg", "video keyframes for the video branch")):
        ok = bool(shutil.which(tool))
        how = installers.get(sys.platform, {}).get(tool, f"your package manager ({tool})")
        rows.append(check(tool, "PASS" if ok else "WARN", "Available." if ok else f"Missing: {why} will be reduced.",
                          "" if ok else f"Install with `{how}`."))
    cache = cache_root()
    gn = list((cache / "geonames").glob("cities500*.pkl"))
    rows.append(check("GeoNames places", "PASS" if gn else "INFO", "Cached." if gn else "Not downloaded yet (14 MB, fetched on first use).",
                      "" if gn else "uv run scripts/geodata.py fetch"))
    nsi = (cache / "nsi" / "nsi.min.json").exists()
    rows.append(check("Brand index", "PASS" if nsi else "INFO", "Cached." if nsi else "Not downloaded yet (12 MB, fetched on first textgeo.py run)."))
    hf = Path(os.environ.get("HF_HUB_CACHE") or Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub")
    for name, folder in MODEL_CACHES.items():
        ok = (hf / folder).exists()
        rows.append(check(name, "PASS" if ok else "INFO", "Weights cached." if ok else "Downloads on first use.",
                          "" if ok else "uv run scripts/doctor.py --models"))
    gc = (Path(os.environ.get("TORCH_HOME") or Path.home() / ".cache" / "torch") / "hub" / "geocalib" / "pinhole.tar").exists()
    rows.append(check("GeoCalib (calib.py)", "PASS" if gc else "INFO", "Weights cached." if gc else "Downloads on first use (~100 MB)."))
    rows.append(check("Other ML models", "INFO", "match.py (DINOv2/CLIP) and sat_scan.py (CLIP) download weights on first use."))
    if network and shutil.which("curl"):
        known = network_checks(proxy)
        if known is not None:
            rows.extend(known)
        else:
            with ThreadPoolExecutor(max_workers=8) as pool:
                rows.extend(pool.map(lambda item: probe(item, proxy), SERVICES.items()))
            rows.append(street_view_check(proxy))
    else:
        rows.append(check("Network probes", "SKIP", "Run with --network to check service reachability."))
    return {"ok": not any(row["status"] == "FAIL" for row in rows), "connection": route, "checks": rows}


def geolib_check() -> dict:
    here = Path(__file__).resolve().parent / "geolib"
    missing = [m for m in GEOLIB_MODULES if not (here / f"{m}.py").is_file()]
    if missing or not (here / "__init__.py").is_file():
        return check("geolib package", "FAIL", f"Missing modules: {', '.join(missing) or '__init__'}.",
                     "Reinstall the complete skill folder (scripts/geolib/).")
    return check("geolib package", "PASS", "Modules present; assets/data found." if DATA_DIR.is_dir()
                 else "Imported, but assets/data is missing.")


def tz_check() -> dict:
    """meta.py's UTC-offset -> countries step needs the IANA zone table (tzdata wheel on Windows)."""
    try:
        from datetime import datetime
        import meta
        if meta._zone_tab_text() is None:
            raise LookupError("no zone1970.tab")
        if "PT" not in meta.countries_for_offset(60, datetime(2024, 7, 12, 10)):
            raise LookupError("DST-aware lookup returned no Portugal for +01:00 in July")
        return check("Time zones (tzdata)", "PASS", "IANA zone table found; DST-aware offset lookups work.")
    except Exception as exc:  # noqa: BLE001
        return check("Time zones (tzdata)", "WARN", f"Offset-to-country lookups unavailable ({exc}).",
                     "meta.py and sun.py declare tzdata; run them with `uv run` so it is installed.")


def ocr_check() -> dict:
    if sys.platform == "darwin":
        return check("OCR", "INFO", "Apple Vision preferred; RapidOCR fallback.",
                     "uv run scripts/ocr.py <photo> tests recognition.")
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        return check("OCR (RapidOCR)", "WARN", "uv not found, cannot check RapidOCR.", "Install uv.")
    try:
        r = subprocess.run([uv, "run", "--offline", "--no-project", "-q", "--with", "rapidocr-onnxruntime", "python", "-c",
                            "from rapidocr_onnxruntime import RapidOCR"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return check("OCR (RapidOCR)", "INFO", "Could not check the uv cache in time.", "uv run scripts/ocr.py <photo>")
    if r.returncode == 0:
        return check("OCR (RapidOCR)", "PASS", "RapidOCR is cached and imports on this platform.")
    return check("OCR (RapidOCR)", "INFO", "Not cached yet: the first ocr.py run downloads RapidOCR + onnxruntime (~100 MB).",
                 "uv run scripts/ocr.py <photo> (needs network once)")


def street_view_check(proxy: str | None) -> dict:
    """Coverage tile at a covered point must list official panoramas (what gsv.py near/area/targets rely on)."""
    from geolib import coverage
    from geolib.geomath import tile_xy
    name = "Google Street View coverage"
    try:
        with tempfile.TemporaryDirectory() as d:
            panos = coverage.tile_panos(*tile_xy(*STREET_VIEW_POINT), proxy, Path(d))
    except coverage.ServiceError as exc:
        return check(name, "FAIL", f"Coverage lookup failed: {str(exc)[:160]}",
                     "gsv.py near/area/targets won't work; if the reply layout changed, geolib/coverage.py needs updating.")
    if not panos:
        return check(name, "FAIL", "A covered test tile came back empty: the reply layout may have changed.",
                     "gsv.py near/area/targets would report no coverage everywhere; geolib/coverage.py needs updating.")
    return check(name, "PASS", f"{len(panos)} official panoramas in the test tile.")


def network_checks(proxy: str | None) -> list[dict] | None:
    """Known-answer probes from sources_check.py; None when it cannot run (then plain reachability probes are used)."""
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        return None
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "sources.json"
        cmd = [uv, "run", "-q", str(Path(__file__).resolve().parent / "sources_check.py"), "--only", ",".join(NETWORK_SUBSET),
               "--timeout", "15", "--no-models", "--json", str(out)] + (["--proxy", proxy] if proxy else [])
        try:
            subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            results = json.loads(out.read_text(encoding="utf-8"))["results"]
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            return None
    rows = []
    for r in results:
        status = r["status"] if r["status"] != "FAIL" else ("WARN" if r["optional"] else "FAIL")
        rows.append(check(r["source"], status, f"{r['detail']} ({r['ms']} ms)",
                          "" if status == "PASS" else "Retry later; run sources_check.py for every source and alternates."))
    return rows


def model_checks() -> list[dict]:
    """Load each local model once on a synthetic image (downloads weights the first time)."""
    here = Path(__file__).resolve().parent
    uv = os.environ.get("UV") or shutil.which("uv") or "uv"
    rows = []
    for name, script in (("prior.py models", "prior.py"), ("detect.py model", "detect.py"), ("calib.py model", "calib.py"),
                         ("sweep.py MegaLoc", "sweep.py")):
        try:
            r = subprocess.run([uv, "run", "-q", str(here / script), "--selftest"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=3600)
            ok = r.returncode == 0
            rows.append(check(name, "PASS" if ok else "FAIL", "Loaded and ran on a synthetic image." if ok else (r.stderr or r.stdout)[-300:],
                              "" if ok else "Check disk space and network, then rerun with --models."))
        except subprocess.TimeoutExpired:
            rows.append(check(name, "FAIL", "Timed out after an hour.", "Download the weights on a faster connection."))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", action="store_true", help="probe public endpoints without uploading photos")
    parser.add_argument("--proxy", help=PROXY_HELP)
    parser.add_argument("--json", action="store_true", help="print JSON for issue reports or automation")
    parser.add_argument("--models", action="store_true", help="load every local model once (downloads weights on first run)")
    args = parser.parse_args()
    report = diagnose(args.network, args.proxy)
    if args.models:
        report["checks"].extend(model_checks())
        report["ok"] = not any(row["status"] == "FAIL" for row in report["checks"])
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for row in report["checks"]:
            print(f"[{row['status']}] {row['name']}: {row['detail']}")
            if row["fix"]:
                print(f"  Next: {row['fix']}")
        print("\nNo failed checks. Review warnings before using optional features." if report["ok"] else "\nSome checks failed. Follow the suggested fixes and rerun doctor.py.")
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
