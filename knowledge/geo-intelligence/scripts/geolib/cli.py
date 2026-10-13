"""Command-line plumbing shared by the scripts: negative-coordinate arguments, UTF-8 console, label fonts, torch device,
contact sheets."""
from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from pathlib import Path

from .accel import CHILD, GPU_CMD, NO_DEVICE, requested

_NEG = re.compile(r"^-\d[\d.]*([,:@]-?[\d.]+)+$")   # lat,lon; lat,lon:lat,lon spans (board.py --covers); lat,lon@bearing (geo.py --sight)


def neg_coords(argv: list[str]) -> list[str]:
    """argparse treats negative coordinates like -1.45,-48.5 as option names; a leading space makes them plain values
    (float() ignores it). Needed for every southern- or western-hemisphere point, in every lat,lon-led value shape."""
    return [" " + a if _NEG.match(a) else a for a in argv]


def utf8_stdio() -> None:
    """UTF-8 console output: Windows code pages (cp1252, GBK) crash on m², ñ and CJK, or garble them."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


# ---------------------------------------------------------------- label fonts

_MAC, _LINUX = "/System/Library/Fonts", "/usr/share/fonts"


def _font_dirs() -> list[Path]:
    """Existing font folders of this platform, system first, then per-user; bare file names are tried here before
    Pillow's own search (which matches case-sensitively, so arial.ttf would miss /Library/Fonts/Arial.ttf)."""
    home = Path.home()
    if sys.platform == "darwin":
        dirs = [Path(_MAC), Path(_MAC) / "Supplemental", Path("/Library/Fonts"), home / "Library" / "Fonts"]
    elif os.name == "nt":
        dirs = [Path(v) / sub for v, sub in ((os.environ.get("WINDIR") or os.environ.get("SystemRoot"), "Fonts"),
                                             (os.environ.get("LOCALAPPDATA"), "Microsoft/Windows/Fonts")) if v]
    else:
        data_home = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
        data_dirs = (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
        dirs = [data_home / "fonts", home / ".fonts", *(Path(d) / "fonts" for d in data_dirs if d)]
    return [d for d in dirs if d.is_dir()]


# per script: macOS and Linux paths, then bare file names (tried in _font_dirs(), then resolved by Pillow itself)
_FONTS = {
    "latin": [f"{_MAC}/Supplemental/Arial.ttf", f"{_MAC}/Helvetica.ttc", f"{_LINUX}/truetype/dejavu/DejaVuSans.ttf",
              "arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "sylfaen.ttf"],
    "han": [f"{_MAC}/Hiragino Sans GB.ttc", f"{_MAC}/STHeiti Medium.ttc", f"{_MAC}/Supplemental/Arial Unicode.ttf",
            f"{_LINUX}/opentype/noto/NotoSansCJK-Regular.ttc", "msyh.ttc", "msjh.ttc", "simsun.ttc", "NotoSansCJK-Regular.ttc"],
    "kana": [f"{_MAC}/ヒラギノ角ゴシック W3.ttc", f"{_MAC}/Hiragino Sans GB.ttc", f"{_MAC}/Supplemental/Arial Unicode.ttf",
             f"{_LINUX}/opentype/noto/NotoSansCJK-Regular.ttc", "YuGothR.ttc", "YuGothM.ttc", "msgothic.ttc", "msyh.ttc"],
    "hangul": [f"{_MAC}/AppleSDGothicNeo.ttc", f"{_MAC}/Supplemental/Arial Unicode.ttf",
               f"{_LINUX}/opentype/noto/NotoSansCJK-Regular.ttc", "malgun.ttf", "msyh.ttc"],
    "thai": [f"{_MAC}/Supplemental/Arial Unicode.ttf", f"{_MAC}/Thonburi.ttc", f"{_LINUX}/truetype/noto/NotoSansThai-Regular.ttf",
             "LeelawUI.ttf", "tahoma.ttf"],
    "indic": [f"{_MAC}/Supplemental/Arial Unicode.ttf", f"{_MAC}/Kohinoor.ttc", f"{_LINUX}/truetype/noto/NotoSansDevanagari-Regular.ttf",
              "Nirmala.ttc", "Nirmala.ttf"],
    "ethiopic": [f"{_MAC}/Supplemental/Kefa.ttc", f"{_LINUX}/truetype/noto/NotoSansEthiopic-Regular.ttf", "ebrima.ttf"],
    "wide": [f"{_MAC}/Supplemental/Arial Unicode.ttf", f"{_MAC}/Hiragino Sans GB.ttc", f"{_MAC}/STHeiti Medium.ttc",
             f"{_LINUX}/opentype/noto/NotoSansCJK-Regular.ttc", "arialuni.ttf", "msyh.ttc", "seguisym.ttf", "ebrima.ttf"],
}


def _script(text: str) -> str:
    """Coarse script of a label, enough to pick a font that has its glyphs."""
    for ch in text:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF:
            return "hangul"
        if 0x3040 <= o <= 0x30FF:
            return "kana"
    for ch in text:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF:
            return "han"
        if 0x0E00 <= o <= 0x0E7F:
            return "thai"
        if 0x0900 <= o <= 0x0DFF:
            return "indic"
        if 0x1200 <= o <= 0x139F:
            return "ethiopic"
        if o >= 0x0900:             # Hebrew/Arabic (0x0590-0x08FF) stay with Arial/DejaVu, which carry them
            return "wide"
    return "latin"


@lru_cache(maxsize=64)
def _load(size: int, key: str):
    from PIL import ImageFont
    dirs = _font_dirs()
    order = _FONTS[key] + [f for k in ("wide", "latin") if k != key for f in _FONTS[k]]
    for name in order:
        cands = [name] if "/" in name else [*(str(d / name) for d in dirs), name]
        for c in cands:
            try:
                return ImageFont.truetype(c, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size)      # Pillow >= 10.1: scalable default font
    except TypeError:
        return ImageFont.load_default()


def font(size: int, text: str = "", prefer_wide: bool = False):
    """Label font for `text`: Arial-like for Latin/Cyrillic/Greek, CJK/Hangul/Kana/Thai/Indic fonts otherwise.
    Without text, prefer_wide picks a font that also has CJK glyphs (Chinese labels drawn later)."""
    key = _script(text) if text else ("wide" if prefer_wide else "latin")
    return _load(int(size), key)


# ---------------------------------------------------------------- torch device

DEVICES = ("auto", "cuda", "xpu", "mps", "cpu")


def device(allow_mps: bool = True, want: str | None = None):
    """Torch device for every model: `want` (a script's --device), else GEOINT_DEVICE, else auto = cuda (ROCm too) → xpu →
    mps → cpu. allow_mps=False restricts to cuda/cpu (GeoCalib needs float64 linear algebra): mps/xpu requests then fall
    back to cpu with a note. In the GPU environment (geolib.accel) a cpu result exits NO_DEVICE instead: the parent reruns
    on the default environment's CPU torch, as the GPU builds' own CPU path is far slower (no MKL in the ROCm build)."""
    import torch
    want = requested(want)
    if want == "directml":
        sys.exit("DirectML is not supported (wrong MegaLoc and GeoCLIP results); AMD and Intel GPUs on Windows: "
                 f"`{GPU_CMD}` builds the GPU environment once")
    if want not in DEVICES:
        sys.exit(f"GEOINT_DEVICE={want!r} is not one of {'|'.join(DEVICES)}")
    if not allow_mps and want in ("mps", "xpu"):
        print(f"{want} is not supported by this model (float64 linear algebra); using cpu", file=sys.stderr)
        want = "cpu"
    if want == "auto":
        xpu, mps = getattr(torch, "xpu", None), getattr(torch.backends, "mps", None)
        want = ("cuda" if torch.cuda.is_available() else
                "xpu" if allow_mps and xpu is not None and xpu.is_available() else
                "mps" if allow_mps and mps is not None and mps.is_available() else "cpu")
    if want == "cpu" and os.environ.get(CHILD):
        sys.exit(NO_DEVICE)
    return torch.device(want)


# ---------------------------------------------------------------- contact sheets

def contact_sheet(cells: list, out, cols: int = 3, tw: int = 480, th: int = 360, bar: int = 22, font_size: int = 16,
                  fit: str = "stretch", quality: int = 88) -> None:
    """cells: [(PIL image, label)] -> black grid, one yellow label bar per cell (gsv, baidu_pano, pano and sweep sheets).
    fit: "stretch" resizes to the cell, "contain" keeps the aspect ratio and centres the image."""
    from PIL import Image, ImageDraw
    rows = max(1, (len(cells) + cols - 1) // cols)
    S = Image.new("RGB", (cols * tw, rows * th), "black")
    d = ImageDraw.Draw(S)
    for i, (im, lab) in enumerate(cells):
        x, y = (i % cols) * tw, (i // cols) * th
        im = im.convert("RGB")
        if fit == "contain":
            im.thumbnail((tw, th))
            S.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        else:
            S.paste(im.resize((tw, th)), (x, y))
        d.rectangle([x, y, x + tw, y + bar], fill="black")
        d.text((x + 4, y + 2), lab, fill="yellow", font=font(font_size, lab, prefer_wide=True))
    S.save(out, quality=quality)


def failed_cells(ims: list) -> list[str]:
    """Error messages of the cells that failed to render: a renderer's grey placeholder carries info["failed"]."""
    return [im.info["failed"] for im in ims if im.info.get("failed")]


def sheet_failures(failed: list[str], n: int) -> None:
    """Outcome of a street-level sheet run of n cells: exit when every cell failed (grey outage tiles are no street check,
    so the caller writes no index either), else note the failed share on stderr."""
    if n and len(failed) == n:
        sys.exit(f"every one of the {n} cells failed ({failed[0]}): no sheet written, so this is not a street check. "
                 "Rerun to retry; doctor.py --network checks service access; with no street-level imagery, evidence.py on the "
                 "tiles.py map is the street check")
    if failed:
        print(f"{len(failed)}/{n} cells failed (first: {failed[0]}); grey cells are not views; rerun to retry them", file=sys.stderr)


def sheet_pages(pages: list[list], out: Path, render, draw) -> list[Path]:
    """Street-level sheet pages out, out_2, out_3…: render(page) -> images, draw(page, images, path) writes one page.
    Whether every cell failed is decided over the whole run (sheet_failures): then nothing is written; otherwise every
    page is drawn, an all-grey one too, so the sheet at `out` always sits beside the caller's index. A page with a real
    view is drawn at once; an all-grey one waits for the verdict. Returns the written paths in page order."""
    written, held, failed, n = {}, [], [], 0
    for i, page in enumerate(pages):
        path = out if i == 0 else out.with_name(f"{out.stem}_{i + 1}{out.suffix}")
        ims = render(page)
        bad = failed_cells(ims)
        failed += bad
        n += len(ims)
        if ims and len(bad) == len(ims):
            held.append((i, page, ims, path))
        else:
            draw(page, ims, path)
            written[i] = path
    sheet_failures(failed, n)
    for i, page, ims, path in held:
        draw(page, ims, path)
        written[i] = path
    return [written[i] for i in sorted(written)]
