import json,sys
D=sys.argv[1]; cur=json.load(open(sys.argv[2]))
book=json.load(open(f'{D}/book.json')); PW=json.load(open(f'{D}/profile.json'))['PW']
role={p['i']:p['role'] for s in cur['sections'] for p in s['photos']}; W={'small':0.45,'normal':1,'large':3,'page':5,'spread':6}
v=[]
for n,sp in enumerate(book):
    pages={}
    for k,f in sp['frames'].items(): pages.setdefault('R' if f[0]>=PW-1 else 'L',{})[int(k)]=f[2]*f[3]
    for side,fr in pages.items():
        for a in fr:
            for b in fr:
                if W[role[a]]<W[role[b]] and fr[a]>fr[b]*1.05: v.append(f"{n}{side} #{a}({role[a]})>{b}({role[b]}) x{fr[a]/fr[b]:.1f}")
print(len(v)); print('\n'.join(v))
