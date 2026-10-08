import { $ } from "bun"
import { describe, expect, test } from "bun:test"
import { createOpencodeClient } from "@opencode-ai/sdk"
import { tool } from "@opencode-ai/plugin"
import type { PluginInput, ToolContext } from "@opencode-ai/plugin"
import plugin from "../src/plugin/index"

function fixture() {
  const logs: unknown[] = []
  const input: PluginInput = {
    client: createOpencodeClient({
      baseUrl: "http://localhost:4096",
      fetch: async (request) => {
        logs.push(await request.json())
        return new Response("true", { headers: { "Content-Type": "application/json" } })
      },
    }),
    project: { id: "fixture", worktree: "/project", time: { created: 0 } },
    directory: "/project",
    worktree: "/project",
    serverUrl: new URL("http://localhost:4096"),
    experimental_workspace: { register() {} },
    $,
  }
  return { input, logs }
}

function toolContext(signal = new AbortController().signal): ToolContext {
  return {
    sessionID: "session",
    messageID: "message",
    agent: "build",
    directory: "/project",
    worktree: "/project",
    abort: signal,
    metadata() {},
    async ask() {},
  }
}

describe("server module", () => {
  test("initializes through its explicit server entrypoint", async () => {
    const { input, logs } = fixture()
    const hooks = await plugin.server(input)
    expect(plugin.id).toBe("example.guard")
    expect(logs).toEqual([{ service: "example.guard", level: "info", message: "Server plugin initialized" }])
    expect(hooks.tool?.example_echo).toBeDefined()
  })
  test("rejects invalid options and supports disabling", async () => {
    const { input } = fixture()
    await expect(plugin.server(input, { enabled: "yes" })).rejects.toThrow("enabled must be a boolean")
    expect(await plugin.server(input, { enabled: false })).toEqual({})
  })
  test("executes the guard closure for denied and allowed reads", async () => {
    const { input } = fixture()
    const hooks = await plugin.server(input)
    const before = hooks["tool.execute.before"]!
    const call = { tool: "read", sessionID: "session", callID: "call" }
    await expect(before(call, { args: { filePath: "/project/.env" } })).rejects.toThrow("protected filename")
    const output = { args: { filePath: "/project/source.ts" } }
    await before(call, output)
    expect(output.args.filePath).toBe("/project/source.ts")
  })
  test("executes a bounded custom tool and rejects cancellation", async () => {
    const { input } = fixture()
    const hooks = await plugin.server(input)
    const echo = hooks.tool!.example_echo!
    expect(tool.schema.object(echo.args).safeParse({ message: "" }).success).toBe(false)
    expect(tool.schema.object(echo.args).safeParse({ message: "x".repeat(4097) }).success).toBe(false)
    expect(await echo.execute({ message: "hello" }, toolContext())).toEqual({ title: "Echo", output: "hello" })
    const cancelled = new AbortController()
    cancelled.abort()
    await expect(echo.execute({ message: "hello" }, toolContext(cancelled.signal))).rejects.toThrow()
  })
})
