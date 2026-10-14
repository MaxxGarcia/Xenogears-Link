import digest as D
S=sorted(int(k) for k in D.N)
out=[]
for i,s in enumerate(S[1:],1):
    P=S[i-1];got=[]
    for f in range(720):
        for own,ins in D.R(f).items():
            if own[1] not in (2,3): continue   # talk / touch
            blk=None
            for j,(p,k,a) in enumerate(ins):
                if k in('84','85','86','88') and len(a)>=4:
                    n=(a[0]|a[1]<<8)&0x7fff
                    # block that runs when step == P: 86 P, or 84 n with P < n <= s (runs if step < n) right after an earlier test excluding lower
                    if k=='86' and n==P: blk=j;break
            if blk is None: continue
            ls=[]
            for p,k,a in ins[blk+1:blk+40]:
                if k in('84','85','86','88','00'): break
                t=D.line(f,k,a)
                if t and t.strip(' !.?'): ls.append(t)
            if ls: got.append('  room %d %s a%d: %s'%(f,D.area(f),own[0],' | '.join(ls[:3])[:260]))
    if got:
        out.append('### %d (at step %d)  now: %s'%(s,P,D.N[str(s)].lstrip('?')));out+=got[:8]
open('/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/win2.txt','w').write('\n'.join(out));print(len(out))
