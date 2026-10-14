import json,collections
import digest as D   # reuses caches and helpers (runs its digest once)
S=sorted(int(k) for k in D.N)
ST={}   # (f,own) -> set of story numbers tested
FL=collections.defaultdict(set); FT=collections.defaultdict(set); IT=collections.defaultdict(list)
for f in range(720):
    for own,ins in D.R(f).items():
        for p,k,a in ins:
            if k in('84','85','86','88') and len(a)>=2: ST.setdefault((f,own),set()).add((a[0]|a[1]<<8)&0x7fff)
for f in range(720):
    for own,ins in D.R(f).items():
        for p,k,a in ins:
            if k=='FE0A' and len(a)>=2: FL[a[0]|a[1]<<8].add((f,own,p))
            if k=='FB' and len(a)>=2: FT[a[0]|a[1]<<8].add((f,own))
            if k=='8C' and len(a)>=2 and a[1]&0x80==0 and False: pass
out=[]
for i,s in enumerate(S):
    if i==0: continue
    P=S[i-1]
    rng=set(range(P,s+1))
    act={x for x,v in ST.items() if v&rng}
    # flags set in active routines and tested in active routines (requirements inside the window)
    req=[]
    for fl,sets in FL.items():
        sa=[x for x in sets if (x[0],x[1]) in act]
        if sa and FT[fl]&act: req.append((fl,sa))
    if not req: continue
    out.append('\n### %d (window from %d)  now: %s'%(s,P,D.N[str(s)].lstrip('?')))
    for fl,sa in sorted(req)[:12]:
        f,own,p=sa[0]
        out.append('  flag %03X set in room %d %s a%d r%d'%(fl,f,D.area(f),own[0],own[1]))
        for t in D.ctx(f,own,p,2): out.append('     .. '+t)
open('/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/window.txt','w').write('\n'.join(out))
print(len(out))
