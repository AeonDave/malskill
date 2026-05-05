---
name: exiftool
description: "exiftool: metadata extraction, copy, conversion, and editing utility for images, video, documents, archives, executables, and many other file types. Use when investigating EXIF, GPS, XMP, IPTC, embedded previews, sidecar metadata, or batch metadata manipulation in forensic, OSINT, or content-processing workflows."
compatibility: "Windows, Linux, macOS; Perl-based tool with packaged binaries; extremely broad file-format support"
metadata:
  author: AeonDave
  version: "1.0"
---

# ExifTool

High-coverage metadata inspection and editing across a huge range of file types.

## When to use ExifTool

Use ExifTool when you need to:

- dump metadata from images, videos, PDFs, archives, or binaries
- extract GPS, EXIF, XMP, IPTC, ICC, and embedded-preview information
- compare, copy, or transform metadata between files
- batch process directories recursively
- geotag images from GPS logs or normalize timestamp fields

## Quick Start

```bash
# Read everything ExifTool considers available
exiftool file.jpg

# Short tag names with group names
exiftool -s -G1 file.jpg

# JSON output for automation
exiftool -j file.jpg
```

## High-Value Read Workflows

### Full metadata dump

```bash
exiftool -a -u -g1 file.jpg
```

Use this when you want duplicate and unknown tags grouped clearly.

### Focused tags

```bash
exiftool -s -ImageSize -ExposureTime -CreateDate file.jpg
```

### Structured output for tooling

```bash
exiftool -j file.jpg
exiftool -csv dir/
```

### Recursive directory processing

```bash
exiftool -r -ext jpg pictures/
```

## Embedded Data and Binary Extraction

```bash
# Extract thumbnail
exiftool -b -ThumbnailImage image.jpg > thumbnail.jpg

# Extract embedded metadata from nested content
exiftool -ee file.pdf
```

`-ee` is especially useful for embedded documents, previews, or timed metadata in container formats.

## Copy and Transform Metadata

### Copy tags from one file to another

```bash
exiftool -tagsFromFile src.jpg dst.jpg
exiftool -TagsFromFile src.jpg -all:all dst.jpg
```

### Copy selected metadata while rewriting groups intentionally

```bash
exiftool -all= -tagsFromFile src.jpg -exif:all dst.jpg
```

## Editing and Deletion

```bash
# Write or replace one tag
exiftool -comment='new comment' file.jpg

# Delete all metadata
exiftool -all= file.jpg

# Recursive delete of one group
exiftool -r -XMP-crss:all= DIR
```

## Geotagging

```bash
exiftool -geotag track.log image.jpg
exiftool -geotag track.log -geosync=-20 DIR
```

Use this for forensic or OSINT workflows that align image timestamps with GPS logs.

## Practical Notes

- By default, when ExifTool writes metadata it preserves originals as `*_original` backups.
- Use `-overwrite_original` only when you intentionally do not want those backups.
- `-n` disables print conversion and is useful when you need raw numeric values.
- `-b` is the right choice when extracting binary values like thumbnails or full XMP blobs.
- `-G` and `-g` matter because the same logical tag may exist in multiple metadata groups.

## Caveats

- Editing metadata is not the same as sanitizing a file for privacy; review generated `_original` files too.
- Upstream notes that PDF edits are reversible because original information is not actually removed from the file.
- `-all=` on RAW formats can destroy metadata needed by vendor workflows; use carefully.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official ExifTool documentation for the full tag database, batch formatting tricks, and advanced copy/write syntax.
