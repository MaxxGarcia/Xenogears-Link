import sys,struct,json,collections
import scr
OT=json.load(open('/home/claude/xg/fld/optable.json'))
LEN={}
for k,(a,pick,res) in OT.items():
    if pick: LEN[k]=pick+(1 if k.startswith('FE') else 0)
MAN={'00':1,'01':3,'04':1,'0D':1,'92':1,'5B':1,'A6':1,'D1':1,'E4':1}
LEN.update(MAN)
def load(f):
    s=scr.block(f,5)
    if not s or len(s)<0x88: return None
    n=struct.unpack_from('<I',s,0x80)[0]
    if not 0<n<400 or 0x84+n*64>len(s): return None
    ent=[struct.unpack_from('<32H',s,0x84+i*64) for i in range(n)]
    return s,n,ent,s[0x84+n*64:]
def opkey(code,p):
    if code[p]==0xFE and p+1<len(code): return 'FE%02X'%code[p+1]
    return '%02X'%code[p]
def sweep(code,start,end,LEN=LEN):
    """linear decode; returns list of (offset,key) and where/why it stopped"""
    p=start; out=[]
    while p<end:
        k=opkey(code,p); L=LEN.get(k)
        if L is None: return out,('unknown',k,p)
        out.append((p,k)); p+=L
    return out,('ok' if p==end else 'overrun',None,p)
if __name__=='__main__':
    stat=collections.Counter(); unk=collections.Counter(); rooms=0
    for f in range(730):
        r=load(f)
        if not r: continue
        s,n,ent,code=r; rooms+=1
        starts=sorted(set(e for a in ent for e in a))+[len(code)]
        for a,b in zip(starts,starts[1:]):
            o,(st,k,p)=sweep(code,a,b); stat[st]+=1
            if st=='unknown': unk[k]+=1
    print(rooms,dict(stat)); print(unk.most_common(30))
