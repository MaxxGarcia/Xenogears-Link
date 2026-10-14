# ===== ops.py =====
import struct,capstone,os,collections
BASE=0x8006FAF0
d=open('/home/claude/xg/ov36.dec','rb').read()
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32|capstone.CS_MODE_LITTLE_ENDIAN)
def w(a): return struct.unpack_from('<I',d,a-BASE)[0]
H1=[w(0x800AE2A0+4*i) for i in range(256)]
H2=[w(0x800AE6A0+4*i) for i in range(0x38C//4)]
def func(a,maxn=1200):
    out=[]
    for i in md.disasm(d[a-BASE:a-BASE+maxn*4],a):
        out.append(i)
        if len(out)>=2 and out[-2].mnemonic=='jr' and out[-2].op_str=='$ra': break
    return out
def incs_new(a):
    ins=func(a); res=[]; calls=[]; reg=set(); stored=False
    for k,i in enumerate(ins):
        m,o=i.mnemonic,i.op_str
        if m=='jal': calls.append(int(o,16))
        if m=='lhu' and '0xcc(' in o: reg.add(o.split(',')[0])
        elif m=='addiu':
            p=[x.strip() for x in o.split(',')]
            if p[1] in reg and p[0]==p[1]:
                try: res.append(int(p[2],0))
                except: pass
        elif m in('sh',) and '0xcc(' in o:
            stored=True
            if o.split(',')[0] not in reg: res.append('?')
    return res,calls,len(ins)
def incs_old(a):
    ins=func(a); res=[]; calls=[]
    reg={}
    for k,i in enumerate(ins):
        m,o=i.mnemonic,i.op_str
        if m=='jal': calls.append(int(o,16))
        if m=='lhu' and '0xcc(' in o: reg[o.split(',')[0]]=0
        elif m=='addiu':
            p=[x.strip() for x in o.split(',')]
            if p[1] in reg and reg[p[1]] is not None:
                try: reg[p[0]]=reg[p[1]]+int(p[2],0)
                except: pass
        elif m=='sh' and '0xcc(' in o:
            res.append(reg.get(o.split(',')[0],'?'))
    return res,calls,len(ins)
incs=incs_old
if __name__=='__main__':
    import sys
    for name,H in (('',H1),('FE',H2)):
        for op,a in enumerate(H):
            r,c,n=incs(a)
            print('%s%02X %08X len=%-4d incs=%s calls=%s'%(name,op,a,n,sorted(set(map(str,r))),' '.join('%08X'%x for x in c[:6])))

# ===== ops2.py =====
import ops,functools
SKIP={0x800ACDB8,0x800ACDEC,0x800ACD7C,0x800A3018,0x800A2FE0,0x800A3074,0x8009CDB4,0x800A3090}
@functools.lru_cache(None)
def deep(a,depth=0):
    r,c,n=ops.incs(a); out=set(r)
    if depth<2:
        for t in c:
            if 0x8006FAF0<=t<0x8006FAF0+len(ops.d) and t not in SKIP: out|=deep(t,depth+1)
    return frozenset(out)
def table():
    L={}
    for pre,H in (('',ops.H1),('FE',ops.H2)):
        for op,a in enumerate(H):
            key=pre+'%02X'%op; res=[]
            for fn in (ops.incs_old,ops.incs_new):
                ops.incs=fn; deep.cache_clear()
                s=set(deep(a)); res.append(sorted(x for x in s if isinstance(x,int) and 0<x<64))
            pick=res[0][0] if len(res[0])==1 else res[1][0] if len(res[1])==1 else None
            L[key]=(a,pick,res)
    return L
if __name__=='__main__':
    L=table(); bad=[(k,v) for k,v in L.items() if v[1] is None]; print(len(bad))
    for k,v in bad: print(k,'%08X'%v[0],v[2])
    import json; json.dump({k:[v[0],v[1],v[2]] for k,v in L.items()},open('optable.json','w'))

# ===== scr.py =====
import sys,struct
sys.path.insert(0,'/home/claude/xg/tools')
import xg
T=xg.table()
def block(f,i):
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154])+(len(h),)
    if not o[i]<o[i+1]<=len(h): return None
    return xg.lzss(h[o[i]:o[i+1]])
if __name__=='__main__':
    f=int(sys.argv[1]); s=block(f,5); print(len(s)); print(s[:0x100].hex(' ',2))

