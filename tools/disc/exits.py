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
# Room exits read off the room scripts: [x, z, destination room] per room. Only exits with a known place and a believable destination:
#  - a room change guarded by a trigger-zone test (place = centre of the zone), or
#  - a room change in the talk / touch routine of an actor that was given a position, when the destination room also leads back here
#    (which doors do and story scenes do not) or the actor is an invisible trigger.
import json,exits,collections,sys
RAW={int(k):v for k,v in json.load(open('exits_raw.json')).items()}
AUD={r['f']:r for r in json.load(open('/home/claude/xg/audit/audit.json'))}
def near(f,p):
    b=AUD.get(f,{}).get('bbox')
    if not b: return True
    mg=max(b[2]-b[0],b[3]-b[1])*0.15+150
    return b[0]-mg<=p[0]<=b[2]+mg and b[1]-mg<=p[1]<=b[3]+mg
links=collections.defaultdict(set)
for f,s in RAW.items():
    for x in s:
        if x['dest']<730 and x['dest']!=f: links[f].add(x['dest'])
out={};st=collections.Counter()
for f,s in sorted(RAW.items()):
    Z=None;got=[]
    for x in s:
        d=x['dest']
        if d>=730 or d==f: continue
        back=f in links.get(d,())
        if x['zone'] is not None:
            if Z is None: Z=exits.zones(f)
            if x['zone']>=len(Z): st['zone missing']+=1;continue
            q=Z[x['zone']];p=[round(sum(c[0] for c in q)/4),round(sum(c[1] for c in q)/4)];kind='zone'
        elif x['pos'] and x['r'] in(2,3) and (back or x.get('door') or (x['bc'] and not x['spr'])):
            p=x['pos'];kind='door'
        else: st['skipped']+=1;continue
        if not near(f,p): st['off the map']+=1;continue
        if any(abs(p[0]-g[0])+abs(p[1]-g[1])<40 and g[2]==d for g in got): continue
        got.append([p[0],p[1],d]);st[kind]+=1;st['with way back' if back else 'one way']+=1
    if got: out[f]=got
print(dict(st),'rooms with exits',len(out),'exits',sum(len(v) for v in out.values()))
json.dump(out,open('exits.json','w'),separators=(',',':'))
if len(sys.argv)>1:
    open('/home/claude/xg/data/exits.js','w').write('/* Room exits read off the room scripts on the disc: room -> [x, z, destination room]. Places are trigger zones or door actors. */\nwindow.EXITS='+json.dumps(out,separators=(',',':'))+';\n')
for f in (1,14,23,24,29,58,65,102,290,406): print(f,out.get(f))
