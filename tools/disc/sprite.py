import sys,struct
sys.path.insert(0,'/home/claude/xg/tools');import xg
from PIL import Image
T=xg.table()
_fc={}
def getf(f):
    if f not in _fc: _fc[f]=xg.getfile(f,T)
    return _fc[f]
def arch(b):
    n=struct.unpack_from('<I',b,0)[0]
    o=struct.unpack_from('<%dI'%(n+1),b,4)
    return [b[o[i]:o[i+1]] for i in range(n)]
def pack(f):
    d=getf(f); n=struct.unpack_from('<I',d,0)[0]
    return d,[struct.unpack_from('<III',d,8+12*i) for i in range(n)]
def resolve(d,ents,i):
    """entry -> (defoff, texoff, variant, type)"""
    a,b,c=ents[i]; hdr=8+12*len(ents)
    if a<hdr: # whole entry is a reference
        a2,b2,c2=ents[a]; return resolve_tex(d,ents,a2,b2)+(c>>24,c&0xFFFFFF)
    return resolve_tex(d,ents,a,b)+(c>>24,c&0xFFFFFF)
def resolve_tex(d,ents,a,b):
    hdr=8+12*len(ents)
    while b<hdr: b=ents[b][1] if ents[b][1]!=b else hdr+1 if False else ents[b][1]
    return (a,b)
def sheets(blk):
    out=[]
    for s in arch(blk):
        w,h=struct.unpack_from('<HH',s,0); out.append((w*2,h,s[4:4+w*2*h]))
    return out
def frames(s1):
    n=s1[0]; offs=struct.unpack_from('<%dH'%n,s1,2); out=[]
    for o in offs:
        try:
            nt=s1[o]; wide=nt&0x80; nt&=0x3f
            tiles=struct.unpack_from('<%dH'%nt,s1,o+4); p=o+4+2*nt; pl=[]
            for t in tiles:
                while s1[p]>=0xC0: p+= 3 if s1[p]>=0xE0 else 1
                fl=s1[p]; p+=1; rot=None
                if fl&0x80: rot=s1[p]; p+=1
                if wide: x,y=struct.unpack_from('<hh',s1,p); p+=4
                else: x,y=struct.unpack_from('<bb',s1,p); p+=2
                pl.append((t,fl,x,y,rot))
            out.append(pl)
        except Exception: out.append(None)
    return out
def pals(s2):
    a,b=struct.unpack_from('<HH',s2,0); n=(len(s2)-4)//32; out=[]
    for i in range(n):
        c=struct.unpack_from('<16H',s2,4+32*i); p=[]
        for k,v in enumerate(c):
            p.append(((v&31)<<3|(v&31)>>2,((v>>5)&31)<<3|((v>>5)&31)>>2,((v>>10)&31)<<3|((v>>10)&31)>>2,0 if (k==0 or v==0) else 255))
        out.append(p)
    return max(a,1),out
def render(d,defoff,texoff,fi,variant=0,flipmask=(0x10,0x20)):
    A=arch(d[defoff:]); s1=A[1]; a,P=pals(A[2]); sh=sheets(d[texoff:])
    pl=frames(s1)[fi]
    if not pl: return None
    px={}
    for t,fl,x,y,rot in reversed(pl):
        tf,u,v,w,h=s1[t:t+5]
        sw,shh,data=sh[min((tf>>1)&7,len(sh)-1)]
        pi=variant*a+(fl&0x0F if (fl&0x0F)<a else 0)
        pal=P[pi if pi<len(P) else 0]
        for yy in range(h):
            sy=v+yy
            if sy>=shh: continue
            for xx in range(w):
                sx=u+xx
                byte=data[sy*sw+(sx>>1)]; c=(byte>>4) if sx&1 else (byte&15)
                if c==0 or pal[c][3]==0: continue
                dx=(w-1-xx) if fl&flipmask[0] else xx; dy=(h-1-yy) if fl&flipmask[1] else yy
                px[(x+dx,y+dy)]=pal[c]
    if not px: return None
    xs=[p[0] for p in px];ys=[p[1] for p in px]
    x0,y0=min(xs),min(ys); im=Image.new('RGBA',(max(xs)-x0+1,max(ys)-y0+1))
    for (x,y),c in px.items(): im.putpixel((x-x0,y-y0),c)
    return im,(x0,y0)
