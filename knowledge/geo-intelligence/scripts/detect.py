#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["torch>=2.2", "transformers>=4.40,<6", "pillow", "numpy", "scipy"]
# ///
"""Find and crop every small object that carries location evidence, so nothing gets missed.

Open-vocabulary detection (OWLv2, google/owlv2-base-patch16-ensemble, Apache-2.0) over the whole image and
overlapping tiles, for: text signs, street-name signs, road signs, licence plates, utility poles, bollards,
guardrails, road markings, kilometre markers, traffic lights, shop fronts, flags, vehicles (buses, taxis,
trucks), mailboxes, fire hydrants, bus stops, house numbers, satellite dishes, power-line towers.
Each hit is saved as an upscaled crop (detect/<class>_<n>.jpg), plus a numbered contact sheet and JSON.

  detect.py photo.jpg --out-dir detect/                 → detect.json, detect_sheet.jpg, crops
  detect.py photo.jpg --out-dir detect/ --classes "a mailbox,a road sign" --threshold 0.12
  detect.py --selftest                                  # load the model (pre-download, ~600 MB)

Then open the sheet, zoom into the crops that matter, read text with ocr.py / textgeo.py, and describe
bollards, poles, plates and paint against references/world/. A detector score is not evidence; what you
see in the crop is.
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
from PIL import Image, ImageDraw, ImageOps  # noqa: E402

from geolib.accel import handoff  # noqa: E402

MODEL = "google/owlv2-base-patch16-ensemble"
CLASSES = {
    "sign": ["a sign with text", "a shop sign", "a billboard"],
    "street-sign": ["a street name sign"],
    "road-sign": ["a traffic sign", "a directional road sign", "a highway sign"],
    "plate": ["a car license plate"],
    "pole": ["a utility pole", "a wooden electricity pole", "a concrete pole"],
    "bollard": ["a roadside bollard", "a delineator post"],
    "guardrail": ["a guardrail"],
    "marking": ["a road marking line", "a pedestrian crossing"],
    "km-marker": ["a kilometer marker stone"],
    "traffic-light": ["a traffic light"],
    "storefront": ["a storefront"],
    "flag": ["a flag"],
    "bus": ["a bus"], "taxi": ["a taxi"], "truck": ["a truck"],
    "mailbox": ["a mailbox", "a post box"],
    "hydrant": ["a fire hydrant"],
    "bus-stop": ["a bus stop"],
    "house-number": ["a house number plate"],
    "dish": ["a satellite dish"],
    "pylon": ["a power line tower"],
}


def device(want: str | None = None):
    from geolib.cli import device as pick
    return pick(want=want)              # --device, else GEOINT_DEVICE, else cuda → xpu → mps → cpu


def tiles(W: int, H: int, grid: int, overlap: float = 0.2) -> list[tuple[int, int, int, int]]:
    out = [(0, 0, W, H)]
    if grid <= 1:
        return out
    tw, th = W / grid, H / grid
    for i in range(grid):
        for j in range(grid):
            x0 = max(0, int(j * tw - tw * overlap))
            y0 = max(0, int(i * th - th * overlap))
            x1 = min(W, int((j + 1) * tw + tw * overlap))
            y1 = min(H, int((i + 1) * th + th * overlap))
            out.append((x0, y0, x1, y1))
    return out


def iou(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def nms(dets: list[dict], thr: float = 0.45, cross_thr: float = 0.6) -> list[dict]:
    """Per-class suppression, then cross-class: one object found by two prompts keeps the better label
    (the other label is kept as `also`)."""
    keep: list[dict] = []
    for d in sorted(dets, key=lambda d: -d["score"]):
        same = [k for k in keep if k["cls"] == d["cls"] and iou(k["box"], d["box"]) > thr]
        other = [k for k in keep if k["cls"] != d["cls"] and iou(k["box"], d["box"]) > cross_thr]
        if same:
            continue
        if other:
            other[0].setdefault("also", [])
            if d["cls"] not in other[0]["also"]:
                other[0]["also"].append(d["cls"])
            continue
        keep.append(d)
    return keep


class Detector:
    def __init__(self, dev):
        import torch
        from transformers import Owlv2ForObjectDetection, Owlv2Processor
        self.torch = torch
        self.dev = dev
        self.proc = Owlv2Processor.from_pretrained(MODEL)
        self.model = Owlv2ForObjectDetection.from_pretrained(MODEL).to(dev).eval()

    def run(self, im: Image.Image, prompts: list[str], threshold: float) -> list[tuple[int, float, list[float]]]:
        t = self.torch
        inputs = self.proc(text=[prompts], images=im, return_tensors="pt")
        inputs = {k: v.to(self.dev) for k, v in inputs.items()}
        with t.no_grad():
            out = self.model(**inputs)
        # OWLv2 pads the image to a square; boxes come back relative to the padded square
        side = max(im.size)
        target = t.tensor([[side, side]], device=self.dev)
        try:
            res = self.proc.post_process_object_detection(outputs=out, threshold=threshold, target_sizes=target)[0]
        except AttributeError:
            res = self.proc.post_process_grounded_object_detection(outputs=out, threshold=threshold, target_sizes=target)[0]
        labels = res.get("labels", res.get("text_labels"))
        return [(int(l), float(s), [float(v) for v in b]) for l, s, b in zip(labels.tolist(), res["scores"].tolist(), res["boxes"].tolist())]


def main() -> None:
    handoff(__file__)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", nargs="?")
    ap.add_argument("--out-dir", default="detect")
    ap.add_argument("--classes", help="comma list of custom prompts instead of the built-in set")
    ap.add_argument("--threshold", type=float, default=0.2)
    ap.add_argument("--grid", type=int, default=2, help="also run on grid×grid overlapping tiles (small, distant objects)")
    ap.add_argument("--max-per-class", type=int, default=6)
    ap.add_argument("--min-px", type=int, default=12, help="ignore boxes smaller than this")
    ap.add_argument("--crop-min", type=int, default=384, help="crops are upscaled so the long side is at least this")
    ap.add_argument("--device", default="auto", help="auto, cuda, xpu, mps or cpu (auto honours GEOINT_DEVICE)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        from geolib.paths import cache_dir
        tmp = cache_dir("selftest")
        tmp.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (640, 480), (120, 130, 140)).save(tmp / "detect_selftest.jpg")
        args.photo, args.out_dir = str(tmp / "detect_selftest.jpg"), str(tmp / "detect")
    if not args.photo:
        sys.exit("Give a photo (or --selftest)")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(args.photo)).convert("RGB")
    W, H = im.size
    if args.classes:
        mapping = {c.strip(): [c.strip()] for c in args.classes.split(",") if c.strip()}
    else:
        mapping = CLASSES
    prompts, owner = [], []
    for cls, ps in mapping.items():
        for pr in ps:
            prompts.append(pr)
            owner.append(cls)
    det = Detector(device(args.device))
    dets = []
    for (x0, y0, x1, y1) in tiles(W, H, args.grid):
        sub = im.crop((x0, y0, x1, y1))
        for li, score, (bx0, by0, bx1, by1) in det.run(sub, prompts, args.threshold):
            box = [max(0, x0 + bx0), max(0, y0 + by0), min(W, x0 + bx1), min(H, y0 + by1)]
            if box[2] - box[0] < args.min_px or box[3] - box[1] < args.min_px:
                continue
            if (box[2] - box[0]) * (box[3] - box[1]) > 0.6 * W * H:
                continue
            dets.append({"cls": owner[li], "prompt": prompts[li], "score": round(score, 3), "box": [int(v) for v in box],
                         "tile": [x0, y0, x1, y1]})
    dets = nms(dets)
    by_cls: dict[str, list[dict]] = {}
    for d in dets:
        by_cls.setdefault(d["cls"], [])
        if len(by_cls[d["cls"]]) < args.max_per_class:
            by_cls[d["cls"]].append(d)
    kept = [d for v in by_cls.values() for d in v]
    kept.sort(key=lambda d: (-d["score"]))
    for i, d in enumerate(kept, 1):
        x0, y0, x1, y1 = d["box"]
        pw, ph = int((x1 - x0) * 0.15) + 4, int((y1 - y0) * 0.15) + 4
        c = im.crop((max(0, x0 - pw), max(0, y0 - ph), min(W, x1 + pw), min(H, y1 + ph)))
        s = max(1.0, args.crop_min / max(c.size))
        if s > 1:
            c = c.resize((int(c.size[0] * s), int(c.size[1] * s)), Image.LANCZOS)
        name = f"{i:02d}_{d['cls']}.jpg"
        c.save(out / name, quality=92)
        d["crop"] = name
        d["id"] = i
    # annotated overview + contact sheet
    ov = im.copy()
    dr = ImageDraw.Draw(ov)
    from geolib.cli import font as _label_font
    f = _label_font(max(14, W // 90))
    for d in kept:
        dr.rectangle(d["box"], outline=(255, 210, 0), width=max(2, W // 600))
        dr.text((d["box"][0] + 2, max(0, d["box"][1] - 18)), f"{d['id']} {d['cls']}", fill=(255, 210, 0), font=f)
    ov.save(out / "detect_overview.jpg", quality=88)
    cell = 240
    cols = 5
    rows = max(1, math.ceil(len(kept) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 20)), (15, 15, 15))
    ds = ImageDraw.Draw(sheet)
    for k, d in enumerate(kept):
        c = Image.open(out / d["crop"])
        c.thumbnail((cell, cell))
        x, y = (k % cols) * cell, (k // cols) * (cell + 20)
        sheet.paste(c, (x + (cell - c.size[0]) // 2, y + 20 + (cell - c.size[1]) // 2))
        ds.text((x + 4, y + 2), f"{d['id']} {d['cls']} {d['score']:.2f}", fill="yellow", font=f)
    sheet.save(out / "detect_sheet.jpg", quality=88)
    (out / "detect.json").write_text(json.dumps({"tool": "detect.py", "model": MODEL, "image": args.photo, "size": [W, H],
                                                "threshold": args.threshold, "detections": kept}, indent=1, ensure_ascii=False), encoding="utf-8")
    counts = {k: len(v) for k, v in by_cls.items()}
    print(f"{len(kept)} detections: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    print(f"-> {out / 'detect_sheet.jpg'} (numbered crops), {out / 'detect_overview.jpg'}, {out / 'detect.json'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
