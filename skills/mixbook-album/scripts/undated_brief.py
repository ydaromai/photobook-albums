"""After group.py: write <BOOK_DIR>/placement_brief.md for references/workflows/place-undated-photos.js.
Usage: BOOK_DIR=<dir> python3 undated_brief.py "<route hints: day -> places>" """
import json, os, sys
D = os.environ['BOOK_DIR']; hints = sys.argv[1] if len(sys.argv) > 1 else ''
R = json.load(open(f'{D}/grouped.json'))
und = [r for r in R if r['day'] == 'undated']
sheets = sorted(f for f in os.listdir(f'{D}/sheets') if f.endswith('.jpg'))
L = ['# Placing undated photos in time', '',
     f'{len(R) - len(und)} photos have a TRUSTED capture time. {len(und)} photos are UNDATED (their day is "undated"); '
     'their real moment must be found from their content (places, landmarks, people, outfits, weather, light).', '',
     '## Route / day hints', hints or '(none given)', '', '## Contact sheets (tiles "#index HH:MM m<moment>")'] + \
    [f'- {D}/sheets/{s}' for s in sheets] + ['', f'Undated photos (W#): ' + ', '.join(f"#{r['i']}" for r in und),
                                              f'Larger previews: {D}/thumbs/<id>.jpg (ids in {D}/grouped.json)']
open(f'{D}/placement_brief.md', 'w').write('\n'.join(L))
print(f'{len(und)} undated photos -> placement_brief.md (pass args.count={len(und)})')
