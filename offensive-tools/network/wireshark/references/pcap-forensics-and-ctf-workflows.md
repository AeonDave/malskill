# Wireshark / tshark — PCAP Forensics and CTF Workflows

Use this reference when a capture file is the evidence and the goal is to reconstruct what happened, extract artifacts, or recover flags, credentials, tokens, and files.

## Fast triage order

1. **Protocol hierarchy** — what protocols dominate?
2. **Endpoints** — which IPs / hosts matter most?
3. **Conversations** — which client/server pairs carry the interesting data?
4. **Display filters** — narrow to likely data-bearing traffic.
5. **Follow Stream** — reconstruct requests, responses, commands, or payloads.
6. **Find Packet** — search for flags, strings, filenames, or magic bytes.
7. **Export artifacts** — objects, bytes, or stream output for offline decoding.

This order works well for incident response, HTB / TryHackMe style labs, and packet-focused CTFs because it turns a noisy capture into a short list of candidate flows quickly.

## Triage from the CLI

```bash
# Protocol hierarchy
tshark -r capture.pcap -q -z io,phs

# Endpoints
tshark -r capture.pcap -q -z endpoints,ip

# Conversations
tshark -r capture.pcap -q -z conv,tcp
tshark -r capture.pcap -q -z conv,udp

# DNS overview
tshark -r capture.pcap -Y "dns.flags.response == 0" \
  -T fields -e frame.number -e ip.src -e dns.qry.name

# HTTP overview
tshark -r capture.pcap -Y "http.request" \
  -T fields -e frame.number -e ip.src -e http.host -e http.request.method -e http.request.uri
```

Use this first pass to decide whether the interesting trail is web, DNS, SMB, email, authentication, or a single IP pair.

## GUI pivots worth using early

- `Statistics -> Protocol Hierarchy`
- `Statistics -> Conversations`
- `Statistics -> Endpoints`
- `Edit -> Find Packet`
- right-click packet -> `Apply as Filter`
- right-click packet -> `Follow`

`Statistics -> Conversations` is especially useful because it gives packet counts, bytes, start time, duration, and a direct **Follow Stream** button for the selected conversation.

## Find Packet: fastest way to hunt secrets

Use `Edit -> Find Packet` when you know or suspect a keyword, header value, filename, or byte signature exists somewhere in the capture.

Useful modes:

- **Display filter** — jump to the next packet matching a condition.
- **String** — search packet data for words like `flag`, `password`, `Authorization`, `session`, `admin`, or a hostname.
- **Hex value** — search for magic bytes or file headers.
- **Regular expression** — search patterns inside payloads.

Examples of useful searches:

- `frame contains "flag"`
- `http contains "password"`
- `dns contains "corp"`
- hex signatures such as PNG, ZIP, PDF, or known markers from a challenge

## Follow Stream effectively

Official behavior that matters in practice:

- Follow Stream automatically applies a display filter for the selected stream.
- Closing with **Close** keeps the stream filter in place.
- Using **Back** restores the previous display filter.
- You can save the stream in multiple formats.

Useful formats:

- **ASCII / UTF-8** — best for HTTP, SMTP, FTP, Telnet, IRC, and text-heavy traffic.
- **HEX Dump** — best for binary protocols or mixed binary/text payloads.
- **Raw** — best when you want to save and decode the reconstructed bytes offline.
- **YAML** — useful when you want packet numbers plus base64-encoded stream chunks.

CLI equivalents:

```bash
# Text view of first TCP stream
tshark -r capture.pcap -q -z follow,tcp,ascii,0

# Raw bytes of first TCP stream
tshark -r capture.pcap -q -z follow,tcp,raw,0

# HTTP view
tshark -r capture.pcap -q -z follow,http,ascii,0
```

Typical use cases:

- reconstruct an HTTP request/response pair
- recover a script or command sequence from plain text protocols
- extract an encoded blob from the response body
- isolate a single suspicious connection out of a crowded capture

## Export artifacts from a capture

### Export Objects

Use `File -> Export Objects -> HTTP` when traffic contains clean reassembled files such as HTML, images, archives, scripts, or executables.

This is often the fastest way to recover challenge artifacts or web-delivered malware samples from a `.pcap`.

CLI:

```bash
tshark -r capture.pcap --export-objects http,./exported_http/
```

### Export Selected Packet Bytes

Use this when the interesting content is a byte range inside a packet rather than a full exported object.

Good for:

- carving a suspicious blob
- saving shellcode or a payload fragment
- extracting a binary header or encoded chunk for offline decoding

### Export Packet Dissections

Use this when you need evidence in plain text, CSV, or JSON form for reporting or offline analysis.

Good for:

- preserving packet metadata
- building a quick IOC list
- feeding parsed packet data into scripts

## Common forensic filters

```text
http
http.request.method == "POST"
http.authorization
http.cookie
dns
ftp.request.command == "PASS"
smtp || pop || imap
ntlmssp
kerberos
smb or smb2
tcp.stream eq 0
ip.addr == 10.10.10.10
frame contains "flag"
http contains "flag"
tcp contains "password"
```

Prefer narrowing by protocol first, then by host, then by stream. Jumping straight into raw packet inspection is how analysts become one with the noise.

## HTB / TryHackMe / CTF-style playbook

When the challenge gives only a `.pcap` and asks for a flag or root cause:

1. Open the capture.
2. Check Protocol Hierarchy, Endpoints, and Conversations.
3. Identify the most promising protocol: commonly HTTP, DNS, FTP, SMTP, SMB, ICMP, or a single odd TCP flow.
4. Search for obvious strings: `flag`, `ctf`, `key`, `token`, `user`, `pass`, `admin`, interesting filenames, or the target domain.
5. Follow the most suspicious streams.
6. Export HTTP objects if any exist.
7. If the recovered content looks encoded, decode it offline with the appropriate tool.
8. Keep packet numbers and stream indexes so the result is reproducible.

Common patterns:

- **Web challenge**: export HTTP objects, inspect odd responses, follow the stream, decode the returned blob.
- **Credential challenge**: look at POST bodies, Basic auth headers, FTP `PASS`, Telnet, or NTLM/Kerberos metadata.
- **Exfil / tunneling challenge**: inspect long DNS queries, repetitive requests, unusual hostnames, or high-volume single conversations.
- **Binary / malware delivery challenge**: export HTTP objects or save stream data as raw and inspect the resulting file offline.

## When the payload is encoded or transformed

If the followed stream or exported object is not immediately readable:

- check for base64-looking text
- check for compression markers
- inspect magic bytes
- try raw export instead of text export
- save the evidence and decode it offline rather than fighting the GUI

This pattern is common in CTFs where Wireshark gets you the blob, but another tool does the final decode.

## TLS and encrypted traffic

If the interesting session is under TLS, look for metadata first:

- SNI / server name
- certificates
- IPs and timing
- JA3 or handshake clues if available

If you have a key log file or keys, load them and re-run the same workflow on the decrypted traffic. After decryption, Follow Stream and object export become much more valuable.

## VPN / lab interfaces

In labs or VPN-based environments, capture from the correct interface first.

Typical example:

```bash
wireshark -k -i tun0
```

If you are given a saved `.pcap`, this mainly matters for reproducing the traffic later or capturing a second session with the same target.