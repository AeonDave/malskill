# Binwalk firmware follow-up

After a scan, use `binwalk -L` to inspect available signatures and extractors. External extractors must be installed separately. Choose signatures only after reviewing offsets and descriptions; extraction can expand substantially, so enforce a disk quota independently.

```bash
binwalk -e --directory ./extracted firmware.bin
find ./extracted -type d
find ./extracted -type f -exec file {} +
```

The output tree can contain nested offset-specific directories. Find the actual filesystem root before examining paths such as `bin/sh`; do not assume it is directly under the chosen output directory. For SquashFS, `unsquashfs` can inspect or extract an identified filesystem. Follow the [firmware workflow](../../../../offensive-techniques/reversing-technique/references/firmware-rev.md) for isolated emulation and extraction controls.

`binwalk -E firmware.bin` saves an entropy graph and reports its path in v3.1.0. High entropy can reflect compression or encryption; it does not establish either without corroborating evidence.
