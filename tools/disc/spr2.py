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
