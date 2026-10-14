import digest as D,collections
S=sorted(int(k) for k in D.N)
B=collections.defaultdict(list)   # story value -> lines from ==value blocks in talk routines
for f in range(720):
    for own,ins in D.R(f).items():
        if own[1] not in (2,3): continue
        for j,(p,k,a) in enumerate(ins):
            if k=='86' and len(a)>=2:
                n=(a[0]|a[1]<<8)&0x7fff;ls=[]
                for p2,k2,a2 in ins[j+1:j+30]:
                    if k2 in('84','85','86','88','00'): break
                    t=D.line(f,k2,a2)
                    if t and len(t.strip(' !.?'))>12: ls.append(t)
                if ls: B[n].append((f,own[0],ls[0]))
out=[]
for i,s in enumerate(S[1:],1):
    P=S[i-1]
    if B[P]:
        out.append('### %d (at %d) now: %s'%(s,P,D.N[str(s)].lstrip('?')))
        seen=set()
        for f,a,l in B[P]:
            if l in seen: continue
            seen.add(l);out.append('  %d %s a%d: %s'%(f,D.area(f),a,l[:200]))
open('/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/win3.txt','w').write('\n'.join(out));print(len(out))
