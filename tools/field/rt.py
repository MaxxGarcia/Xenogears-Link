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
