import type {
  ExtensionAPI,
  ExtensionContext,
  ReadonlyFooterDataProvider,
  Theme,
} from "@earendil-works/pi-coding-agent";
import type { Component } from "@earendil-works/pi-tui";
import { Text, truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";

function fitLine(left: string, right: string, width: number): string {
  if (width <= 0) return "";
  const leftWidth = visibleWidth(left);
  const rightWidth = visibleWidth(right);
  if (leftWidth + 1 + rightWidth <= width) {
    return left + " ".repeat(width - leftWidth - rightWidth) + right;
  }
  if (rightWidth + 1 < width) {
    const fittedLeft = truncateToWidth(left, width - rightWidth - 1, "...");
    return fittedLeft + " " + right;
  }
  return truncateToWidth(right, width, "...");
}

function shortCwd(cwd: string): string {
  const home = process.env.HOME || process.env.USERPROFILE;
  const normalized = home && cwd.startsWith(home) ? `~${cwd.slice(home.length)}` : cwd;
  const parts = normalized.split(/[\\/]+/);
  return parts.length <= 3 ? normalized : parts.slice(-3).join("/");
}

class RedesignFooter implements Component {
  constructor(
    private readonly ctx: ExtensionContext,
    private readonly theme: Theme,
    private readonly footerData: ReadonlyFooterDataProvider,
  ) {}

  invalidate(): void {}

  render(width: number): string[] {
    const model = this.ctx.model?.id ?? "no-model";
    const usage = this.ctx.getContextUsage();
    const usageText =
      usage?.percent === null || usage?.percent === undefined
        ? "ctx ?"
        : `ctx ${Math.round(usage.percent)}%`;
    const branch = this.footerData.getGitBranch();
    const statuses = [...this.footerData.getExtensionStatuses().values()].filter(Boolean).join(" ");

    const left = this.theme.fg("accent", model);
    const rightParts = [usageText, branch ? `git:${branch}` : shortCwd(this.ctx.cwd), statuses].filter(Boolean);
    const right = this.theme.fg("dim", rightParts.join(" | "));
    return [fitLine(left, right, width)];
  }
}

export default function advancedRedesign(pi: ExtensionAPI) {
  let enabled = true;

  pi.registerMessageRenderer("redesign.event", (message, { expanded }, theme) => {
    const suffix = expanded && message.details ? `\n${JSON.stringify(message.details, null, 2)}` : "";
    return new Text(theme.fg("customMessageLabel", "[redesign] ") + message.content + suffix, 0, 0);
  });

  function apply(ctx: ExtensionContext): void {
    if (!ctx.hasUI) return;

    ctx.ui.setStatus("redesign", ctx.ui.theme.fg("dim", "redesign"));
    ctx.ui.setWidget(
      "redesign-help",
      [ctx.ui.theme.fg("dim", "Redesign active | /redesign toggles UI chrome")],
      { placement: "belowEditor" },
    );

    if (ctx.mode !== "tui") return;

    ctx.ui.setWorkingVisible(false);
    ctx.ui.setHiddenThinkingLabel("thinking");
    ctx.ui.setFooter((tui, theme, footerData) => {
      const footer = new RedesignFooter(ctx, theme, footerData);
      const unsub = footerData.onBranchChange(() => tui.requestRender());
      return {
        dispose: unsub,
        invalidate: () => footer.invalidate(),
        render: (width: number) => footer.render(width),
      };
    });
  }

  function clear(ctx: ExtensionContext): void {
    if (!ctx.hasUI) return;
    ctx.ui.setStatus("redesign", undefined);
    ctx.ui.setWidget("redesign-help", undefined);
    if (ctx.mode !== "tui") return;
    ctx.ui.setWorkingVisible(true);
    ctx.ui.setHiddenThinkingLabel();
    ctx.ui.setFooter(undefined);
    ctx.ui.setHeader(undefined);
    ctx.ui.setEditorComponent(undefined);
  }

  pi.on("session_start", (_event, ctx) => {
    if (enabled) apply(ctx);
  });

  pi.on("agent_start", (_event, ctx) => {
    if (enabled && ctx.hasUI) {
      ctx.ui.setStatus("redesign", ctx.ui.theme.fg("accent", "working"));
    }
  });

  pi.on("agent_end", (_event, ctx) => {
    if (enabled && ctx.hasUI) {
      ctx.ui.setStatus("redesign", ctx.ui.theme.fg("dim", "idle"));
    }
  });

  pi.on("session_shutdown", (_event, ctx) => {
    clear(ctx);
  });

  pi.registerCommand("redesign", {
    description: "Toggle advanced UI redesign chrome",
    handler: async (_args, ctx) => {
      enabled = !enabled;
      if (enabled) {
        apply(ctx);
        pi.sendMessage({
          customType: "redesign.event",
          content: "Redesign enabled",
          display: true,
          details: { mode: ctx.mode },
        });
      } else {
        clear(ctx);
        ctx.ui.notify("Redesign disabled", "info");
      }
    },
  });
}
