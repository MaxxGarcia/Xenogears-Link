# Trims every room picture to the walkable area plus a margin (the way KH 2 Link's map art was trimmed).
# Reads the untrimmed pictures kept in /home/claude/xg/plan_full, writes v/www/plan. Usage: trim_plan.py [margin%] [rooms...]
# Mask = the room's walk-mesh triangles drawn into the picture (PLAN: centre x, centre z, width; x right, z down), blocked
# triangles left out; closed (bites and gaps up to about 28% of the longer side filled), grown by the margin (10% of the
# walkable area's longer side, 11 to 67 pixels) and given a soft edge.
import sys,json,base64,struct,os,re,numpy as np
from PIL import Image,ImageDraw,ImageFilter
W='/home/claude/xg/v/www/'; SRC='/home/claude/xg/plan_full/'
PLAN=json.loads(open(W+'plan.js').read().split('=',1)[1].rstrip().rstrip(';'))
CLOSE=14
def mesh(f):
    p=W+'maps/%d.js'%f
    if not os.path.exists(p): return None
    m=re.search(r'"([A-Za-z0-9+/=]+)"',open(p).read())
    if not m: return None
    b=base64.b64decode(m.group(1)); nv,nt=struct.unpack_from('<HH',b,0)
    v=np.frombuffer(b,'<i2',nv*2,4).reshape(nv,2).astype(np.float64); o=4+nv*4
    t=np.array([struct.unpack_from('<HHHB',b,o+7*i) for i in range(nt)])
    return v,t
def mask(f,size,pct):
    mt=mesh(f)
    if mt is None or not len(mt[1]): return None
    v,t=mt; cx,cz,w=PLAN[str(f)]; S=4; n=size//S*S
    px=((v-[cx,cz])/w+0.5)*size
    im=Image.new('L',(size,size),0); d=ImageDraw.Draw(im)
    walk=[r for r in t if r[3]&3!=2] or list(t)   # triangles marked blocked are left out, unless the room has no others
    for a,b,c,fl in walk: d.polygon([tuple(px[a]),tuple(px[b]),tuple(px[c])],fill=255,outline=255)
    wi=np.unique(np.array(walk)[:,:3]); ext=max(np.ptp(px[wi,0]),np.ptp(px[wi,1])); mg=int(max(11,min(67,ext*pct/100)))
    from scipy import ndimage
    core=np.asarray(im)>0
    # close the shape first: bites and gaps narrower than 2 x R (R = CLOSE% of the longer side) are filled, so furniture, pits and
    # other blocked patches inside a room, and the ground between two walkable parts, stay in the picture
    R=ext*CLOSE/100
    if R>=2:
        pad=int(R)+2; big=np.pad(core,pad)
        grown=ndimage.distance_transform_edt(~big)<=R
        core=core|(ndimage.distance_transform_edt(grown)>R)[pad:-pad,pad:-pad]
    dist=ndimage.distance_transform_edt(~core)          # distance from the kept area, in pixels
    g=Image.fromarray(((dist<=mg)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(2,mg/4)))
    return np.asarray(g).astype(np.float32),mg
def one(f,pct):
    a=Image.open(SRC+'%d.webp'%f).convert('RGBA'); r=mask(f,a.size[0],pct)
    if r is None: return None
    m,mg=r; A0=np.asarray(a.getchannel('A'))>40
    if (A0&(m*1.6>128)).sum()<0.05*max(A0.sum(),1): return a,0   # the mask misses the picture (rooms 478, 246, 101): left untrimmed
    al=np.minimum(np.asarray(a.getchannel('A')).astype(np.float32),np.clip(m*1.6,0,255))
    px=np.asarray(a).copy(); px[...,3]=al.astype(np.uint8); px[al<1,:3]=0
    return Image.fromarray(px,'RGBA'),mg
def job(f,pct):
    r=one(f,pct)
    if r is None: return 0
    dst=W+'plan/%d.webp'%f; r[0].save(dst,'WEBP',quality=75,method=6,alpha_quality=90); return os.path.getsize(dst)
if __name__=='__main__':
    pct=float(sys.argv[1]) if len(sys.argv)>1 else 10
    rooms=[int(x) for x in sys.argv[2:]] or sorted(int(x[:-5]) for x in os.listdir(SRC))
    import multiprocessing as mp
    with mp.Pool(max(1,mp.cpu_count())) as pool: res=pool.starmap(job,[(f,pct) for f in rooms])
    print(len(rooms),'rooms, no mesh:',sum(1 for x in res if not x),'total',sum(res)//1024,'KB')
