import tre,vm,json,collections,sys
def u16(c,p): return c[p]|c[p+1]<<8
def arg(c,p):
    v=u16(c,p);return ('#%d'%(v&0x7FFF)) if v&0x8000 else 'v%d'%v
def dump(f,full=False):
    R=tre.routines(f);by=collections.defaultdict(dict)
    for (ai,ri),a,b,o,stt,code in R: by[ai][ri]=(a,b,o,stt,code)
    for ai in sorted(by):
        has=[(ri,p) for ri,(a,b,o,stt,code) in by[ai].items() for p,k in o if k in('98','FE84','FECF','46')]
        if not has: continue
        print('actor',ai,'routines with a room change:',sorted(set(r for r,p in has)))
        for ri in sorted(by[ai]):
            a,b,o,stt,code=by[ai][ri]
            if ri!=0 and not any(r==ri for r,p in has): continue
            print('  routine',ri,stt[0])
            for i,(p,k) in enumerate(o):
                L=(o[i+1][0] if i+1<len(o) else b)-p
                print('     %04X %-5s %s'%(p,k,code[p+(2 if k.startswith('FE') else 1):p+L].hex(' ')))
if __name__=='__main__': dump(int(sys.argv[1]))
