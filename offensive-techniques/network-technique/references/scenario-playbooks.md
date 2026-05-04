# Scenario playbooks

## Purpose

Provide reusable flow templates for high-frequency network investigation cases.

## Playbook A: New external exposure spike

1. Run broad exposure census and compare with last known baseline.
2. Validate unexpected services with targeted version/scripts.
3. Check if exposure aligns with approved change window.
4. If not approved, prioritize internet-facing high-risk services for containment.

Success condition: confirmed delta list with owner attribution and containment path.

## Playbook B: Suspected beaconing/C2 over encrypted channels

1. Triage metadata for periodic low-volume recurring sessions.
2. Pivot by DNS + TLS identifiers and recurring endpoint pairs.
3. Isolate top suspicious peers and verify timing regularity.
4. Escalate to endpoint correlation for process/user attribution.

Success condition: defensible list of likely C2 sessions with confidence tags.

## Playbook C: Possible data exfiltration window

1. Identify asymmetric transfer sessions and unusual destinations.
2. Correlate with DNS resolution and service profile.
3. Validate transfer significance using packet/session evidence.
4. Build timeline with pre-transfer and post-transfer context.

Success condition: bounded exfiltration hypothesis with volume/time/target estimates.

## Playbook D: Segmented target requires pivoting

1. Establish tunnel path and verify routing assumptions.
2. Run minimal scoped discovery through pivot.
3. Validate critical services only; avoid wide scans initially.
4. Expand scope only after objective-aligned findings.

Success condition: reachable surface map with low-noise pivot evidence.

## Playbook E: Relay/poisoning suspicion in internal network

1. Identify suspicious name resolution/auth patterns.
2. Correlate SMB/LDAP/NTLM-related events in same time window.
3. Validate suspected relay path with packet/protocol evidence.
4. Report affected hosts/accounts and immediate hardening actions.

Success condition: evidence-backed relay path and impacted scope.

## Playbook F: DNS anomaly or suspected covert channel

1. Baseline query volume, domains, record types, response sizes, and timing for the relevant hosts.
2. Identify high-entropy labels, unusual subdomain depth, excessive NXDOMAINs, TXT/NULL abuse, and periodic low-volume trickle patterns.
3. Pivot from domain → host pair → process/user context where endpoint logs exist.
4. Check for DoH/DoT fallback, newly observed resolvers, and HTTP traffic to known DNS providers.
5. Validate with packet or Zeek DNS evidence before declaring exfiltration.

Success condition: bounded covert-channel hypothesis with source host, destination domain/resolver, time window, volume estimate, and confidence label.
