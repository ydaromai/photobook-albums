"""Photobook layout engine for Picabook books (default right-to-left / Hebrew binding; the same engine powers the mixbook-album skill with DIRECTION=LTR).

Input : data/curation.json  -> {"sections":[{date,title_en,caption_he,photos:[{i,role}]}], "cover":{...}, "page1":{...}, "last":{...}}
Output: data/book.json      -> abstract book: list of pages with frames/texts in editor units
        data/preview/*.jpg  -> rendered previews of every spread (for review)
Coordinates are abstract page units from profile.json (PW x PH per page; spreads are 2*PW wide).
"""
import json, math, os, sys, itertools
from PIL import Image, ImageDraw, ImageFont, ImageFile, ImageFilter
ImageFile.LOAD_TRUNCATED_IMAGES = True

D = os.environ['BOOK_DIR']   # required: the book's data folder (grouped.json, images, profile.json)
_prof = json.load(open(f'{D}/profile.json')) if os.path.exists(f'{D}/profile.json') else {}
PW, PH = _prof.get('PW', 3354.330810546875), _prof.get('PH', 2586.6142578125)   # one page
SW = PW * 2                                           # spread width
BLEED = int(_prof.get('BLEED', 30))                     # Mixbook: round(0.0175*PH) matches its own 1.035 frames
OUTER, TOP, BOTTOM, GUT, GAP = 110, 115, 95, 75, 48   # grid geometry (margins, gutter, gap)
COVER_W, COVER_H = _prof.get('COVER_W', 7275.59033203125), _prof.get('COVER_H', 2940.945068359375)
THUMBS = _prof.get('THUMBS', f'{D}/thumbs')
DIRECTION = _prof.get('DIRECTION', 'RTL')            # Picabook default: RTL (Hebrew binding). LTR only when set explicitly.
FIRST, SECOND = ('R', 'L') if DIRECTION == 'RTL' else ('L', 'R')   # page read first on each spread
P1_SIDE, LAST_SIDE = ('L', 'R') if DIRECTION == 'RTL' else ('R', 'L')  # page 1 / last page sit opposite the covers

feat = {r['i']: r for r in json.load(open(f'{D}/grouped.json'))}
_imgs_path = f'{D}/' + _prof.get('IMAGES', 'images.json')
imgs = {im['id']: im for im in json.load(open(_imgs_path))} if os.path.exists(_imgs_path) else {}

def aspect(i):
    r = feat[i]; return r['W'] / r['H']

# ---------------------------------------------------------------- page grid (guillotine DP)
class Node:
    def __init__(self, kind, a=None, b=None, idx=None, asp=None):
        self.kind, self.a, self.b, self.idx = kind, a, b, idx
        self.asp = asp
def leaf(k, asp): return Node('leaf', idx=k, asp=asp)
def hcat(a, b): return Node('h', a, b, asp=a.asp + b.asp)            # side by side (a on the RIGHT: RTL)
def vcat(a, b): return Node('v', a, b, asp=1 / (1 / a.asp + 1 / b.asp))  # a on top

def candidates(asps, lo, hi, memo, K=24):
    key = (lo, hi)
    if key in memo: return memo[key]
    if hi - lo == 1:
        res = [leaf(lo, asps[lo])]
    else:
        res = []
        for m in range(lo + 1, hi):
            L = candidates(asps, lo, m, memo, K); R = candidates(asps, m, hi, memo, K)
            for a in L[:8]:
                for b in R[:8]:
                    res.append(hcat(a, b)); res.append(vcat(a, b))
        # keep a diverse set of aspects
        res.sort(key=lambda n: n.asp)
        if len(res) > K:
            step = len(res) / K
            res = [res[int(j * step)] for j in range(K)]
    memo[key] = res
    return res

def place(node, x, y, w, h, out):
    if node.kind == 'leaf':
        out[node.idx] = (x, y, w, h); return
    if node.kind == 'h':      # a on the reading-start side (right for RTL, left for LTR)
        wa = (w - GAP) * node.a.asp / (node.a.asp + node.b.asp)
        if DIRECTION == 'RTL':
            place(node.a, x + w - wa, y, wa, h, out)
            place(node.b, x, y, w - GAP - wa, h, out)
        else:
            place(node.a, x, y, wa, h, out)
            place(node.b, x + wa + GAP, y, w - GAP - wa, h, out)
    else:
        ha = (h - GAP) * (1 / node.a.asp) / (1 / node.a.asp + 1 / node.b.asp)
        place(node.a, x, y, w, ha, out)
        place(node.b, x, y + ha + GAP, w, h - GAP - ha, out)

