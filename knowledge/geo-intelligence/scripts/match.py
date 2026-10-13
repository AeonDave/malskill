#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "torch", "torchvision", "transformers", "opencv-python-headless", "socksio", "pysocks", "requests", "streetlevel", "huggingface_hub", "safetensors"]
# ///
"""Similarity ranking of a photo against a batch of candidate real-scene images (street-view renders, satellite thumbnails, reference images): the machine ranks first, you look only at the top few.

Uses:
- Street-view confirmation: with dozens to hundreds of candidate panorama points, sort by similarity first and open only the top 10 to compare invariant features.
- Satellite thumbnails: compare the top-down views of candidate points with the top-down features visible in the photo (weaker than street view; coarse ranking only).
- Reference library: compare reference images of bus liveries, streetlight styles, etc. with crops of the photo.

  rank    score and rank the candidates, output ranked.json + contact sheet of the top N
  index   save embeddings of a batch of images to disk (reused repeatedly within the same city)

Candidate source, pick one of three:
  --images <dir or glob>                          existing images, file name is the id
  --items <.index.json> --render baidu|gsv      index written by baidu_pano.py sheet/sample or gsv.py sheet/targets, rendered item by item (--within needs their wgs: not in baidu_pano.py sheet)
  --panos panos.json --toward lat,lon | --headings 0,60,…   output of gsv.py area or baidu_pano.py scan, rendered by heading (can add --within, --spread)

Scoring:
  global descriptor: MegaLoc (default; a visual place-recognition model built for "same place, different day/year/camera"),
  DINOv2 (facebook/dinov2-small, CLS + patch mean) or CLIP (openai/clip-vit-base-patch32) cosine similarity. For street-level
  candidates use megaloc: on a 1990s photo against 2,703 panoramas of 2013 it ranked the true one 1st, dinov2 479th.
  Use dino/clip for satellite thumbnails and object reference libraries;
  --refine sift re-ranks the top --refine-top by SIFT + RANSAC inlier count (only inliers ≥ 15 count as geometric consistency).
  Final order: those with inliers by inlier count, the rest by global score. Scores are only for ordering; whether it is the same place still requires you to compare ≥3 invariant features.

On first use the model downloads from HuggingFace and is cached in ~/.cache/huggingface.

Examples:
  match.py rank --query photo.jpg --panos panos.json --toward <lat,lon> --spread 15 --refine sift --top 10 --out ranked.json --sheet ranked.jpg
  match.py rank --query photo.jpg --query-box 200,100,900,700 --items around.index.json --render baidu --spread-headings -30,0,30 --out r.json --sheet r.jpg
  match.py rank --query photo.jpg --images cands/ --method clip --out r.json
  match.py index --images city_panos/ --out city.npz
"""
from __future__ import annotations

import argparse
from geolib.net import PROXY_HELP, model_proxy_env
import glob
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import geo  # noqa: E402
from geolib.accel import handoff  # noqa: E402
from geolib.coverage import USER_UPLOAD_PREFIXES, official  # noqa: E402

MODELS = {"dino": "facebook/dinov2-small", "clip": "openai/clip-vit-base-patch32", "megaloc": "gberton/MegaLoc"}


IMNET = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
CLIPN = ([0.48145466, 0.4578275, 0.40821073], [0.26862954, 0.26130258, 0.27577711])


def _tensor(ims: list[Image.Image], norm: tuple, torch):
    """PIL 224×224 → (N,3,224,224) normalized tensor. Does its own preprocessing, no torchvision dependency."""
    mean, std = (np.array(v, dtype=np.float32).reshape(1, 3, 1, 1) for v in norm)
    arr = np.stack([np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0 for im in ims]).transpose(0, 3, 1, 2)
    return torch.from_numpy((arr - mean) / std)


def _feat(out):
    """In transformers 5, get_*_features returns BaseModelOutputWithPooling with the projected vector in pooler_output; older versions return the tensor directly."""
    if hasattr(out, "shape"):
        return out
    for k in ("pooler_output", "text_embeds", "image_embeds"):
        v = getattr(out, k, None)
        if v is not None and hasattr(v, "shape"):
            return v
    return out[0]


