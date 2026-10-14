import tre,vm,scr,json,collections,struct,sys
sys.path.insert(0,'/home/claude/xg/tools')
def u16(c,p): return c[p]|c[p+1]<<8
def s16(c,p):
    v=u16(c,p);return v-65536 if v&0x8000 else v
ZT=('C9','CB','CC','0A')
def zones(f):
    b=scr.block(f,8)
    if not b: return []
    out=[]
    for i in range(len(b)//24):
        q=struct.unpack_from('<12h',b,i*24);out.append([(q[0],q[2]),(q[3],q[5]),(q[6],q[8]),(q[9],q[11])])
    return out
import xg
T=xg.table()
def ents(f):
    h=xg.getfile(606+2*f,T);ne=struct.unpack('<I',h[0x18C:0x190])[0]
    return [struct.unpack('<8h',h[0x190+16*i:0x190+16*i+16]) for i in range(min(ne,2000))]
def scan(f):
    R=tre.routines(f);init={};out=[]
    for (ai,ri),a,b,o,stt,code in R:
        if ri==0:
            pos=None;ks=set()
            for p,k in o:
                ks.add(k)
                if k=='19' and pos is None and p+6<=len(code) and code[p+5]&0xC0==0xC0: pos=[s16(code,p+1),s16(code,p+3)]
            init[ai]=(pos,ks)
    E=ents(f)
    def epos(ai):
        if ai<len(E) and (E[ai][4] or E[ai][6]): return [E[ai][4],E[ai][6]]
        return None
    for (ai,ri),a,b,o,stt,code in R:
        guards=[]
        for i,(p,k) in enumerate(o):
            guards=[g for g in guards if g[1]>p]
            if k in ZT: guards.append((code[p+1],u16(code,p+2),k))
            if k=='47' and p+6<=len(code):
                d=u16(code,p+2);e=u16(code,p+4)
                if d&0x8000:
                    pos,ks=init.get(ai,(None,set()))
                    out.append(dict(a=ai,r=2,dest=d&0x3FF,flags=(d&0x7FFF)>>10,entry=(e&0x7FFF) if e&0x8000 else None,zone=None,zk=None,pos=pos or epos(ai),bc=True,spr=False,door=True))
            if k=='98':
                d=u16(code,p+1);e=u16(code,p+3)
                if not d&0x8000: continue
                pos,ks=init.get(ai,(None,set()))
                out.append(dict(a=ai,r=ri,dest=d&0x3FF,flags=(d&0x7FFF)>>10,entry=(e&0x7FFF) if e&0x8000 else None,zone=guards[-1][0] if guards else None,zk=guards[-1][2] if guards else None,pos=pos or (epos(ai) if ri in(2,3) else None),bc='BC' in ks,spr='0B' in ks))
    return out
if __name__=='__main__':
    st=collections.Counter();byroom={}
    for f in range(730):
        try: s=scan(f)
        except Exception as e: st['err']+=1;continue
        byroom[f]=s
        for x in s:
            st['total']+=1
            if x['zone'] is not None: st['zone '+x['zk']]+=1
            else: st['r%d %s%s%s'%(min(x['r'],4),'pos ' if x['pos'] else 'nopos ','BC ' if x['bc'] else '','spr' if x['spr'] else '')]+=1
    for k,v in sorted(st.items()): print(v,k)
    print('rooms with a zone exit',sum(1 for f,s in byroom.items() if any(x['zone'] is not None for x in s)),'rooms with any',sum(1 for s in byroom.values() if s))
    json.dump(byroom,open('exits_raw.json','w'))
