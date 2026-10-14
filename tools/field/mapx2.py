import struct,collections,mapx
from mapx import xg,T,shipped
def build(f,geo=True,dropdeg=True):
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154])
    if not o[1]<o[2]<=len(h): return None
    w=xg.lzss(h[o[1]:o[2]])
    sz=struct.unpack_from('<4I',w,4); so=struct.unpack_from('<I',w,0x14)[0]; to,vo=struct.unpack_from('<2I',w,0x18)
    k=max(0,min(256,(len(w)-so)//4)); surf=list(struct.unpack_from('<%dI'%k,w,so))+[0]*(256-k)
    nt=sz[0]//14; tr=[struct.unpack_from('<6HBB',w,to+14*i) for i in range(nt)]
    if not nt: return b''
    nvv=max(max(t[:3]) for t in tr)+1
    V=[struct.unpack_from('<3h',w,vo+8*i) for i in range(nvv)]
    key=lambda j:(V[j][0],V[j][2])
    if dropdeg: tr=[t for t in tr if len({key(t[0]),key(t[1]),key(t[2])})==3]
    idx={};vs=[];remap={}
    for t in tr:
        for j in t[:3]:
            kk=key(j)
            if kk not in idx: idx[kk]=len(vs);vs.append(kk)
            remap[j]=idx[kk]
    tones=[2 if surf[t[6]]&0x800000 else (0 if surf[t[6]]==0 else 1) for t in tr]
    cnt=collections.Counter()
    for i,t in enumerate(tr):
        if tones[i]==2: continue
        for e in range(3):
            a,b=remap[t[e]],remap[t[(e+1)%3]];cnt[(min(a,b),max(a,b))]+=1
    out=bytearray(struct.pack('<HH',len(vs),len(tr)))
    for x,z in vs: out+=struct.pack('<hh',x,z)
    for i,t in enumerate(tr):
        fl=tones[i]
        if fl!=2:
            for e in range(3):
                a,b=remap[t[e]],remap[t[(e+1)%3]]
                if cnt[(min(a,b),max(a,b))]==1: fl|=4<<e
        out+=struct.pack('<3HB',remap[t[0]],remap[t[1]],remap[t[2]],fl)
    return bytes(out)
if __name__=='__main__':
    ok=0;miss=[]
    for f in range(730):
        s=shipped(f)
        if s is None: continue
        if build(f)==s: ok+=1
        else: miss.append(f)
    print('match',ok,'differ',len(miss),miss[:30])
