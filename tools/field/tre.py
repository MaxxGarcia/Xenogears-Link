import vm,json,struct,collections,sys
vm.LEN.update(json.load(open('len.json')))
def routines(f):
    r=vm.load(f)
    if not r: return []
    s,n,ent,code=r; st=sorted(set(e for a in ent for e in a))+[len(code)]; out=[]
    owner={}
    for ai,a in enumerate(ent):
        for ri,e in enumerate(a): owner.setdefault(e,(ai,ri))
    for a,b in zip(st,st[1:]):
        o,stt=vm.sweep(code,a,b); out.append((owner[a],a,b,o,stt,code))
    return out
def u16(code,p): return code[p]|code[p+1]<<8
if __name__=='__main__':
    f=int(sys.argv[1])
    for (ai,ri),a,b,o,stt,code in routines(f):
        if any(k=='8C' for p,k in o):
            print('actor',ai,'routine',ri,hex(a),hex(b),stt[0])
            for i,(p,k) in enumerate(o):
                L=(o[i+1][0] if i+1<len(o) else b)-p
                print('   %04X %-5s %s'%(p,k,code[p+ (2 if k.startswith('FE') else 1):p+L].hex(' ')))
