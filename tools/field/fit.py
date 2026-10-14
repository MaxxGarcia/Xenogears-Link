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
