import struct
import os
F=open(os.environ.get('XG_DISC','/home/claude/xg/disc/d1.bin'),'rb')
def sec(n,cnt=1):
    out=bytearray()
    for i in range(cnt):
        F.seek((n+i)*2352+24); out+=F.read(2048)
    return bytes(out)
def table():
    t=sec(24,16); ents=[]
    for i in range(0,len(t)-7,7):
        s=t[i]|t[i+1]<<8|t[i+2]<<16; z=struct.unpack('<i',t[i+3:i+7])[0]
        if s==0xFFFFFF: break
        ents.append((s,z))
    return ents
def getfile(i,T=None):
    T=T or table(); s,z=T[i]
    if z<=0: return None
    return sec(s,(z+2047)//2048)[:z]
def lzss(d):
    n=struct.unpack('<I',d[:4])[0]; out=bytearray(); p=4
    while len(out)<n and p<len(d):
        fl=d[p]; p+=1
        for b in range(8):
            if len(out)>=n or p>=len(d): break
            if fl>>b&1:
                v=d[p]|d[p+1]<<8; p+=2
                off=v&0xFFF; ln=(v>>12)+3
                for k in range(ln): out.append(out[-off] if off<=len(out) else 0)
            else: out.append(d[p]); p+=1
    return bytes(out[:n])
