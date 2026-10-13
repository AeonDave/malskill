#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["onnxruntime", "numpy", "pillow", "pillow-heif", "huggingface_hub"]
# ///
"""AI-generated-image score of the submitted original: model status, a ranking, never a verdict.

  aidet.py original/photo.jpg --out-dir recon/aidet    → recon/aidet/aidet.json (recon.py runs it in its own lane)
  aidet.py --selftest                                  → download the weights (44 MB, once) and check a fixed fixture score

One whole-image classifier (ViT-S/16 at 384 px, fp16 ONNX, CPU only), pinned by revision hash: short edge 440 (bilinear),
centre crop 384, ImageNet normalisation, one logit; p = sigmoid(logit - 0.7403), flagged at p >= 0.65 (the model card's
calibration). A high score is not proof: real phone HDR and night photos reach 0.99. A low score never clears: re-saved
images and generators newer than the model score low. Only provenance, a confirmed AI-gallery page or the operator decide.
When the model or the image cannot be loaded, aidet.json is {"tool": "aidet.py", "skipped": reason} and the exit code is 0.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

REPO = "Thermostatic/community-forensics-frontier-detector-2026-08"
REVISION = "16db135220b318d811b207db576d90368980b595"
FILE = "community_forensics_frontier_fp16.onnx"
LICENCE = "MIT"
INTERCEPT = -0.7403357915937764          # config.json calibration (bias only): p = sigmoid(logit + intercept)
THRESHOLD = 0.65                         # = raw logit 1.359375
SHORT_EDGE, CROP = 440, 384
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)
# The card names no filter for the short-edge resize; its own evaluation views resize with bilinear, as does the base
# model's pipeline. Bicubic shifts single scores by up to 0.4 on real photos.
INTERPOLATION = "bilinear"
SELFTEST_LOGIT, SELFTEST_TOLERANCE = -2.519, 0.1


def preprocess(img: Image.Image) -> np.ndarray:
    """RGB image → (1, 3, 384, 384) float32, the card's pipeline."""
    img = img.convert("RGB")
    w, h = img.size
    s = SHORT_EDGE / min(w, h)
    img = img.resize((max(CROP, round(w * s)), max(CROP, round(h * s))), Image.BILINEAR)
    w, h = img.size
    left, top = (w - CROP) // 2, (h - CROP) // 2
    a = (np.asarray(img.crop((left, top, left + CROP, top + CROP)), np.float32) / 255.0 - MEAN) / STD
    return a.transpose(2, 0, 1)[None]


def onnx_logit() -> Callable[[np.ndarray], float]:
    """Pinned single-file download (cached after the first run), CPU provider only."""
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    sess = ort.InferenceSession(hf_hub_download(REPO, FILE, revision=REVISION), providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    return lambda x: float(np.ravel(sess.run(None, {name: x})[0])[0])


def skipped(reason: str) -> dict:
    return {"tool": "aidet.py", "skipped": reason[:300]}


def analyse(photo: Path, logit: Callable[[np.ndarray], float] | None = None) -> dict:
    """aidet.json record for one file; any failure is a skip, never a score."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    try:
        with Image.open(photo) as im:
            x = preprocess(im)
    except Exception as e:  # noqa: BLE001 - videos, truncated files, unknown formats
        return skipped(f"image unreadable: {type(e).__name__}: {e}")
    try:
        fn = logit or onnx_logit()
        t0 = time.time()
        z = fn(x)
    except Exception as e:  # noqa: BLE001 - no network on the first run, missing runtime, corrupt cache
        return skipped(f"model unavailable: {type(e).__name__}: {e} (`doctor.py --models` fetches the weights)")
    return {"tool": "aidet.py", "model": REPO, "revision": REVISION, "file": FILE, "licence": LICENCE,
            "p_ai": round(1 / (1 + math.exp(-(z + INTERCEPT))), 4), "raw_logit": round(z, 4), "threshold": THRESHOLD,
            "interpolation": INTERPOLATION, "seconds": round(time.time() - t0, 2)}


def fixture() -> Image.Image:
    """Deterministic 640x480 test card (colour ramps and a checkerboard, no RNG): every machine scores the same pixels."""
    y, x = np.mgrid[0:480, 0:640]
    a = np.stack([x * 255 // 639, y * 255 // 479, ((x // 40 + y // 40) % 2) * 200 + 25], -1).astype(np.uint8)
    return Image.fromarray(a)


def selftest() -> int:
    try:
        z = onnx_logit()(preprocess(fixture()))
    except Exception as e:  # noqa: BLE001
        print(f"aidet selftest: model unavailable: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    ok = abs(z - SELFTEST_LOGIT) <= SELFTEST_TOLERANCE
    print(json.dumps({"selftest": "pass" if ok else "fail", "raw_logit": round(z, 4), "expected": SELFTEST_LOGIT,
                      "tolerance": SELFTEST_TOLERANCE}))
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", nargs="?", type=Path, help="the submitted original (never a crop or a re-save)")
    ap.add_argument("--out-dir", type=Path, help="write aidet.json here")
    ap.add_argument("--selftest", action="store_true", help="download the weights and check a fixed fixture score")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if args.photo is None:
        ap.error("give a photo (or --selftest)")
    rec = analyse(args.photo)
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "aidet.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
