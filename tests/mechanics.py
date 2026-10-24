"""Canvas mechanics through real input and restart persistence, in a child session."""
import importlib.util,json,subprocess,time,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('nested',ROOT/'source/tests/navigator-nested.py')
nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
nav.WINDOWS=[('mechanic-a','A'),('mechanic-b','B')]
state=tempfile.TemporaryDirectory(prefix='hotlilit-memory-')
failures=[]
def make():
 n=nav.Nested(ROOT/'spatialoverview.so',ROOT/'work/mechanics-shots',state=state.name,test_binds=False)
 n.config_source=(ROOT/'tests/nested.lua').read_text().replace('@MODULE@',json.dumps(str(ROOT/'config/canvas.lua'),ensure_ascii=False))
 return n
n=make()
def check(ok,msg):
 print(('PASS ' if ok else 'FAIL ')+msg,flush=True)
 if not ok: failures.append(msg)
def run(expr,wait=.35): n.dispatch(expr);time.sleep(wait)
def mode(a): run('hl.plugin.spatialoverview.mode('+json.dumps(a)+')',.7)
def canvas(a,wait=.35): run('hl.plugin.spatialoverview.canvas('+json.dumps(a)+')',wait)
def camera(): return json.loads(n.ctl('spatialoverview'))['screens'][0]
def client(app): return next(c for c in n.clients() if c['class']==app)
def geom(app):
 c=client(app);return c['at']+c['size']
def pointer(*args): subprocess.run([str(ROOT/'source/.build/vpointer'),'1280','720',*map(str,args)],env=n.env(),check=True,timeout=8)
def drag(*args):
 hold=subprocess.Popen([str(ROOT/'work/tools/keyboard'),'hold-super'],env=n.env(),stdout=subprocess.PIPE,text=True)
 try:
  assert hold.stdout.readline().strip()=='ready'
  pointer(*args)
 finally: hold.wait(timeout=4)
def place(app,x,y,w=250,h=200):
 run(f'hl.dsp.window.resize({{window="class:{app}",x={w},y={h}}})',.3)
 run(f'hl.dsp.window.move({{window="class:{app}",x={x},y={y}}})',.5)
try:
 n.launch();mode('on');canvas('home');place('mechanic-a',100,200);place('mechanic-b',700,200)
 drag('abs',200,300,'down','sleep',40,'rel',335,0,'sleep',220,'up')
 check(abs(client('mechanic-a')['at'][0]-438)<=2,'drag magnet aligns adjacent edges with configured gap')
 # Resize toward the neighbour, keeping the opposite corner fixed.
 place('mechanic-a',100,200);place('mechanic-b',700,200)
 drag('abs',345,395,'rdown','rel',335,0,'sleep',200,'rup')
 check(abs(client('mechanic-a')['size'][0]-588)<=2 and client('mechanic-a')['at']==[100,200], f'resize magnet aligns edges without moving the fixed corner (actual {geom("mechanic-a")})')
 place('mechanic-a',100,450);place('mechanic-b',700,50)
 drag('abs',200,550,'down','sleep',20,'rel',45,0,'sleep',20,'rel',45,0,'sleep',20,'rel',45,0,'up')
 # hold helper waits for modifier release; the throw should have coasted by then.
 check(client('mechanic-a')['at'][0]>280,'a fast window drag continues moving after release')
 canvas('home');before=camera()['view'][0]
 pointer('abs',600,400,'mdown','sleep',20,'rel',-40,0,'sleep',20,'rel',-40,0,'sleep',20,'rel',-40,0,'mup')
 after=camera();time.sleep(.28);coast=camera()
 check(coast['view'][0]>after['view'][0]+20,'camera coasts after a quick pan release')
 canvas('home');time.sleep(.3)
 check(camera()['zoom']==1 and camera()['view'][:2]==[0,0] and not camera()['mechanics']['pan_inertia'],'home cancels inertia and returns to origin at 100%')
 pointer('abs',50,40,'down','rel',50,20,'sleep',180,'up');time.sleep(.3)
 check(camera()['view'][0]<-25,'plain left drag on empty background pans the canvas')
 canvas('home');pointer('abs',50,40,'axis',15);time.sleep(.2)
 check(camera()['zoom']<1,'wheel on empty background zooms without a modifier')
 canvas('home');canvas('spawn-region')
 check(camera()['mechanics']['region_armed'],'spawn-region action arms explicit selection')
 pointer('abs',90,90,'down','rel',360,260,'sleep',150,'up');time.sleep(.2)
 check(camera()['mechanics']['region']==[90.0,90.0,360.0,260.0],'drawn region is expressed in canvas world coordinates')
 run('hl.dsp.exec_cmd("foot --app-id=mechanic-new --title=Region /usr/bin/cat")',.8)
 check(geom('mechanic-new')==[90,90,360,260],'new application occupies the selected region')
 check(camera()['mechanics']['region'] is None,'spawn region is consumed exactly once')
 canvas('spawn-region');subprocess.run([str(ROOT/'work/tools/keyboard'),'escape'],env=n.env(),check=True);time.sleep(.2);check(not camera()['mechanics']['region_armed'],'Escape cancels region selection')
 canvas('zoom out');canvas('pan right',.9);place('mechanic-a',1800,330,320,240)
 localbox=geom('mechanic-a');localcamera=camera();n.shot('01-local-features')
 # Camera-only changes must reach disk without a normal canvas shutdown.
 memory=Path(state.name)/'hotlilit/canvas-memory-v2.txt'
 time.sleep(.8)
 check(memory.exists() and 'camera "workspace:1"' in memory.read_text(), 'camera movement schedules a durable save while the canvas stays open')
 mode('scope');place('mechanic-a',2700,640,340,260);canvas('home');canvas('pan down',.9)
 globalbox=geom('mechanic-a');globalcamera=camera();mode('off')
 memory=Path(state.name)/'hotlilit/canvas-memory-v2.txt'
 text=memory.read_text();check('"workspace:1"' in text and '"global"' in text,'both scopes are persisted independently to disk')
 check(memory.stat().st_mode & 0o777 == 0o600,'saved window titles are private to the user')
 n.stop();n=make();n.launch();mode('on');time.sleep(.8)
 check(geom('mechanic-a')==localbox,'workspace arrangement survives a compositor restart')
 restored=camera();check(restored['zoom']==localcamera['zoom'] and restored['view']==localcamera['view'],'workspace camera and zoom survive a compositor restart')
 mode('scope');time.sleep(.8)
 check(geom('mechanic-a')==globalbox,'global arrangement survives a compositor restart')
 restored=camera();check(restored['zoom']==globalcamera['zoom'] and restored['view']==globalcamera['view'],'global camera and zoom survive a compositor restart')
 n.shot('02-restored-global');mode('off')
 check(all(not c['floating'] for c in n.clients()),'disk restoration does not overwrite native tiling state')
 check(n.proc.poll() is None and not n.ctl('configerrors'),'mechanics and restart scenarios leave a healthy compositor')
finally:
 if getattr(n,'log',None):
  n.log.flush();(ROOT/'work/mechanics-runtime.log').write_text(Path(n.log.name).read_text(errors='replace'))
 n.stop()
print('ALL PASSED' if not failures else f'{len(failures)} FAILED',flush=True)
raise SystemExit(bool(failures))
