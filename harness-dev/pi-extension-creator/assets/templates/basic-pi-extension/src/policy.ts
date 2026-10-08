export type Decision =
  | { kind: "allow" }
  | { kind: "deny"; reason: string };

const DANGEROUS_PATTERNS = [
  /\brm\s+-rf\b/,
  /\bsudo\b/,
  /\bchmod\s+777\b/,
];

export function classifyCommand(command: string): Decision {
  for (const pattern of DANGEROUS_PATTERNS) {
    if (pattern.test(command)) {
      return { kind: "deny", reason: `Command matched policy pattern: ${pattern.source}` };
    }
  }

  return { kind: "allow" };
}
