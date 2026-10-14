import xg,struct
T=xg.table()
def model(f):
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154])
    if not (o[2]<o[3]<=len(h)): return None
    md=xg.lzss(h[o[2]:o[3]])
    n=struct.unpack('<I',md[:4])[0]
    if not 1<=n<=4000: return None
    offs=list(struct.unpack('<%dI'%n,md[4:4+4*n]))+[len(md)]
    out={}
    for i in range(n):
        s=md[offs[i]:offs[i+1]]
        if len(s)<0x48: continue
        nv,nf,ng=struct.unpack('<3H',s[0x12:0x18])
        vo,no,fo,eo=struct.unpack('<4I',s[0x18:0x28])
        if not(0x48<=vo<=fo<=eo<=len(s)) or nv==0 or fo+4>len(s): continue
        if vo+nv*8>len(s): continue
        V=[struct.unpack('<3h',s[vo+8*k:vo+8*k+6]) for k in range(nv)]
        # every face entry is four u16 vertex indices; a triangle leaves the fourth unused
        faces=[];p=fo;ok=True
        for g in range(max(ng,1)):
            if p+4>eo: ok=False;break
            typ,cnt=struct.unpack('<2H',s[p:p+4]); p+=4
            if p+cnt*8>eo: ok=False;break
            idx=struct.unpack('<%dH'%(cnt*4),s[p:p+cnt*8]); p+=cnt*8
            k=4 if (typ&0x08) else 3
            for c in range(cnt):
                fa=idx[c*4:c*4+k]
                if max(fa)<nv: faces.append(fa)
        if ok and faces: out[i]=(V,faces)
    return out

def entities(f):
    """placement table: (flags, rotX, rotY, rotZ, x, y, z, modelID); angles are 4096 per turn"""
    h=xg.getfile(606+2*f,T); ne=struct.unpack('<I',h[0x18C:0x190])[0]
    return [struct.unpack('<8h',h[0x190+16*i:0x190+16*i+16]) for i in range(min(ne,2000))]
def placed(f,ysign=1):
    """room geometry in room coordinates: every entity without the sprite bit (0x40) places one model"""
    import math
    m=model(f)
    if not m: return None
    out=[]
    for fl,rx,ry,rz,px,py,pz,mid in entities(f):
        if fl&0x40 or mid not in m: continue
        V,F=m[mid]
        a=ry*math.pi/2048*ysign; c,s_=math.cos(a),math.sin(a)
        ax=rx*math.pi/2048; cx,sx=math.cos(ax),math.sin(ax)
        az=rz*math.pi/2048; cz,sz=math.cos(az),math.sin(az)
        W=[]
        for x,y,z in V:
            y,z=y*cx-z*sx,y*sx+z*cx          # about X
            x,z=x*c+z*s_,-x*s_+z*c           # about Y
            x,y=x*cz-y*sz,x*sz+y*cz          # about Z
            W.append((x+px,y+py,z+pz))
        out.append((W,F))
    return out