class Embedder:
    """Global descriptor. dino: DINOv2 CLS + patch mean; clip: image-tower embedding."""

    def __init__(self, method: str):
        import torch
        from geolib.cli import device
        self.method = method
        self.dev = device()
        self.torch = torch
        if method == "megaloc":
            from geolib import megaloc as _megaloc
            self.ml = _megaloc.Embedder(self.dev)
            return
        from transformers import AutoModel, CLIPModel
        t0 = time.time()
        try:
            self.model = (CLIPModel if method == "clip" else AutoModel).from_pretrained(MODELS[method]).to(self.dev).eval()
        except Exception as e:  # noqa: BLE001
            sys.exit(f"failed to load model {MODELS[method]}: {str(e)[:300]}\n"
                     f"check disk space, model availability and `doctor.py --network`.")
        self.torch = torch
        print(f"model {MODELS[method]} ready ({self.dev}, {time.time() - t0:.1f}s)", file=sys.stderr)

    def _views(self, im: Image.Image, multi: bool) -> list[Image.Image]:
        im = im.convert("RGB")
        vs = [im.resize((224, 224), Image.BICUBIC)]
        if multi:
            w, h = im.size
            s = min(w, h)
            vs.append(im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((224, 224), Image.BICUBIC))
            # left and right halves: when the street view and the photo viewpoints are offset, the overlapping half matches better
            vs.append(im.crop((0, 0, int(w * 0.6), h)).resize((224, 224), Image.BICUBIC))
            vs.append(im.crop((int(w * 0.4), 0, w, h)).resize((224, 224), Image.BICUBIC))
        return vs

    def _views_full(self, im: Image.Image, multi: bool) -> list[Image.Image]:
        im = im.convert("RGB")
        if not multi:
            return [im]
        w, h = im.size
        return [im, im.crop((0, 0, int(w * 0.66), int(h * 0.75))), im.crop((int(w * 0.55), 0, w, h))]

    def embed(self, ims: list[Image.Image], multi: bool = False, batch: int = 32) -> np.ndarray:
        """Returns (N, V, D): normalized vectors for the V views of each image."""
        views = [self._views(im, multi) for im in ims]
        flat = [v for vs in views for v in vs]
        if self.method == "megaloc":
            # MegaLoc sees the whole frame at 322x322: give it the uncropped views (not the 224 px squares made above)
            full = [self._views_full(im, multi) for im in ims]
            arr = self.ml.embed([v for vs in full for v in vs])
            return arr.reshape(len(ims), len(full[0]) if full else 1, -1)
        out = []
        with self.torch.no_grad():
            for i in range(0, len(flat), batch):
                chunk = flat[i:i + batch]
                if self.method == "clip":
                    x = _tensor(chunk, CLIPN, self.torch).to(self.dev)
                    f = _feat(self.model.get_image_features(pixel_values=x))
                else:
                    x = _tensor(chunk, IMNET, self.torch).to(self.dev)
                    h = self.model(pixel_values=x).last_hidden_state
                    f = self.torch.cat([h[:, 0], h[:, 1:].mean(1)], dim=1)
                f = f / f.norm(dim=1, keepdim=True)
                out.append(f.float().cpu().numpy())
        arr = np.concatenate(out, 0)
        nv = len(views[0]) if views else 1
        return arr.reshape(len(ims), nv, -1)


def sift_inliers(a: Image.Image, b: Image.Image, max_side: int = 1024) -> tuple[int, int]:
    """Inlier count (and match count) from SIFT + ratio test + RANSAC homography."""
    import cv2

    def prep(im):
        im = im.convert("L")
        s = max_side / max(im.size)
        if s < 1:
            im = im.resize((int(im.width * s), int(im.height * s)), Image.BICUBIC)
        return np.array(im)

    sift = cv2.SIFT_create(nfeatures=3000)
    ka, da = sift.detectAndCompute(prep(a), None)
    kb, db = sift.detectAndCompute(prep(b), None)
    if da is None or db is None or len(ka) < 8 or len(kb) < 8:
        return 0, 0
    m = cv2.BFMatcher().knnMatch(da, db, k=2)
    good = [x[0] for x in m if len(x) == 2 and x[0].distance < 0.75 * x[1].distance]
    if len(good) < 8:
        return 0, len(good)
    pa = np.float32([ka[g.queryIdx].pt for g in good])
    pb = np.float32([kb[g.trainIdx].pt for g in good])
    _, mask = cv2.findHomography(pa, pb, cv2.RANSAC, 6.0)
    return (int(mask.sum()) if mask is not None else 0), len(good)


