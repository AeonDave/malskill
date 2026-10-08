# Retrieval and Provenance

Load when collecting remote evidence or deciding how to preserve it. Tool names and schemas vary by host; inspect the available tools and current schema before use.

## Choose the least intrusive method that answers the question

1. Use an available search tool to locate candidate sources; record the exact query and any time/domain filters that affect coverage.
2. Fetch the primary source directly when an available tool can return the needed content. Use extraction or browser rendering only when the first method omits material evidence.
3. Stop when additional retrieval will not change the decision, or when the source is inaccessible, outside scope, or would cross the engagement's traffic boundary. Report the gap.

Do not assume that a reader proxy, search cache, browser, or MCP endpoint is installed, unauthenticated, complete, or passive. Verify the active tool contract and whether it contacts the assessment target. Do not copy example parameters from another provider's documentation into the active tool call.

## Evidence record

For each retained source, record:

```text
source_id:
url:
publisher:
source_type: primary | secondary | artifact
published_or_updated:
retrieved_at:
retrieval_method:
content_hash:       # if a local copy is retained
locator:            # section, page, line range, table row, or JSON path
claim_supported_or_refuted:
excerpt:
limitations:
```

Use SHA-256 or another explicitly named digest for a retained file. Hash the bytes actually analyzed; if content is transformed or cleaned, preserve the original hash and identify the transformation. A hash supports integrity checks for the retained copy; it does not establish who published the source or whether the source is true.

Keep a claim-to-source relation rather than an undifferentiated URL list. Mark derivative reports that rely on the same advisory, researcher, or incident report so repetition is not mistaken for independent confirmation. Save only the relevant excerpt and necessary locator; redact secrets and personal data.

## Inaccessible or changing sources

If a source changes, record both retrieval times and compare the relevant claims. If only a search snippet or partial extraction is available, label it as incomplete and do not use it as sole evidence for a consequential claim. If the active tool fails, use another exposed method only if it respects scope and policy; otherwise report the missing evidence.
