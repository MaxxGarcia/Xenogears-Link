# ==== fld/trim_plan.py ====
# Trims every room picture to the walkable area plus a margin (the way KH 2 Link's map art was trimmed).
# Reads the untrimmed pictures kept in /home/claude/xg/plan_full, writes v/www/plan. Usage: trim_plan.py [margin%] [rooms...]
# Mask = the room's walk-mesh triangles drawn into the picture (PLAN: centre x, centre z, width; x right, z down), blocked
# triangles left out; closed (bites and gaps up to about 28% of the longer side filled), grown by the margin (10% of the
# walkable area's longer side, 11 to 67 pixels) and given a soft edge.
import sys,json,base64,struct,os,re,numpy as np
from PIL import Image,ImageDraw,ImageFilter
W='/home/claude/xg/v/www/'; SRC='/home/claude/xg/plan_full/'
PLAN=json.loads(open(W+'plan.js').read().split('=',1)[1].rstrip().rstrip(';'))
CLOSE=14
def mesh(f):
    p=W+'maps/%d.js'%f
    if not os.path.exists(p): return None
    m=re.search(r'"([A-Za-z0-9+/=]+)"',open(p).read())
    if not m: return None
    b=base64.b64decode(m.group(1)); nv,nt=struct.unpack_from('<HH',b,0)
    v=np.frombuffer(b,'<i2',nv*2,4).reshape(nv,2).astype(np.float64); o=4+nv*4
    t=np.array([struct.unpack_from('<HHHB',b,o+7*i) for i in range(nt)])
    return v,t
def mask(f,size,pct):
    mt=mesh(f)
    if mt is None or not len(mt[1]): return None
    v,t=mt; cx,cz,w=PLAN[str(f)]; S=4; n=size//S*S
    px=((v-[cx,cz])/w+0.5)*size
    im=Image.new('L',(size,size),0); d=ImageDraw.Draw(im)
    walk=[r for r in t if r[3]&3!=2] or list(t)   # triangles marked blocked are left out, unless the room has no others
    for a,b,c,fl in walk: d.polygon([tuple(px[a]),tuple(px[b]),tuple(px[c])],fill=255,outline=255)
    wi=np.unique(np.array(walk)[:,:3]); ext=max(np.ptp(px[wi,0]),np.ptp(px[wi,1])); mg=int(max(11,min(67,ext*pct/100)))
    from scipy import ndimage
    core=np.asarray(im)>0
    # close the shape first: bites and gaps narrower than 2 x R (R = CLOSE% of the longer side) are filled, so furniture, pits and
    # other blocked patches inside a room, and the ground between two walkable parts, stay in the picture
    R=ext*CLOSE/100
    if R>=2:
        pad=int(R)+2; big=np.pad(core,pad)
        grown=ndimage.distance_transform_edt(~big)<=R
        core=core|(ndimage.distance_transform_edt(grown)>R)[pad:-pad,pad:-pad]
    dist=ndimage.distance_transform_edt(~core)          # distance from the kept area, in pixels
    g=Image.fromarray(((dist<=mg)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(2,mg/4)))
    return np.asarray(g).astype(np.float32),mg
def one(f,pct):
    a=Image.open(SRC+'%d.webp'%f).convert('RGBA'); r=mask(f,a.size[0],pct)
    if r is None: return None
    m,mg=r; A0=np.asarray(a.getchannel('A'))>40
    if (A0&(m*1.6>128)).sum()<0.05*max(A0.sum(),1): return a,0   # the mask misses the picture (rooms 478, 246, 101): left untrimmed
    al=np.minimum(np.asarray(a.getchannel('A')).astype(np.float32),np.clip(m*1.6,0,255))
    px=np.asarray(a).copy(); px[...,3]=al.astype(np.uint8); px[al<1,:3]=0
    return Image.fromarray(px,'RGBA'),mg
def job(f,pct):
    r=one(f,pct)
    if r is None: return 0
    dst=W+'plan/%d.webp'%f; r[0].save(dst,'WEBP',quality=75,method=6,alpha_quality=90); return os.path.getsize(dst)