# ===== vm.py =====
import sys,struct,json,collections
import scr
OT=json.load(open('/home/claude/xg/fld/optable.json'))
LEN={}
for k,(a,pick,res) in OT.items():
    if pick: LEN[k]=pick+(1 if k.startswith('FE') else 0)
MAN={'00':1,'01':3,'04':1,'0D':1,'92':1,'5B':1,'A6':1,'D1':1,'E4':1}
LEN.update(MAN)
def load(f):
    s=scr.block(f,5)
    if not s or len(s)<0x88: return None
    n=struct.unpack_from('<I',s,0x80)[0]
    if not 0<n<400 or 0x84+n*64>len(s): return None
    ent=[struct.unpack_from('<32H',s,0x84+i*64) for i in range(n)]
    return s,n,ent,s[0x84+n*64:]
def opkey(code,p):
    if code[p]==0xFE and p+1<len(code): return 'FE%02X'%code[p+1]
    return '%02X'%code[p]
def sweep(code,start,end,LEN=LEN):
    """linear decode; returns list of (offset,key) and where/why it stopped"""
    p=start; out=[]
    while p<end:
        k=opkey(code,p); L=LEN.get(k)
        if L is None: return out,('unknown',k,p)
        out.append((p,k)); p+=L
    return out,('ok' if p==end else 'overrun',None,p)
if __name__=='__main__':
    stat=collections.Counter(); unk=collections.Counter(); rooms=0
    for f in range(730):
        r=load(f)
        if not r: continue
        s,n,ent,code=r; rooms+=1
        starts=sorted(set(e for a in ent for e in a))+[len(code)]
        for a,b in zip(starts,starts[1:]):
            o,(st,k,p)=sweep(code,a,b); stat[st]+=1
            if st=='unknown': unk[k]+=1
    print(rooms,dict(stat)); print(unk.most_common(30))

# ===== fit.py =====
import vm,collections
vm.LEN.update({'10':11,'11':13})
R=[]
for f in range(730):
    r=vm.load(f)
    if r:
        s,n,ent,code=r; st=sorted(set(e for a in ent for e in a))+[len(code)]; R.append((f,code,st))
def score(LEN):
    ok=0;unk=collections.Counter();over=0
    for f,code,st in R:
        for a,b in zip(st,st[1:]):
            o,(s,k,p)=vm.sweep(code,a,b,LEN)
            if s=='ok': ok+=1
            elif s=='unknown': unk[k]+=1
            else: over+=1
    return ok,over,unk
ok,over,unk=score(vm.LEN); print('start',ok,over,unk.most_common(12))
while unk:
    K=unk.most_common(1)[0][0]; res=[]
    for L in range(1,26):
        T=dict(vm.LEN); T[K]=L; o,ov,u=score(T); res.append((o,-ov,L))
    res.sort(reverse=True); print(K,'best',res[:3],'cands',vm.OT.get(K,[0,0,0])[2])
    vm.LEN[K]=res[0][2]; ok,over,unk=score(vm.LEN)
print('final',ok,over)
import json; json.dump(vm.LEN,open('len.json','w'))

# ===== tre.py =====
import vm,json,struct,collections,sys
vm.LEN.update(json.load(open('len.json')))
def routines(f):
    r=vm.load(f)
    if not r: return []
    s,n,ent,code=r; st=sorted(set(e for a in ent for e in a))+[len(code)]; out=[]
    owner={}
    for ai,a in enumerate(ent):
        for ri,e in enumerate(a): owner.setdefault(e,(ai,ri))
    for a,b in zip(st,st[1:]):
        o,stt=vm.sweep(code,a,b); out.append((owner[a],a,b,o,stt,code))
    return out
def u16(code,p): return code[p]|code[p+1]<<8
if __name__=='__main__':
    f=int(sys.argv[1])
    for (ai,ri),a,b,o,stt,code in routines(f):
        if any(k=='8C' for p,k in o):
            print('actor',ai,'routine',ri,hex(a),hex(b),stt[0])
            for i,(p,k) in enumerate(o):
                L=(o[i+1][0] if i+1<len(o) else b)-p
                print('   %04X %-5s %s'%(p,k,code[p+ (2 if k.startswith('FE') else 1):p+L].hex(' ')))

