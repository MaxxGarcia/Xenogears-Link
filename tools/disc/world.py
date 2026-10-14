# ==== world map tools: tim.py, wmap.py, wrender.py, mkworld.py ====

# ---- tim.py ----
import struct
from PIL import Image
def tim(b,clut_index=0):
    magic,fl=struct.unpack_from('<II',b,0); p=8; bpp=fl&7; pal=None
    if fl&8:
        ln,cx,cy,cw,ch=struct.unpack_from('<IHHHH',b,p); cl=struct.unpack_from('<%dH'%(cw*ch),b,p+12); p+=ln
        n=16 if bpp==0 else 256; base=clut_index*n
        pal=[cl[(base+i)%len(cl)] for i in range(n)]
    ln,x,y,w,h=struct.unpack_from('<IHHHH',b,p); data=b[p+12:p+ln]
    def rgb(v): return ((v&31)<<3,((v>>5)&31)<<3,((v>>10)&31)<<3,0 if v==0 else 255)
    if bpp==0:
        W=w*4;im=Image.new('RGBA',(W,h))
        px=[rgb(pal[(data[i>>1]>>((i&1)*4))&15]) for i in range(W*h)]
    elif bpp==1:
        W=w*2;im=Image.new('RGBA',(W,h));px=[rgb(pal[data[i]]) for i in range(W*h)]
    else:
        W=w;im=Image.new('RGBA',(W,h));px=[rgb(struct.unpack_from('<H',data,i*2)[0]) for i in range(W*h)]
    im.putdata(px);return im,(x,y,W,h,bpp)
