# Validation record: 0.2 development snapshot

Initial validation recorded on **2026-10-22**, Hyprland **0.56.2**, commit `efb50993780079460b0cbed1363e2166a2de1d9f`. This records the tested environment, not compatibility with later compositor versions or other desktop presets.

## Hyprland 0.57.0 port: 2026-11-13

The current source targets **Hyprland 0.57.0**, commit `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426`, Lua and dwindle. The 0.56.2 results below remain historical evidence. The old binary is incompatible with 0.57.0; rebuild against matching headers.

The port updates workspace addresses, window metadata/backends/presentation, explicit render contexts and hook signatures, keybind dispatch, popup positioning and IPC commands. Unset appearance and animation options still inherit the user's theme; the new `setByUser` pointer is checked by value. A named workspace retains independent canvas memory and exits correctly when the user changes workspace.

Validation used one physical monitor and a disposable 1280×720 headless output, bootstrapped through a separate Wayland compositor. No Steam game, desktop locker or experimental plugin was loaded into the main compositor. System hyprutils was updated from CachyOS 0.14.2-1.1 to **0.14.3-1.1**, satisfying the existing `hyprland.pc` dependency. Initial checks used an isolated 0.14.3 build; the final build uses the system library without `PKG_CONFIG_PATH` or `LD_LIBRARY_PATH` overrides. The 29 integration checks and both 15-check relative-input runs passed again with the packaged system library. The existing main compositor still maps the removed old library file; log out and back in before loading the new plugin there. This validation did not restart that session.

| Runtime suite | Passing checks |
| --- | ---: |
| Tiling/canvas integration | 29 |
| Standalone installation and binding preservation | 16 |
| Workspace/scratchpad and restoration regressions | 13 |
| Theme inheritance and camera motion | 12 |
| Named workspace addresses and scope | 8 |
| Region placement and transient dialogs | 18 |
| Canvas mechanics and persistence across restart | 21 |
| Session lock and fullscreen restoration | 27 |
| Relative input, native Wayland / XWayland | 15 / 15 |
| Client maximum-size hints, Wayland / XWayland | 10 / 10 |
| Real Wayland drag-and-drop | 7 |

All 22 Python build/installer tests passed, including preservation of the previous build when development dependencies are missing. The C++ geometry/inertia and drag routing checks also passed. Shell/Python syntax, repository publication checks and renderer-patch reproducibility were checked.

**Limitations:** these tests do not establish that the previously reported Lords of the Fallen borderless renderer/control freeze is fixed. Steam gameplay was not repeated for this port. Physical multi-monitor behavior and third-party decoration plugins such as hyprbars were not validated. The source uses private compositor APIs and requires a matching rebuild after future Hyprland updates.

## Hook lifecycle follow-up: 2026-11-13

The 14 canvas hooks now share one ordered list for activation and reverse-order shutdown. The independent, always-on X11 client-message hook is excluded. Activation stops on the first failure, rolls back, and reports the existing error; a missing hook pointer takes this path instead of being dereferenced.

All **23 Python tests** passed. The new lifecycle test compiles the production list and lifecycle functions against hook doubles and injects a failed activation or a missing pointer at each of the 14 positions. It checks reverse rollback, repeated activation and repeated shutdown. This tests lifecycle control flow, not machine-code patching failures inside Hyprland.

After rebuilding against system hyprutils, **29 integration checks** and **15 XWayland relative-input checks** passed again in isolated Hyprland. Two additional runtime assertions verified unloading while the canvas is active restores exact native tiling, and freshly loading the plugin can activate and deactivate it again without stale state. The main session and Steam games were not modified or exercised.

## Additional game investigation: 2026-10-24

**Borderless mode is not yet accepted:** after the scripted checks below, the user reported loss of gameplay control. With the plugin unloaded, the game rendered only a small image in a larger black window; focus reset and window-mode toggling did not recover it. The passing checks establish compositor geometry and capture bookkeeping, not a healthy post-test game renderer or restored gameplay input. Further live recovery and end-to-end validation are required.

A controlled follow-up kept ordinary Windowed gameplay healthy through native resize/retile and a single canvas cycle, with user confirmation. After changing that same process to borderless, frames stopped on a native fullscreen-to-window transition while the plugin was unloaded, before any new canvas entry. Because that process had used the canvas earlier, residual effects are not yet excluded; a fresh-process comparison is required.

**Native tiling restoration fix:** Lords of the Fallen (Steam AppID 1501750, XWayland) updates its protocol maximum size to the canvas window size. A failing live trace recorded a maximum of 806×504, a correctly saved tiled state, and a successful native float-disable action that nevertheless left the window floating. Hyprland's dwindle insertion rejects a target whose maximum is too small for its prospective tile.

When returning an originally tiled window, HotLilith now ignores protocol maximum-size hints only for the native reinsertion call. The previous `no_max_size` override is restored immediately, and explicit user `max_size` properties/rules retain precedence. Originally floating windows keep their existing restoration path. This does not add a permanent game rule or change the user's dotfiles.

`tests/size_hints.py` reproduces the failure with an SDL2 client that publishes a finite maximum after entering the canvas. Before the fix, exact tiling restoration and repeated entry/exit failed. After the fix, **10 checks each on XWayland and Wayland** pass, including actual application render-buffer size, keyboard delivery after exit, unchanged client maxima and preservation of an explicit user maximum. These SDL2 checks do not reproduce the game-specific stalled-frame symptom.

The live borderless game restored exact native tiled geometry both directly and after a native fullscreen roundtrip. A further run passed all **11 scripted checks**: reduced canvas, focus, pointer capture/release/reacquisition, fullscreen suspension, exact canvas camera/zoom return, tiled geometry restoration, process/window continuity and no configuration errors. These assertions establish lifecycle and capture state; they do not measure gameplay mouse-look or performance.

In an earlier ordinary **Windowed** mode run, the user manually played for 20 seconds with the menus closed and confirmed normal character movement and mouse-look inside the reduced window. That run also passed all 11 scripted checks. Earlier screenshots separately showed camera rotation in both directions. These are short observations, not a sustained performance or general compatibility benchmark.

The initial failure also occurred without locking or fullscreen, so the user's brief screen lock during the first game run was not required to reproduce it. `tests/session_lock.py` separately exercises an initially tiled SDL2 XWayland client across capture/fullscreen, unlock before exit, exit while locked, and fullscreen exit while covered by a real `ext-session-lock-v1` lock. Its **27 checks** cover exact geometry, canvas camera return and keyboard isolation from the locked application. It does not test the game's renderer, anti-cheat or online modes.

Temporary desktop plugins/bindings were removed, the main desktop configuration was unchanged, and the game process survived. Personal screenshots and session logs remain local and are not published.

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
