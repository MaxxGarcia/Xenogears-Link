import os,sys,numpy as np
from PIL import Image
def finish(f,size,colors):
    im=Image.open('master/%d.png'%f).convert('RGBA'); a=np.asarray(im).astype(np.float32)
    v=a[...,3]>0
    if not v.any(): return None,0,0
    lum=a[...,:3].mean(-1)[v]; p95=np.percentile(lum,95)
    g=1.0
    if p95<100: g=min(3.0,100/max(p95,1))
    if g>1.02:
        rgb=a[...,:3]/255; rgb=1-(1-np.clip(rgb*g**0.5,0,1))**(g**0.5) if False else np.clip(rgb*g,0,1); a[...,:3]=rgb*255
    im=Image.fromarray(a.astype(np.uint8),'RGBA')
    # premultiplied downscale so the edges do not pick up black
    pm=np.asarray(im).astype(np.float32); pm[...,:3]*=pm[...,3:]/255
    sm=np.asarray(Image.fromarray(pm.astype(np.uint8),'RGBA').resize((size,size),Image.LANCZOS)).astype(np.float32)
    al=sm[...,3]; rgb=np.where(al[...,None]>0,sm[...,:3]*255/np.maximum(al[...,None],1),0)
    out=np.dstack([np.clip(rgb,0,255),np.where(al>=128,255,0)]).astype(np.uint8)
    q=Image.fromarray(out[...,:3],'RGB').quantize(colors-1,method=Image.MEDIANCUT,dither=Image.NONE)
    idx=np.asarray(q).copy()+1; idx[out[...,3]==0]=0
    pal=[0,0,0]+q.getpalette()[:(colors-1)*3]
    p=Image.fromarray(idx.astype(np.uint8),'P'); p.putpalette(pal); p.info['transparency']=0
    return p,float(v.mean()),float(p95)
if __name__=='__main__':
    size=int(sys.argv[1]); colors=int(sys.argv[2]); out=sys.argv[3]; os.makedirs(out,exist_ok=True)
    ids=sorted(int(x[:-4]) for x in os.listdir('master')); tot=0; rep=[]
    if len(sys.argv)>4: ids=ids[::int(sys.argv[4])]
    for f in ids:
        p,cov,p95=finish(f,size,colors)
        if p is None: rep.append((f,'empty')); continue
        fn='%s/%d.png'%(out,f); p.save(fn,optimize=True,transparency=0); tot+=os.path.getsize(fn)
        if p95<20 or cov<0.01: rep.append((f,round(cov,3),round(p95)))
    print(size,colors,len(ids),'files',tot//1024,'KB','flagged',len(rep),rep)