if __name__=='__main__':
    pct=float(sys.argv[1]) if len(sys.argv)>1 else 10
    rooms=[int(x) for x in sys.argv[2:]] or sorted(int(x[:-5]) for x in os.listdir(SRC))
    import multiprocessing as mp
    with mp.Pool(max(1,mp.cpu_count())) as pool: res=pool.starmap(job,[(f,pct) for f in rooms])
    print(len(rooms),'rooms, no mesh:',sum(1 for x in res if not x),'total',sum(res)//1024,'KB')

# ==== fld/reframe.py ====
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

# ==== fld/mktre.py ====
import sys,json,collections
sys.path.insert(0,'/home/claude/xg/fld')
import tre,surv,chest,exits
def actor_pos(f,acts):
    r=tre.vm.load(f); ent=r[2]; out={}
    for own,a,b,o,stt,code in tre.routines(f):
        if own[0] in acts and a==ent[own[0]][0] and own[0] not in out:
            for p,k,arg in surv.ins(o,b,code):
                if k=='19' and len(arg)>=5 and arg[4]&0xC0==0xC0: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
                if k=='1D' and len(arg)>=6: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
                if k=='1B' and len(arg)>=6 and arg[len(arg)-1]&0xC0==0xC0: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
    # no place in the set-up routine: the room's object placement table, then the trigger zone the give sits behind
    E=exits.ents(f); Z=exits.zones(f)
    for a in acts:
        if a not in out and a<len(E) and (E[a][4] or E[a][6]): out[a]=[E[a][4],E[a][6]]
    for own,a,b,o,stt,code in tre.routines(f):
        if own[0] not in acts or own[0] in out: continue
        guards=[]
        for p,k,arg in surv.ins(o,b,code):
            guards=[g for g in guards if g[1]>p]
            if k in exits.ZT and len(arg)>=3: guards.append((arg[0],arg[1]|arg[2]<<8))
            if k in('8C','8F') and guards and guards[-1][0]<len(Z):
                q=Z[guards[-1][0]]; out[own[0]]=[round(sum(c[0] for c in q)/4),round(sum(c[1] for c in q)/4)]; break
    # a place far off the room's walkable area is not trusted (one case: room 318)
    import trim_plan,numpy as np
    m=trim_plan.mesh(f)
    if m is not None:
        v=m[0]; ext=max(np.ptp(v[:,0]),np.ptp(v[:,1]))
        for a in list(out):
            if np.hypot(v[:,0]-out[a][0],v[:,1]-out[a][1]).min()>ext*0.15: del out[a]
    return out
OUT={}; st=collections.Counter()
for f in range(730):
    L=[t for t in chest.room(f) if t['flag']]
    if not L: continue
    pos=actor_pos(f,{t['actor'] for t in L if t['src']=='actor'})
    groups=collections.OrderedDict()
    for t in L:
        key=(tuple(t['flag']),t['src'])
        g=groups.setdefault(key,{'items':[],'gold':0,'pos':None,'src':t['src']})
        if t['k']=='gold': g['gold']+=t['v']
        elif t['v'] not in g['items']: g['items'].append(t['v'])
        if t['pos']: g['pos']=t['pos']
        elif t['src']=='actor' and t.get('actor') in pos: g['pos']=pos[t['actor']]
        g['n']=g.get('n',0)+1
    rows=[]
    for (flag,src),g in groups.items():
        if src=='actor' and g['n']>3: st['dropped: one flag, many gives']+=1; continue
        if src=='chest' and len(g['items'])>1: st['chest with alternatives']+=1
        if any((c>>8)>4 for c in g['items']): st['dropped: bad item code']+=1; continue
        row=[flag[0],flag[1],g['items'],g['gold']]+(g['pos'] if g['pos'] else [])+([1] if src=='actor' and g['pos'] else [])
        rows.append(row); st[src+(' pos' if g['pos'] else ' nopos')]+=1
    if rows: OUT[f]=rows
print(dict(st),'rooms',len(OUT),'entries',sum(len(v) for v in OUT.values()))
js='/* treasure and one-time pickups per room, read off the room scripts on the disc (see "Room scripts" in the RAM map).\n   room -> [flag variable, bit, [item codes], gold, x, z, gift]; item code = inventory x 256 + id (0 items, 1 weapons, 2 equipment, 3 gear weapons, 4 gear parts);\n   taken when bit `bit` of the 16-bit script variable at 0x800C3A68 + variable is set; x, z are missing when the script gives no position;\n   a seventh entry of 1 marks a gift (handed over by a person or an event at that spot, not a chest). */\nwindow.TREASURE='+json.dumps(OUT,separators=(',',':'))+';\n'
open('/home/claude/xg/v/www/treasure.js','w').write(js); print(len(js))
json.dump(OUT,open('treasure.json','w'))

