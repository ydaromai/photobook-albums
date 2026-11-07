"""Picabook project photos -> images.json + features.json (+ ~400px previews in <BOOK_DIR>/thumbs/<image_id>.jpg).

Usage: BOOK_DIR=<dir> [TZ_OFFSET_H=<hours>] python3 pb_features.py
Reads  <BOOK_DIR>/getproject.json   (the editor's Project/GetProject response)
       <BOOK_DIR>/up/ + upload_map.json  (prepare_upload.py) -> each Picabook photo is matched back to the file we
                                     uploaded by its pixels (Picabook renames new uploads), and takes its TRUE date and
                                     place from <BOOK_DIR>/meta.tsv (iCloud) or the file's own EXIF.
       <BOOK_DIR>/ts_override.json  optional {image_id: "YYYY-MM-DD HH:MM:SS"} (apply_placement.py)
Undated: WhatsApp-style copies (UUID file names) and photos without a camera date get day 'undated' -> place them by content.
Photos with no local file (already in the project): Picabook's stored date is shifted by the uploading computer's
       timezone; local = epoch + TZ_OFFSET_H. If unset, the offset is estimated (fewest night-time photos) — CHECK it
       with the user (it can be off by an hour).
"""
import json, os, re, urllib.request
import numpy as np
from PIL import Image, ImageOps
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import cv2

D = os.environ['BOOK_DIR']
UUIDNAME = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-', re.I)
g = json.load(open(f'{D}/getproject.json'))
dp = json.loads(g['result'][1]['data_project'].replace('#JSON_WE#', '', 1))
ims = [i for i in dp['images'] if not i.get('deleted')]
json.dump(ims, open(f'{D}/images.json', 'w'))
override = json.load(open(f'{D}/ts_override.json')) if os.path.exists(f'{D}/ts_override.json') else {}
os.makedirs(f'{D}/thumbs', exist_ok=True)


def fetch(im):
    dst = f"{D}/thumbs/{im['id']}.jpg"
    if os.path.exists(dst) and os.path.getsize(dst) > 1000: return
    stem = im['filerename'].rsplit('.', 1)[0]
    for suf in ('_m', '_l', '_s', ''):
        try:
            urllib.request.urlretrieve(f"{im['url']}{im['storageFolder']}/{stem}{suf}.jpg", dst); return
        except Exception:
            continue
    print('no preview for', im['id'])


with ThreadPoolExecutor(16) as ex: list(ex.map(fetch, ims))


def sig(gray):
    return cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32).flatten()


