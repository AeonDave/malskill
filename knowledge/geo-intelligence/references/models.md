# Local models: what they are good for, how to read them, when to ignore them

All models run locally (Apple MPS, CUDA or CPU); nothing about the photo leaves the machine. Weights download
once (`uv run scripts/doctor.py --models`, ~6.2 GB). Licences: StreetCLIP is non-commercial; the AI-image detector is MIT (its training data carry source-specific, partly
non-commercial terms).

| Tool | Model | Output |
|---|---|---|
| `prior.py` | StreetCLIP (CLIP ViT-L/14-336) + GeoCLIP (CLIP ViT-L/14 + GPS gallery of 100k points) | country ranking, regions of the top countries, GeoCLIP clusters, a consistent point guess, self-assessment |
| `detect.py` | OWLv2 (google/owlv2-base-patch16-ensemble), open vocabulary | numbered crops of signs, plates, poles, bollards, markings, vehicles… |
| `calib.py` | GeoCalib (ETH CVG) | FOV, focal (px and 35 mm eq.), pitch, roll, horizon line, uncertainties |
| `sweep.py`, `match.py` | MegaLoc (DINOv2-B + optimal-transport aggregation) | visual place recognition: ranks street-level views of the same place across days, years and cameras |
| `match.py` | DINOv2-small / CLIP ViT-B/32 + SIFT | generic similarity (satellite thumbnails, object references) |
| `sat_scan.py` | CLIP ViT-B/32 | ranks satellite cells by a text query/preset |
| `ocr.py` | Apple Vision (auto language) / RapidOCR | text lines with boxes and confidence |
| `aidet.py` | Thermostatic/community-forensics-frontier-detector-2026-08 (ViT-S/16 384 fine-tune, fp16 ONNX, CPU) | p_ai of the whole original, flag at 0.65 |
| `textgeo.py` | lingua (offline language ID) + rules + libphonenumber + GeoNames + name-suggestion-index | board-ready text signals |

## World prior (`prior.py`)

Two models that learned what places look like from geotagged photos and street views. StreetCLIP scores the
image against "A Street View photo in <country>" for ~200 countries (and regions of the leading ones); GeoCLIP
scores it against 100,000 GPS points. Both run on several crops and are averaged.

- **Ignore it** on indoor scenes, museum objects, close-ups, historical or monochrome photos, generic
  forest/desert/sea. `assessment.informative = false` → no board signal is written; do not ingest it by hand.
- It confuses look-alikes (Taiwan vs Hong Kong, Czechia vs Germany, Ecuador vs Guatemala): settle those with
  reference sheets and text, not with its ranking.
- Use it as a third opinion after your gut call and the text. Agreement → move faster; disagreement → find the
  reason (often a strong clue it cannot read, such as a plate format). On the board it is status `model`:
  likelihood ratio ≤3, never verified, never excludes. Its point guess is a starting area, not an answer.

## AI-image score (`aidet.py`)

One whole-image classifier, pinned by revision hash (MIT, 44 MB fp16 ONNX, CPU only). Short edge 440 (bilinear), centre
crop 384, ImageNet normalisation; p = sigmoid(logit − 0.7403), flagged at p ≥ 0.65 (the card's calibration). About
0.1–0.2 s per image after a ~2 s start; result in `recon/aidet/aidet.json`; `aidet.py --selftest` downloads the weights
and checks a fixed score.

- Measured on 47 real and 32 generated photos (originals): 3 real flagged (a Pixel metro photo 0.997, an HDR panorama
  0.977, a building 0.667), 32 of 32 generated caught, AUC 0.986. Re-saved as JPEG q75 at 1024 px: 2 real flagged (0.998
  and 1.000), 26 of 32 caught, AUC 0.948, and 3 of 5 photoreal gpt-image-2 fakes fell below 0.13. The test images are
  mostly from the model's training distribution, so real-world recall is lower. The card's held-out recall on recent
  generators: 0.88 clean, 0.66 web-laundered, 0.48 hard.
- A high score is not proof: phone computational, HDR and night photos reach 0.95–0.999, and about 4% of real photos warn
  at the provisional 0.65. A low score never clears: re-encoding hides fakes, and generators newer than the model score
  low. Untested on screenshots, Street View/GeoGuessr frames, old scans, drone footage and very low light.
- It never stops, refuses or closes anything: provenance (`meta.py`), a confirmed AI-gallery page or the operator decide
  (SKILL.md "Generated image?"). "Skipped" (no weights, no network, unreadable file, over 20 s in recon) means unknown.

## Object crops (`detect.py`)

Recall-oriented: it would rather label a tree trunk "bollard" than miss a real bollard. Use the numbered sheet
as a checklist of places to zoom; judge each crop yourself. Scores are not evidence. Tune with
`--classes "a yellow road sign,a kilometre marker"` and `--threshold`. Nothing above threshold (common in
wall-heavy alleys) → scan by eye.

## Camera calibration (`calib.py`)

Reliable on ordinary street scenes; narrow close-ups (an alley wall) can be far off, and then it reports a large
uncertainty (vfov ±10° or more, focal ±hundreds of px) and `recon.md` marks the result UNRELIABLE. Always look
at the red horizon in `calib.jpg` before feeding numbers to `pose.py`, `terrain.py` or `geo.py`. If EXIF has a
trustworthy 35 mm focal length, pass `--prior-focal-35mm` to fix it.

## OCR coverage

The backend that ran is named in `intake/ocr.json` (`backend`); recon.md and textgeo.md adapt their warning to it.
RapidOCR (every system except macOS, or when Vision fails) reads only Chinese characters, Latin letters and digits,
ignores `--langs` and may drop Latin diacritics (Długa → Dtuga). Any other script (Cyrillic, Greek, Hangul, kana,
Arabic, Hebrew, Thai, Indic…) comes out as Latin/Chinese look-alikes or nothing, so textgeo.py scores it apart from
text you type with `textgeo.py --text`: the typed text gives `read` signals of its own, and a RapidOCR script or Han
signal stays `observed` (LR cap 5) with "(RapidOCR, unconfirmed)" unless the typed text gives one of the same kind
over the same countries. On macOS: Apple Vision with automatic language detection (`--langs auto`, the default) keeps diacritics and Cyrillic; a
fixed language list strips them. It reads Latin-script European languages, Turkish, Vietnamese, Indonesian,
Malay, Russian, Ukrainian, Arabic, Thai, Chinese, Japanese and Korean. It does not read Greek, Hebrew,
Georgian, Armenian, Indic scripts, Sinhala, Khmer, Lao, Burmese or Ethiopic: read those yourself and pass them
to `textgeo.py --text`. Lines read only after upscaling or tiling (`pass` up/tile) are hypotheses: zoom in and
confirm.
