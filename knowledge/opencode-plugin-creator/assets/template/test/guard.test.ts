import { describe, expect, test } from "bun:test"
import { isProtectedRead } from "../src/plugin/guard"

describe("isProtectedRead", () => {
	test("blocks reading a .env file", () => {
		expect(isProtectedRead("read", { filePath: "/proj/.env" })).toBe(true)
	})

	test("blocks reading an ssh key", () => {
		expect(isProtectedRead("read", { filePath: "/home/u/.ssh/id_rsa" })).toBe(true)
	})

	test("allows a normal source file", () => {
		expect(isProtectedRead("read", { filePath: "/proj/src/index.ts" })).toBe(false)
	})

	test("ignores non-read tools", () => {
		expect(isProtectedRead("write", { filePath: "/proj/.env" })).toBe(false)
	})

	test("tolerates missing/odd args", () => {
		expect(isProtectedRead("read", undefined)).toBe(false)
		expect(isProtectedRead("read", { filePath: 42 })).toBe(false)
	})
})
