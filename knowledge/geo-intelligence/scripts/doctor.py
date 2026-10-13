#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tzdata"]
# ///
"""Check geoint setup without uploading photos.

  uv run scripts/doctor.py                   local tools, data, caches, browser, writable directory
  uv run scripts/doctor.py --network         also run known-answer probes of the core services (sources_check.py subset)
  uv run scripts/doctor.py --models          also load each local model once (downloads ~6.2 GB on first run)
  uv run scripts/doctor.py --gpu             build the GPU environment the model scripts hand off to (NVIDIA, AMD,
                                             Intel Arc; 1-7 GB download, 4-16 GB on disk, once); --gpu remove
                                             deletes it
  uv run scripts/doctor.py --json            machine-readable results on stdout

--network runs `sources_check.py --only <core subset>` (full list: uv run scripts/sources_check.py); without uv it
falls back to plain reachability probes. Neither uploads photos nor checks coverage or model inference.
Exit codes: 0 = no failed checks (warnings may remain); 1 = at least one failed check.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
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
from geolib import accel  # noqa: E402
from geolib.browser import launch_browser  # noqa: E402
from geolib.net import PROXY_HELP, curl_args, resolve_proxy  # noqa: E402
from geolib.paths import DATA_DIR, cache_root  # noqa: E402
import regions  # noqa: E402

# Core probes run by --network (sources_check.py keys); the rest stay in the full sources_check run.
NETWORK_SUBSET = ("nominatim-search", "overpass", "google-sat", "esri", "esri-wayback", "terrarium", "open-meteo",
                  "geonames-info", "gsv-coverage", "osrm-driving")
GEOLIB_MODULES = ("net", "paths", "browser", "cli", "geomath", "coverage", "pano", "streetlevel", "megaloc", "accel")
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
    "AI-image detector (aidet.py)": "models--Thermostatic--community-forensics-frontier-detector-2026-08",
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
    rows.append(gpu_row(accel.detected(refresh=True)))
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


# Runs in the GPU python: the device exists, float32 kernels match the CPU (TF32 off) and torchvision's ops load,
# which fails when torch and torchvision are not a built pair. It tests the GPU with the most compute units (a Radeon,
# not the Ryzen iGPU next to it) and reports its index for the profile.
SMOKE = """
import json, torch, torchvision
kind = "cuda" if torch.cuda.is_available() else "xpu" if hasattr(torch, "xpu") and torch.xpu.is_available() else None
if kind is None:
    raise SystemExit(f"no GPU device visible to torch {torch.__version__}")
index = 0 if kind == "xpu" else max(range(torch.cuda.device_count()),
                                    key=lambda i: torch.cuda.get_device_properties(i).multi_processor_count)
dev = f"{kind}:{index}"
torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
g = torch.Generator().manual_seed(0)
a, b = torch.randn(256, 256, generator=g) / 16, torch.randn(256, 256, generator=g)
x, w = torch.randn(2, 16, 32, 32, generator=g), torch.randn(16, 16, 3, 3, generator=g) / 12
conv = torch.nn.functional.conv2d
err = {"matmul": (a.to(dev) @ b.to(dev)).cpu().sub(a @ b).abs().max().item(),
       "conv": conv(x.to(dev), w.to(dev), padding=1).cpu().sub(conv(x, w, padding=1)).abs().max().item()}
torchvision.ops.nms(torch.tensor([[0.0, 0, 10, 10], [1, 1, 11, 11]], device=dev), torch.tensor([0.9, 0.8], device=dev), 0.5)
name = (torch.cuda if kind == "cuda" else torch.xpu).get_device_name(index)
print(json.dumps({"device": name, "index": index, "torch": torch.__version__, **err}))
if max(err.values()) > 1e-4:
    raise SystemExit(f"GPU results differ from the CPU: {err}")
"""


# How a GPU run is kept on one device; xpu always tests device 0
VISIBLE = {"cuda": "CUDA_VISIBLE_DEVICES", "rocm": "HIP_VISIBLE_DEVICES"}


def gpu_row(gpu: dict | None, platform: str = sys.platform) -> dict:
    """GPU hardware and the GPU environment's state; INFO only, as the CPU path always works."""
    prof = accel.profile()
    if prof:
        ok = Path(prof.get("python") or "").is_file()
        return check("GPU", "INFO", f"{prof['backend']} environment, torch {prof['torch']}, smoke test passed {prof['created'][:10]}; "
                     + ("prior, detect, match, sweep and sat_scan run there." if ok else "its python is missing."),
                     "" if ok else f"{accel.GPU_CMD} rebuilds it.")
    if platform == "darwin":
        return check("GPU", "INFO", "Apple Silicon: the default environment uses mps.")
    if not gpu:
        return check("GPU", "INFO", "No NVIDIA, AMD or Intel Arc GPU found; the models run on the CPU.")
    name = ", ".join(v for v in (gpu["name"], gpu.get("arch"), gpu.get("driver") and f"driver {gpu['driver']}") if v)
    plan = accel.gpu_plan(platform, gpu)
    if not plan:
        if gpu["vendor"] == "nvidia":
            return check("GPU", "INFO", f"{name}: the default environment uses CUDA.")
        return check("GPU", "INFO", f"{name}: GPU target unknown (clinfo, from the AMD driver, reports it); the models run on the CPU.")
    failed = accel.build_failed()
    if failed:
        return check("GPU", "INFO", f"{name}: the last GPU build failed ({failed}); the models run on the CPU.",
                     f"{accel.GPU_CMD} retries (after a driver update).")
    return check("GPU", "INFO", f"{name}: no GPU environment yet; the models run on the CPU.",
                 f"{accel.GPU_CMD} ({accel.size_note(plan)}, once)")


