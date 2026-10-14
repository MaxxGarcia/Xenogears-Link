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
