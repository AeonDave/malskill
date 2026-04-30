# Sleuth Kit disk + timeline workflow

## Golden path

```bash
mmls image.dd
fsstat -o <offset> image.dd
fls -r -m / -o <offset> image.dd > bodyfile.txt
mactime -b bodyfile.txt > timeline.csv
```

## Recovery/pivot commands

```bash
# recover full file tree where possible
tsk_recover -o <offset> image.dd recovered/

# carve/read a specific inode/file
icat -o <offset> image.dd <inode> > recovered.bin
```

## Analyst tricks

- Always record offsets explicitly in notes; offset mistakes cause silent bad analysis.
- Use timeline first to narrow to incident window, then deep-dive specific paths.
- Correlate inode-based extraction with timeline entries to preserve context.

## Common pitfalls

- Running tools without correct partition offset.
- Interpreting MACB timestamps as guaranteed user actions.
- Ignoring timezone normalization during timeline fusion.
