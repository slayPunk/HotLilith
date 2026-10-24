# HotLilith

[Русская инструкция](README.ru.md) · [Validation](docs/validation.md) · [Contributing](CONTRIBUTING.md)

An infinite canvas for Hyprland, with a hotkey to switch back to tiling. Inspired by [Lilith](https://github.com/ohto121/lilith) and built on a locally adapted [Phantomat](https://github.com/kaolti/phantomat) renderer.

**0.2 development snapshot.** The plugin targets **Hyprland 0.56.2 with Lua configuration and dwindle**, independently of any desktop preset. Serpantinum is not required. Other compositor versions/layouts need separate validation. A single physical monitor is sufficient.

![Three synthetic Wayland terminal windows on the HotLilith canvas](docs/assets/preview.png)

## Features

- Switch between tiling and a canvas without restarting applications.
- Choose the current workspace or all ordinary workspaces, with separate window positions, sizes, camera and zoom memory for each scope.
- Pan, zoom from 10% to 200%, throw windows and the camera with inertia, and align edges with magnetic guides.
- Draw a region for every new standalone window. Windows wait in a queue; Escape automatically places the current one. Dialogs follow their parent, including a parent still waiting for placement.
- Restore the previous dwindle tree and split proportions when its window membership is unchanged. Otherwise, return to a valid new tiled layout.
- Preserve explicit workspace and scratchpad moves, and the original geometry of floating windows on an unchanged output.
- Interact with real Wayland and XWayland applications, including Wayland drag-and-drop and relative game input inside scaled windows.
- Let fullscreen applications use native Hyprland rendering and return to the previous canvas camera and zoom afterwards.

Pinned windows and special workspaces are excluded. Normal workspace switching closes a workspace-only canvas. Moving a window across the global canvas does not change its workspace; an explicit workspace command does.

## Requirements and compatibility

| Component | Current requirement |
|---|---|
| Compositor | Hyprland **0.56.2**, matching development headers and running ABI |
| Desktop preset | None required; Lua `hyprland.lua` and dwindle |
| Compiler | GCC 15+; the renderer uses `#embed` |
| Build tools | Make, pkg-config, Python 3, binutils (`strip`) |
| Libraries | Hyprland, Lua 5.4, hyprgraphics, pangocairo, pixman-1, libdrm, libinput, libudev, wayland-server, xkbcommon |
| Preview | A running Wayland session, `hyprctl`, `foot` |

Dependencies are declared in [source/Makefile](source/Makefile). No compiled plugin is included: build it against your installed compositor. The build wrapper rejects mismatched headers and uses separate object caches for each ABI.

The settings module adds no key bindings and removes none of yours. Optional shortcuts live in [config/bindings.example.lua](config/bindings.example.lua); copy and edit them to avoid collisions. Mouse move/resize examples are included there as comments. Desktop-specific overrides belong in your own dotfiles.

## Appearance follows your dotfiles

Window borders and gradients, per-window rounding, opacity and shadows use Hyprland's native decorations and window rules. HotLilith does not edit your theme files. Camera transitions inherit `windowsMove` speed, curve and enabled state; globally disabled animations remain disabled. Explicit plugin animation settings override the corresponding inherited values; `animation.inherit = false` selects the plugin defaults. The extra double border is opt-in.

Selection regions, magnetic guides and the minimap use the active/inactive border palette. The minimap follows native rounding and border width. Changes apply after reloading your Hyprland configuration. For a panel palette that differs from Hyprland's border colors, add explicit overrides **after** loading `config/canvas.lua`:

```lua
hl.config({plugin={spatialoverview={canvas={
  accent = "rgb(89b4fa)",       -- region, guides and minimap focus
  panel_color = "rgb(1e1e2e)",  -- minimap background
  -- double_border = true,     -- optional extra native-colored frame
}}}})
```

These are examples, not installed theme values. Arbitrary GTK, QML or panel palettes cannot be inferred reliably from Hyprland; your dotfiles theme generator can write this small override block. Optional upstream navigator and distortion modes have separate appearance settings and are disabled in the public canvas preset.

## Build and preview

From this repository's root, inside the matching Hyprland session:

```bash
bash build.sh
python3 preview.py
```

The preview opens a disposable child Hyprland with three synthetic `foot` windows. Close its window or press **Super+Shift+Escape inside the preview** to exit. Its applications, state files and plugin instance are separate from the main session.

## Install without changing key bindings

```bash
python3 install.py
```

This copies the build and preset into `${XDG_DATA_HOME:-$HOME/.local/share}/hotlilith`. To connect it to `~/.config/hypr/hyprland.lua`:

```bash
python3 install.py --enable
```

The installer backs up the config and appends a marked plugin-load and settings-module block after the existing configuration. It does not include the optional binding example. Hyprland may reload automatically; otherwise use `hyprctl reload`. `--config PATH` and `--target PATH` select alternative locations, but do not adapt the preset's key bindings to another desktop.

To disconnect:

```bash
python3 install.py --remove
```

Removal first checks that the canvas dispatcher succeeded and that no canvas cameras or fullscreen records remain. An unconfirmed shutdown leaves the managed connection intact for recovery. Installed files and backups remain. The inactive plugin can remain loaded until the session ends.

## Opt in to controls

After enabling the settings module, review the installed `config/bindings.example.lua`, choose unused combinations, then explicitly include your edited copy from `hyprland.lua`. For example, if you use the installed example unchanged:

```lua
local data = os.getenv("XDG_DATA_HOME") or (os.getenv("HOME") .. "/.local/share")
dofile(data .. "/hotlilith/config/bindings.example.lua")
```

You can also bind the public dispatchers directly, or test them from a terminal:

```bash
hyprctl dispatch 'hl.plugin.spatialoverview.mode("toggle")'
hyprctl dispatch 'hl.plugin.spatialoverview.mode("scope")'
hyprctl dispatch 'hl.plugin.spatialoverview.mode("off")'
```

The example suggests these combinations; they are **not installed as bindings by default**:

| Action | Binding |
|---|---|
| Tiling ↔ canvas | Super+G |
| Current workspace ↔ global scope | Super+Ctrl+G |
| Emergency return to tiling | Super+Ctrl+Shift+G |
| Pan | Middle drag, or left drag on empty background |
| Zoom around the pointer | Wheel on empty background; Ctrl+wheel or Super+wheel over a window |
| Move / resize a window | Existing Super+left / right drag bindings |
| Focus a neighbouring canvas window | Super+Ctrl+Alt+arrows |
| Move the camera | Super+Alt+arrows |
| Fit all windows | Super+Z |
| Overview ↔ 100% | Super+Alt+G |
| Keyboard zoom | Super+Ctrl+= / Super+Ctrl+- |
| Camera origin at 100% | Super+Ctrl+Home |
| Centre the active window | Super+Ctrl+C |
| Draw a region before launching an application | Super+Ctrl+N |
| Toggle manual pointer capture for an older game | Super+Ctrl+P |
| Release the game pointer | Super+Ctrl+Escape |
| Place the current waiting window automatically; otherwise cancel a region or stop inertia | Escape |

When the canvas is off, the scope shortcut selects the next scope. The generic module and optional example never unbind Super+arrows, Super+J, Super+Shift+F, lock, launcher, clipboard or workspace shortcuts. The example adds suggested chords only after you choose to load it.

## Persistence and games

Layout memory is stored atomically with permissions `0600` in `${XDG_STATE_HOME:-$HOME/.local/state}/hotlilit/canvas-memory-v2.txt`. It contains application classes and window titles. Window matching uses application and title, so changing titles can require manual placement. The most recent changes can be lost before a pending save completes. Disable persistence with `remember_layout = false` in your installed preset.

Relative mouse deltas are forwarded in device units; canvas zoom does not rescale camera sensitivity. Locks and confinement regions use the projected window coordinates. Canvas move/resize gestures suppress relative motion. Some older games need manual capture; use Super+Ctrl+Escape to release it.

Celeste and Prince of Persia: The Sands of Time were exercised in scaled windows. Sands of Time camera and keyboard movement worked at 40% zoom using WineD3D and manual capture. This is not a compatibility guarantee for other games, Proton versions, overlays or anti-cheat systems. See [the validation record](docs/validation.md).

## Updates and limits

After updating Hyprland, restart the session, rebuild and reinstall. The installer refuses to overwrite an already loaded `spatialoverview` plugin. Matching an ABI is necessary; future internal API changes may also require source changes.

The module is separate from your desktop configuration. A dotfiles reinstall can remove its include block; reconnect it after checking the new configuration. Personal Serpantinum adapters are maintained in private dotfiles, outside this public plugin.

Window groups are currently rejected on entry. Physical multi-monitor setups, hotplug, driver changes and long gaming sessions need further validation. Exact old split-tree restoration requires unchanged tiled-window membership.

## Development

CI runs compositor-independent installer/build tests and C++ mechanics/DnD models. Full integration tests require a real matching Hyprland session; they are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

Current coverage includes a plain Lua Hyprland session with no Serpantinum imports and existing user bindings. Broader compositor-version, output and game testing remains planned.

## Credits and license

HotLilith changes are maintained by [slayPunk](https://github.com/slayPunk). The renderer is derived from Phantomat; upstream copyrights and its **BSD-3-Clause** license are retained. Protocol XML files retain their own notices. Lilith is an interaction reference; its source code is not included.

See [LICENSE](LICENSE), [NOTICE.md](NOTICE.md) and [UPSTREAM.md](UPSTREAM.md) for attribution and pinned sources. Existing internal names (`spatialoverview`, `hotlilit`, `syspunk-canvas`) are retained for compatibility.
