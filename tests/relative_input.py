"""Locked/confined game input at several zooms, through native SDL2 protocols."""
import importlib.util,json,os,shlex,subprocess,time,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('nested',R/'source/tests/navigator-nested.py');nav=importlib.util.module_from_spec(s);s.loader.exec_module(nav)
nav.WINDOWS=[]
backend=sys.argv[1] if len(sys.argv)>1 else 'wayland'
n=nav.Nested(R/'spatialoverview.so',R/'work/relative-shots',test_binds=False)
n.config_source=(R/'tests/nested.lua').read_text().replace('@MODULE@',json.dumps(str(R/'config/canvas.lua'),ensure_ascii=False))
log=R/'work'/('relative-'+backend+'.log');fail=[];anchor=None;keyboard_anchor=None
def check(ok,msg):
 print(('PASS ' if ok else 'FAIL ')+msg,flush=True)
 if not ok:fail.append(msg)
def dispatch(expr):n.dispatch(expr);time.sleep(.5)
def canvas(a):dispatch('hl.plugin.spatialoverview.canvas('+json.dumps(a)+')')
def pointer(*a):
 anchor.stdin.write(' '.join(map(str,a))+'\n');anchor.stdin.flush()
 assert anchor.stdout.readline().strip()=='done'
 time.sleep(.15)
def key(a):subprocess.run([str(R/'work/tools/keyboard'),a],env=n.env(),check=True,timeout=8);time.sleep(.25)
def data():return log.read_text(errors='replace') if log.exists() else ''
def motion(text):
 rows=[line.split() for line in text.splitlines() if line.startswith('motion 1 ')]
 return sum(int(r[2]) for r in rows),sum(int(r[3]) for r in rows)
def move():
 before=len(data());pointer('rel',20,10,'sleep',25,'rel',20,10,'sleep',25,'rel',20,10,'sleep',25,'rel',20,10)
 return motion(data()[before:])