# ===== surv.py =====
import sys;sys.path.insert(0,'/home/claude/xg/fld')
import tre
def ins(o,b,code):
    for i,(p,k) in enumerate(o):
        L=(o[i+1][0] if i+1<len(o) else b)-p
        yield p,k,code[p+(2 if k.startswith('FE') else 1):p+L]
def show(f):
    R=tre.routines(f); vars_=set()
    for own,a,b,o,stt,code in R:
        for p,k,arg in ins(o,b,code):
            if k=='8C' and not arg[1]&0x80: vars_.add(bytes(arg[:2]))
    print('=== room',f,'item vars',[v.hex() for v in vars_])
    for own,a,b,o,stt,code in R:
        lines=[]
        for p,k,arg in ins(o,b,code):
            if k in('8C','FB','FE0A','FE0B','8B','8F') or (k in('35','36','37') and bytes(arg[:2]) in vars_) or (k in('35',) and arg[:2] in(b'\x3c\x04',)):
                lines.append('   %04X %-5s %s'%(p,k,arg.hex(' ')))
        if any(' 8C ' in l or ' 35 ' in l or ' 8F ' in l for l in lines):
            print(' actor',own,'@%04X'%a,stt[0]); print('\n'.join(lines))
for f in map(int,sys.argv[1:]): show(f)

# ===== chest.py =====
import sys,json,collections,math
sys.path.insert(0,'/home/claude/xg/fld')
import tre,surv
def u16(b,i=0): return b[i]|b[i+1]<<8
def s16(b,i=0):
    v=u16(b,i); return v-65536 if v&0x8000 else v
def cond_flag(k,arg):
    """flag (var offset, bit) tested by a conditional, or None"""
    if len(arg)<(4 if k=='FB' else 7 if k=='02' else 99): return None
    if k=='FB': x=u16(arg); return (x>>4,x&15)
    if k=='02' and arg[4]==0x46:
        m=u16(arg,2)
        if m and m&(m-1)==0: return (u16(arg),m.bit_length()-1)
    return None
def set_flag(k,arg):
    if len(arg)<(2 if k=='FE0A' else 5 if k=='3A' else 99): return None
    if k=='FE0A': x=u16(arg); return (x>>4,x&15)
    if k=='3A' and arg[4]&0x40 and u16(arg,2)<16: return (u16(arg),u16(arg,2))
    return None
def room(f):
    R=tre.routines(f); out=[]; I=[]
    NEED={'8C':2,'8F':2,'35':5,'36':2}
    for own,a,b,o,stt,code in R: I.append((own,a,[(p,k,arg) for p,k,arg in surv.ins(o,b,code) if len(arg)>=NEED.get(k,0)]))
    tested=set()
    for own,a,L in I:
        for p,k,arg in L:
            c=cond_flag(k,arg)
            if c: tested.add(c)
    gives=[]  # (own, routine start, index, kind, arg)
    for ri,(own,a,L) in enumerate(I):
        for i,(p,k,arg) in enumerate(L):
            if k in('8C','8F'): gives.append((ri,i,k,u16(arg)))
    vars_=collections.defaultdict(set)
    for ri,i,k,v in gives:
        if not v&0x8000: vars_[v].add(k)
    done=set()
    # template chests: item comes from a variable set in a set-up routine
    for V,kinds in vars_.items():
        for ri,(own,a,L) in enumerate(I):
            for i,(p,k,arg) in enumerate(L):
                if k=='35' and u16(arg)==V and arg[4]&0x40:
                    val=u16(arg,2); flag=None; best=None
                    for j,(p2,k2,a2) in enumerate(L):
                        if ((k2=='36' and u16(a2)==V+2) or (k2=='35' and u16(a2)==V+2 and u16(a2,2)==1)) and j>0:
                            c=cond_flag(L[j-1][1],L[j-1][2])
                            if c and (best is None or abs(j-i)<best): best=abs(j-i); flag=c
                    pos=None; got={}
                    for p2,k2,a2 in L:
                        if k2=='35' and a2[4]&0x40 and u16(a2) in(V-8,V-6): got[u16(a2)]=s16(a2,2)
                    if V-8 in got and V-6 in got: pos=[got[V-8],got[V-6]]
                    out.append({'k':'gold' if '8F' in kinds and '8C' not in kinds else 'item','v':val,'flag':flag,'pos':pos,'src':'chest'})
    # direct pickups: the item is written into the instruction
    for ri,i,k,v in gives:
        if not v&0x8000: continue
        own,a,L=I[ri]; flag=None
        for d in range(1,14):
            for j in (i+d,i-d):
                if 0<=j<len(L):
                    c=set_flag(L[j][1],L[j][2])
                    if c and c in tested: flag=c; break
            if flag: break
        out.append({'k':'gold' if k=='8F' else 'item','v':v&0x7FFF,'flag':flag,'pos':None,'src':'actor','actor':own[0]})
    return out
