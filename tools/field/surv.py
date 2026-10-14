import sys;sys.path.insert(0,'/home/claude/xg/fld')
import tre
def ins(o,b,code):
    for i,(p,k) in enumerate(o):
        L=(o[i+1][0] if i+1<len(o) else b)-p
        yield p,k,code[p+(2 if k.startswith('FE') else 1):p+L]
def show(f):
    R=tre.routines(f); vars_=set()
    for own,a,b,o,stt,code in R:
        for p,k,arg in ins(o,b,code):
            if k=='8C' and not arg[1]&0x80: vars_.add(bytes(arg[:2]))
    print('=== room',f,'item vars',[v.hex() for v in vars_])
    for own,a,b,o,stt,code in R:
        lines=[]
        for p,k,arg in ins(o,b,code):
            if k in('8C','FB','FE0A','FE0B','8B','8F') or (k in('35','36','37') and bytes(arg[:2]) in vars_) or (k in('35',) and arg[:2] in(b'\x3c\x04',)):
                lines.append('   %04X %-5s %s'%(p,k,arg.hex(' ')))
        if any(' 8C ' in l or ' 35 ' in l or ' 8F ' in l for l in lines):
            print(' actor',own,'@%04X'%a,stt[0]); print('\n'.join(lines))
if __name__=="__main__":
    for f in map(int,sys.argv[1:]): show(f)
