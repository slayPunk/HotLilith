#!/usr/bin/env python3
"""Run a disposable nested Hyprland, without installing into the current session."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('canvas_preview', root / 'source/tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
nav.WINDOWS = []
module = root / 'config/canvas.lua'
n = nav.Nested(root / 'spatialoverview.so', root / 'work/preview-shots', test_binds=False,
    extra_lua='hl.config({plugin={spatialoverview={canvas={spawn_on_open=true}}}})')
n.config_source = (root / 'tests/nested.lua').read_text().replace('@MODULE@', json.dumps(str(module), ensure_ascii=False))
children = []
try:
    n.launch()
    print('Preview instance:', n.sig, flush=True)
    print('Preview: Super+G toggle, Super+Ctrl+G scope, Ctrl+wheel zoom, middle drag pan.', flush=True)
    print('Close the nested Hyprland window to exit. Your desktop configuration is unchanged.', flush=True)
    for i, title in enumerate(['Canvas notes', 'Controls', 'Terminal']):
        children.append(subprocess.Popen(['foot', '--font=monospace:size=13', '--app-id=canvas-preview-' + str(i), '--title=' + title,
            'python3', str(root / 'demo-window.py'), title], env=n.env(), start_new_session=True))
        time.sleep(.4)
    for _ in range(80):
        if len(n.clients()) >= len(children): break
        if n.proc.poll() is not None: raise RuntimeError('Preview compositor exited')
        time.sleep(.1)
    n.dispatch('hl.plugin.spatialoverview.mode("on")')
    time.sleep(.5)
    for i,(x,y) in enumerate([(80,80),(700,80),(380,520)]):
        selector=json.dumps('class:canvas-preview-'+str(i))
        n.dispatch('hl.dsp.window.resize({window='+selector+',x=520,y=330})')
        n.dispatch('hl.dsp.window.move({window='+selector+',x='+str(x)+',y='+str(y)+'})')
    time.sleep(.7)
    n.dispatch('hl.plugin.spatialoverview.canvas("fit")')
    n.dispatch('hl.plugin.spatialoverview.canvas("zoom out")')
    while n.proc.poll() is None: time.sleep(.5)
except KeyboardInterrupt:
    pass
finally:
    n.stop()
    for child in children:
        if child.poll() is None: child.terminate()
