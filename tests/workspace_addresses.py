"""Named workspace identity and canvas scope on Hyprland 0.57."""
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nested', ROOT/'source/tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
nav.WINDOWS = [('address-a', 'Address A'), ('address-b', 'Address B')]
n = nav.Nested(ROOT/'spatialoverview.so', ROOT/'work/workspace-address-shots', test_binds=False)
n.config_source = (ROOT/'tests/nested.lua').read_text().replace('@MODULE@', json.dumps(str(ROOT/'config/canvas.lua'), ensure_ascii=False))
failures = []


def check(ok, message):
    print(('PASS ' if ok else 'FAIL ')+message, flush=True)
    if not ok:
        failures.append(message)


def dispatch(expression):
    n.dispatch(expression)
    time.sleep(.7)


def mode(action):
    dispatch('hl.plugin.spatialoverview.mode('+json.dumps(action)+')')


def state():
    return json.loads(n.ctl('spatialoverview'))


def geometry():
    return {c['class']: (c['floating'], c['workspace']['name'], c['at'], c['size']) for c in n.clients()}


try:
    n.launch()
    dispatch('hl.dsp.window.move({window="class:address-a",workspace="name:Canvas Studio",follow=true})')
    original = geometry()
    mode('on')
    current = geometry()
    check(current['address-a'][0] and current['address-b'] == original['address-b'], 'named workspace canvas only detaches its own windows')
    result = n.ctl('eval', 'assert(hl.plugin.spatialoverview.session().workspace_address == hl.get_active_workspace().addressable_name)')
    check(result == 'ok', 'session exposes the full named workspace address')
    check(bool(state()['screens']), 'named workspace canvas survives its own workspace event')
    dispatch('hl.plugin.spatialoverview.canvas("zoom out")')
    camera = state()['screens'][0]['zoom']
    mode('off')
    check(geometry() == original, 'named workspace returns to exact original native geometry')
    mode('on')
    check(abs(state()['screens'][0]['zoom']-camera) < .005, 'named workspace retains its separate camera')
    dispatch('hl.dsp.focus({workspace="1"})')
    check(not state()['screens'] and geometry() == original, 'leaving the named workspace closes its local canvas and restores tiling')
    mode('global')
    mode('on')
    check(all(c['floating'] for c in n.clients()), 'global canvas includes numbered and named workspaces together')
    mode('off')
    check(geometry() == original and not n.ctl('configerrors'), 'global exit preserves each original workspace and geometry')
finally:
    if getattr(n, "log", None):
        n.log.flush()
        (ROOT/"work/workspace-address-runtime.log").write_text(Path(n.log.name).read_text(errors="replace"))
    n.stop()

print('ALL PASSED' if not failures else f'{len(failures)} FAILED', flush=True)
raise SystemExit(bool(failures))
