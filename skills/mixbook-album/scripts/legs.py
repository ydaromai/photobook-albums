import json,os
D=os.environ['BOOK_DIR']  # required: the book's data folder
R=json.load(open(f'{D}/grouped.json'))
# Trip legs come from <BOOK_DIR>/legs_config.json:
#   [["leg1", "title + GPS/route hints for the curator", ["2024-08-01", ...], [lo, hi]], ...]
LEGS=[tuple(x) for x in json.load(open(f'{D}/legs_config.json'))]
os.makedirs(f'{D}/legs',exist_ok=True)
out=[]
for key,title,days,(lo,hi) in LEGS:
    rs=[r for r in R if r['day'] in days]
    if not rs:
        print('WARN: leg', key, 'matches no photos for days', days); continue
    sheets=sorted(f'{D}/sheets/{f}' for f in os.listdir(f'{D}/sheets') if f[:10] in days)
    lines=[f'# {key}: {title}',f'Days: {", ".join(days)} | photos: {len(rs)} | target selection: {lo}-{hi} photos','', 'Contact sheets (each tile labelled "#<index> <local time> m<moment> d<dup-group>"):']+[f'- {s}' for s in sheets]+['','## Moments (auto-split by >40 min gap or >3 km jump; GPS centroid; photo index range)']
    ms={}
    for r in rs: ms.setdefault(r['moment'],[]).append(r)
    for m,mr in sorted(ms.items()):
        g=[r for r in mr if r['gps']]
        c=f"{sum(r['lat'] for r in g)/len(g):.4f},{sum(r['lon'] for r in g)/len(g):.4f}" if g else 'no-gps'
        lines.append(f"- m{m}: {mr[0]['local'][5:16]}–{mr[-1]['local'][11:16]}  n={len(mr)}  gps={c}  photos #{mr[0]['i']}..#{mr[-1]['i']}")
    lines+=['','## Per-photo data (index, local time, orientation WxH, sharpness, faces-detected, dup-group)']
    for r in rs:
        o='L' if r['W']>r['H']*1.05 else ('P' if r['H']>r['W']*1.05 else 'S')
        pano=' PANO' if r['W']>=r['H']*1.9 else ''
        lines.append(f"#{r['i']} id={r['id']} {r['local'][5:16]} {o}{pano} {r['W']}x{r['H']} sharp={r.get('sharp',0):.0f} faces={len(r.get('faces',[]))} d{r['dup']}")
    open(f'{D}/legs/{key}.md','w').write('\n'.join(lines))
    out.append(dict(key=key,title=title,days=days,lo=lo,hi=hi,file=f'{D}/legs/{key}.md',n=len(rs),first=rs[0]['i'],last=rs[-1]['i']))
json.dump(out,open(f'{D}/legs/legs.json','w'),indent=1)
for o in out: print(o['key'],o['n'],o['first'],o['last'],o['lo'],o['hi'])
print('sum lo-hi',sum(o['lo'] for o in out),sum(o['hi'] for o in out))
