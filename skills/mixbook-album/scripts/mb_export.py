"""book.json (+ book_extra.json) -> Mixbook PUT /api/projects/{id} body.

Usage: BOOK_DIR=<dir> python3 mb_export.py <out_put.json>
Needs in BOOK_DIR: content.json (FRESH GET /api/v2/my/projects/{id}/content — page ids + modified_at),
                   book.json, book_extra.json, crops.json, grouped.json, profile.json (DIRECTION=LTR, PAGE_H_IN).
Mixbook geometry: every page is its own coordinate space; units = fractions of the PAGE HEIGHT;
item rel_x/rel_y = item CENTRE offset from the page centre; image_* = crop in the same units relative to the frame.
Cover pages: -1 front, -2 back (keeps Mixbook's logo item), -3 spine. Inside pages 1..N (1 = first right page).
"""
import json, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L

D = L.D
OUT = sys.argv[1]
prof = json.load(open(f'{D}/profile.json'))
PAGE_H_IN = prof.get('PAGE_H_IN', 8.5)
content = json.load(open(f'{D}/content.json'))
proj = content['data']['project'] if 'data' in content else content
book = json.load(open(f'{D}/book.json'))
extra = json.load(open(f'{D}/book_extra.json'))
if os.path.exists(f'{D}/crops.json'):
    L.CROP_OVR.update(json.load(open(f'{D}/crops.json'))['crops'])
PW, PH = L.PW, L.PH
CREATOR = {'id': proj['creator']['id']}


def uid(): return str(uuid.uuid4())


def style(fill_alpha=0.0):
    """Item style. NOTE: Mixbook does not render text items that carry a drop shadow — never set drop_shadow_*.
    For legibility use dark text on bright areas, or a soft dark text-box fill (Mixbook's 'Fills' effect)."""
    return {'client_id': uid(), 'border_alpha': 0, 'border_color': 0, 'border_thickness': 0,
            'drop_shadow_alpha': 0, 'drop_shadow_angle': 0, 'drop_shadow_blur_x': 0, 'drop_shadow_blur_y': 0,
            'drop_shadow_color': 0, 'drop_shadow_distance': 0, 'drop_shadow_strength': 0,
            'fill_alpha': fill_alpha, 'fill_color': 0, 'shape': {'id': 1}, 'transparency_alpha': 1}


def fid(i): return L.feat[int(i)]['id']   # engine index -> Mixbook photo id


def photo_item(i, frame, page_x0=0.0, part=None):
    """frame (x,y,w,h) in engine units; page_x0 = x offset of this page inside the spread.
    part: None, or (px0, px1) = the slice of the frame that falls on this page (panoramas)."""
    x, y, w, h = frame
    left, top, cw, ch = L.crop_for(int(i), w, h)
    iw, ih = (w / PH) / cw, (h / PH) / ch          # whole image size in page units
    ox, oy = -left * iw, -top * ih
    sx0, sx1 = (x, x + w) if part is None else part
    fx, fw = sx0 - page_x0, sx1 - sx0
    ox -= (sx0 - x) / PH                            # slice offset inside the full frame
    # bleed: full-bleed frames already extend past the trim by layout.BLEED (profile BLEED ~ 0.0175*PH,
    # the same 1.035 frame Mixbook uses), and the crop above is computed for that grown frame.
    rel_w, rel_h = fw / PH, h / PH
    cx, cy = (fx + fw / 2 - PW / 2) / PH, (y + h / 2 - PH / 2) / PH
    return {'client_id': uid(), 'creator': CREATOR, 'rel_x': cx, 'rel_y': cy, 'rel_width': rel_w, 'rel_height': rel_h,
            'related_item_id': None, 'related_item_client_id': None, 'rotation': 0, 'style': style(), 'overflow': True,
            'type': 'page_photo_item', 'is_flipped': False, 'image_offset_x': ox, 'image_offset_y': oy,
            'image_width': iw, 'image_height': ih, 'image_rotation': 0, 'photo': {'id': fid(i)}, 'effects': [],
            'border_radius': 0}


