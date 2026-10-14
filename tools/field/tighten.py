# Re-frames the rooms whose picture covered far more ground than the walkable area (so the part the app shows was blurry).
import json,os,sys,shutil,numpy as np
sys.path.insert(0,'/home/claude/xg/tools')
from PIL import Image
import rt,export
A=json.load(open('/home/claude/xg/audit/audit.json'))
todo=[r for r in A if 'res' in r and r['res']<200 and r['nt']>4]
K=2.2
os.makedirs('master_wide',exist_ok=True);os.makedirs('old_crop',exist_ok=True);os.makedirs('/home/claude/xg/plan_wide',exist_ok=True)
newplan={}
def one(r):
    f=r['f'];x0,z0,x1,z1=r['bbox'];cx0,cz0,s0=rt.PLAN[str(f)]
    s=max(x1-x0,z1-z0)*K;cx=(x0+x1)/2;cz=(z0+z1)/2
    if s>=s0*0.8: return f,None
    # underlay: the same ground cut out of the old shaded picture
    o=Image.open(export.OLD%f).convert('RGBA');W=o.size[0];px=lambda v,c:(v-c)/s0*W+W/2
    box=(px(cx-s/2,cx0),px(cz-s/2,cz0),px(cx+s/2,cx0),px(cz+s/2,cz0))
    o.transform((512,512),Image.EXTENT,box,Image.BILINEAR).save('old_crop/%d.png'%f)
    rt.PLAN[str(f)]=[cx,cz,s]
    im=rt.room(f,1024)
    if im is None: rt.PLAN[str(f)]=[cx0,cz0,s0];return f,None
    if not os.path.exists('master_wide/%d.png'%f): shutil.copy('master/%d.png'%f,'master_wide/%d.png'%f)
    im.save('master/%d.png'%f)
    return f,[round(cx,1),round(cz,1),round(s,1)]
if __name__=='__main__':
    import xg
    for r in todo:
        f,p=one(r)
        if p: newplan[f]=p
        print(f,r['res'],'->',p,flush=True)
    export.OLD='old_crop/%d.png'
    P=json.loads(open('/home/claude/xg/v/www/plan.js').read().split('=',1)[1].rstrip().rstrip(';'))
    for f,p in newplan.items():
        im,cov,g=export.final(f)
        dst='/home/claude/xg/v/www/plan/%d.webp'%f
        if not os.path.exists('/home/claude/xg/plan_wide/%d.webp'%f): shutil.copy(dst,'/home/claude/xg/plan_wide/%d.webp'%f)
        im.save(dst,'WEBP',quality=75,method=6,alpha_quality=90);P[str(f)]=p
    shutil.copy('/home/claude/xg/v/www/plan.js','/home/claude/xg/plan_wide/plan.js.before')
    head=open('/home/claude/xg/v/www/plan.js').read().split('=',1)[0]
    open('/home/claude/xg/v/www/plan.js','w').write(head+'='+json.dumps(P,separators=(',',':'))+';\n')
    print('reframed',len(newplan))
