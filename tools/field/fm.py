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
