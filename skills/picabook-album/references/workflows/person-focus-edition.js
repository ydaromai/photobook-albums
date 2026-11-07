export const meta = {
  name: 'picabook-person-focus-edition',
  description: 'Per-person edition: tag who appears in each photo (reference sheet), re-curate each group with the focus people as the stars, adversarially review',
  phases: [{ title: 'Tag people' }, { title: 'Curate' }, { title: 'Review' }],
}
// args: {
//   bookDir, context,
//   people: "NAME = how to recognise (beard, hair, glasses...); NAME2 = ...",   // + <bookDir>/people_reference.jpg
//   names: ["Dana", "Tom", "Alex", "Sam"], focus: ["Dana", "Tom"],
//   groups: [{key:'A', first:0, last:82, lo:34, hi:44}, ...],
//   previous: "<bookDir>/curation_prev.json"   // optional: the earlier edition = occasion checklist
// }
const B = args.bookDir
const FOCUS = args.focus.join(' and ')
const TAGS = { type: 'object', properties: { photos: { type: 'array', items: { type: 'object', properties: {
  i: { type: 'integer' },
  people: { type: 'array', items: { type: 'object', properties: { name: { type: 'string', enum: args.names }, level: { type: 'integer', description: '1 present/small, 2 prominent' } }, required: ['name', 'level'] } },
  note: { type: 'string', description: 'very short: who/what' } }, required: ['i', 'people', 'note'] } } }, required: ['photos'] }
const SEC = { type: 'object', properties: {
  sections: { type: 'array', items: { type: 'object', properties: {
    date: { type: 'string' }, title: { type: 'string' }, title_on: { type: 'integer' }, caption: { type: 'string' }, caption_on: { type: 'integer' },
    photos: { type: 'array', items: { type: 'object', properties: { i: { type: 'integer' }, role: { type: 'string', enum: ['spread', 'page', 'large', 'normal', 'small'] }, why: { type: 'string' } }, required: ['i', 'role', 'why'] } } },
    required: ['date', 'title', 'title_on', 'caption', 'caption_on', 'photos'] } },
  cover_candidates: { type: 'array', items: { type: 'integer' } }, notes: { type: 'string' } }, required: ['sections', 'cover_candidates', 'notes'] }
const REV = { type: 'object', properties: { ...SEC.properties, changes: { type: 'array', items: { type: 'string' } } }, required: [...SEC.required, 'changes'] }
const PEOPLE = `People (Read the reference sheet ${B}/people_reference.jpg first): ${args.people}`
const RULES = `
CONTEXT: ${args.context}
This is the ${FOCUS} edition. FOCUS RULES:
- Same story: every occasion keeps >=1 photo${args.previous ? ` (use ${args.previous} as the occasion checklist; do not just copy its heroes)` : ''}, chronological, no near-duplicates.
- Prefer photos where ${FOCUS} are visible, especially prominent; their couple/solo shots are the stars.
- Heroes ("page" 2-4 per group, "large" 3-8) must feature ${FOCUS}; group shots including them are fine.
- "spread" (0-1 per group): a wide scene including ${FOCUS}; the centre fold must not cut a face.
- Photos without any of ${FOCUS}: only when needed for an occasion, as "normal"/"small", never heroes. "small" = incidental objects.
- Captions: English place label (title, on a photo of that place = title_on) + about one short warm line in ${args.captionLanguage || 'Hebrew'} per 2 sections (caption on the photo it is about = caption_on); unique, natural; -1 when none.`
const res = await pipeline(args.groups,
  g => agent(`${PEOPLE}\n\nTag EVERY photo #${g.first}..#${g.last} with who appears. Brief/contact sheets: ${B}/legs/${g.key}.md. For small faces Read ${B}/thumbs/<id>.jpg (ids in the brief). Distinguish look-alikes carefully using the reference.`, { label: `tag:${g.key}`, phase: 'Tag people', schema: TAGS }),
  (tags, g) => tags && agent(`${PEOPLE}\n${RULES}\n\nCurate group ${g.key} (photos #${g.first}..#${g.last}). Brief + contact sheets: ${B}/legs/${g.key}.md. Target ${g.lo}-${g.hi} photos.\nPeople tags:\n${JSON.stringify(tags.photos)}`, { label: `curate:${g.key}`, phase: 'Curate', schema: SEC }).then(r => r && ({ r, tags })),
  (x, g) => x && agent(`${PEOPLE}\n${RULES}\n\nYou are an independent skeptical editor reviewing the ${FOCUS} edition DRAFT for group ${g.key} (brief ${B}/legs/${g.key}.md; open previews to verify who is in the hero photos). Check heroes really feature ${FOCUS}; every occasion covered; no near-duplicates; spread fold OK; captions on the right photos; lines unique and natural; correct place names. Return the FULL corrected selection + changes.\nTags: ${JSON.stringify(x.tags.photos)}\nDRAFT: ${JSON.stringify(x.r)}`, { label: `review:${g.key}`, phase: 'Review', schema: REV }).then(r => ({ result: r, tags: x.tags.photos })))
return args.groups.map((g, k) => ({ key: g.key, ...(res[k] || {}) }))
