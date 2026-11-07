"""Resize photos for upload with safe unique names; skip videos; keep EXIF (dates, GPS).
Usage: python3 prepare_upload.py <source_dir> <BOOK_DIR>
<source_dir> may contain subfolders (an unzipped Google Photos "Download all" or Google Takeout export).
Writes <BOOK_DIR>/up/NNNN_<safe>.jpg, <BOOK_DIR>/up/list.json, <BOOK_DIR>/upload_map.json {uploaded_name: original_name}.
Converts with macOS `sips` when present, otherwise with Pillow (HEIC needs `pip install pillow-heif`).
The source folder is only READ — never modified or deleted."""
import json, os, re, shutil, subprocess, sys
src, D = os.path.expanduser(sys.argv[1]), sys.argv[2]
up = f'{D}/up'; os.makedirs(up, exist_ok=True)
IMG = ('.jpg', '.jpeg', '.heic', '.heif', '.png', '.tif', '.tiff', '.webp')
VID = ('.mov', '.mp4', '.m4v', '.avi', '.3gp', '.mkv')
files, skipped = [], 0
for root, dirs, names in os.walk(src):
    dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
    for f in sorted(names):
        if f.startswith('.'): continue
        if f.lower().endswith(IMG): files.append(os.path.join(root, f))
        elif f.lower().endswith(VID): skipped += 1
SIPS = shutil.which('sips')


def convert(path, out):
    if SIPS:
        g = subprocess.run([SIPS, '-g', 'pixelWidth', '-g', 'pixelHeight', path], capture_output=True, text=True).stdout
        big = max([int(x) for x in re.findall(r'pixel(?:Width|Height): (\d+)', g)] or [0]) > 3600   # never upscale
        r = subprocess.run([SIPS, '-s', 'format', 'jpeg', '-s', 'formatOptions', '88'] + (['-Z', '3600'] if big else []) +
                           [path, '--out', out], capture_output=True, text=True)
        return r.returncode == 0 and os.path.exists(out)
    from PIL import Image
    try:
        import pillow_heif; pillow_heif.register_heif_opener()
    except ImportError:
        pass
    try:
        im = Image.open(path); exif = im.info.get('exif')
        im.thumbnail((3600, 3600)); im = im.convert('RGB')
        im.save(out, 'JPEG', quality=88, **({'exif': exif} if exif else {}))   # orientation tag kept in EXIF
        return True
    except Exception:
        return False


names, mp, seen = [], {}, set()
for k, path in enumerate(files, 1):
    f = os.path.basename(path)
    if f.lower() in seen and os.path.getsize(path) in seen: continue      # same photo in two Takeout folders
    seen.update({f.lower(), os.path.getsize(path)})
    out = f"{k:04d}_{re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.splitext(f)[0])[:60]}.jpg"
    if not convert(path, os.path.join(up, out)):
        print('could not convert', path); continue
    names.append(out); mp[out] = f
json.dump(names, open(f'{up}/list.json', 'w')); json.dump(mp, open(f'{D}/upload_map.json', 'w'), ensure_ascii=False)
print(f'{len(names)} photos ready in {up} | {skipped} videos skipped')
