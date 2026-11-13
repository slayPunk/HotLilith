"""Restore initially tiled clients that constrain their size on the canvas."""
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nested', ROOT/'source/tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
nav.WINDOWS = [('hints-anchor', 'Size hints anchor')]
backend = sys.argv[1] if len(sys.argv) > 1 else 'x11'
assert backend in ('x11', 'wayland')
n = nav.Nested(ROOT/'spatialoverview.so', ROOT/'work/size-hints-shots', test_binds=False)
n.config_source = (ROOT/'tests/nested.lua').read_text().replace('@MODULE@', json.dumps(str(ROOT/'config/canvas.lua'), ensure_ascii=False))
failures = []
keyboard = None
selector = json.dumps('title:hotlilit-relative')


def dispatch(expr):
    n.dispatch(expr)
    time.sleep(.9)


def state():
    return json.loads(n.ctl('spatialoverview'))


def window():
    return next(w for w in n.clients() if w['title'] == 'hotlilit-relative')


def geometry(w):
    return {key: w[key] for key in ('at', 'size', 'workspace', 'floating', 'fullscreen')}


def check(ok, message):
    print(('PASS ' if ok else 'FAIL ')+message, flush=True)
    if not ok:
        failures.append(message)


try:
    n.launch()
    log = Path(n.tmp.name)/'client.log'
    command = shlex.join(['env', 'SDL_VIDEODRIVER='+backend, str(ROOT/'work/tools/relative-client')])
    dispatch('hl.dsp.exec_cmd('+json.dumps(command+' > '+shlex.quote(str(log))+' 2>&1', ensure_ascii=False)+')')
    keyboard = subprocess.Popen([str(ROOT/'work/tools/keyboard'), 'hold-seat'], env=n.env(), stdout=subprocess.DEVNULL)
    dispatch('hl.dsp.window.float({window='+selector+',action="disable"})')
    native = geometry(window())
    assert not native['floating'] and 'ready '+backend in log.read_text(), 'invalid native fixture'
    identity = window()['pid'], window()['address']
    dispatch('hl.plugin.spatialoverview.mode("on")')
    dispatch('hl.dsp.focus({window='+selector+'})')
    subprocess.run([str(ROOT/'work/tools/keyboard'), 'n'], env=n.env(), check=True, timeout=5)
    time.sleep(.5)
    record = next(w for w in state()['native_windows'] if w['address'] == identity[1])
    maximum = record['max_size']
    check('maximum ' in log.read_text() and max(maximum) < 1280 and min(maximum) > 0,
          backend+': client publishes finite canvas-sized maximum hints')
    check(not record['saved_floating'] and record['floating'], backend+': saved state remains tiled')
    dispatch('hl.plugin.spatialoverview.mode("off")')
    check(geometry(window()) == native, backend+': exact original tiled state and geometry restored despite new client maximum')
    rendered = [line.split()[1:] for line in log.read_text().splitlines() if line.startswith('render-size ')]
    check(bool(rendered) and list(map(int, rendered[-1])) == native['size'],
          backend+': application render buffer resizes to the restored native geometry')
    dispatch('hl.dsp.focus({window='+selector+'})')
    offset = log.stat().st_size
    subprocess.run([str(ROOT/'work/tools/keyboard'), 'w'], env=n.env(), check=True, timeout=5)
    time.sleep(.3)
    check('key W' in log.read_text()[offset:], backend+': application receives keyboard input after returning to tiling')
    # Re-enter to inspect the real maximum after the scoped restore policy ended.
    dispatch('hl.plugin.spatialoverview.mode("on")')
    record = next(w for w in state()['native_windows'] if w['address'] == identity[1])
    check(record['max_size'] == maximum, backend+': client size hints remain effective after restoration')
    dispatch('hl.plugin.spatialoverview.mode("off")')
    check(geometry(window()) == native, backend+': repeated entry/exit restores the same geometry')
    check((window()['pid'], window()['address']) == identity and not n.ctl('configerrors'),
          backend+': same client survives with no configuration errors')
    dispatch('hl.plugin.spatialoverview.mode("on")')
    dispatch('hl.dsp.window.set_prop({window='+selector+',prop="max_size",value="400 300"})')
    dispatch('hl.plugin.spatialoverview.mode("off")')
    check(window()['floating'], backend+': explicit user maximum still prevents incompatible tiling')
    dispatch('hl.plugin.spatialoverview.mode("on")')
    record = next(w for w in state()['native_windows'] if w['address'] == identity[1])
    check(record['max_size'] == [400, 300], backend+': explicit user maximum is preserved')
    dispatch('hl.plugin.spatialoverview.mode("off")')
finally:
    if keyboard:
        keyboard.terminate()
        keyboard.wait(timeout=3)
    n.stop()
print('ALL PASSED' if not failures else f'{len(failures)} FAILED', flush=True)
raise SystemExit(bool(failures))
