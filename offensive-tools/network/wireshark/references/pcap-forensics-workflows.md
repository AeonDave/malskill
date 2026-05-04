# Wireshark / tshark — PCAP forensics workflows

Use this reference when a capture file is evidence and the goal is to reconstruct activity, extract artifacts, recover credentials or tokens, and preserve a reproducible packet-level evidence chain.

## Fast triage order

1. **Protocol hierarchy** — identify dominant protocols and unexpected traffic classes.
2. **Endpoints** — find top talkers and unusual peers.
3. **Conversations** — isolate client/server pairs with meaningful byte counts or timing.
4. **Display filters** — narrow to likely data-bearing traffic.
5. **Follow Stream** — reconstruct requests, responses, commands, or payloads.
6. **Find Packet** — search for tokens, strings, filenames, hostnames, or magic bytes.
7. **Export artifacts** — objects, selected bytes, or stream output for offline analysis.

This order works for incident response, malware delivery reconstruction, credential exposure analysis, and packet-level root-cause investigations.

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

## Find Packet: fastest way to hunt strings and artifacts

Use `Edit -> Find Packet` when you know or suspect a keyword, header value, filename, token, or byte signature exists somewhere in the capture.

Useful modes:

- **Display filter** — jump to the next packet matching a condition.
- **String** — search packet data for words like `password`, `Authorization`, `session`, `token`, `admin`, or a hostname.
- **Hex value** — search for magic bytes or file headers.
- **Regular expression** — search patterns inside payloads.

Examples of useful searches:

- `http contains "password"`
- `http.authorization || http.cookie`
- `dns contains "corp"`
- `frame contains "Authorization"`
- hex signatures such as PNG, ZIP, PDF, PE, ELF, or archive headers

## Follow Stream effectively

Official behavior that matters in practice:

- Follow Stream automatically applies a display filter for the selected stream.
- Closing with **Close** keeps the stream filter in place.
- Using **Back** restores the previous display filter.
- You can save the stream in multiple formats.

Useful formats:

- **ASCII / UTF-8** — best for HTTP, SMTP, FTP, Telnet, IRC, and text-heavy traffic.
- **HEX Dump** — best for binary protocols or mixed binary/text payloads.
- **Raw** — best when saving reconstructed bytes for offline decoding or carving.
- **YAML** — useful when packet numbers plus base64-encoded stream chunks are needed.

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
- isolate a suspicious connection out of a crowded capture

## Export artifacts from a capture

### Export Objects

Use `File -> Export Objects -> HTTP` when traffic contains clean reassembled files such as HTML, images, archives, scripts, or executables.

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

Use this when evidence is needed in plain text, CSV, or JSON form for reporting or offline analysis.

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
http contains "password"
tcp contains "Authorization"
```

Prefer narrowing by protocol first, then by host, then by stream. Jumping straight into raw packet inspection is how analysts become one with the noise.

## Incident reconstruction playbook

When the evidence is a `.pcap` and the objective is root cause or artifact recovery:

1. Open the capture.
2. Check Protocol Hierarchy, Endpoints, and Conversations.
3. Identify the most promising protocol: commonly HTTP, DNS, FTP, SMTP, SMB, ICMP, or a single odd TCP flow.
4. Search for high-signal strings: `key`, `token`, `user`, `pass`, `admin`, filenames, hostnames, or the target domain.
5. Follow the most suspicious streams.
6. Export HTTP objects if any exist.
7. If recovered content looks encoded or compressed, decode it offline with the appropriate tool.
8. Keep packet numbers and stream indexes so the result is reproducible.

Common patterns:

- **Web delivery**: export HTTP objects, inspect odd responses, follow the stream, decode returned blobs.
- **Credential exposure**: review POST bodies, Basic auth headers, FTP `PASS`, Telnet, or NTLM/Kerberos metadata.
- **Exfiltration or tunneling**: inspect long DNS queries, repetitive requests, unusual hostnames, or high-volume single conversations.
- **Binary or malware delivery**: export HTTP objects or save stream data as raw and inspect the resulting file offline.

## Encoded or transformed payloads

If a followed stream or exported object is not immediately readable:

- check for base64-looking text
- check for compression markers
- inspect magic bytes
- try raw export instead of text export
- save the evidence and decode it offline rather than fighting the GUI

## TLS and encrypted traffic

If the interesting session is under TLS, look for metadata first:

- SNI / server name
- certificates
- IPs and timing
- JA3 or handshake clues if available

If you have a key log file or keys, load them and re-run the same workflow on the decrypted traffic. After decryption, Follow Stream and object export become much more valuable.

## Lab or replay interfaces

When reproducing traffic, capture from the correct interface first.

Typical example:

```bash
wireshark -k -i tun0
```

If you are given a saved `.pcap`, this mainly matters for reproducing traffic later or capturing a second session with the same target.