if __name__=='__main__':
    allr={}; st=collections.Counter(); fl=collections.Counter()
    for f in range(730):
        r=room(f)
        if r: allr[f]=r
        for t in r:
            st[(t['src'],t['k'],'flag' if t['flag'] else 'noflag','pos' if t['pos'] else 'nopos')]+=1
            if t['flag']: fl[t['flag'][0]]+=1
    for k,v in sorted(st.items()): print(k,v)
    print('flag vars',sorted(fl.items()))
    json.dump(allr,open('chests.json','w'))

# ===== mktre.py =====
import sys,json,collections
sys.path.insert(0,'/home/claude/xg/fld')
import tre,surv,chest
def actor_pos(f,acts):
    r=tre.vm.load(f); ent=r[2]; out={}
    for own,a,b,o,stt,code in tre.routines(f):
        if own[0] in acts and a==ent[own[0]][0] and own[0] not in out:
            for p,k,arg in surv.ins(o,b,code):
                if k=='19' and len(arg)>=5 and arg[4]&0xC0==0xC0: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
                if k=='1D' and len(arg)>=6: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
                if k=='1B' and len(arg)>=7 and arg[6]&0xC0==0xC0: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
    return out
OUT={}; st=collections.Counter()
for f in range(730):
    L=[t for t in chest.room(f) if t['flag']]
    if not L: continue
    pos=actor_pos(f,{t['actor'] for t in L if t['src']=='actor'})
    groups=collections.OrderedDict()
    for t in L:
        key=(tuple(t['flag']),t['src'])
        g=groups.setdefault(key,{'items':[],'gold':0,'pos':None,'src':t['src']})
        if t['k']=='gold': g['gold']+=t['v']
        elif t['v'] not in g['items']: g['items'].append(t['v'])
        if t['pos']: g['pos']=t['pos']
        elif t['src']=='actor' and t.get('actor') in pos: g['pos']=pos[t['actor']]
        g['n']=g.get('n',0)+1
    rows=[]
    for (flag,src),g in groups.items():
        if src=='actor' and g['n']>3: st['dropped: one flag, many gives']+=1; continue
        if src=='chest' and len(g['items'])>1: st['chest with alternatives']+=1
        if any((c>>8)>4 for c in g['items']): st['dropped: bad item code']+=1; continue
        row=[flag[0],flag[1],g['items'],g['gold']]+(g['pos'] if g['pos'] else [])
        rows.append(row); st[src+(' pos' if g['pos'] else ' nopos')]+=1
    if rows: OUT[f]=rows
print(dict(st),'rooms',len(OUT),'entries',sum(len(v) for v in OUT.values()))
js='/* treasure and one-time pickups per room, read off the room scripts on the disc (see "Room scripts" in the RAM map).\n   room -> [flag variable, bit, [item codes], gold, x, z]; item code = inventory x 256 + id (0 items, 1 weapons, 2 equipment, 3 gear weapons, 4 gear parts);\n   taken when bit `bit` of the 16-bit script variable at 0x800C3A68 + variable is set; x, z are missing when the script gives no position. */\nwindow.TREASURE='+json.dumps(OUT,separators=(',',':'))+';\n'
open('/home/claude/xg/v/www/treasure.js','w').write(js); print(len(js))
json.dump(OUT,open('treasure.json','w'))

