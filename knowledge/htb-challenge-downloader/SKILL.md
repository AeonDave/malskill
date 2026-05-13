---
name: htb-challenge-downloader
description: "Download Hack The Box CTF challenge artifacts and metadata through BrowserMCP. Use when given an HTB CTF event URL, a destination path, and a selector describing either a challenge category or a challenge name. If any of those three inputs is missing, return an error and stop. The workflow filters matching challenges, downloads files when present, always spawns Docker when a spawn control exists, and writes one `readme.md` per challenge folder with title, description, and an `ip:porta` array when endpoints are exposed."
---

# HTB Challenge Downloader

## Overview

Use this skill to collect challenge artifacts from Hack The Box CTF events with BrowserMCP. It does not solve the challenge; it only finds the requested challenge set, downloads attached files when present, writes local metadata, and starts a Docker or instance whenever HTB exposes a spawn control.

## Inputs

Gather these required inputs before acting:

- event URL or challenge URL
- destination directory, for example `./testdownload`
- selector: exact challenge name or family/category

Treat "family" as the visible HTB category or badge text. Prefer exact challenge-name matches over substring matches.

If any of the three required inputs is missing, return an error and stop. Do not guess defaults, do not reuse an old destination, and do not start browsing the event without a selector.

## Workflow

### 1. Connect BrowserMCP to a live browser tab

1. Before any HTB navigation, ensure the Browser MCP browser extension is installed in the target browser.
2. Ask the user to click the Browser MCP extension icon in the browser toolbar and press `Connect`.
3. Only start navigation after the BrowserMCP server has an active browser-extension connection.
4. If BrowserMCP returns `No connection to browser extension`, stop and ask the user to connect the extension before retrying.

Why: the `browsermcp` MCP server cannot drive tabs until the browser extension is actively connected.

### 2. Open HTB and verify login

1. Open the provided HTB URL with BrowserMCP.
2. Check whether the page redirected to `account.hackthebox.com/login` or shows `Sign in to Hack The Box`.
3. If login is required, stop automation and ask the user to complete login and MFA in the same browser session.
4. After the user finishes login, return to the target event URL and continue in the same tab.
5. Never store credentials, session tokens, or MFA material in files, shell history, or tool output.

Why: HTB CTF event pages are gated. Unauthenticated sessions cannot enumerate challenges, download files, or spawn machines.

### 3. Enumerate and filter challenges

1. Dismiss cookie banners only if they block interaction.
2. Extract the visible challenge inventory with BrowserMCP.
3. Capture at least the challenge name, family/category, points if visible, and a clickable handle or URL.
4. Normalize whitespace and compare values case-insensitively.
5. Apply selection rules in this order:
	- exact normalized challenge-name match
	- exact normalized family/category match
	- case-insensitive contains match only as a fallback, with ambiguity reported before opening multiple targets
6. Prefer the search box when it is visible:
	- partial challenge names usually return a challenge result entry that opens the detail view directly
	- category names usually return a category result entry that switches the board into the filtered category view
7. Interpret the selector this way:
	- if it resolves to a category, process every challenge in that category and create one folder per challenge
	- if it resolves to a challenge name, process only that challenge and create one folder for it
8. If nothing matches, report the available challenge names or families and stop.
9. If a non-category selector matches multiple challenge names and no exact challenge-name match exists, return an ambiguity error instead of guessing.

If the user supplied a direct challenge URL, verify the name on the page before proceeding and skip broad event enumeration.

### 4. Extract metadata for each match

For each matched challenge:

1. Open the challenge detail view or dedicated challenge page.
2. Extract:
	- name
	- family/category
	- description
	- points if visible
	- source URL or current challenge URL
	- whether a downloadable file/button exists
	- whether a spawn/start/launch control exists
3. Create a local layout:

```text
<dest>/
  <challenge-slug>/
	 readme.md
	 downloads/
```

4. Keep one directory per challenge even when there is only one file or no file at all.
5. Create `downloads/` only when at least one attachment is recovered.

### 5. Download challenge files

