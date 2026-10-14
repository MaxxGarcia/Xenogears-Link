import dlg,json,re,collections
N=json.load(open('hint_notes.json')); S=json.load(open('story_sets.json'))
AR=json.loads(re.search(r'window.AREAS=(\[.*?\]);',open('/home/claude/xg/v/www/areas.js').read()).group(1))
def area(r):
    for a in AR:
        if a[0]<=r<=a[1]: return a[2]
    return '?'
out=[]
for n in sorted(N,key=int):
    if not N[n].startswith('?'): continue
    out.append('\n### %s (%s)'%(n,N[n][1:]))
    seen=set()
    for f,a,r in S[n]:
        if f>=720 or f in seen: continue
        seen.add(f); L=dlg.lines(f)
        sp=collections.Counter(l.split('/')[0] for l in L if '/|' in l)
        out.append('room %d %s: %d lines; speakers %s'%(f,area(f),len(L),', '.join('%s x%d'%kv for kv in sp.most_common(6))))
        for l in L[:10]: out.append('   '+l.replace('/|',': ').replace('/',' ')[:120])
open('/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/ctx2.txt','w').write('\n'.join(out))
print(len(out))
