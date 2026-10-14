# Shop stock tables: disc file 2593 (menu directory, the game's file 1) sub-files 6 (item shops, 40 x 92 bytes) and 7 (gear shops, 30 x 100 bytes).
# Names come from the app's tables; prices from disc file 2594. Rooms come from the room scripts (FE59 n = item shop n, FE5A n = gear shop n).
import json,pickle,struct,collections,sys
sys.path.insert(0,'/home/claude/xg/tools');import xg
N=json.load(open('/home/claude/xg/menu/names.json'));T=N['T'];G=N['G'];A=N['A']
TB=xg.table()
def pack(i):
    f=xg.getfile(i,TB);n=struct.unpack('<I',f[:4])[0];o=struct.unpack('<%dI'%(n+1),f[4:8+4*n]);return [xg.lzss(f[o[k]:o[k+1]]) for k in range(n)]
subs=pack(2594);P=pack(2593);d=P[6];g=P[7]
def price(sub,rec,off,i):
    return struct.unpack_from('<H',subs[sub],i*rec+off)[0] if i*rec+off+2<=len(subs[sub]) else None
def area(f):
    for a in A:
        if a[0]<=f<=a[1]: return a[2]
R=pickle.load(open('/home/claude/xg/fld/allr.pkl','rb'))
def u16(c,p): return c[p]|c[p+1]<<8
use={'FE59':collections.defaultdict(set),'FE5A':collections.defaultdict(set)}
for f in sorted(R):
    for (ai,ri),a,b,o,stt,code in R[f]:
        for p,k in o:
            if k in use and p+4<=len(code):
                v=u16(code,p+2)
                if v&0x8000: use[k][v&0x7FFF].add(f)
def build(data,n,rec,per,cats,key):
    out={}
    for s in range(n):
        r={}
        for c,(nm,tab,sub,rs,po) in enumerate(cats):
            l=[v for v in data[s*rec+c*per:s*rec+c*per+per] if v]
            if l: r[nm]=[[v,tab[v].strip() if v<len(tab) else '?',price(sub,rs,po,v)] for v in l]
        if r or s in use[key]:
            rooms=sorted(use[key].get(s,[]));r['rooms']=rooms;r['areas']=sorted(set(filter(None,(area(f) for f in rooms if 0<f<719))));out[s]=r
    return out
out={'item_shops':build(d,40,92,30,[('weapons',T['weapons'],1,16,4),('equipment',T['equipment'],2,16,2),('items',T['items'],0,16,2)],'FE59'),
     'gear_shops':build(g,30,100,20,[('frames',G['gear_frames'],16,24,0xA),('armor',G['gear_armor'],17,20,4),('engines',G['gear_engines'],18,16,0xA),('weapons',T['gear_weapons'],42,20,8),('parts',T['gear_parts'],19,28,4)],'FE5A')}
json.dump(out,open('/home/claude/xg/menu/shops.json','w'),separators=(',',':'))
if __name__=='__main__':
    for k in out:
        print('==',k,len(out[k]))
        for s,r in out[k].items():
            print(s,r['areas'],r['rooms'],{c:' | '.join('%s %s'%(x[1],x[2]) for x in v) for c,v in r.items() if c not in('rooms','areas')})
