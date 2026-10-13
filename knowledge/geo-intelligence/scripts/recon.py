#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""One command for the whole first pass on a photo (reverse image search included; all pre-approved).

Runs in parallel and writes everything under --out-dir (default recon/):
  meta/      deep metadata, time-zone countries, filename/platform hints, embedded previews  (meta.py)
  intake/    edge and corner crops, search variants, OCR with automatic language detection, and
             Yandex + Baidu reverse image search on the original and variants                 (intake.py)
  textgeo.*  text → countries/regions/places: scripts, letters, phones, domains, brands, place names (textgeo.py)
  detect/    numbered crops of signs, plates, poles, bollards, markings, vehicles…          (detect.py)
  calib.*    field of view, pitch/roll, horizon line                                       (calib.py)
  prior/     learned world prior (StreetCLIP + GeoCLIP), self-assessed                       (prior.py)
  aidet/     AI-generated-image score of the original: model status, never a verdict      (aidet.py)
  recon.md   one page summarising all of it — read this, then open the crops it lists

  recon.py original/photo.jpg                      # full pass (first run downloads models, later runs ~1 min)
  recon.py original/photo.jpg --no-ml              # metadata, crops, OCR, text and reverse search, no local models
  recon.py original/photo.jpg --no-rev             # everything except the reverse image search
  recon.py original/photo.jpg --skip detect,calib  # skip some steps

The tools do not replace your own read of the image: make your gut call first (SKILL.md, step 1), then use
this page to confirm, contradict or sharpen it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
UV = os.environ.get("UV") or "uv"
ML_STEPS = ("detect", "calib", "prior", "aidet")
AIDET_TIMEOUT = 20          # seconds; the first run downloads 44 MB, so without `doctor.py --models` it reports a skip
SCENE_UNTAGGED = ("- Scene: not tagged ({}) → finish requires no skyline/street check; pick the decisive check from SKILL.md "
                  "step 6 by what the photo shows (finish still needs one verification artifact).")


