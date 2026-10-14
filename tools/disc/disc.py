import struct
class Disc:
    def __init__(self,path):
        self.F=open(path,'rb'); self.T=self.table()
    def sec(self,n,cnt=1):
        out=bytearray()
        for i in range(cnt):
            self.F.seek((n+i)*2352+24); out+=self.F.read(2048)
        return bytes(out)
    def table(self):
        t=self.sec(24,16); ents=[]
        for i in range(0,len(t)-7,7):
            s=t[i]|t[i+1]<<8|t[i+2]<<16; z=struct.unpack('<i',t[i+3:i+7])[0]
            if s==0xFFFFFF: break
            ents.append((s,z))
        return ents
    def get(self,i):
        s,z=self.T[i]
        if z<=0: return None
        return self.sec(s,(z+2047)//2048)[:z]
    def exe(self):
        p=self.sec(16); rl,rs=struct.unpack_from('<I',p,158)[0],struct.unpack_from('<I',p,166)[0]
        d=self.sec(rl,(rs+2047)//2048); i=0; out={}
        while i<len(d):
            L=d[i]
            if L==0: i=(i//2048+1)*2048; continue
            lba,sz=struct.unpack_from('<I',d,i+2)[0],struct.unpack_from('<I',d,i+10)[0]; nm=d[i+33:i+33+d[i+32]].decode('latin1')
            out[nm]=(lba,sz); i+=L
        return out
def lzss(d):
    n=struct.unpack('<I',d[:4])[0]; out=bytearray(); p=4
    while len(out)<n and p<len(d):
        fl=d[p]; p+=1
        for b in range(8):
            if len(out)>=n or p>=len(d): break
            if fl>>b&1:
                v=d[p]|d[p+1]<<8; p+=2; off=v&0xFFF; ln=(v>>12)+3
                for k in range(ln): out.append(out[-off] if off<=len(out) else 0)
            else: out.append(d[p]); p+=1
    return bytes(out[:n])
