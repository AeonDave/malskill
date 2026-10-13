#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["torch>=2.2", "geocalib @ git+https://github.com/cvg/GeoCalib", "pillow", "numpy"]
# ///
"""Single-image camera calibration: field of view, focal length, roll, pitch and the horizon line.

GeoCalib (ETH Zürich CVG, ECCV 2024, Apache-2.0) estimates the camera intrinsics and the gravity direction from
one photo, with uncertainties. This replaces eyeballing the horizon row and guessing the zoom for the geometry
tools: geo.py range/frame (--hfov), pose.py (init hfov, pitch), terrain.py view/ridge/fit (--hrow, --f0/--f35),
sun.py (shadow and object angles need a level reference).

  calib.py photo.jpg --out calib.json --draw calib.jpg
  calib.py photo.jpg --prior-focal-35mm 26        # EXIF 35 mm-equivalent focal known: fix it, estimate the rest
  calib.py --selftest                              # download the weights (~100 MB)

Output: hfov/vfov (deg), focal (px) and 35 mm-equivalent, roll/pitch (deg, + = camera tilted up), horizon
row at the image centre and the horizon line endpoints, with 1-sigma uncertainties. Uncertain on close-ups,
images without straight lines or a visible ground, fisheye/heavily distorted or cropped-and-rescaled images:
check the drawn horizon against the scene before you feed numbers into other tools.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))      # geolib: device picker, label font, cache dir
warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageOps  # noqa: E402


def device(want: str | None = None):
    # GeoCalib's optimizer uses float64 linear algebra that MPS/XPU do not support; CPU is fast enough (~1 s).
    # --device, else GEOINT_DEVICE (cuda|cpu honoured; mps/xpu fall back to cpu), else cuda → cpu
    from geolib.cli import device as pick
    return pick(allow_mps=False, want=want)


def _f(x) -> float:
    try:
        return float(x.reshape(-1)[0])
    except Exception:  # noqa: BLE001
        return float(x)


def calibrate(path: Path, prior_f35: float | None, dev) -> dict:
    import torch
    from geocalib import GeoCalib
    model = GeoCalib(weights="pinhole").to(dev)
    # orientation fixed first (phones store rotation in EXIF); GeoCalib then sees what a viewer sees
    pil = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    W, H = pil.size
    img = torch.from_numpy(np.asarray(pil).astype(np.float32) / 255.0).permute(2, 0, 1).to(dev)
    priors = {}
    if prior_f35:
        f_px = prior_f35 / 43.2666 * math.hypot(W, H)
        priors["focal"] = torch.tensor(f_px, device=dev)
    res = model.calibrate(img, priors=priors) if priors else model.calibrate(img)
    cam, grav = res["camera"], res["gravity"]
    f = cam.f.reshape(-1).tolist()
    fx = float(f[0])
    c = cam.c.reshape(-1).tolist()
    cx, cy = float(c[0]), float(c[1])
    hfov = math.degrees(_f(cam.hfov))
    vfov = math.degrees(_f(cam.vfov))
    roll, pitch = math.degrees(_f(grav.roll)), math.degrees(_f(grav.pitch))
    g = grav.vec3d.reshape(-1).tolist()
    # horizon: image points whose viewing ray is perpendicular to gravity → line l = K^-T g
    K = np.array([[fx, 0, cx], [0, fx, cy], [0, 0, 1.0]])
    l = np.linalg.inv(K).T @ np.array(g, dtype=float)
    horizon = None
    if abs(l[1]) > 1e-9:
        yl = -(l[0] * 0 + l[2]) / l[1]
        yr = -(l[0] * W + l[2]) / l[1]
        yc = -(l[0] * (W / 2) + l[2]) / l[1]
        horizon = {"left": [0, round(yl, 1)], "right": [W, round(yr, 1)], "row_at_centre": round(yc, 1),
                   "in_frame": bool(0 <= yc <= H)}
    unc = {}
    for k, v in res.items():
        if "uncertainty" in k:
            try:
                val = _f(v)
                unc[k] = round(math.degrees(val), 2) if any(s in k for s in ("roll", "pitch", "fov")) else round(val, 2)
            except Exception:  # noqa: BLE001
                pass
    f35 = fx * 43.2666 / math.hypot(W, H)
    return {"tool": "calib.py", "image": str(path), "size": [W, H], "hfov_deg": round(hfov, 2), "vfov_deg": round(vfov, 2),
            "focal_px": round(fx, 1), "focal_35mm_equiv": round(f35, 1), "principal_point": [round(cx, 1), round(cy, 1)],
            "roll_deg": round(roll, 2), "pitch_deg": round(pitch, 2), "gravity_camera": [round(x, 4) for x in g],
            "horizon": horizon, "uncertainty": unc, "prior_focal_35mm": prior_f35, "device": str(dev),
            "note": "pitch + = camera tilted up (horizon below the centre); roll + = clockwise image rotation as GeoCalib defines it. "
                    "Use hfov for geo.py/pose.py, horizon.row_at_centre for terrain.py --hrow."}


def draw(path: Path, r: dict, out: Path) -> None:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    lw = max(2, W // 400)
    if r["horizon"]:
        d.line([tuple(r["horizon"]["left"]), tuple(r["horizon"]["right"])], fill=(255, 40, 40), width=lw)
    d.line([(W / 2, 0), (W / 2, H)], fill=(80, 200, 255), width=1)
    d.line([(0, H / 2), (W, H / 2)], fill=(80, 200, 255), width=1)
    from geolib.cli import font as _label_font
    f = _label_font(max(14, W // 60))
    u = r["uncertainty"]
    txt = (f"hfov {r['hfov_deg']}° (f35 {r['focal_35mm_equiv']} mm)  pitch {r['pitch_deg']}°  roll {r['roll_deg']}°"
           + (f"  ±pitch {u.get('pitch_uncertainty')}° ±roll {u.get('roll_uncertainty')}°" if u else ""))
    d.rectangle([0, 0, W, max(24, W // 45)], fill=(0, 0, 0))
    d.text((6, 3), txt, fill=(255, 220, 60), font=f)
    im.save(out, quality=90)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", nargs="?")
    ap.add_argument("--out", default="calib.json")
    ap.add_argument("--draw", help="save the photo with the estimated horizon (red) and image centre lines (blue)")
    ap.add_argument("--prior-focal-35mm", type=float, help="35 mm-equivalent focal length from EXIF, if trusted")
    ap.add_argument("--device", default="auto", help="auto, cuda or cpu (auto honours GEOINT_DEVICE)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        from geolib.paths import cache_dir
        tmp = cache_dir("selftest")
        tmp.mkdir(parents=True, exist_ok=True)
        im = Image.new("RGB", (640, 480), (150, 190, 230))
        ImageDraw.Draw(im).rectangle([0, 260, 640, 480], fill=(90, 110, 70))
        im.save(tmp / "calib_selftest.jpg")
        args.photo, args.out = str(tmp / "calib_selftest.jpg"), str(tmp / "calib_selftest.json")
    if not args.photo:
        sys.exit("Give a photo (or --selftest)")
    dev = device(args.device)
    r = calibrate(Path(args.photo), args.prior_focal_35mm, dev)
    Path(args.out).write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    if args.draw:
        draw(Path(args.photo), r, Path(args.draw))
    h = r["horizon"] or {}
    print(f"hfov {r['hfov_deg']}° vfov {r['vfov_deg']}° | focal {r['focal_px']} px (35 mm eq. {r['focal_35mm_equiv']}) | "
          f"pitch {r['pitch_deg']}° roll {r['roll_deg']}° | horizon row at centre {h.get('row_at_centre')} "
          f"({'in frame' if h.get('in_frame') else 'outside the frame'}) | uncertainty {r['uncertainty']}")
    print(f"-> {args.out}" + (f", {args.draw}" if args.draw else ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