# ---- truth from the files we uploaded (iCloud metadata or EXIF), matched by pixels
meta = {}
if os.path.exists(f'{D}/meta.tsv'):
    for line in open(f'{D}/meta.tsv', encoding='utf-8'):
        r = line.rstrip('\n').split('\t')
        if len(r) < 5: continue
        try:
            dpart, secs = r[2].split(' '); y, mo, dd = map(int, dpart.split('-')); secs = int(float(secs))
            dt0 = datetime(y, mo, dd, secs // 3600, secs % 3600 // 60, secs % 60)
        except Exception:
            dt0 = None
        try: la, lo = float(r[3]), float(r[4])
        except ValueError: la = lo = 0.0
        meta[os.path.splitext(r[1])[0].lower()] = (dt0, la, lo)
truth = {}                                   # picabook image id -> (datetime|None, lat, lon, original name)
upmap = json.load(open(f'{D}/upload_map.json')) if os.path.exists(f'{D}/upload_map.json') else {}
if upmap and os.path.isdir(f'{D}/up'):
    local = []
    for name, orig in upmap.items():
        try: im0 = ImageOps.exif_transpose(Image.open(f'{D}/up/{name}'))
        except Exception: continue
        ex = im0.getexif().get_ifd(0x8769).get(36867) if hasattr(im0.getexif(), 'get_ifd') else None
        stem = os.path.splitext(orig)[0]
        m = meta.get(stem.lower())
        if UUIDNAME.match(stem): dt0 = None                       # WhatsApp copy: its date is when it was received
        elif m and m[0]: dt0 = m[0]
        elif ex:
            try: dt0 = datetime.strptime(str(ex)[:19], '%Y:%m:%d %H:%M:%S')
            except ValueError: dt0 = None
        else: dt0 = None
        im0.thumbnail((400, 400))
        local.append((name, im0.width / im0.height, sig(np.array(im0.convert('L'))), dt0, (m[1], m[2]) if m else (0, 0), orig))
    pairs = []
    for im in ims:
        th = cv2.imread(f"{D}/thumbs/{im['id']}.jpg", cv2.IMREAD_GRAYSCALE)
        if th is None: continue
        a, s0 = th.shape[1] / th.shape[0], sig(th)
        for k, l in enumerate(local):
            if abs(l[1] - a) <= 0.03: pairs.append((float(np.mean(np.abs(l[2] - s0))), im['id'], k))
    pairs.sort(); used_i, used_l = set(), set()
    for d0, iid, k in pairs:
        if iid in used_i or k in used_l or d0 > 25: continue
        used_i.add(iid); used_l.add(k); l = local[k]; truth[iid] = (l[3], l[4][0], l[4][1], l[5])
    print(f'matched {len(truth)} of {len(ims)} project photos to the uploaded files ({len(local)} files)')

# ---- photos with no local file: Picabook's stored date + timezone offset
rest = [im for im in ims if im['id'] not in truth and (im.get('exif') or {}).get('date') and not UUIDNAME.match(im.get('filename') or '')]
if os.environ.get('TZ_OFFSET_H'):
    OFF = float(os.environ['TZ_OFFSET_H'])
elif rest:
    night = lambda o: sum(1 for im in rest if 1 <= (datetime.fromtimestamp(im['exif']['date'] / 1000, timezone.utc) + timedelta(hours=o)).hour < 7)
    OFF = min(range(-12, 15), key=lambda o: (night(o), abs(o)))
    print(f'{len(rest)} photos dated by Picabook only: estimated TZ_OFFSET_H={OFF} — confirm with the user (set TZ_OFFSET_H to override)')
else:
    OFF = 0
fc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
rows = []
for im in ims:
    img = cv2.imread(f"{D}/thumbs/{im['id']}.jpg")
    if img is None: continue
    g8 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); h, w = g8.shape
    e = im.get('exif') or {}
    placed = str(im['id']) in override
    t = truth.get(im['id'])
    lat, lon = e.get('latitude') or 0, e.get('longitude') or 0
    if placed:
        dt = datetime.strptime(override[str(im['id'])], '%Y-%m-%d %H:%M:%S')
    elif t:
        dt = t[0]; lat, lon = (t[1], t[2]) if abs(t[2]) > 0.01 else (lat, lon)
    elif e.get('date') and not UUIDNAME.match(im.get('filename') or ''):
        dt = (datetime.fromtimestamp(e['date'] / 1000, timezone.utc) + timedelta(hours=OFF)).replace(tzinfo=None)
    else:
        dt = None
    small = cv2.resize(g8, (9, 8), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(cv2.resize(img, (32, 32)), cv2.COLOR_BGR2HSV)
    faces = fc.detectMultiScale(g8, 1.15, 5, minSize=(max(12, w // 30),) * 2)
    rows.append(dict(
        id=im['id'], fn=(truth[im['id']][3] if im['id'] in truth else im.get('filename')) or str(im['id']), W=int(im['width']), H=int(im['height']),
        ts=int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000) if dt else 0,
        local=dt.strftime('%Y-%m-%d %H:%M:%S') if dt else '0000-00-00 00:00:00',
        day=dt.strftime('%Y-%m-%d') if dt else 'undated', dated=bool(dt), trusted=bool(dt) and not placed,
        lat=lat, lon=lon, gps=abs(lon) > 0.01,
        sharp=float(cv2.Laplacian(g8, cv2.CV_64F).var()), bright=float(g8.mean()), contrast=float(g8.std()),
        dhash=int(''.join('1' if b else '0' for b in (small[:, 1:] > small[:, :-1]).flatten()), 2),
        hist=[float(x) for x in cv2.normalize(cv2.calcHist([hsv], [0, 1], None, [8, 4], [0, 180, 0, 256]), None).flatten()],
        faces=[[round(x / w, 3), round(y / h, 3), round(fw / w, 3), round(fh / h, 3)] for (x, y, fw, fh) in faces]))
rows.sort(key=lambda r: (not r['dated'], r['ts'], r['fn']))
json.dump(rows, open(f'{D}/features.json', 'w'))
hours = sorted(int(r['local'][11:13]) for r in rows if r['dated'])
und = sum(1 for r in rows if not r['dated'])
print(f'{len(rows)} photos | {und} undated | capture hours p10..p90: '
      f'{hours[len(hours) // 10] if hours else "-"}..{hours[len(hours) * 9 // 10] if hours else "-"} (should look like waking hours)')
