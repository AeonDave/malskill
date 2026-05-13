# Security Boundaries

Load this file before broadening access, exposing local HTTP, or packaging the server for others.

## Local-first security posture

Assume a local MCP server can be dangerous if misconfigured. It runs code on the user’s machine and may touch files, networks, or secrets.

## Baseline rules

- prefer stdio for local-only integrations
- keep privileges narrow
- expose only the directories, APIs, or actions the workflow truly needs
- sanitize logs and avoid leaking secrets into tool outputs

## Least privilege

- smallest useful directory set
- smallest useful environment variable set
- smallest useful network access
- smallest useful scope set for any auth flow

If the user can accomplish the task with read-only access, do not default to write access.

## Local server compromise mindset

When a host config installs or launches a local server, the exact command matters.

- commands should be visible and reviewable
- dangerous patterns should stand out
- one-click convenience must not hide what will execute

## Stdio vs local HTTP

- **stdio** limits exposure to the launching host process path
- **local HTTP** is a bigger surface and should usually add explicit auth or restricted IPC

If you do not need service-style access, do not switch to HTTP just because it feels modern.

## Auth and session pitfalls

- do not treat session IDs as authentication
- do not blindly pass upstream tokens through the server
- do not request or advertise giant omnibus scopes “just in case”

Prefer progressive scope elevation and explicit challenges over “grant everything up front”.

## Sandboxing direction

For higher-risk servers or broader distribution, consider:

- restricted filesystem views
- restricted network access
- container or application sandbox boundaries
- per-host approval for privileged actions

## Common mistakes

- a local file server with whole-home-directory access by default
- hardcoded secrets in code or examples
- logs that echo credentials, file contents, or bearer tokens
- localhost HTTP servers with no auth that any local process can call
- packaging a server before you have defined its privilege boundaries
