import { describe, expect, test } from "bun:test"
import { isProtectedRead } from "../src/plugin/guard"

describe("protected read filenames", () => {
  test.each(["/project/.env", "/project/.env.local", "/project/id_rsa", "C:\\project\\id_ed25519", "/project/key.PEM"])(
    "blocks %s",
    (path) => expect(isProtectedRead("read", { filePath: path })).toBe(true),
  )
  test.each(["/project/environment.ts", "/project/.env-directory/source.ts", "/project/id_rsa.pub"])(
    "allows %s",
    (path) => expect(isProtectedRead("read", { filePath: path })).toBe(false),
  )
  test("leaves other tools unchanged", () => {
    expect(isProtectedRead("write", { filePath: "/project/.env" })).toBe(false)
  })
  test.each([undefined, null, 42, {}, { filePath: 42 }])("tolerates malformed arguments: %j", (args) => {
    expect(isProtectedRead("read", args)).toBe(false)
  })
})
