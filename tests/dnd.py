"""Real Wayland DnD between transformed GTK windows, isolated from the host."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('nav',ROOT/'source/tests/navigator-nested.py')
nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
nav.WINDOWS=[]
n=nav.Nested(ROOT/'spatialoverview.so',ROOT/'work/dnd-shots',test_binds=False)
n.config_source=(ROOT/'tests/nested.lua').read_text().replace('@MODULE@',json.dumps(str(ROOT/'config/canvas.lua'),ensure_ascii=False))
children=[]; files={}; failures=[]

def check(ok, text):
    print(('PASS ' if ok else 'FAIL ')+text,flush=True)
    if not ok: failures.append(text)

def read(name):
    return (ROOT/'work'/('dnd-'+name+'.log')).read_text(errors='replace')

def point(name):
    c=next(c for c in n.clients() if c['title']=='dnd-'+name)
    camera=json.loads(n.ctl('spatialoverview'))['screens'][0]
    z=camera['zoom']; x,y=camera['view'][:2]
    return (round((c['at'][0]+c['size'][0]/2-x)*z),round((c['at'][1]+c['size'][1]/2-y)*z))

def pointer(*args):
    subprocess.run([str(ROOT/'source/.build/vpointer'),'1280','720',*map(str,args)],env=n.env(),check=True,timeout=15)
    time.sleep(.3)

try:
    n.launch()
    env=n.env();env['GDK_BACKEND']='wayland'
    for name in ['source','target']:
        files[name]=open(ROOT/'work'/('dnd-'+name+'.log'),'w')
        children.append(subprocess.Popen(['python3',str(ROOT/'source/tests/tools/dnd-app.py'),'dnd-'+name],
            env=env,stdout=files[name],stderr=subprocess.STDOUT,start_new_session=True))
        for _ in range(70):
            if 'ready' in read(name): break
            time.sleep(.1)
        else: raise RuntimeError(name+' did not map: '+read(name))
    n.dispatch('hl.plugin.spatialoverview.mode("on")');time.sleep(.7)
    for name,x in [('source',180),('target',680)]:
        selector='title:dnd-'+name
        n.dispatch('hl.dsp.window.resize({window='+json.dumps(selector)+',x=360,y=240})')
        n.dispatch('hl.dsp.window.move({window='+json.dumps(selector)+',x='+str(x)+',y=230})')
    n.dispatch('hl.plugin.spatialoverview.canvas("zoom out")');time.sleep(1.2)
    a,b=point('source'),point('target')
    check(all(10<x<1270 and 10<y<710 for x,y in [a,b]),'both transformed windows are visible')
    print('Drawn centers:',a,b,flush=True)
    commands=['abs',*a,'sleep',200,'down','sleep',150]
    for _ in range(6): commands+=['rel',4,3,'sleep',35]
    commands+=['sleep',250]
    for i in range(1,16):
        commands+=['abs',round(a[0]+(b[0]-a[0])*i/15),round(a[1]+(b[1]-a[1])*i/15),'sleep',35]
    commands+=['sleep',400,'up','sleep',1000]
    pointer(*commands)
    check('drag-begin' in read('source'),'GTK initiated a real wl_data_device drag')
    check('dnd-enter' in read('target') and 'dnd-motion' in read('target'),'transformed drop target receives enter and motion')
    check('drop dnd-payload_dnd-source' in read('target'),'payload drops onto the transformed target')
    check('drag-end' in read('source') and 'drag-cancel' not in read('source'),'drag completes without cancellation')
    before=read('target').count('hover ')
    pointer('abs',*b,'rel',2,0,'sleep',200)
    check(read('target').count('hover ')>before,'ordinary pointer input resumes after the drop')
    n.shot('drop-completed')
    n.dispatch('hl.plugin.spatialoverview.mode("off")');time.sleep(.7)
    check(n.proc.poll() is None,'return to tiling after DnD keeps compositor alive')
finally:
    for child in children:
        if child.poll() is None: child.terminate()
    n.stop()
    for file in files.values(): file.close()
print('ALL PASSED' if not failures else str(len(failures))+' FAILED',flush=True)
raise SystemExit(bool(failures))
