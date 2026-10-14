import sys,struct
sys.path.insert(0,'/home/claude/xg/tools')
import xg
T=xg.table()
def block(f,i):
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154])+(len(h),)
    if not o[i]<o[i+1]<=len(h): return None
    return xg.lzss(h[o[i]:o[i+1]])
if __name__=='__main__':
    f=int(sys.argv[1]); s=block(f,5); print(len(s)); print(s[:0x100].hex(' ',2))
