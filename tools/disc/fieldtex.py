# fm.py — field room models and textures
import sys;sys.path.insert(0,'/home/claude/xg/tools')
import xg,struct,math,collections
import numpy as np
T=xg.table()
def vram(f):
    t=xg.getfile(607+2*f,T); V=np.zeros((512,1024),np.uint16); p=0; blocks=[]
    while t and p+0x1C<=len(t):
        typ,_,x,y,mx,my,w,h,one,cnt=struct.unpack_from('<10H',t,p)
        if typ not in(0x1200,0x1201) or cnt==0 or cnt>600: break
        hs=struct.unpack_from('<%dH'%cnt,t,p+0x1C); q=p+0x800; X=x+mx; Y=y+my
        blocks.append((typ,X,Y,w,sum(hs)))
        for hh in hs:
            if hh and q+w*hh*2<=len(t) and X+w<=1024:
                rows=np.frombuffer(t[q:q+w*hh*2],'<u2').reshape(hh,w); r=min(hh,512-Y)
                if r>0: V[Y:Y+r,X:X+w]=rows[:r]
            Y+=hh; q+=0x800
        p=q
    return V,blocks
def models(f):
    """model id -> list of parts (vertices Nx3, groups [(type,[4 idx])], stream bytes)"""
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154])
    if not (o[2]<o[3]<=len(h)): return {}
    md=xg.lzss(h[o[2]:o[3]]); n=struct.unpack('<I',md[:4])[0]
    if not 1<=n<=4000: return {}
    offs=list(struct.unpack('<%dI'%n,md[4:4+4*n]))+[len(md)]; out={}
    for i in range(n):
        m=md[offs[i]:offs[i+1]]
        if len(m)<0x3C: continue
        np_=struct.unpack_from('<I',m,0)[0]
        if not 1<=np_<=64 or 4+0x38*np_>len(m): continue
        parts=[]
        for k in range(np_):
            hh=4+0x38*k
            nv,nf,ng=struct.unpack_from('<3H',m,hh+0x0E); vo,no,fo,eo=struct.unpack_from('<4I',m,hh+0x14)
            if nv==0 or not(vo<=fo<=eo<=len(m)) or vo+nv*8>len(m): continue
            V=np.frombuffer(m[vo:vo+nv*8],'<i2').reshape(nv,4)[:,:3].astype(float)
            groups=[];p=fo;ok=True
            for g in range(ng):
                if p+4>eo: ok=False;break
                typ,cnt=struct.unpack_from('<HH',m,p); p+=4
                if p+cnt*8>eo: ok=False;break
                groups.append((typ&0xFF,[struct.unpack_from('<4H',m,p+8*c) for c in range(cnt)])); p+=cnt*8
            if ok: parts.append([V,groups,eo])
        ends=sorted(set(x[2] for x in parts))+[len(m)]
        out[i]=[(V,g,m[eo:ends[ends.index(eo)+1]]) for V,g,eo in parts]
    return out
def polys(groups,st):
    p=0;tp=0;cl=0;out=[];fi=0
    for typ,faces in groups:
        quad=bool(typ&8);tex=bool(typ&1)
        for f in faces:
            while p+4<=len(st) and st[p+3]>=0x80:
                w=struct.unpack_from('<I',st,p)[0]
                if w>>24==0xC4: tp=w&0xFFFF
                elif w>>24==0xC8: cl=w&0xFFFF
                p+=4
            need=(12 if quad else 8) if tex else 4
            if p+need>len(st): return out,fi,p
            if tex:
                if quad:
                    b=st[p+4:p+12]; uv=[(b[0],b[1]),(b[2],b[3]),(b[4],b[5]),(b[6],b[7])]; c=st[p+3]
                else:
                    b=st[p:p+8]; uv=[(b[4],b[5]),(b[6],b[7]),(b[0],b[1])]; c=st[p+3]
                out.append((f[:4 if quad else 3],'t',(uv,tp,cl,c)))
            else:
                out.append((f[:4 if quad else 3],'c',(struct.unpack_from('<I',st,p)[0]&0xFFFFFF,tp,st[p+3])))
            p+=need;fi+=1
    return out,fi,p
def entities(f):
    h=xg.getfile(606+2*f,T); ne=struct.unpack('<I',h[0x18C:0x190])[0]
    return [struct.unpack('<8h',h[0x190+16*i:0x190+16*i+16]) for i in range(min(ne,2000))]
