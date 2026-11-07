"""book.json (+ cover/page1/last) -> jPages in the editor's SaveProjectComplete format.
Usage: export.py <template_save_payload.json> <out_jpages.json>
Template payload supplies page skeleton keys and the exact object field sets the editor writes.
"""
import json, sys, os, uuid, copy, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L

D = L.D
tpl = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
_prof = json.load(open(f'{D}/profile.json'))
if _prof.get('DIRECTION') != 'RTL' and os.environ.get('ALLOW_LTR') != '1':
    sys.exit(f"profile.json DIRECTION is {_prof.get('DIRECTION')!r}: Picabook books are right-to-left. "
             "Set DIRECTION=RTL (pb_profile.py does), or ALLOW_LTR=1 only for a deliberate left-to-right book.")
print('direction', _prof.get('DIRECTION'))
book = json.load(open(f'{D}/book.json'))
if os.path.exists(f'{D}/crops.json'):
    L.CROP_OVR.update(json.load(open(f'{D}/crops.json'))['crops'])   # reviewer crop overrides
print('crop overrides', len(L.CROP_OVR))
extra = json.load(open(f'{D}/book_extra.json'))     # cover / page1 / last  (same structure as spreads)
widths = {}
if len(sys.argv) > 3:
    widths = json.load(open(sys.argv[3]))           # measured text widths: {font|size|text: px_at_size}

def uid(): return str(uuid.uuid1())

# find template objects
tp = tpl['jPages']
IMG_T = next(o for p in tp for o in p['objects'] if o.get('tipo') == 'img')
BG_SPREAD = next(o for o in tp[2]['objects'] if o.get('tipo') == 'background')
BG_PAGE = next(o for o in tp[1]['objects'] if o.get('tipo') == 'background')
BG_COVER = next(o for o in tp[0]['objects'] if o.get('tipo') == 'background')
TXT_O = next((o for p in tp for o in p['objects'] if o.get('tipo') == 'texto'), None)
TXT_T = next((t for p in tp for t in p.get('texts', [])), None)
if not (TXT_O and TXT_T):   # project saved without any text box: use the editor's standard text format
    TXT_O = dict(alpha=1, w=800, h=144, x=0, y=0, lock=False, alwaysUp=False, lockTextProperties=False, lockTextDimsProperties=False,
                 isSpineCoverText=False, printable=True, visibleInPreview=True, nome='', rodar=0, shadowAngle=360, shadowBlur=0,
                 shadowDist=0, shadowTransp=1, shadowColor=7829367, tipo='texto', link='', zIndex=0)
    TXT_T = dict(align='right', vAlign='top', textDirection='rtl', bold=False, change=True, color=0, font='ArialCFF', id='',
                 italic=False, size=120, sublinhado=False, texto='', plainText='', htmlText='', numLines=1, paragraphs='[]',
                 versionText='11', fromTheme=False, themeVariables='', capitalizeOption=0)
    print('no text box in the template: using the standard text format')
PAGE_KEYS = [k for k in tp[2].keys() if k != 'objects']
SCALE_ED = 0.15979822214154554

def page_skel(src):
    p = {k: copy.deepcopy(src[k]) for k in PAGE_KEYS}
    p['texts'] = []; p['fixedUID'] = uid()
    return p

def img_obj(i, frame, z):
    x, y, w, h = frame
    r = L.feat[i]; im = L.imgs[r['id']]
    M = im['M']
    iw, ih = im['width'] * M, im['height'] * M
    left, top, cw, ch = L.crop_for(i, w, h)
    o = copy.deepcopy(IMG_T)
    src = f"{im['url']}{im['storageFolder']}/{im['filerename']}"
    s = w / (cw * iw)
    o.update(dict(alpha=1, w=w, h=h, x=x, y=y, imgRot=0, imageVO=im['id'], imgName=im['filerename'],
                  imgWidth=iw, imgHeight=ih, imgScale=M, imgSrc=src, srcOriginal=src,
                  imgW=cw * iw, imgH=ch * ih, imgX=left * iw, imgY=top * ih, imgS=s * 0.10815,
                  checksum=im['checksum'], XL=im['XL'], L=im['L'], M=im['M'], S=im['S'], XS=im['XS'], XXS=im['XXS'],
                  storageFolder=im['storageFolder'], oldImage=False, idUrl=im.get('idUrl', 2), lock=False,
                  nome=uid(), imgUID=uid(), zIndex=z, tipo='img', rodar=0, mascara=False, contentor='quadrado',
                  uploadCompleted=True, imgStatus=6))
    return o

