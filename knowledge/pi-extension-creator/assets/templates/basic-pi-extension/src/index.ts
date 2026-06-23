import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { classifyCommand } from "./policy.js";

const EchoParams = Type.Object({
  message: Type.String({ description: "Message to echo back to the conversation" }),
});

export default function piExtensionTemplate(pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return;

    const command = event.input.command;
    if (typeof command !== "string") return;

    const decision = classifyCommand(command);
    if (decision.kind === "allow") return;

    if (!ctx.hasUI) {
      return { block: true, reason: decision.reason };
    }

    const ok = await ctx.ui.confirm("Command policy", `${decision.reason}\n\nAllow anyway?`);
    if (!ok) return { block: true, reason: "Blocked by user after policy warning." };
  });

  pi.registerTool({
    name: "template_echo",
    label: "Template Echo",
    description: "Echo a message. Use only to verify that the template extension is loaded.",
    promptSnippet: "Use template_echo to verify the template extension is installed.",
    parameters: EchoParams,
    async execute(_toolCallId, params) {
      return {
        content: [{ type: "text", text: params.message }],
        details: { echoed: params.message },
      };
    },
  });

  pi.registerCommand("template-status", {
    description: "Show template extension status",
    handler: async (_args, ctx) => {
      ctx.ui.notify("pi-extension-template loaded", "info");
    },
  });
}
