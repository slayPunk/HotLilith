"""Reproduce audit failures using a real, disposable compositor."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nested', ROOT/'source/tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
nav.WINDOWS = [('reg-a', 'Floating'), ('reg-b', 'Tiled'), ('reg-c', 'Anchor')]
n = nav.Nested(ROOT/'spatialoverview.so', ROOT/'work/regression-shots', test_binds=False)
n.config_source = (ROOT/'tests/nested.lua').read_text().replace('@MODULE@', json.dumps(str(ROOT/'config/canvas.lua'), ensure_ascii=False))
failures = []


def check(ok, message):
    print(('PASS ' if ok else 'FAIL ') + message, flush=True)
    if not ok:
        failures.append(message)


def run(expr):
    n.dispatch(expr)
    time.sleep(.7)


def mode(action):
    run('hl.plugin.spatialoverview.mode(' + json.dumps(action) + ')')


def client(app):
    return next(c for c in n.clients() if c['class'] == app)


def box(c):
    return c['at'], c['size']


try:
    n.launch()
    time.sleep(1)
    monitor = json.loads(n.ctl('-j', 'monitors'))[0]
    width, height = int(monitor['width']/monitor['scale']), int(monitor['height']/monitor['scale'])
    run('hl.dsp.window.float({window="class:reg-a",action="enable"})')
    run(f'hl.dsp.window.resize({{window="class:reg-a",x={width+320},y={height+180}}})')
    run('hl.dsp.window.move({window="class:reg-a",x=-200,y=-100})')
    original = box(client('reg-a'))
    check(original[0] == [-200, -100] and original[1][0] > width and original[1][1] > height,
          'fixture is deliberately off-screen and larger than the monitor')
    mode('on')
    mode('off')
    check(box(client('reg-a')) == original, 'unchanged output preserves floating position and oversized dimensions exactly')
    mode('on')
    run('hl.dsp.window.move({window="class:reg-b",workspace="2",follow=false})')
    check(client('reg-b')['workspace']['id'] == 2 and not client('reg-b')['floating'],
          'moving outside the local canvas immediately restores native tiling')
    mode('off')
    check(client('reg-b')['workspace']['id'] == 2 and not client('reg-b')['floating'],
          'mode exit preserves the explicit workspace move')
    run('hl.dsp.window.move({window="class:reg-b",workspace="1",follow=false})')
    mode('on')
    run('hl.dsp.window.move({window="class:reg-b",workspace="special:magic",follow=false})')
    check(client('reg-b')['workspace']['name'] == 'special:magic' and not client('reg-b')['floating'],
          'sending to scratchpad immediately releases the window from the canvas')
    mode('off')
    check(client('reg-b')['workspace']['name'] == 'special:magic', 'scratchpad membership survives mode exit')
    run('hl.dsp.window.move({window="class:reg-b",workspace="1",follow=false})')
    mode('global')
    mode('on')
    run('hl.dsp.window.move({window="class:reg-b",workspace="2",follow=false})')
    check(client('reg-b')['floating'], 'moving between normal workspaces keeps a global-canvas window managed')
    mode('off')
    check(client('reg-b')['workspace']['id'] == 2 and not client('reg-b')['floating'],
          'global-canvas exit preserves the chosen native workspace')
    run('hl.dsp.window.move({window="class:reg-b",workspace="1",follow=false})')
    mode('workspace')
    mode('on')
    run('hl.dsp.window.move({window="class:reg-b",workspace="2",follow=true})')
    state = json.loads(n.ctl('spatialoverview'))
    check(not state['screens'] and client('reg-b')['workspace']['id'] == 2 and not client('reg-b')['floating'],
          'move-and-follow exits the local canvas without undoing the move')
    run('hl.dsp.focus({workspace="1"})')
    mode('on')
    run('hl.dsp.window.move({window="class:reg-a",workspace="2",follow=false})')
    check(client('reg-a')['workspace']['id'] == 2 and client('reg-a')['floating'] and box(client('reg-a')) == original,
          'a released native floating window retains its original geometry')
    mode('off')
    check(client('reg-a')['workspace']['id'] == 2 and box(client('reg-a')) == original,
          'later mode exit does not reclaim a released floating window')
    # Exercise the actual installer against this child's socket and a throwaway
    # config file; never point --config at the user's desktop configuration.
    mode('on')
    config = Path(n.tmp.name)/'installer.lua'
    config.write_text('-- fixture\n-- BEGIN SYSPUNK CANVAS\n-- bindings\n-- END SYSPUNK CANVAS\n')
    removed = subprocess.run([sys.executable, str(ROOT/'install.py'), '--remove', '--config', str(config)],
                             env=n.env(), capture_output=True, text=True, timeout=15)
    state = json.loads(n.ctl('spatialoverview'))
    check(removed.returncode == 0 and not state['screens'] and not state['fullscreen'] and
          'BEGIN SYSPUNK CANVAS' not in config.read_text(), 'real installer verifies shutdown before disconnecting the module')
    if removed.returncode:
        print(removed.stdout, removed.stderr, flush=True)
    check(n.proc.poll() is None and not n.ctl('configerrors'), 'regression scenarios leave a healthy compositor')
finally:
    if getattr(n, 'log', None):
        n.log.flush()
        (ROOT/'work/regressions-runtime.log').write_text(Path(n.log.name).read_text(errors='replace'))
    n.stop()
print('ALL PASSED' if not failures else f'{len(failures)} FAILED', flush=True)
raise SystemExit(bool(failures))
