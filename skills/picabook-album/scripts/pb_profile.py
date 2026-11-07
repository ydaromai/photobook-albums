"""Captured editor save (SaveProjectComplete body) -> profile.json + restore copy + project summary.
Usage: BOOK_DIR=<dir> python3 pb_profile.py <save_template.json> [RTL|LTR]
The save template must come from THIS project after its page count was set in the editor (pages only in steps of 4)."""
import json, os, shutil, sys, time
D = os.environ['BOOK_DIR']; tpl = sys.argv[1]; direction = (sys.argv[2] if len(sys.argv) > 2 else 'RTL').upper()
s = json.load(open(tpl)); P = s['project']; pc = P['pageConfiguration']; cv = P['cover']
if not any(f.startswith('save.orig.') for f in os.listdir(D)):
    shutil.copy(tpl, f'{D}/save.orig.{time.strftime("%Y%m%d-%H%M%S")}.json')     # restore point (re-POST it to undo)
prof = dict(PW=pc['width'], PH=pc['height'], COVER_W=cv['maxWidth'], COVER_H=cv['height'], BLEED=30, DIRECTION=direction,
            FONT_TITLE='LobsterCFF', FONT_CAPTION='LobsterCFF', FONT_HE='AlefCFF', IMAGES='images.json',
            MIN_PAGES=pc.get('min'), MAX_PAGES=pc.get('max'))
json.dump(prof, open(f'{D}/profile.json', 'w'), indent=1)
items = sum(1 for p in s['jPages'] for o in p['objects'] if o.get('tipo') == 'img' and o.get('imageVO'))
texts = sum(1 for p in s['jPages'] for o in p['objects'] if o.get('tipo') == 'texto')
print(f"project {s['projectId']} '{P['choosedData'].get('title')}' | {P['choosedData'].get('coverName')} | "
      f"{P['choosedData']['numberOfPages']} pages (allowed {pc.get('min')}-{pc.get('max')}) | page {pc['width']:.0f}x{pc['height']:.0f} | "
      f"{items} placed photos, {texts} text boxes now | direction {direction}")
if items: print('NOTE: the project already has content — saving REPLACES it (restore copy saved as save.orig.*.json).')
