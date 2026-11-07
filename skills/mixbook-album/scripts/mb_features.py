"""Mixbook project content -> features.json (+ ~700px previews in <BOOK_DIR>/thumbs/<photo_id>.jpg).

Usage: BOOK_DIR=<dir> python3 mb_features.py
Reads  <BOOK_DIR>/content.json      (GET /api/v2/my/projects/{pid}/content)
       <BOOK_DIR>/ts_override.json  optional {photo_id: "YYYY-MM-DD HH:MM:SS"} — times for undated photos (apply_placement.py)
       <BOOK_DIR>/meta.tsv          optional iCloud metadata (album_meta.applescript) — GPS by file name when Mixbook has none
Env:   EXCLUDE_NAMES=regex          skip photos whose file name matches
Output schema matches group.py / legs.py / layout.py. Undated photos get day='undated', ts=0 and sort last.
"""
import json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import cv2

D = os.environ['BOOK_DIR']
content = json.load(open(f'{D}/content.json'))
proj = content['data']['project'] if 'data' in content else content
excl = re.compile(os.environ['EXCLUDE_NAMES']) if os.environ.get('EXCLUDE_NAMES') else None
override = json.load(open(f'{D}/ts_override.json')) if os.path.exists(f'{D}/ts_override.json') else {}
os.makedirs(f'{D}/thumbs', exist_ok=True)

meta_gps = {}
if os.path.exists(f'{D}/meta.tsv'):
    for line in open(f'{D}/meta.tsv', encoding='utf-8'):
        r = line.rstrip('\n').split('\t')
        if len(r) >= 5 and r[3] not in ('', 'missing value'):
            try: meta_gps[os.path.splitext(r[1])[0].lower()] = (float(r[3]), float(r[4]))
            except ValueError: pass

upload_map = json.load(open(f'{D}/upload_map.json')) if os.path.exists(f'{D}/upload_map.json') else {}
photos = [p for p in proj['photos'] if not (excl and excl.search(p.get('name') or ''))]


def preview_url(p):
    urls = sorted(p['urls'], key=lambda u: max(u['width'], u['height']))
    return next((u['url'] for u in urls if max(u['width'], u['height']) >= 700), urls[-1]['url'])


def fetch(p):
    dst = f"{D}/thumbs/{p['id']}.jpg"
    if os.path.exists(dst) and os.path.getsize(dst) > 1000: return
    try: urllib.request.urlretrieve(preview_url(p), dst)
    except Exception as e: print('download failed', p.get('name'), e)


with ThreadPoolExecutor(16) as ex: list(ex.map(fetch, photos))


def parse(s):
    """Mixbook taken_at is the camera wall-clock ('2024-08-04T21:45:24'). No fallback to upload time."""
    if not s: return None
    try: return datetime.fromisoformat(str(s).replace('Z', '+00:00').replace(' ', 'T')).replace(tzinfo=None)
    except ValueError: return None


fc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
rows = []
for p in photos:
    img = cv2.imread(f"{D}/thumbs/{p['id']}.jpg")
    if img is None:
        print('missing preview', p['id'], p.get('name')); continue
    g8 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); h, w = g8.shape
    placed = str(p['id']) in override
    dt = parse(override.get(str(p['id']))) or parse(p.get('taken_at'))
    lat, lon = p.get('location_latitude'), p.get('location_longitude')
    if not (lat and lon):
        orig = upload_map.get(p.get('name') or '', p.get('name') or '')
        lat, lon = meta_gps.get(os.path.splitext(orig)[0].lower(), (0, 0))
    faces = []
    for f in p.get('faces') or []:          # Mixbook face boxes (relative) when present
        try: faces.append([round(f['rel_x'], 3), round(f['rel_y'], 3), round(f['rel_width'], 3), round(f['rel_height'], 3)])
        except (KeyError, TypeError): pass
    if not faces:
        faces = [[round(x / w, 3), round(y / h, 3), round(fw / w, 3), round(fh / h, 3)]
                 for (x, y, fw, fh) in fc.detectMultiScale(g8, 1.15, 5, minSize=(max(12, w // 30),) * 2)]
    small = cv2.resize(g8, (9, 8), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(cv2.resize(img, (32, 32)), cv2.COLOR_BGR2HSV)
    rows.append(dict(
        id=p['id'], fn=p.get('name') or str(p['id']), W=p['width'], H=p['height'],
        ts=int(dt.timestamp() * 1000) if dt else 0,
        local=dt.strftime('%Y-%m-%d %H:%M:%S') if dt else '0000-00-00 00:00:00',
        day=dt.strftime('%Y-%m-%d') if dt else 'undated', dated=bool(dt), trusted=bool(dt) and not placed,
        lat=lat or 0, lon=lon or 0, gps=bool(lat and lon),
        sharp=float(cv2.Laplacian(g8, cv2.CV_64F).var()), bright=float(g8.mean()), contrast=float(g8.std()),
        dhash=int(''.join('1' if b else '0' for b in (small[:, 1:] > small[:, :-1]).flatten()), 2),
        hist=[float(x) for x in cv2.normalize(cv2.calcHist([hsv], [0, 1], None, [8, 4], [0, 180, 0, 256]), None).flatten()],
        faces=faces, focus=p.get('focus_point')))
rows.sort(key=lambda r: (not r['dated'], r['ts'], r['fn']))
json.dump(rows, open(f'{D}/features.json', 'w'))
undated = sum(1 for r in rows if not r['dated'])
print(f'{len(rows)} photos | {undated} undated' + (' -> run undated_brief.py + references/workflows/place-undated-photos.js before curating'
                                                   if undated else ''))
