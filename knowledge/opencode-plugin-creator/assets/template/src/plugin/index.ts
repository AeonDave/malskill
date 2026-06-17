/**
 * @you/opencode-myplugin — plugin entry point.
 *
 * Demonstrates the canonical OpenCode plugin shape:
 *   - one-time init in the plugin body (logger, state)
 *   - a guard hook that blocks a tool call (tool.execute.before)
 *   - a system-prompt injection (experimental.chat.system.transform)
 *   - a custom tool the model can call (tool)
 *   - resource cleanup (dispose)
 *
 * Replace the TODOs with your behavior. Delete hooks you don't use — return
 * only the ones you implement.
 */

import type { Plugin } from "@opencode-ai/plugin"
import { tool } from "@opencode-ai/plugin"
import { isProtectedRead } from "./guard"

const SERVICE = "myplugin"

/** Log through the OpenCode client, keeping its `this` binding; fall back to console. */
function makeLog(client: unknown) {
	const c = client as {
		app?: { log?: (o: { body: { service: string; level: string; message: string } }) => Promise<unknown> }
	}
	return (level: "debug" | "info" | "warn" | "error", message: string): void => {
		if (c?.app?.log) {
			c.app.log({ body: { service: SERVICE, level, message } }).catch(() => {})
			return
		}
		const line = `[${SERVICE}] ${message}`
		if (level === "warn" || level === "error") console.error(line)
		else console.log(line)
	}
}

const MyPlugin: Plugin = async (input) => {
	const log = makeLog(input.client)
	log("info", `loaded in ${input.directory}`)

	// TODO: one-time setup here (load config, start a server, restore state).
	// Heavy/slow work must be fire-and-forget so it never delays session start:
	//   void doExpensiveInit().catch(() => {})

	return {
		// Block reads of sensitive files. Throwing aborts the tool call; the
		// message is surfaced to the model.
		"tool.execute.before": async (hookInput, hookOutput) => {
			if (isProtectedRead(hookInput.tool, hookOutput.args)) {
				throw new Error(`Refusing to read protected file: ${hookOutput.args.filePath}`)
			}
		},

		// Inject a rule into the system prompt. Push — never reassign output.
		"experimental.chat.system.transform": async (_hookInput, hookOutput) => {
			hookOutput.system.push("TODO: project-specific instruction for the model.")
		},

		// A custom tool the model can call as "myplugin_echo".
		tool: {
			myplugin_echo: tool({
				description: "Echo a message back. Replace with a real action.",
				args: {
					message: tool.schema.string().describe("Text to echo back."),
				},
				async execute(args, ctx) {
					ctx.metadata({ title: `echo: ${args.message.slice(0, 32)}` })
					return `Echo: ${args.message}`
				},
			}),
		},

		// Release anything opened in init (ports, watchers, timers).
		dispose: async () => {
			log("debug", "disposed")
			// TODO: server?.stop(); watcher?.close()
		},
	}
}

export default MyPlugin
