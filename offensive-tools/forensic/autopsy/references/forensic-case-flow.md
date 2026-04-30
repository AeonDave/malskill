# Autopsy forensic case flow

## Suggested ingest order

1. File type and metadata extraction.
2. Recent activity / OS artifacts.
3. Hash lookup (known good/known bad sets).
4. Keyword index/search.
5. Optional specialized modules per case scope.

## Practical analyst tricks

- Start with timeline + user profile directories for quickest context.
- Use tags heavily (`interesting`, `to-validate`, `report-ready`) to separate noise.
- Correlate by timestamp and path before claiming causality.
- Export artifact subsets early for peer review.

## Common pitfalls

- Over-collecting screenshots without preserving path/hash provenance.
- Running every ingest module by default on huge datasets.
- Mixing hypothesis and evidence in report notes.

## Report workflow

- Include: source details, processing settings, findings, limitations.
- Separate observed facts from analyst interpretation.
- Add hashes/paths/timestamps for reproducibility.