if __name__=='__main__':
    for f in map(int,sys.argv[1:]):
        V,bl=vram(f); M=models(f); c=collections.Counter(); types=collections.Counter()
        for i,parts in M.items():
            for Vt,g,st in parts:
                pl,fi,p=polys(g,st); c['faces']+=sum(len(x) for _,x in g); c['parsed']+=fi; c['left']+=len(st)-p
                for t,x in g: types[t]+=len(x)
        print(f,len(bl),'blocks',dict(c),dict(types),'vram nonzero',int((V!=0).sum()))

# rt.py — textured top-down room render
import sys,json,math,struct
sys.path.insert(0,'/home/claude/xg/tools')
import numpy as np, xg, fm
from PIL import Image
PLAN=json.loads(open('/home/claude/xg/v/www/plan.js').read().split('=',1)[1].rstrip().rstrip(';'))
def walk(f):
    h=xg.getfile(606+2*f,fm.T); o=struct.unpack('<9I',h[0x130:0x154]); w=xg.lzss(h[o[1]:o[2]])
    n=struct.unpack_from('<I',w,0)[0]; sz=struct.unpack_from('<4I',w,4); to,vo=struct.unpack_from('<2I',w,0x18)
    tr=np.frombuffer(w[to:to+sz[0]//14*14],'<u2').reshape(-1,7)[:,:3]
    nv=int(tr.max())+1
    return np.frombuffer(w[vo:vo+nv*8],'<i2').reshape(nv,4)[:,:3].astype(float)
def walktris(f):
    h=xg.getfile(606+2*f,fm.T); o=struct.unpack('<9I',h[0x130:0x154]); w=xg.lzss(h[o[1]:o[2]])
    sz=struct.unpack_from('<4I',w,4); to,vo=struct.unpack_from('<2I',w,0x18)
    tr=np.frombuffer(w[to:to+sz[0]//14*14],'<u2').reshape(-1,7)[:,:3].astype(int)
    return tr
def floormap(f,W,cx,cz,sc,grow=1e9):
    """height of the walkable floor under each pixel (topmost level), 1e9 where there is none"""
    V=walk(f); T_=walktris(f); fl=np.full((W,W),1e9,np.float32)
    for t in T_:
        p=V[t]; x=W/2+(p[:,0]-cx)*sc; y=W/2+(p[:,2]-cz)*sc; z=p[:,1]
        x0=max(int(x.min())-1,0);x1=min(int(x.max())+1,W-1);y0=max(int(y.min())-1,0);y1=min(int(y.max())+1,W-1)
        if x1<x0 or y1<y0: continue
        den=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
        if abs(den)<1e-6: continue
        gx,gy=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
        a=((y[1]-y[2])*(gx-x[2])+(x[2]-x[1])*(gy-y[2]))/den; b=((y[2]-y[0])*(gx-x[2])+(x[0]-x[2])*(gy-y[2]))/den; c=1-a-b
        e=0.5/max(abs(den)**0.5,1)
        m=(a>=-e)&(b>=-e)&(c>=-e); zz=a*z[0]+b*z[1]+c*z[2]; sub=fl[y0:y1+1,x0:x1+1]; m&=zz<sub; sub[m]=zz[m]
    if grow:
        from scipy import ndimage
        have=fl<1e8
        if have.any():
            d,ix=ndimage.distance_transform_edt(~have,return_indices=True)
            near=fl[ix[0],ix[1]]; fl=np.where(d<=grow,near,fl)
    return fl
def placed(f):
    M=fm.models(f); out=[]
    for fl,rx,ry,rz,px,py,pz,mid in fm.entities(f):
        if fl&0x40 or mid not in M: continue
        a=ry*math.pi/2048; c,s_=math.cos(a),math.sin(a)
        ax=rx*math.pi/2048; cx,sx=math.cos(ax),math.sin(ax)
        az=rz*math.pi/2048; cz,sz=math.cos(az),math.sin(az)
        obj=[]
        for V,groups,st in M[mid]:
            x,y,z=V[:,0],V[:,1],V[:,2]
            y,z=y*cx-z*sx,y*sx+z*cx
            x,z=x*c+z*s_,-x*s_+z*c
            x,y=x*cz-y*sz,x*sz+y*cz
            obj.append((np.stack([x+px,y+py,z+pz],1),fm.polys(groups,st)[0]))
        out.append(obj)
    return out
def room(f,W=1024,**k):
    im,cov=room1(f,W,**k)
    if im is not None and cov>0.5: im,_=room1(f,W,cut='all',**k)
    return im
def room1(f,W=1024,clip_above=1500,semi=True,shade=0.35,head=130,cut='down'):
    if str(f) not in PLAN: return None,0
    cx,cz,s=PLAN[str(f)]; sc=W/s
    wv=walk(f); top=wv[:,1].min()-clip_above
    wx0,wx1,wz0,wz1=wv[:,0].min(),wv[:,0].max(),wv[:,2].min(),wv[:,2].max(); wh=wv[:,1].max()-wv[:,1].min()
    VR,_=fm.vram(f); seen=np.zeros((W,W),bool)
    FL0=floormap(f,W,cx,cz,sc,0); FL=floormap(f,W,cx,cz,sc)-head
    zb=np.full((W,W),1e9,np.float32); col=np.zeros((W,W,3),np.float32)
    tris=[]
    for obj in placed(f):
        allv=np.concatenate([P for P,_ in obj])
        if allv[:,0].min()<wx0-400 and allv[:,0].max()>wx1+400 and allv[:,2].min()<wz0-400 and allv[:,2].max()>wz1+400 and (allv[:,1].max()-allv[:,1].min())>2.5*wh: continue
        for P,pl in obj:
            for idx,kind,data in pl:
                if max(idx)>=len(P): continue
                for tr in ([(0,1,2),(1,3,2)] if len(idx)==4 else [(0,1,2)]):
                    p=P[[idx[j] for j in tr]]
                    if p[:,1].mean()<top: continue
                    if kind=='t': uv,tp,cl,cmd=data; d=([uv[j] for j in tr],tp,cl)
                    else:
                        c0,tp,cmd=data; d=c0
                        if (c0&255)+((c0>>8)&255)+((c0>>16)&255)<30 and not cmd&2: continue   # black filler planes carry nothing and hide the floor
                    tris.append((bool(cmd&2) and semi,p,kind,d,(tp>>5)&3))
    order=[t for t in tris if not t[0]]+sorted([t for t in tris if t[0]],key=lambda t:-t[1][:,1].mean())
    for sm,p,kind,data,abr in order:
        x=W/2+(p[:,0]-cx)*sc; y=W/2+(p[:,2]-cz)*sc; z=p[:,1]
        x0=max(int(x.min()),0);x1=min(int(x.max())+1,W-1);y0=max(int(y.min()),0);y1=min(int(y.max())+1,W-1)
        if x1<x0 or y1<y0: continue
        den=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
        if abs(den)<1e-6: continue
        gx,gy=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
        a=((y[1]-y[2])*(gx-x[2])+(x[2]-x[1])*(gy-y[2]))/den
        b=((y[2]-y[0])*(gx-x[2])+(x[0]-x[2])*(gy-y[2]))/den
        c=1-a-b
        m=(a>=0)&(b>=0)&(c>=0)
        if not m.any(): continue
        zz=a*z[0]+b*z[1]+c*z[2]
        sub=zb[y0:y1+1,x0:x1+1]; m&=(zz<sub+12) if sm else (zz<sub)
        nrm=np.cross(p[1]-p[0],p[2]-p[0])
        if nrm[1]<0 or cut=='all':
            fl=FL[y0:y1+1,x0:x1+1]; m&=(fl>1e8)|(zz>=fl)   # undersides above head height are ceilings: seen from above they only hide the room
        if not m.any(): continue
        n=np.cross(p[1]-p[0],p[2]-p[0]); l=np.linalg.norm(n) or 1; up=abs(n[1])/l
        sh=1.0 if sm else (1-shade)+shade*up
        stp=None
        if kind=='t':
            uv,tp,cl=data
            uu=np.clip(np.floor(a*uv[0][0]+b*uv[1][0]+c*uv[2][0]+0.5),0,255).astype(int)
            vv=np.clip(np.floor(a*uv[0][1]+b*uv[1][1]+c*uv[2][1]+0.5),0,255).astype(int)
            bx=(tp&0xF)*64;by=((tp>>4)&1)*256;mode=(tp>>7)&3;qx=(cl&0x3F)*16;qy=(cl>>6)&0x1FF
            if mode==0:
                wd=VR[(by+vv)&511,(bx+(uu>>2))&1023];ix=(wd>>((uu&3)*4))&15;px=VR[qy,(qx+ix)&1023]
            elif mode==1:
                wd=VR[(by+vv)&511,(bx+(uu>>1))&1023];ix=(wd>>((uu&1)*8))&255;px=VR[qy,(qx+ix)&1023]
            else: px=VR[(by+vv)&511,(bx+uu)&1023]
            m&=px!=0
            if not m.any(): continue
            rgb=np.stack([(px&31),(px>>5)&31,(px>>10)&31],-1).astype(np.float32)*(255/31)
            stp=(px&0x8000)!=0
        else:
            rgb=np.empty(a.shape+(3,),np.float32); rgb[...,0]=data&255; rgb[...,1]=(data>>8)&255; rgb[...,2]=(data>>16)&255
        dst=col[y0:y1+1,x0:x1+1]
        if not sm:
            sub[m]=zz[m]; dst[m]=(rgb*sh)[m]
        else:
            bl=m if stp is None else (m&stp); op=None if stp is None else (m&~stp)
            if abr==0: v=(dst+rgb)/2
            elif abr==1: v=dst+rgb
            elif abr==2: v=dst-rgb
            else: v=dst+rgb/4
            dst[bl]=np.clip(v,0,255)[bl]
            if op is not None and op.any(): dst[op]=rgb[op]
            seen[y0:y1+1,x0:x1+1][m&(sub>1e8)]=True
    valid=(zb<1e8)|(seen&(col.sum(-1)>24))
    out=np.zeros((W,W,4),np.uint8); out[...,:3]=np.clip(col,0,255); out[...,3]=np.where(valid,255,0)
    foot=FL0<1e8; cov=float(((zb<FL0-2*head)&foot).sum())/max(int(foot.sum()),1)
    return Image.fromarray(out,'RGBA'),cov
if __name__=='__main__':
    f=int(sys.argv[1]); im=room(f); im.save(sys.argv[2]); print(im.size)

# all.py — render every room
import sys,os,rt,traceback
from multiprocessing import Pool
def init():
    import xg; xg.F=open('/home/claude/xg/disc/d1.bin','rb')
def one(f):
    out='master/%d.png'%f
    if os.path.exists(out): return f,'have'
    try:
        im=rt.room(f,1024)
        if im is None: return f,'none'
        im.save(out); return f,'ok'
    except Exception as e:
        return f,'ERR '+repr(e)[:120]
if __name__=='__main__':
    ids=sorted(int(k) for k in rt.PLAN)
    with Pool(os.cpu_count(),initializer=init) as p:
        res=p.map(one,ids,chunksize=4)
    bad=[r for r in res if r[1] not in('ok','have')]
    print(len(res),'rooms',len(bad),'bad',bad[:20])

# export.py — finish and write the WebP pictures
import os,sys,numpy as np
from PIL import Image
OLD='/home/claude/xg/plan_old/%d.png'
def load(f,size=512):
    a=np.asarray(Image.open('master/%d.png'%f).convert('RGBA')).astype(np.float32)
    v=a[...,3]>0
    if not v.any(): return None,0,0,1
    lum=a[...,:3].mean(-1)[v]; p95=float(np.percentile(lum,95)); g=1.0
    if p95<100: g=min(3.0,100/max(p95,1))
    a[...,:3]=np.clip(a[...,:3]*g,0,255)
    a[...,:3]*=a[...,3:]/255
    s=np.asarray(Image.fromarray(a.astype(np.uint8),'RGBA').resize((size,size),Image.LANCZOS)).astype(np.float32)
    al=s[...,3:]; rgb=np.where(al>0,s[...,:3]*255/np.maximum(al,1),0)
    out=np.dstack([np.clip(rgb,0,255),al[...,0]]).astype(np.uint8)
    return Image.fromarray(out,'RGBA'),float(v.mean()),p95,g
def final(f,size=512):
    """textured picture; where it has nothing, the old shaded picture shows through dimmed so no part of the room is lost"""
    im,cov,p95,g=load(f,size)
    o=np.asarray(Image.open(OLD%f).convert('RGBA').resize((size,size),Image.BILINEAR)).astype(np.float32)
    l=o[...,:3].mean(-1,keepdims=True)*0.30
    under=np.dstack([l*0.92,l*0.96,l*1.12,o[...,3:]])
    if im is None: return Image.fromarray(under.astype(np.uint8),'RGBA'),0,g
    n=np.asarray(im).astype(np.float32); a=n[...,3:]/255; ua=under[...,3:]/255
    oa=a+ua*(1-a); rgb=(n[...,:3]*a+under[...,:3]*ua*(1-a))/np.maximum(oa,1e-6)
    return Image.fromarray(np.dstack([rgb,oa*255]).clip(0,255).astype(np.uint8),'RGBA'),cov,g
if __name__=='__main__':
    out=sys.argv[1]; os.makedirs(out,exist_ok=True); tot=0; gains=0; n=0
    for f in sorted(int(x[:-4]) for x in os.listdir('master')):
        im,cov,g=final(f); gains+=g>1.02; n+=1
        fn='%s/%d.webp'%(out,f); im.save(fn,'WEBP',quality=75,method=6,alpha_quality=90); tot+=os.path.getsize(fn)
    print(n,'files, total',tot//1024,'KB; brightened',gains)
