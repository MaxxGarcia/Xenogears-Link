import sys,json,collections
sys.path.insert(0,'/home/claude/xg/fld')
import tre,surv,chest,exits
def info(f,act):
    R=tre.routines(f); r=tre.vm.load(f); ent=r[2]; out=[]
    for own,a,b,o,stt,code in R:
        if own[0]==act and a==ent[act][0]:
            for p,k,arg in surv.ins(o,b,code):
                if k in('19','1D','1B','0B','16','BC','4A','1A'): out.append('%s %s'%(k,arg.hex()))
    return out
if __name__=='__main__':
    n=0
    for f in range(730):
        L=[t for t in chest.room(f) if t['flag'] and t['src']=='actor']
        if not L: continue
        pos=__import__('mktre_pos').actor_pos(f,{t['actor'] for t in L}) if False else None
        E=exits.ents(f)
        seen=set()
        for t in L:
            a=t['actor']
            if a in seen: continue
            seen.add(a)
            e=E[a] if a<len(E) else None
            print(f,'actor',a,'item',t['v'],'ent',e,info(f,a)[:8])
