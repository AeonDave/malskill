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

- **Exposed Docker Socket**: `ls -la /var/run/docker.sock`. If writable, attach the host root filesystem to a new container.
- **Privileged Container**: If `fdisk -l` lists host drives or `capsh` shows `CAP_SYS_ADMIN`, mount the host filesystem (e.g., `mount /dev/sda1 /mnt`) or load a malicious kernel module.
- **Cgroups Release Agent**: If `CAP_SYS_ADMIN` is present on cgroups v1, leverage the `release_agent` feature to spawn host processes.
- **core_pattern / modprobe_path**: Overwrite `/proc/sys/kernel/core_pattern` (pipe format) or `/proc/sys/kernel/modprobe` to make the kernel run an attacker script as root on the host. Works on cgroups v1 and v2. Trigger via SIGSEGV crash or unknown-magic binary execution. Use overlay `upperdir` from `/proc/self/mountinfo` for host-accessible read/write path.
- **Entrypoint UID-drop bypass**: If the image entrypoint checks `$(id -u)` to decide whether to drop privileges via `gosu`/`su-exec`, and `/bin/sh` is bash, inject `BASH_FUNC_id%%=() { echo uid=1000; }` as an environment variable. Bash imports it as a function overriding `/usr/bin/id`, so the check sees non-root and skips the privilege drop. Container stays as real uid 0.

### 3. Kubernetes Specifics
- **Service Account Tokens**: Located at `/var/run/secrets/kubernetes.io/serviceaccount/`.
- **API Server Recon**: Use `curl -skH "Authorization: Bearer $TOKEN" https://$KUBERNETES_SERVICE_HOST/api/v1/namespaces/default/pods/`
- **Kubelet / ETCD Unauthenticated Ports**: Check if ports `10250` (kubelet), `10255` (kubelet readonly), or `2379` (etcd) are exposed internally without authentication. 

## Quality Gates
- **Do not break the pod**: Kernel module injection and heavy cgroup manipulation can crash the container host. Perform checks first.
- **Proof of Action**: Once you escape, immediately collect evidence of reaching the underlying host (e.g., `cat /etc/shadow` from the host mount) rather than deploying destructive backdoors.

## References
- [references/privileged-escapes.md](references/privileged-escapes.md) — Load when dealing with a container running with `--privileged` or `CAP_SYS_ADMIN`.
