#!/bin/bash
# build_bof.sh — Compile a C++ source file into a BOF (.o) with optimized flags.
# Usage: ./build_bof.sh source.cpp [output.o]

set -euo pipefail

CC="${BOF_CXX:-x86_64-w64-mingw32-g++}"

CXXFLAGS=(
    -Wall
    -Wno-unused-function
    -Wno-unused-variable
    -std=c++17
    -O2
    -fno-exceptions
    -fno-rtti
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
OUT="${2:-${SRC%.cpp}.o}"

if [ ! -f "$SRC" ]; then
    echo "[!] Source file not found: $SRC"
    exit 1
fi

if [ ! -f "${SKILL_ROOT}/assets/beacon.h" ]; then
    echo "[!] beacon.h not found in ${SKILL_ROOT}/assets/"
    echo "    Download from the Cobalt Strike bof_template repo."
    exit 1
fi

echo "[*] Compiling (C++) $SRC -> $OUT"
$CC "${CXXFLAGS[@]}" -o "$OUT" $INCLUDE "$SRC"

# Strip unnecessary sections
if command -v x86_64-w64-mingw32-strip &>/dev/null; then
    x86_64-w64-mingw32-strip --strip-unneeded -R .comment -R .eh_frame "$OUT" 2>/dev/null || true
fi

echo "[+] Done: $(file "$OUT" | cut -d, -f1)"
ls -lh "$OUT"