1. If the challenge exposes a download control, use BrowserMCP download handling and save files into `<dest>/<challenge-slug>/downloads/`.
2. Preserve the server-provided filename when possible.
3. If a BrowserMCP click on the download button times out, do not assume the download failed. Recover the file with `scripts/recover_browser_download.py` before marking it missing.
4. On Chromium-family browsers, check recent browser download records first and then fallback locations such as the system trash when the target path is missing.
5. If no files exist, do not create fake placeholders. Record an empty downloads array in the metadata instead.
6. If HTB shows a disabled control or download error, capture the visible error text and stop for that challenge.

### 6. Spawn the machine or instance

1. If the challenge exposes a spawn/start/launch control, click it once. Spawning is mandatory when the control exists.
2. Wait for a clear state change such as `Running`, `Stop`, `Reset`, connection details, or another active-instance indicator.
3. If the challenge is already running, record `already running` rather than forcing a respawn.
4. Capture every visible endpoint as an `ip:porta` array, even if only one endpoint appears.
5. If spawn is quota-limited or unavailable, capture the visible status and continue.
6. Do not loop on timeouts. Re-read the page state before any second click.

### 7. Write `readme.md`

After metadata extraction, downloads, and spawn handling, write `<dest>/<challenge-slug>/readme.md` with `scripts/write_challenge_markdown.py`.

Include:

- title/name
- family/category
- description
- source URL
- local download filenames as an array
- `ip:porta` values as an array when Docker or another spawned target exposes endpoints
- spawn status
- retrieval date

The helper expects JSON on stdin or via `--input`. Use it after BrowserMCP work is finished so the markdown reflects the final download and spawn state.

### 8. Report outcome

Summarize, per matched challenge:

- saved directory
- downloaded files array
- `ip:porta` array when present
- spawn result
- blockers or HTB-side errors

## BrowserMCP Rules

- Reuse one authenticated tab for the whole workflow.
- Prefer normal browser open and click actions first.
- Use Playwright snippets when HTB renders dynamic challenge lists, when structured extraction is easier in code, or when downloads require `page.waitForEvent('download')`.
- Keep downloads inside the user-specified destination path.
- On Linux Chromium setups, verify whether the browser moved the file into a browser-managed fallback location before declaring the download missing.
- Do not claim success until the file exists locally and the page state shows the final spawn result.

## Failure Handling

- BrowserMCP not connected: ask the user to connect the browser extension and retry the same navigation.
- Missing required input: return an error and stop.
- Login wall: ask the user to sign in manually, then resume.
- Missing matches: report visible names or families.
- Ambiguous challenge-name selector: return an error and stop.
- Download click timeout: inspect Chromium download history and fallback file locations with `scripts/recover_browser_download.py` before calling the attachment unavailable.
- No download control: record an empty downloads array and continue.
- Spawn not available: record the visible status and continue.
- Rate limit, 403, or expired event: stop and report the HTB message verbatim.

## Example

Input:

- URL: `https://ctf.hackthebox.com/event/1434`
- destination: `./testdownload`
- family: `Web`

Expected agent flow:

1. Open the HTB event with BrowserMCP.
2. Wait for the user to log in if HTB redirects to the account portal.
3. Collect all `Web` challenges.
4. Save each challenge under `./testdownload/<challenge-slug>/`.
5. Write `readme.md`.
6. Download attached files.
7. Spawn the machine-backed challenge if HTB exposes the control.

Single-challenge example:

- URL: `https://ctf.hackthebox.com/event/1434`
- destination: `./pippo/caio`
- selector: `Jailbreak`

Result:

1. Match the challenge `Jailbreak` by name.
2. Create `./pippo/caio/Jailbreak/`.
3. Download attachments if present.
4. Spawn Docker if present.
5. Write `./pippo/caio/Jailbreak/readme.md` with title, description, downloads array, and `ip:porta` array.

## Resources

### scripts/

- `scripts/write_challenge_markdown.py` — write deterministic `readme.md` files from extracted JSON metadata after BrowserMCP finishes a challenge.
- `scripts/recover_browser_download.py` — recover recent Chromium-family downloads from browser history and fallback locations, then copy them into the challenge `downloads/` directory.

### references/

- `references/browsermcp-recipes.md` — HTB-specific BrowserMCP and Playwright patterns for login-gate detection, challenge extraction, download saving, and guarded spawning.
