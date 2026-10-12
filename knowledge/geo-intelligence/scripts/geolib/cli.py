"""Command-line plumbing shared by the scripts: negative-coordinate arguments, UTF-8 console, label fonts, torch device."""
from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from pathlib import Path

_NEG = re.compile(r"^-\d[\d.]*([,:]-?[\d.]+)+$")   # lat,lon and lat,lon:lat,lon spans (board.py --covers)


def neg_coords(argv: list[str]) -> list[str]:
    """argparse treats negative coordinates like -1.45,-48.5 as option names; a leading space makes them plain values
    (float() ignores it). Needed for every southern- or western-hemisphere point."""
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

DEVICES = ("auto", "cuda", "mps", "cpu", "directml")


def _directml():
    """torch_directml's device (AMD/Intel GPUs on Windows), or None when the package is missing or finds no adapter."""
    try:
        import torch_directml
        return torch_directml.device()
    except Exception:  # noqa: BLE001 - ImportError, or a runtime error from a broken DirectML install
        return None


def device(allow_mps: bool = True, want: str | None = None):
    """Torch device for every model: `want` (a script's --device), else GEOINT_DEVICE, else auto = cuda → mps → DirectML → cpu.
    Returns a torch.device, or torch_directml's device object. allow_mps=False restricts to cuda/cpu (GeoCalib needs
    float64 linear algebra): mps/directml requests then fall back to cpu with a note."""
    import torch
    want = (want if want and want != "auto" else os.environ.get("GEOINT_DEVICE") or "auto").strip().lower()
    if want not in DEVICES:
        sys.exit(f"GEOINT_DEVICE={want!r} is not one of {'|'.join(DEVICES)}")
    if not allow_mps and want in ("mps", "directml"):
        print(f"{want} is not supported by this model (float64 linear algebra); using cpu", file=sys.stderr)
        return torch.device("cpu")
    if want == "directml":
        dml = _directml()
        if dml is None:
            sys.exit("GEOINT_DEVICE=directml but torch_directml is not installed or finds no adapter (pip install torch-directml)")
        return dml
    if want != "auto":
        return torch.device(want)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if allow_mps and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    dml = _directml() if allow_mps else None
    return dml if dml is not None else torch.device("cpu")


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
