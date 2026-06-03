---
name: tesseract
description: "Auth/lab ref: Tesseract OCR engine for extracting text from images and scanned documents."
compatibility: "Linux, Windows, macOS; language packs installed as needed."
metadata:
  author: AeonDave
  version: "1.0"
---

# Tesseract

OCR for when the flag is technically visible but insists on pretending it is art.

## When to use Tesseract

Use Tesseract when you need to:

- extract text from screenshots, photos, scans, or UI captures
- OCR serial numbers, labels, or handwritten-ish block text after preprocessing
- turn image-only evidence into searchable text

## Quick Start

```bash
# OCR to stdout
tesseract image.png stdout

# OCR to a text file prefix
tesseract image.png output

# Specify language and page segmentation mode
tesseract image.png stdout -l eng --psm 6
```

## Practical Notes

- Clean input matters: crop, deskew, increase contrast, and remove noise before blaming OCR.
- `--psm` changes behavior a lot; single-line, sparse-text, and full-page inputs want different modes.
- Pair with `exiftool` for metadata and with image preprocessing outside the OCR step when results are poor.

## Caveats

- Garbage in, garbage out; screenshots of tiny text and stylized fonts need preprocessing.
- Wrong language packs or segmentation modes can destroy otherwise easy reads.
- OCR output still needs human verification before you treat it as evidence.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official Tesseract docs for language packs, OCR engine modes, and advanced config files.
