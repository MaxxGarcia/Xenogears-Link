import sys,struct,json
sys.path.insert(0,'/home/claude/xg/tools');import xg
from PIL import Image,ImageDraw
T=xg.table()
PLAN=json.loads(open('/home/claude/xg/v/www/plan.js').read().split('=',1)[1].rstrip().rstrip(';'))
def layers(f):
    h=xg.getfile(606+2*f,T); o=struct.unpack('<9I',h[0x130:0x154]); w=xg.lzss(h[o[1]:o[2]])
    n=struct.unpack_from('<I',w,0)[0]; sz=struct.unpack_from('<4I',w,4); so=struct.unpack_from('<I',w,0x14)[0]
    k=max(0,min(256,(len(w)-so)//4)); surf=list(struct.unpack_from('<%dI'%k,w,so))+[0]*(256-k)
    out=[]
    for L in range(n):
        to,vo=struct.unpack_from('<2I',w,0x18+8*L); nt=sz[L]//14
        tr=[struct.unpack_from('<6HBB',w,to+14*i) for i in range(nt)]
        if not tr: out.append(([],[]));continue
        nv=max(max(t[:3]) for t in tr)+1
        V=[struct.unpack_from('<3h',w,vo+8*i) for i in range(nv)]
        out.append((V,[(t,surf[t[6]]) for t in tr]))
    return out
def draw(f,S=512,src='/home/claude/xg/plan_full/%d.webp'):
    cx,cz,s=PLAN[str(f)]
    im=Image.open(src%f).convert('RGBA');bg=Image.new('RGBA',im.size,(20,20,40,255));bg.alpha_composite(im);im=bg
    d=ImageDraw.Draw(im);cols=[(255,255,0),(0,255,255),(255,0,255),(255,128,0)]
    for L,(V,tr) in enumerate(layers(f)):
        for t,fl in tr:
            P=[(((V[j][0]-cx)/s+0.5)*S,((V[j][2]-cz)/s+0.5)*S) for j in t[:3]]
            d.polygon(P,outline=cols[L]+(255,) if not fl&0x800000 else (255,0,0,255))
    return im
if __name__=='__main__':
    ims=[draw(int(a)) for a in sys.argv[1:]]
    W=Image.new('RGBA',(512*len(ims),512))
    for i,im in enumerate(ims):W.paste(im,(512*i,0))
    W.save('/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/layers.png')
