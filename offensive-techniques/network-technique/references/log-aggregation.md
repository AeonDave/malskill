# Log aggregation and correlation

Use this when evidence spans scanner output, Zeek logs, firewall/proxy logs, DNS logs, endpoint events, and packet captures.

## Objective

Build one consistent evidence model across heterogeneous network sources. The goal is not to import everything into a SIEM; it is to preserve enough context to prove or disprove the network hypothesis.

## 1) Normalize first

Before correlation, normalize:

- Timezone and clock offset per source.
- Host identity: IP, hostname, MAC, DHCP lease, user, process where available.
- Direction: inbound, outbound, lateral, pivoted, NAT-translated.
- Source confidence: sensor position, packet loss, log completeness, retention gap.

Never merge logs from unmatched windows and call it one story.

## 2) Minimum useful schema

Use this field set for each event row:

| Field | Why |
|---|---|
| timestamp_utc | Ordering and cross-source merge |
| source_type | zeek, firewall, proxy, dns, endpoint, scanner, pcap |
| src, dst, port, proto | Network pivot core |
| host_identity | User/hostname/process where known |
| observation | Short fact: connection, DNS query, TLS handshake, alert |
| evidence_pointer | File path, log row, packet number, event id |
| confidence | direct, corroborated, inferred |

## 3) Correlation pivots

Start broad, then narrow:

1. IP/port/session UID.
2. DNS name → resolved IP → TLS SNI/cert → HTTP Host.
3. User/process → socket → remote domain.
4. Scanner finding → service banner → packet proof.
5. Alert → raw log row → packet or endpoint confirmation.

For Zeek, preserve `uid` across `conn.log`, `dns.log`, `ssl.log`, `http.log`, and `files.log` before exporting summaries.

## 4) Practical aggregation workflow

1. Build source inventory with time coverage and trust notes.
2. Generate per-source summaries first; do not dump raw logs into final report.
3. Join only on strong pivots: UID, 5-tuple+time, hostname+lease, process/socket.
4. Mark inferred joins when NAT, DHCP, VPN, or proxy changes identity.
5. Keep raw evidence pointers so any finding can be replayed.

## 5) Common failure modes

- Treating NAT public IP as host identity.
- Ignoring DHCP lease changes.
- Joining DNS answer to unrelated later connection after TTL expiry.
- Letting SIEM alert names replace raw evidence.
- Losing packet numbers or log row references during CSV cleanup.
