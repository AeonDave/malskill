# World clue library

Read the file for the region your shortlist points to, in the funnel step that separates countries and
regions ([country-funnel.md](../country-funnel.md)). Each regional file starts with a quick table of the
strongest tells and ends with a "Commonly confused" section.

| File | Scope |
|---|---|
| [general.md](general.md) | Discriminators that work everywhere: driving side, plates, scripts, road paint, signs, poles, vegetation, soil, architecture, sun |
| [europe.md](europe.md) | Europe, including Turkey, the Caucasus, Russia west of the Urals and the microstates |
| [americas.md](americas.md) | North, Central and South America and the Caribbean |
| [asia.md](asia.md) | East, Southeast, South and Central Asia |
| [oceania.md](oceania.md) | Australia, New Zealand and the Pacific islands |
| [africa-middle-east.md](africa-middle-east.md) | Africa, the Arabian Peninsula, the Levant, Iran |
| [china.md](china.md) | Mainland China in depth: platform metadata, text, plates, vehicles, infrastructure, phenology, terrain, urban form |
| [streetview.md](streetview.md) | Google Street View imagery itself: camera generations, car and mount tells, coverage, capture dates. Only for Street View or game screenshots |

## Entry format

```markdown
### <clue name>
- Look for: exactly what to find in the image and how to recognize it
- Points to: country / region / city / type of area
- Strength: strong (a single clue reaches this level) / medium (needs one more) / weak (can only exclude or boost)
- Counterexamples: when it misleads
- Verify: how to confirm it (a tool command, a reference sheet comparison, a lookup)
- Source: general knowledge | regulation/standard | URL checked YYYY-MM | (single source) | (unverified)
```

## Rules

- Every entry states strength and counterexamples.
- "Strong" needs three or more independent sources or a regulation that makes it true by law. Mark
  single-source claims "(single source)"; unchecked claims "(unverified)", and keep them weak. "(verify)"
  on a Strength line means the claim may be stale: check it before leaning on it.
- Only clues that transfer to new photos. One landmark's appearance does not belong here.
- Never write a puzzle's place name or answer into an entry; cite cases by method-level facts only.
- Conventions change and old and new styles coexist for years: a format change dates a photo as well as
  placing it.
- Context sets strength: a plate on a local street beats one in a tourist car park or on a freight corridor;
  vegetation without a month is always weak.
- Library clues only rank candidates (`board.py evidence`). Excluding one needs read text or a computed
  result (`board.py exclude`).
- Write in your own words; do not copy community guides (Plonkit, GeoHints).

After a session with known truth (`photo_session.py truth`), add the clue that decided or misled the case in this format, without the place name or any case reference.
