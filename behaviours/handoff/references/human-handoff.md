# Human Handoff

Load only when the user requests a handoff for a person, such as a colleague, reviewer, or manager. Use the parent skill's state inspection, evidence, and delivery checks. Produce the requested human document; a second agent packet is needed only if also requested.

## Choose what the reader needs

Infer the audience and purpose from the request. Identify what the recipient needs to understand, decide, review, or take over; ask only if an unresolved distinction would materially change the document.

| Recipient | Emphasize |
|---|---|
| Colleague taking over | Current work, relevant technical decisions, known pitfalls, dependencies, and the first practical actions with supporting artifacts |
| Reviewer, including a PR reviewer | Problem addressed, resulting behavior or findings, affected components, verification against the relevant state, unresolved tradeoffs, and what needs review |
| Manager or project lead | Objective, current result and its practical impact, remaining uncertainty, blockers or dependencies, decisions needed, and the next milestone supported by available facts |

For mixed audiences, open with a shared overview and put necessary technical detail later. Explain acronyms on first use where the reader needs it. Use direct, connected prose; keep commands, hashes, tool handles, and raw logs out of the main narrative unless they help this recipient act.

## Turn the snapshot into a readable account

Start with the subject, current situation, and what the reader should do next. Then include only the sections the task needs:

- **Results and progress:** what is established, changed, or still being worked on, with concise supporting evidence.
- **Decisions:** important choices, their reasons, and alternatives still open. Separate decisions already made from recommendations awaiting a decision.
- **Open issues:** concrete blockers, uncertainty, failed approaches worth knowing, and their effect on the next step.
- **Next actions:** action, expected outcome, and dependencies. Include owner and date only when supplied or agreed; label an unassigned action when assignment matters.
- **Supporting material:** a few clearly labeled links or references the recipient can use. Include the context needed to understand a finding without opening every attachment.

Preserve the distinctions in the source: observed versus inferred, implemented versus tested, historical verification versus current status, and a running job versus a delivered result. Do not turn unknowns into reassuring conclusions, invent business impact, or assign commitments to make the document appear complete. Keep the observation date or relevant revision when it affects interpretation.

Link evidence with meaningful labels and locations accessible to the recipient. If an internal artifact is unavailable to them, retain the essential supported finding and state what must be shared; a machine-local path alone is not a useful human citation across machines. Reuse canonical records and their conclusions without creating conflicting versions.

## Produce the document

1. Follow the requested format, destination, and supplied template. If the format is open, prefer DOCX when a working generation and validation workflow is available; otherwise use Markdown. A short handoff may be a few paragraphs; do not add a cover, table of contents, or appendix by default.
2. For DOCX, use the available document-generation skill or tool. Create a real Word document with clear headings and readable paragraphs. Reopen it, check extracted content against the verified snapshot, and render and inspect the pages for layout problems. File creation alone is not evidence of a usable document.
3. If DOCX generation or validation is unavailable, deliver a readable `.md` when fallback is allowed and state that limitation briefly. If DOCX is explicitly required, keep Markdown as a draft and report the unresolved conversion instead of claiming the requested format is complete. Never rename Markdown to `.docx`.
4. For Markdown, check headings, lists or small tables, source links, and readability as a standalone document. Keep the substantive content the same as the intended DOCX.

Before delivery, check that the recipient can answer: where the work stands, what supports that assessment, what remains open, and what they need to do or decide. Check that technical detail matches the audience and no invented owner, deadline, result, or promise has appeared. Apply the parent skill's handling of sensitive material and access checks.

Deliver the document location and identify the actual format and any material limitation. Creating the document does not send it to the recipient.
