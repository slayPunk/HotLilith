"""Visible theme inheritance and camera motion in a disposable compositor.

Requires Pillow in addition to the integration-test dependencies.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nested', ROOT/'source/tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
nav.WINDOWS = [('theme-a', 'Theme A'), ('theme-b', 'Theme B')]
n = nav.Nested(ROOT/'spatialoverview.so', ROOT/'work/appearance-shots', test_binds=False)
n.config_source = (ROOT/'tests/nested.lua').read_text().replace('@MODULE@', json.dumps(str(ROOT/'config/canvas.lua'), ensure_ascii=False))
n.extra_lua = '''hl.config({general={border_size=8,["col.active_border"]="rgb(ff2020)",
 ["col.inactive_border"]="rgb(402020)"},decoration={rounding=0},animations={enabled=false}})'''
failures = []


def check(ok, message):
    print(('PASS ' if ok else 'FAIL ')+message, flush=True)
    if not ok:
        failures.append(message)


def action(name, arg, delay=.25):
    n.dispatch('hl.plugin.spatialoverview.'+name+'('+json.dumps(arg)+')')
    time.sleep(delay)


def zoom():
    return json.loads(n.ctl('spatialoverview'))['screens'][0]['zoom']


def colored(path, channel, box):
    image = Image.open(path).convert('RGB').crop(box)
    pixels = (image.getpixel((x, y)) for y in range(image.height) for x in range(image.width))
    return sum(p[channel] > 100 and all(p[channel] > p[c]*1.8 for c in range(3) if c != channel) for p in pixels)


def option(name):
    return n.ctl('-j', 'getoption', name)


def region():
    action('canvas', 'spawn-region')
    subprocess.run([str(ROOT/'source/.build/vpointer'), '1280', '720', 'abs', '650', '70', 'down', 'rel', '260', '180', 'up'], env=n.env(), check=True, timeout=8)
    time.sleep(.25)


try:
    n.launch()
    names = ['general:border_size', 'general:col.active_border', 'decoration:rounding', 'animations:enabled']
    before = [option(name) for name in names]
    action('mode', 'on')
    action('canvas', 'home')
    for app, x, y in [('theme-a', 100, 100), ('theme-b', 700, 350)]:
        n.dispatch(f'hl.dsp.window.resize({{window="class:{app}",x=300,y=200}})')
        n.dispatch(f'hl.dsp.window.move({{window="class:{app}",x={x},y={y}}})')
    n.dispatch('hl.dsp.focus({window="class:theme-a"})')
    time.sleep(.3)
    region()
    red = n.shot('red-square')
    check(colored(red, 0, (645, 90, 655, 230)) > 100, 'region border inherits the red active-border accent')
    check(colored(red, 0, (90, 120, 105, 270)) > 300, 'native thick window border remains red on the canvas')
    subprocess.run([str(ROOT/'work/tools/keyboard'), 'escape'], env=n.env(), check=True, timeout=8)
    action('canvas', 'zoom out', .12)
    z = zoom()
    time.sleep(.3)
    check(z < 1 and zoom() == z, 'globally disabled animations make zoom settle immediately')
    action('canvas', 'home')
    check([option(name) for name in names] == before, 'canvas interactions leave native appearance options unchanged')

    # Reload an actual user config while the canvas is active.
    config = Path(n.tmp.name)/'nested.lua'
    config.write_text(config.read_text()+'''\nhl.config({general={border_size=3,["col.active_border"]="rgb(20ff40)",
 ["col.inactive_border"]="rgb(204028)"},decoration={rounding=28},animations={enabled=true}})
hl.curve("userLinear",{type="bezier",points={{0,0},{1,1}}})
hl.animation({leaf="windowsMove",enabled=true,speed=20,bezier="userLinear"})\n''')
    n.ctl('reload')
    time.sleep(.5)
    action('canvas', 'home', 2.2)
    region()
    green = n.shot('green-rounded')
    check(colored(green, 1, (645, 90, 655, 230)) > 100 and colored(green, 0, (645, 90, 655, 230)) == 0, 'live theme reload recolors the region without a plugin preset change')
    check(colored(green, 1, (90, 120, 105, 270)) > 50, 'native window border follows the green theme after reload')
    square = Image.open(red).convert('RGB')
    rounded = Image.open(green).convert('RGB')
    check(square.getpixel((98, 98))[0] > 200 and max(rounded.getpixel((98, 98))) < 50, 'window corners change from square to rounded with the native theme')
    check(square.getpixel((94, 150))[0] > 200 and max(rounded.getpixel((94, 150))) < 50, 'native border width changes from eight pixels to three')
    subprocess.run([str(ROOT/'work/tools/keyboard'), 'escape'], env=n.env(), check=True, timeout=8)
    action('canvas', 'zoom out', .15)
    early = zoom()
    time.sleep(2.1)
    settled = zoom()
    check(early > settled+.01, f'camera inherits the slow user windowsMove animation (early={early}, settled={settled})')

    action('canvas', 'home', 2.2)
    n.ctl('eval', 'hl.config({plugin={spatialoverview={canvas={accent="rgb(4080ff)",panel_color="rgb(e0e0e0)"}}}})')
    region()
    custom = n.shot('explicit-accent')
    check(colored(custom, 2, (645, 90, 655, 230)) > 100, 'an explicit canvas accent overrides automatic inheritance')
    n.ctl('eval', 'hl.config({animations={enabled=false},plugin={spatialoverview={animation={enabled=true}}}})')
    action('canvas', 'zoom out', .12)
    z = zoom()
    time.sleep(.3)
    check(zoom() == z, 'global reduced motion wins over an explicit plugin animation enable')
    action('mode', 'off')
    check(all(not c['floating'] for c in n.clients()) and not n.ctl('configerrors'), 'theme reload and overrides preserve return to native tiling')
finally:
    if getattr(n, 'log', None):
        n.log.flush()
        (ROOT/'work/appearance-runtime.log').write_text(Path(n.log.name).read_text(errors='replace'))
    n.stop()

print('ALL PASSED' if not failures else f'{len(failures)} FAILED', flush=True)
raise SystemExit(bool(failures))
