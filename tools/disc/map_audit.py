import base64,struct,json,os,re,sys
import numpy as np
from PIL import Image,ImageDraw
W='/home/claude/xg/v/www/'
s=open(W+'plan.js').read();PLAN={int(k):v for k,v in json.loads(s[s.index('=')+1:].strip().rstrip(';')).items()}
def mesh(f):
    t=open(W+'maps/%d.js'%f).read();m=re.search(r'="([^"]*)"',t)
    if not m: return None
    b=base64.b64decode(m.group(1))
    if len(b)<4: return None
    nv,nt=struct.unpack('<2H',b[:4]);o=4
    V=np.frombuffer(b,dtype='<i2',count=nv*2,offset=o).reshape(nv,2).astype(float);o+=nv*4
    T=[];F=[]
    for i in range(nt):
        a,b_,c,fl=struct.unpack('<3HB',b[o:o+7]);o+=7;T.append((a,b_,c));F.append(fl)
    return V,np.array(T).reshape(-1,3),np.array(F,dtype=int),len(b)-o
rows=[]
for f in range(730):
    r={'f':f};rows.append(r)
    try: m=mesh(f)
    except Exception as e: r['err']=str(e);continue
    if m is None: r['nomesh']=1;continue
    V,T,F,left=m;r.update(nv=len(V),nt=len(T),left=left)
    if len(T)==0: r['empty']=1;continue
    if T.max()>=len(V): r['badidx']=1;continue
    tone=F&3;r['tones']=[int((tone==k).sum()) for k in range(4)]
    # outline flags against the mesh's own boundaries (edges keyed by vertex position)
    key=lambda i:(V[i,0],V[i,1])
    def boundary(sel):
        cnt={}
        for ti in np.nonzero(sel)[0]:
            for k in range(3):
                e=tuple(sorted((key(T[ti,k]),key(T[ti,(k+1)%3]))));cnt[e]=cnt.get(e,0)+1
        return {e for e,c in cnt.items() if c==1}
    fl=set()
    for ti in range(len(T)):
        e=F[ti]>>2
        for k in range(3):
            if e>>k&1: fl.add(tuple(sorted((key(T[ti,k]),key(T[ti,(k+1)%3])))))
    r['outline']=len(fl)
    for nm,sel in (('all',np.ones(len(T),bool)),('walk',tone!=2),('plain',tone==0)):
        B=boundary(sel);r['b_'+nm]=[len(B),len(fl-B),len(B-fl)]
    x0,z0=V[T.ravel()].min(0);x1,z1=V[T.ravel()].max(0);r['bbox']=[x0,z0,x1,z1];span=max(x1-x0,z1-z0,1)
    if f not in PLAN: r['noplan']=1;continue
    cx,cz,w=PLAN[f];im=np.array(Image.open(W+'plan/%d.webp'%f).convert('RGBA'));al=im[...,3]>8;lum=im[...,:3].astype(float).mean(2)
    r['res']=round(512*span/w);r['opaque']=round(float(al.mean()),3)
    def score(fx,fz):
        mk=Image.new('L',(512,512),0);d=ImageDraw.Draw(mk);out=0;tot=0
        for ti in range(len(T)):
            if tone[ti]==2: continue
            p=[]
            for k in range(3):
                x,z=V[T[ti,k]];x=cx+(x-cx)*fx;z=cz+(z-cz)*fz
                p.append((256+(x-cx)/w*512,256+(z-cz)/w*512))
            d.polygon(p,fill=255)
            for q in p:
                tot+=1
                if not(0<=q[0]<512 and 0<=q[1]<512): out+=1
        mk=np.array(mk)>0;n=mk.sum()
        if n==0: return None
        return float((mk&al).sum()/n),float((mk&al&(lum<14)).sum()/n),out/max(tot,1),int(n)
    s0=score(1,1)
    if s0 is None: r['tiny']=1;continue
    r['cover'],r['dark'],r['outside'],r['px']=round(s0[0],3),round(s0[1],3),round(s0[2],3),s0[3]
    fl_=[score(-1,1),score(1,-1),score(-1,-1)];r['flipbest']=round(max(x[0] for x in fl_ if x),3)
json.dump(rows,open('audit.json','w'))
ok=[r for r in rows if 'cover' in r]
print('rooms',len(rows),'with mesh',sum('nt' in r for r in rows),'empty mesh',[r['f'] for r in rows if r.get('empty') or r.get('nomesh')],'errors',[r['f'] for r in rows if 'err' in r or 'badidx' in r],'leftover bytes',[r['f'] for r in rows if r.get('left')])
print('scored',len(ok))
import statistics as st
print('cover median',st.median(r['cover'] for r in ok),'dark median',st.median(r['dark'] for r in ok),'res median',st.median(r['res'] for r in ok))
print('walk area off the picture (>2% of corners):',[(r['f'],r['outside']) for r in ok if r['outside']>0.02])
print('cover < 0.9:',[(r['f'],r['cover']) for r in sorted(ok,key=lambda r:r['cover']) if r['cover']<0.9])
print('flip fits better by >0.05:',[(r['f'],r['cover'],r['flipbest']) for r in ok if r['flipbest']>r['cover']+0.05])
print('dark floor > 0.5:',[(r['f'],r['dark']) for r in sorted(ok,key=lambda r:-r['dark']) if r['dark']>0.5])
print('low detail (<110 px across the walkable area):',[(r['f'],r['res']) for r in sorted(ok,key=lambda r:r['res']) if r['res']<110])
for nm in ('all','walk','plain'):
    ex=sum(1 for r in rows if 'b_'+nm in r and r['b_'+nm][1]==0 and r['b_'+nm][2]==0);print('outline == boundary of',nm,':',ex,'rooms')
bad=[(r['f'],r['outline'],r['b_all'],r['b_walk']) for r in rows if 'outline' in r and min(r['b_all'][1]+r['b_all'][2],r['b_walk'][1]+r['b_walk'][2],r['b_plain'][1]+r['b_plain'][2])>0]
print('outline matches none exactly:',len(bad),bad[:25])
print('no outline edges:',[r['f'] for r in rows if r.get('outline')==0])
