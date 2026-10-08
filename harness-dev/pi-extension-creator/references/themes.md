# Themes

Load this when authoring a Pi theme JSON file — choosing color roles or color syntax, setting `appearance`, `vars`, HTML `export` colors, the `system` theme, or switching/reading themes from an extension. For redesign *extensions* (chrome, footer/header/editor, renderers, auto-switch logic), use [advanced-redesign.md](advanced-redesign.md).

A theme is a JSON resource, not an extension — it carries no code. Pi ships `system` (default), `dark`, and `light`.

## File format

```json
{
  "$schema": "https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/schemas/theme.schema.json",
  "name": "my-theme",
  "appearance": "dark",
  "vars": { "primary": "okhsl(250 60% 55%)" },
  "colors": { "accent": "primary", "text": "#e6e6e6" },
  "export": { "pageBg": "#111111", "cardBg": "#1a1a1a" }
}
```

| Property | Required | Role |
|---|---|---|
| `$schema` | no | Editor validation and completion against Pi's published schema. |
| `name` | yes | Unique; cannot contain `/`; cannot be `system`. Must match the filename to hot-reload. |
| `appearance` | no | `"dark"` or `"light"` — the background the theme targets. Detected from the colors when omitted. |
| `vars` | no | Reusable color values; may reference other vars. A missing or circular reference makes the theme invalid. |
| `colors` | yes | A color per interface role. The schema marks required vs optional roles. |
| `export` | no | Overrides page and panel backgrounds in HTML exports. |

## Color forms

| Form | Example | Meaning |
|---|---|---|
| sRGB hex | `"#0af"`, `"#00aaff"` | 3- or 6-digit sRGB. |
| OKLCH | `"oklch(62% 0.1 200)"` | Perceptual lightness, chroma, hue. |
| OKHSL | `"okhsl(250 60% 55%)"` | Hue, saturation (relative to the in-gamut maximum), lightness. Built-in themes use this. |
| 256-color index | `39` | ANSI palette index `0`–`255`. |
| Variable reference | `"primary"` | The value of a `vars` entry (chained references resolve). |
| Terminal default | `""` | The terminal's own foreground or background color. |

Pi uses truecolor when available, gamut-maps OKLCH to sRGB, and approximates on 256-color terminals. HTML export converts OKHSL to hex because CSS lacks it.

## Color roles

Locate the role to change by area:

| Area | Color names |
|---|---|
| General | `accent`, `border*`, `text`, `muted`, `dim`, `success`, `error`, `warning` |
| Selection and fullscreen | `selectedBg`, `searchMatch*`, `scrollbar*` |
| Messages | `userMessage*`, `customMessage*`, `thinkingText` |
| Tool execution | `toolPendingBg`, `toolSuccessBg`, `toolErrorBg`, `toolTitle`, `toolOutput` |
| Markdown | `md*` |
| Tool diffs | `toolDiff*` |
| Syntax highlighting | `syntax*` |
| Editor modes | `thinking*`, `bashMode` |
| HTML export | `export.pageBg`, `export.cardBg`, `export.infoBg` |

Optional colors inherit when omitted: `scrollbarTrack`→`muted`, `scrollbarThumb`→`text`, `searchMatchBg`→`selectedBg`, `searchMatchText`→`text`, `thinkingMax`→`thinkingXhigh`. Omitted `export` colors derive from `userMessageBg`.

Copy a [built-in theme](https://github.com/earendil-works/pi/tree/main/packages/coding-agent/src/modes/interactive/theme) for the complete required-color set; the published [schema](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/schemas/theme.schema.json) is the authority on required and optional roles. The file-format snippet omits required colors; do not use it as a complete theme.

For a source checkout newer than the 1.1.0 release, use its `schemas/theme.schema.json`: theme loading rejects unknown top-level, `colors`, and `export` properties. Put reusable custom colors under `vars` and remove unsupported metadata. For a released host, validate against that host's schema rather than assuming `main` has the same contract.

## Load and select

- Save as `<agent-dir>/themes/<name>.json` (default `~/.pi/agent/themes/`); the active user theme hot-reloads only from there. Put project themes in `.pi/themes/` (loaded after project trust). Themes can also come from the `themes` setting or a Pi package.
- Select in `/settings` → Theme, or set `"theme": "my-theme"` (use `"light/dark"` for an auto pair). `--use-theme <name>` overrides for one run without saving.
- `system` is reserved (a custom theme named `system` is ignored). Names cannot contain `/`. Duplicate names are reported as resource collisions. Run `/reload` after changing a theme from any non-active source.

## The `system` theme

The default derives Pi's colors from the terminal's reported foreground, background, and 16 ANSI colors, setting each color's lightness for a minimum contrast (body text ≥ 4.5:1), and rebuilds when the terminal switches light/dark. With no reported colors it falls back to ANSI indices the terminal renders itself.

## Use themes from an extension

- `ctx.ui.getAllThemes()` returns `{ name, path }[]`; `ctx.ui.getTheme(name)` returns a `Theme` or `undefined`; `ctx.ui.setTheme(nameOrTheme)` returns `{ success, error? }`.
- In renderers, color with the passed `Theme`: `theme.fg("accent", text)`, `theme.style(...)`, `theme.colors`, and `theme.appearance`. Use semantic role names, never hardcoded ANSI values, so a theme switch restyles the extension.
- Switch the theme only in an explicit user flow or a documented auto-switch; do not force one at startup unless that is the package's purpose.