# ===== len.json (opcode lengths; FE-prefixed include the prefix byte) =====
{"02": 8, "03": 4, "05": 3, "06": 5, "07": 3, "08": 3, "09": 3, "0A": 4, "0B": 3, "0C": 1, "0E": 1, "0F": 1, "13": 1, "14": 1, "15": 1, "16": 3, "17": 18, "18": 5, "19": 6, "1A": 2, "1B": 7, "1C": 4, "1D": 7, "1E": 1, "1F": 2, "20": 3, "21": 3, "22": 1, "23": 1, "24": 2, "25": 2, "26": 3, "27": 2, "28": 2, "29": 2, "2A": 1, "2B": 1, "2C": 2, "2D": 8, "2E": 3, "2F": 3, "30": 3, "31": 5, "32": 5, "33": 1, "34": 5, "35": 6, "36": 3, "37": 3, "38": 6, "39": 6, "3A": 6, "3B": 6, "3C": 3, "3D": 3, "3E": 6, "3F": 6, "40": 6, "41": 5, "42": 5, "43": 3, "44": 5, "45": 8, "46": 1, "47": 6, "48": 7, "49": 8, "4A": 6, "4B": 8, "4C": 8, "4D": 10, "4E": 6, "4F": 8, "50": 8, "51": 10, "52": 2, "53": 4, "54": 5, "55": 7, "56": 10, "58": 4, "59": 1, "5A": 1, "5D": 2, "5E": 1, "5F": 2, "60": 1, "61": 8, "62": 2, "63": 8, "64": 1, "65": 8, "66": 2, "67": 4, "68": 4, "69": 3, "6A": 3, "6B": 3, "6C": 3, "6D": 8, "6E": 8, "6F": 2, "70": 2, "71": 3, "72": 3, "73": 8, "74": 3, "75": 3, "76": 1, "77": 1, "78": 4, "79": 1, "7A": 1, "7B": 4, "7C": 4, "7D": 4, "7E": 4, "7F": 3, "80": 5, "81": 5, "82": 5, "83": 5, "84": 5, "85": 5, "86": 5, "87": 3, "88": 3, "89": 6, "8A": 4, "8B": 5, "8C": 3, "8D": 3, "8E": 7, "8F": 3, "90": 3, "91": 4, "93": 3, "94": 5, "95": 2, "96": 1, "97": 3, "98": 5, "99": 1, "9A": 3, "9B": 5, "9C": 1, "9D": 4, "9E": 1, "9F": 1, "A0": 7, "A1": 3, "A2": 2, "A3": 8, "A4": 4, "A5": 3, "A7": 1, "A8": 5, "A9": 2, "AA": 2, "AB": 1, "AC": 4, "AD": 7, "AE": 7, "AF": 4, "B0": 4, "B1": 4, "B2": 2, "B3": 3, "B4": 3, "B5": 5, "B6": 5, "B7": 1, "B8": 1, "B9": 4, "BA": 2, "BB": 2, "BC": 1, "BD": 3, "BE": 3, "BF": 3, "C0": 3, "C1": 3, "C2": 3, "C3": 1, "C4": 2, "C5": 2, "C6": 1, "C7": 3, "C8": 3, "C9": 4, "CA": 8, "CB": 4, "CC": 4, "CD": 1, "CE": 1, "CF": 5, "D0": 11, "D2": 4, "D3": 4, "D5": 3, "D6": 3, "D7": 3, "D8": 3, "D9": 3, "DA": 17, "DB": 5, "DC": 5, "DD": 6, "DE": 6, "DF": 6, "E0": 7, "E1": 14, "E2": 5, "E3": 5, "E5": 17, "E6": 9, "E7": 7, "E8": 7, "E9": 7, "EA": 6, "EB": 20, "EC": 15, "ED": 8, "EE": 3, "EF": 3, "F0": 7, "F1": 11, "F2": 9, "F3": 7, "F4": 2, "F5": 4, "F6": 2, "F7": 5, "F8": 4, "F9": 2, "FA": 5, "FB": 5, "FD": 1, "FE": 2, "FF": 1, "FE01": 2, "FE02": 5, "FE03": 4, "FE04": 4, "FE05": 7, "FE06": 7, "FE07": 3, "FE08": 8, "FE09": 4, "FE0A": 4, "FE0B": 4, "FE0C": 14, "FE0D": 4, "FE0E": 6, "FE0F": 7, "FE10": 6, "FE11": 7, "FE12": 4, "FE13": 6, "FE14": 6, "FE15": 6, "FE16": 2, "FE17": 4, "FE19": 3, "FE1A": 2, "FE1B": 6, "FE1C": 9, "FE1D": 9, "FE1E": 3, "FE1F": 2, "FE20": 3, "FE21": 4, "FE22": 4, "FE23": 21, "FE24": 2, "FE25": 3, "FE26": 16, "FE27": 3, "FE28": 4, "FE29": 4, "FE2A": 4, "FE2B": 4, "FE2C": 4, "FE2D": 4, "FE2E": 4, "FE2F": 4, "FE30": 6, "FE31": 6, "FE32": 6, "FE33": 6, "FE34": 7, "FE35": 7, "FE36": 7, "FE37": 7, "FE38": 6, "FE39": 4, "FE3A": 4, "FE3B": 4, "FE3C": 6, "FE3D": 11, "FE3E": 11, "FE3F": 8, "FE40": 8, "FE41": 4, "FE42": 4, "FE43": 2, "FE44": 2, "FE45": 3, "FE46": 3, "FE47": 4, "FE48": 9, "FE49": 2, "FE4A": 4, "FE4B": 2, "FE4C": 3, "FE4D": 3, "FE4E": 2, "FE4F": 2, "FE50": 2, "FE51": 2, "FE52": 2, "FE53": 2, "FE54": 2, "FE55": 2, "FE56": 4, "FE57": 2, "FE58": 4, "FE59": 4, "FE5A": 4, "FE5B": 4, "FE5C": 5, "FE5D": 8, "FE5E": 4, "FE5F": 9, "FE60": 10, "FE61": 2, "FE62": 6, "FE63": 6, "FE64": 4, "FE65": 6, "FE66": 10, "FE67": 20, "FE68": 7, "FE69": 6, "FE6A": 4, "FE6B": 6, "FE6C": 2, "FE6D": 2, "FE6E": 5, "FE6F": 9, "FE70": 4, "FE71": 4, "FE72": 11, "FE73": 13, "FE74": 4, "FE75": 5, "FE76": 17, "FE77": 3, "FE7F": 2, "FE80": 16, "FE81": 9, "FE82": 26, "FE83": 4, "FE84": 10, "FE85": 4, "FE86": 3, "FE87": 2, "FE88": 19, "FE89": 12, "FE8A": 4, "FE8B": 4, "FE8C": 8, "FE8D": 4, "FE8E": 6, "FE8F": 9, "FE90": 10, "FE91": 15, "FE92": 15, "FE93": 12, "FE94": 11, "FE95": 15, "FE96": 2, "FE97": 3, "FE98": 4, "FE99": 3, "FE9A": 10, "FE9B": 4, "FE9C": 4, "FE9D": 4, "FE9E": 10, "FE9F": 5, "FEA0": 13, "FEA1": 6, "FEA2": 2, "FEA3": 3, "FEA4": 2, "FEA5": 8, "FEA6": 6, "FEA7": 10, "FEA8": 8, "FEA9": 8, "FEAA": 3, "FEAB": 5, "FEAC": 5, "FEAD": 5, "FEAE": 8, "FEAF": 19, "FEB1": 2, "FEB2": 5, "FEB3": 5, "FEB4": 5, "FEB5": 2, "FEB6": 3, "FEB7": 4, "FEB8": 5, "FEB9": 10, "FEBA": 11, "FEBB": 4, "FEBC": 5, "FEBD": 8, "FEBE": 2, "FEBF": 14, "FEC0": 4, "FEC1": 8, "FEC2": 10, "FEC3": 2, "FEC4": 3, "FEC5": 6, "FEC7": 6, "FEC8": 19, "FEC9": 19, "FECA": 3, "FECB": 2, "FECC": 2, "FECD": 4, "FECE": 4, "FECF": 6, "FED0": 6, "FED1": 2, "FED2": 4, "FED3": 18, "FED4": 11, "FED5": 6, "FED6": 6, "FED7": 7, "FED8": 3, "FED9": 3, "FEDA": 2, "FEDB": 4, "FEDC": 6, "FEDE": 6, "FEDF": 4, "FEE0": 3, "FEE1": 6, "FEE2": 2, "00": 1, "01": 3, "04": 1, "0D": 1, "92": 1, "5B": 1, "A6": 1, "D1": 1, "E4": 1, "10": 11, "11": 13, "57": 14, "FC": 5, "D4": 6, "5C": 3, "FE18": 5, "12": 4, "FEC6": 9, "FE00": 4, "FEB0": 10, "FEDD": 12, "FEE6": 25, "FEFA": 5, "FEF4": 13, "FE7E": 20, "FEE3": 20, "FEF8": 25, "FEFE": 25, "FEFD": 25, "FE7A": 6, "FEF7": 14, "FEFF": 7}