# ---------------------------------------------------------------- candidate sources

def _image_files(spec: str) -> list[Path]:
    """Image files of a directory (jpg/jpeg then png, sorted) or of a glob pattern."""
    p = Path(spec)
    return sorted(p.glob("*.jp*g")) + sorted(p.glob("*.png")) if p.is_dir() else [Path(x) for x in sorted(glob.glob(spec))]


def _within(args):
    """--within lat,lon,m as ((lat, lon), m), or None."""
    if not args.within:
        return None
    wl, wo, wr = (float(v) for v in args.within.split(","))
    return (wl, wo), wr


def _items_from_panos(args) -> list[dict]:
    import baidu_pano as bp
    panos = json.loads(Path(args.panos).read_text(encoding="utf-8"))
    if within := _within(args):
        panos = {k: v for k, v in panos.items() if geo.distance(within[0], tuple(v["wgs"])) <= within[1]}
    if args.spread:
        panos = bp.thin(panos, args.spread)
    target = tuple(float(v) for v in args.toward.split(",")) if args.toward else None
    items = []
    for pid, v in panos.items():
        heads = [float(x) for x in args.headings.split(",")] if args.headings else (
            [geo.bearing(tuple(v["wgs"]), target) + args.offset] if target else None)
        if heads is None:
            sys.exit("--panos needs --toward or --headings")
        for hd in heads:
            items.append({"id": pid, "heading": hd % 360, "pitch": args.pitch, "fov": args.fov, "wgs": v["wgs"],
                          "road": v.get("road", ""), "date": v.get("date", "")})
    return items


def _render_items(items: list[dict], engine: str, proxy: str | None, cache: Path) -> list[Image.Image | None]:
    if engine == "gsv":
        import gsv
        def one(it):
            try:
                return gsv.render(it["id"], it["heading"], it.get("pitch", 0), it.get("fov", 90), 640, 480, proxy, cache / "gsv")
            except Exception:  # noqa: BLE001
                return None
    else:
        import baidu_pano as bp
        def one(it):
            try:
                return bp.render(it["id"], it["heading"], it.get("pitch", 10), it.get("fov", 80), cache=cache / "pano", proxy=proxy)
            except Exception:  # noqa: BLE001
                return None
    with ThreadPoolExecutor(12) as ex:
        return list(ex.map(one, items))


