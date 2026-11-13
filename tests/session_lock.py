"""XWayland fullscreen/capture restoration across real lock/unlock in a child.

The lock client has no authentication UI and is restricted to the explicit
disposable Wayland socket. It never locks or unlocks the desktop session.
"""
import importlib.util
import json
import os
from pathlib import Path
import select
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nested', ROOT/'source/tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
nav.WINDOWS = [('lock-anchor', 'Lock anchor')]
n = nav.Nested(ROOT/'spatialoverview.so', ROOT/'work/session-lock-shots', test_binds=False)
n.config_source = (ROOT/'tests/nested.lua').read_text().replace('@MODULE@', json.dumps(str(ROOT/'config/canvas.lua'), ensure_ascii=False))
client_log = Path(n.tmp.name)/'client.log'
selector = 'title:hotlilit-relative'
pointer = keyboard = locker = None
failures = []


def literal(value):
    return json.dumps(value, ensure_ascii=False)


def dispatch(expr):
    n.dispatch(expr)
    time.sleep(.35)


def mode(action):
    dispatch('hl.plugin.spatialoverview.mode('+literal(action)+')')


def canvas(action):
    dispatch('hl.plugin.spatialoverview.canvas('+literal(action)+')')


def window_action(action, options):
    dispatch('hl.dsp.window.'+action+'({window='+literal(selector)+','+options+'})')


def game():
    return next(w for w in n.clients() if w['title'] == 'hotlilit-relative')


def geometry(window):
    return {key: window[key] for key in ['floating', 'at', 'size', 'fullscreen', 'workspace']}


def state():
    return json.loads(n.ctl('spatialoverview'))


def key():
    subprocess.run([str(ROOT/'work/tools/keyboard'), 'w'], env=n.env(), check=True, timeout=5)
    time.sleep(.15)


def check(ok, message):
    print(('PASS ' if ok else 'FAIL ')+message, flush=True)
    if not ok:
        failures.append(message)


try:
    n.launch()
    command = shlex.join(['env', 'SDL_VIDEODRIVER=x11', str(ROOT/'work/tools/relative-client')])
    dispatch('hl.dsp.exec_cmd('+literal(command+' > '+shlex.quote(str(client_log))+' 2>&1')+')')
    window_action('float', 'action="disable"')
    native = geometry(game())
    check(game()['xwayland'] and not native['floating'], 'fixture is a native tiled XWayland window before canvas entry')
    assert game()['xwayland'] and not native['floating'], 'invalid fixture'
    identity = game()['pid'], game()['address']
    pointer = subprocess.Popen([str(ROOT/'source/.build/vpointer'), '1280', '720', 'stdin'], env=n.env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert pointer.stdout.readline().strip() == 'ready'
    keyboard = subprocess.Popen([str(ROOT/'work/tools/keyboard'), 'hold-seat'], env=n.env(), stdout=subprocess.DEVNULL)

    for phase in ['no-lock', 'capture-no-lock', 'unlock-before-exit', 'exit-while-locked', 'fullscreen-lock-exit']:
        mode('on')
        canvas('zoom out')
        # The fixture's windowsMove lasts 0.8 s: snapshot the settled camera.
        time.sleep(.6)
        dispatch('hl.dsp.focus({window='+literal(selector)+'})')
        if phase != 'no-lock':
            canvas('capture-pointer')
        native_record = next(w for w in state()['native_windows'] if w['address'] == game()['address'])
        assert not native_record['saved_floating'] and native_record['floating'], 'native-state diagnostic lost the tiled baseline'
        assert len(native_record['max_size']) == 2
        saved = state()['screens'][0]
        window_action('fullscreen', 'mode="fullscreen",action="set"')
        check(bool(state()['fullscreen']) and not state()['screens'], phase+': native fullscreen suspends the canvas')
        if phase != 'fullscreen-lock-exit':
            window_action('fullscreen', 'mode="fullscreen",action="unset"')
            time.sleep(.6)
            restored = state()['screens'][0]
            check(restored['zoom'] == saved['zoom'] and restored['view'] == saved['view'], phase+': fullscreen restores the exact camera '+str((saved['zoom'], saved['view'], restored['zoom'], restored['view'])))

        if phase in ['no-lock', 'capture-no-lock']:
            canvas('release-pointer')
            mode('off')
        else:
            # Positive control: this device really delivers W to the client.
            start = len(client_log.read_text(errors='replace'))
            key()
            check('key W' in client_log.read_text(errors='replace')[start:], phase+': keyboard reaches the unlocked application')
            host = os.environ['WAYLAND_DISPLAY']
            assert n.socket != host, 'refuse to lock the host socket'
            env = n.env()
            env['HOTLILITH_HOST_WAYLAND_DISPLAY'] = host
            locker = subprocess.Popen([str(ROOT/'work/tools/session-lock-client'), n.socket], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            assert select.select([locker.stdout], [], [], 5)[0], 'lock client timed out'
            assert locker.stdout.readline().strip() == 'locked', 'lock was not granted'
            time.sleep(.2)
            start = len(client_log.read_text(errors='replace'))
            key()
            check('key W' not in client_log.read_text(errors='replace')[start:], phase+': locked session does not forward keyboard input to the game')
            if phase != 'unlock-before-exit':
                mode('off')
            locker.stdin.write('unlock\n')
            locker.stdin.flush()
            assert locker.wait(timeout=5) == 0, 'lock client failed to unlock'
            locker = None
            time.sleep(.25)
            if phase == 'unlock-before-exit':
                mode('off')

        check(geometry(game()) == native, phase+': original tiled state, workspace, position and size are restored')
        check(not state()['screens'] and not state()['fullscreen'], phase+': no canvas/fullscreen records remain')

    check((game()['pid'], game()['address']) == identity and not n.ctl('configerrors'), 'all scenarios keep the same client and a healthy compositor')
finally:
    for child in [locker, pointer, keyboard]:
        if child and child.poll() is None:
            child.terminate()
    if getattr(n, 'log', None):
        n.log.flush()
        (ROOT/'work/session-lock-runtime.log').write_text(Path(n.log.name).read_text(errors='replace'))
    n.stop()

print('ALL PASSED' if not failures else f'{len(failures)} FAILED', flush=True)
raise SystemExit(bool(failures))
