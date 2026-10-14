import sys;sys.path.insert(0,'/home/claude/xg/tools')
import xg,struct
T=xg.table()
f=int(sys.argv[1]); t=xg.getfile(607+2*f,T)
for p in range(0,len(t),0x800):
    w=struct.unpack_from('<I',t,p)[0]
    if w in(0x1100,0x1101,0x1200,0x1201) or p==0:
        print(hex(p),t[p:p+48].hex(' ',2))
