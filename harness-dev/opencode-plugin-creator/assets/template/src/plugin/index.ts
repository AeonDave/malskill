import type { Plugin, PluginModule } from "@opencode-ai/plugin"
import { tool } from "@opencode-ai/plugin"
import { isProtectedRead } from "./guard"

const Guard: Plugin = async (input, options) => {
  const enabled = options?.enabled ?? true
  if (typeof enabled !== "boolean") throw new TypeError("enabled must be a boolean")

  await input.client.app.log({
    body: { service: "example.guard", level: "info", message: "Server plugin initialized" },
  }).catch((error: unknown) => {
    console.error("[example.guard] Startup log failed", error)
  })

  if (!enabled) return {}

  return {
    "tool.execute.before": async (hookInput, output) => {
      if (isProtectedRead(hookInput.tool, output.args)) {
        throw new Error("This read targets a protected filename.")
      }
    },
    tool: {
      example_echo: tool({
        description: "Echo a short message without changing project files.",
        args: {
          message: tool.schema.string().min(1).max(4096).describe("Text to echo."),
        },
        async execute(args, context) {
          context.abort.throwIfAborted()
          return { title: "Echo", output: args.message }
        },
      }),
    },
  }
}

export default { id: "example.guard", server: Guard } satisfies PluginModule
