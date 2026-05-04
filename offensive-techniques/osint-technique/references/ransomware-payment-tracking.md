# Ransomware payment tracking

## Purpose

Trace publicly visible cryptocurrency flows from ransom wallets to clusters, services, mixers, bridges, and likely cash-out points while preserving analytical uncertainty.

## Inputs

- Wallet addresses from ransom notes, negotiation portals, screenshots, or victim reports.
- Currency/network: BTC, ETH, TRON, Monero caveat, stablecoins, L2 networks.
- Approximate payment windows and amounts.
- Related infrastructure: onion portal, email, support chat, malware family, incident time.

## Workflow

1. Validate address format and chain.
2. Confirm inbound transactions matching amount/time window.
3. Build first-hop and multi-hop transaction graph.
4. Identify service clusters: exchanges, mixers, bridges, payment processors, known actor wallets.
5. Mark peel chains, consolidation wallets, and split/merge patterns.
6. Cross-reference public labels from multiple explorers and threat-intel sources.
7. Report confidence and avoid claiming identity from wallet movement alone.

## Flow patterns

| Pattern | Interpretation |
|---|---|
| Peel chain | Gradual laundering or operational spend |
| Fan-out split | Obfuscation, affiliate payout, or service deposit preparation |
| Fan-in consolidation | Collection wallet or exchange deposit preparation |
| Mixer deposit | Obfuscation; traceability depends on chain/service |
| Bridge transfer | Cross-chain movement to reduce simple tracking |
| Exchange cluster | Possible cash-out or hosted wallet |

## Evidence quality

High confidence:

- Direct transaction from victim-controlled payment to known deposit address.
- Multiple independent labels for the same service cluster.
- Reused wallet across related incidents and infrastructure.

Medium confidence:

- Timing and amount align but source control is not independently confirmed.
- Wallet clusters share behavior and nearby flows.

Low confidence:

- Shared exchange, mixer, bridge, or commodity infrastructure only.

## Cross-chain considerations

- Track bridge deposit and withdrawal times, amounts, and destination chain.
- Account for fees, slippage, and batching.
- Treat privacy protocols and mixers as confidence reducers unless additional linkage exists.
- Document where tracing stops and why.

## Output

- Transaction graph with timestamps, values, chains, and labels.
- Cluster rationale and source for each label.
- Cash-out or service-touch hypotheses with confidence.
- Known gaps: privacy tooling, missing victim confirmation, exchange-hosted wallets.

## Common pitfalls

- Treating an exchange deposit as attacker identity.
- Ignoring affiliate revenue splits.
- Mixing chain timezones and local incident times.
- Overstating traceability through privacy-preserving systems.
- Failing to separate observed flow from attribution judgment.
