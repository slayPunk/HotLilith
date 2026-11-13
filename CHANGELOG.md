# Changelog

## Unreleased — 0.2 development snapshot

- Port the renderer, window backends, workspace identity, keybinds and IPC to Hyprland 0.57.0. Rebuild against matching headers; the previous 0.56.2 binary is incompatible.
- Preserve theme inheritance with the new configuration provenance API, including unset accent, shadow and animation overrides.
- Reject missing development dependencies before replacing an existing build.
- Restore originally tiled clients even when they publish canvas-sized protocol maxima; keep explicit user size rules effective.
- Share the canvas hook lifecycle list and test partial activation rollback, repeated shutdown and plugin reload.

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

The public snapshot targets Hyprland 0.57.0 with Lua configuration and dwindle, independently of Serpantinum. The main module does not assign or remove bindings; examples are opt-in. Personal Serpantinum integration is kept in separate private dotfiles. No release has been published yet.
