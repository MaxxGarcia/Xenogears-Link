# Re-renders the rooms whose walkable area is small in the picture (under MINPX of 512), framed on the walkable area x K,
# then the pictures are trimmed again by trim_plan.py. Old masters are kept in master_wide, old pictures in plan_wide2.
import sys,json,os,shutil,numpy as np
sys.path.insert(0,'/home/claude/xg/tools')
import trim_plan as T, rt, export
MINPX=200; K=1.5
def wbox(f):
    v,t=T.mesh(f); w=t[(t[:,3]&3)!=2]
    if not len(w): w=t
    p=v[np.unique(w[:,:3])]; return p[:,0].min(),p[:,1].min(),p[:,0].max(),p[:,1].max()
def one(f):
    x0,z0,x1,z1=wbox(f); cx0,cz0,s0=T.PLAN[str(f)]; s=max(x1-x0,z1-z0)*K
    if max(x1-x0,z1-z0)/s0*512>=MINPX or s>=s0*0.8 or s<=0: return None
    new=[round((x0+x1)/2,1),round((z0+z1)/2,1),round(s,1)]; rt.PLAN[str(f)]=new
    im=rt.room(f,1024)
    if im is None: rt.PLAN[str(f)]=[cx0,cz0,s0]; return None
    os.makedirs('master_wide',exist_ok=True)
    if not os.path.exists('master_wide/%d.png'%f): shutil.copy('master/%d.png'%f,'master_wide/%d.png'%f)
    im.save('master/%d.png'%f); out=export.load(f)[0]
    if out is None: shutil.copy('master_wide/%d.png'%f,'master/%d.png'%f); return None
    os.makedirs('/home/claude/xg/plan_wide2',exist_ok=True)
    if not os.path.exists('/home/claude/xg/plan_wide2/%d.webp'%f): shutil.copy(T.SRC+'%d.webp'%f,'/home/claude/xg/plan_wide2/%d.webp'%f)
    out.save(T.SRC+'%d.webp'%f,'WEBP',quality=80,method=6,alpha_quality=90)
    return new
if __name__=='__main__':
    rooms=[int(x) for x in sys.argv[1:]] or sorted(int(x[:-5]) for x in os.listdir(T.SRC))
    P=dict(T.PLAN); done={}
    for f in rooms:
        try: n=one(f)
        except Exception as e: print(f,'ERR',repr(e)[:100]); n=None
        if n: done[f]=n; P[str(f)]=n; print(f,n,flush=True)
    if done:
        p=T.W+'plan.js'
        if not os.path.exists('/home/claude/xg/plan_wide2/plan.js.before'): shutil.copy(p,'/home/claude/xg/plan_wide2/plan.js.before')
        head=open(p).read().split('=',1)[0]; open(p,'w').write(head+'='+json.dumps(P,separators=(',',':'))+';\n')
    print('reframed',len(done),sorted(done))
