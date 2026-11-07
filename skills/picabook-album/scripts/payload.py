"""Build SaveProjectComplete payload: fresh editor payload + our jPages."""
import json, sys
tpl = json.load(open(sys.argv[1])); jp = json.load(open(sys.argv[2])); out = sys.argv[3]
p = dict(tpl)
p['jPages'] = jp
proj = dict(tpl['project'])
cd = dict(proj['choosedData']); npages = 2 + 2 * (len(jp) - 3)
cd['numberOfPages'] = npages; proj['choosedData'] = cd
proj['pagesListOrder'] = [{'fixedUID': pg['fixedUID'], 'toSave': True} for pg in jp]
p['project'] = proj
json.dump(p, open(out, 'w'), ensure_ascii=False)
print('pages', npages, 'jPages', len(jp), 'bytes', len(json.dumps(p, ensure_ascii=False)))
