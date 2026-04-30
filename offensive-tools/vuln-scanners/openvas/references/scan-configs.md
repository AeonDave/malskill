# OpenVAS Scan Configs and Port Lists

## Scan Configuration IDs

| Config Name | UUID |
|-------------|------|
| Full and Fast | `daba56c8-73ec-11df-a475-002264764cea` |
| Full and Fast Ultimate | `698f691e-7489-11df-9d8c-002264764cea` |
| Full and Deep | `8715c877-47a0-438d-98a3-27c7a6ab2196` |
| Full and Deep Ultimate | `74db13d6-7489-11df-91b9-002264764cea` |
| Empty | `085569ce-73ed-11df-83c3-002264764cea` |
| Discovery | `8715c877-47a0-438d-98a3-27c7a6ab2196` |
| Host Discovery | `2d3f051c-55ba-11e3-bf43-406186ea4fc5` |
| System Discovery | `bbca7412-a950-11e3-9109-406186ea4fc5` |

Retrieve dynamically: `gvmcli '<get_scan_configs/>'`

## Port List IDs

| Port List | UUID |
|-----------|------|
| All IANA Assigned TCP | `33d0cd82-57c6-11e1-8ed1-406186ea4fc5` |
| All TCP and Nmap Top 100 UDP | `730ef368-57e2-11e1-a90f-406186ea4fc5` |
| All TCP | `fd591a34-56fd-11e1-9f27-406186ea4fc5` |
| Nmap Top 2000 TCP and Top 100 UDP | `9ddce9de-0f6b-4577-a30d-3f0b43e4c99e` |

Retrieve dynamically: `gvmcli '<get_port_lists/>'`

## Full Automation Script (Python)

```python
#!/usr/bin/env python3
"""Minimal OpenVAS scan automation via python-gvm."""
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform

SOCKET = "/run/gvmd/gvmd.sock"
USER = "admin"
PASS = "admin"
TARGET_HOST = "192.168.1.1"
CONFIG_ID = "daba56c8-73ec-11df-a475-002264764cea"  # Full and Fast
PORT_LIST_ID = "33d0cd82-57c6-11e1-8ed1-406186ea4fc5"

connection = UnixSocketConnection(path=SOCKET)
with Gmp(connection=connection, transform=EtreeTransform()) as gmp:
    gmp.authenticate(USER, PASS)

    # Create target
    res = gmp.create_target(name="AutoScan", hosts=[TARGET_HOST], port_list_id=PORT_LIST_ID)
    target_id = res.get("id")

    # Create task
    res = gmp.create_task(name="AutoScanTask", config_id=CONFIG_ID, target_id=target_id)
    task_id = res.get("id")

    # Start task
    gmp.start_task(task_id)
    print(f"Task started: {task_id}")
```

## gvm-cli XML Reference

```bash
# Get all results (no filter)
gvmcli '<get_results/>'

# Get results filtered by severity and QoD
gvmcli '<get_results filter="severity>5 min_qod=70 sort-reverse=severity"/>'

# Get tasks with details
gvmcli '<get_tasks details="1"/>'

# Get report formats
gvmcli '<get_report_formats/>'

# Export report as XML
gvmcli '<get_reports report_id="REPORT_ID" filter="min_qod=70" format_id="a994b278-1f62-11e1-96ac-406186ea4fc5"/>'
# XML format_id: a994b278-1f62-11e1-96ac-406186ea4fc5
# PDF format_id: c402cc3e-b531-11e1-9163-406186ea4fc5
# CSV format_id: c1645568-627a-11e3-a660-406186ea4fc5
```
