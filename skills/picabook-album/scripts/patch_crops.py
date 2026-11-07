"""Re-apply reviewer crop overrides to an exported jPages file without re-running layout.
Usage: BOOK_DIR=<dir> patch_crops.py <curation.json> <jpages_in.json> <jpages_out.json>"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
cur = json.load(open(sys.argv[1])); jp = json.load(open(sys.argv[2]))
L.CROP_OVR.update(cur.get('crops', {}))
by_id = {r['id']: r['i'] for r in L.feat.values()}
n = 0
for pg in jp:
    for o in pg['objects']:
        if o.get('tipo') != 'img': continue
        i = by_id.get(o['imageVO'])
        if i is None or str(i) not in L.CROP_OVR: continue
        iw, ih = o['imgWidth'], o['imgHeight']
        left, top, cw, ch = L.crop_for(i, o['w'], o['h'])
        old = (round(o['imgX'] / iw, 3), round(o['imgY'] / ih, 3))
        o.update(imgW=cw * iw, imgH=ch * ih, imgX=left * iw, imgY=top * ih, imgS=o['w'] / (cw * iw) * 0.10815)
        n += 1; print(f'#{i}: crop origin {old} -> {(round(left, 3), round(top, 3))}')
json.dump(jp, open(sys.argv[3], 'w'), ensure_ascii=False)
print('patched', n, 'of', len(L.CROP_OVR), 'overrides')