def _load_candidates(args) -> tuple[list[dict], list[Image.Image]]:
    cache = Path(args.cache)
    if args.images:
        files = _image_files(args.images)
        if not files:
            sys.exit(f"--images has no images: {args.images}")
        items = [{"id": f.stem, "file": str(f)} for f in files]
        return items, [Image.open(f) for f in files]
    within = _within(args)
    if args.items:
        items = json.loads(Path(args.items).read_text(encoding="utf-8"))
        if within:
            if not any(it.get("wgs") for it in items):
                sys.exit(f"{args.items} has no positions (baidu_pano.py sheet writes none): drop --within, or take candidates "
                         "that carry them: baidu_pano.py sample or gsv.py targets (--items), baidu_pano.py scan (--panos)")
            items = [it for it in items if it.get("wgs") and geo.distance(within[0], tuple(it["wgs"])) <= within[1]]
        if args.spread_headings:
            ds = [float(x) for x in args.spread_headings.split(",")]
            items = [dict(it, heading=(it["heading"] + d) % 360) for it in items for d in ds]
    elif args.panos:
        items = _items_from_panos(args)
    else:
        sys.exit("no candidate source; give one of:\n"
                 "  --images cands/                                  existing images, the file name is the id\n"
                 "  --items targets.index.json --render gsv          an index from gsv.py targets/sheet or baidu_pano.py sheet/sample\n"
                 "  --panos panos.json --headings 0,90,180,270       gsv.py area or baidu_pano.py scan output (or --toward lat,lon)\n"
                 "--within lat,lon,m narrows --items and --panos")
    cap = args.max_candidates
    if len(items) > cap:
        centre = (tuple(float(v) for v in args.toward.split(",")), "the --toward target") if args.toward else \
            (within[0], "the --within centre") if within else None
        if centre and all(it.get("wgs") for it in items):
            items.sort(key=lambda it: geo.distance(tuple(it["wgs"]), centre[0]))
            how = f"nearest to {centre[1]} first"
        else:
            how = f"the first {cap} in file order"
        print(f"{len(items)} candidates, above --max-candidates {cap}: scoring {cap}, {how}; {len(items) - cap} not scored. "
              "Narrow first: --within lat,lon,m, fewer --headings / --spread-headings, or split the set and rank each part "
              "(a higher --max-candidates costs memory)", file=sys.stderr, flush=True)
        items = items[:cap]
    if not items:
        sys.exit("no candidates left: widen --within/--spread, or check the index file")
    first = str(items[0].get("id", ""))                # Google ids (official or user upload) render with gsv, the rest with Baidu
    engine = args.render or ("gsv" if official(first) or first.startswith(USER_UPLOAD_PREFIXES) else "baidu")
    ims = _render_items(items, engine, args.proxy, cache)
    # a renderer's grey placeholder (info["failed"]) is no view: ranked, it would pass an outage off as the street check
    ok = [(it, im) for it, im in zip(items, ims) if im is not None and not im.info.get("failed")]
    if len(ok) < len(items):
        cause = next((im.info["failed"] for im in ims if im is not None and im.info.get("failed")), "renderer error")
        if not ok:
            sys.exit(f"every one of the {len(items)} candidates failed to render ({cause}): no ranking written. Check the provider "
                     f"with `sources_check.py --only {engine}`, or render another set (other ids or area)")
        print(f"{len(items) - len(ok)}/{len(items)} candidates failed to render (first: {cause}), dropped; ranking the other "
              f"{len(ok)}", file=sys.stderr)
    return [it for it, _ in ok], [im for _, im in ok]


def _sheet(rows: list[dict], ims: list[Image.Image], out: Path) -> None:
    from geolib.cli import contact_sheet
    cells = []
    for r in rows:
        t = f"#{r['rank']} inliers {r['inliers'] if r['inliers'] is not None else '-'} global {r['score_global']:.3f} …{str(r['id'])[-9:]}"
        if r.get("heading") is not None:
            t += f" h{r['heading']:.0f}"
        cells.append((ims[r["id_key"]], t))
    contact_sheet(cells, out)