def score_layout(rects, asps, weights, area_total):
    s = 0
    for k, (x, y, w, h) in rects.items():
        if w < 250 or h < 250: s += 50
        if w < 0.21 * PW or h < 0.2 * PH: s += 6          # sliver
        d = abs(math.log((w / h) / asps[k]))
        s += d * d * 6 + max(0, d - 0.35) * 20           # crop distortion
        share = w * h / area_total
        want = weights[k] / sum(weights)
        s += abs(math.log(max(share, 1e-3) / want)) * 1.5  # area share vs importance
        if weights[k] == 1.0 and share > 0.42 and max(weights) > 1: s += 6   # a normal photo hogging the page
    # hierarchy: no lesser photo may get more area than a more important one on the same page
    ks = list(rects)
    for a in ks:
        for b in ks:
            if weights[a] < weights[b]:
                ra = rects[a][2] * rects[a][3]; rb = rects[b][2] * rects[b][3]
                if ra > rb * 1.05: s += 10 + 15 * (ra / rb - 1)
    return s

def layout_page(photos, rect):
    """photos: list of (i, role). rect: (x,y,w,h) inner area. Returns {i: frame}"""
    x, y, w, h = rect
    asps = [aspect(i) for i, _ in photos]
    weights = []; got = False
    for i, r in photos:
        if r == 'large': weights.append(3.0)
        elif r == 'small': weights.append(0.45)
        else: weights.append(1.0)
    best = None
    memo = {}
    for node in candidates(asps, 0, len(photos), memo, K=60):
        out = {}
        place(node, x, y, w, h, out)
        sc = score_layout(out, asps, weights, w * h)
        if best is None or sc < best[0]: best = (sc, out)
    # hero-cell templates: the most important photo gets its own cell, the rest fill the remainder
    n = len(photos)
    if n >= 3 and max(weights) > 1:
        hk = max(range(n), key=lambda k: (weights[k], -k))
        rest = [k for k in range(n) if k != hk]
        ra = [asps[k] for k in rest]
        rmemo = {}
        rcands = candidates(ra, 0, len(ra), rmemo, K=40)
        for f in (0.45, 0.5, 0.55, 0.6, 0.66):
            for side in ('R', 'L', 'T', 'B'):
                if side in 'RL':
                    cw = (w - GAP) * f; cell = (x + w - cw, y, cw, h) if side == 'R' else (x, y, cw, h)
                    rem = (x, y, w - GAP - cw, h) if side == 'R' else (x + cw + GAP, y, w - GAP - cw, h)
                else:
                    ch = (h - GAP) * f; cell = (x, y, w, ch) if side == 'T' else (x, y + h - ch, w, ch)
                    rem = (x, y + ch + GAP, w, h - GAP - ch) if side == 'T' else (x, y, w, h - GAP - ch)
                for node in rcands:
                    o2 = {}
                    place(node, *rem, o2)
                    out = {hk: cell}
                    for j, k in enumerate(rest): out[k] = o2[j]
                    sc = score_layout(out, asps, weights, w * h) + 0.3   # slight preference for pure mosaics
                    if sc < best[0]: best = (sc, out)
    return {photos[k][0]: v for k, v in best[1].items()}, best[0]

# ---------------------------------------------------------------- pagination
def page_rect(side):
    """inner grid rect for a page; side 'R' (first, right page) or 'L'"""
    if side == 'R':
        return (PW + GUT, TOP, PW - GUT - OUTER, PH - TOP - BOTTOM)
    if side == 'L':
        return (OUTER, TOP, PW - GUT - OUTER, PH - TOP - BOTTOM)
    return (OUTER, TOP, PW - 2 * OUTER, PH - TOP - BOTTOM)  # single page

def units(role): return 1.6 if role == 'large' else (0.7 if role == 'small' else 1.0)

