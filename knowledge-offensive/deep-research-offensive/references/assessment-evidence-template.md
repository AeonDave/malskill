# Assessment Evidence Template

Load when mapping a supported assessment finding to behavior, validation, or defensive coverage. Use current ATT&CK content and record the version or retrieval date. This template documents evidence and safe validation; it is not an intrusion procedure.

```markdown
## Finding: [concise claim]

- Assessment scope: [asset, environment, and relevant constraints]
- Status: confirmed | supported | inconclusive | not assessed
- Status basis: [the precise claim covered by that status; distinguish local observations from external demonstrations]
- Confidence: high | moderate | low — [evidence-based reason]
- Affected conditions: [product/build/configuration/access prerequisites]
- Evidence: [source IDs and exact locators]
- Contradictions or gaps: [what conflicts or remains unknown]
- Chained prerequisites: [supported transitions, missing links and affected identity/trust boundary, if relevant]
- Impact: [supported consequence and affected boundary]
- ATT&CK mapping: [current ID and name, or unmapped]
- Validation: [non-invasive check or explicitly scoped test; expected safe result]
- Detection: [telemetry source, collection status, analytic, observed alert-test result or untested state, and coverage gap]
- Remediation: [vendor-backed fix or compensating control]
```

Use an ATT&CK mapping only when observed or source-supported behavior fits the current technique definition. A mapping is an organizing label; it does not prove that the behavior occurred, that a control detects it, or that the finding applies to an asset. Keep observed activity distinct from a proposed validation step.

Omit fields that do not serve the decision. Do not let a confirmed initial observation imply confirmation of the entire chain. For a validation plan, name the discriminating observation and relevant control; record the actual outcome separately if the test is performed.