def poses(d,defoff):
    A=arch(d[defoff:]); s0=A[0]; n=struct.unpack_from('<H',s0,0)[0]; offs=struct.unpack_from('<%dH'%n,s0,2)
    return s0[2+2*n:min(offs)]

# ---- mkspr.py: render every on-foot enemy's idle frame into www/spr and record it ----
# import spr2,struct,pickle,os,json,collections
# from PIL import Image
# R=pickle.load(open('recs.pkl','rb'))
# files=[];names={}
# for f,k,n,r in R:
#     if f not in files: files.append(f)
#     names[(f,k)]=(n,r)
# OUT='/home/claude/xg/v/www/spr'; os.makedirs(OUT,exist_ok=True)
# for x in os.listdir(OUT): os.remove(os.path.join(OUT,x))
# def idle(d,a):
#     s0=spr2.arch(d[a:])[0]; n=struct.unpack_from('<H',s0,0)[0]; offs=struct.unpack_from('<%dH'%n,s0,2)
#     o=offs[0]; fl,a1,a2=struct.unpack_from('<HHH',s0,o); t1=o+2+a1
#     for p in range(t1,min(t1+12,len(s0)-1)):
#         if s0[p]==0xBE: return max(s0[p+1]-1,0)
#     return 0
# P=[];done={};sheet=[];stats=collections.Counter()
# for bi,f in enumerate(files):
#     d,ents=spr2.pack(f+1); row=[0]*8
#     for k in range(min(8,len(ents))):
#         n,r=names.get((f,k),('',None))
#         try:
#             a,b,v,t=spr2.resolve(d,ents,k)
#         except Exception as ex: stats['resolve-err']+=1;continue
#         if t!=0: stats['model']+=1;continue
#         key=(f,a,b,v)
#         if key not in done:
#             im=None
#             try:
#                 fi=idle(d,a); fr=spr2.frames(spr2.arch(d[a:])[1])
#                 cand=[fi]+list(range(len(fr)))
#                 for c in cand:
#                     if c<len(fr) and fr[c]:
#                         res=spr2.render(d,a,b,c,v)
#                         if res and res[0].width>=8 and res[0].height>=8: im=res[0];break
#             except Exception as ex: stats['render-err']+=1; print('ERR',f,k,n,repr(ex)[:80])
#             if im is None: done[key]=0
#             else:
#                 name='%d_%d'%(bi,k); im.save(os.path.join(OUT,name+'.png'),optimize=True); done[key]=name; sheet.append((n,im))
#                 stats['ok']+=1
#         row[k]=done[key]
#     P.append(row)
# json.dump(P,open('sprmap.json','w'))
# print(stats, sum(os.path.getsize(os.path.join(OUT,x)) for x in os.listdir(OUT)), len(os.listdir(OUT)))
# print(max(im.width for _,im in sheet),max(im.height for _,im in sheet))
# # contact sheet
# cw,ch=110,110;cols=12
# cs=Image.new('RGBA',(cols*cw,((len(sheet)+cols-1)//cols)*ch),(40,40,60,255))
# for i,(n,im) in enumerate(sheet):
#     s=min(1,(cw-4)/im.width,(ch-4)/im.height)
#     t=im if s>=1 else im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.NEAREST)
#     cs.alpha_composite(t,(i%cols*cw+(cw-t.width)//2,i//cols*ch+(ch-t.height)//2))
# cs.save('contact.png');print(cs.size,[n for n,_ in sheet][:40])

