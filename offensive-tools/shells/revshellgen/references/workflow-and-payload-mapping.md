# RevShellGen Workflow & Payload Mapping

## End-to-End Workflow

```text
Confirm target runtime -> Generate payload -> Start listener -> Execute payload -> Upgrade TTY
```

## Runtime Check Before Payload

On target foothold, quickly test available runtimes:

```bash
which bash sh python python3 perl php ruby socat nc ncat powershell 2>/dev/null
```

Pick payload family based on what actually exists.

## Listener Reliability Checklist

- Listener started before payload execution
- Callback IP reachable from target segment
- Port not blocked by egress policy
- Correct transport expectations (plain TCP vs TLS)

## Payload Failure Triage

| Symptom | Likely cause | Fix |
|---|---|---|
| No callback | wrong IP/port or blocked egress | re-check route and port, try allowed egress port |
| Callback then immediate drop | payload syntax/runtime mismatch | switch payload family to available interpreter |
| Command executes but no interactive terminal | no PTY | run PTY upgrade sequence |
| Works in direct shell but fails in web exploit | quoting/escaping | switch to URL/Base64 output and retest |

## Practical Mapping

- Web RCE with strict quoting -> encoded bash/python payload
- Minimal busybox host -> `sh` or netcat mkfifo style payload
- Hardened Linux with python present -> python payload then PTY upgrade
- Mixed environments -> generate multiple payload candidates before execution

## Security / Scope Reminder

Use only with explicit written authorization in controlled assessments.

## Source Pointers

- RevShellGen upstream README for installation, shell catalog and workflow UX
- Common PTY hardening commands used in post-exploitation operations