def text_objs(t, z):
    o = copy.deepcopy(TXT_O); tt = copy.deepcopy(TXT_T)
    tid = uid()
    key = f"{t['font']}|{t['size']}|{t['text']}"
    tw = widths.get(key)
    w = t['w']
    if tw:
        w = tw + t['size'] * 0.25
        if t['align'] == 'right': t['x'] = t['x'] + t['w'] - w
        t['w'] = w
    o.update(dict(alpha=1, w=w, h=t['h'], x=t['x'], y=t['y'], nome=tid, tipo='texto', zIndex=z, lock=False,
                  shadowAngle=360 if not t['shadow'] else 0, shadowBlur=10 if t['shadow'] else 0, shadowDist=0,
                  shadowTransp=1, shadowColor=0))
    lw = (tw or t['w']) * SCALE_ED
    para = [{"span": t['text'], "lines": [t['text']], "linesWidth": [lw], "scaleEditor": SCALE_ED}]
    tt.update(dict(align=t['align'], vAlign='top', textDirection='rtl' if t['heb'] else 'ltr', bold=False, change=True,
                   color=t['color'], font=t['font'], id=tid, italic=False, size=t['size'], sublinhado=False,
                   texto=html.escape(t['text'], quote=False), plainText='[' + t['text'] + ']',
                   htmlText=html.escape(t['text'], quote=False), numLines=1,
                   paragraphs=json.dumps(para, ensure_ascii=False, separators=(',', ':')).replace('"', '&quot;'), fromTheme=False,
                   themeVariables='', capitalizeOption=0))
    return o, tt

def build_page(sp, skel_src, bg, bgw, bgh):
    p = page_skel(skel_src)
    objs = []
    for b0 in [o for o in skel_src['objects'] if o.get('tipo') == 'background']:
        b = copy.deepcopy(b0); b.update(nome=uid(), backgroundColor=sp.get('bg', b0.get('backgroundColor', 16777215)))
        objs.append(b)
    z = 1
    for i, fr in sp['frames'].items():
        objs.append(img_obj(int(i), fr, z)); z += 1
    for t in sp['texts']:
        o, tt = text_objs(t, z); z += 1
        objs.append(o); p['texts'].append(tt)
    p['objects'] = objs
    return p

jp = []
jp.append(build_page(extra['cover'], tp[0], BG_COVER, BG_COVER['w'], BG_COVER['h']))
jp.append(build_page(extra['page1'], tp[1], BG_PAGE, L.PW, L.PH))
for sp in book:
    jp.append(build_page(sp, tp[2], BG_SPREAD, L.SW, L.PH))
jp.append(build_page(extra['last'], tp[-1], BG_PAGE, L.PW, L.PH))
json.dump(jp, open(OUT, 'w'), ensure_ascii=False)
_pc = tpl['project']['pageConfiguration']; _np = 2 + 2 * len(book); _have = tpl['project']['choosedData']['numberOfPages']
if not (_pc.get('min') or 0) <= _np <= (_pc.get('max') or 10**6):
    sys.exit(f"the book has {_np} pages but this product allows {_pc.get('min')}-{_pc.get('max')}: change TARGET (photos per spread) and re-run layout.py")
if _np != _have:
    print(f"NOTE: the book has {_np} pages, the project currently {_have}; saving sets it to {_np}. "
          f"To keep {_have}, re-run layout.py with a different TARGET (more photos per spread = fewer pages).")
print('jPages', len(jp), 'total pages', 2 + 2 * len(book), 'images', sum(1 for p in jp for o in p['objects'] if o['tipo'] == 'img'),
      'texts', sum(len(p['texts']) for p in jp))
