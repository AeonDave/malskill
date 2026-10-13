#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "pillow"]
# ///
"""Reverse image search + keyword image search on the local engines: headless Chrome or Chromium opens the search engines, saves result screenshots, extracts guess text and links.

  revimg.py <image> [<image> ...] --out-dir rev/ [--engines baidu,yandex]      reverse image search
  revimg.py --query "<keywords>" [--query ...] --country XX --out-dir q/ [--text-engines naverimg,daumimg]   keyword search

Reverse image search:
- baidu: the main engine for China. Best coverage of Chinese web pages, Weibo, Baijiahao, e-commerce and scenic-area content; gives a one-line "图中可能是…" ("the image may show…").
  The "相似图片" (similar images) cards are not links; they are captured from the pcsimi requests the page sends (it scrolls a few times to get more pages), deduplicated by contsign and written to `similar` in the JSON;
  the first --similar-sheet of them are downloaded into a numbered contact sheet `<name>_baidu_similar.jpg` (first cell is the query image): near-duplicate photos of the same object/scene are the fastest path to a location, always open it.
- yandex: supplement for buildings, street scenes and foreign content; gives "Image appears to contain" tags and source sites.
- Google Lens asks for human verification from a server egress, so the script doesn't do it; when you have a browser-control tool (e.g. Claude in Chrome), search in the user's own browser, see references/search.md.

Keyword search (general web search tools rarely index a country's local web):
- --country XX (ISO2) picks the image engines that index that country's web (table under --country below and in
  references/search.md); --text-engines overrides it.
- Image engines: naverimg, daumimg, yahoojpimg, yandeximg, bingimg, googleimg, baiduimg, sogouimg. Each query saves up to
  two 3000-px screenshots of the result grid (`qNN_<engine>.png`, plus `qNN_<engine>_2.png` when the page loads a second batch).
- bing: Bing China web results (title + link). Baidu web search pops up a security check, not done.
- A CAPTCHA, consent or region-block page is reported as blocked, never bypassed; that engine is skipped for the rest of the run.

Each item outputs `<name>_<engine>.png` (result-page screenshot, always open it) and `.json` (guess text + links; Baidu also has `similar` and the similar-images contact sheet).
Before reverse image search, use `imgprep.py variants` to make tight-crop / flipped / color-cast-removed versions and search each one — no hit on the full image is normal.
Requires Google Chrome or Playwright Chromium. Chrome is tried first, then Chromium.
Run `uvx playwright install chromium` if neither is installed; `doctor.py` checks that the browser can start.

Examples:
  revimg.py photo.jpg --out-dir rev/
  revimg.py v/left_crop.jpg v/left_flip.jpg --out-dir rev/ --engines baidu
  revimg.py photo.jpg --out-dir rev/ --engines yandex
  revimg.py --query "蓝色拱形顶棚 人行天桥" --query "<city> 出租车 颜色" --country CN --out-dir q/   (queries in Chinese: blue arched canopy footbridge; <city> taxi color)
"""
from __future__ import annotations

import argparse
from geolib.browser import launch_browser
from geolib.net import fetch_bytes, PROXY_HELP
import asyncio
import html
import io
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

# The engine's own hosts: links there are not results, except posts and articles (path two levels deep) on KEEP hosts
OWN = {"baidu": ("baidu.com", "bdimg.com", "bdstatic.com"), "yandex": ("yandex.", "ya.ru", "yastatic.net"),
       "bing": ("bing.com", "bing.net", "microsoft.com"), "baiduimg": ("baidu.com", "bdimg.com", "bdstatic.com"),
       "sogouimg": ("sogou.com", "sogoucdn.com"), "naverimg": ("naver.com", "naver.net", "pstatic.net"),
       "daumimg": ("daum.net", "kakao.com", "daumcdn.net", "melon.com", "www.tistory.com"),
       "yahoojpimg": ("yahoo.co.jp", "yahoo-net.jp", "yimg.jp", "lycorp.co.jp"), "googleimg": ("google.", "gstatic.com")}
