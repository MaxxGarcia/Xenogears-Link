# party battle sprites: disc files 2988-2998 (idle frame 0) -> www/img/pb/<character id>.png
import pbr,os,json
OUT='/home/claude/xg/v/www/img/pb'; os.makedirs(OUT,exist_ok=True)
FILE={0:2988,1:2989,2:2991,3:2990,4:2992,5:2993,6:2994,7:2995,8:2996,9:2997,10:2998}
sz=[]
for i in range(11):
    im=pbr.render(pbr.load(FILE[i]),0)[0]; im.save('%s/%d.png'%(OUT,i),optimize=True); sz.append([im.width,im.height])
print(json.dumps(sz).replace(' ',''), sum(os.path.getsize(OUT+'/'+x) for x in os.listdir(OUT)))
