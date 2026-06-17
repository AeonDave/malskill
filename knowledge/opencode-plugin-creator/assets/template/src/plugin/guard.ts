/**
 * Pure, testable helper for the plugin's hooks.
 *
 * Keeping logic out of the hook closures (which can't be unit-tested directly)
 * and in plain functions here is the core testability pattern. The plugin entry
 * (index.ts) stays thin and just wires these in.
 */

/** File-name fragments that should never be read by a tool. */
const PROTECTED = [".env", "id_rsa", ".pem"]

/**
 * Decide whether a `read`-style tool call targets a protected file.
 * Returns true when the call should be blocked.
 */
export function isProtectedRead(tool: string, args: unknown): boolean {
	if (tool !== "read") return false
	const path = (args as { filePath?: unknown })?.filePath
	if (typeof path !== "string") return false
	const lower = path.toLowerCase()
	return PROTECTED.some((frag) => lower.includes(frag))
}
