import sys,struct,json,collections
sys.path.insert(0,'/home/claude/xg/tools')
import disc
A=disc.Disc('/home/claude/xg/disc/d1.bin'); B=disc.Disc('/home/claude/xg/pw/Xenogears_PW_CD1.bin')
NAMES=['textures?','walkmesh','models','sprites','sprite sheets','scripts','battle line-ups','dialogue','triggers']
ch=collections.Counter(); rooms=0; hdr=0; ex=collections.defaultdict(list)
for f in range(730):
    a=A.get(606+2*f); b=B.get(606+2*f)
    if a is None or b is None: continue
    rooms+=1
    if a==b: continue
    oa=struct.unpack('<9I',a[0x130:0x154])+(len(a),); ob=struct.unpack('<9I',b[0x130:0x154])+(len(b),)
    if a[0x154:oa[0]]!=b[0x154:ob[0]]: hdr+=1
    for i in range(9):
        if a[oa[i]:oa[i+1]]!=b[ob[i]:ob[i+1]]:
            ch[NAMES[i]]+=1; ex[NAMES[i]].append(f)
    ta=A.get(607+2*f); tb=B.get(607+2*f)
    if ta!=tb: ch['texture file']+=1; ex['texture file'].append(f)
print('rooms',rooms,'changed blocks:',dict(ch),'entity/header area changed in',hdr)
for k,v in ex.items():
    if k!='dialogue': print(' ',k,len(v),v[:30])