TARGET = float(os.environ.get('TARGET', '5.6'))
def paginate(seq, target_units=None):
    target_units = target_units or TARGET
    """seq: list of dict(i, role, sec). Produces list of page dicts: {'kind':'grid'|'hero'|'pano', 'photos':[...]}"""
    pages = []
    buf = []
    def flush_runs(run, need=None):
        # split a run of grid photos into pages with ~target units each, preferring section boundaries.
        # need: required parity (0/1) of the number of pages produced (so a following pano starts a spread)
        n = len(run)
        if n == 0: return []
        INF = 1e18
        B = [[INF, INF] for _ in range(n + 1)]; P = [[None, None] for _ in range(n + 1)]; B[0][0] = 0
        for j in range(1, n + 1):
            u = 0
            for i in range(j - 1, -1, -1):
                u += units(run[i]['role'])
                cnt = j - i
                if cnt > 9 or u > 9.5: break
                c = (u - target_units) ** 2
                if cnt == 1 and run[i]['role'] != 'large': c += 6
                if sum(1 for q in run[i:j] if q['role'] == 'large') > 2: c += 3
                # prefer breaks at section boundaries
                if j < n and run[j]['sec'] == run[j - 1]['sec']: c += 1.2
                for par in (0, 1):
                    v = B[i][par] + c
                    if v < B[j][1 - par]: B[j][1 - par] = v; P[j][1 - par] = (i, par)
        par = need if need is not None and B[n][need] < INF else (0 if B[n][0] <= B[n][1] else 1)
        cuts = []; j = n
        while j > 0:
            i, pp = P[j][par]; cuts.append((i, j)); j, par = i, pp
        return [{'kind': 'grid', 'photos': run[a:b]} for a, b in reversed(cuts)]
    run = []
    last = None   # (start index in pages, run items) of the most recent grid run
    slots = lambda: sum(2 if q['kind'] == 'pano' else 1 for q in pages)
    for it in seq:
        if it['role'] in ('page', 'spread'):
            need = (slots() % 2) if it['role'] == 'spread' else None   # pages so far + run must be even
            if run:
                start = len(pages); pages.extend(flush_runs(run, need)); last = (start, run, len(pages) - start)
            run = []
            if it['role'] == 'spread' and slots() % 2 == 1 and last:
                st, lr, cnt = last   # re-split the previous run with flipped parity
                redo = flush_runs(lr, 1 - (cnt % 2))
                if len(redo) % 2 != cnt % 2:
                    pages[st:st + cnt] = redo; last = (st, lr, len(redo))
            if it['role'] == 'spread' and slots() % 2 == 1:
                print('WARN pano parity not satisfiable at', it['i'])
            pages.append({'kind': 'hero' if it['role'] == 'page' else 'pano', 'photos': [it]})
        else:
            run.append(it)
    if run: pages.extend(flush_runs(run, slots() % 2))   # make the total even (no empty last page)
    return pages

def assemble_spreads(pages):
    """Place pages into spreads (R then L). A pano needs a whole spread: if it falls on an L slot,
    swap it with the following page (tiny chronology shift)."""
    out = []  # list of spreads: each {'R':page,'L':page} or {'pano':page}
    q = list(pages)
    cur = {}
    while q:
        p = q.pop(0)
        if p['kind'] == 'pano':
            if FIRST in cur:  # need something for the second page first
                nxt = next((k for k, x in enumerate(q) if x['kind'] != 'pano'), None)
                if nxt is None:
                    cur[SECOND] = {'kind': 'empty', 'photos': []}
                else:
                    cur[SECOND] = q.pop(nxt)
                out.append(cur); cur = {}
            out.append({'pano': p})
            continue
        if FIRST not in cur: cur[FIRST] = p
        else:
            cur[SECOND] = p; out.append(cur); cur = {}
    if cur:
        cur.setdefault(SECOND, {'kind': 'empty', 'photos': []}); out.append(cur)
    return out

