---
name: osint-ctf
description: "Lab/CTF: OSINT challenges; people/usernames/email, domains/infra, images/video/geolocation, DNS/archive/social/public records."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# OSINT CTF

Goal: solve OSINT CTF tasks with artifact-first triage, confidence-scored pivots, and reproducible public-source evidence.

## When this skill applies

- people, usernames, emails, domains, infrastructure, images, videos, geolocation, social-media clues, DNS history, archives, public records, or public API artifacts
- research tasks requiring public-source correlation, confidence labels, and reproducible evidence trails

## Operating model

1. Classify the primary lane: media/geolocation, person/username, domain/infrastructure, social platform, archive/history, or public record.
2. State the objective and success oracle before searching.
3. Load the closest `offensive-techniques` methodology before selecting tools.
4. Load only the reference file that matches the lane; do not treat the references as a checklist to exhaust.
5. Choose the smallest tool chain that can produce an independent validation signal.
6. Record the exact proof path, confidence level, and failed pivots before moving on.

## Technique integration

Primary methodology to load:

- `osint-technique`
- `recon-technique`
- `forensic-technique` for metadata, media artifacts, timelines, and evidence preservation.
- `network-technique` for infrastructure, DNS, TLS, banners, and passive traffic artifacts.

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and category pivots for flag-style public-source tasks.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `sherlock`
- `maigret`
- `holehe`
- `ghunt`
- `phoneinfoga`
- `spiderfoot`
- `amass`
- `theharvester`
- `dnsx`
- `httpx`
- `gau`
- `hakrawler`
- `asnmap`
- `massdns`
- `shodan`
- `subfinder`
- `wafw00f`
- `exiftool`
- `tesseract`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Evidence patterns

- Favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, decoded artifact, correlated evidence chain, archived source, or independently confirmed location/account/infrastructure link.

## Category-specific quick pivots

- Define target entity and objective before searching: person, media, infrastructure, event, or organization.
- Use source independence and confidence labels to avoid false pivots.
- Archive exact URL, query, timestamp, and evidence artifact for reproducibility.
- Media/geolocation: extract metadata first, then visual anchors, reverse-image crops, map/street-view checks, OSM queries, and independent confirmation from signs, terrain, weather, or public photos.
- Username/persona: enumerate handles, score reuse, check archived profiles, correlate profile images and bios, and reject matches that share only a common name.
- Domain/infrastructure: pivot through DNS, WHOIS/RDAP, CT logs, subdomains, web archives, source repositories, TLS/SSH fingerprints, and passive banners.
- Social platforms: prefer stable IDs, timestamps, public API fields, profile image history, linked bios, and archived pages over current display names.
- Public records: normalize jurisdiction, date range, and entity spelling before searching; preserve query parameters and record IDs.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Keep challenge/platform/competition names out of notes and generated reports.
- Separate fact, inference, and guess. Mark confidence and the evidence that would disprove the pivot.

## Resources

- [references/geolocation-and-media.md](references/geolocation-and-media.md) — media triage, metadata, reverse image search, maps, coordinates, street-view, OSM, and visual-geolocation pivots.
- [references/social-media.md](references/social-media.md) — username reuse, account IDs, archived profiles, social-platform clues, gaming/fitness traces, and public API pivots.
- [references/web-and-dns.md](references/web-and-dns.md) — dorking, DNS/WHOIS/RDAP, archives, repositories, banners, CT/passive infrastructure, and public-record pivots.
