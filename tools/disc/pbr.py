import sys,struct
import spr2
from PIL import Image
def load(f):
    d=spr2.getf(f); A=spr2.arch(d); return A
def frames(s1):
    n=s1[0]; offs=struct.unpack_from('<%dH'%n,s1,2); out=[]
    for o in offs:
        nt=s1[o]&0x3f; hdr=s1[o:o+6]
        prs=[struct.unpack_from('<HH',s1,o+6+4*k) for k in range(nt)]
        p=o+6+4*nt; pl=[]
        for a,b in prs:
            ctl=[]
            while s1[p]>=0xC0:
                if s1[p]>=0xE0: ctl.append(s1[p:p+3]); p+=3
                else: ctl.append(s1[p:p+1]); p+=1
            fl=s1[p]; x,y=struct.unpack_from('<bb',s1,p+1); p+=3
            pl.append((a,b,fl,x,y,ctl))
        out.append((hdr,pl))
    return out
def render(A,fi,flip=(0x10,0x20),order=-1):
    s1=A[1]; a,P=spr2.pals(A[2]); hdr,pl=frames(s1)[fi]; px={}
    for t,b,fl,x,y,ctl in pl[::order]:
        w,h=s1[t*4],s1[t*4+1]; data=s1[t*4+4:]; pal=P[min(fl&0x0F,len(P)-1)]; rw=(w+1)//2
        rw=(rw+3)&~3 if False else rw
        for yy in range(h):
            for xx in range(w):
                byte=data[yy*rw+(xx>>1)]; c=(byte>>4) if xx&1 else (byte&15)
                if c==0: continue
                dx=(w-1-xx) if fl&flip[0] else xx; dy=(h-1-yy) if fl&flip[1] else yy
                px[(x+dx,y+dy)]=pal[c][:3]+(255,)
    if not px: return None
    xs=[p[0] for p in px];ys=[p[1] for p in px]
    x0,y0=min(xs),min(ys); im=Image.new('RGBA',(max(xs)-x0+1,max(ys)-y0+1))
    for (x,y),c in px.items(): im.putpixel((x-x0,y-y0),c)
    return im,(x0,y0)
if __name__=='__main__':
    f=int(sys.argv[1]); A=load(f); fr=frames(A[1]); n=len(fr)
    cols=16; cell=96; sheet=Image.new('RGBA',(cols*cell,((n+cols-1)//cols)*cell),(40,40,60,255))
    for i in range(n):
        try: r=render(A,i)
        except Exception as e: print(i,e); r=None
        if r: 
            im=r[0]; sheet.alpha_composite(im.crop((0,0,min(im.width,cell),min(im.height,cell))),((i%cols)*cell+2,(i//cols)*cell+2))
    sheet.save('pb_%d.png'%f); print(n,sheet.size)
