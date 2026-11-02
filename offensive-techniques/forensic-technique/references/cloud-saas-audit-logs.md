# Cloud/SaaS audit-log analysis

## Purpose

Reconstruct activity from provider audit records (AWS CloudTrail, Microsoft 365/Entra unified audit log, Google Workspace, Okta), whether pulled through the provider API/export or inspected through a SIEM UI. Resolve record and field semantics and event-time vs ingestion-time before ordering or interpreting anything.

## 1) Record and field semantics are provider- and schema-scoped

An audit code/enum is only meaningful relative to its full field path, service/record type, and schema version. Do not transfer an enum meaning between fields, services, or providers. Resolve each value against the provider's schema doc.

Key event-time field and action-scoping path per provider:

- **AWS CloudTrail** — event-time: `eventTime` (request **completed**, service-side, UTC). Action scoped by `eventSource` + `eventName`. Also `awsRegion`, `sourceIPAddress`, `userIdentity`, `userAgent`, `readOnly`, `managementEvent`, `eventType`, `requestParameters`/`responseElements`. Records carry a unique `eventID`.
- **Microsoft 365 / Entra unified audit log** (Office 365 Management Activity API) — event-time: `CreationTime`. Common schema (`RecordType`, `Operation`, `Workload`, `UserId`, `ClientIP`, `ResultStatus`, `Id`) is extended by a per-service schema in `AuditData`. The meaning of `Operation` is scoped by `RecordType`/`Workload`.
- **Google Workspace** (Reports API `activities.list`) — event-time: `id.time` (RFC 3339). Action scoped by `id.applicationName` → `events[].type` → `events[].name`, with typed `events[].parameters[]`. Each `applicationName` has its own event/parameter catalog.
- **Okta System Log** (`/api/v1/logs`) — event-time: `published`. Action scoped by `eventType`, with typed sub-objects `actor`, `client`, `outcome` (`outcome.result`, `outcome.reason`), `target[]`.

## 2) Event time vs ingestion/display time

The provider event-time fields above record when the activity happened on the service. A SIEM adds its own receive/index time on top; they are different clocks.

- **Splunk**: `_time` = when the event occurred; `_indextime` = when Splunk indexed it.
- **Elastic/ECS**: `@timestamp` (occurred) < `event.created` (first read by agent/pipeline) < `event.ingested` (arrived in the store).
- **Microsoft Sentinel / Log Analytics**: `TimeGenerated` (created by the data source) vs `_TimeReceived` / `ingestion_time()` (ingestion point). Ingestion time cannot order activity — order by the source event-time column.

Order activity by the provider/source event-time field, not by ingestion/index/display time. If the event-time field is missing or ambiguous, report the ordering uncertainty rather than falling back to ingestion time.

## 3) Delivery latency and absence

- Delivery lags event time: CloudTrail typically delivers within ~5 minutes of the API call (not guaranteed); UAL and Workspace can lag minutes to hours.
- Absence of a record at query time does not prove the activity never occurred. Re-query after the provider's lag window before concluding absence.

## 4) Working through a SIEM or provider UI

- Verify the displayed row is the intended raw record (match event id, provider, record/event type, and the relevant host/user/account) before extracting or interpreting it. A row or query change may still render the previous result; a cleared loading indicator does not prove content identity. Discard mismatched extracts and reacquire.
- Prefer exporting/querying the raw JSON record over reading rendered columns; rendered columns hide the field path and schema needed to interpret codes.
- Deduplicate by record id, not by UI row count. Providers may deliver duplicates (CloudTrail duplicates share the same `eventID`).
- Treat scenario descriptions and threat intelligence as hypotheses to test against the records (seek disconfirming evidence); they do not establish activity absent from the inspected records.

## 5) Correlate back to host and network

- Pivot cloud identity (`userIdentity` / `UserId` / `actor`) and source address (`sourceIPAddress` / `ClientIP` / `client`) to endpoint and network evidence.
- Normalize every source to one timezone (prefer UTC) before merging; see [timeline-correlation.md](timeline-correlation.md) for field-semantics and confidence labeling.

## 6) Preserve the export

- Record the exact query (filters, time window, API/endpoint, tool and version) and hash the exported record set. API/live export is not bit-for-bit repeatable because the service keeps changing — the query parameters plus hash are what make it reproducible.
