# Pi Advanced Redesign Extensions

## Table of Contents

- [Decision](#decision)
- [Capability Map](#capability-map)
- [Architecture](#architecture)
- [Theme Package Pattern](#theme-package-pattern)
- [Chrome Replacement](#chrome-replacement)
- [Message And Tool Rendering](#message-and-tool-rendering)
- [Editor And Overlay](#editor-and-overlay)
- [State And Refresh](#state-and-refresh)
- [Mode Limits](#mode-limits)
- [Validation](#validation)
- [Source Anchors](#source-anchors)

## Decision

Use a JSON theme only when the request is limited to colors.

Use an extension when the request includes any of these verbs:

- Hide built-in UI.
- Show new persistent UI.
- Replace header, footer, status line, editor, or widgets.
- Collapse, restyle, or enrich tool output.
- Add a dashboard, modal, side panel, selector, or alternate editor.
- Switch themes automatically.

Use a Pi package when the redesign needs both:

- `themes/*.json` for color tokens.
- An extension for layout, visibility, dynamic state, and renderers.

Do not describe an advanced redesign as a "theme" in code. Name it as a package or extension, such as `pi-redesign`, with an optional bundled theme.

## Capability Map

| Requirement | Surface |
|---|---|
| Change all semantic colors | JSON theme |
| Load/share theme with an extension | `package.json` `pi.themes` or conventional `themes/` |
| Switch active theme | `ctx.ui.setTheme(nameOrTheme)` (returns `{ success, error? }`) |
| Set terminal window/tab title | `ctx.ui.setTitle(text)` |
| Hide streaming working row | `ctx.ui.setWorkingVisible(false)` |
| Replace working-row text | `ctx.ui.setWorkingMessage(text)` (omit arg to reset) |
| Hide spinner only | `ctx.ui.setWorkingIndicator({ frames: [] })` |
| Rename collapsed thinking | `ctx.ui.setHiddenThinkingLabel(label)` |
| Add footer status fragments | `ctx.ui.setStatus(key, text)` |
| Replace footer completely | `ctx.ui.setFooter(factory)` |
| Replace startup header | `ctx.ui.setHeader(factory)` |
| Add persistent panel near editor | `ctx.ui.setWidget(key, content, { placement })` |
| Replace input editor | `ctx.ui.setEditorComponent(factory)` |
| Show focused custom UI | `ctx.ui.custom(factory, options)` |
| Render extension messages | `pi.registerMessageRenderer(customType, renderer)` |
| Render custom tool calls/results | tool `renderCall` and `renderResult` |
| Expand/collapse built-in tool output | `ctx.ui.setToolsExpanded(expanded)` |

Treat themes as semantic color contracts. Treat extensions as UI behavior.

## Architecture

Advanced redesigns should be split into modules:

```text
pi-redesign/
├── package.json
├── extensions/
│   ├── index.ts
│   ├── footer.ts
│   ├── renderers.ts
│   └── state.ts
└── themes/
    └── redesign.json
```

Use this split:

- `index.ts`: event wiring, commands, mode guards, cleanup.
- `footer.ts`: pure width-aware render logic.
- `renderers.ts`: message/tool renderer definitions.
- `state.ts`: session-derived state and async refresh caches.
- `themes/*.json`: all required theme color tokens.

Keep TUI components deterministic:

- Implement `render(width): string[]`.
- Truncate with `truncateToWidth`.
- Measure styled strings with `visibleWidth`.
- Store async data in cache fields.
- Call `tui.requestRender()` after async data changes.
- Return `dispose()` for timers, subscriptions, and watchers.

Do not run shell commands, network calls, or filesystem scans from `render()`.

## Theme Package Pattern

Package manifest:

```json
{
  "name": "pi-redesign",
  "type": "module",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./extensions/index.ts"],
    "themes": ["./themes"]
  },
  "peerDependencies": {
    "@earendil-works/pi-coding-agent": "*",
    "@earendil-works/pi-tui": "*",
    "typebox": "*"
  }
}
```

If the extension imports `@earendil-works/pi-ai` types at runtime or typecheck time, add it to peer dependencies.

Theme JSON rules:

- Define all required color tokens.
- Use semantic tokens in code: `theme.fg("accent", text)`, not hardcoded ANSI colors.
- Use `export` colors only for HTML export styling.
- Include project themes only after project trust.
- Use `resources_discover` only for dynamic theme path discovery.

Use `ctx.ui.setTheme("redesign")` only in explicit user-controlled flows or documented auto-switch behavior. Avoid surprising users by forcing a theme at startup unless the package is dedicated to that behavior.

## Chrome Replacement

Footer replacement pattern:

```ts
ctx.ui.setFooter((tui, theme, footerData) => {
  const unsub = footerData.onBranchChange(() => tui.requestRender());
  return {
    dispose: unsub,
    invalidate() {},
    render(width: number): string[] {
      const branch = footerData.getGitBranch();
      const left = theme.fg("accent", ctx.model?.id ?? "no-model");
      const right = theme.fg("dim", branch ? `git:${branch}` : ctx.cwd);
      return [fitLine(left, right, width)];
    },
  };
});
```

Footer data exposes values not otherwise reachable from `ctx`:

- Current git branch.
- Extension statuses created with `ctx.ui.setStatus()`.
- Branch-change subscription.

Read these from `ctx` instead:

- Model and provider.
- Context usage.
- Session entries and assistant token usage.
- Current cwd.
- System prompt and thinking level through Pi APIs.

Header replacement:

- Use `setHeader()` for startup branding, short session context, or mode hints.
- Do not put live data in the header unless you can invalidate it.
- Restore with `ctx.ui.setHeader(undefined)`.

Widgets:

- Use `aboveEditor` for transient task dashboards.
- Use `belowEditor` for statusline-style bars.
- Clear widgets on disable or shutdown with `ctx.ui.setWidget(key, undefined)`.
- Prefer string arrays for simple widgets and component factories for width-aware bars.

Working row:

- `setWorkingVisible(false)` hides the built-in loader row.
- `setWorkingMessage(text)` replaces the loader text without hiding the row; call with no argument to restore the default.
- If hidden, show equivalent progress in footer, widget, title, or message renderer.
- Restore with `setWorkingVisible(true)` when disabling the redesign.

## Message And Tool Rendering

Use custom message rendering for extension-owned session entries:

```ts
pi.registerMessageRenderer("redesign.event", (message, { expanded }, theme) => {
  const suffix = expanded && message.details ? `\n${JSON.stringify(message.details, null, 2)}` : "";
  return new Text(theme.fg("customMessageLabel", "[redesign] ") + message.content + suffix, 0, 0);
});
```

Use tool renderers when a custom tool should have a dense collapsed view:

- `renderCall(args, theme, context)` renders the pending call.
- `renderResult(result, options, theme, context)` renders completed or partial output.
- Return TUI `Component`s, not strings.
- Put LLM-facing facts in `content`.
- Put UI/state facts in `details`.
- Keep collapsed output one to three lines when possible.
- Use `options.expanded` to reveal details.

Registering a tool with the same name as a built-in can replace behavior. Only do this when the redesign intentionally changes the built-in workflow and preserves expected argument semantics.

## Editor And Overlay

Use `setEditorComponent()` only for a true editor redesign:

- Vim/modal editor.
- Prompt history overlay.
- Border/status editor.
- Alternate keyboard model.

Extend `CustomEditor` and call `super.handleInput(data)` for keys not owned by the extension. This preserves app-level keybindings and normal editing behavior.

Use `ctx.ui.custom()` for focused workflows:

- Settings panels.
- Pickers.
- Multi-step confirmations.
- Side panels and overlays.

Rules:

- Guard with `ctx.mode === "tui"`.
- Use the injected `keybindings` argument.
- Return `done(result)` on completion.
- Use `{ overlay: true }` only when the component should render over existing content.
- Provide a non-TUI fallback for required decisions.

## State And Refresh

For live chrome:

- Cache expensive data outside render.
- Refresh from lifecycle events such as `session_start`, `turn_end`, `tool_result`, `model_select`, and `thinking_level_select`.
- Reflect a "waiting for user" state from `ui_prompt_start` / `ui_prompt_end` when a custom footer or statusline replaces the built-in working row.
- Use timers only when event-driven refresh is insufficient.
- Clear timers on `session_shutdown`.
- Keep `dispose()` idempotent.

For VCS status:

- Prefer `footerData.getGitBranch()` for branch name.
- Run `git --no-optional-locks status --porcelain` asynchronously if dirty counts are needed.
- Invalidate after write/edit/bash/user_bash events that can change VCS state.
- Never block render on git.

For context and cost:

- Use `ctx.getContextUsage()` for current context window state.
- Walk `ctx.sessionManager.getBranch()` only when aggregate token or cost history is needed.
- Recompute aggregates outside render for large sessions if rendering becomes slow.

## Mode Limits

Mode behavior:

| Mode | Redesign behavior |
|---|---|
| `tui` | Full redesign: footer/header/widgets/editor/custom components/theme switching |
| `rpc` | Dialogs, notify, status, title, editor text, and simple widgets can work through protocol; component factories, footer, header, working indicator, custom UI, editor replacement, and theme switching are no-op or degraded |
| `json` | No UI; return data and decisions only |
| `print` | No UI; avoid redesign side effects |

Guard rules:

```ts
if (!ctx.hasUI) return;
ctx.ui.setStatus("redesign", "loaded");

if (ctx.mode !== "tui") return;
ctx.ui.setFooter(/* component factory */);
```

Do not use `ctx.hasUI` alone for TUI components.

## Validation

Run:

```bash
npm install
npm run typecheck
npm test
pi -e .
```

Manual redesign checks:

- Start in TUI mode and verify no overlapping text at narrow and wide terminal widths.
- Toggle the redesign off and confirm default footer/header/editor/working row return.
- Run a tool while streaming and confirm progress remains visible if the working row is hidden.
- Trigger `/reload` and confirm timers/subscriptions are not duplicated.
- Test `--mode rpc`, `--mode json`, or `-p` when the package may run outside TUI.
- Change git branch or dirty state and confirm async UI refresh does not block input.
- Expand and collapse custom messages/tool output.
- Switch themes and confirm semantic token usage still reads correctly.

## Source Anchors

Use these as implementation anchors:

- Pi extension docs: https://pi.dev/docs/latest/extensions
- Pi theme docs: https://pi.dev/docs/latest/themes
- Pi TUI component docs: https://pi.dev/docs/latest/tui
- Pi RPC docs: https://pi.dev/docs/latest/rpc
- Official extension examples: https://github.com/earendil-works/pi/tree/main/packages/coding-agent/examples/extensions

Local source paths to verify before coding against a checked-out Pi version:

- `<pi-repo>/packages/coding-agent/src/core/extensions/types.ts`
- `<pi-repo>/packages/coding-agent/docs/extensions.md`
- `<pi-repo>/packages/coding-agent/docs/themes.md`
- `<pi-repo>/packages/coding-agent/docs/rpc.md`
- `<pi-repo>/packages/coding-agent/examples/extensions/custom-footer.ts`
- `<pi-repo>/packages/coding-agent/examples/extensions/custom-header.ts`
- `<pi-repo>/packages/coding-agent/examples/extensions/message-renderer.ts`
- `<pi-repo>/packages/coding-agent/examples/extensions/border-status-editor.ts`
