#!/bin/bash
# build_bof.sh — Compile a C source file into a BOF (.o) with optimized flags.
# Usage: ./build_bof.sh source.c [output.o]

set -euo pipefail

CC="${BOF_CC:-x86_64-w64-mingw32-gcc}"

CFLAGS=(
    -Wall
    -Wno-unused-function
    -Wno-unused-variable
    -Wno-pointer-sign
    -O2
    -fno-asynchronous-unwind-tables
    -fno-ident
    -fpack-struct=8
    -falign-functions=1
    -s
    -ffunction-sections
    -fdata-sections
    -fno-merge-constants
    -m64
    -c
)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
INCLUDE="-I${SKILL_ROOT}/assets"

SRC="$1"
OUT="${2:-${SRC%.c}.o}"

if [ ! -f "$SRC" ]; then
    echo "[!] Source file not found: $SRC"
    exit 1
fi

if [ ! -f "${SKILL_ROOT}/assets/beacon.h" ]; then
    echo "[!] beacon.h not found in ${SKILL_ROOT}/assets/"
    echo "    Download from: https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/beacon.h"
    echo "    Or use the Cobalt Strike bof_template repo."
    exit 1
fi

echo "[*] Compiling $SRC -> $OUT"
$CC "${CFLAGS[@]}" -o "$OUT" $INCLUDE "$SRC"

# Strip unnecessary sections
if command -v x86_64-w64-mingw32-strip &>/dev/null; then
    x86_64-w64-mingw32-strip --strip-unneeded -R .comment -R .eh_frame "$OUT" 2>/dev/null || true
fi

echo "[+] Done: $(file "$OUT" | cut -d, -f1)"
ls -lh "$OUT"
