import sys,os,rt,traceback
from multiprocessing import Pool
def init():
    import xg; xg.F=open('/home/claude/xg/disc/d1.bin','rb')
def one(f):
    out='master/%d.png'%f
    if os.path.exists(out): return f,'have'
    try:
        im=rt.room(f,1024)
        if im is None: return f,'none'
        im.save(out); return f,'ok'
    except Exception as e:
        return f,'ERR '+repr(e)[:120]
if __name__=='__main__':
    ids=sorted(int(k) for k in rt.PLAN)
    with Pool(os.cpu_count(),initializer=init) as p:
        res=p.map(one,ids,chunksize=4)
    bad=[r for r in res if r[1] not in('ok','have')]
    print(len(res),'rooms',len(bad),'bad',bad[:20])
