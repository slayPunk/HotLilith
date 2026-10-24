# Validation record: 0.2 development snapshot

Initial validation recorded on **2026-10-22**, Hyprland **0.56.2**, commit `efb50993780079460b0cbed1363e2166a2de1d9f`. This records the tested environment, not compatibility with later compositor versions or other desktop presets.

## Publication preparation: 2026-10-23

The generic Lua module was separated from optional shortcuts and the private Serpantinum adapter. The installer now targets the standalone public package. The 118 non-Steam runtime checks below passed again before the appearance update. Installer/build unit coverage grew from 16 to **21**, and **16** new standalone checks exercised actual installation, preservation of user bindings, workspace exit and removal in a plain Lua compositor with no Serpantinum imports. Together with the 45 unchanged C++ model checks, this preparation baseline has **200 non-Steam checks**.

Appearance inheritance adds **12** screenshot/motion checks in `tests/appearance.py`: red square windows with eight-pixel borders, a live reload to green rounded windows with three-pixel borders, theme-derived selection, slow native camera animation, explicit UI accents, globally disabled animations and return to tiling. Screenshots are read from the child compositor rather than compared with a mocked style resolver. The optional upstream navigator/distortion modes are outside this appearance check.

After the appearance changes, the focused runtime rerun covers appearance, standalone installation, the 29 lifecycle/fullscreen checks, 21 mechanics/persistence checks and the private-adapter shortcut smoke test. Steam was **not** rerun on this date; its observations below remain the 22 October record.

## Initial automated and scripted checks

| Group | Passed |
|---|---:|
| Canvas scopes, real shortcuts, tiling restoration, fullscreen | 29 |
| Workspace/scratchpad moves, floating geometry, installer shutdown regressions | 13 |
| Magnets, inertia, spawn regions, persistence and compositor restart | 21 |
| New-window queue, Escape, early and later GTK parent dialogs | 18 |
| Native Wayland SDL2 relative pointer, confinement, capture and fullscreen | 15 |
| XWayland SDL2 equivalent | 15 |
| Real Wayland drag-and-drop between transformed GTK4 windows | 7 |
| DnD routing model | 27 |
| Physics/magnetic geometry invariants | 18 |
| Build-ABI and installer unit tests | 16 |
| Scripted transitions around a real Steam game | 11 |
| **Total checks and invariants** | **190** |

The 179 non-Steam checks have test entry points in the repository. The additional 11 Steam lifecycle checks were run against a local game installation and are not a portable CI test suite. Gameplay/camera observations below also used visual inspection. These counts describe this validation run; they are not a continuous-integration badge or a benchmark.

The complete renderer patch was applied to the pinned Phantomat + PR #19 baseline in a temporary directory. Reconstructed source files matched `source/` byte for byte. Reproduction commands are in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Important scenarios

- Each standalone toplevel waits for its own region. Escape places one queued window automatically. Releasing a held button after Escape cannot place the next window accidentally.
- A transient dialog bypasses its own region, including when it opens before its parent has been placed. It appears centred on the parent after placement.
- Scope-specific window arrangements, camera position and zoom survive a compositor restart. Native dwindle geometry is kept separate from canvas memory.
- Relative deltas `(80, 40)` reach the SDL2 client unchanged at 100% and approximately 26% zoom. Large moves stay inside the projected constraint; buttons do not inject camera motion.
- Both Wayland and XWayland exercise protocol capture, visible confinement, the manual capture hotkey, universal release, reacquisition and exact camera/zoom restoration after fullscreen.
- Real GTK drag-and-drop transfers its payload between scaled windows and returns to normal pointer input afterwards.

The child compositor used a fixed 1280×720 virtual output. Virtual pointer devices stayed connected during capture tests: removing one releases Hyprland's native constraints and does not represent an ordinary physical-mouse motion.

## Steam observations

Game files and Proton prefixes were copied into disposable test locations; original game files and saves were not edited. Those temporary copies were removed after testing. Game screenshots and personal session logs are not included in the public repository.

**Celeste:** a gameplay segment accepted keyboard input inside a reduced XWayland canvas window. This does not test a 3D mouse-look camera.

**Prince of Persia: The Sands of Time:** menu clicks, a new game, character movement and mouse camera turns in both directions were observed at **40% canvas zoom**. It used an installed Proton CachyOS build, a Wine virtual desktop, `PROTON_USE_WINED3D=1` and manual pointer capture (Super+Ctrl+P). Its ordinary DXVK path failed to create a graphics device even with the canvas off; WineD3D was required in that test environment.

A separate run of the same game passed 11 lifecycle checks: capture/release, native fullscreen, exact canvas camera/zoom return, scope changes, tiling exit and canvas re-entry. The same game process/window survived those transitions with no compositor configuration errors.

Prince of Persia 2008 could not select a display mode in this headless test environment and is **not** counted as a successful game test. No general compatibility claim is made for other engines, Proton builds, overlays or anti-cheat systems.

## Remaining coverage

Physical multi-monitor setups, hotplug, driver changes, long gaming sessions and performance under sustained load need separate validation. Window groups are currently rejected. Manual capture can leave a system cursor visible in older games. Future Hyprland private API changes require a new build and can require source changes.
