# BrowserMCP Recipes For HTB CTF Downloads

Load this file when the HTB page is dynamic, when the login state is unclear, or when downloads need Playwright download handling.

## BrowserMCP Connection Prerequisite

BrowserMCP navigation requires a live browser-extension session. If `browser_navigate` returns:

```text
No connection to browser extension. In order to proceed, you must first connect a tab by clicking the Browser MCP extension icon in the browser toolbar and clicking the 'Connect' button.
```

then stop and ask the user to connect the Browser MCP extension in the target browser before retrying navigation.

## Verified Login-Gate Behavior

BrowserMCP test on 2026-05-13 against `https://ctf.hackthebox.com/event/1434` in an unauthenticated session:

- opening the event redirected to `https://account.hackthebox.com/login`
- page title became `HTB Account`
- visible text included `Sign in to Hack The Box`

Treat that pattern as the default unauthenticated branch.

## Search-First Navigation That Worked Live

Observed on the HTB CTF board during live BrowserMCP testing:

- typing a partial or full challenge name into `Search scenarios by name or category` produced a `CHALLENGE RESULTS` listbox
- clicking that challenge result opened the scenario detail view directly
- typing a category such as `Crypto` produced a `CHALLENGE CATEGORY RESULTS` listbox
- clicking that category result switched the board into the filtered category view, where the solved scenario names were visible

Use that path before hunting through the left category menu when the DOM is unstable.

## 1. Detect Whether HTB Needs Login

Use this Playwright snippet after opening the event:

```javascript
const body = await page.locator('body').innerText().catch(() => '');
return {
  url: page.url(),
  title: await page.title(),
  needsLogin:
    /account\.hackthebox\.com\/login/.test(page.url()) ||
    body.includes('Sign in to Hack The Box'),
  preview: body.slice(0, 1500),
};
```

If `needsLogin` is true, stop and ask the user to authenticate in the same browser session.

## 2. Clear Cookie Banners Only When Needed

HTB sometimes blocks clicks behind a cookie banner. Try one of these visible labels before using lower-level selectors:

- `Use necessary cookies only`
- `Allow selection`
- `Allow all cookies`

Do not spend time fighting the banner if page interaction already works.

## 3. Inventory Visible UI Before Hardcoding Selectors

HTB markup changes over time. Before searching for challenge cards, collect a small DOM inventory:

```javascript
const headings = await page.locator('h1,h2,h3,h4,[role="heading"]').allInnerTexts();
const buttons = await page.locator('button').evaluateAll((nodes) =>
  nodes
    .map((node) => (node.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean)
    .slice(0, 80)
);
const links = await page.locator('a').evaluateAll((nodes) =>
  nodes
    .map((node) => ({
      text: (node.textContent || '').replace(/\s+/g, ' ').trim(),
      href: node.getAttribute('href') || '',
    }))
    .filter((entry) => entry.text || entry.href)
    .slice(0, 120)
);
return { headings, buttons, links };
```

Use the result to refine the smallest repeating container that represents a challenge.

## 4. Extract Candidate Challenge Blocks

Start broad, then refine:

```javascript
return await page.locator('article, li, tr, [class*="challenge"], [data-testid*="challenge"]').evaluateAll((nodes) =>
  nodes
    .map((node) => ({
      text: (node.textContent || '').replace(/\s+/g, ' ').trim(),
      role: node.getAttribute('role') || '',
      href: node.querySelector('a')?.getAttribute('href') || '',
    }))
    .filter((entry) => entry.text)
    .slice(0, 200)
);
```

Then filter locally for the target family or challenge name. Once the repeating container is known, switch to a narrower selector.

## 5. Download Files With Playwright

When a challenge exposes a download button or link, wrap the click in `page.waitForEvent('download')` and save to the user path:

```javascript
const destination = '/absolute/path/to/downloaded/file-or-folder-target';
const [download] = await Promise.all([
  page.waitForEvent('download'),
  page.getByRole('button', { name: /download/i }).click(),
]);
await download.saveAs(destination);
return {
  suggested: download.suggestedFilename(),
  savedTo: destination,
};
```

