"""New-window placement, cancellation, queueing and transient dialogs."""
import importlib.util,json,os,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('nested',R/'source/tests/navigator-nested.py');nav=importlib.util.module_from_spec(s);s.loader.exec_module(nav)
nav.WINDOWS=[('place-anchor','Anchor')]
n=nav.Nested(R/'spatialoverview.so',R/'work/placement-shots',test_binds=False,extra_lua='hl.config({plugin={spatialoverview={canvas={spawn_on_open=true}}}})')
n.config_source=(R/'tests/nested.lua').read_text().replace('@MODULE@',json.dumps(str(R/'config/canvas.lua'),ensure_ascii=False))
fail=[];children=[]
def check(ok,msg):
 print(('PASS ' if ok else 'FAIL ')+msg,flush=True)
 if not ok:fail.append(msg)
def dispatch(expr):n.dispatch(expr);time.sleep(.6)
def mode(a):dispatch('hl.plugin.spatialoverview.mode('+json.dumps(a)+')')
def state():return json.loads(n.ctl('spatialoverview'))['screens'][0]['mechanics']
def app(app):return next(c for c in n.clients() if c['class']==app)
def pointer(*a):subprocess.run([str(R/'source/.build/vpointer'),'1280','720',*map(str,a)],env=n.env(),check=True,timeout=8);time.sleep(.3)
def keys(a):subprocess.run([str(R/'work/tools/keyboard'),a],env=n.env(),check=True,timeout=8);time.sleep(.3)
def draw(x,y,w,h):pointer('abs',x,y,'down','rel',w,h,'sleep',150,'up')
try:
 n.launch();mode('on');dispatch('hl.plugin.spatialoverview.canvas("home")')
 check(state()['pending_windows']==0,'existing windows are freely arranged without placement prompts')
 dispatch('hl.dsp.exec_cmd("foot --app-id=place-a --title=A /usr/bin/cat")')
 check(state()['pending_windows']==1 and state()['region_armed'],'a new application waits for a drawn area')
 dispatch('hl.dsp.exec_cmd("foot --app-id=place-b --title=B /usr/bin/cat")')
 check(state()['pending_windows']==2,'simultaneous new windows form an ordered placement queue')
 draw(90,90,400,260)
 check(app('place-a')['at']==[90,90] and app('place-a')['size']==[400,260],'first region places the first waiting window exactly')
 check(state()['pending_windows']==1 and state()['region_armed'],'next waiting window receives its own placement prompt')
 keys('escape');check(state()['pending_windows']==0 and not state()['region_armed'],'Escape automatically places one waiting window and releases the prompt')
 for name in ['place-c','place-d']:
  dispatch('hl.dsp.exec_cmd("foot --app-id='+name+' --title='+name+' /usr/bin/cat")')
 gesture=subprocess.Popen([str(R/'source/.build/vpointer'),'1280','720','abs','100','80','down','rel','220','140','sleep','1400','up'],env=n.env())
 time.sleep(.35);keys('escape');gesture.wait(timeout=5);time.sleep(.25)
 check(state()['pending_windows']==1 and state()['region_armed'],'Escape during a held drag places only the first queued window; its release cannot place the next')
 keys('escape');check(state()['pending_windows']==0 and not state()['region_armed'],'a second Escape places the next queued window independently')
 dispatch('hl.dsp.exec_cmd("foot --app-id=place-close --title=Close /usr/bin/cat")')
 dispatch('hl.dsp.window.close({window="class:place-close"})')
 check(state()['pending_windows']==0 and not state()['region_armed'],'closing a waiting application clears its pending region')
 trigger=R/'work/open-placement-dialog';trigger.unlink(missing_ok=True)
 env=n.env();env['GDK_BACKEND']='wayland'
 children.append(subprocess.Popen(['python3',str(R/'tests/placement-client.py'),str(trigger)],env=env))
 time.sleep(1);check(state()['pending_windows']==1,'a GTK parent waits for its initial region')
 trigger.touch();time.sleep(1)
 check(state()['pending_windows']==1,'a dialog opened before its parent is placed does not add another region prompt')
 draw(650,180,480,320)
 check(state()['pending_windows']==0,'placing the parent also reveals its waiting transient dialog')
 parent=next(c for c in n.clients() if c['title']=='placement-parent');dialog=next(c for c in n.clients() if c['title']=='placement-dialog')
 centre=lambda c:(c['at'][0]+c['size'][0]/2,c['at'][1]+c['size'][1]/2)
 check(all(abs(a-b)<=2 for a,b in zip(centre(parent),centre(dialog))),'dialog is centred on its parent in canvas coordinates')
 dispatch('hl.dsp.window.close({window="title:placement-dialog"})');trigger.touch();time.sleep(.7)
 check(state()['pending_windows']==0,'a later dialog on an already placed parent also bypasses region selection')
 dialog=next(c for c in n.clients() if c['title']=='placement-dialog')
 check(all(abs(a-b)<=2 for a,b in zip(centre(parent),centre(dialog))),'a later dialog is also centred on its parent')
 n.shot('placement-complete')
 dispatch('hl.dsp.exec_cmd("foot --app-id=place-exit --title=Exit /usr/bin/cat")');mode('off')
 check(not json.loads(n.ctl('spatialoverview'))['screens'],'return to tiling while a region is pending succeeds')
 check(not app('place-exit')['floating'],'a still-waiting application returns to normal native tiling')
 check(n.proc.poll() is None and not n.ctl('configerrors'),'placement scenarios leave a healthy compositor')
finally:
 for child in children:
  if child.poll() is None:child.terminate()
 n.stop()
print('ALL PASSED' if not fail else f'{len(fail)} FAILED',flush=True)
raise SystemExit(bool(fail))
