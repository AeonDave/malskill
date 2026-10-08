const PROTECTED_NAMES = new Set([".env", "id_rsa", "id_ed25519"])

/** Classify the read tool's filename; other access paths are outside this hook. */
export function isProtectedRead(tool: string, args: unknown): boolean {
  if (tool !== "read" || args === null || typeof args !== "object") return false
  const path = (args as { filePath?: unknown }).filePath
  if (typeof path !== "string") return false
  const filename = path.split(/[\\/]/).pop()?.toLowerCase() ?? ""
  return PROTECTED_NAMES.has(filename) || filename.startsWith(".env.") || filename.endsWith(".pem")
}
