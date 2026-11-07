export const meta = {
  name: 'mixbook-place-undated-photos',
  description: 'Place undated photos (WhatsApp copies, scans) into the trusted camera timeline by content: 3 independent placers + arbiter on disagreements',
  phases: [
    { title: 'Place', detail: '3 independent placers' },
    { title: 'Arbitrate', detail: 'resolve photos where placers disagree' },
  ],
}
const B = args.bookDir   // args: {bookDir, count: <number of undated photos (undated_brief.py prints it)>}
const N = args.count
const SCHEMA = {
  type: 'object',
  properties: {
    placements: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          w: { type: 'integer', description: 'undated photo index (W#)' },
          day: { type: 'string', description: 'YYYY-MM-DD the photo was really taken' },
          after: { type: 'integer', description: 'index of the CAMERA photo (#) it should come right after in time order (use the closest matching moment); -1 if before all photos of that day' },
          moment: { type: 'string', description: 'short description of the moment/place (e.g. "Holzgau suspension bridge")' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          evidence: { type: 'string', description: 'what visual evidence ties it there (landmark, river, trail, outfit, weather, people, companion photo #N of the same scene)' },
          exclude: { type: 'string', description: 'non-empty if the photo should not be in the book (not from this trip, meme/screenshot, unusable). Otherwise ""' },
        },
        required: ['w', 'day', 'after', 'moment', 'confidence', 'evidence', 'exclude'],
      },
    },
  },
  required: ['placements'],
}
const LENS = [
  'Work landmark-first: identify places (bridges, lakes, villages, signs, river character, mountains) and match them to the camera photos of the same place.',
  'Work people/outfit-first: who is in the photo, what they wear (on each day people usually wear different clothes), backpacks, weather/light; match to camera photos of the same day.',
  'Work sequence-first: for each day, reconstruct the order of places/activities from the camera photos, then slot each undated photo where its scene fits between consecutive camera photos.',
]
const prompt = (lens) => `Read ${B}/placement_brief.md and LOOK at every contact sheet it lists (Read the .jpg files); open larger previews (thumbs) when needed. ${lens}\nFor EVERY one of the ${N} undated photos (W#), decide the real day and the camera photo (#) it should follow. Be honest with confidence. Return all ${N}.`
phase('Place')
const runs = (await parallel(LENS.map((l, k) => () => agent(prompt(l), { label: `place:${k + 1}`, phase: 'Place', schema: SCHEMA })))).filter(Boolean)
// merge
const byW = {}
runs.forEach((r, k) => r.placements.forEach(p => { (byW[p.w] = byW[p.w] || []).push({ ...p, run: k }) }))
const agreed = [], disputed = []
for (const [w, ps] of Object.entries(byW)) {
  const days = ps.map(p => p.day); const dayMaj = days.sort((a, b) => days.filter(x => x === b).length - days.filter(x => x === a).length)[0]
  const sameDay = ps.filter(p => p.day === dayMaj)
  const afters = sameDay.map(p => p.after); const span = Math.max(...afters) - Math.min(...afters)
  const excl = ps.filter(p => p.exclude).length
  if (sameDay.length === ps.length && span <= 3 && excl === 0 && ps.length >= 2) agreed.push({ w: +w, day: dayMaj, after: Math.round(afters.reduce((a, b) => a + b, 0) / afters.length), moment: sameDay[0].moment, exclude: '' })
  else disputed.push({ w: +w, opinions: ps })
}
log(`${agreed.length} agreed, ${disputed.length} disputed`)
phase('Arbitrate')
let arb = { placements: [] }
if (disputed.length) {
  arb = await agent(`Read ${B}/placement_brief.md and look at the contact sheets. Three independent editors disagreed about where these undated photos belong. For each, look at the photo yourself (thumbs/<id>.jpg; ids in ${B}/features.json) and at the candidate camera photos, and give the final placement (or exclude with reason). Disputes:\n${JSON.stringify(disputed)}`,
    { label: 'arbitrate', phase: 'Arbitrate', schema: SCHEMA })
}
return { agreed, arbitrated: arb ? arb.placements : [], disputedCount: disputed.length }
