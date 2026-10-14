import sys;sys.path.insert(0,'/home/claude/xg/tools');sys.path.insert(0,'.')
import xg,struct,collections
T=xg.table()
f=int(sys.argv[1])
h=xg.getfile(606+2*f,T); t=xg.getfile(607+2*f,T)
print('even',len(h),'odd',len(t))
print('hdr 0x100..0x190',h[0x100:0x190].hex(' ',4))
print('odd head',t[:64].hex(' ',4))
o=struct.unpack('<9I',h[0x130:0x154]); md=xg.lzss(h[o[2]:o[3]])
n=struct.unpack('<I',md[:4])[0]; offs=list(struct.unpack('<%dI'%n,md[4:4+4*n]))+[len(md)]
c=collections.Counter()
for i in range(n):
    s=md[offs[i]:offs[i+1]]
    if len(s)>=4: c[struct.unpack('<I',s[:4])[0]]+=1
print('models',n,'part counts',c.most_common(8))