# ---------------------------------------------------------------- crops
CROP_OVR = {}
TEXTPOS = {}
def crop_for(i, fw, fh):
    """returns crop (left, top, cw, ch) as fractions of the image; faces-aware, overridable"""
    r = feat[i]; faces = r.get('faces') or []
    W, H = r['W'], r['H']
    s = max(fw / W, fh / H)
    cw, ch = fw / s / W, fh / s / H          # crop size as fraction of image
    o = CROP_OVR.get(str(i)) or CROP_OVR.get(i)
    if o:
        return (1 - cw) * o.get('x', 0.5), (1 - ch) * o.get('y', 0.42), cw, ch
    if faces:
        x0 = min(f[0] for f in faces); x1 = max(f[0] + f[2] for f in faces)
        y0 = min(f[1] for f in faces); y1 = max(f[1] + f[3] for f in faces)
        cx = (x0 + x1) / 2; cy = (y0 + y1) / 2
        # horizontal: center on faces
        left = min(max(cx - cw / 2, 0), 1 - cw)
        # vertical: keep faces in upper-middle
        top = min(max(cy - ch * 0.42, 0), 1 - ch)
        # make sure all faces fit if possible
        if x1 - x0 < cw: left = min(max(left, x1 - cw), x0)
        if y1 - y0 < ch: top = min(max(top, y1 - ch), y0)
        left = min(max(left, 0), 1 - cw); top = min(max(top, 0), 1 - ch)
    else:
        left = (1 - cw) / 2; top = (1 - ch) * 0.42
    return left, top, cw, ch

# ---------------------------------------------------------------- captions
FONT_EN = _prof.get('FONT_TITLE', 'LobsterCFF'); FONT_HE = _prof.get('FONT_HE', 'AlefCFF'); FONT_CAP = _prof.get('FONT_CAPTION', 'LobsterCFF')
import re as _re
is_heb = lambda t: bool(_re.search('[\u0590-\u05FF]', t or ''))
def text_width(txt, size, heb):
    # rough metrics (Lobster ~0.47em avg, Alef ~0.5em avg); refined in-browser at export
    per = 0.50 if heb else 0.47
    return len(txt) * size * per + size * 0.3

def region_brightness(i, frame, box):
    """mean luminance (0-255) of the thumbnail area under a text box (frame coords)"""
    fx, fy, fw, fh = frame
    left, top, cw, ch = crop_for(i, fw, fh)
    im = Image.open(f"{THUMBS}/{feat[i]['id']}.jpg").convert('L')
    W, H = im.size
    bx, by, bw, bh = box
    u0 = left + (bx - fx) / fw * cw; u1 = left + (bx + bw - fx) / fw * cw
    v0 = top + (by - fy) / fh * ch; v1 = top + (by + bh - fy) / fh * ch
    reg = im.crop((int(max(0, u0) * W), int(max(0, v0) * H), int(min(1, u1) * W) + 1, int(min(1, v1) * H) + 1))
    px = list(reg.getdata())
    return sum(px) / max(1, len(px))

def face_overlap(i, frame, box):
    fx, fy, fw, fh = frame
    left, top, cw, ch = crop_for(i, fw, fh)
    bx, by, bw, bh = box; tot = 0
    for (x, y, w, h) in feat[i].get('faces') or []:
        X = fx + (x - left) / cw * fw; Y = fy + (y - top) / ch * fh; Wd = w / cw * fw; Hd = h / ch * fh
        ox = max(0, min(bx + bw, X + Wd) - max(bx, X)); oy = max(0, min(by + bh, Y + Hd) - max(by, Y))
        tot += ox * oy
    return tot

def make_text(txt, frame, i, heb, where, big=False, side='R', forced=False, fontname=None):
    fx, fy, fw, fh = frame
    size = 75 if not heb else 80
    pad = 70 if big else 50
    while size > 55 and text_width(txt, size, heb) > fw - 2 * pad: size -= 5
    tw = min(fw - 2 * pad, text_width(txt, size, heb)); th = size * 1.15
    # outer side alignment: right page -> align right edge, left page -> left edge (English); Hebrew right
    alignr = (side == 'R') or heb
    tx = fx + fw - pad - tw if alignr else fx + pad
    ty = fy + fh - pad - th if where == 'bottom' else fy + pad
    if not forced and face_overlap(i, frame, (tx, ty, tw, th)) > 0:
        ty2 = fy + pad if where == 'bottom' else fy + fh - pad - th
        if face_overlap(i, frame, (tx, ty2, tw, th)) < face_overlap(i, frame, (tx, ty, tw, th)): ty = ty2
    br = region_brightness(i, frame, (tx, ty, tw, th))
    dark = br > 160
    return dict(text=txt, x=tx, y=ty, w=tw, h=th, size=size, font=fontname or (FONT_HE if heb else FONT_EN),
                heb=heb, align='right' if alignr else 'left', color=0 if dark else 16777215,
                shadow=not dark, photo=i, bright=round(br))

