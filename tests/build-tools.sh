#!/usr/bin/env bash
set -euo pipefail
base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$base/work/tools"
wayland-scanner client-header "$base/tests/protocols/virtual-keyboard-unstable-v1.xml" "$base/work/tools/virtual-keyboard-unstable-v1-client-protocol.h"
wayland-scanner private-code "$base/tests/protocols/virtual-keyboard-unstable-v1.xml" "$base/work/tools/virtual-keyboard-unstable-v1-protocol.c"
cc -O2 -I"$base/work/tools" "$base/tests/keyboard.c" "$base/work/tools/virtual-keyboard-unstable-v1-protocol.c" -o "$base/work/tools/keyboard" $(pkg-config --cflags --libs wayland-client xkbcommon)
make -C "$base/source" .build/vpointer

# SDL2 exercises native relative-pointer protocols, as used by games.
if pkg-config --exists sdl2; then
  cc -O2 "$base/tests/relative-client.c" -o "$base/work/tools/relative-client" $(pkg-config --cflags --libs sdl2)
fi
