"""Install into a plain Lua Hyprland session and preserve its existing binds."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('nested',ROOT/'source/tests/navigator-nested.py')
nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
nav.WINDOWS=[('plain-a','Plain A'),('plain-b','Plain B')]
n=nav.Nested(ROOT/'spatialoverview.so',ROOT/'work/standalone-shots',test_binds=False)
cfg=(ROOT/'tests/nested.lua').read_text()
a=cfg.index('hl.plugin.load("@PLUGIN@")');b=cfg.index('-- Lifecycle fixtures')
cfg=cfg[:a]+'''-- An ordinary user config, without Serpantinum or a preloaded plugin.
hl.bind("SUPER + G", function() end, {description="User G"})
hl.bind("SUPER + Left", hl.dsp.focus({direction="left"}), {description="User Left"})
hl.bind("SUPER + J", function() end, {description="User J"})
hl.bind("SUPER + SHIFT + F", function() end, {description="User Float"})
'''+cfg[cfg.index('hl.permission',b):]
n.config_source=cfg
failures=[]
def check(ok,message):
 print(('PASS ' if ok else 'FAIL ')+message,flush=True)
 if not ok:failures.append(message)
def state():return json.loads(n.ctl('spatialoverview'))
def action(name,arg):n.dispatch('hl.plugin.spatialoverview.'+name+'('+json.dumps(arg)+')');time.sleep(.7)
def key(k):subprocess.run([str(ROOT/'work/tools/keyboard'),k],env=n.env(),check=True,timeout=8);time.sleep(.3)
def install(*args):
 return subprocess.run([sys.executable,str(ROOT/'install.py'),*args,'--config',str(config),'--target',str(target)],env=n.env(),capture_output=True,text=True,timeout=15)
def user_binds():
 return [(b.get('modmask'),b.get('key'),b.get('description')) for b in json.loads(n.ctl('-j','binds')) if b.get('description','').startswith('User ')]
try:
 n.launch();config=Path(n.tmp.name)/'nested.lua';target=Path(n.tmp.name)/'generic-install'
 original=config.read_text();before=user_binds();before_count=len(json.loads(n.ctl('-j','binds')))
 check(len(before)==4 and not json.loads(n.ctl('-j','plugin','list')),'plain fixture has four user binds and no plugin')
 result=install('--enable');check(result.returncode==0,'installer connects the generic module to a real Lua compositor')
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 n.ctl('reload');time.sleep(1)
 check(not n.ctl('configerrors'),'generic module loads with no Serpantinum imports or config errors')
 check(user_binds()==before,'existing G, arrow, J and floating user bindings remain identical')
 binds=json.loads(n.ctl('-j','binds'))
 check(len(binds)==before_count and not any(b.get('description','').startswith('Canvas:') or b.get('description')=='Tiling / canvas' for b in binds),'default installation adds no HotLilith keyboard bindings')
 check('bindings.example.lua' not in config.read_text(),'optional binding example is not included by the installer')
 key('super+g');check(not state()['screens'],'a pre-existing user chord does not become a canvas toggle')
 action('mode','on');check(bool(state()['screens']) and all(w['floating'] for w in n.clients()),'canvas works through its public dispatcher without a desktop preset')
 action('canvas','zoom out');check(state()['screens'][0]['zoom']<1,'plain session renders a scaled canvas')
 n.dispatch('hl.dsp.exec_cmd("foot --app-id=plain-new --title=Plain-new /usr/bin/cat")');time.sleep(.8)
 check(state()['screens'][0]['mechanics']['pending_windows']==1,'a new plain-session window waits for its own region')
 key('escape');check(state()['screens'][0]['mechanics']['pending_windows']==0,'Escape auto-placement works without optional hotkeys')
 n.shot('standalone')
 n.dispatch('hl.dsp.focus({workspace="2"})');time.sleep(.8)
 check(not state()['screens'],'workspace lifecycle closes the local canvas without private preset helpers')
 n.dispatch('hl.dsp.focus({workspace="1"})');time.sleep(.3)
 action('mode','on')
 action('mode','off');check(not state()['screens'] and all(not w['floating'] for w in n.clients()),'plain-session windows return to native tiling')
 action('mode','on');result=install('--remove')
 loaded=any(p.get('name')=='spatialoverview' for p in json.loads(n.ctl('-j','plugin','list')))
 check(result.returncode==0 and (not loaded or not state()['screens']),'generic uninstall verifies and closes a live canvas')
 check(config.read_text()==original,'generic uninstall restores the original user config exactly')
 n.ctl('reload');time.sleep(.8)
 check(user_binds()==before and not n.ctl('configerrors'),'user bindings survive disconnect and reload')
finally:
 n.stop()
print('ALL PASSED' if not failures else f'{len(failures)} FAILED',flush=True)
raise SystemExit(bool(failures))
