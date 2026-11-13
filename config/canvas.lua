-- HotLilith settings and lifecycle for Hyprland 0.57.0. No key bindings.
-- The renderer is a locally patched Phantomat, with its original license.
local loaded = false
for _, plugin in ipairs(hl.get_loaded_plugins()) do
  if plugin.name == "spatialoverview" then loaded = true; break end
end
if not loaded then
  return -- Load the plugin binary before including this module.
end
if not hl.plugin.spatialoverview.session then return end

local function state() return hl.plugin.spatialoverview.session() end

-- Camera animations inherit windowsMove; window decorations stay native.
-- Put explicit appearance overrides after this module in your own dotfiles.
hl.config({ plugin = { spatialoverview = {
  layout = "grid", workspace_gap = 0, scale = 0.45,
  distortion = { enabled = false },
  -- Workspace-card effects; individual windows keep native blur/shadows.
  blur = false, shadow = { enabled = false },
  chrome_animation = { enabled = false },
  parallax = { enabled = false },
  navigator = { enabled = false, pointer = false, labels = false },
  canvas = {
    enabled = true, desktop_mode = true, persistent = true,
    initial_zoom = 0.5, min_zoom = 0.1, max_zoom = 2.0, zoom_step = 0.12,
    auto_float = true, auto_place = true, placement_gap = 32,
    direct_input = true, hover_focus = false, linked_screens = true,
    space_pan = false, remember_layout = true, spawn_on_open = true,
    inertia_enabled = true, magnet_enabled = true, magnet_guides = true,
    magnet_distance = 12, magnet_gap = 12, double_border = false,
    snap_enabled = false, grid_enabled = false,
    minimap_enabled = true, minimap_width = 200, minimap_height = 125,
    background_dim = 0, allow_window_overflow = true,
    viewport_enabled = false,
    commit_viewport_on_close = false,
  },
} } })

-- A normal workspace change exits a workspace-only canvas. Defer destruction
-- until the current event has finished traversing its listeners.
local exit_timer
hl.on("workspace.active", function()
  local s, ws = state(), hl.get_active_workspace()
  if s.active and s.scope == "workspace" and ws and ws.addressable_name ~= s.workspace_address then
    exit_timer = hl.timer(function()
      local current, current_ws = state(), hl.get_active_workspace()
      if current.active and current.scope == "workspace" and current_ws and
          current_ws.addressable_name ~= current.workspace_address then hl.plugin.spatialoverview._dispatch("mode", "off") end
    end, { type = "oneshot", timeout = 1 })
  end
end)