try:
 n.launch()
 # Keep seat pointer capability stable between independently scripted moves.
 # A real desktop keeps its physical mouse; a headless child has none.
 anchor=subprocess.Popen([str(R/'source/.build/vpointer'),'1280','720','stdin'],env=n.env(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
 assert anchor.stdout.readline().strip()=='ready'
 keyboard_anchor=subprocess.Popen([str(R/'work/tools/keyboard'),'hold-seat'],env=n.env(),stdout=subprocess.DEVNULL)
 time.sleep(.2)
 dispatch('hl.plugin.spatialoverview.mode("on")')
 cmd=shlex.join(['env','SDL_VIDEODRIVER='+backend,str(R/'work/tools/relative-client')])+' > '+shlex.quote(str(log))+' 2>&1'
 dispatch('hl.dsp.exec_cmd('+json.dumps(cmd,ensure_ascii=False)+')');time.sleep(.8)
 check('ready '+backend in data(),'SDL2 client uses the requested '+backend+' protocol path')
 selector='title:hotlilit-relative'
 dispatch('hl.dsp.window.resize({window='+json.dumps(selector)+',x=720,y=400})')
 dispatch('hl.dsp.window.move({window='+json.dumps(selector)+',x=200,y=160})')
 canvas('home');dispatch('hl.dsp.focus({window='+json.dumps(selector)+'})');pointer('abs',560,360,'down','up');key('c')
 check('relative 1 result 0' in data(),'game requests relative capture successfully')
 one=move();check(one==(80,40),f'100% zoom delivers the original device deltas exactly: {one}')
 canvas('zoom out');canvas('zoom out');canvas('zoom out')
 zoom=json.loads(n.ctl('spatialoverview'))['screens'][0]['zoom'];small=move()
 check(zoom<.6 and small==one,f'zoom {zoom} preserves game camera sensitivity: {small}')
 before=len(data());pointer('down','sleep',80,'up');clicked=data()[before:]
 check('button 1 1' in clicked and 'button 1 0' in clicked and motion(clicked)==(0,0),
       'clicking during capture delivers both button events without rotating the camera')
 pointer('rel',2000,1000,'sleep',100,'rel',-2000,-1000)
 pos=json.loads(n.ctl('-j','cursorpos'));check(100<pos['x']<1180 and 70<pos['y']<650,f'locked pointer stays in the projected game window rather than reaching a screen edge: {pos}')
 held=subprocess.Popen([str(R/'work/tools/keyboard'),'hold-super'],env=n.env(),stdout=subprocess.PIPE,text=True)
 try:
  assert held.stdout.readline().strip()=='ready'
  before=len(data());pointer('rel',40,20);suppressed=motion(data()[before:])
 finally:held.wait(timeout=4)
 check(suppressed==(0,0),'canvas modifier gestures do not rotate the game camera')
 n.shot('relative-'+backend+'-zoomed')
 key('super+ctrl+escape');pointer('rel',2000,1000)
 pos=json.loads(n.ctl('-j','cursorpos'));check(pos['x']>=1200 or pos['y']>=680,'universal pointer-release shortcut lets the cursor leave the game')
 # Toggle mode off/on, then click: a released persistent lock may be reacquired.
 key('c');canvas('home');pointer('abs',560,360,'down','up');key('c')
 resumed=move();check(resumed==one,'clicking the game and enabling capture again resumes camera input')
 key('c');canvas('zoom out');key('g')
 pointer('rel',2000,1000)
 pos=json.loads(n.ctl('-j','cursorpos'));view=json.loads(n.ctl('spatialoverview'))['screens'][0]
 window=next(c for c in n.clients() if c['title']=='hotlilit-relative')
 x=(window['at'][0]-view['view'][0])*view['zoom'];y=(window['at'][1]-view['view'][1])*view['zoom']
 w=window['size'][0]*view['zoom'];h=window['size'][1]*view['zoom']
 check(x-2<=pos['x']<=x+w+2 and y-2<=pos['y']<=y+h+2, f'confined visible cursor stays in the projected window region: {pos}, bounds {(x,y,w,h)}')
 key('g')
 key('super+ctrl+p');pointer('rel',2000,1000)
 pos=json.loads(n.ctl('-j','cursorpos'));view=json.loads(n.ctl('spatialoverview'))['screens'][0]
 check(view['mechanics']['captured_pointer'] and x-2<=pos['x']<=x+w+2 and y-2<=pos['y']<=y+h+2,
       'manual legacy capture shortcut holds the pointer without an application lock request')
 key('super+ctrl+escape');pointer('rel',2000,1000)
 check(not json.loads(n.ctl('spatialoverview'))['screens'][0]['mechanics']['captured_pointer'],
       'universal release also clears manual legacy capture')
 canvas('home');pointer('abs',560,360,'down','up');key('c')
 canvas('zoom out');time.sleep(.8)
 before_fullscreen=json.loads(n.ctl('spatialoverview'))['screens'][0]
 dispatch('hl.dsp.window.fullscreen({window='+json.dumps(selector)+',mode="fullscreen",action="set"})')
 state=json.loads(n.ctl('spatialoverview'));check(bool(state['fullscreen']) and not state['screens'],'captured game can enter native fullscreen')
 dispatch('hl.dsp.window.fullscreen({window='+json.dumps(selector)+',mode="fullscreen",action="unset"})')
 returned=json.loads(n.ctl('spatialoverview'))['screens']
 check(bool(returned) and returned[0]['zoom']==before_fullscreen['zoom'] and returned[0]['view']==before_fullscreen['view'],
       f'leaving fullscreen restores the exact canvas camera and zoom while the game lives: before {(before_fullscreen["zoom"],before_fullscreen["view"])}, after {[(r["zoom"],r["view"]) for r in returned]}')
 dispatch('hl.plugin.spatialoverview.mode("off")')
 check(n.proc.poll() is None and not n.ctl('configerrors'),'relative input and mode transitions leave a healthy compositor')
finally:
 if anchor and anchor.poll() is None:anchor.terminate()
 if keyboard_anchor and keyboard_anchor.poll() is None:keyboard_anchor.terminate()
 if n.sig:
  try:
   runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/1000'))/'hypr'/n.sig/'hyprland.log'
   (R/'work'/('relative-runtime-'+backend+'.log')).write_text(runtime.read_text(errors='replace'))
  except OSError:pass
 n.stop()
print('ALL PASSED' if not fail else f'{len(fail)} FAILED',flush=True)
raise SystemExit(bool(fail))
