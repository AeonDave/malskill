# Lookup data

Local tables read by `clues.py`, `regions.py`, `geodata.py`, `textgeo.py`, `gazetteer.py`, `board.py` and `intake.py`; lookups never go online. Each JSON `_meta` records source, fetch date, licence and count. `refresh.py <table>` (or `clues.py update <table>`) refetches the Wikipedia/GitHub tables and keeps driving-side rows marked `curated`; `geodata.py build-countries` rebuilds `countries.json`.

## Global tables

| File | Content | Source | Fetched | Entries | Licence |
|---|---|---|---|---|---|
| `ai_hosts.json` | AI-image galleries and prompt pages; `intake.py` suffix-matches reverse-search result hosts and prints "AI-gallery host: open and compare" (a host alone only down-weights; stock sites are never tagged by host) | Hand-compiled | 2026-10-13 | 14 | MIT (with this repository) |
| `calling_codes.json` | International calling codes for countries and regions | [en.wikipedia.org/wiki/List_of_telephone_country_codes](https://en.wikipedia.org/wiki/List_of_telephone_country_codes) | 2026-09-14 | 281 | Derived from Wikipedia, CC BY-SA 4.0 |
| `countries.json` | 249 countries/territories: ISO codes, names, capital, continent, TLD, currency, phone prefix, postal format/regex, languages, neighbours, driving side, population-weighted centre and extent | [GeoNames countryInfo.txt](https://download.geonames.org/export/dump/countryInfo.txt) + `driving_side.json` + GeoNames cities500 | 2026-10-08 | 249 | CC BY 4.0 (GeoNames) |
| `country_names.json` | Chinese-English country and region names with aliases (short, traditional, former names) | Hand-compiled | 2026-09-14 | 300 | MIT (with this repository) |
| `driving_side.json` | Driving side by country and territory, switch year, notes; 40 hand-curated rows (China right, Hong Kong/Macau left, UK left) | [en.wikipedia.org/wiki/Left-_and_right-hand_traffic](https://en.wikipedia.org/wiki/Left-_and_right-hand_traffic) | 2026-10-08 | 242 | Derived from Wikipedia, CC BY-SA 4.0 |
| `plate_codes.json` | Regional plate codes outside China with eras: IT, ES, FR (incl. French Algeria), DE, AT, CH, GR, TR, GB, MA (`clues.py lookup plate-code`) | One Wikipedia page per country (`PLATE_PAGES` in `refresh.py`; URL kept per country) | 2026-10-09 | 2103 | Derived from Wikipedia, CC BY-SA 4.0 |
| `streetview_coverage.json` | Countries/territories with official Google Street View road coverage, partial coverage, notable gaps | Wikipedia "Coverage of Google Street View" + launch news | 2026-10 | 181 | MIT (with this repository) |
| `territories.json` | Overseas territories and dependencies, plus integral overseas regions (`curated`) | [en.wikipedia.org/wiki/List_of_dependent_territories](https://en.wikipedia.org/wiki/List_of_dependent_territories) | 2026-09-14 | 60 | Derived from Wikipedia, CC BY-SA 4.0 |
| `text_signals.json` | Scripts -> countries, telltale letters -> languages, CJK character forms, currency marks, vanity TLDs, regional signage words | Hand-compiled from Unicode properties and national orthographies | 2026-10-08 | 548 | MIT (with this repository) |

## Region packs (`regions/<cc>/`)

Each pack holds `region.json` (names, admin levels, lookups, services, tips, `docs` pointing at `references/world/*.md`), optional `data/*.json` tables and `tests.json`; format and lint rules in the `regions.py` docstring. Packs with a manifest only: `ca`, `jp`, `lk`, `mm`, `mx`, `us`.

| File | Content | Source | Fetched | Entries | Licence |
|---|---|---|---|---|---|
| `regions/cn/data/admin.json` | China admin divisions, three levels (province, prefecture, county/district) with codes and parents | [modood/Administrative-divisions-of-China](https://github.com/modood/Administrative-divisions-of-China) `dist/pca-code.json` | 2026-09-14 | 3420 | WTFPL |
| `regions/cn/data/plates.json` | `<province>` and `<province><letter>` plate prefixes -> admin1 / admin2 (city) / district; vehicle classes kept as notes, Chongqing letter split `unverified` | [zh.wikipedia.org/zh-cn/中华人民共和国民用机动车号牌](https://zh.wikipedia.org/zh-cn/中华人民共和国民用机动车号牌), places resolved against `admin.json` | 2026-09-14 | 501 | Derived from Wikipedia, CC BY-SA 4.0 |
| `regions/cn/data/area_codes.json` | Mainland China landline area codes -> admin1 / admin2 / district (010/02X three digits, the rest four) | [zh.wikipedia.org/zh-cn/中国大陆固定电话号码](https://zh.wikipedia.org/zh-cn/中国大陆固定电话号码), places resolved against `admin.json` | 2026-09-14 | 349 | Derived from Wikipedia, CC BY-SA 4.0 |

## Viewer data (`../viewer/`)

| File | Content | Source | Fetched | Entries | Licence |
|---|---|---|---|---|---|
| `../viewer/countries.json` | Country outlines for the live-view globe (name, ISO 3166-1 alpha-2), coordinates rounded to 0.01° | [Natural Earth 1:110m admin_0_countries](https://www.naturalearthdata.com/) | 2026-10-12 | 177 | Public domain |

- Wikipedia-derived tables are released under CC BY-SA 4.0 with attribution to Wikipedia and its editors.
- Chongqing plate letter splits come from general knowledge, not Wikipedia (`unverified: true`); verify before use.
- No OpenStreetMap data is stored here; `osm.py`, `gazetteer.py` and `poi.py` query Overpass live.
- Source names and quoted notes stay in their original language; maintained annotations are in English.
