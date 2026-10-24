# Source provenance

HotLilith changes are maintained by [slayPunk](https://github.com/slayPunk), copyright 2026, under the root BSD-3-Clause license. The renderer's original license remains in `source/LICENSE`; protocol files retain their per-file notices. See [NOTICE.md](NOTICE.md).

- Renderer: [kaolti/phantomat](https://github.com/kaolti/phantomat), pinned commit `a1e8a0806541640d01503ac861a8a39548de8724` (2026-10-08).
- Upstream renderer is BSD-3-Clause, copyright Hypr Development and Zsolt Kacso. Original license is retained both here and in `source/LICENSE`.
- Wayland drag-and-drop: [upstream PR #19](https://github.com/kaolti/phantomat/pull/19), Zsolt Mencseli's commits `14c12937b1ddf986737a25af163689f07046a569` and `d1a06ab6d11d280c0b47f09d48f9ac4a42ca8094`. This is a proposed upstream change, applied locally. Original patch and attribution are kept in `patches/upstream-pr19-dnd.patch`.
- Virtual keyboard protocol XML: [atx/wtype](https://github.com/atx/wtype), copyright notice retained inside the XML. No wtype binary is installed or shipped by this project.
- Virtual pointer protocol XML: retained from the pinned renderer's test tools, copyright Josef Gajdusek, with its original permissive notice in `source/tests/tools/wlr-virtual-pointer-unstable-v1.xml`.

Local work adds a distinct mode lifecycle, workspace/global scope selection, separate spatial/camera memory, conditional dwindle-tree restoration, guarded group handling, a generic binding-free Lua module, an opt-in binding example, installation/rollback tools, preview and integration tests.

The original upstream scripts and examples are kept for reference. Use the root-level build/install/preview commands for Hotlilit; upstream's installer deploys its own default bindings instead.

The canvas interaction reference is [ohto121/lilith](https://github.com/ohto121/lilith) at `4acbf2871316dce751a5448ea799953bf0bd3ad8`, alongside private reference recordings that are not distributed. HotLilith's motion sampling, exponential coasting, magnetic geometry, spawn-region selection and scoped v2 persistence are independently implemented here; no Lilith source code is imported. Hyprland and the user-selected desktop shell continue to provide native compositor and shell services.

HotLilith 0.2 adds `CanvasPhysics.hpp`, the compositor integration in `CanvasFeatures.inc`, queued window placement and parent-dialog handling in `CanvasPlacement.inc`, projected pointer capture and gesture filtering in `CanvasInput.inc`, private atomic memory files, navigation actions and real-input/restart checks. The full local renderer diff, including added files, is retained in `patches/hotlilit-renderer.patch` against the pinned upstream plus PR #19.
