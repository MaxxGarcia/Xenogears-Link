import scr,struct
M={0x01:'/',0x10:' ',0x12:',',0x14:'.',0x0f:'!',0x60:'?',0x5c:"'",0x02:' // '}
for i in range(26): M[0x20+i]=chr(65+i); M[0x3d+i]=chr(97+i)
def dec(b):
    s='';i=0
    while i<len(b):
        c=b[i]
        if c==0: break
        if c in M: s+=M[c]
        elif c==0x58: s+='|'
        elif c==0x57: s+=''
        else: s+='<%02X>'%c
        i+=1
    return s
def lines(f):
    d=scr.block(f,7)
    if not d or len(d)<8: return []
    try:
        n=struct.unpack_from('<I',d)[0]
        if 4+2*n>len(d): return []
    except Exception: return []
    n=struct.unpack_from('<I',d)[0]; o=list(struct.unpack_from('<%dH'%n,d,4))+[len(d)]
    return [dec(d[o[i]:o[i+1]]) for i in range(n)]
if __name__=='__main__':
    import sys
    for i,l in enumerate(lines(int(sys.argv[1]))): print(i,l)
