import json,math,os
from PIL import Image,ImageDraw,ImageFont,ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES=True
import os
D=os.environ['BOOK_DIR']  # required: the book's data folder
R=json.load(open(f'{D}/features.json'))
R=[r for r in R if not r.get('missing')]
def hd(a,b): return bin(a^b).count('1')
def hsim(a,b): return sum(min(x,y) for x,y in zip(a,b))/max(1e-9,sum(a))
def km(a,b):
    if not(a['gps'] and b['gps']): return 0
    return math.hypot((a['lat']-b['lat'])*111,(a['lon']-b['lon'])*111*math.cos(math.radians(a['lat'])))
# near-duplicate bursts: compare to previous few in time
for i,r in enumerate(R): r['i']=i
grp=list(range(len(R)))
def find(x):
    while grp[x]!=x: grp[x]=grp[grp[x]]; x=grp[x]
    return x
for i in range(len(R)):
    for j in range(max(0,i-6),i):
        a,b=R[i],R[j]
        dt=abs(a['ts']-b['ts'])/1000
        d=hd(a['dhash'],b['dhash']); s=hsim(a['hist'],b['hist'])
        if (dt<120 and (d<=14 or (d<=20 and s>0.8))) or (dt<600 and d<=8):
            grp[find(i)]=find(j)
roots={}
for r in R:
    k=find(r['i']); roots.setdefault(k,len(roots)); r['dup']=roots[k]
# moments: new moment if gap > 40min or jump > 3km
m=0
for i,r in enumerate(R):
    if i>0:
        p=R[i-1]
        if (r['ts']-p['ts'])/1000>40*60 or km(r,p)>3 or r['day']!=p['day']: m+=1
    r['moment']=m
json.dump(R,open(f'{D}/grouped.json','w'))
ndup=len(set(r['dup'] for r in R)); print('photos',len(R),'dup-groups',ndup,'moments',m+1)
# contact sheets per day
os.makedirs(f'{D}/sheets',exist_ok=True)
try: font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',18); fsm=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',13)
except: font=fsm=ImageFont.load_default()
days={}
for r in R: days.setdefault(r['day'],[]).append(r)
COLS,T,PAD=8,210,4
sheets=[]
for day,rs in sorted(days.items()):
    chunks=[rs[k:k+64] for k in range(0,len(rs),64)]
    for ci,ch in enumerate(chunks):
        rows=math.ceil(len(ch)/COLS)
        S=Image.new('RGB',(COLS*(T+PAD)+PAD,rows*(T+PAD+18)+PAD+30),'white')
        dr=ImageDraw.Draw(S); dr.text((8,6),f'{day}  part {ci+1}/{len(chunks)}  ({len(rs)} photos that day)',fill='black',font=font)
        for k,r in enumerate(ch):
            x=PAD+(k%COLS)*(T+PAD); y=30+PAD+(k//COLS)*(T+PAD+18)
            im=Image.open(f'{D}/thumbs/{r["id"]}.jpg').convert('RGB'); im.thumbnail((T,T))
            S.paste(im,(x+(T-im.width)//2,y+(T-im.height)//2))
            col=['#c00','#06c','#080','#a60','#808','#088'][r['moment']%6]
            dr.rectangle([x,y+T,x+T,y+T+17],fill=col)
            dr.text((x+3,y+T+1),f"#{r['i']} {r['local'][11:16]} m{r['moment']} d{r['dup']}",fill='white',font=fsm)
        fn=f'{D}/sheets/{day}_{ci+1}.jpg'; S.save(fn,quality=82); sheets.append(fn)
print(len(sheets),'sheets')
for d,rs in sorted(days.items()): print(d,len(rs),'dupgroups',len(set(r['dup'] for r in rs)),'moments',sorted(set(r['moment'] for r in rs))[0],'-',sorted(set(r['moment'] for r in rs))[-1])