OWN["yandeximg"], OWN["bingimg"] = OWN["yandex"], OWN["bing"]
KEEP = {"naverimg": ("blog.naver.com", "cafe.naver.com", "post.naver.com", "news.naver.com"),
        "daumimg": ("v.daum.net", "cafe.daum.net")}
BAIDU_REFUSED = ("功能优化中", "建议您重新上传其他图片")
# www.bing.com: cn.bing.com redirects non-China egress to the www homepage and drops the /search path (empty page, no error);
# inside China www.bing.com redirects to cn.bing.com keeping the path. No mkt=zh-CN: that market page answers "no results"
# from outside China; the zh-CN context locale already gives the Chinese UI and ranking
TEXT_URL = {"bing": "https://www.bing.com/search?q={q}", "baiduimg": "https://image.baidu.com/search/index?tn=baiduimage&word={q}",
            "sogouimg": "https://pic.sogou.com/pics?query={q}",
            "naverimg": "https://search.naver.com/search.naver?where=image&query={q}",
            "daumimg": "https://search.daum.net/search?w=img&q={q}",
            "yahoojpimg": "https://search.yahoo.co.jp/image/search?p={q}&ei=UTF-8",
            "yandeximg": "https://yandex.com/images/search?text={q}",
            "bingimg": "https://www.bing.com/images/search?q={q}",
            "googleimg": "https://www.google.com/search?q={q}&udm=2"}
TEXT_LOCALE = {"bing": "zh-CN", "baiduimg": "zh-CN", "sogouimg": "zh-CN", "naverimg": "ko-KR", "daumimg": "ko-KR",
               "yahoojpimg": "ja-JP", "yandeximg": "ru-RU"}                  # the rest: en-US
# --country → the image engines that index that country's web; references/search.md holds the operator's table
COUNTRY_ENGINES = {"KR": ("naverimg", "daumimg"), "JP": ("yahoojpimg", "yandeximg", "googleimg"), "CN": ("baiduimg", "sogouimg"),
                   "RU": ("yandeximg", "googleimg"), "BY": ("yandeximg", "googleimg"), "KZ": ("yandeximg", "googleimg")}
DEFAULT_ENGINES = ("bingimg", "yandeximg")
# A result tile or row: Bing's "no results" page has none (its #b_results container is still there)
RESULT_ITEM = {"bing": "li.b_algo", "bingimg": "a.iusc"}
# Verification, consent and region walls: (where, marker, what); "url" is the host + path, "text" the page's first 400 characters
BLOCKS = (("url", "captcha", "a CAPTCHA"), ("url", "/sorry/", "a CAPTCHA"), ("url", "consent.", "a consent page"),
          ("text", "安全验证", "a security check"), ("text", "unusual traffic from your computer network", "a CAPTCHA"),
          ("text", "欧州経済領域", "a region block (Yahoo! JAPAN is not served in the EEA and the UK)"))
SLICE = 3000            # px per result screenshot: thumbnails stay legible once the image is scaled down for reading
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


async def _collect(page, engine: str) -> dict:
    text = await page.evaluate("document.body ? document.body.innerText : ''")
    links = await page.evaluate("""() => [...document.querySelectorAll('a[href^="http"]')]
        .map(a => ({t: (a.innerText || a.title || '').trim().replace(/\\s+/g, ' ').slice(0, 120), h: a.href}))
        .filter(x => x.t.length >= 4)""")
    seen, out = set(), []
    for ln in links:
        u = urlparse(ln["h"])
        host = u.netloc
        kept = host in KEEP.get(engine, ()) and len([s for s in u.path.split("/") if s]) >= 2
        if (any(o in host for o in OWN[engine]) and not kept) or ln["h"] in seen:
            continue
        seen.add(ln["h"])
        out.append({"title": html.unescape(ln["t"]), "url": ln["h"], "site": host})
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    guess = [s for s in lines if s.startswith("图中可能是") or "appears to contain" in s.lower()]
    if engine == "yandex" and guess:            # the tags are the few lines right after "appears to contain"
        i = lines.index(guess[0])
        guess = [guess[0] + ": " + " / ".join(lines[i + 1:i + 8])]
    return {"url": page.url, "guess": guess, "links": out[:25], "text_head": "\n".join(lines[:60])[:2500]}


