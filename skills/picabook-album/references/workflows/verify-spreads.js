export const meta = {
  name: 'picabook-verify-spreads',
  description: 'Verify every rendered spread (crops, frame sizes, caption hosts/readability, panoramas, focus people, off-story photos) and return machine-applicable fixes',
  phases: [{ title: 'Verify' }],
}
// args: { bookDir, context, spreads: <number of spreads>, focus?: "who must be in focus (optional)", perAgent?: 9 }
// Needs <bookDir>/review/spread_NN.md manifests + preview/*.jpg (see SKILL.md step 6).
const D = args.bookDir
const FIX = { type: 'object', properties: {
  hosts: { type: 'array', items: { type: 'object', properties: { section: { type: 'integer' }, kind: { type: 'string', enum: ['title', 'caption'] }, photo: { type: 'integer' }, reason: { type: 'string' } }, required: ['section', 'kind', 'photo', 'reason'] } },
  textpos: { type: 'array', items: { type: 'object', properties: { section: { type: 'integer' }, kind: { type: 'string', enum: ['title', 'caption'] }, pos: { type: 'string', enum: ['top', 'bottom'] }, reason: { type: 'string' } }, required: ['section', 'kind', 'pos', 'reason'] } },
  texts: { type: 'array', items: { type: 'object', properties: { section: { type: 'integer' }, kind: { type: 'string', enum: ['title', 'caption'] }, text: { type: 'string', description: 'replacement, "" to remove' }, reason: { type: 'string' } }, required: ['section', 'kind', 'text', 'reason'] } },
  crops: { type: 'array', items: { type: 'object', properties: { i: { type: 'integer' }, x: { type: 'number', description: '0=keep left edge .. 1=keep right edge' }, y: { type: 'number', description: '0=keep top .. 1=keep bottom' }, reason: { type: 'string' } }, required: ['i', 'x', 'y', 'reason'] } },
  roles: { type: 'array', items: { type: 'object', properties: { i: { type: 'integer' }, role: { type: 'string', enum: ['small', 'normal', 'large', 'page'] }, reason: { type: 'string' } }, required: ['i', 'role', 'reason'] } },
  drops: { type: 'array', items: { type: 'object', properties: { i: { type: 'integer' }, reason: { type: 'string' } }, required: ['i', 'reason'] } },
  other: { type: 'array', items: { type: 'string' } },
}, required: ['hosts', 'textpos', 'texts', 'crops', 'roles', 'drops', 'other'] }
const BRIEF = `You verify a printed family photobook before print. CONTEXT: ${args.context}
Owner rules: captions sit on the photo they describe, readable, not over faces; modest label size; two-page panoramas include the people and the centre fold cuts no face; no near-duplicates; no off-story photos; incidental objects/signs/food never get bigger frames than people photos on the same page.${args.focus ? ` FOCUS: ${args.focus} must be in the big frames; photos without them stay small.` : ''}
Preview renders use a stand-in font. For each spread: Read its manifest and preview image; open originals (paths in the manifest) to judge crops. Return ONLY real problems with concrete fixes; empty arrays if all good.`
const n = args.spreads, per = args.perAgent || 9
const batches = []
for (let a = 0; a < n; a += per) batches.push(Array.from({ length: Math.min(per, n - a) }, (_, k) => a + k))
const pad = x => String(x).padStart(2, '0')
return await parallel(batches.map(ns => () => agent(`${BRIEF}\n\nYour spreads: ${ns.map(pad).join(', ')} (manifests ${D}/review/spread_NN.md).${ns[0] === 0 ? ` Also check ${D}/preview/cover.jpg, page1.jpg, last.jpg.` : ''}`,
  { label: `verify:${ns[0]}-${ns[ns.length - 1]}`, phase: 'Verify', schema: FIX })))
