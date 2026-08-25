# Protocol Reverse Engineering Supplement

Load this when the artifact is a PCAP, raw capture, WebSocket dump, gRPC/protobuf body, or a client binary whose main unknown is the application protocol rather than the program logic.

## Contents

- [Scope and first split](#scope-and-first-split)
- [Capture-first triage](#capture-first-triage)
- [Active HTTP replay contract](#active-http-replay-contract)
- [Framing patterns that collapse the search space](#framing-patterns-that-collapse-the-search-space)
- [Static and dynamic recovery](#static-and-dynamic-recovery)
- [Minimal output contract](#minimal-output-contract)
- [Common mistakes](#common-mistakes)

## Scope and first split

Decide the lane before deep reversing:

- **Plain text** — delimiters, commands, status codes, JSON/XML.
- **Binary framed** — magic bytes, opcode, length, checksum, flags, sequence.
- **Serialized RPC** — protobuf/gRPC/grpc-web/MessagePack/FlatBuffers.
- **Encrypted/compressed** — TLS, XOR/AES layer, zlib/gzip/lz4 wrapper.

If the main blocker is browser-side request signing, use `document-script-analysis.md` instead. If the protocol sits inside firmware or an IoT image, pair with `firmware-rev.md`.

## Capture-first triage

Start with a flow inventory before disassembling anything:

```bash
tshark -r cap.pcapng -T fields \
  -e frame.number -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e tcp.payload
```

Record:
- direction (`C->S`, `S->C`)
- connection preface / handshake / auth / heartbeat / ready / request / response / close
- repeated fixed bytes, candidate opcodes, candidate length fields
- whether lengths are big-endian or little-endian, header-inclusive or body-only

For binary captures, align several same-type messages and compare the first 16-32 bytes before naming fields.

## Active HTTP replay contract

For each endpoint, preserve `(scheme, connect address:port, TLS SNI/ALPN, HTTP Host, method, path/query, headers, body bytes)`. Replay one known-good request verbatim before changing one field. A response from the right IP with the wrong virtual host is not a valid oracle, and endpoint contracts can differ: do not reuse a form body on a header-driven endpoint or vice versa. Record raw encoding plus response status, headers, body, and decoded structure. Public captures are compatibility fixtures, not live-instance evidence; use `oracle-verification-technique` for freshness and acceptance.

## Framing patterns that collapse the search space

### Text protocols

Look for `\n`, `\r\n`, `|`, `;`, `,`, JSON braces, or obvious command words. Confirm whether one TCP segment can carry multiple messages or a partial message before treating segments as frames.

### Binary framed protocols

Typical fixed header questions:
- magic / opcode / version?
- 1/2/4-byte length? endian? includes header?
- checksum/CRC at tail or header?
- sequence/session/request ID?
- compression or crypto flag bit?

Use a structure template only after those five are stable. `ImHex`, `010 Editor`, and `Kaitai Struct` are good once the field order is real.

### WebSocket

Separate transport framing from application framing. Browser/devtools captures often already deframe WebSocket transport and show only the app payload. Recover message types from opcode/JSON keys/protobuf tags, not from the WebSocket FIN/MASK header unless you are working from raw packets.

### gRPC / grpc-web / protobuf

High-signal markers:
- HTTP/2 + `content-type: application/grpc` or `application/grpc-web+proto`
- service and method in `:path` or request URL
- each protobuf message prefixed by **1 byte compression flag + 4-byte big-endian length**

Decode protobuf bodies with the least assumption first:

```bash
protoc --decode_raw < body.bin
```

When the schema is unknown but the payload is protobuf, `blackboxprotobuf` is the quickest field-map bootstrap:

```python
import blackboxprotobuf
msg, typedef = blackboxprotobuf.decode_message(body_bytes)
```

Treat the result as a candidate schema, then verify against repeated samples and client-side serialization code.

## Static and dynamic recovery

In the client/server binary, find serialization boundaries first:
- `send` / `recv`, `WSASend` / `WSARecv`, `SSL_write` / `SSL_read`
- protobuf encode/decode helpers, varint loops, field-switch dispatchers
- compression calls (`compress`, `uncompress`, `inflate`, `deflate`)
- MAC/checksum routines and key-derivation functions

Dynamic rule: if payloads are encrypted, hook **before encrypt** and **after decrypt**. A hook on plaintext beats guessing frame semantics from ciphertext every time.

## Minimal output contract

Produce all three:
- message dictionary: `type/opcode -> field sketch`
- state machine: `connect -> auth -> ready -> request/response -> close`
- one reproducible decoder or parser command/script

## Common mistakes

- Treating TCP segments as message boundaries.
- Calling a field "length" before checking endian and whether it includes the header.
- Mixing transport framing (WebSocket, TLS record, HTTP/2 DATA) with app framing.
- Freezing on the first protobuf typedef from one sample instead of validating it against multiple messages.
- Reversing the whole binary before enumerating messages and states from the capture.