def esc(t): return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def text_item(t, page_x0=0.0):
    pt = round(t['size'] / PH * PAGE_H_IN * 72)
    color = '#ffffff' if t['color'] else '#1a1a1a'
    # Mixbook re-flows text itself; give the box room (Avenir/Lobster widths differ from our estimate)
    w, h = t['w'] * 1.45 + t['size'] * 0.6, t['h'] * 1.3
    # white text over a mid-tone area -> soft dark box behind it (no shadows: Mixbook drops shadowed text)
    fill = 0.35 if (t['color'] and t.get('bright', 0) >= 110) else 0.0
    x = t['x'] - (w - t['w']) if t['align'] == 'right' else t['x']
    cx, cy = (x - page_x0 + w / 2 - PW / 2) / PH, (t['y'] + h / 2 - PH / 2) / PH
    doc = (f'<p text-align="{t["align"]}"><s font-family="{t["font"]}" font-weight="400" font-style="normal" '
           f'font-size="{pt}" color="{color}" line-height="1.14">{esc(t["text"])}</s></p>')
    return {'client_id': uid(), 'creator': CREATOR, 'rel_x': cx, 'rel_y': cy, 'rel_width': w / PH, 'rel_height': h / PH,
            'related_item_id': None, 'related_item_client_id': None, 'rotation': 0,
            'style': style(fill), 'overflow': False,
            'type': 'page_text_item', 'text': None, 'min_height': h / PH, 'text_document': {'doc': doc, 'flow': []}}


pages = {}                              # position -> list of items


def put(pos, item): pages.setdefault(pos, []).append(item)


def emit(sp, left_pos, right_pos):
    """sp frames/texts are in spread coords: x in [0, PW) = left page, [PW, 2PW) = right page."""
    for i, fr in sp['frames'].items():
        x, y, w, h = fr
        tol = L.BLEED + 1                             # cover/hero bleeds overlap the middle slightly
        if x < PW - tol and x + w > PW + tol:        # spans the gutter (panorama): split in two
            put(left_pos, photo_item(i, fr, 0.0, (x, PW)))
            put(right_pos, photo_item(i, fr, PW, (PW, x + w)))
        elif x >= PW - 1:
            put(right_pos, photo_item(i, fr, PW))
        else:
            put(left_pos, photo_item(i, fr, 0.0))
    for t in sp['texts']:
        mid = t['x'] + t['w'] / 2
        put(right_pos, text_item(t, PW)) if mid >= PW else put(left_pos, text_item(t, 0.0))


# inside pages: 1 = page1 (single right page), spreads (2,3),(4,5)..., last single left page
for i, fr in extra['page1']['frames'].items(): put(1, photo_item(i, fr))
for t in extra['page1']['texts']: put(1, text_item(t))
for k, sp in enumerate(book):
    emit(sp, 2 + 2 * k, 3 + 2 * k)
last = 2 + 2 * len(book)
for i, fr in extra['last']['frames'].items(): put(last, photo_item(i, fr))
for t in extra['last']['texts']: put(last, text_item(t))
# cover: spread coords with the front cover on the RIGHT half (LTR) -> back -2 (left), front -1 (right)
cov = extra['cover']
emit(cov, -2, -1)

existing = {p['position']: p for p in proj['pages']}
if -3 in existing:
    pages.setdefault(-3, [])                     # rewrite the spine (title) when the product has one
prod = proj['intended_product']
if last > prod.get('max_page_count', 10 ** 6):
    sys.exit(f"book needs {last} inside pages but '{prod.get('internal_name')}' allows at most {prod['max_page_count']} "
             f"— raise TARGET density or curate fewer photos")