# ==== gear.py: gear-sized enemies (3D models) ====
#G import sys,struct,math,collections
#G import numpy as np
#G import spr2
#G from PIL import Image
#G def arch_safe(b):
#G     n=struct.unpack_from('<I',b,0)[0]
#G     if not 0<n<400: raise ValueError('arch n=%d'%n)
#G     o=struct.unpack_from('<%dI'%(n+1),b,4)
#G     return [b[o[i]:o[i+1]] if 0<o[i]<=o[i+1]<=len(b) else b'' for i in range(n)]
#G def load(d,a,b):
#G     A=arch_safe(d[a:]); anims=arch_safe(arch_safe(A[0])[0]); B=arch_safe(d[b:])
#G     return anims,B
#G def vram(texblk):
#G     V=np.zeros((512,1024),dtype=np.uint16)
#G     for e in arch_safe(texblk):
#G         if len(e)<16: continue
#G         fl,x,y,ox,oy,w,h=struct.unpack_from('<I6H',e,0)
#G         if w==0 or h==0 or 16+w*h*2>len(e)+1: continue
#G         X=x+ox;Y=y+oy
#G         if X+w>1024 or Y+h>512: continue
#G         V[Y:Y+h,X:X+w]=np.frombuffer(e[16:16+w*h*2],dtype='<u2').reshape(h,w)
#G     return V
#G def meshes(m):
#G     """parts: (vertices, [(type, faces)], status/primitive stream)"""
#G     n=struct.unpack_from('<I',m,0)[0]; out=[]
#G     for i in range(n):
#G         h=4+0x38*i
#G         nv,nf,ng=struct.unpack_from('<3H',m,h+0x0E); vo,no,fo,eo=struct.unpack_from('<4I',m,h+0x14)
#G         V=np.array([struct.unpack_from('<3h',m,vo+8*k) for k in range(nv)],dtype=float).reshape(-1,3)
#G         groups=[];p=fo
#G         for g in range(ng):
#G             typ,cnt=struct.unpack_from('<HH',m,p); p+=4
#G             groups.append((typ&0xFF,[struct.unpack_from('<4H',m,p+8*c) for c in range(cnt)])); p+=cnt*8
#G         out.append((V,groups,eo))
#G     ends=sorted(set(x[2] for x in out))+[len(m)]
#G     return [(V,groups,m[eo:ends[ends.index(eo)+1]]) for V,groups,eo in out]
#G def polys(groups,st):
#G     """walk the stream. Group type bits: 1 textured, 2 lit, 8 quad. Words with a top byte >= 0x80 are status words
#G     (0xC4 texture page, 0xC8 palette). Textured triangle: [uv of vertex 2 | command], [uv 0, uv 1]. Textured quad:
#G     [command], [uv 0, uv 1], [uv 2, uv 3]. Untextured: one colour word."""
#G     p=0;tp=0;cl=0;out=[];fi=0;nf=sum(len(f) for _,f in groups)
#G     for typ,faces in groups:
#G         quad=bool(typ&8);tex=bool(typ&1)
#G         for f in faces:
#G             while p+4<=len(st) and st[p+3]>=0x80:
#G                 w=struct.unpack_from('<I',st,p)[0]
#G                 if w>>24==0xC4: tp=w&0xFFFF
#G                 elif w>>24==0xC8: cl=w&0xFFFF
#G                 p+=4
#G             need=(12 if quad else 8) if tex else 4
#G             if p+need>len(st): return out,fi,p
#G             if tex:
#G                 if quad:
#G                     b=st[p+4:p+12]; uv=[(b[0],b[1]),(b[2],b[3]),(b[4],b[5]),(b[6],b[7])]
#G                 else:
#G                     b=st[p:p+8]; uv=[(b[4],b[5]),(b[6],b[7]),(b[0],b[1])]
#G                 out.append((f[:4 if quad else 3],'t',(uv,tp,cl,st[p+3])))
#G             else:
#G                 out.append((f[:4 if quad else 3],'c',struct.unpack_from('<I',st,p)[0]&0xFFFFFF))
#G             p+=need;fi+=1
#G     return out,fi,p
#G def rot(rx,ry,rz,order):
#G     def R(axis,a):
#G         a=a*math.pi/2048;c,s=math.cos(a),math.sin(a)
#G         if axis=='x': return np.array([[1,0,0],[0,c,-s],[0,s,c]])
#G         if axis=='y': return np.array([[c,0,s],[0,1,0],[-s,0,c]])
#G         return np.array([[c,-s,0],[s,c,0],[0,0,1]])
#G     M=np.eye(3)
#G     for ax in order: M=M@R(ax,{'x':rx,'y':ry,'z':rz}[ax])
#G     return M
#G def pose(anim0,hier,order='zyx'):
#G     nb=struct.unpack_from('<H',anim0,0)[0]
#G     nodes=[struct.unpack_from('<hh',hier,i*4) for i in range(nb)]
#G     W=[]
#G     for i,(mesh,par) in enumerate(nodes):
#G         rx,ry,rz,tx,ty,tz=struct.unpack_from('<6h',anim0,0x18+12*i)
#G         L=np.eye(4);L[:3,:3]=rot(rx,ry,rz,order);L[:3,3]=(tx,ty,tz)
#G         W.append(L if par<0 or par>=i else W[par]@L)
#G     return nodes,W
#G def build(d,a,b,order='zyx'):
#G     anims,B=load(d,a,b)
#G     M=meshes(B[1]);V=vram(B[0]);nodes,W=pose(anims[0],B[2],order)
#G     tris=[];stat=collections.Counter()
#G     for i,(mesh,par) in enumerate(nodes):
#G         if mesh<0 or mesh>=len(M): continue
#G         Vt,groups,st=M[mesh]
#G         P=(W[i][:3,:3]@Vt.T).T+W[i][:3,3]
#G         pl,fi,p=polys(groups,st); stat['faces']+=sum(len(f) for _,f in groups);stat['parsed']+=fi;stat['left']+=max(0,len(st)-p-3)
#G         for idx,kind,data in pl:
#G             if max(idx)>=len(P): continue
#G             order_=[(0,1,2),(1,3,2)] if len(idx)==4 else [(0,1,2)]
#G             for tr in order_:
#G                 pts=[P[idx[j]] for j in tr]
#G                 if kind=='t':
#G                     uv,tp,cl,c=data; tris.append((pts,'t',([uv[j] for j in tr],tp,cl)))
#G                 elif kind=='g': tris.append((pts,'g',[data[j] for j in tr]))
#G                 else: tris.append((pts,'c',data))
#G     return tris,V,stat
#G def texel(V,tp,cl,u,v):
#G     bx=(tp&0xF)*64;by=((tp>>4)&1)*256;mode=(tp>>7)&3
#G     cx=(cl&0x3F)*16;cy=(cl>>6)&0x1FF
#G     if mode==0:
#G         w=V[(by+v)&511,(bx+(u>>2))&1023];i=(w>>((u&3)*4))&15
#G     elif mode==1:
#G         w=V[(by+v)&511,(bx+(u>>1))&1023];i=(w>>((u&1)*8))&255
#G     else: return V[(by+v)&511,(bx+u)&1023]
#G     return V[cy,(cx+i)&1023]
#G def render(tris,V,view='x',size=160,flip=False,yaw=0,pitch=0):
#G     if not tris: return None
#G     pts=np.array([p for t in tris for p in t[0]])
#G     if yaw or pitch:
#G         a=math.radians(yaw);c,s_=math.cos(a),math.sin(a)
#G         x=pts[:,0]*c+pts[:,2]*s_;z=-pts[:,0]*s_+pts[:,2]*c;pts=np.stack([x,pts[:,1],z],1)
#G         b=math.radians(pitch);c,s_=math.cos(b),math.sin(b)
#G         x=pts[:,0]*c-pts[:,1]*s_;y=pts[:,0]*s_+pts[:,1]*c;pts=np.stack([x,y,pts[:,2]],1)
#G     # view axes: horizontal h, vertical y (down positive), depth
#G     ax={'x':(2,1,0),'z':(0,1,2),'-x':(2,1,0),'-z':(0,1,2)}[view]
#G     H=pts[:,ax[0]].copy();Y=pts[:,ax[1]];D=pts[:,ax[2]].copy()
#G     if view in('-x',): H=-H;D=-D
#G     if view=='-z': H=-H;D=-D
#G     if flip: H=-H
#G     span=max(H.max()-H.min(),Y.max()-Y.min(),1);sc=(size-2)/span
#G     w=int((H.max()-H.min())*sc)+3;h=int((Y.max()-Y.min())*sc)+3
#G     col=np.zeros((h,w,4),dtype=np.uint8);zb=np.full((h,w),-1e18)
#G     X2=(H-H.min())*sc+1;Y2=(Y-Y.min())*sc+1
#G     L=np.array([0.3,-0.6,0.74]) # light in view space (h, y, depth toward viewer)
#G     for ti,(p3,kind,data) in enumerate(tris):
#G         i0=ti*3
#G         x=X2[i0:i0+3];y=Y2[i0:i0+3];z=D[i0:i0+3]
#G         x0=max(int(math.floor(x.min())),0);x1=min(int(math.ceil(x.max())),w-1);y0=max(int(math.floor(y.min())),0);y1=min(int(math.ceil(y.max())),h-1)
#G         if x1<x0 or y1<y0: continue
#G         den=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
#G         if abs(den)<1e-9: continue
#G         gx,gy=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
#G         a=((y[1]-y[2])*(gx-x[2])+(x[2]-x[1])*(gy-y[2]))/den
#G         b=((y[2]-y[0])*(gx-x[2])+(x[0]-x[2])*(gy-y[2]))/den
#G         c=1-a-b
#G         m=(a>=-0.01)&(b>=-0.01)&(c>=-0.01)
#G         if not m.any(): continue
#G         zz=a*z[0]+b*z[1]+c*z[2]
#G         # normal shading in view space
#G         v0=np.array([x[0],y[0],z[0]*sc]);v1=np.array([x[1],y[1],z[1]*sc]);v2=np.array([x[2],y[2],z[2]*sc])
#G         nrm=np.cross(v1-v0,v2-v0);nl=np.linalg.norm(nrm)
#G         sh=0.62+0.48*abs(float(nrm@L)/nl) if nl>0 else 1
#G         sub=zb[y0:y1+1,x0:x1+1];m&=zz>sub
#G         if not m.any(): continue
#G         if kind=='t':
#G             uv,tp,cl=data
#G             uu=np.clip(np.rint(a*uv[0][0]+b*uv[1][0]+c*uv[2][0]-0.0),0,255).astype(int);vv=np.clip(np.rint(a*uv[0][1]+b*uv[1][1]+c*uv[2][1]),0,255).astype(int)
#G             bx=(tp&0xF)*64;by=((tp>>4)&1)*256;mode=(tp>>7)&3;cx=(cl&0x3F)*16;cy=(cl>>6)&0x1FF
#G             if mode==0:
#G                 wv=V[(by+vv)&511,(bx+(uu>>2))&1023];ix=(wv>>((uu&3)*4))&15;px=V[cy,(cx+ix)&1023]
#G             elif mode==1:
#G                 wv=V[(by+vv)&511,(bx+(uu>>1))&1023];ix=(wv>>((uu&1)*8))&255;px=V[cy,(cx+ix)&1023]
#G             else: px=V[(by+vv)&511,(bx+uu)&1023]
#G             m&=px!=0
#G             r=(px&31)*8.2;g=((px>>5)&31)*8.2;bl=((px>>10)&31)*8.2
#G         else:
#G             if kind=='g':
#G                 cs=[((q&255),(q>>8)&255,(q>>16)&255) for q in data]
#G                 r=a*cs[0][0]+b*cs[1][0]+c*cs[2][0];g=a*cs[0][1]+b*cs[1][1]+c*cs[2][1];bl=a*cs[0][2]+b*cs[1][2]+c*cs[2][2]
#G             else:
#G                 r=np.full(a.shape,float(data&255));g=np.full(a.shape,float((data>>8)&255));bl=np.full(a.shape,float((data>>16)&255))
#G         if not m.any(): continue
#G         sc_=col[y0:y1+1,x0:x1+1]
#G         sc_[m,0]=np.clip(r*sh,0,255)[m];sc_[m,1]=np.clip(g*sh,0,255)[m];sc_[m,2]=np.clip(bl*sh,0,255)[m];sc_[m,3]=255
#G         sub[m]=zz[m]
#G     return Image.fromarray(col,'RGBA')
#G if __name__=='__main__':
#G     f=int(sys.argv[1]);ei=int(sys.argv[2])
#G     d,ents=spr2.pack(f);a,b,c=ents[ei]
#G     out=Image.new('RGBA',(4*170,3*170),(40,40,60,255))
#G     for r,order in enumerate(('xyz','zyx','yxz')):
#G         tris,V,stat=build(d,a,b,order)
#G         if r==0: print(stat,len(tris))
#G         for cidx,view in enumerate(('x','-x','z','-z')):
#G             im=render(tris,V,view)
#G             if im: out.alpha_composite(im,(cidx*170+2,r*170+2))
#G     out.resize((out.width*2,out.height*2),Image.NEAREST).save(sys.argv[3])

