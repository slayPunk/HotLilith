#!/usr/bin/env bash
set -euo pipefail
base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$base/work/tools"
wayland-scanner client-header "$base/tests/protocols/virtual-keyboard-unstable-v1.xml" "$base/work/tools/virtual-keyboard-unstable-v1-client-protocol.h"
wayland-scanner private-code "$base/tests/protocols/virtual-keyboard-unstable-v1.xml" "$base/work/tools/virtual-keyboard-unstable-v1-protocol.c"
cc -O2 -I"$base/work/tools" "$base/tests/keyboard.c" "$base/work/tools/virtual-keyboard-unstable-v1-protocol.c" -o "$base/work/tools/keyboard" $(pkg-config --cflags --libs wayland-client xkbcommon)
make -C "$base/source" .build/vpointer

# A real lock protocol client, restricted to an explicit disposable socket.
protocols="$(pkg-config --variable=pkgdatadir wayland-protocols)"
wayland-scanner client-header "$protocols/staging/ext-session-lock/ext-session-lock-v1.xml" "$base/work/tools/ext-session-lock-v1-client-protocol.h"
wayland-scanner private-code "$protocols/staging/ext-session-lock/ext-session-lock-v1.xml" "$base/work/tools/ext-session-lock-v1-protocol.c"
cc -O2 -I"$base/work/tools" "$base/tests/session-lock-client.c" "$base/work/tools/ext-session-lock-v1-protocol.c" -o "$base/work/tools/session-lock-client" $(pkg-config --cflags --libs wayland-client)

# SDL2 exercises native relative-pointer protocols, as used by games.
if pkg-config --exists sdl2; then
  cc -O2 "$base/tests/relative-client.c" -o "$base/work/tools/relative-client" $(pkg-config --cflags --libs sdl2)
fi
