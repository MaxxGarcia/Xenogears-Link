import tre,surv,dlg,json,re,collections
S=json.load(open('story_sets.json'));N=json.load(open('hint_notes.json'))
AR=json.loads(re.search(r'window.AREAS=(\[.*?\]);',open('/home/claude/xg/v/www/areas.js').read()).group(1))
def area(r):
    for a in AR:
        if a[0]<=r<=a[1]: return a[2]
    return '?'
RC={};LC={}
def R(f):
    if f not in RC:
        d={}
        for own,a,b,o,stt,code in tre.routines(f): d.setdefault(own,list(surv.ins(o,b,code)))
        RC[f]=d
    return RC[f]
def L(f):
    if f not in LC: LC[f]=dlg.lines(f)
    return LC[f]
def line(f,k,arg):
    l=L(f);i=None
    if k=='D2' and len(arg)>=1: i=arg[0]|(arg[1]<<8 if len(arg)>1 else 0)
    if k in('FC','D4') and len(arg)>=3: i=arg[1]|arg[2]<<8
    if i is not None and i<len(l): return l[i].replace('/|',': ').replace('/',' ').replace('|','')[:110]
# flag setters index (FE0A), var setters (35/36/3A), item gives (8C)
FS=collections.defaultdict(list)
for f in range(720):
    for own,ins in R(f).items():
        for p,k,arg in ins:
            if k=='FE0A' and len(arg)>=2: FS[arg[0]|arg[1]<<8].append((f,own,p))
def callers(f,own):
    out=[]
    for o2,ins in R(f).items():
        for p,k,arg in ins:
            if k in('07','08','09') and len(arg)>=2 and (arg[0],arg[1]&0x1f)==own: out.append(o2)
    return out
def ctx(f,own,p,n=3):
    ins=R(f)[own];i=[q for q,(pp,k,a) in enumerate(ins) if pp==p][0];ls=[]
    for pp,k,a in ins[max(0,i-25):i+8]:
        t=line(f,k,a)
        if t and t.strip(' !.'): ls.append(t)
    return ls[-n:]
def path_before(ins,p87):
    """conditions and dialogue in the routine before the set"""
    cond=[];txt=[]
    for p,k,a in ins:
        if p>=p87: break
        if k=='FB' and len(a)>=2: cond.append('flag %03X'%(a[0]|a[1]<<8))
        if k=='8B' and len(a)>=2: cond.append('item %04X'%(a[0]|a[1]<<8))
        if k=='02' and len(a)>=5: cond.append('var %03X ? %d'%(a[0]|a[1]<<8,a[2]|a[3]<<8))
        t=line(ins and f0,k,a) if False else None
    return cond
out=[]
for n in sorted(N,key=int):
    out.append('\n### %s  now: %s'%(n,N[n][1:]))
    for f,a,r in S[n]:
        if f>=720: continue
        global f0
        ins=R(f).get((a,r),[]);p87=[p for p,k,x in ins if k=='87' and len(x)>=2 and ((x[0]|x[1]<<8)&0x7fff)==int(n)]
        if not p87: continue
        p87=p87[0];ch=[(a,r)];c=(a,r);seen=set()
        while True:
            cs=[x for x in callers(f,c) if x not in seen]
            if not cs: break
            c=cs[0];seen.add(c);ch.append(c)
        out.append(' room %d %s: %s'%(f,area(f),' <- '.join('a%d r%d'%x for x in ch)))
        conds=set()
        for o2 in ch:
            for p,k,x in R(f)[o2]:
                if o2==(a,r) and p>=p87: break
                if k=='FB' and len(x)>=2: conds.add(x[0]|x[1]<<8)
        txt=[]
        for p,k,x in ins:
            if p>p87: break
            t=line(f,k,x)
            if t and t.strip(' !.'): txt.append(t)
        for t in txt[-4:]: out.append('   says: '+t)
        for fl in sorted(conds):
            st=FS.get(fl,[])
            out.append('   needs flag %03X (set in %s)'%(fl,', '.join('%d %s'%(s[0],area(s[0])) for s in st[:3]) or '?'))
            for s in st[:2]:
                for t in ctx(*s): out.append('      .. '+t)
open('/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/digest.txt','w').write('\n'.join(out))
print(len(out))
