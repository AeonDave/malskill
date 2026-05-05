---
name: saleae-logic-2
description: "Saleae Logic 2 capture and export workflow for `.sal` traces, raw CSV export, analyzer-table export, and automation API control. Use when you need to inspect or convert Saleae captures, script analyzer exports, or bridge hardware traces into text or CSV for later protocol analysis."
compatibility: "Windows, macOS, Linux; Saleae Logic 2 application; optional Python automation API"
metadata:
  author: AeonDave
  version: "1.0"
---

# Saleae Logic 2

Use this when hardware traces need to become something analyzable instead of just pretty waveforms.

## When to use Saleae Logic 2

Use Saleae Logic 2 when you need to:

- open `.sal` captures and inspect digital or analog traces
- export raw signal data to CSV or binary
- export analyzer tables such as UART, I2C, SPI, CAN, or protocol decodes
- automate record, load, analyze, save, or export workflows from Python

## Manual Export Workflow

### Data table export

In Logic 2, use the three-dot menu next to **Data** and choose **Export Table**.

### Raw data export

Use **Options** in the lower-right corner, then **Export Raw Data**.
Choose channels, time range, format, and destination.

### Analyzer export

Use the three-dot menu next to a specific analyzer and choose **Export to TXT/CSV**.

## Automation API Workflow

```python
from saleae import automation

with automation.Manager.connect() as manager:
    capture = manager.load_capture("trace.sal")
    capture.export_raw_data_csv("export_dir")
    capture.close()
```

Key automation capabilities include:

- `Manager.connect()` or `Manager.launch()`
- `load_capture()` for existing `.sal` files
- `export_raw_data_csv()` and `export_data_table()`
- `save_capture()` for `.sal` output

## Practical Notes

- Official docs note that raw digital CSV only records transitions plus a final trailing sample marker.
- Some analyzers cannot use native per-analyzer export in Logic 2; exporting through the data table is the supported fallback.
- The automation API is ideal when the end goal is CSV, scripting, or batch protocol parsing.

## Caveats

- The automation API expects a running local Logic 2 instance unless you launch it programmatically.
- Exported CSV is not identical to every original waveform detail unless you choose the right channels and ranges.
- Some workflows still require manual analyzer setup before export choices become meaningful.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use Saleae's official export documentation and Logic 2 automation API docs for version-specific details.
