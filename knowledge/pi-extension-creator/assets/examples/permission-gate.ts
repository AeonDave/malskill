import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const DANGEROUS = [/\brm\s+-rf\b/, /\bsudo\b/, /\bchmod\s+777\b/];

export default function permissionGate(pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return;
    const command = event.input.command;
    if (typeof command !== "string") return;
    if (!DANGEROUS.some((pattern) => pattern.test(command))) return;

    if (!ctx.hasUI) return { block: true, reason: "Dangerous command blocked in non-interactive mode." };

    const ok = await ctx.ui.confirm("Dangerous command", command);
    if (!ok) return { block: true, reason: "Blocked by user." };
  });
}
