# .NET Reverse Engineering Supplement

Load this after `triage.md` when the sample is a managed PE. This reference goes deeper on assembly-specific workflow, deobfuscation order, config extraction, and mixed managed/native pivots. For runtime families outside plain .NET, see `languages.md`.

## Managed-first workflow

```text
managed triage -> obfuscator detection -> entry/config/resource path -> runtime decrypt pivot -> native interop pivot (if present)
```

The main decision is whether the assembly is mostly readable after deobfuscation or merely a thin launcher for another stage.

## High-value triage questions

1. **What obfuscator family?** ConfuserEx, SmartAssembly, .NET Reactor, Babel, or custom.
2. **Is config static, resource-backed, or runtime-only?**
3. **Does it load more assemblies?** `Assembly.Load`, `Assembly.LoadFrom`, reflection, resource streams.
4. **Is there native interop?** `DllImport`, delegates, shellcode loaders, RunPE.

## Practical deobfuscation order

### 1. Stabilize the assembly

- detect obfuscator first
- save a cleaned copy before deep annotation
- if the module decrypts at load time, let the constructor complete and save the in-memory state

```bash
de4dot --detect sample.exe
de4dot sample.exe -o sample_clean.exe
```

### 2. Find the real execution path

Do not assume `Main` contains the real logic. Common alternatives:

- module `.cctor`
- form/application startup handlers
- installer/custom action classes
- resource loader feeding `Assembly.Load()`
- command dispatcher inside a `Client`, `Settings`, or `Plugin` namespace

### 3. Break on the decrypt boundary, not every encrypted string

Best dynamic pivots:

- return of the main decrypt method
- config object construction
- `GetManifestResourceStream` consumer
- `Assembly.Load(byte[])`
- `Process.Start`, `RunPE`, or injection bridge method

This usually gives you the whole plaintext set at once instead of one string at a time.

## Resource and config extraction checklist

- `Properties.Resources`
- `.rsrc` entries with blobs or nested assemblies
- `Settings` / `Config` / `Gate` / `Panel` classes
- JSON/XML blobs decoded from Base64
- hardcoded mutex, install path, campaign ID, wallet list, extension filters

If static strings are sparse, assume the config lives in resources or is assembled at runtime.

## Mixed managed/native pivot

Pivot out of dnSpy when you see:

- `[DllImport]` or `Marshal.GetDelegateForFunctionPointer`
- manual mapping / RunPE helpers
- shellcode blobs copied into RWX memory
- native DLL dropped or reflectively loaded

At that point, continue with `pe-rev.md` for the native stage instead of forcing everything through the managed view.

## Family-oriented heuristics

### Stealers

- `Passwords`, `Wallets`, `Browsers`, `Clipper`, `Grabber`
- browser path tables and wallet extension lists
- webhook, Telegram, panel, or POST config blobs

### RATs

- `Settings` or `Client` with host/port/mutex
- plugin or command dispatch namespaces
- persistence plus surveillance capabilities in one assembly

### Loaders / droppers

- resource extraction followed by `Assembly.Load(byte[])`
- download + execute chains
- delay/sleep + anti-analysis + process injection bridge

## Common pitfalls

- **Over-trusting renamed symbols**: the namespace tree lies; control flow and object lifetimes do not.
- **Saving too late**: let the module decrypt, then save before making edits.
- **Missing resource-only payloads**: not all stage-2 assemblies touch disk.
- **Staying in dnSpy too long**: once native interop dominates, switch to native workflow.
- **Debugging on a live network**: many stealers exfiltrate immediately on first execution.