# ---------------------------------------------------------------- build
def build(cur):
    secs = cur['sections']
    seq = []
    for si, s in enumerate(secs):
        for p in s['photos']:
            seq.append(dict(i=p['i'], role=p['role'], sec=si))
    pages = paginate(seq)
    spreads = assemble_spreads(pages)
    book = []
    titled = set(); captioned = set(); recent_titles = []

    def frames_for(page, side):
        if page['kind'] == 'empty': return {}
        if page['kind'] == 'hero':
            i = page['photos'][0]['i']
            if side == 'R': return {i: (PW, -BLEED, PW + BLEED, PH + 2 * BLEED)}
            if side == 'L': return {i: (-BLEED, -BLEED, PW + BLEED, PH + 2 * BLEED)}
            return {i: (-BLEED, -BLEED, PW + 2 * BLEED, PH + 2 * BLEED)}
        if page['kind'] == 'pano':
            i = page['photos'][0]['i']
            return {i: (-BLEED, -BLEED, SW + 2 * BLEED, PH + 2 * BLEED)}
        fr, sc = layout_page([(q['i'], q['role']) for q in page['photos']], page_rect(side))
        page['score'] = sc
        return fr

    def captions_for(page_items, frames, side_of):
        texts = []
        here = {q['i'] for q in page_items}
        bysec = {}
        for q in page_items: bysec.setdefault(q['sec'], []).append(q)
        # sections whose anchored captions live on a photo of this spread (may belong to any section)
        for si, s in enumerate(secs):
            for key in ('title_on', 'caption_on', 'he_on'):
                if s.get(key) in here and si not in bysec: bysec[si] = []
        for si in sorted(bysec):
            s = secs[si]; qs = bysec[si]
            cand = sorted(qs, key=lambda q: -(frames[q['i']][2] * frames[q['i']][3]))
            def host(key):
                a = s.get(key)
                if a is not None: return a if a in here else None   # anchored: only on its own spread
                return cand[0]['i'] if cand else None
            s.setdefault('title_en', s.get('title', ''))
            if s['title_en'] and si not in titled:
                t_norm = s['title_en'].strip().lower()
                h = host('title_on')
                if h is not None:
                    titled.add(si)
                    if not any(t_norm == x for x in recent_titles[-12:]):
                        recent_titles.append(t_norm); fr = frames[h]
                        big = fr[2] * fr[3] > PW * PH * 0.6
                        pos = TEXTPOS.get(str(si), {}).get('title', 'bottom')
                        t = make_text(s['title_en'], fr, h, False, pos, big, side_of(h), forced=str(si) in TEXTPOS)
                        t['sec'] = si; t['kind'] = 'title'; texts.append(t)
            cap = s.get('caption_he') or s.get('caption') or ''
            if cap and si not in captioned:
                h = s.get('he_on', s.get('caption_on'))
                if h is None:
                    rest = [q for q in cand if not any(t['photo'] == q['i'] for t in texts)] or cand
                    h = rest[0]['i'] if rest else None
                elif h not in here: h = None
                if h is not None:
                    fr = frames[h]
                    where = 'top' if any(t['photo'] == h for t in texts) else 'bottom'
                    where = TEXTPOS.get(str(si), {}).get('he', where)
                    big = fr[2] * fr[3] > PW * PH * 0.6
                    hb = is_heb(cap)
                    t = make_text(cap, fr, h, hb, where, big, side_of(h), forced='he' in TEXTPOS.get(str(si), {}),
                                  fontname=None if hb else FONT_CAP)
                    t['sec'] = si; t['kind'] = 'he'; texts.append(t)
                    captioned.add(si)
        return texts

    for sp in spreads:
        if 'pano' in sp:
            p = sp['pano']; fr = frames_for(p, 'S')
            book.append(dict(kind='spread', layout='pano', frames=fr, items=p['photos'],
                             texts=captions_for(p['photos'], fr, lambda i: 'R')))
            continue
        fr = {}; items = []; side = {}
        for sd in (FIRST, SECOND):
            f = frames_for(sp[sd], sd); fr.update(f); items += sp[sd]['photos']
            for i in f: side[i] = sd
        book.append(dict(kind='spread', layout=sp['R']['kind'] + '/' + sp['L']['kind'], frames=fr, items=items,
                         texts=captions_for(items, fr, lambda i: side[i])))
    return book

