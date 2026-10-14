import sys,json,struct,collections
sys.path.insert(0,'/home/claude/xg/tools')
import xg
T=xg.table(); E=json.load(open('enemies.json'))
def bankfile(k):
    d=xg.getfile(2618+2*k,T)
    if not d or struct.unpack_from('<H',d,0)[0]!=0x0BB2: return None
    return d
def sig(d,o1,o2):
    return [[struct.unpack_from('<H',d,0x32+0x170*i+o1)[0],struct.unpack_from('<I',d,0x32+0x170*i+o2)[0]] for i in range(8)]
FILE2E={}
if __name__=='__main__':
    esig={json.dumps(e['h']):i for i,e in enumerate(E)}
    for o1 in (0x4E,0x4C):
        for o2 in (0x108,0x104):
            hit=0
            for k in range(80):
                d=bankfile(k)
                if d and json.dumps(sig(d,o1,o2)) in esig: hit+=1
            print(hex(o1),hex(o2),hit)
def filemap():
    esig={json.dumps(e['h']):i for i,e in enumerate(E)}; m={}
    for k in range(80):
        d=bankfile(k)
        if d: m[k]=esig.get(json.dumps(sig(d,0x4E,0x108)))
    return m
def enc(f):
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154])
    if not o[6]<o[7]<=len(h): return None
    d=xg.lzss(h[o[6]:o[7]]); return d if len(d)>=0x210 else None
