import os,sys,numpy as np
from PIL import Image
OLD='/home/claude/xg/plan_old/%d.png'
def load(f,size=512):
    a=np.asarray(Image.open('master/%d.png'%f).convert('RGBA')).astype(np.float32)
    v=a[...,3]>0
    if not v.any(): return None,0,0,1
    lum=a[...,:3].mean(-1)[v]; p95=float(np.percentile(lum,95)); g=1.0
    if p95<100: g=min(3.0,100/max(p95,1))
    a[...,:3]=np.clip(a[...,:3]*g,0,255)
    a[...,:3]*=a[...,3:]/255
    s=np.asarray(Image.fromarray(a.astype(np.uint8),'RGBA').resize((size,size),Image.LANCZOS)).astype(np.float32)
    al=s[...,3:]; rgb=np.where(al>0,s[...,:3]*255/np.maximum(al,1),0)
    out=np.dstack([np.clip(rgb,0,255),al[...,0]]).astype(np.uint8)
    return Image.fromarray(out,'RGBA'),float(v.mean()),p95,g
def final(f,size=512):
    """textured picture; where it has nothing, the old shaded picture shows through dimmed so no part of the room is lost"""
    im,cov,p95,g=load(f,size)
    o=np.asarray(Image.open(OLD%f).convert('RGBA').resize((size,size),Image.BILINEAR)).astype(np.float32)
    l=o[...,:3].mean(-1,keepdims=True)*0.30
    under=np.dstack([l*0.92,l*0.96,l*1.12,o[...,3:]])
    if im is None: return Image.fromarray(under.astype(np.uint8),'RGBA'),0,g
    n=np.asarray(im).astype(np.float32); a=n[...,3:]/255; ua=under[...,3:]/255
    oa=a+ua*(1-a); rgb=(n[...,:3]*a+under[...,:3]*ua*(1-a))/np.maximum(oa,1e-6)
    return Image.fromarray(np.dstack([rgb,oa*255]).clip(0,255).astype(np.uint8),'RGBA'),cov,g
if __name__=='__main__':
    out=sys.argv[1]; os.makedirs(out,exist_ok=True); tot=0; gains=0; n=0
    for f in sorted(int(x[:-4]) for x in os.listdir('master')):
        im,cov,g=final(f); gains+=g>1.02; n+=1
        fn='%s/%d.webp'%(out,f); im.save(fn,'WEBP',quality=75,method=6,alpha_quality=90); tot+=os.path.getsize(fn)
    print(n,'files, total',tot//1024,'KB; brightened',gains)
