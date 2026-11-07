"""Apply place-undated-photos.js results -> <BOOK_DIR>/ts_override.json, then re-run mb_features.py + group.py.
Usage: BOOK_DIR=<dir> python3 apply_placement.py <placement_result.json>"""
import json, os, sys
from datetime import datetime, timedelta
D = os.environ['BOOK_DIR']
res = json.load(open(sys.argv[1]))
P = {p['w']: p for p in res.get('agreed', [])}; P.update({p['w']: p for p in res.get('arbitrated', [])})
R = {r['i']: r for r in json.load(open(f'{D}/grouped.json'))}
ov = json.load(open(f'{D}/ts_override.json')) if os.path.exists(f'{D}/ts_override.json') else {}
count, excluded = {}, []
for w, p in sorted(P.items()):
    if p.get('exclude'): excluded.append(w); continue
    a = p.get('after', -1)
    if a in R and R[a]['dated']:
        base = datetime.strptime(R[a]['local'], '%Y-%m-%d %H:%M:%S')
    else:   # before the first photo of that day
        day = [r for r in R.values() if r['day'] == p['day'] and r['dated']]
        base = (min(datetime.strptime(r['local'], '%Y-%m-%d %H:%M:%S') for r in day) if day
                else datetime.strptime(p['day'] + ' 12:00:00', '%Y-%m-%d %H:%M:%S')) - timedelta(minutes=1)
    count[a] = count.get(a, 0) + 1
    ov[str(R[w]['id'])] = (base + timedelta(seconds=count[a])).strftime('%Y-%m-%d %H:%M:%S')
json.dump(ov, open(f'{D}/ts_override.json', 'w'), indent=1)
print(f'{len(ov)} placed, {len(excluded)} excluded {excluded} -> re-run mb_features.py and group.py (indices change)')