# ==== mkgear2.py: render every gear model into www/spr ====
#M # render a three-quarter view of every gear-sized enemy's 3D model into www/spr and record it in enemies.js
#M import os,sys,json,pickle,collections
#M import gear,spr2
#M from PIL import Image
#M R=pickle.load(open('recs.pkl','rb'));files=[]
#M for f,k,n,r in R:
#M     if f not in files: files.append(f)
#M OUT='/home/claude/xg/v/www/spr'
#M p='/home/claude/xg/v/www/enemies.js';s=open(p).read()
#M i=s.index('window.ENEMIES=');head=s[:i];E=json.loads(s[i+15:].rstrip().rstrip(';'))
#M for x in os.listdir(OUT):
#M     if x.startswith('g'): os.remove(os.path.join(OUT,x))
#M done={};st=collections.Counter();SS=4;SIZE=80
#M for bi,f in enumerate(files):
#M     d,ents=spr2.pack(f+1);hdr=8+12*len(ents)
#M     for k in range(min(8,len(ents))):
#M         if not E[bi]['n'][k] or E[bi]['n'][k].startswith('Monster'): continue
#M         a,b,c=ents[k]
#M         if (c&0xFFFFFF)!=1: continue
#M         hops=0
#M         while a<hdr and hops<4: a,b,c2=ents[a];hops+=1
#M         if a<hdr or b<hdr: st['unresolved']+=1;continue
#M         key=(f,a,b)
#M         if key not in done:
#M             try:
#M                 tris,V,stat=gear.build(d,a,b,'xyz');im=gear.render(tris,V,'-x',size=SIZE*SS,yaw=40)
#M                 im=im.crop(im.getbbox());im=im.resize((max(1,round(im.width/SS)),max(1,round(im.height/SS))),Image.LANCZOS)
#M                 name='g%d_%d'%(bi,k);im.save(os.path.join(OUT,name+'.png'),optimize=True);done[key]=[name,round(im.width/2,1),round(im.height/2,1)];st['ok']+=1
#M             except Exception as ex: done[key]=0;st['err']+=1;print('ERR',f,k,E[bi]['n'][k],repr(ex)[:80])
#M         E[bi]['p'][k]=done[key];st['records']+=1
#M head=head.replace("0 for gear-sized enemies, which are 3D models","sprites are the idle frame at one game pixel per unit; names starting g are three-quarter renders of a gear-sized enemy's 3D model at two image pixels per unit")
#M open(p,'w').write(head.rstrip()+'\nwindow.ENEMIES='+json.dumps(E,separators=(',',':'))+';\n')
#M print(st, sum(os.path.getsize(os.path.join(OUT,x)) for x in os.listdir(OUT)), len(os.listdir(OUT)))
#M nop=[(e['n'][k]) for e in E for k in range(8) if e['n'][k] and not e['n'][k].startswith('Monster') and (e['h'][k][0] or e['h'][k][1]) and not e['p'][k]]
#M print('named enemies still without a picture:',nop)

