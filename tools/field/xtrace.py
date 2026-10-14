import tre,surv,dlg,sys,json
REQ=('07','08','09')
def room(f):
    R={};calls={}
    for own,a,b,o,stt,code in tre.routines(f):
        ins=list(surv.ins(o,b,code)); R.setdefault(own,ins)
        for p,k,arg in ins:
            if k in REQ and len(arg)>=2: calls.setdefault((arg[0],arg[1]&0x1f),[]).append((own,p))
    return R,calls
def show(f,own,L,mark=None,lim=80):
    R,_=room(f); out=[]
    for p,k,arg in R.get(own,[]):
        t=''
        if k=='D2' and arg[0]<len(L): t=L[arg[0]][:90]
        if k in ('02','FB','8B','84','85','86','88','87','07','08','09','8C','35','36','37','3A','FE0A','98','47','71','D2','FE55','FE59','FE5A','01'):
            out.append('    %04X %-5s %-26s %s'%(p,k,arg.hex(' ')[:26],t))
    return out[:lim]
def chain(f,own,depth=0,seen=None):
    seen=seen or set();R,calls=room(f);out=[]
    if own in seen or depth>4: return out
    seen.add(own)
    for c,p in calls.get(own,[]):
        out.append('  '*depth+'  <- started by actor %d routine %d @%04X'%(c[0],c[1],p))
        out+=chain(f,c,depth+1,seen)
    return out
if __name__=='__main__':
    f,a,r=map(int,sys.argv[1:4]);L=dlg.lines(f)
    print('room',f,'actor',a,'routine',r)
    print('\n'.join(chain(f,(a,r))))
