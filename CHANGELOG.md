# Changelog

## Unreleased — 0.2 development snapshot

- Add tiling/canvas lifecycle and current-workspace/global scopes with separate persistent spatial memory.
- Restore native floating/workspace/fullscreen state and the original dwindle tree when window membership is unchanged.
- Preserve explicit workspace and scratchpad moves across canvas exit.
- Add window/camera inertia, magnetic move/resize alignment, guides, double borders, home and centre actions.
- Queue new standalone windows for drawn regions; Escape automatically places one. Keep transient dialogs with their parent.
- Project pointer locks/confinement into scaled windows, preserve relative device deltas and add legacy-game manual capture/release.
- Restore canvas camera and zoom after native fullscreen.
- Incorporate Phantomat PR #19 Wayland drag-and-drop support.
- Add ABI-aware builds, a guarded, binding-free Lua installer, a disposable preview and isolated integration tests.

- Inherit native window appearance and camera animations; theme-derived selection/minimap colors with explicit palette overrides, and opt-in extra borders.

The public snapshot targets Hyprland 0.56.2 with Lua configuration and dwindle, independently of Serpantinum. The main module does not assign or remove bindings; examples are opt-in. Personal Serpantinum integration is kept in separate private dotfiles. No release has been published yet.