def _stop_tree(p: subprocess.Popen) -> None:
    """Stop a timed-out step with its child: `uv run` leaves the script running when uv alone is killed on Windows, and
    the script holds the output pipes, so the read would wait for it to end."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    else:
        p.terminate()                                          # SIGTERM: uv forwards it to the script it runs
    try:
        p.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()


def run(name: str, cmd: list[str], log: dict, timeout: int = 1800) -> int:
    t0 = time.time()
    p = subprocess.Popen(cmd, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env={**os.environ, "PYTHONUTF8": "1", "TOKENIZERS_PARALLELISM": "false"})
    try:
        out, err = p.communicate(timeout=timeout)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        _stop_tree(p)
        rc, err, out = 124, f"timed out after {timeout}s", ""
    log[name] = {"rc": rc, "seconds": round(time.time() - t0, 1),
                 "error": "" if rc == 0 else (err or out).strip()[-600:], "stdout_tail": out.strip()[-400:]}
    return rc


def jload(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def aidet_state(out: Path, log: dict) -> dict:
    """aidet.json of this run, or {"skipped": reason} when the lane timed out, failed or did not run (main removes an earlier
    run's record first and writes this skip in its place)."""
    step = log.get("aidet") or {}
    if step.get("rc"):
        reason = (step.get("error") or "failed").strip().splitlines()[-1][:200]
        if step["rc"] == 124:
            reason += "; `doctor.py --models` prefetches the weights"
        return {"skipped": reason}
    return jload(out / "aidet" / "aidet.json") or {"skipped": "not run"}


def generated_check(meta: dict, ij: dict, aj: dict) -> str:
    """The generated-image sentence folded into Next 0 ('' when nothing points there). Only a declaration or a confirmed
    AI-gallery page can close as generated; a score alone keeps the search going."""
    g = (meta.get("provenance") or {}).get("generated") or {}
    hits = ij.get("ai_gallery_hits") or []
    p = aj.get("p_ai")
    if g.get("declared"):
        return (f" Generated-image check: the file declares generated content ({g['term']}) → `photo_session.py finish \"<session folder>\" "
                f"--generated \"{g['term']}\"`, unless a pinning artifact places it or the operator says it is real; once "
                "`photo_session.py not-generated` has recorded that, this command no longer applies: continue to the place.")
    if hits:
        return (f" Generated-image check: an AI-gallery page returned this image ({hits[0]['url']}) → open the page, confirm the "
                "duplicate on fixed features and save it as a session file; only then `finish --generated <that file>`.")
    if p is not None and p >= aj.get("threshold", 0.65):
        return f" Generated-image check: possible generated image, unconfirmed (model {p:.2f}): continue and say so in the report."
    return ""


def summary(photo: Path, out: Path, log: dict, total: float, rev: bool) -> str:
    L = [f"# Recon: {photo.name}", "",
         f"First pass in {total:.0f}s (" + ", ".join(f"{k} {v['seconds']}s" + ("" if v["rc"] == 0 else " FAILED") for k, v in log.items()) + ").",
         ("Reverse image search ran on Yandex and Baidu (original + variants). " if rev else "Reverse image search skipped (--no-rev). ")
         + "Make (or revisit) your gut call, then use the evidence below to confirm, contradict or sharpen it.", ""]
    # metadata
    meta = jload(out / "meta" / "meta.json").get("digest", {})
    aj = aidet_state(out, log)
    L += ["## Metadata", ""]
    if meta:
        g, t = meta.get("gps") or {}, meta.get("time") or {}
        if g.get("lat") is not None:
            L.append(f"- **GPS {g['lat']}, {g['lon']}** — a hypothesis until the scene confirms it (see meta/meta.md).")
        if t.get("utc_offset"):
            ccs = t.get("countries_with_this_offset_on_that_date", [])
            L.append(f"- UTC offset {t['utc_offset']} ({t.get('utc_offset_source')}): {len(ccs)} countries used it on that date "
                     f"({', '.join(ccs[:25])}{' …' if len(ccs) > 25 else ''}).")
        if t.get("DateTimeOriginal"):
            L.append(f"- Capture time (local clock): {t['DateTimeOriginal']}")
        for h in meta.get("filename_hints", []):
            L.append(f"- Filename: {h['pattern']}")
        if meta.get("camera"):
            L.append(f"- Camera/software: {json.dumps(meta['camera'], ensure_ascii=False)}")
        for pv in meta.get("previews") or []:
            if pv.get("note"):
                L.append(f"- Embedded {pv['tag']}: {pv['note']} → `meta/{pv['file']}`")
        for mv in meta.get("motion_video", []) or []:
            f = mv["file"]
            L.append(f"- **Motion photo**: embedded video `meta/{f}` ({mv['bytes'] // 1024} KB) — more frames and angles; "
                     f"`ffmpeg -i meta/{f} -vf fps=2 meta/motion_%02d.jpg` and read the clearest")
        if (meta.get("provenance") or {}).get("WARNING"):
            L.append(f"- **{meta['provenance']['WARNING']}**")
        if not g and not t and not meta.get("filename_hints"):
            L.append("- No GPS, no time, no telling filename (normal for forwarded/screenshot images).")
    else:
        L.append(f"- meta.py did not run: {log.get('meta', {}).get('error', '')[:200]}")
    if "p_ai" in aj:
        line = f"AI-image score {aj['p_ai']:.2f} (model rank, not proof; threshold {aj['threshold']})"
        L.append(f"- **{line}** → Next 0" if aj["p_ai"] >= aj["threshold"] else
                 f"- {line}: not flagged; a low score never clears (re-saved images and newer generators score low).")
    else:
        L.append(f"- AI-image check: skipped ({aj['skipped']})")
    # text
    L += ["", "## Text", ""]
    oj = jload(out / "intake" / "ocr.json")
    ocr = oj.get("items", [])
    rapid = oj.get("backend") == "rapidocr"
    if rapid:
        import textgeo                                   # same directory: the RapidOCR blind spot is worded there once
    import re as _re
    marks = [it["text"] for it in ocr if _re.search(r"(19|20)\d\d\s*(google|goodle|apple|yandex|baidu|bing|maxar|airbus)", it["text"], _re.I)]
    if marks:
        L.append(f"- Provider watermark read: “{marks[0]}” → street-level/map imagery screenshot; the year is the copyright year, "
                 "close to (not equal to) the capture date. See references/world/streetview.md.")
    if ocr:
        hint = (". " + textgeo.RAPIDOCR_NOTE if rapid else
                "; Vision cannot read Greek, Hebrew, Georgian, Armenian, Indic, Sinhala, Khmer, Lao, Burmese or Ethiopic: "
                "read those yourself and run `textgeo.py --text`:")
        L.append("OCR lines (conf, pass) — verify each in the zoomed crop" + hint)
        for it in ocr[:20]:
            L.append(f"- {it['conf']:.2f} {it['pass']}: {it['text']}")
    else:
        L.append("- OCR found no text (or it is too small: zoom the crops in intake/edges and detect/).")
        if rapid:
            L.append(f"- {textgeo.RAPIDOCR_EMPTY}")
    tg = jload(out / "textgeo.json")
    if tg.get("shortlist"):
        L.append("")
        L.append("Text → country shortlist: " + ", ".join(f"{r['name']} ({r['log_lr']})" for r in tg["shortlist"][:8]))
        for s in tg.get("signals", [])[:12]:
            L.append(f"  - [{s['kind']}/{s['status']}] {s['clue']}")
        if tg.get("places"):
            L.append("  - Place-name matches: " + "; ".join(f"“{p['matched']}” → {p['name']}, {p['admin1']}, {p['country_name']}"
                                                       for p in tg["places"][:6] if "matched" in p))
    # reverse image search
    L += ["", "## Reverse image search (Yandex, Baidu)", ""]
    ij = jload(out / "intake" / "intake.json")
    if not rev:
        L.append("- Not run (--no-rev).")
    elif ij:
        st = ij.get("status", {})
        L.append("- Engines: " + ", ".join(f"{k.replace('rev-', '')} {v}" for k, v in st.items() if k.startswith("rev-")))
        votes = ij.get("votes", {})
        city = sorted((votes.get("city") or {}).items(), key=lambda kv: -len(kv[1]))[:6]
        place = sorted((votes.get("place") or {}).items(), key=lambda kv: -len(kv[1]))[:6]
        if city:
            L.append("- City-level labels: " + "; ".join(f"{t} ({len(e)} votes)" for t, e in city))
        if place:
            L.append("- Labels that may name a place (often a scene or object word): " + "; ".join(f"{t} ({len(e)})" for t, e in place)
                     + " → `poi.py \"<name>\"` (or web search) only for a proper name, then verify")
        sims = [e for e in ij.get("rev", []) if e.get("similar_sheet")]
        if sims:
            L.append("- Near-duplicate sheets to open first: " + ", ".join(f"`intake/rev/{e['similar_sheet']}`" for e in sims[:4]))
        if not city and not place and not sims:
            L.append("- No labels or similar images captured: open the screenshots in `intake/rev/`; then try tight crops of "
                     "distinctive objects (`intake.py original/<photo> --box …`) and Google Lens through the browser tool.")
        L.append("- Read the result screenshots in `intake/rev/` yourself: labels are votes, near-duplicates are leads, "
                 "neither is a location until verified.")
    else:
        L.append(f"- intake did not finish: {log.get('intake', {}).get('error', '')[:200]}")
    # prior
    pr = jload(out / "prior" / "prior.json")
    L += ["", "## World prior (learned models: ranking only)", ""]
    if pr:
        a = pr.get("assessment", {})
        L.append(("- **Uninformative here** — " + "; ".join(a.get("reasons", []))) if not a.get("informative", True) else
                 "- Combined: " + ", ".join(f"{r['name']} {r['p']:.0%}" for r in pr.get("combined", [])[:6]))
        if a.get("informative", True) and a.get("reasons"):
            L.append("- Caution: " + "; ".join(a["reasons"]))
        bg = pr.get("best_guess")
        if bg and a.get("informative", True):
            L.append(f"- Model-only point guess: {bg['lat']}, {bg['lon']}" + (f" near {bg['near']}" if bg.get("near") else "")
                     + " (benchmark median error ~270 km: an area to start from, not an answer)")
        cl = (pr.get("geoclip") or {}).get("clusters", [])[:3]
        if cl:
            L.append("- GeoCLIP clusters: " + "; ".join(f"{c['lat']},{c['lon']} near {(c.get('near') or {}).get('name')}, "
                                                       f"{(c.get('near') or {}).get('country_name')} ({c['mass']:.0%})" for c in cl))
        regs = (pr.get("streetclip") or {}).get("regions", {})
        for cc, rs in list(regs.items())[:2]:
            L.append(f"- Regions of {cc}: " + ", ".join(f"{r['admin1']} {r['p_given_country']:.0%}" for r in rs[:5]))
        L.append("- Map: `prior/prior_map.png`")
        if pr.get("scene"):
            import photo_session                                   # same directory: the scene → required checks mapping lives there
            L.append("- Scene: " + ", ".join(f"{k} {v:.0%}" for k, v in sorted(pr["scene"].items(), key=lambda kv: -kv[1])))
            req = photo_session.checks_for_scene(pr["scene"])
            if req:
                L.append("- **Required before finish** (finish refuses without their files; `photo_session.py checks <session>` lists them): "
                         + "; ".join(f"**{c['name']}** ({c['why']}) → {c['command']}" for c in req))
        else:
            L.append(SCENE_UNTAGGED.format("no StreetCLIP"))
    else:
        L.append(f"- not run ({log.get('prior', {}).get('error', 'skipped')[:160]})")
        L.append(SCENE_UNTAGGED.format("prior did not run"))
    # camera
    cb = jload(out / "calib.json")
    L += ["", "## Camera", ""]
    if cb:
        h = cb.get("horizon") or {}
        u = cb.get("uncertainty") or {}
        shaky = (u.get("vfov_uncertainty", 0) > 8 or u.get("pitch_uncertainty", 0) > 3
                 or u.get("focal_uncertainty", 0) > 0.3 * cb.get("focal_px", 1))
        L.append(f"- hfov {cb['hfov_deg']}° (35 mm eq. {cb['focal_35mm_equiv']} mm), pitch {cb['pitch_deg']}° ±{u.get('pitch_uncertainty', '?')}, "
                 f"roll {cb['roll_deg']}° ±{u.get('roll_uncertainty', '?')}, horizon row {h.get('row_at_centre')}, vfov ±{u.get('vfov_uncertainty', '?')}°"
                 + (" — **UNRELIABLE (large uncertainty): do not feed these into geometry tools; measure the horizon by hand.**" if shaky else
                    " — check the red line in `calib.jpg` before using these numbers."))
    else:
        L.append(f"- not run ({log.get('calib', {}).get('error', 'skipped')[:160]})")
    # detections
    dt = jload(out / "detect" / "detect.json")
    L += ["", "## Things to inspect", ""]
    if dt.get("detections"):
        from collections import Counter
        cnt = Counter(d["cls"] for d in dt["detections"])
        L.append("- " + ", ".join(f"{k} {v}" for k, v in cnt.most_common()) + " → open `detect/detect_sheet.jpg`, then the numbered crops.")
    elif dt:
        L.append("- The detector found nothing above its threshold: scan the image yourself (edges, corners, distant signs).")
    L.append("- Edge and corner crops: `intake/edges/` (look at every one); OCR boxes: `intake/ocr.png`.")
    L += ["", "## Next", "",
          "0. The checks named under Prior (scene) are required before finish whatever else you find (a mountain or lake: the skyline route; "
          "a street: the panorama route): the floor, not the first route. Run your plan's line A first unless it is one of them; start long "
          "ones in the background with a budget. An explicit Quick request stops before heavy work: record those checks as skipped with "
          "the reason 'operator asked: Quick, stop before heavy analysis' (SKILL.md Session and speed)." + generated_check(meta, ij, aj),
          "1. Compare this page with your gut call. Where they disagree, find out why (a misread, an unusual scene, a wrong gut). A place name "
          "read here or a near-duplicate hit moves up in your plan.",
          "2. board.json exists since `photo_session.py start` and already holds the text and prior signals (ingested here): "
          "record your own observations as clues (`board.py clue`), then evidence for the candidates they touch.",
          "3. Separate the top candidates with the cheapest decisive test (text lookups, web search, `refsheet.py`, the world clue files).",
          "4. Follow every reverse-search lead (source pages, albums, captions); try Google Lens through the browser tool and "
          "re-run the scripted engines on a tight crop of the most distinctive object. No questions to the user — decide and continue."]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("recon"))
    ap.add_argument("--no-ml", action="store_true", help="skip detect, calib, prior and aidet")
    ap.add_argument("--skip", default="", help="comma list of steps to skip: meta,intake,textgeo,detect,calib,prior,aidet")
    ap.add_argument("--no-rev", action="store_true", help="skip the Yandex/Baidu reverse image search")
    args = ap.parse_args()
    photo = args.photo.resolve()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()} | (set(ML_STEPS) if args.no_ml else set())
    record = out / "aidet" / "aidet.json"
    record.unlink(missing_ok=True)          # an earlier run's score (another frame, another photo) never passes for this one
    log: dict = {}
    t0 = time.time()
    S = lambda n: str(HERE / n)  # noqa: E731

    def light():
        if "meta" not in skip:
            run("meta", [UV, "run", "-q", S("meta.py"), str(photo), "--out-dir", str(out / "meta")], log)
        if "intake" not in skip:
            run("intake", [UV, "run", "-q", S("intake.py"), str(photo), "--out-dir", str(out / "intake")]
                + (["--no-rev"] if args.no_rev else []), log)
        if "textgeo" not in skip and (out / "intake" / "ocr.json").exists():
            run("textgeo", [UV, "run", "-q", S("textgeo.py"), "--ocr", str(out / "intake" / "ocr.json"),
                            "--out", str(out / "textgeo.json"), "--md", str(out / "textgeo.md")], log)

    def heavy():
        if "detect" not in skip:
            run("detect", [UV, "run", "-q", S("detect.py"), str(photo), "--out-dir", str(out / "detect")], log)
        if "calib" not in skip:
            run("calib", [UV, "run", "-q", S("calib.py"), str(photo), "--out", str(out / "calib.json"), "--draw", str(out / "calib.jpg")], log)
        if "prior" not in skip:
            run("prior", [UV, "run", "-q", S("prior.py"), str(photo), "--out-dir", str(out / "prior")], log)

    def aidet():                # own lane: the heavy lane is the critical path, a 20 s cap here never delays it
        if "aidet" not in skip:
            run("aidet", [UV, "run", "-q", S("aidet.py"), str(photo), "--out-dir", str(out / "aidet")], log, timeout=AIDET_TIMEOUT)

    with ThreadPoolExecutor(3) as ex:
        for f in [ex.submit(light), ex.submit(heavy), ex.submit(aidet)]:
            f.result()
    state = ({"skipped": "not run (--no-ml)" if args.no_ml else "not run (--skip aidet)"} if "aidet" in skip else aidet_state(out, log))
    if "p_ai" not in state:                 # one current record for recon.md, the viewer and finish
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"tool": "aidet.py", "skipped": state["skipped"]}, indent=1), encoding="utf-8")
        if "aidet" not in skip:
            print(f"aidet: skipped ({state['skipped']})")
    md = summary(photo, out, log, time.time() - t0, not args.no_rev)
    (out / "recon.md").write_text(md, encoding="utf-8")
    (out / "recon.json").write_text(json.dumps({"photo": str(photo), "steps": log}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(md)
    print(f"-> {out / 'recon.md'}")
    ingest_into_board(out)


def ingest_into_board(out: Path) -> list[str]:
    """board.json in the session root (photo_session.py start creates it): the text and prior signals are ingested with their
    status caps, so the board carries the first pass even when nobody runs board.py ingest by hand."""
    root = out.resolve().parent
    board = root / "board.json"
    lines: list[str] = []
    if not board.is_file():
        return lines
    for rel in ("textgeo.json", "prior/prior.json"):
        f = (out / rel).resolve()
        if not f.is_file():
            continue
        r = subprocess.run([UV, "run", "-q", str(HERE / "board.py"), "ingest", str(f)], cwd=str(root),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or ["ok"])[-1]
        lines.append(f"board.py ingest {rel}: {tail}")
    for line in lines:
        print(line)
    return lines


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