# ==== pbr.py: the party's battle sprites (disc files 2988-2998; tiles carry their own pixels) ====
#P import sys,struct
#P import spr2
#P from PIL import Image
#P def load(f):
#P     d=spr2.getf(f); A=spr2.arch(d); return A
#P def frames(s1):
#P     n=s1[0]; offs=struct.unpack_from('<%dH'%n,s1,2); out=[]
#P     for o in offs:
#P         nt=s1[o]&0x3f; hdr=s1[o:o+6]
#P         prs=[struct.unpack_from('<HH',s1,o+6+4*k) for k in range(nt)]
#P         p=o+6+4*nt; pl=[]
#P         for a,b in prs:
#P             ctl=[]
#P             while s1[p]>=0xC0:
#P                 if s1[p]>=0xE0: ctl.append(s1[p:p+3]); p+=3
#P                 else: ctl.append(s1[p:p+1]); p+=1
#P             fl=s1[p]; x,y=struct.unpack_from('<bb',s1,p+1); p+=3
#P             pl.append((a,b,fl,x,y,ctl))
#P         out.append((hdr,pl))
#P     return out
#P def render(A,fi,flip=(0x10,0x20),order=-1):
#P     s1=A[1]; a,P=spr2.pals(A[2]); hdr,pl=frames(s1)[fi]; px={}
#P     for t,b,fl,x,y,ctl in pl[::order]:
#P         w,h=s1[t*4],s1[t*4+1]; data=s1[t*4+4:]; pal=P[min(fl&0x0F,len(P)-1)]; rw=(w+1)//2
#P         rw=(rw+3)&~3 if False else rw
#P         for yy in range(h):
#P             for xx in range(w):
#P                 byte=data[yy*rw+(xx>>1)]; c=(byte>>4) if xx&1 else (byte&15)
#P                 if c==0: continue
#P                 dx=(w-1-xx) if fl&flip[0] else xx; dy=(h-1-yy) if fl&flip[1] else yy
#P                 px[(x+dx,y+dy)]=pal[c][:3]+(255,)
#P     if not px: return None
#P     xs=[p[0] for p in px];ys=[p[1] for p in px]
#P     x0,y0=min(xs),min(ys); im=Image.new('RGBA',(max(xs)-x0+1,max(ys)-y0+1))
#P     for (x,y),c in px.items(): im.putpixel((x-x0,y-y0),c)
#P     return im,(x0,y0)
#P if __name__=='__main__':
#P     f=int(sys.argv[1]); A=load(f); fr=frames(A[1]); n=len(fr)
#P     cols=16; cell=96; sheet=Image.new('RGBA',(cols*cell,((n+cols-1)//cols)*cell),(40,40,60,255))
#P     for i in range(n):
#P         try: r=render(A,i)
#P         except Exception as e: print(i,e); r=None
#P         if r: 
#P             im=r[0]; sheet.alpha_composite(im.crop((0,0,min(im.width,cell),min(im.height,cell))),((i%cols)*cell+2,(i//cols)*cell+2))
#P     sheet.save('pb_%d.png'%f); print(n,sheet.size)
# ---- mkpb.py: idle frame of each party member into www/img/pb/<character id>.png ----
#Q # party battle sprites: disc files 2988-2998 (idle frame 0) -> www/img/pb/<character id>.png
#Q import pbr,os,json
#Q OUT='/home/claude/xg/v/www/img/pb'; os.makedirs(OUT,exist_ok=True)
#Q FILE={0:2988,1:2989,2:2991,3:2990,4:2992,5:2993,6:2994,7:2995,8:2996,9:2997,10:2998}
#Q sz=[]
#Q for i in range(11):
#Q     im=pbr.render(pbr.load(FILE[i]),0)[0]; im.save('%s/%d.png'%(OUT,i),optimize=True); sz.append([im.width,im.height])
#Q print(json.dumps(sz).replace(' ',''), sum(os.path.getsize(OUT+'/'+x) for x in os.listdir(OUT)))