keep_types = {-2: {'page_logo_item'}, -3: {'page_text_item'}}   # Mixbook logo on the back, spine text
MIN_PAGES = int(prof.get('MIN_PAGES', 20))      # keep at least this many inside pages (blank if needed)
MIN_PAGES += MIN_PAGES % 2                        # page counts are even
keep_upto = max(last, MIN_PAGES)
for pos in range(1, keep_upto + 1):
    pages.setdefault(pos, [])                     # full rewrite: unused pages are cleared, never left with old content
out_pages = []
for pos in sorted(p for p in set(existing) | set(pages) | set(range(1, keep_upto + 1)) if p <= keep_upto):
    # pages beyond keep_upto are simply omitted -> Mixbook deletes them
    old = existing.get(pos)
    if pos not in pages and old is not None:
        out_pages.append({'id': old['id'], 'client_id': uid()}); continue
    items = pages.get(pos, [])
    if old is not None:
        # Mixbook's own cover items must be re-sent in the editor's WRITE format (fresh item, no server ids,
        # no nested 'logo'/shape data) — sending the GET format back returns HTTP 500.
        for it in old.get('content_items', []):
            if it.get('type') not in keep_types.get(pos, set()): continue
            base = {'client_id': uid(), 'creator': CREATOR, 'rel_x': it['rel_x'], 'rel_y': it['rel_y'],
                    'rel_width': it['rel_width'], 'rel_height': it['rel_height'], 'rotation': it.get('rotation', 0),
                    'related_item_id': None, 'related_item_client_id': None, 'overflow': False, 'style': style()}
            if it['type'] == 'page_logo_item':
                base.update(type='page_logo_item', logo_id=it.get('logo_id') or (it.get('logo') or {}).get('id', 3),
                            alignment=it.get('alignment', 8), logo_fill_color=it.get('logo_fill_color', 0),
                            logo_border_color=it.get('logo_border_color', 16777215),
                            logo_border_thickness=it.get('logo_border_thickness', 0))
            else:   # spine text: keep Mixbook's geometry/rotation, put the book title on it
                title = extra.get('spine_title') or (cov['texts'][0]['text'] if cov['texts'] else '')
                doc = (f'<p text-align="center"><s font-family="{L.FONT_EN}" font-weight="400" font-style="normal" '
                       f'font-size="12" color="#1a1a1a" line-height="1.14">{esc(title)}</s></p>')
                base.update(type='page_text_item', text=None, min_height=it.get('min_height', it['rel_height']),
                            text_document={'doc': doc, 'flow': []})
            items.insert(0, base)
    page = {'client_id': uid(), 'creator': CREATOR, 'position': pos, 'background': None, 'content_items': items}
    if old is not None: page['id'] = old['id']
    out_pages.append(page)

extra_pages = [p for p in existing if p > keep_upto]
body = {'project': {'creator': CREATOR, 'id': proj['id'], 'name': proj['name'], 'pages': out_pages,
                    'photos': [{'id': p['id']} for p in proj['photos']], 'deleted_photo_ids': [],
                    'hidden_background_ids': proj.get('hidden_background_ids', []), 'backgrounds': [],
                    'hidden_sticker_ids': proj.get('hidden_sticker_ids', []), 'stickers': [], 'variables': [],
                    'intended_product': {'id': proj['intended_product']['id']}, 'template': {'id': proj['template']['id']},
                    'modified_at': proj['modified_at']}}
json.dump(body, open(OUT, 'w'), ensure_ascii=False)
n_items = sum(len(p.get('content_items', [])) for p in out_pages)
print(f'inside pages 1..{last} | new pages {len([p for p in out_pages if "id" not in p])} | items {n_items} | '
      f'photos used {len({it["photo"]["id"] for p in out_pages for it in p.get("content_items", []) if it.get("type") == "page_photo_item"})}')
if extra_pages:
    print(f'deleting {len(extra_pages)} unused pages beyond {keep_upto}')
if last < MIN_PAGES:
    print(f'WARNING: the book fills {last} pages but the minimum kept is {MIN_PAGES}: pages {last + 1}..{MIN_PAGES} stay blank '
          f'— lower TARGET density or add photos.')