def cmd_rank(args) -> None:
    model_proxy_env(args.proxy)
    q = Image.open(args.query)
    if args.query_box:
        x0, y0, x1, y1 = (int(float(v)) for v in args.query_box.split(","))
        q = q.crop((x0, y0, x1, y1))
    items, ims = _load_candidates(args)
    t0 = time.time()
    methods = ["dino", "clip"] if args.method == "both" else [args.method]
    sims = np.zeros(len(ims))
    for m in methods:
        emb = Embedder(m)
        qf = emb.embed([q], multi=True)[0]              # (V, D)
        cf = emb.embed(ims, multi=False)[:, 0]          # (N, D)
        s = (cf @ qf.T).max(axis=1)                     # each candidate takes its max similarity over the query's views
        sims += s / len(methods)
    order = np.argsort(-sims)
    rows = []
    for rk, i in enumerate(order):
        it = items[i]
        rows.append({"rank": rk + 1, "id": it.get("id"), "id_key": i, "file": it.get("file"), "score_global": round(float(sims[i]), 4),
                     "inliers": None, "matches": None, "heading": it.get("heading"), "wgs": it.get("wgs"),
                     "road": it.get("road", ""), "date": it.get("date", ""), "label": it.get("label", "")})
    t1 = time.time()
    if args.refine != "none":
        top = rows[: args.refine_top]
        def one(r):
            return sift_inliers(q, ims[r["id_key"]])
        with ThreadPoolExecutor(4) as ex:
            for r, (inl, mt) in zip(top, ex.map(one, top)):
                r["inliers"], r["matches"] = inl, mt
        rows.sort(key=lambda r: (-(r["inliers"] or 0) if (r["inliers"] or 0) >= args.min_inliers else 0, -r["score_global"]))
        for k, r in enumerate(rows):
            r["rank"] = k + 1
    t2 = time.time()
    out_rows = rows[: args.top]
    print(f"{len(ims)} candidates; global scoring {t1 - t0:.1f}s, refinement {t2 - t1:.1f}s")
    print(f"{'#':>3} {'inliers':>7} {'global':>7}  id / heading / position")
    for r in out_rows:
        pos = f"{r['wgs'][0]:.5f},{r['wgs'][1]:.5f}" if r.get("wgs") else (r.get("file") or "")
        print(f"{r['rank']:>3} {(r['inliers'] if r['inliers'] is not None else '-'):>7} {r['score_global']:>7.3f}  …{str(r['id'])[-10:]}"
              f" h{r['heading']:.0f} {pos} {r.get('road', '')}" if r.get("heading") is not None else
              f"{r['rank']:>3} {(r['inliers'] if r['inliers'] is not None else '-'):>7} {r['score_global']:>7.3f}  {r['id']} {pos}")
    strong = [r for r in out_rows if (r["inliers"] or 0) >= args.min_inliers]
    if args.refine != "none":
        print(f"{len(strong)} with inliers ≥{args.min_inliers}" + (": open these first and compare invariant features" if strong else ": this does not mean none of them is right — with a season change, an old capture, or the photo taken on the sidewalk while the street view is from the middle of the road, the ground truth also often has only single-digit inliers. First open the top 10 in --sheet and compare invariant features; if none match, change heading (--spread-headings) or widen the area"))
        print("note: across years (old prints, decade-old imagery) inlier counts are noise — measured 8–35 for the true panorama and "
              "for look-alikes alike; there, trust the global ranking plus your own comparison of invariant structure")
    if not args.out:                                   # always keep the ranking: the live map and the evidence need it
        args.out = Path(args.sheet).with_name(Path(args.sheet).stem + "_rank.json") if args.sheet else Path(f"rank_{time.strftime('%H%M%S')}.json")
    views_dir = Path(args.out).with_name(Path(args.out).stem + "_views")   # the top views as files: evidence, and the live map shows them
    views_dir.mkdir(parents=True, exist_ok=True)
    for r in out_rows:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(r["id"]))[-24:]
        name = f"{r['rank']:02d}_{safe}" + (f"_h{r['heading']:.0f}" if r.get("heading") is not None else "") + ".jpg"
        try:
            ims[r["id_key"]].convert("RGB").save(views_dir / name, "JPEG", quality=85)
            r["view"] = f"{views_dir.name}/{name}"
        except OSError:
            pass
    Path(args.out).write_text(json.dumps([{k: v for k, v in r.items() if k != "id_key"} for r in rows], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {args.out} (all {len(rows)} rows; top {len(out_rows)} views in {views_dir.name}/)")
    _auto_camera_mark(Path(args.out), out_rows, args)
    if args.sheet:
        _sheet(out_rows, ims, Path(args.sheet))
        print(f"-> {args.sheet}")


STRONG_SCORE, STRONG_INLIERS = 0.30, 15


def _auto_camera_mark(out: Path, rows: list[dict], args) -> None:
    """A strong top match is a camera position: put it on the live map (viewer_marks.json in the session root) with its
    heading and field of view, so the view cone appears without a separate `viewer.py mark camera` call."""
    if not rows:
        return
    top = rows[0]
    strong = (top.get("score_global") or 0) >= STRONG_SCORE or (top.get("inliers") or 0) >= STRONG_INLIERS
    if not strong or not top.get("wgs") or top.get("heading") is None:
        return
    root = next((p for p in (out.resolve().parent, *out.resolve().parents) if (p / "session.json").is_file()), None)
    if root is None:
        return
    marks_file = root / "viewer_marks.json"
    try:
        marks = json.loads(marks_file.read_text(encoding="utf-8-sig")) if marks_file.is_file() else []
        if not isinstance(marks, list):
            marks = []
    except (OSError, ValueError):
        marks = []
    label = f"best match {out.stem} ({top.get('score_global', 0):.2f}, {top.get('inliers') or 0} inliers)"
    marks = [m for m in marks if not (isinstance(m, dict) and m.get("auto") == out.stem)]
    marks.append({"kind": "camera", "lat": top["wgs"][0], "lon": top["wgs"][1], "heading": float(top["heading"]) % 360,
                  "fov": float(getattr(args, "fov", 90) or 90), "label": label, "radius_m": None, "auto": out.stem,
                  "t": time.strftime("%Y-%m-%dT%H:%M:%S")})
    marks_file.write_text(json.dumps(marks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> camera mark on the map: {label} at {top['wgs'][0]:.5f},{top['wgs'][1]:.5f} heading {top['heading']:.0f}° "
          f"(pass --heading {top['heading']:.0f} to finish if this is the shot)")


def cmd_index(args) -> None:
    model_proxy_env(args.proxy)
    files = _image_files(args.images)
    emb = Embedder(args.method)
    feats = emb.embed([Image.open(f) for f in files], multi=False)[:, 0]
    np.savez(args.out, ids=np.array([f.stem for f in files]), files=np.array([str(f) for f in files]), feats=feats, method=args.method)
    print(f"{len(files)} images -> {args.out}")


from geolib.cli import neg_coords as _neg_coords  # noqa: E402  (shared helper)


def main() -> None:
    handoff(__file__)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    ap.add_argument("--cache", type=Path, default=Path(".geo-cache"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("rank")
    r.add_argument("--query", required=True)
    r.add_argument("--query-box", help="x0,y0,x1,y1: compare only this region")
    r.add_argument("--images")
    r.add_argument("--items", help=".index.json from baidu_pano.py / gsv.py")
    r.add_argument("--render", choices=["baidu", "gsv"], help="which engine renders --items; if omitted, guessed from the id format")
    r.add_argument("--spread-headings", help="extra heading offsets for each --items entry, e.g. -30,0,30")
    r.add_argument("--panos", help="output of baidu_pano.py scan")
    r.add_argument("--toward", help="lat,lon")
    r.add_argument("--headings")
    r.add_argument("--offset", type=float, default=0)
    r.add_argument("--within", help="lat,lon,radius in meters: keep the --items / --panos candidates inside")
    r.add_argument("--spread", type=float, help="thinning spacing in meters")
    r.add_argument("--pitch", type=float, default=10)
    r.add_argument("--fov", type=float, default=80)
    r.add_argument("--max-candidates", type=int, default=400)
    r.add_argument("--method", choices=["megaloc", "dino", "clip", "both"], default="megaloc",
                   help="megaloc for street-level candidates (default); dino/clip for satellite thumbnails and objects")
    r.add_argument("--refine", choices=["none", "sift"], default="sift")
    r.add_argument("--refine-top", type=int, default=30)
    r.add_argument("--min-inliers", type=int, default=15)
    r.add_argument("--top", type=int, default=10)
    r.add_argument("--out")
    r.add_argument("--sheet")
    r.add_argument("--proxy", default=argparse.SUPPRESS)
    r.add_argument("--cache", type=Path, default=argparse.SUPPRESS)

    i = sub.add_parser("index")
    i.add_argument("--images", required=True)
    i.add_argument("--method", choices=["megaloc", "dino", "clip"], default="megaloc")
    i.add_argument("--out", required=True)
    i.add_argument("--proxy", default=argparse.SUPPRESS)

    args = ap.parse_args(_neg_coords(sys.argv[1:]))
    if args.cmd == "rank":
        cmd_rank(args)
    else:
        cmd_index(args)


if __name__ == "__main__":
    # Chinese-locale Windows writes GBK by default: m², ñ make it crash, and the Chinese the agent reads comes out garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
