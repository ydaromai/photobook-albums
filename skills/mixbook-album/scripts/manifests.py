"""Write <BOOK_DIR>/review/spread_NN.md manifests for verify-spreads.js (after layout.py).
Usage: BOOK_DIR=<dir> python3 manifests.py <curation.json>"""
import json, os, sys
D = os.environ['BOOK_DIR']
book = json.load(open(f'{D}/book.json')); cur = json.load(open(sys.argv[1]))
feat = {r['i']: r for r in json.load(open(f'{D}/grouped.json'))}
prof = json.load(open(f'{D}/profile.json')); PW, PH = prof['PW'], prof['PH']
thumbs = prof.get('THUMBS', f'{D}/thumbs')
role = {p['i']: (p['role'], si, p.get('why', '')) for si, s in enumerate(cur['sections']) for p in s['photos']}
os.makedirs(f'{D}/review', exist_ok=True)
first = 'LEFT' if prof.get('DIRECTION', 'LTR') == 'LTR' else 'RIGHT'
for n, sp in enumerate(book):
    L = [f'# Spread {n:02d} ({sp["layout"]}) preview: {D}/preview/spread_{n:02d}.jpg', f'Reading order: {first} page first.', '', '## Photos']
    for i, (x, y, w, h) in sp['frames'].items():
        i = int(i); r, si, why = role[i]; s = cur['sections'][si]
        side = 'SPREAD' if w > PW * 1.5 else ('R' if x >= PW - 1 else 'L'); x0 = x - PW if side == 'R' else x
        L.append(f"- #{i} [{side} x{x0 / PW * 100:.0f}% y{y / PH * 100:.0f}% w{w / PW * 100:.0f}% h{h / PH * 100:.0f}%] role={r} "
                 f"section={si} \"{s.get('title') or s.get('title_en', '')}\" {feat[i]['local'][5:16]} — {why[:90]} | original: {thumbs}/{feat[i]['id']}.jpg")
    L += ['', '## Captions (exact text)']
    for t in sp['texts']:
        L.append(f"- section {t.get('sec')} {'title' if t.get('kind') == 'title' else 'caption'}: \"{t['text']}\" on #{t['photo']} "
                 f"({'dark' if t['color'] == 0 else 'white'} text, area brightness {t.get('bright')})")
    open(f'{D}/review/spread_{n:02d}.md', 'w').write('\n'.join(L))
print(len(book), 'manifests')
