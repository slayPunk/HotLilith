-- Disposable child compositor; it never imports the user's session config.
hl.monitor({ output = "", mode = "1280x720@60", position = "auto", scale = 1 })
hl.config({
  general = { gaps_in = 4, gaps_out = 6, border_size = 1 },
  decoration = { rounding = 12, blur = {enabled = false}, shadow = {enabled = false} },
  animations = { enabled = true },
  misc = { disable_hyprland_logo = true, disable_splash_rendering = true, force_default_wallpaper = 0 },
})
hl.curve("nestedEase", {type="bezier",points={{0.22,1},{0.36,1}}})
hl.animation({leaf="global",enabled=true,speed=8,bezier="nestedEase"})
hl.bind("SUPER + SHIFT + ESCAPE", hl.dsp.exit())
hl.bind("SUPER + Q", hl.dsp.window.close())
hl.bind("SUPER + L", function() end, {description = "Original lock binding"})
hl.plugin.load("@PLUGIN@")
local hotlilith_module = @MODULE@
dofile(hotlilith_module)
-- Tests and preview explicitly opt in to the public example shortcuts.
dofile(hotlilith_module:gsub("canvas%.lua$", "bindings.example.lua"))
-- Lifecycle fixtures map windows without interactive placement.
hl.config({plugin={spatialoverview={canvas={spawn_on_open=false}}}})
hl.permission("/usr/bin/grim", "screencopy", "allow")
-- Disable the upstream harness's extra overview defaults.
local plugin_loaded = false
