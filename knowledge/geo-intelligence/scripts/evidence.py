#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Make the evidence image: mark the camera position, heading wedge and key features on satellite imagery, with street-view comparison panels below.

Input is a JSON spec file:
{
  "map": "area.jpg",                         # output of tiles.py fetch (needs the same-name .json next to it)
  "crop": [x0, y0, x1, y1],                  # optional, crop in original-image pixels
  "width": 1280,                             # output width
  "camera": [lat, lon],
  "heading": 52, "hfov": 54, "range_m": 560, # heading wedge
  "labels": [{"at": [lat, lon], "text": "Xinghe Twin Towers", "color": "#ffdd55", "dx": 0, "dy": 0}],
  "lines":  [{"from": [lat, lon], "bearing": 47, "length_m": 75, "color": "#00ffff"}],
  "panels": [{"image": "sv1.jpg", "caption": "Street view: same road, looking northeast"}]
}

Example: evidence.py spec.json --out evidence.jpg

With --match, a different proof: two images side by side with colour-coded matching lines (photo vs Street View /
reference), to show the same structure feature by feature (balconies, painted stripes, a roof line). Spec:
{
  "left":  {"image": "photo.jpg", "caption": "photo"},
  "right": {"image": "sv.jpg",    "caption": "Street View, closest capture in time"},
  "pairs": [{"color": "#ff5bbf", "label": "balcony", "a": [x,y], "b": [x,y]}, ...],   # a=left px, b=right px
  "height": 700
}
Example: evidence.py match_spec.json --out match.jpg --match
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import geo  # noqa: E402
from geolib.cli import font  # noqa: E402
from tiles import Mosaic  # noqa: E402


def _path(base: Path, rel: str) -> Path:
    """An image path from a spec: absolute, relative to the spec's folder, or relative to the working directory (the
    session folder, where the workflow writes session-relative paths even when the spec itself sits in evidence/)."""
    p = Path(rel)
    if p.is_absolute():
        return p
    for cand in (base / p, Path.cwd() / p):
        if cand.exists():
            return cand
    raise SystemExit(f"image {rel!r} not found next to the spec ({base}) or in the working directory ({Path.cwd()})")


def _wrap(text: str, font, width: float, max_lines: int = 3) -> list[str]:
    """Greedy word wrap to `width` px; a token wider than the width (CJK with no spaces, a URL) breaks per character."""
    lines, cur = [], ""
    for word in text.split():
        if cur and font.getlength(f"{cur} {word}") <= width:
            cur = f"{cur} {word}"
            continue
        if cur:
            lines.append(cur)
            cur = ""
        for ch in word:
            if cur and font.getlength(cur + ch) > width:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
    lines.append(cur)
    return lines[:max_lines]


def _warn_camera_outside(spec: dict, m: Mosaic, size: tuple[int, int], map_path: Path) -> None:
    """One stderr line when the camera falls outside the final image: the evidence would not show the answer it proves.
    Only the camera is checked: a long-range wedge (a lake, a skyline) may leave the image by design."""
    lat, lon = spec["camera"]
    x, y = m.to_px(lat, lon)
    w, h = size
    if not (0 <= x < w and 0 <= y < h):
        span = math.hypot(x - w / 2, y - h / 2) / 2 + max(size) / 2      # px from the new centre: the camera and the old extent
        dz = 0
        while span / 2 ** dz > 8 * 256 and dz < m.z:                     # over 8 rings (17x17 tiles): zoom out instead
            dz += 1
        rad = max(2, math.ceil(span / 2 ** dz / 256))
        clat, clon = m.to_ll((x + w / 2) / 2, (y + h / 2) / 2)
        src = f" --source {m.meta['source']}" if "source" in m.meta else ""
        crop = '; drop or redo "crop" (pixel coordinates of the old map)' if spec.get("crop") else ""
        print(f"camera {lat:.6f},{lon:.6f} is outside this map (px {x:.0f},{y:.0f} vs box {(0, 0, w, h)}); refetch: tiles.py fetch "
              f"{clat:.6f},{clon:.6f} --zoom {m.z - dz} --radius {rad}{src} --out {map_path}{crop}", file=sys.stderr)
    elif spec.get("crop"):
        x0, y0, x1, y1 = spec["crop"]
        if not (x0 <= x < x1 and y0 <= y < y1):
            print(f"camera {lat:.6f},{lon:.6f} is outside the crop (px {x:.0f},{y:.0f} vs crop {tuple(spec['crop'])}); "
                  "widen or drop \"crop\"", file=sys.stderr)