# ---------------------------------------------------------------- preview
def font(sz, heb=False):
    for p in (['/System/Library/Fonts/Supplemental/Arial Hebrew.ttc', '/System/Library/Fonts/ArialHB.ttc'] if heb else
              ['/System/Library/Fonts/Supplemental/SnellRoundhand.ttc', '/System/Library/Fonts/Supplemental/Brush Script.ttf']):
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

def render(book, outdir, scale=0.18):
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir): os.remove(os.path.join(outdir, f))
    files = []
    for n, sp in enumerate(book):
        W = int(SW * scale); H = int(PH * scale)
        im = Image.new('RGB', (W, H), 'white')
        for i, (x, y, w, h) in sp['frames'].items():
            src = Image.open(f"{THUMBS}/{feat[i]['id']}.jpg").convert('RGB')
            left, top, cw, ch = crop_for(i, w, h)
            sw_, sh_ = src.size
            c = src.crop((int(left * sw_), int(top * sh_), int((left + cw) * sw_), int((top + ch) * sh_)))
            c = c.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            im.paste(c, (int(x * scale), int(y * scale)))
        dr = ImageDraw.Draw(im)
        for t in sp['texts']:
            txt = t['text'][::-1] if t['heb'] else t['text']   # PIL has no bidi: reverse for preview only
            f = font(int(t['size'] * scale * (0.9 if t['heb'] else 1.1)), t['heb'])
            tx, ty = t['x'] * scale, t['y'] * scale
            if t['align'] == 'right':
                tw = dr.textlength(txt, font=f); tx = (t['x'] + t['w']) * scale - tw
            col = (0, 0, 0) if t['color'] == 0 else (255, 255, 255)
            if t['shadow']: dr.text((tx + 1.5, ty + 1.5), txt, fill=(0, 0, 0), font=f)
            dr.text((tx, ty), txt, fill=col, font=f)
        dr.line([(W // 2, 0), (W // 2, H)], fill=(200, 200, 200), width=1)
        fn = os.path.join(outdir, f'spread_{n:02d}.jpg'); im.save(fn, quality=85); files.append(fn)
    return files

COVER_SPINE_X = COVER_W / 2
def build_extra(cur):
    ex = {}
    fi, bi = cur['front'], cur['back']
    left = (-BLEED, -BLEED, COVER_SPINE_X + BLEED, COVER_H + 2 * BLEED)
    right = (COVER_SPINE_X, -BLEED, COVER_W - COVER_SPINE_X + BLEED, COVER_H + 2 * BLEED)
    front, back = (left, right) if DIRECTION == 'RTL' else (right, left)   # RTL books: front cover = LEFT half
    T = []
    def tx(txt, x, y, size, align='left', heb=False, i=fi, fr=front):
        w = text_width(txt, size, heb)
        bx = x if align == 'left' else x - w
        try:
            br = region_brightness(i, fr, (bx, y, w, size * 1.15))
        except Exception:
            br = 0
        dark = br > 160                                   # dark text on bright areas, white + shadow otherwise
        T.append(dict(text=txt, x=bx, y=y, w=w, h=size * 1.15, size=size,
                      font=FONT_HE if heb else FONT_EN, heb=heb, align=align, color=0 if dark else 16777215,
                      shadow=not dark, photo=i, bright=round(br)))
    ct = cur.get('cover_text')
    missing = [k for k in ('title', 'subtitle', 'back') if not ct or k not in ct] + [k for k in ('page1_text', 'last_text') if k not in cur]
    if missing:
        sys.exit(f'curation.json is missing {missing} (cover_text.title/subtitle/back, page1_text, last_text; "" = none)')
    fx0 = max(front[0], 0) + 404                          # title inset from the front cover's left edge
    # back caption sits on the back cover's OUTER edge (right edge for RTL books, left edge for LTR books)
    back_outer_right = DIRECTION == 'RTL'
    bx1 = (min(back[0] + back[2], COVER_W) - 330) if back_outer_right else (max(back[0], 0) + 330)
    if ct['title']: tx(ct['title'], fx0, 282, ct.get('title_size', 200))
    if ct['subtitle']: tx(ct['subtitle'], fx0, 282 + ct.get('title_size', 200) * 1.15, ct.get('sub_size', 120))
    if ct['back']: tx(ct['back'], bx1, COVER_H - 350, 95, 'right' if back_outer_right else 'left', i=bi, fr=back)
    ex['cover'] = dict(frames={fi: front, bi: back}, texts=T, items=[])
    p1 = (-BLEED, -BLEED, PW + 2 * BLEED, PH + 2 * BLEED)
    ex['page1'] = dict(frames={cur['page1']: p1}, items=[],
                       texts=[make_text(cur['page1_text'], p1, cur['page1'], is_heb(cur['page1_text']), 'bottom', True, P1_SIDE)] if cur['page1_text'] else [])
    import re as _re
    lt = cur['last_text']; lh = is_heb(lt)
    ex['last'] = dict(frames={cur['last']: p1}, items=[],
                      texts=[make_text(lt, p1, cur['last'], lh, 'bottom', True, LAST_SIDE)] if lt else [])
    return ex

def render_extra(ex, outdir):
    global SW
    for name, W in (('cover', COVER_W), ('page1', PW), ('last', PW)):
        sw0 = SW; SW = W
        H0 = COVER_H if name == 'cover' else PH
        sp = ex[name]
        scale = 0.18
        im = Image.new('RGB', (int(W * scale), int(H0 * scale)), 'white')
        for i, (x, y, w, h) in sp['frames'].items():
            src = Image.open(f"{THUMBS}/{feat[int(i)]['id']}.jpg").convert('RGB')
            left, top, cw, ch = crop_for(int(i), w, h); a, b = src.size
            c = src.crop((int(left * a), int(top * b), int((left + cw) * a), int((top + ch) * b))).resize((max(1, int(w * scale)), max(1, int(h * scale))))
            im.paste(c, (int(x * scale), int(y * scale)))
        dr = ImageDraw.Draw(im)
        for t in sp['texts']:
            f = font(int(t['size'] * scale * 1.1)); dr.text((t['x'] * scale + 1.5, t['y'] * scale + 1.5), t['text'], fill=(0, 0, 0), font=f)
            dr.text((t['x'] * scale, t['y'] * scale), t['text'], fill=(255, 255, 255), font=f)
        if name == 'cover': dr.line([(int(COVER_SPINE_X * scale), 0), (int(COVER_SPINE_X * scale), im.height)], fill=(255, 0, 0))
        im.save(os.path.join(outdir, f'{name}.jpg'), quality=85)
        SW = sw0

if __name__ == '__main__':
    cur = json.load(open(sys.argv[1] if len(sys.argv) > 1 else f'{D}/curation.json'))
    CROP_OVR.update(cur.get('crops', {})); TEXTPOS.update(cur.get('textpos', {}))
    book = build(cur)
    extra = build_extra(cur)
    json.dump(extra, open(f'{D}/book_extra.json', 'w'), ensure_ascii=False)
    json.dump(book, open(f'{D}/book.json', 'w'))
    json.dump({'crops': CROP_OVR}, open(f'{D}/crops.json', 'w'))
    files = render(book, f'{D}/preview')
    render_extra(extra, f'{D}/preview')
    nphotos = sum(len(sp['frames']) for sp in book)
    print('spreads', len(book), 'inner pages', len(book) * 2, 'photos', nphotos)
    for n, sp in enumerate(book):
        print(n, sp['layout'], len(sp['frames']), [t['text'][:22] for t in sp['texts']])
