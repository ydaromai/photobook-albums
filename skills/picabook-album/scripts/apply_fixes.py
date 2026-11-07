"""Merge verify-spreads.js fixes into a curation file.
Usage: python3 apply_fixes.py <curation_in.json> <verify_result.json> <curation_out.json>
verify_result.json = the workflow's returned array (one object per checker).
kind 'caption' maps to the engine's second-caption slot ('he' in TEXTPOS / caption_on anchor).
"""
import json, sys
cur = json.load(open(sys.argv[1])); res = [x for x in json.load(open(sys.argv[2])) if x]
S = cur['sections']; cur.setdefault('crops', {}); cur.setdefault('textpos', {})
anchor = {'title': 'title_on', 'caption': 'caption_on'}
field = {'title': 'title', 'caption': 'caption'}
slot = {'title': 'title', 'caption': 'he'}
roles, drops = {}, set()
for x in res:
    for h in x.get('hosts', []): S[h['section']][anchor[h['kind']]] = h['photo']
    for t in x.get('textpos', []): cur['textpos'].setdefault(str(t['section']), {})[slot[t['kind']]] = t['pos']
    for t in x.get('texts', []):
        s = S[t['section']]
        if t['kind'] == 'title': s['title'] = t['text']; s.pop('title_en', None)
        else: s['caption'] = t['text']; s.pop('caption_he', None)
    for c in x.get('crops', []): cur['crops'][str(c['i'])] = {'x': c['x'], 'y': c['y']}
    for r in x.get('roles', []): roles[r['i']] = r['role']
    for d in x.get('drops', []): drops.add(d['i'])
for s in S:
    s['photos'] = [dict(p, role=roles.get(p['i'], p['role'])) for p in s['photos'] if p['i'] not in drops]
    for k in ('title_on', 'caption_on', 'he_on'):
        if s.get(k) in drops: s.pop(k)
cur['sections'] = S          # never drop sections: fixes reference them by index
json.dump(cur, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
print(f"applied: {sum(len(x.get('hosts', [])) for x in res)} hosts, {sum(len(x.get('textpos', [])) for x in res)} positions, "
      f"{sum(len(x.get('texts', [])) for x in res)} texts, {len(cur['crops'])} crops, {len(roles)} roles, {len(drops)} drops")
for x in res:
    for o in x.get('other', []): print('NOTE:', o[:300])
