export const meta = {
  name: 'picabook-curate-and-review',
  description: 'Curate a trip photobook per day-group (dedupe, keep every occasion, heroes/panoramas with people, English captions anchored to photos), then adversarially review each group',
  phases: [{ title: 'Curate' }, { title: 'Review' }],
}
// args: { bookDir, context: "who/where/when + owner wishes", groups: [{key:'A', lo:30, hi:40}, ...],
//         direction: 'RTL'|'LTR' (default RTL), captionLanguage: 'Hebrew'|'English' (default Hebrew) }
// Each group needs <bookDir>/legs/<key>.md (scripts/legs.py) listing its contact sheets.
const B = args.bookDir
const GROUPS = args.groups
const SEC = {
  type: 'object',
  properties: {
    sections: { type: 'array', items: { type: 'object', properties: {
      date: { type: 'string' },
      title: { type: 'string', description: 'short, correct place/occasion label in English (script font), e.g. "Bondi Beach"; "" if none' },
      title_on: { type: 'integer', description: 'photo index the label is printed on (-1 if none)' },
      caption: { type: 'string', description: 'optional short warm/funny line (2-7 words) in the caption language, "" if none' },
      caption_on: { type: 'integer', description: 'photo index whose CONTENT the line is about (-1 if none)' },
      photos: { type: 'array', items: { type: 'object', properties: {
        i: { type: 'integer' }, role: { type: 'string', enum: ['spread', 'page', 'large', 'normal', 'small'] }, why: { type: 'string' } }, required: ['i', 'role', 'why'] } },
    }, required: ['date', 'title', 'title_on', 'caption', 'caption_on', 'photos'] } },
    cover_candidates: { type: 'array', items: { type: 'integer' } },
    notes: { type: 'string' },
  },
  required: ['sections', 'cover_candidates', 'notes'],
}
const REV = { type: 'object', properties: { ...SEC.properties, changes: { type: 'array', items: { type: 'string' } } }, required: [...SEC.required, 'changes'] }
const STYLE = `
CONTEXT: ${args.context}
The book is a printed Picabook photobook, ${(args.direction || 'RTL') === 'RTL' ? 'right-to-left (Hebrew) binding — the RIGHT page of each spread comes first' : 'left-to-right'}; captions: English place labels in a script font laid over photos + occasional short playful lines in ${args.captionLanguage || 'Hebrew'}.

OWNER RULES (mandatory):
1. Don't use all photos; be smart; NEVER miss an occasion (every place, event, meal, hotel, activity, transport moment keeps >=1 photo); remove duplicates/near-duplicates (keep the best: sharp, eyes open, everyone in frame).
2. Big images: "page" = full-page bleed (2-4 per group), "large" = half page (3-8 per group). "small" = incidental objects/signs/food kept only for the story.
3. "spread" = two-page panorama: ONLY a wide scene that clearly includes the people, with no face at the centre (the book fold). 0-1 per group. Pure landscapes are never spreads.
4. Captions sit on the photo they describe (title_on / caption_on). Correct place names only (GPS hints in the brief; if unsure use a broader name). Lines are natural, correct ${args.captionLanguage || 'Hebrew'}, warm, 2-7 words, each unique, no people's names unless the context gives them. About one line per 2 sections.
5. Exclude off-story photos (screenshots, maps, receipts, blurry, unflattering).
6. Keep chronological order (index order).
Read the brief, LOOK at every contact sheet listed (Read the .jpg), open ${B}/thumbs/<id>.jpg previews when needed.`
const res = await pipeline(GROUPS,
  g => agent(`${STYLE}\n\nCurate group ${g.key}. Brief: ${B}/legs/${g.key}.md. Target ${g.lo}-${g.hi} photos.`, { label: `curate:${g.key}`, phase: 'Curate', schema: SEC }),
  (d, g) => d && agent(`${STYLE}\n\nYou are an independent, skeptical photo editor. Review this DRAFT for group ${g.key} (brief ${B}/legs/${g.key}.md; look at every contact sheet yourself). Hunt for: missed occasions, near-duplicates, weak picks with better alternatives, wrong/invented place names, captions on the wrong photo, unnatural or repeated lines, spreads without people or with a face at the centre, off-story photos, chronology errors. Return the FULL corrected selection and a list of changes.\nDRAFT:\n${JSON.stringify(d)}`, { label: `review:${g.key}`, phase: 'Review', schema: REV }))
return GROUPS.map((g, k) => ({ key: g.key, result: res[k] }))
