"""Integration checks against a real, isolated nested Hyprland.
Only the child's IPC instance is ever used for test actions.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('nested', ROOT / 'source/tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
nav.WINDOWS = [('canvas-a', 'Canvas A'), ('canvas-b', 'Canvas B'), ('canvas-c', 'Canvas C')]
shots = ROOT / 'work/shots'
module = ROOT / 'config/canvas.lua'
n = nav.Nested(ROOT / 'spatialoverview.so', shots, test_binds=False)
n.config_source = (ROOT / 'tests/nested.lua').read_text().replace('@MODULE@', json.dumps(str(module), ensure_ascii=False))
failures = []

def check(ok, message):
    print(('PASS ' if ok else 'FAIL ') + message, flush=True)
    if not ok: failures.append(message)

def mode(action):
    n.dispatch('hl.plugin.spatialoverview.mode(' + json.dumps(action) + ')')
    time.sleep(.7)

def canvas(action):
    n.dispatch('hl.plugin.spatialoverview.canvas(' + json.dumps(action) + ')')
    time.sleep(.5)

def geometry(c):
    return (c['floating'], c['workspace']['id'], c['at'], c['size'])

try:
    n.launch()
    check(len(n.clients()) == 3, 'three native Wayland test windows mapped')
    check(not n.ctl('configerrors'), 'custom Lua module loads without config errors')
    binds = json.loads(n.ctl('-j', 'binds'))
    check(any(b.get('description') == 'Original lock binding' for b in binds), 'original lock shortcut survives module loading')
    check(sum(b.get('description') == 'Tiling / canvas' for b in binds) == 1, 'cold loader registers exactly one mode hotkey')
    # Put a tiled window on a different workspace, then return.
    n.dispatch('hl.dsp.window.move({window="class:canvas-c",workspace="2",follow=false})')
    time.sleep(.4)
    outside = next(c for c in n.clients() if c['class'] == 'canvas-c')
    original_outside = geometry(outside)
    before = {c['class']: c['floating'] for c in n.clients()}
    n.dispatch('hl.dsp.window.resize({window="class:canvas-a",x=135,y=0,relative=true})')
    time.sleep(.5)
    original_tiled = {c['class']: geometry(c) for c in n.clients()}
    n.shot('01-tiling')
    mode('on')
    windows = n.clients()
    check(all(c['floating'] for c in windows if c['workspace']['id'] == 1), 'workspace canvas detaches current workspace windows')
    check(geometry(next(c for c in windows if c['class']=='canvas-c')) == original_outside, 'workspace canvas does not alter another workspace')
    canvas('zoom out')
    check(json.loads(n.ctl('spatialoverview'))['screens'][0]['zoom'] < 1, 'canvas supports real render zoom')
    n.shot('02-workspace-canvas')
    n.dispatch('hl.dsp.window.move({window="class:canvas-a",x=2200,y=400})')
    time.sleep(.4)
    saved_workspace = geometry(next(c for c in n.clients() if c['class']=='canvas-a'))
    canvas('pan right')
    time.sleep(1.1)  # compare the settled camera, not an in-flight animation
    saved_camera = json.loads(n.ctl('spatialoverview'))['screens'][0]
    mode('toggle')
    check({c['class']:c['floating'] for c in n.clients()} == before, 'mode toggle returns windows to native tiled/floating states')
    check({c['class']:geometry(c) for c in n.clients()} == original_tiled, 'dwindle restores original window placement and split proportions')
    check(not json.loads(n.ctl('spatialoverview'))['screens'], 'mode exit removes all canvas cameras')
    mode('on')
    check(geometry(next(c for c in n.clients() if c['class']=='canvas-a')) == saved_workspace, 'workspace canvas remembers its window arrangement')
    time.sleep(1.1)
    camera = json.loads(n.ctl('spatialoverview'))['screens'][0]
    check(camera['zoom'] == saved_camera['zoom'] and camera['view'] == saved_camera['view'], 'workspace canvas remembers camera position and zoom')
    if camera['zoom'] != saved_camera['zoom'] or camera['view'] != saved_camera['view']:
        print('Camera before/after:', saved_camera, camera, flush=True)
    mode('scope')
    check(all(c['floating'] for c in n.clients()), 'scope hotkey action includes other workspaces in global mode')
    canvas('fit')
    n.shot('03-global-canvas')
    n.dispatch('hl.dsp.window.move({window="class:canvas-a",x=3200,y=900})')
    time.sleep(.3)
    saved_global = geometry(next(c for c in n.clients() if c['class']=='canvas-a'))
    mode('scope')
    check(geometry(next(c for c in n.clients() if c['class']=='canvas-c')) == original_outside, 'switching back restores other workspace state')
    check(geometry(next(c for c in n.clients() if c['class']=='canvas-a')) == saved_workspace, 'workspace and global spatial arrangements stay separate')
    mode('scope')
    check(geometry(next(c for c in n.clients() if c['class']=='canvas-a')) == saved_global, 'global arrangement is restored on next visit')
    # A window that was already floating must remain floating on exit.
    mode('off')
    n.dispatch('hl.dsp.window.float({window="class:canvas-b",action="enable"})')
    time.sleep(.3)
    mode('on')
    mode('off')
    check(next(c for c in n.clients() if c['class']=='canvas-b')['floating'], 'pre-existing floating window remains floating')
    for _ in range(4): mode('toggle')
    mode('off')
    # When membership changes, retain a valid native tree rather than restoring
    # stale targets from the snapshot.
    mode('on')
    n.dispatch('hl.dsp.exec_cmd("foot --app-id=canvas-new --title=New /usr/bin/cat")')
    time.sleep(.6)
    mode('off')
    check(any(c['class']=='canvas-new' and not c['floating'] for c in n.clients()), 'new windows return to a valid tiled layout')
    mode('on')
    n.dispatch('hl.dsp.window.close({window="class:canvas-new"})')
    time.sleep(.5)
    mode('off')
    check(n.proc.poll() is None and len(n.clients()) == 3, 'closing windows on the canvas does not restore stale targets')
    mode('workspace')
    mode('on')
    n.dispatch('hl.dsp.focus({workspace="2"})')
    time.sleep(.8)
    check(not json.loads(n.ctl('spatialoverview'))['screens'], 'switching workspace exits the local canvas')
    keyboard = ROOT / 'work/tools/keyboard'
    if keyboard.is_file():
        def keys(chord):
            subprocess.run([str(keyboard),chord],env=n.env(),check=True,timeout=8)
            time.sleep(.6)
        keys('super+g')
        check(bool(json.loads(n.ctl('spatialoverview'))['screens']), 'Super+G really opens the canvas through its key binding')
        pointer = ROOT / 'source/.build/vpointer'
        if pointer.is_file():
            camera = json.loads(n.ctl('spatialoverview'))['screens'][0]
            subprocess.run([str(pointer),'1280','720','abs','640','360','mdown','rel','110','55','sleep','200','mup'],env=n.env(),check=True,timeout=8)
            time.sleep(.7)
            moved = json.loads(n.ctl('spatialoverview'))['screens'][0]
            check(abs(moved['view'][0]-camera['view'][0])>30,'middle-button drag really pans the canvas')
            held = subprocess.Popen([str(keyboard),'hold-ctrl'],env=n.env(),stdout=subprocess.PIPE,text=True)
            try:
                check(held.stdout.readline().strip()=='ready','virtual Ctrl key is held inside the child session')
                subprocess.run([str(pointer),'1280','720','axis','15','sleep','100'],env=n.env(),check=True,timeout=8)
                time.sleep(.8)
                zoomed = json.loads(n.ctl('spatialoverview'))['screens'][0]
                check(zoomed['zoom']<moved['zoom'],'Ctrl+wheel really zooms through pointer input')
            finally:
                held.wait(timeout=5)
        keys('super+ctrl+g')
        check(all(c['floating'] for c in n.clients()), 'Super+Ctrl+G really switches to the global canvas')
        keys('super+ctrl+shift+g')
        check(not json.loads(n.ctl('spatialoverview'))['screens'], 'emergency shortcut really returns to native layout')
    mode('on')
    n.dispatch('hl.dsp.window.fullscreen({mode="fullscreen",action="toggle"})')
    time.sleep(.8)
    mode('off')
    check(not any(c['fullscreen'] for c in n.clients()) and not json.loads(n.ctl('spatialoverview'))['screens'], 'mode exit restores a window taken fullscreen from the canvas')
    check(n.proc.poll() is None, 'compositor survives repeated mode toggles')
    check(not n.ctl('configerrors'), 'no config errors after mode transitions')
    n.shot('04-returned-to-tiling')
finally:
    print('Nested log:', n.log.name if getattr(n,'log',None) else '', flush=True)
    if getattr(n,'log',None):
        n.log.flush()
        (ROOT / 'work/runtime.log').write_text(Path(n.log.name).read_text(errors='replace'))
    n.stop()
print('ALL PASSED' if not failures else f'{len(failures)} FAILED', flush=True)
raise SystemExit(bool(failures))
