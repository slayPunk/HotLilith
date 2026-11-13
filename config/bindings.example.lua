-- OPTIONAL example bindings for Hyprland 0.57.0.
-- Copy/edit the combinations before including this file. Never loaded by install.py.
-- Existing user bindings are not removed. Do not add a combination you already use.
local function run(name, action)
  return hl.plugin.spatialoverview._dispatch(name, action)
end
local function state() return hl.plugin.spatialoverview.session() end
local function notice(text)
  hl.notification.create({ text = text, timeout = 1800 })
end
local function mode(action)
  local ok, err = pcall(run, "mode", action)
  if not ok then notice(tostring(err)); return end
  local s = state()
  notice((s.active and "Canvas · " or "Tiling · canvas preset: ") ..
    (s.scope == "workspace" and "workspace" or "all workspaces"))
end

-- Suggested combinations: review conflicts before opting in.
hl.bind("SUPER + G", function() mode("toggle") end,
  { description = "Tiling / canvas" })
hl.bind("SUPER + CTRL + G", function() mode("scope") end,
  { description = "Canvas: current workspace / all workspaces" })
hl.bind("SUPER + CTRL + SHIFT + G", function() mode("off") end,
  { description = "Canvas: emergency return to tiling", submap_universal = true })
hl.bind("SUPER + ALT + G", function()
  if state().active then run("overview", "toggle all") end
end, { description = "Canvas: overview / 100%" })
hl.bind("SUPER + Z", function()
  if state().active then run("canvas", "fit") end
end, { description = "Canvas: fit all windows" })
hl.bind("SUPER + CTRL + equal", function()
  if state().active then run("canvas", "zoom in") end
end, { repeating = true, description = "Canvas: zoom in" })
hl.bind("SUPER + CTRL + minus", function()
  if state().active then run("canvas", "zoom out") end
end, { repeating = true, description = "Canvas: zoom out" })


for _, item in ipairs({{"Home", "home"}, {"C", "center"}, {"N", "spawn-region"}}) do
  local key, action = item[1], item[2]
  hl.bind("SUPER + CTRL + " .. key, function()
    if state().active then
      run("canvas", action)
      if action == "spawn-region" then notice("Draw an area, then open an app · Esc cancels") end
    end
  end, { description = "Canvas: " .. action })
end

hl.bind("SUPER + CTRL + P", function()
  if state().active then run("canvas", "capture-pointer") end
end, { description = "Canvas: toggle pointer capture for older games" })
hl.bind("SUPER + CTRL + Escape", function()
  if state().active then run("canvas", "release-pointer") end
end, { description = "Canvas: release game pointer", submap_universal = true })

-- Canvas-only navigation uses a separate chord; native focus bindings stay yours.
for _, item in ipairs({{"Left", "left"}, {"Right", "right"}, {"Up", "up"}, {"Down", "down"}}) do
  local key, direction = item[1], item[2]
  hl.bind("SUPER + CTRL + ALT + " .. key, function()
    if state().active then run("navigate", direction) end
  end)
  hl.bind("SUPER + ALT + " .. key, function()
    if state().active then run("canvas", "pan " .. direction) end
  end, { repeating = true })
end

-- If your config does not already provide mouse move/resize, opt in to these:
-- hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
-- hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
