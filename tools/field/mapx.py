import sys,struct,base64,re
sys.path.insert(0,'/home/claude/xg/tools');import xg
T=xg.table()
def shipped(f):
    try: s=open('/home/claude/xg/v/www/maps/%d.js'%f).read()
    except: return None
    m=re.search(r'"([A-Za-z0-9+/=]*)"',s)
    return base64.b64decode(m.group(1)) if m else b''
def build(f,variant=0):
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154])
    if not o[1]<o[2]<=len(h): return None
    w=xg.lzss(h[o[1]:o[2]])
    n=struct.unpack_from('<I',w,0)[0]; sz=struct.unpack_from('<4I',w,4); so=struct.unpack_from('<I',w,0x14)[0]
    to,vo=struct.unpack_from('<2I',w,0x18)
    k=max(0,min(256,(len(w)-so)//4)); surf=list(struct.unpack_from('<%dI'%k,w,so))+[0]*(256-k)
    nt=sz[0]//14; tr=[struct.unpack_from('<6HBB',w,to+14*i) for i in range(nt)]
    if not nt: return b''
    nvv=max(max(t[:3]) for t in tr)+1
    V=[struct.unpack_from('<3h',w,vo+8*i) for i in range(nvv)]
    idx={};vs=[];remap=[]
    remap=[None]*nvv
    for t in tr:
        for j in t[:3]:
            x,y,z=V[j];k=(x,z)
            if k not in idx: idx[k]=len(vs);vs.append(k)
            remap[j]=idx[k]
    def tone(t):
        fl=surf[t[6]]
        return 2 if fl&0x800000 else (0 if fl==0 else 1)
    tones=[tone(t) for t in tr]
    out=bytearray(struct.pack('<HH',len(vs),nt))
    for x,z in vs: out+=struct.pack('<hh',x,z)
    for i,t in enumerate(tr):
        fl=tones[i]
        for e in range(3):
            nb=t[3+e]
            if variant==0: edge = nb==0xFFFF or nb>=nt or ((tones[nb]==2)!=(tones[i]==2))
            if edge and tones[i]!=2: fl|=4<<e
        out+=struct.pack('<3HB',remap[t[0]],remap[t[1]],remap[t[2]],fl)
    return bytes(out)
if __name__=='__main__':
    ok=bad=0;miss=[]
    for f in range(730):
        s=shipped(f)
        if s is None: continue
        b=build(f)
        if b==s: ok+=1
        else: bad+=1; miss.append(f)
    print('match',ok,'differ',bad,miss[:20])
