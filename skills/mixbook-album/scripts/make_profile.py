"""content.json -> profile.json (+ images.json) and a one-time backup of the project as it was.
Usage: BOOK_DIR=<dir> python3 make_profile.py
Prints the project summary — CONFIRM with the user that this is the right project before any PUT."""
import json, os, shutil, time
D = os.environ['BOOK_DIR']
c = json.load(open(f'{D}/content.json')); p = c['data']['project'] if 'data' in c else c
if not any(f.startswith('content.orig.') for f in os.listdir(D)):
    shutil.copy(f'{D}/content.json', f'{D}/content.orig.{time.strftime("%Y%m%d-%H%M%S")}.json')   # restore point
prod = p['intended_product']; W, H = float(prod['width']), float(prod['height'])
PH = 2600.0; PW = PH * W / H
prof = dict(PW=PW, PH=PH, COVER_W=2 * PW, COVER_H=PH, BLEED=round(0.0175 * PH), DIRECTION='LTR',
            FONT_TITLE='Lobster', FONT_CAPTION='Avenir Next', FONT_HE='Lobster', PAGE_H_IN=H,
            IMAGES='images.json', MIN_PAGES=20, MAX_PAGES=prod.get('max_page_count'))
old = json.load(open(f'{D}/profile.json')) if os.path.exists(f'{D}/profile.json') else {}
prof.update({k: v for k, v in old.items() if k in ('FONT_TITLE', 'FONT_CAPTION', 'MIN_PAGES')})   # keep user choices
json.dump(prof, open(f'{D}/profile.json', 'w'), indent=1)
json.dump(p['photos'], open(f'{D}/images.json', 'w'))
inner = [x for x in p['pages'] if x['position'] > 0]
used = sum(len(x['content_items']) for x in p['pages'] if x['position'] > 0)
print(f"project {p['id']} '{p['name']}' | {prod.get('internal_name')} ({W}x{H} in, max {prod.get('max_page_count')} pages) | "
      f"{len(inner)} inside pages, {used} items already on them | {len(p['photos'])} photos | modified {p['modified_at']}")
if used: print('NOTE: this project already has content on its pages — the PUT will REPLACE it (backup saved as content.orig.*.json).')