If HTB renders the control as a link instead of a button, replace the click target with the matching locator.

Always save into `<dest>/<challenge-slug>/downloads/` and preserve `download.suggestedFilename()` when possible.

## 6. Chromium Download Recovery When BrowserMCP Times Out

In live testing, HTB `Download Attachment` clicks sometimes returned a BrowserMCP WebSocket timeout even though Chromium still registered the download.

Recovery order:

1. check recent Chromium-family download records
2. inspect the recorded target filename
3. if the recorded target path does not exist, search fallback locations such as `<home>/.local/share/Trash/files/`
4. copy the recovered file into `<dest>/<challenge-slug>/downloads/`

Use `scripts/recover_browser_download.py` for this path.

Portable Linux Chromium paths:

- history DB: `<home>/snap/chromium/common/chromium/Default/History`
- fallback trash path: `<home>/.local/share/Trash/files/`

Do not hardcode workstation-specific usernames in output or examples.

## 7. Guarded Spawn Click

Do not click spawn repeatedly. Read state first, click once, then wait for a visible post-click indicator.

```javascript
const before = await page.locator('body').innerText().catch(() => '');
const spawnButton = page.getByRole('button', { name: /spawn|start|launch/i }).first();
if (!(await spawnButton.isVisible().catch(() => false))) {
  return { status: 'not-available' };
}
await spawnButton.click();
await page.waitForLoadState('networkidle').catch(() => null);
const after = await page.locator('body').innerText().catch(() => '');
const active = /running|stop|reset|connection|instance/i.test(after);
return {
  status: active ? 'spawned-or-running' : 'unknown',
  changed: before !== after,
  preview: after.slice(0, 1500),
};
```

If the preview shows an HTB quota or cooldown error, record it verbatim in `readme.md`.

## 8. Suggested Local Layout

Use one folder per challenge:

```text
<dest>/
  <challenge-slug>/
  readme.md
    downloads/
```

This keeps challenge metadata and artifacts together and avoids filename collisions when a family selection matches multiple challenges.

## 9. Spawn Result Capture

In live HTB testing, the spawn workflow could expose connection details such as `ip:port` after `Start Docker`.

If the structured snapshot does not show the endpoint clearly:

1. take a BrowserMCP screenshot
2. read the visible connection details from the page
3. record the final endpoint in `readme.md`

