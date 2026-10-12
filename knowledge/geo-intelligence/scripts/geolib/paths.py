"""Skill-relative paths, the download cache root and optional machine settings."""
from __future__ import annotations

import json
import os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILL_DIR = SCRIPTS_DIR.parent
DATA_DIR = SKILL_DIR / "assets" / "data"


def cache_root() -> Path:
    """GEOINT_CACHE, else ~/.cache/geoint; on Windows without ~/.cache, %LOCALAPPDATA%/geoint."""
    env = os.environ.get("GEOINT_CACHE")
    if env:
        return Path(env).expanduser()
    home_cache = Path.home() / ".cache"
    if os.name == "nt" and not home_cache.is_dir() and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "geoint"
    return home_cache / "geoint"


def cache_dir(*parts: str) -> Path:
    """Cache subdirectory, created on first use (creation errors are left to the caller's write)."""
    p = cache_root().joinpath(*parts)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return p


def local_config() -> dict:
    """Optional machine settings in <skill>/config.local.json (git-ignored): {"photos_root": ..., "timezone": ...}."""
    try:
        return json.loads((SKILL_DIR / "config.local.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