if __name__=='__main__':
    import sys
    for f in (3966,3965):
        b=open('w%d.bin'%f,'rb').read()
        n=struct.unpack_from('<I',b,0)[0];o=list(struct.unpack_from('<%dI'%n,b,4))+[len(b)]
        ims=[]
        for i in range(n):
            try: im,info=tim(b[o[i]:o[i+1]]);ims.append(im);print(f,i,info)
            except Exception as e: print(f,i,'ERR',e)
        W=sum(i.width+4 for i in ims);H=max(i.height for i in ims)
        if f==3966:
            sheet=Image.new('RGBA',(1100,700),(40,40,60,255));x=y=0;rowh=0
            for im in ims:
                if x+im.width>1100: x=0;y+=rowh+4;rowh=0
                sheet.alpha_composite(im,(x,y));x+=im.width+4;rowh=max(rowh,im.height)
            sheet.save('tim3966.png')
        else:
            sheet=Image.new('RGBA',(3*260,2*260),(40,40,60,255))
            for k,im in enumerate(ims): sheet.alpha_composite(im,(k%3*260,k//3*260))
            sheet.save('tim3965.png')

# ---- wmap.py ----
import sys,struct
sys.path.insert(0,'/home/claude/xg/tools');import xg
import numpy as np
from PIL import Image
T=xg.table()
def grid(f,order=(0,1,2,3),chunk_rowmajor=True):
    raw=np.frombuffer(xg.getfile(f,T),dtype=np.uint8)
    G=np.zeros((256,256,4),dtype=np.uint8);A=np.zeros((256,256),dtype=np.uint16)
    for c in range(256):
        ch=raw[c*2048:(c+1)*2048]
        cy,cx=(c//16,c%16) if chunk_rowmajor else (c%16,c//16)
        cells=ch[:1296].reshape(4,9,9,4)
        for s in range(4):
            sy,sx=divmod(order[s],2)
            G[cy*16+sy*8:cy*16+sy*8+8,cx*16+sx*8:cx*16+sx*8+8]=cells[s,:8,:8]
        A[cy*16:cy*16+16,cx*16:cx*16+16]=np.frombuffer(ch[1296:1808].tobytes(),dtype='<u2').reshape(16,16)
    return G,A
if __name__=='__main__':
    out=Image.new('RGB',(4*260,2*260),(40,40,60))
    k=0
    for rm in (True,False):
        for order in ((0,1,2,3),(0,2,1,3)):
            G,A=grid(3972,order,rm)
            out.paste(Image.fromarray(np.clip(G[:,:,0].astype(int)*3,0,255).astype(np.uint8)),(k*260,0))
            out.paste(Image.fromarray((A>>4).astype(np.uint8)*8),(k*260,260));k+=1
    out.save('wgrid.png')
    import collections
    G,A=grid(3972);print(collections.Counter(A.flatten().tolist()).most_common(12))
    print(collections.Counter(zip(G[:,:,1].flatten().tolist(),G[:,:,3].flatten().tolist())).most_common(20))

# ---- wrender.py ----
import struct,sys
import numpy as np
from PIL import Image
import wmap,tim
def pages(path='w3965.bin'):
    b=open(path,'rb').read();n=struct.unpack_from('<I',b,0)[0];o=list(struct.unpack_from('<%dI'%n,b,4))+[len(b)]
    return [np.array(tim.tim(b[o[i]:o[i+1]])[0].convert('RGB')) for i in range(n)]
PMAP={0:0,1:1,2:2,11:3,12:4,13:5}
def render(f,px=8,pmap=PMAP,P=None):
    G,A=wmap.grid(f);P=P or pages()
    out=np.zeros((256*px,256*px,3),dtype=np.uint8);step=16//px
    for y in range(256):
        for x in range(256):
            h,b1,t,b3=[int(q) for q in G[y,x]]
            pg=pmap.get(b1&15)
            if pg is None: out[y*px:(y+1)*px,x*px:(x+1)*px]=(255,0,255);continue
            u=(t&15)*16;v=(t>>4)*16
            tile=P[pg][v:v+16,u:u+16]
            if step>1: tile=tile.reshape(px,step,px,step,3).mean(axis=(1,3)).astype(np.uint8)
            out[y*px:(y+1)*px,x*px:(x+1)*px]=tile
    return out,G,A
if __name__=='__main__':
    out,G,A=render(int(sys.argv[1]) if len(sys.argv)>1 else 3972,4)
    Image.fromarray(out).save('world4.png');print(out.shape)

# ---- mkworld.py ----
# world map assets: top-down render of the terrain grid for the normal world (a) and the late-game world (b),
# plus per-chunk checksums so the app can tell which one the game has loaded
import sys,os,json
sys.path.insert(0,'/home/claude/xg/tools');import xg
import numpy as np
from PIL import Image
import wrender,wmap
T=xg.table();OUT='/home/claude/xg/v/www/world';os.makedirs(OUT,exist_ok=True)
P=wrender.pages()
for name,f in (('a',3983),('b',4060)):
    o,G,A=wrender.render(f,4,P=P)
    im=Image.fromarray(o).quantize(colors=192,method=Image.MEDIANCUT,dither=Image.NONE)
    im.save(os.path.join(OUT,name+'.png'),optimize=True);print(name,os.path.getsize(os.path.join(OUT,name+'.png')))
def ck(b):
    s=0
    for v in b: s=(s*31+v)&0xFFFFFF
    return s
SETS={'a':[0,1,2,3,4,5,6,7,11,12,13,14],'b':[8,15,16]}
sig={}
for name,sets in SETS.items():
    per=[set() for _ in range(256)]
    for s in sets:
        for k in (9,10):
            raw=xg.getfile(3963+11*s+k,T)
            for c in range(256): per[c].add(ck(raw[c*2048:c*2048+1296]))
    sig[name]=[sorted(x) for x in per]
both=sum(1 for c in range(256) if set(sig['a'][c])&set(sig['b'][c]));print('chunks ambiguous',both,'of 256')
open('/home/claude/xg/v/www/world.js','w').write("/* world map: per 2048-unit chunk (16 x 16 of them, row = z), checksums of the first 1296 bytes (the four 9 x 9 blocks) of the chunk's terrain data\n   for the normal world (a) and the late-game world (b); the app compares the chunk under the player to choose the picture */\nwindow.WSIG="+json.dumps(sig,separators=(',',':'))+";\n")
print(os.path.getsize('/home/claude/xg/v/www/world.js'))
