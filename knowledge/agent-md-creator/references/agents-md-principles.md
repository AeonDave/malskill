# Instruction Scope, Migration, and Decisions

Load when splitting instruction files, migrating a host-specific format, or preserving decisions and exceptions during a rewrite.

## Scope and loading

`AGENTS.md` is ordinary Markdown with no required section schema. The [open-format guidance](https://agents.md/) describes root and nested files, with the nearest file taking precedence for conflicting repository instructions. Confirm the target host's actual discovery, inheritance, filename, and import behavior before relying on that convention; support is not identical across clients.

- Put shared instructions at the root and only subtree differences in nested files.
- Add a nested file when a package has distinct commands or constraints and the host will discover it. File length alone is not a reason to split.
- Check the combined instructions for a representative edited path. A nested exception should name its scope; it must not accidentally weaken a repository-wide boundary.
- Resolve conflicts according to the host's instruction hierarchy. Repository text cannot grant permissions or override higher-priority instructions.
- Avoid a second canonical copy in a host-specific file. Use a supported import or pointer only after verifying that the target host follows it.

## Migration

1. Identify the instruction files used by the supported hosts and the unique rules each contributes.
2. Consolidate duplicate facts in the appropriate `AGENTS.md`; keep genuinely host-specific configuration in its native file.
3. Check that moved instructions remain discoverable from the relevant working directories. A Markdown link is not necessarily an automatic import.
4. Remove an obsolete file only when replacement loading is confirmed and the requested migration covers it. Otherwise preserve it and identify the unresolved dependency.

Do not bulk-rename files, introduce symlinks, or promise cross-host equivalence based only on filename similarity. Verify the needed mechanism against the host's current primary documentation or runtime behavior.

## Persistent decisions

Preserve explicit user or team decisions that still govern repository work. Record only the choice, its scope, and any condition that changes it. Do not turn a one-off task request or an assistant's preferred tool into team policy.

For ambiguous or conflicting decisions, use the current conversation and repository evidence first. Ask when the conflict materially affects the result and remains unresolved; do not insert a new permanent approval rule as a substitute for resolving it.

## Accepted diagnostics

An accepted diagnostic needs an identifiable warning or error, affected path or command, approved disposition, and revisit condition where known. One scoped entry is enough; it may sit beside the command that emits it.

Do not broaden a single accepted warning into permission to ignore new failures. Keep the exception when shortening the file; revise it when the issue is fixed, the relevant code changes, or the user reopens it.
