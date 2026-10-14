import sys,json,collections
sys.path.insert(0,'/home/claude/xg/fld')
import tre,surv,chest,exits
import importlib
def base(f,acts):
    r=tre.vm.load(f); ent=r[2]; out={}
    for own,a,b,o,stt,code in tre.routines(f):
        if own[0] in acts and a==ent[own[0]][0] and own[0] not in out:
            for p,k,arg in surv.ins(o,b,code):
                if k=='19' and len(arg)>=5 and arg[4]&0xC0==0xC0: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
                if k=='1D' and len(arg)>=6: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
                if k=='1B' and len(arg)>=7 and arg[6]&0xC0==0xC0: out[own[0]]=[chest.s16(arg),chest.s16(arg,2)]; break
    return out
for f in range(730):
    L=[t for t in chest.room(f) if t['flag'] and t['src']=='actor']
    if not L: continue
    acts={t['actor'] for t in L}; pos=base(f,acts); E=exits.ents(f); R=tre.routines(f); Z=exits.zones(f)
    for a in sorted(acts-set(pos)):
        if a<len(E) and (E[a][4] or E[a][6]): print(f,a,'ENT',E[a][4],E[a][6]); continue
        print(f,'actor',a,'items',[t['v'] for t in L if t['actor']==a],'zones',len(Z))
        for own,s,b,o,stt,code in R:
            if own[0]!=a: continue
            ks=[]
            for p,k,arg in surv.ins(o,b,code):
                if k in('19','1D','1B','0B','16','BC','4A','1A','8C','8F','C9','CB','CC','0A','08','09','2A','20','21','22','23'): ks.append('%s:%s'%(k,arg.hex()))
            print('    r%d'%own[1],stt[0],' '.join(ks)[:330])
