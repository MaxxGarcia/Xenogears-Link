import dlg,tre,surv,json,re,sys
N=json.load(open('hint_notes.json')); S=json.load(open('story_sets.json'))
AR=json.loads(re.search(r'window.AREAS=(\[.*?\]);',open('/home/claude/xg/v/www/areas.js').read()).group(1))
def area(r):
    for a in AR:
        if a[0]<=r<=a[1]: return a[2]
    return '?'
out=[]
for n in sorted(N,key=int):
    if not N[n].startswith('?'): continue
    out.append('\n### step %s  (now: %s)'%(n,N[n][1:]))
    for f,a,r in S[n]:
        if f>=720: continue
        L=dlg.lines(f); out.append('room %d %s actor %d routine %d'%(f,area(f),a,r))
        for own,a0,b,o,stt,code in tre.routines(f):
            if own!=(a,r): continue
            ins=list(surv.ins(o,b,code)); txt=[]
            for p,k,arg in ins:
                if k=='D2' and arg[0]<len(L): txt.append(L[arg[0]])
                if k=='87' and len(arg)>=2 and arg[1]&0x80 and ((arg[0]|arg[1]<<8)&0x7fff)==int(n): txt.append('<<SET %s>>'%n)
            if len(txt)>14: txt=txt[:7]+['...']+txt[-7:]
            for t in txt: out.append('   '+t[:110])
        if len(L)==0: out.append('   (no dialogue in room)')
open('/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/ctx.txt','w').write('\n'.join(out))
print(len(out))
