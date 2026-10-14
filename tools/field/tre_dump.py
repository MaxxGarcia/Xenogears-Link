import sys,json,collections
sys.path.insert(0,'/home/claude/xg/fld')
import tre,surv,chest,vm
OUT={}; enc={}
for f in range(730):
    L=[t for t in chest.room(f) if t['flag']]
    if L: OUT[f]=sorted([[t['flag'][0],t['flag'][1],t['k'],t['v']] for t in L])
    # random battle window set by the room (script command F7)
    for own,a,b,o,stt,code in tre.routines(f):
        for p,k,arg in surv.ins(o,b,code):
            if k=='F7' and len(arg)>=4: enc.setdefault(f,[]).append([arg[0]|arg[1]<<8,arg[2]|arg[3]<<8])
json.dump({'t':OUT,'e':enc},open(sys.argv[1],'w'))
st=collections.Counter()
r=vm.load(1)
print('rooms with treasure',len(OUT),'entries',sum(len(v) for v in OUT.values()),'rooms setting battle window',len(enc))
