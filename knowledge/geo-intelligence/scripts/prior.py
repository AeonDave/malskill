#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["torch>=2.2", "torchvision", "transformers>=4.40,<6", "geoclip>=1.2,<2", "pillow", "numpy", "safetensors"]
# ///
"""World prior: where on Earth does this image look like? Two learned geolocation models, ranked output.

  StreetCLIP (geolocal/StreetCLIP, CLIP ViT-L/14-336 trained for geolocation; CC BY-NC 4.0): zero-shot over
  ~200 countries, then over the first-level regions of the leading countries.
  GeoCLIP (MIT): image → probability over a gallery of 100k GPS points; top points are clustered and
  labelled with the nearest town (GeoNames).
Both run on several crops of the photo (full frame + left/centre/right squares) and are averaged, so details
at the edges count. Runs locally (Apple MPS / CUDA / CPU). First use downloads ~3.5 GB of weights from
Hugging Face into ~/.cache/huggingface.

  prior.py photo.jpg --out-dir prior/            → prior.json (board-ready signal), prior.md, prior_map.png
  prior.py photo.jpg --out-dir prior/ --models streetclip --labels FR,ES,PT,IT   # only these countries
  prior.py --selftest                            # load both models on a synthetic image (pre-download)

READ THIS BEFORE USING THE OUTPUT: these models are pattern matchers trained on internet and street-level
photos. They are often right about the continent and frequently right about the country, but they are
confidently wrong on unusual scenes, indoor shots, close-ups, deserts/forests/oceans, and anything that
resembles a better-photographed place. The result goes on the board as status "model" (LR capped at 3,
never verified, never excludes). Use it to order the hypotheses you test, not to answer.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geodata  # noqa: E402
from geolib.accel import handoff  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageOps  # noqa: E402

STREETCLIP = "geolocal/StreetCLIP"
TEMPLATES = ["A Street View photo in {}.", "A photo taken in {}."]
# scene tags: one (present, absent) prompt pair per tag, scored independently (a photo can be mountains + water + road)
SCENE_PROMPTS = {
    "mountains": ("a photo with mountains or a rocky ridge on the horizon", "a photo with a flat horizon and no mountains"),
    "water": ("a photo of a lake, a river or the sea", "a photo with no water in it"),
    "coast": ("a photo of a sea coast or a beach", "a photo taken far from the sea"),
    "urban": ("a city street with buildings, shops or traffic", "a natural landscape with no buildings"),
    "road": ("a photo taken on a road or street", "a photo with no road or street"),
    "text": ("a photo with readable signs, text or a licence plate", "a photo with no text, signs or plates"),
    "indoor": ("an indoor photo", "an outdoor photo"),
}


def device(want: str | None = None):
    from geolib.cli import device as pick
    return pick(want=want)              # --device, else GEOINT_DEVICE, else cuda → xpu → mps → cpu


def crops(im: Image.Image) -> list[Image.Image]:
    """Full frame padded to a square + left/centre/right (or top/middle/bottom) squares."""
    im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    side = max(w, h)
    pad = Image.new("RGB", (side, side), (124, 116, 104))
    pad.paste(im, ((side - w) // 2, (side - h) // 2))
    out = [pad]
    s = min(w, h)
    if w > h * 1.15:
        for x in (0, (w - s) // 2, w - s):
            out.append(im.crop((x, 0, x + s, s)))
    elif h > w * 1.15:
        for y in (0, (h - s) // 2, h - s):
            out.append(im.crop((0, y, s, y + s)))
    else:
        out.append(im)
    return out


def label_set(only: list[str] | None) -> list[tuple[str, str]]:
    """(ISO2, English name) of the countries the zero-shot classifier chooses among."""
    C = geodata.countries()
    if only:
        return [(c, C[c]["name"]) for c in only if c in C]
    keep = []
    for cc, c in C.items():
        if c.get("population", 0) >= 30000 or cc in ("FK", "GL", "VA", "SM", "MC", "LI", "AD", "GI"):
            keep.append((cc, c["name"]))
    return sorted(keep, key=lambda x: x[1])


# ------------------------------------------------------------------ StreetCLIP

class StreetCLIPModel:
    def __init__(self, dev: str):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self.torch = torch
        self.dev = dev
        self.model = CLIPModel.from_pretrained(STREETCLIP).to(dev).eval()
        self.proc = CLIPProcessor.from_pretrained(STREETCLIP)

    def image_embedding(self, ims: list[Image.Image]):
        t = self.torch
        with t.no_grad():
            px = self.proc(images=ims, return_tensors="pt")["pixel_values"].to(self.dev)
            f = self.model.get_image_features(pixel_values=px)
            f = getattr(f, "pooler_output", f)
            f = f / f.norm(dim=-1, keepdim=True)
            m = f.mean(dim=0, keepdim=True)
            return m / m.norm(dim=-1, keepdim=True)

    def text_embeddings(self, names: list[str]):
        t = self.torch
        embs = []
        with t.no_grad():
            for tpl in TEMPLATES:
                tok = self.proc(text=[tpl.format(n) for n in names], return_tensors="pt", padding=True, truncation=True)
                tok = {k: v.to(self.dev) for k, v in tok.items() if k in ("input_ids", "attention_mask")}
                f = self.model.get_text_features(**tok)
                f = getattr(f, "pooler_output", f)
                embs.append(f / f.norm(dim=-1, keepdim=True))
            e = t.stack(embs).mean(dim=0)
            return e / e.norm(dim=-1, keepdim=True)

    def scene_tags(self, img_emb) -> dict[str, float]:
        """p(tag present) per SCENE_PROMPTS pair; photo_session.py turns tags into the checks finish requires."""
        t = self.torch
        out = {}
        with t.no_grad():
            for tag, (pos, neg) in SCENE_PROMPTS.items():
                tok = self.proc(text=[pos, neg], return_tensors="pt", padding=True, truncation=True)
                tok = {k: v.to(self.dev) for k, v in tok.items() if k in ("input_ids", "attention_mask")}
                f = self.model.get_text_features(**tok)
                f = getattr(f, "pooler_output", f)
                f = f / f.norm(dim=-1, keepdim=True)
                logits = (self.model.logit_scale.exp() * img_emb @ f.T)[0]
                out[tag] = round(float(t.softmax(logits, dim=-1)[0]), 3)
        return out

    def classify(self, img_emb, names: list[str]) -> np.ndarray:
        t = self.torch
        te = self.text_embeddings(names)
        scale = self.model.logit_scale.exp()
        with t.no_grad():
            logits = (scale * img_emb @ te.T)[0]
            return t.softmax(logits, dim=-1).float().cpu().numpy()


# ------------------------------------------------------------------ GeoCLIP

class GeoCLIPModel:
    def __init__(self, dev: str):
        import torch
        from geoclip import GeoCLIP
        self.torch = torch
        self.model = GeoCLIP().to(dev).eval()
        self.dev = dev

    def points(self, ims: list[Image.Image], top_k: int) -> tuple[np.ndarray, np.ndarray]:
        """GeoCLIP.forward per crop, with the 100k-point gallery encoded once per run instead of once per crop."""
        t = self.torch
        F = t.nn.functional
        m = self.model
        with t.no_grad():
            gallery = m.gps_gallery.to(self.dev)
            locations = F.normalize(m.location_encoder(gallery), dim=1)
            scale = m.logit_scale.exp()
            probs = None
            for im in ims:
                x = m.image_encoder.preprocess_image(im).to(self.dev)
                p = (scale * (F.normalize(m.image_encoder(x), dim=1) @ locations.t())).softmax(dim=-1)[0]
                probs = p if probs is None else probs + p
            probs = probs / len(ims)
            top = t.topk(probs, top_k)
            gps = gallery.index_select(0, top.indices).float().cpu().numpy()
            return gps, top.values.float().cpu().numpy()


def cluster(points: np.ndarray, probs: np.ndarray, radius_km: float = 150.0) -> list[dict]:
    """Greedy clustering: heaviest unassigned point seeds a cluster that absorbs points within radius."""
    left = list(np.argsort(-probs))
    out = []
    while left:
        i = left[0]
        d = geodata.haversine_km(points[i, 0], points[i, 1], points[left, 0], points[left, 1])
        members = [left[j] for j in range(len(left)) if d[j] <= radius_km]
        w = probs[members]
        lat = float(np.average(points[members, 0], weights=w))
        lon = float(np.average(points[members, 1], weights=w))
        near = geodata.reverse(lat, lon, 1, min_pop=1000) or geodata.reverse(lat, lon, 1)
        out.append({"lat": round(lat, 4), "lon": round(lon, 4), "mass": float(w.sum()), "n": len(members),
                    "near": near[0] if near else None})
        left = [x for x in left if x not in set(members)]
    return out


# ------------------------------------------------------------------ map

def world_map(path: Path, pts: np.ndarray | None, probs: np.ndarray | None, countries: list[dict], W: int = 1440) -> None:
    H = W // 2
    im = Image.new("RGB", (W, H), (18, 22, 30))
    d = ImageDraw.Draw(im)
    P = geodata.places()
    xs = ((P.lon.astype(float) + 180) / 360 * W).astype(int).clip(0, W - 1)
    ys = ((90 - P.lat.astype(float)) / 180 * H).astype(int).clip(0, H - 1)
    arr = np.asarray(im).copy()
    arr[ys, xs] = (70, 78, 92)
    im = Image.fromarray(arr)
    d = ImageDraw.Draw(im)
    for lon in range(-180, 181, 30):
        x = int((lon + 180) / 360 * W)
        d.line([(x, 0), (x, H)], fill=(34, 40, 52))
    for lat in range(-60, 61, 30):
        y = int((90 - lat) / 180 * H)
        d.line([(0, y), (W, y)], fill=(34, 40, 52))
    if pts is not None and len(pts):
        mx = float(probs.max())
        for (la, lo), p in sorted(zip(pts.tolist(), probs.tolist()), key=lambda t: t[1]):
            x, y = (lo + 180) / 360 * W, (90 - la) / 180 * H
            r = 2 + 9 * math.sqrt(p / mx)
            d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 90, 60), width=2)
    from geolib.cli import font as _label_font
    f = _label_font(16)
    C = geodata.countries()
    for r in countries[:6]:
        c = C.get(r["iso2"], {})
        if not c.get("center"):
            continue
        la, lo = c["center"]
        x, y = (lo + 180) / 360 * W, (90 - la) / 180 * H
        d.rectangle([x - 3, y - 3, x + 3, y + 3], fill=(250, 220, 70))
        d.text((x + 6, y - 9), f"{c['name']} {r['p']:.0%}", fill=(250, 220, 70), font=f)
    d.text((8, H - 22), "red: GeoCLIP top points (size = probability); yellow: combined country ranking", fill=(200, 200, 200), font=f)
    im.save(path)


# ------------------------------------------------------------------ main

def run(photo: Path, args) -> tuple[dict, np.ndarray | None, np.ndarray | None]:
    dev = device(args.device)
    im = Image.open(photo)
    ims = crops(im)
    res: dict = {"tool": "prior.py", "photo": str(photo), "device": str(dev), "crops": len(ims), "models": args.models}
    labels = label_set([x.strip().upper() for x in args.labels.split(",")] if args.labels else None)
    names = [n for _, n in labels]
    codes = [c for c, _ in labels]
    sc_country = None
    t0 = time.time()
    if "streetclip" in args.models:
        sc = StreetCLIPModel(dev)
        emb = sc.image_embedding(ims)
        p = sc.classify(emb, names)
        order = np.argsort(-p)
        sc_country = {codes[i]: float(p[i]) for i in order}
        res["streetclip"] = {"countries": [{"iso2": codes[i], "name": names[i], "p": round(float(p[i]), 4)} for i in order[: args.top]]}
        regions = {}
        for i in order[: args.regions]:
            if p[i] < 0.08:
                break
            cc = codes[i]
            a1 = sorted({(k.split(".", 1)[1], v["name"]) for k, v in geodata.admin1().items() if k.startswith(cc + ".")}, key=lambda x: x[1])
            if len(a1) < 5:
                # too coarse or outdated to be useful (e.g. GeoNames lists Taiwan as Taipei/Takao/Taiwan/Fukien)
                regions[cc] = [{"admin1": "(skipped: only %d coarse first-level regions in GeoNames)" % len(a1), "code": "",
                                "p_given_country": 0.0, "p": 0.0}]
                continue
            rnames = [f"{n}, {names[i]}" for _, n in a1]
            rp = sc.classify(emb, rnames)
            ro = np.argsort(-rp)
            regions[cc] = [{"admin1": a1[j][1], "code": a1[j][0], "p_given_country": round(float(rp[j]), 4),
                            "p": round(float(rp[j] * p[i]), 4)} for j in ro[:8]]
        res["streetclip"]["regions"] = regions
        res["streetclip"]["seconds"] = round(time.time() - t0, 1)
        res["scene"] = sc.scene_tags(emb)
        del sc
    gc_country = None
    pts = probs = None
    if "geoclip" in args.models:
        t1 = time.time()
        gm = GeoCLIPModel(dev)
        pts, probs = gm.points(ims, args.top_k)
        mass: dict[str, float] = {}
        for (la, lo), pr in zip(pts.tolist(), probs.tolist()):
            cc = geodata.reverse_country(la, lo)
            if cc:
                mass[cc] = mass.get(cc, 0.0) + pr
        tot = sum(mass.values()) or 1.0
        gc_country = {k: v / tot for k, v in sorted(mass.items(), key=lambda kv: -kv[1])}
        cl = cluster(pts, probs, args.cluster_km)
        res["geoclip"] = {"top_k": args.top_k, "mass_in_top_k": round(float(probs.sum()), 4),
                          "countries": [{"iso2": k, "name": geodata.country_name(k), "p": round(v, 4)} for k, v in list(gc_country.items())[: args.top]],
                          "clusters": [{**c, "mass": round(c["mass"] / float(probs.sum()), 4)} for c in cl[:10]],
                          "points": [[round(float(a), 4), round(float(b), 4), round(float(c), 6)] for (a, b), c in zip(pts.tolist(), probs.tolist())][:50],
                          "seconds": round(time.time() - t1, 1)}
        del gm
    # combined country distribution (mixture of the two; only labelled countries)
    comb: dict[str, float] = {}
    srcs = [d for d in (sc_country, gc_country) if d]
    for d in srcs:
        for k, v in d.items():
            comb[k] = comb.get(k, 0.0) + v / len(srcs)
    tot = sum(comb.values()) or 1.0
    combined = [{"iso2": k, "name": geodata.country_name(k), "p": round(v / tot, 4)} for k, v in sorted(comb.items(), key=lambda kv: -kv[1])]
    res["combined"] = combined[: args.top]
    top_txt = ", ".join(f"{r['name']} {r['p']:.0%}" for r in combined[:5])
    res["assessment"] = assess(im, res, combined)
    res["best_guess"] = best_guess(res)
    if not res["assessment"]["informative"]:
        res["signals"] = []
        return res, pts, probs
    res["signals"] = [{
        "kind": "model", "status": "model", "level": "country",
        "clue": f"world-prior models ({' + '.join(args.models)}) rank: {top_txt}",
        "p": {r["iso2"]: r["p"] for r in combined[:30]}, "n_classes": len(labels),
        "file": str(Path(args.out_dir) / "prior.json") if args.out_dir else "prior.json",
    }]
    return res, pts, probs


def best_guess(res: dict) -> dict | None:
    """Internally consistent point guess: the top combined country and, inside it, the heaviest GeoCLIP cluster
    (else its most probable gallery point, else the country's population centre). On a 24-round Street View
    benchmark this halved the median error of taking GeoCLIP's top cluster alone (274 vs 523 km)."""
    comb = res.get("combined") or []
    gc = res.get("geoclip") or {}
    if not comb:
        return None
    cc = comb[0]["iso2"]
    for c in gc.get("clusters") or []:
        if (c.get("near") or {}).get("country") == cc:
            return {"lat": c["lat"], "lon": c["lon"], "country": cc, "near": (c.get("near") or {}).get("name"), "how": "GeoCLIP cluster in top country"}
    for la, lo, _p in gc.get("points") or []:
        if geodata.reverse_country(la, lo) == cc:
            return {"lat": la, "lon": lo, "country": cc, "how": "best GeoCLIP point in top country"}
    c = geodata.countries().get(cc, {})
    if c.get("center"):
        return {"lat": c["center"][0], "lon": c["center"][1], "country": cc, "how": "population centre of top country"}
    return None


def assess(im: Image.Image, res: dict, combined: list[dict]) -> dict:
    """Is this prior worth anything for this image? Monochrome/historical photos and model disagreement → no."""
    small = ImageOps.exif_transpose(im).convert("RGB").resize((96, 96))
    a = np.asarray(small).astype(float)
    chroma = float(np.mean(np.abs(a[..., 0] - a[..., 1]) + np.abs(a[..., 1] - a[..., 2])))
    reasons = []
    if chroma < 8:
        reasons.append("monochrome or sepia image (probably historical): the models learned from modern colour photos")
    top = combined[0]["p"] if combined else 0.0
    if top < 0.25:
        reasons.append(f"flat distribution (top country only {top:.0%}): the scene carries little learned geographic signal")
    sc = [r["iso2"] for r in res.get("streetclip", {}).get("countries", [])[:3]]
    gc = [r["iso2"] for r in res.get("geoclip", {}).get("countries", [])[:3]]
    if sc and gc and not (set(sc) & set(gc)):
        reasons.append(f"the two models disagree completely (StreetCLIP {', '.join(sc)} vs GeoCLIP {', '.join(gc)})")
    elif sc and gc and sc[0] != gc[0]:
        reasons.append(f"top picks differ (StreetCLIP {sc[0]} vs GeoCLIP {gc[0]}): treat as a short list, not a ranking")
    hard = [r for r in reasons if not r.startswith("top picks differ")]
    return {"informative": not hard, "chroma": round(chroma, 1), "top_p": top, "reasons": reasons}


def to_md(res: dict) -> str:
    L = ["# World prior (learned models — ranking only, never proof)", ""]
    L.append(f"Device {res['device']}, {res['crops']} crops averaged. Status on the board: model (LR ≤3, cannot exclude).")
    a = res.get("assessment") or {}
    if a and not a.get("informative"):
        L += ["", "**UNINFORMATIVE for this image — no board signal was written.** " + "; ".join(a.get("reasons", [])) + ". "
              "Indoor scenes, close-ups, museum objects, historical photos and generic nature defeat these models: "
              "rely on text, objects, reverse image search and provenance instead."]
    elif a.get("reasons"):
        L += ["", "Caution: " + "; ".join(a["reasons"]) + "."]
    bg = res.get("best_guess")
    if bg:
        L += ["", f"Model-only point guess: {bg['lat']}, {bg['lon']} ({geodata.country_name(bg['country'])}"
              + (f", near {bg['near']}" if bg.get("near") else "") + f"; {bg['how']}). Benchmark: median error ~270 km — a starting area, not an answer."]
    L += ["", "## Combined country ranking", "", "| # | Country | p |", "|---|---|---|"]
    for i, r in enumerate(res.get("combined", [])[:12], 1):
        L.append(f"| {i} | {r['name']} ({r['iso2']}) | {r['p']:.1%} |")
    sc = res.get("streetclip")
    if sc:
        L += ["", "## StreetCLIP (zero-shot countries)", "", ", ".join(f"{r['name']} {r['p']:.1%}" for r in sc["countries"][:10])]
        for cc, rs in sc.get("regions", {}).items():
            L.append(f"- Regions of {geodata.country_name(cc)}: " + ", ".join(f"{r['admin1']} {r['p_given_country']:.0%}" for r in rs[:6]))
    if res.get("scene"):
        L += ["", "## Scene (zero-shot tags)", "", ", ".join(f"{k} {v:.0%}" for k, v in sorted(res["scene"].items(), key=lambda kv: -kv[1]))
              + "  — mountains or water ≥ 60% → the skyline route is a required check before finish; urban or road ≥ 60% → the street route (photo_session.py checks)."]
    gc = res.get("geoclip")
    if gc:
        L += ["", "## GeoCLIP (GPS gallery)", "", "Countries: " + ", ".join(f"{r['name']} {r['p']:.1%}" for r in gc["countries"][:10]), "", "Clusters (150 km):"]
        for c in gc["clusters"][:6]:
            n = c.get("near") or {}
            L.append(f"- {c['lat']}, {c['lon']} — mass {c['mass']:.0%} ({c['n']} points), near {n.get('name', '?')}, {n.get('admin1', '')}, {n.get('country_name', '')}")
    L += ["", "How to use: test the top 2–3 countries with cheap discriminators (text, plates, driving side, road paint, "
          "`refsheet.py countries A,B,C`). If the image clues contradict the model, believe the clues and say why."]
    return "\n".join(L) + "\n"


def main() -> None:
    handoff(__file__)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", nargs="?")
    ap.add_argument("--out-dir", default="prior")
    ap.add_argument("--models", default="streetclip,geoclip", help="comma list: streetclip, geoclip")
    ap.add_argument("--labels", help="restrict the country classifier to these ISO2 codes")
    ap.add_argument("--regions", type=int, default=3, help="rank first-level regions for this many leading countries")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--top-k", type=int, default=300, help="GeoCLIP gallery points kept")
    ap.add_argument("--cluster-km", type=float, default=150.0)
    ap.add_argument("--device", default="auto", help="auto, cuda, xpu, mps or cpu (auto honours GEOINT_DEVICE)")
    ap.add_argument("--selftest", action="store_true", help="load the models on a synthetic image (downloads weights)")
    args = ap.parse_args()
    args.models = [m.strip() for m in args.models.split(",") if m.strip()]
    if args.selftest:
        tmp = Path(geodata.cache_dir("selftest")) / "prior_selftest.jpg"
        Image.new("RGB", (640, 480), (110, 140, 90)).save(tmp)
        args.photo, args.out_dir = str(tmp), str(tmp.parent / "prior")
    if not args.photo:
        sys.exit("Give a photo (or --selftest)")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res, pts, probs = run(Path(args.photo), args)
    (out / "prior.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    world_map(out / "prior_map.png", pts, probs, res.get("combined", []))
    md = to_md(res)
    (out / "prior.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"-> {out / 'prior.json'}, {out / 'prior.md'}, {out / 'prior_map.png'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
