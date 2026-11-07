"""Resize photos for upload with safe unique names; skip videos; keep EXIF.
Usage: python3 prepare_upload.py <source_dir> <BOOK_DIR>
Writes <BOOK_DIR>/up/NNNN_<safe>.jpg, <BOOK_DIR>/up/list.json, <BOOK_DIR>/upload_map.json {uploaded_name: original_name}.
The source folder is only READ — never modified or deleted."""
import json, os, re, subprocess, sys
src, D = sys.argv[1], sys.argv[2]
up = f'{D}/up'; os.makedirs(up, exist_ok=True)
IMG = ('.jpg', '.jpeg', '.heic', '.heif', '.png', '.tif', '.tiff', '.webp')
files = sorted(f for f in os.listdir(src) if f.lower().endswith(IMG))
skipped = [f for f in os.listdir(src) if f.lower().endswith(('.mov', '.mp4', '.m4v', '.avi'))]
names, mp = [], {}
for k, f in enumerate(files, 1):
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.splitext(f)[0])[:60]
    out = f'{k:04d}_{safe}.jpg'
    r = subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '88', '-Z', '3600',
                        os.path.join(src, f), '--out', os.path.join(up, out)], capture_output=True, text=True)
    if r.returncode or not os.path.exists(os.path.join(up, out)):
        print('could not convert', f); continue
    names.append(out); mp[out] = f
json.dump(names, open(f'{up}/list.json', 'w')); json.dump(mp, open(f'{D}/upload_map.json', 'w'), ensure_ascii=False)
print(f'{len(names)} photos ready in {up} | {len(skipped)} videos skipped')
