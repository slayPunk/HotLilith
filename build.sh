#!/usr/bin/env bash
set -euo pipefail
base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$base/work/build"
c++ -std=c++2b "$base/tools/header-abi.cpp" -o "$base/work/build/header-abi" $(pkg-config --cflags hyprland pixman-1 libdrm)
hyprlandHeaderAbi="$("$base/work/build/header-abi")"
hyprctl -j version > "$base/work/build/running-version.json"
python3 - "$hyprlandHeaderAbi" "$base/work/build/running-version.json" <<'PY'
import json,sys
running=json.load(open(sys.argv[2]))
if not running.get('abiHash') or running['abiHash'] != sys.argv[1]:
    raise SystemExit('Running Hyprland does not match the development headers. Restart the session after updating before building.')
PY
export SCROLLOVERVIEW_BUILD_VERSION="hotlilit-0.2+phantomat-a1e8a0806541"
# Objects include Hyprland's private C++ types and its compiled ABI hash.
# An ordinary incremental make does not track these system headers.
make -C "$base/source" OBJDIR=".build/obj/$hyprlandHeaderAbi" -j2
install -m 755 "$base/source/spatialoverview.so" "$base/spatialoverview.so.next"
strip --strip-unneeded "$base/spatialoverview.so.next"
mv -f "$base/spatialoverview.so.next" "$base/spatialoverview.so"
cp "$base/work/build/running-version.json" "$base/build-version.json"
printf 'Built %s\n' "$base/spatialoverview.so"