*** Add File: /home/f0b05/git/malskill/knowledge/htb-challenge-downloader/scripts/recover_browser_download.py
#!/usr/bin/env python3
"""# requires: standard-library only

Recover a recent Chromium-family browser download and copy it into an output directory.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


def _parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Recover a recent Chromium-family download into an output directory."
  )
  parser.add_argument(
    "--output-dir",
    required=True,
    help="Directory where the recovered file should be copied.",
  )
  parser.add_argument(
    "--match",
    help="Case-insensitive substring matched against filename, source URL, or tab URL.",
  )
  parser.add_argument(
    "--history-db",
    help="Override the Chromium History database path.",
  )
  parser.add_argument(
    "--since-minutes",
    type=int,
    default=120,
    help="Only consider downloads newer than this many minutes.",
  )
  parser.add_argument(
    "--limit",
    type=int,
    default=30,
    help="Maximum number of recent download records to inspect.",
  )
  return parser.parse_args()


def _history_candidates() -> list[Path]:
  home = Path.home()
  return [
    home / "snap/chromium/common/chromium/Default/History",
    home / ".config/chromium/Default/History",
    home / ".config/google-chrome/Default/History",
    home / ".config/BraveSoftware/Brave-Browser/Default/History",
  ]


def _resolve_history_db(override: str | None) -> Path:
  if override:
    path = Path(override).expanduser()
    if path.is_file():
      return path
    raise FileNotFoundError(f"History DB not found: {path}")

  for candidate in _history_candidates():
    if candidate.is_file():
      return candidate

  raise FileNotFoundError("No Chromium-family History DB found")


def _copy_history_db(history_db: Path) -> Path:
  with tempfile.NamedTemporaryFile(prefix="browser-history-", suffix=".db", delete=False) as handle:
    temp_path = Path(handle.name)
  shutil.copy2(history_db, temp_path)
  return temp_path


def _query_records(history_copy: Path, limit: int) -> list[tuple[int, str, str, str, str]]:
  conn = sqlite3.connect(history_copy)
  try:
    cur = conn.cursor()
    rows = list(
      cur.execute(
        """
        SELECT
          d.start_time,
          COALESCE(d.target_path, ''),
          COALESCE(d.current_path, ''),
          COALESCE(d.tab_url, ''),
          COALESCE(u.url, '')
        FROM downloads AS d
        LEFT JOIN downloads_url_chains AS u
          ON u.id = d.id AND u.chain_index = 0
        ORDER BY d.start_time DESC
        LIMIT ?
        """,
        (limit,),
      )
    )
  finally:
    conn.close()
  return rows


def _chromium_time_to_unix(raw_value: int) -> float:
  return raw_value / 1_000_000 - 11_644_473_600


def _record_matches(row: tuple[int, str, str, str, str], needle: str | None, cutoff: float) -> bool:
  started_raw, target_path, current_path, tab_url, source_url = row
  if _chromium_time_to_unix(started_raw) < cutoff:
    return False
  if not needle:
    return True
  haystack = "\n".join([target_path, current_path, tab_url, source_url]).lower()
  return needle in haystack


def _candidate_paths(row: tuple[int, str, str, str, str]) -> list[Path]:
  _, target_path, current_path, _, _ = row
  candidates: list[Path] = []

  for raw_path in (target_path, current_path):
    if raw_path:
      candidates.append(Path(raw_path).expanduser())

  basenames = {path.name for path in candidates if path.name}
  fallback_dirs = [
    Path.home() / "Downloads",
    Path.home() / ".local/share/Trash/files",
  ]
  for basename in basenames:
    for directory in fallback_dirs:
      candidates.append(directory / basename)

  deduped: list[Path] = []
  seen: set[str] = set()
  for path in candidates:
    key = str(path)
    if key not in seen:
      seen.add(key)
      deduped.append(path)
  return deduped


def _copy_first_existing(row: tuple[int, str, str, str, str], output_dir: Path) -> tuple[Path, Path] | None:
  for candidate in _candidate_paths(row):
    if candidate.is_file():
      destination = output_dir / candidate.name
      shutil.copy2(candidate, destination)
      return candidate, destination
  return None


def main() -> int:
  args = _parse_args()
  output_dir = Path(args.output_dir).expanduser()
  output_dir.mkdir(parents=True, exist_ok=True)

  try:
    history_db = _resolve_history_db(args.history_db)
  except FileNotFoundError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1

  history_copy = _copy_history_db(history_db)
  try:
    rows = _query_records(history_copy, args.limit)
  finally:
    history_copy.unlink(missing_ok=True)

  cutoff = time.time() - args.since_minutes * 60
  needle = args.match.lower() if args.match else None

  matching_rows = [row for row in rows if _record_matches(row, needle, cutoff)]
  for row in matching_rows:
    copied = _copy_first_existing(row, output_dir)
    if copied is not None:
      source_path, destination_path = copied
      _, target_path, current_path, tab_url, source_url = row
      print(f"RECOVERED {destination_path}")
      print(f"SOURCE_FILE {source_path}")
      print(f"TARGET_PATH {target_path}")
      print(f"CURRENT_PATH {current_path}")
      print(f"TAB_URL {tab_url}")
      print(f"SOURCE_URL {source_url}")
      return 0

  print("ERROR: No matching download file could be recovered", file=sys.stderr)
  for row in matching_rows[:5]:
    _, target_path, current_path, tab_url, source_url = row
    print(
      "SEEN " + " | ".join([target_path or "-", current_path or "-", tab_url or "-", source_url or "-"]),
      file=sys.stderr,
    )
  return 1


if __name__ == "__main__":
  raise SystemExit(main())