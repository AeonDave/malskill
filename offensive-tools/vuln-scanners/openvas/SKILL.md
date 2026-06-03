---
name: openvas
description: "Auth/lab ref: OpenVAS / Greenbone Community Edition: broad network vulnerability scanner checking 90,000+ NVTs across hosts, services, and web apps."
license: GPL-2.0
compatibility: "Linux (recommended)."
metadata:
  author: AeonDave
  version: "1.0"
---

# OpenVAS / Greenbone Community Edition

Network and service vulnerability scanner — 90,000+ NVTs, CVEs, misconfigs, compliance.

## Architecture

```
GSA (Web UI :9392) ─→ gvmd ─→ ospd-openvas ─→ openvas-scanner
                       │                             │
                  PostgreSQL                      Redis (NVT cache)
```

Components: `gvmd` (manager daemon), `ospd-openvas` (OSP wrapper), `openvas` (scanner), `gsa` (web UI), `notus-scanner` (fast CVE checks via JSON advisories).

## Deploy (Docker — Greenbone Community Edition)

```bash
# Download compose file
curl -f -O https://greenbone.github.io/docs/latest/_static/docker-compose-22.4.yml

# Start all services
docker compose -f docker-compose-22.4.yml -p greenbone-community-edition pull
docker compose -f docker-compose-22.4.yml -p greenbone-community-edition up -d

# Wait for feed sync (can take 30-60 min first time)
docker compose -f docker-compose-22.4.yml -p greenbone-community-edition \
    logs -f vulnerability-tests

# Default credentials: admin / admin
# Web UI: https://127.0.0.1:9392
```

## GSA Web UI Scan Workflow

```
1. Configuration → Credentials    # Optional: SSH/SMB creds for authenticated scan
2. Configuration → Targets        # Create target (hosts/subnet, port list)
3. Configuration → Scan Configs   # Choose config (see table)
4. Scans → Tasks → New Task       # Bind target + config + optional credentials
5. ▶ Start Task                   # Execute
6. Scans → Reports → select       # View findings; export XML/CSV/PDF
```

### Scan Configurations

| Config | ID | Use |
|--------|----|-----|
| Full and Fast | `daba56c8-73ec-11df-a475-002264764cea` | Standard pentest scan |
| Full and Deep | `698f691e-7489-11df-9d8c-002264764cea` | Slower, more thorough |
| Empty | `085569ce-73ed-11df-83c3-002264764cea` | Base for custom configs |
| Discovery | `8715c877-47a0-438d-98a3-27c7a6ab2196` | Port/service discovery only |
| Host Discovery | `2d3f051c-55ba-11e3-bf43-406186ea4fc5` | Ping sweep only |
| System Discovery | `bbca7412-a950-11e3-9109-406186ea4fc5` | OS/service fingerprinting |

## gvm-cli (Command Line)

```bash
# Install
pip install gvm-tools

# Auth alias — add to shell profile
alias gvmcli='gvm-cli --gmp-username admin --gmp-password admin \
    socket --socketpath /run/gvmd/gvmd.sock --xml'

# Test connectivity
gvmcli '<get_version/>'

# List targets
gvmcli '<get_targets/>'

# List tasks
gvmcli '<get_tasks/>'

# Get results for task
gvmcli '<get_results task_id="TASK_ID"/>'

# Get report (XML)
gvmcli '<get_reports report_id="REPORT_ID" filter="apply_overrides=0 min_qod=70"/>'
```

### Create Scan via CLI

```bash
# 1. Create target
gvmcli '<create_target>
  <name>My Target</name>
  <hosts>192.168.1.0/24</hosts>
  <port_list id="33d0cd82-57c6-11e1-8ed1-406186ea4fc5"/>
</create_target>'
# → note target id from response

# 2. Create task
gvmcli '<create_task>
  <name>Scan Task</name>
  <target id="TARGET_ID"/>
  <config id="daba56c8-73ec-11df-a475-002264764cea"/>
</create_task>'
# → note task id from response

# 3. Start task
gvmcli '<start_task task_id="TASK_ID"/>'

# 4. Check status
gvmcli '<get_tasks task_id="TASK_ID"/>'
# Look for: <status>Running</status> or <status>Done</status>
```

### Port List IDs

| Port List | ID |
|-----------|-----|
| All IANA Assigned TCP | `33d0cd82-57c6-11e1-8ed1-406186ea4fc5` |
| All TCP and Nmap Top 100 UDP | `730ef368-57e2-11e1-a90f-406186ea4fc5` |
| All TCP | `fd591a34-56fd-11e1-9f27-406186ea4fc5` |

## gvm-pyshell (Python Scripting)

```bash
gvm-pyshell --gmp-username admin --gmp-password admin \
    socket --socketpath /run/gvmd/gvmd.sock

# In shell:
>>> targets = gmp.get_targets()
>>> tasks = gmp.get_tasks()
>>> gmp.start_task(task_id='TASK_ID')
```

## Useful Filters

```bash
# Results with severity >= 7.0, QoD >= 70
gvmcli '<get_results filter="severity>7 min_qod=70 sort-reverse=severity"/>'

# Only active CVEs
gvmcli '<get_nvts filter="type=cve"/>'
```

## Feed Update (Manual)

```bash
# In Docker deployment
docker compose exec ospd-openvas greenbone-nvt-sync
docker compose exec gvmd greenbone-feed-sync --type GVMD_DATA
docker compose exec gvmd greenbone-feed-sync --type SCAP
docker compose exec gvmd greenbone-feed-sync --type CERT
```

## Common Troubleshooting

| Symptom | Fix |
|---------|-----|
| Scan stuck at 0% | Check scanner registered: `gvmcli '<get_scanners/>'` |
| Feed empty / old NVTs | Run `greenbone-nvt-sync` manually |
| GSA unreachable | Check port 9392 and SSH tunnel if remote |
| Scan very slow | Use "Full and Fast" not "Full and Deep"; reduce concurrent hosts |
| Low QoD results | Filter with `min_qod=70` (confirmed findings only) |

## QoD (Quality of Detection)

| QoD | Meaning |
|-----|---------|
| 100% | Package version check (most reliable) |
| 70%+ | Active exploit confirmation |
| 50% | Remote banner check |
| 30% | Unreliable/indirect detection |

Filter `min_qod=70` eliminates most false positives.

## References

- [Greenbone Community Docs](https://greenbone.github.io/docs/)
- [GMP XML Protocol Reference](https://docs.greenbone.net/API/GMP/gmp-22.4.html)
- Scan configs and port list IDs: `references/scan-configs.md`
