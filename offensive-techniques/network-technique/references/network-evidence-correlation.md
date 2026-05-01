# Network evidence correlation

## Purpose

Build a coherent narrative by correlating scan data, protocol logs, and packet evidence.

## 1) Normalize first

- Use one canonical timezone.
- Record source clock assumptions and known drift.
- Keep raw and normalized timestamps both available.

## 2) Correlation primitives

- Endpoint tuple: source IP, source port, destination IP, destination port, protocol.
- Session key: sensor UID/flow key where available.
- Protocol context: DNS query-answer pair, HTTP request-response pair, TLS handshake context.

## 3) Recommended correlation sequence

1. Start from alert or anomalous host pair.
2. Expand to all sessions in window.
3. Group by protocol stage (resolution, connection, transfer).
4. Validate suspicious stage with packet evidence.
5. Attach confidence label.

## 4) Typical pivots

- DNS query → resolved IPs → outbound TLS/HTTP sessions.
- Suspicious cert/SNI fingerprint → peer set with same handshake traits.
- High-volume transfer session → corresponding host/service exposure and timeline.

## 5) Contradiction handling

- If scan says closed but logs show connection, mark timing mismatch and re-check collection windows.
- If metadata suggests anomaly but packet evidence is missing, downgrade confidence and request additional collection.
- Keep alternative hypotheses visible until disproven.

## 6) Output format

Each key event should include:
- normalized timestamp,
- source pointer (log file or packet/session id),
- short event claim,
- linked prior/next event,
- confidence level.
