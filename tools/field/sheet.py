import sys,rt
from PIL import Image
S='/tmp/claude-0/-home-claude/8e6fc456-c737-554d-97c2-7a103c217ffc/scratchpad/'
ids=[int(x) for x in sys.argv[2:]]
sh=Image.new('RGB',(4*384,((len(ids)+3)//4)*384),(24,24,40))
for i,f in enumerate(ids):
    try: im=rt.room(f,768)
    except Exception as e: print(f,'ERR',e); continue
    if im is None: print(f,'none'); continue
    sh.paste(im.resize((384,384),Image.LANCZOS),((i%4)*384,(i//4)*384),im.resize((384,384),Image.LANCZOS))
sh.save(S+sys.argv[1])