def _version(py: Path, package: str) -> str:
    return subprocess.run([str(py), "-c", f"import importlib.metadata as m; print(m.version({package!r}))"],
                          capture_output=True, text=True, check=True).stdout.strip()


def _step(cmd: list, env: dict) -> None:
    r = subprocess.run([str(c) for c in cmd], env=env)
    if r.returncode:
        raise RuntimeError(f"{' '.join(str(c) for c in cmd[:3])} … exited {r.returncode}")


def gpu_build() -> int:
    """Build <cache>/gpu/venv with a GPU torch for this machine, pin torch/torchvision, smoke-test it, and only then write
    the profile the model scripts hand off to. A failure writes no profile, so everything stays on the CPU."""
    gpu = accel.detected(refresh=True)
    plan = accel.gpu_plan(sys.platform, gpu)
    if not plan:
        print(gpu_row(gpu, sys.platform)["detail"] + " Nothing to build.")
        return 0
    root = accel.gpu_dir()
    venv, cons, failed = root / "venv", root / "constraints.txt", root / "failed.txt"
    py = accel.venv_python(venv).absolute()
    uv = os.environ.get("UV") or shutil.which("uv") or "uv"
    env = {**os.environ, **plan["env"]}
    print(f"{gpu['name']}: building the {plan['backend']} torch environment in {venv} ({accel.size_note(plan)}, once)",
          flush=True)
    root.mkdir(parents=True, exist_ok=True)
    (root / "profile.json").unlink(missing_ok=True)
    failed.unlink(missing_ok=True)
    pip = [uv, "pip", "install", "--python", py, *plan["args"]]
    try:
        _step([uv, "venv", "--clear", "--managed-python", "--python", "3.12", venv], env)   # a uv-managed Python: a system upgrade cannot break it
        _step([*pip, f"torch{plan['extra']}", "numpy", "pillow"], env)    # torchvision's dependencies as final releases
        torch_v = _version(py, "torch")
        cons.write_text(f"torch=={torch_v}\n", encoding="utf-8")
        _step([*pip, *plan["pre"], "-c", cons, accel.torchvision_spec(torch_v, plan["extra"])], env)
        cons.write_text(f"torch=={torch_v}\ntorchvision=={_version(py, 'torchvision')}\n", encoding="utf-8")
        smoke = subprocess.run([str(py), "-c", SMOKE], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        if smoke.returncode:
            raise RuntimeError("smoke test: " + ((smoke.stderr or smoke.stdout).strip().splitlines() or ["no output"])[-1])
        index = json.loads(smoke.stdout.strip().splitlines()[-1]).get("index")
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        failed.write_text(str(exc), encoding="utf-8")
        print(f"GPU build failed: {exc}. No profile written: the models keep running on the CPU.", file=sys.stderr)
        return 1
    tag = torch_v.partition("+")[2]          # the backend uv chose (cu130, rocm7.2, xpu), fixed for every later sync
    args = [f"--torch-backend={tag}" if a == "--torch-backend=auto" and tag else a for a in plan["args"]]
    visible = {VISIBLE[plan["backend"]]: str(index)} if index else {}    # device 0 needs no restriction
    quiet = {"MIOPEN_LOG_LEVEL": "3"} if plan["backend"] == "rocm" else {}   # MIOpen warns on every run (kernel database, CK library)
    accel.write_json(root / "profile.json", {"backend": plan["backend"], "python": str(py), "uv_args": args, "torch": torch_v,
                                             "env": {**quiet, **visible}, "created": datetime.now().isoformat(timespec="seconds")})
    print(f"Smoke test passed: {smoke.stdout.strip()}\nprior, detect, match, sweep and sat_scan now run on {gpu['name']}; "
          "GEOINT_DEVICE=cpu skips the GPU environment, doctor.py --gpu remove deletes it.")
    return 0


def gpu_remove() -> int:
    root = accel.gpu_dir()
    try:
        shutil.rmtree(root)
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"Could not remove {root}: {exc} (close the scripts that use it).", file=sys.stderr)
        return 1
    print(f"Removed {root}: the models run on the CPU.")
    return 0


def model_checks() -> list[dict]:
    """Load each local model once on a synthetic image (downloads weights the first time)."""
    here = Path(__file__).resolve().parent
    uv = os.environ.get("UV") or shutil.which("uv") or "uv"
    rows = []
    for name, script in (("prior.py models", "prior.py"), ("detect.py model", "detect.py"), ("calib.py model", "calib.py"),
                         ("sweep.py MegaLoc", "sweep.py"), ("aidet.py model", "aidet.py")):
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
    parser.add_argument("--gpu", nargs="?", const="build", choices=("build", "remove"),
                        help="build the GPU environment the model scripts hand off to; `--gpu remove` deletes it")
    args = parser.parse_args()
    if args.gpu:
        sys.exit(gpu_build() if args.gpu == "build" else gpu_remove())
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