def build(spec: dict, base: Path, out: Path) -> None:
    map_path = _path(base, spec["map"])
    m = Mosaic(map_path)
    im = Image.open(map_path).convert("RGBA")
    if "camera" in spec:
        _warn_camera_outside(spec, m, im.size, map_path)
    scale_font = max(im.size) / 1400

    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    pts = None
    if "camera" in spec:
        cam = tuple(spec["camera"])
        if "heading" in spec:
            h, fov, rng = spec["heading"], spec.get("hfov", 54), spec.get("range_m", 400)
            pts = [m.to_px(*cam)] + [m.to_px(*geo.dest(cam, h - fov / 2 + k * fov / 24, rng)) for k in range(25)]
            d.polygon(pts, fill=(255, 220, 0, 55), outline=(255, 220, 0, 210))
    for ln in spec.get("lines", []):
        a = m.to_px(*ln["from"])
        b = m.to_px(*geo.dest(tuple(ln["from"]), ln["bearing"], ln["length_m"]))
        d.line([a, b], fill=ln.get("color", "#00ffff"), width=int(8 * scale_font) or 3)
    im = Image.alpha_composite(im, ov).convert("RGB")

    d = ImageDraw.Draw(im)
    f = font(int(42 * scale_font), prefer_wide=True)
    for lb in spec.get("labels", []):
        ax, ay = m.to_px(*lb["at"])
        r = 8 * scale_font
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=lb.get("color", "white"), outline="black")   # anchor point
        x, y = ax + lb.get("dx", 12), ay + lb.get("dy", -12)
        bb = d.textbbox((0, 0), lb["text"], font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = min(max(8, x), im.size[0] - tw - 16)                                                   # stay inside the image edges
        y = min(max(8, y), im.size[1] - th - 16)
        d.rectangle([x - 8, y - 6, x + tw + 8, y + th + 10], fill="black")
        d.text((x, y), lb["text"], font=f, fill=lb.get("color", "white"))
    if "camera" in spec:                                   # camera and wedge outline last: no label may hide the answer
        if pts:
            d.line(pts + [pts[0]], fill=(255, 220, 0), width=3)
        x, y = m.to_px(*spec["camera"])
        r = 18 * scale_font
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 40, 40), outline="white", width=4)

    if spec.get("crop"):
        im = im.crop(tuple(spec["crop"]))
    W = spec.get("width", 1280)
    im = im.resize((W, int(im.size[1] * W / im.size[0])))

    panels = spec.get("panels", [])
    if panels:
        pw = W // len(panels)
        ph = int(pw * 3 / 4)
        cf = font(20, prefer_wide=True)
        lines_per = [_wrap(p.get("caption", ""), cf, pw - 12) for p in panels]   # panel width: no overlap with the neighbour
        cap_h = 10 + 26 * max(len(x) for x in lines_per)
        S = Image.new("RGB", (W, im.size[1] + ph + cap_h), "black")
        S.paste(im, (0, 0))
        d = ImageDraw.Draw(S)
        for k, (p, lines) in enumerate(zip(panels, lines_per)):
            pim = Image.open(_path(base, p["image"])).convert("RGB")
            pim.thumbnail((pw, ph))                        # keep aspect ratio, centered with black borders
            S.paste(pim, (k * pw + (pw - pim.width) // 2, im.size[1] + cap_h + (ph - pim.height) // 2))
            for li, text in enumerate(lines):
                d.text((k * pw + 6, im.size[1] + 6 + 26 * li), text, font=cf, fill="white")
        im = S
    im.save(out, quality=88)



def build_match(spec: dict, base: Path, out: Path) -> None:
    """Two images side by side with colour-coded correspondence lines (the photo vs a Street View / reference): prove the
    same structure with matched features. Each pair draws a dot in its colour on each image and a connector between them,
    so "these balconies, these painted stripes, this roof line are the same" is visible at a glance.

    spec = {"left": {"image": p, "caption": c}, "right": {...},
            "pairs": [{"color": "#ff5bbf", "label": "balcony", "a": [x,y], "b": [x,y]}, ...], "width": 1600}
    a is a pixel in the left image, b a pixel in the right image (original pixels, before scaling)."""
    if not spec.get("pairs"):                              # a match image proves matched features; without pairs it is not a match proof
        raise ValueError("--match needs at least one pair in the spec (a feature seen in both images); for a plain side-by-side "
                         "comparison with no matched features use the evidence spec without --match")

    def load(side):
        im = Image.open(_path(base, side["image"])).convert("RGB")
        return im, im.size
    lim, (lw, lh) = load(spec["left"])
    rim, (rw, rh) = load(spec["right"])
    H = spec.get("height", 700)
    lsc, rsc = H / lh, H / rh
    lim = lim.resize((int(lw * lsc), H)); rim = rim.resize((int(rw * rsc), H))
    gap, cap = 40, 34
    W = lim.width + gap + rim.width
    S = Image.new("RGB", (W, H + cap), (16, 16, 16))
    S.paste(lim, (0, cap)); S.paste(rim, (lim.width + gap, cap))
    d = ImageDraw.Draw(S)
    f = font(22, prefer_wide=True)
    d.text((6, 6), spec["left"].get("caption", "photo"), font=f, fill="white")
    d.text((lim.width + gap + 6, 6), spec["right"].get("caption", "reference"), font=f, fill="white")
    xoff = lim.width + gap
    r = 6
    pts = [(p.get("color", "#ffdd33"), p.get("label"), (p["a"][0] * lsc, p["a"][1] * lsc + cap),
            (p["b"][0] * rsc + xoff, p["b"][1] * rsc + cap)) for p in spec.get("pairs", [])]
    for col, _, a, b in pts:
        d.line([a, b], fill=col, width=2)
    for col, _, a, b in pts:
        for cx, cy in (a, b):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=3)
    lf = font(18, prefer_wide=True)
    for col, label, (ax, ay), _ in pts:                     # labels last, on a dark box, kept inside the left image
        if not label:
            continue
        bb = d.textbbox((0, 0), label, font=lf)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = min(max(4, ax + 10), lim.width - tw - 10)
        y = min(max(cap + 4, ay - th - 14), H + cap - th - 10)
        d.rectangle([x - 4, y - 3, x + tw + 4, y + th + 7], fill=(0, 0, 0))
        d.text((x, y), label, font=lf, fill=col)
    out.parent.mkdir(parents=True, exist_ok=True)
    S.save(out, quality=90)


from geolib.cli import neg_coords as _neg_coords  # noqa: E402  (shared helper)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--match", action="store_true",
                    help="two images + colour-coded matching lines (photo vs reference) instead of the satellite evidence image")
    args = ap.parse_args(_neg_coords(sys.argv[1:]))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    try:
        (build_match if args.match else build)(spec, args.spec.parent, args.out)
    except ValueError as exc:
        sys.exit(f"evidence.py: {exc}")
    print(args.out)


if __name__ == "__main__":
    # Chinese Windows outputs GBK by default: it crashes on m², ñ, and Chinese text the agent reads comes out garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