def query_url(engine: str, query: str) -> str:
    return TEXT_URL[engine].format(q=quote(query, safe=""))


def pick_text_engines(country: str | None, explicit: str | None) -> list[str]:
    """An explicit --text-engines list wins; otherwise the country's engines, or the default pair."""
    if explicit:
        return [e for e in explicit.split(",") if e in TEXT_URL]
    return list(COUNTRY_ENGINES.get((country or "").upper(), DEFAULT_ENGINES))


def _blocked(url: str, text: str) -> str | None:
    u = urlparse(url)
    where = {"url": (u.netloc + u.path).lower(), "text": text}
    return next((what for kind, marker, what in BLOCKS if marker in where[kind]), None)


async def _dismiss_cookies(page) -> None:
    for label in ("Allow essential cookies", "Only essential", "Accept essential", "Allow all", "Accept all"):
        try:                                            # a cookie popup covers part of the screenshot
            btn = page.get_by_role("button", name=label)
            if await btn.count():
                await btn.first.click(timeout=2000)
                await page.wait_for_timeout(800)
                return
        except Exception:  # noqa: BLE001
            continue


async def _grid_shots(page, shot: Path) -> list[str]:
    """Scrolls two slices down, which loads an infinite-scroll second batch, then back up, which loads its lazy
    thumbnails; saves one or two slices."""
    steps = list(range(0, 2 * SLICE + 1, 1000))
    for y in steps + steps[::-1]:
        await page.evaluate(f"window.scrollTo(0, {y})")
        await page.wait_for_timeout(400)
    await page.wait_for_timeout(1000)
    height = await page.evaluate("document.documentElement.scrollHeight")
    paths = [shot] + ([shot.with_name(shot.stem + "_2.png")] if height > SLICE + 500 else [])
    for i, path in enumerate(paths):
        await page.screenshot(path=str(path), full_page=True, clip={"x": 0, "y": i * SLICE, "width": 1400, "height": SLICE})
    return [str(p) for p in paths]


def _site(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":")[0]
    for pre in ("www.", "m.", "wap.", "mobile."):
        if host.startswith(pre) and host.count(".") > 1:
            return host[len(pre):]
    return host


def _similar_sheet(query: Path, items: list[dict], out: Path, cols: int = 5, tile: int = 300, proxy: str | None = None) -> int:
    """Query image + thumbnails of the first N similar images → numbered contact sheet (number = index in the similar array). Returns how many downloaded successfully."""
    from PIL import Image, ImageDraw
    from geolib.cli import font

    def fetch(url: str):
        try:
            data = fetch_bytes(url, proxy, 15, {"User-Agent": UA, "Referer": "https://graph.baidu.com/"})
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:  # noqa: BLE001
            return None

    with ThreadPoolExecutor(8) as ex:
        ims = list(ex.map(fetch, [it["thumb"] for it in items]))
    try:
        q = Image.open(query).convert("RGB")
    except Exception:  # noqa: BLE001
        q = None
    tiles = [(q, "query", "cyan")] + [
        (im, f"{i:02d} {it['site'] or '?'}", "yellow") for i, (it, im) in enumerate(zip(items, ims))]
    bar = 24
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new("RGB", (cols * tile, rows * (tile + bar)), (40, 40, 40))
    d = ImageDraw.Draw(S)
    f = font(17, prefer_wide=True)
    for k, (im, label, color) in enumerate(tiles):
        x, y = (k % cols) * tile, (k // cols) * (tile + bar)
        d.rectangle([x, y, x + tile - 1, y + bar - 1], fill="black")
        d.text((x + 4, y + 2), label[:30], fill=color, font=f)
        if im is None:
            d.text((x + 10, y + bar + tile // 2), "download failed", fill="gray", font=f)
            continue
        im.thumbnail((tile - 4, tile - 4))
        S.paste(im, (x + (tile - im.width) // 2, y + bar + (tile - im.height) // 2))
    S.save(out, quality=88)
    return sum(im is not None for im in ims)


async def _baidu(ctx, img: Path, shot: Path, similar_pages: int = 2, sheet_n: int = 24, proxy: str | None = None) -> dict:
    page = await ctx.new_page()
    simi: list = []                                   # "相似图片" (similar images) cards aren't DOM links; they come from ajax/pcsimi responses

    async def grab(resp):
        try:
            data = (await resp.json()).get("data") or {}
            simi.append((int(parse_qs(urlparse(resp.url).query).get("page", ["0"])[0] or 0), data.get("list") or []))
        except Exception:  # noqa: BLE001
            simi.append((0, []))

    pending: list = []
    page.on("response", lambda r: pending.append(asyncio.ensure_future(grab(r))) if "graph.baidu.com/ajax/pcsimi" in r.url else None)
    await page.goto("https://graph.baidu.com/pcpage/index?tpl_from=pc", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(2000)
    inp = await page.query_selector("input[type=file]")
    if not inp:
        await page.screenshot(path=str(shot))
        return {"error": "upload input not found (page redesigned or blocked); check the screenshot"}
    await inp.set_input_files(str(img))
    for _ in range(60):
        await page.wait_for_timeout(500)
        if "graph.baidu.com/s" in page.url:
            break
    await page.wait_for_timeout(4500)
    await page.screenshot(path=str(shot), full_page=True, clip={"x": 0, "y": 0, "width": 1400, "height": 3200})
    res = await _collect(page, "baidu")
    misses, got = 0, 0                                # scrolling to the bottom triggers the next page; stop after two misses in a row
    while got < similar_pages and misses < 2 and pending:
        n0 = len(pending)
        await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        for _ in range(16):
            await page.wait_for_timeout(250)
            if len(pending) > n0:
                break
        got, misses = (got + 1, 0) if len(pending) > n0 else (got, misses + 1)
    await asyncio.gather(*pending)
    await page.close()
    seen, similar = set(), []
    for _, lst in sorted(simi, key=lambda t: t[0]):
        for it in lst:
            key = it.get("contsign") or it.get("thumbUrl")
            if not it.get("thumbUrl") or key in seen:
                continue
            seen.add(key)
            similar.append({"thumb": it["thumbUrl"], "from": it.get("fromUrl") or "", "site": _site(it.get("fromUrl") or "")})
    res["similar"] = similar
    if similar and sheet_n > 0:
        sheet = shot.with_name(shot.stem + "_similar.jpg")
        ok = await asyncio.to_thread(_similar_sheet, img, similar[:sheet_n], sheet, proxy=proxy)
        res["similar_sheet"] = str(sheet)
        if ok < min(sheet_n, len(similar)):
            res["similar_sheet_note"] = f"{min(sheet_n, len(similar)) - ok} thumbnails failed to download"
    if not res["guess"] and any(w in res["text_head"] for w in BAIDU_REFUSED):
        res["error"] = "Baidu refused to process this image (the \"功能优化中\" (\"under optimization\") page); this does not count as searched with no result: try another crop, retry later, or use only Yandex"
    return res


async def _yandex(ctx, img: Path, shot: Path) -> dict:
    page = await ctx.new_page()
    await page.goto("https://yandex.com/images/search?rpt=imageview", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(2500)
    inp = await page.query_selector("input[type=file]")
    if not inp:
        await page.screenshot(path=str(shot))
        return {"error": "upload input not found (possibly asked for verification); check the screenshot"}
    await inp.set_input_files(str(img))
    for _ in range(60):
        await page.wait_for_timeout(500)
        if "url=" in page.url or "cbir_id" in page.url:
            break
    await page.wait_for_timeout(4500)
    await _dismiss_cookies(page)
    await page.screenshot(path=str(shot), full_page=True, clip={"x": 0, "y": 0, "width": 1400, "height": 3200})
    res = await _collect(page, "yandex")
    await page.close()
    return res


async def _give_up(page, shot: Path, res: dict) -> dict:
    await page.screenshot(path=str(shot))
    await page.close()
    return res


async def _text(ctx, engine: str, query: str, shot: Path) -> dict:
    page = await ctx.new_page()
    await page.goto(query_url(engine, query), wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3500)
    head = await page.evaluate("document.body ? document.body.innerText.slice(0, 400) : ''")
    what = _blocked(page.url, head)
    if what:
        return await _give_up(page, shot, {"error": f"{engine} answered with {what} (not bypassed, not retried this run): use the "
                                                    "other engines, or --proxy with an exit in the engine's country", "blocked": True})
    await _dismiss_cookies(page)
    if engine == "bing":
        try:                                            # Bing lands on an rdr=1 redirect page first; results render a few seconds later
            await page.wait_for_selector("li.b_algo", timeout=15000)
        except Exception:  # noqa: BLE001 - zero results or a changed layout: judged below
            pass
        if not await page.evaluate("!!document.querySelector('#b_results')"):
            return await _give_up(page, shot, {"error": f"results page not reached (landed on {page.url}); check the screenshot"})
    if engine in RESULT_ITEM and not await page.query_selector(RESULT_ITEM[engine]):
        return await _give_up(page, shot, {"error": f"no results for this query on {engine}: not evidence that nothing matches "
                                                    "(Bing note in references/search.md); use the other engines"})
    if engine != "bing":
        shots = await _grid_shots(page, shot)
        res = await _collect(page, engine)
        if len(shots) > 1:
            res["screenshot_2"] = shots[1]
        await page.close()
        return res
    await page.screenshot(path=str(shot), full_page=True, clip={"x": 0, "y": 0, "width": 1400, "height": SLICE})
    rows = await page.evaluate("""() => [...document.querySelectorAll('li.b_algo')].map(li => ({
        t: (li.querySelector('h2') || {}).innerText || '',
        h: (li.querySelector('h2 a') || {}).href || '',
        site: (li.querySelector('cite') || {}).innerText || '',
        s: ((li.querySelector('.b_caption p, .b_lineclamp2, .b_lineclamp3, .b_paractl') || {}).innerText || '').slice(0, 200)}))""")
    links = [{"title": r["t"].strip(), "url": r["h"], "site": r["site"].strip()[:80], "snippet": r["s"].strip()} for r in rows if r["t"]]
    await page.close()
    return {"url": page.url, "guess": [], "links": links[:20], "text_head": ""}


async def run(images: list[Path], engines: list[str], out_dir: Path, proxy: str | None,
              queries: list[str] | None = None, text_engines: list[str] | None = None,
              similar_pages: int = 2, sheet_n: int = 24) -> list[dict]:
    from playwright.async_api import async_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    async with async_playwright() as p:
        async def browser():
            result, _ = await launch_browser(p, proxy)
            return result

        if queries:
            b = await browser()
            ctxs: dict = {}
            blocked: set[str] = set()
            for k, q in enumerate(queries):
                for eng in text_engines or []:
                    shot = out_dir / f"q{k + 1:02d}_{eng}.png"
                    for old in (shot, shot.with_name(shot.stem + "_2.png")):    # an earlier call's query had these names
                        old.unlink(missing_ok=True)
                    res = {"image": f"q{k + 1:02d}"}
                    if eng in blocked:              # a wall stays up for this session; asking again only hardens it
                        res["error"] = f"skipped: {eng} was blocked earlier in this run (not retried)"
                    else:
                        try:
                            if eng not in ctxs:
                                ctxs[eng] = await b.new_context(viewport={"width": 1400, "height": 1000},
                                                                locale=TEXT_LOCALE.get(eng, "en-US"))
                            res.update(await _text(ctxs[eng], eng, q, shot))
                        except Exception as e:  # noqa: BLE001
                            res["error"] = str(e)[:300]
                        if shot.exists():
                            res["screenshot"] = str(shot)
                        if res.get("blocked"):
                            blocked.add(eng)
                    res.update({"query": q, "engine": eng})
                    (out_dir / f"q{k + 1:02d}_{eng}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
                    results.append(res)
            await b.close()

        for eng in engines if images else []:
            b = await browser()
            ctx = await b.new_context(viewport={"width": 1400, "height": 1000},
                                      locale="zh-CN" if eng == "baidu" else "en-US")
            stems = [i.stem for i in images]
            for k, img in enumerate(images):
                name = img.stem if stems.count(img.stem) == 1 else f"{k + 1:02d}_{img.stem}"
                shot = out_dir / f"{name}_{eng}.png"
                try:
                    res = await (_baidu(ctx, img, shot, similar_pages, sheet_n, proxy) if eng == "baidu" else _yandex(ctx, img, shot))
                except Exception as e:  # noqa: BLE001
                    res = {"error": str(e)[:300]}
                res.update({"image": str(img), "engine": eng, "screenshot": str(shot)})
                (out_dir / f"{name}_{eng}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
                results.append(res)
            await b.close()
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--engines", default="baidu,yandex", help="reverse image search engines")
    ap.add_argument("--query", action="append", help="keyword search, repeatable")
    ap.add_argument("--country", metavar="XX", help="ISO2 country of the --query words: picks the engines that index its web ("
                    + "; ".join(f"{c} {','.join(e)}" for c, e in COUNTRY_ENGINES.items()) + f"; other or none {','.join(DEFAULT_ENGINES)})")
    ap.add_argument("--text-engines", help="keyword search engines, comma-separated; overrides --country: " + ",".join(TEXT_URL))
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    ap.add_argument("--exclude", help="comma-separated exclude words: results whose title contains them are not listed (e.g. to hide the puzzle's source in blind tests)")
    ap.add_argument("--similar-pages", type=int, default=2, help="how many more pages of Baidu similar images to load by scrolling past the first (about 30 per page)")
    ap.add_argument("--similar-sheet", type=int, default=24, help="how many of the top similar images to download into a contact sheet; 0 = no sheet")
    args = ap.parse_args()
    excl = [w for w in (args.exclude or "").split(",") if w]
    if not args.images and not args.query:
        ap.error("give image paths for reverse image search, or use --query for keyword search")
    missing = [str(p) for p in args.images if not p.is_file()]
    if missing:
        ap.error("image not found: " + ", ".join(missing))
    if args.country and not re.fullmatch(r"[A-Za-z]{2}", args.country):
        ap.error(f"--country takes an ISO2 code (KR, JP, RU…), not {args.country!r}")
    engines = [e for e in args.engines.split(",") if e in ("baidu", "yandex")]
    text_engines = pick_text_engines(args.country, args.text_engines)
    if args.query and all(len(q.split()) > 3 for q in args.query):   # long conjunctions mixing the anchor with the foreground found nothing
        print("Note: every --query has more than 3 words. Start with the settled town and the anchor's noun (2-3 words), then add one "
              "attribute per further --query; never a foreground feature.", file=sys.stderr)
    for r in asyncio.run(run(args.images, engines, args.out_dir, args.proxy, args.query, text_engines,
                             args.similar_pages, args.similar_sheet)):
        head = f"[{r['engine']}] {r['query'] if r.get('query') else Path(r['image']).name}"
        shots = "  screenshot " + "  ".join(r[k] for k in ("screenshot", "screenshot_2") if k in r) if "screenshot" in r else ""
        if r.get("error"):
            print(f"{head}  error: {r['error']}{shots}")
            continue
        print(f"{head}{shots}")
        for g in r["guess"][:2]:
            print(f"   guess: {g[:160]}")
        links = [ln for ln in r["links"] if not any(w in ln["title"] for w in excl)]
        if excl and (len(links) < len(r["links"]) or any(w in r.get("text_head", "") for w in excl)):
            print(f"   note: exclude words appear in the results; {len(r['links']) - len(links)} hidden; they may still be visible in the screenshot")
        for ln in links[:8]:
            print(f"   - {ln['title'][:60]}  ({ln['site']})")
        if r.get("similar"):
            tally = ", ".join(f"{s} {n}" for s, n in Counter(x["site"] for x in r["similar"]).most_common(6))
            print(f"   similar images: {len(r['similar'])} ({tally})" + (f"  contact sheet {r['similar_sheet']} (open it and look for the same object/scene)" if r.get("similar_sheet") else ""))
        elif r["engine"] == "baidu":
            print("   similar images: none captured")


if __name__ == "__main__":
    # Chinese-locale Windows writes GBK by default: m², ñ make it crash, and the Chinese the agent reads comes out garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
