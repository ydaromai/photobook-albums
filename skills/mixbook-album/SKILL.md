---
name: mixbook-album
description: Build or rebuild a Mixbook (mixbook.com) photo book end to end — curate hundreds of trip/event photos (dedupe, keep every occasion, heroes and panoramas with the people in them), lay them out (mosaics, full bleeds, two-page panoramas, English place labels and short captions on the photo they describe) and save the whole book in one call through the Mixbook editor's own API instead of clicking. Photos can come from an iCloud Photos album (Mac), a folder, Google Photos, or photos already in the Mixbook project. Also handles undated photos (e.g. WhatsApp copies), per-person editions ("make one where X and Y are in focus") and crop fixes. Use when the user asks to create, fill, edit, fix or re-focus a Mixbook photo book / album.
---

# Mixbook album builder

Scripts live in `${CLAUDE_SKILL_DIR}/scripts/`, multi-agent workflow templates in `${CLAUDE_SKILL_DIR}/references/workflows/`. Every book gets its own **book folder** `BOOK_DIR` (e.g. `~/Mixbooks/<book-name>`); all working files go there — never into the skill folder and never into the user's photo folders.

**Requirements**: macOS; Claude in Chrome connected (Chrome's claude.ai login = the account Claude Code uses) with Mixbook signed in; Python 3 with `pillow numpy opencv-python` (if `pip install --user` is refused, use a venv: `python3 -m venv ~/.venvs/mixbook && ~/.venvs/mixbook/bin/pip install pillow numpy opencv-python` and run the scripts with that python). Books are **English, left-to-right**. If the Workflow tool is unavailable, run each workflow's prompts as subagents one group at a time.

## Defaults (confirm with the user in the interview)
- Don't use all photos: curate; **never miss an occasion**; remove duplicates / near-duplicates; include some big images and panoramas.
- **Two-page panoramas must include the people**, and the centre fold must not cut a face. Pure landscapes never span two pages.
- **Every caption sits on the photo it describes**; modest size; correct place names only; no people's names unless the user says so.
- Remove off-story photos (screenshots, maps, receipts, blurry).
- Incidental objects/signs/food stay small and never out-size people photos on the same page.

## Safety rules (always)
- **Never** click Order/Checkout/Buy, enter or confirm payment, change shipping or account settings.
- **Never** delete or modify the user's photos (iCloud library, source folders, Mixbook photos). Clean-up deletes only the subfolders this skill created inside `BOOK_DIR`.
- Work in a **new, blank project** made for this book (Mixbook "Start from scratch"/blank design). If the user insists on an existing project, the first save REPLACES its pages — `make_profile.py` keeps a restore copy (`content.orig.*.json`); say so and get a yes.
- **Show the previews and get the user's go-ahead before the first save** to Mixbook.
- Never remove Mixbook's back-cover logo (the exporter keeps it).

## Step 0 — interview (short, before anything else)
Ask: (1) which photos — iCloud album name (My Album, not a Shared Album: for a shared album ask them to "Add to Library" first, or export to a folder), a folder, Google Photos, or already in Mixbook; (2) the occasion, places and dates (feeds place names and `legs_config.json`); (3) who is in the photos, how to recognise them, and whether names may be printed; (4) any focus people; (5) cover title/subtitle wishes; (6) book size/cover type (they choose it when creating the project) and a rough page budget (pages cost money; the product has a maximum).

## Step 1 — project and helpers
1. The user creates (or opens) the project in the Mixbook editor. The editor URL looks like `https://www.mixbook.com/editor?…pid=<PID>…` — `PID` is the number after `pid=`. Use a tab whose URL shows that pid.
2. Start the helper: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/helper_server.py <BOOK_DIR> 8765` (background). Same-origin JSON cannot be printed by the browser tool, so data moves through it.
3. Read the project and check it:
```js
const t=await fetch('/api/v2/my/projects/PID/content',{credentials:'include'}).then(r=>r.text());
await fetch('http://127.0.0.1:8765/content.json',{method:'POST',body:t});
```
   then `BOOK_DIR=<dir> python3 ${CLAUDE_SKILL_DIR}/scripts/make_profile.py` → prints name, product, size, page count, existing content; **confirm it is the right project**. It writes `profile.json` (page geometry from `intended_product`, max pages) and the restore copy.

## Step 2 — photos into the project
- **Already in Mixbook / Google Photos**: the user adds them in the editor (Photos → Google Photos). Go to step 3.
- **iCloud album**: `osascript ${CLAUDE_SKILL_DIR}/scripts/album_meta.applescript "<album>" > <BOOK_DIR>/meta.tsv` (columns: id, filename, date, lat, lon, w, h); stills only: `awk -F'\t' 'tolower($2) !~ /\.(mov|mp4|m4v)$/ {print $1}' <BOOK_DIR>/meta.tsv > <BOOK_DIR>/ids.txt`; export: `osascript ${CLAUDE_SKILL_DIR}/scripts/export_ids.applescript <BOOK_DIR>/ids.txt <BOOK_DIR>/export` (run in background; iCloud downloads are slow — wait until the file count in `export/` stops growing).
- **Folder**: use it as the source (read-only).
- Prepare: `python3 ${CLAUDE_SKILL_DIR}/scripts/prepare_upload.py <source_dir> <BOOK_DIR>` → resized copies in `<BOOK_DIR>/up/` with safe unique names + `up/list.json` + `upload_map.json`; videos skipped.
- Serve them: `python3 -I ${CLAUDE_SKILL_DIR}/scripts/helper_server.py <BOOK_DIR>/up 8766` (background).
- Upload in the editor: open **Photos → Add more photos** (the file input only exists there), then per batch of 50 (set `A`):
```js
const A=0, list=await fetch('http://127.0.0.1:8766/list.json').then(r=>r.json());
const have=new Set((await fetch('/api/v2/my/projects/PID/content',{credentials:'include'}).then(r=>r.json())).data.project.photos.map(p=>p.name));
const inp=[...document.querySelectorAll('input[type=file]')].find(i=>i.multiple&&!i.webkitdirectory);
const dt=new DataTransfer();
for(const n of list.slice(A,A+50)){if(have.has(n))continue;const b=await fetch('http://127.0.0.1:8766/'+encodeURIComponent(n)).then(r=>r.blob());dt.items.add(new File([b],n,{type:'image/jpeg'}))}
inp.files=dt.files;inp.dispatchEvent(new Event('change',{bubbles:true}));dt.files.length
```
  Before the next batch wait until the project's photo count (GET content) has grown by the batch size; reopen "Add more photos" if the input is gone. Mixbook keeps the file name, so photos map back by name.

## Step 3 — features and briefs
Re-read content (step 1 snippet), then:
`BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/mb_features.py` (≈700 px previews, capture times, GPS (from Mixbook or `meta.tsv`), faces, duplicate hashes) → `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/group.py` (bursts, moments, contact sheets) → write `<BOOK_DIR>/legs_config.json` (`[["A","title + place/GPS hints",["2027-05-01","2027-05-02"],[30,40]], …]`, one leg per 1–3 days, target photo ranges) → `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/legs.py`.

**Undated photos** (`mb_features.py` reports them): `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/undated_brief.py "<route hints>"` → run Workflow `${CLAUDE_SKILL_DIR}/references/workflows/place-undated-photos.js` with `args:{bookDir, count}` → save its result JSON → `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/apply_placement.py <result.json>` → re-run `mb_features.py`, `group.py`, `legs.py` (indices change — do this BEFORE curating).

## Step 4 — curate (multi-agent)
Workflow `${CLAUDE_SKILL_DIR}/references/workflows/curate-and-review.js`, `args: {bookDir, context: "<interview answers>", groups:[{key:"A",lo:30,hi:40}, …]}` (keys and ranges from `legs/legs.json`). Per-person edition instead: make `<BOOK_DIR>/people_reference.jpg` (a few labelled photos) and run `person-focus-edition.js` with `args:{bookDir, context, people:"NAME = how to recognise; …", names:[…], focus:[…], groups:[{key,first,last,lo,hi}], previous?}` (first/last from `legs/legs.json`).
Merge the group results into `<BOOK_DIR>/curation.json`; cap heroes (≈10–20 `page`, 2–6 `spread`); pick front cover, back cover, page 1 and last page photos (remove those from the sections):
```json
{"sections":[{"date":"…","title":"…","title_on":12,"caption":"…","caption_on":14,"photos":[{"i":12,"role":"large"}]}],
 "front":5,"back":40,"page1":0,"last":99,"page1_text":"","last_text":"",
 "cover_text":{"title":"…","subtitle":"…","back":"","title_size":200,"sub_size":120},"crops":{},"textpos":{}}
```

## Step 5 — layout, verify, fix
`BOOK_DIR=… TARGET=5 python3 ${CLAUDE_SKILL_DIR}/scripts/layout.py <BOOK_DIR>/curation.json` → `book.json`, `book_extra.json`, `crops.json`, `preview/*.jpg`. Inside pages = 2 + 2 × spreads: tune `TARGET` (photo units per page) to the budget and the product maximum. `python3 ${CLAUDE_SKILL_DIR}/scripts/hier_check.py <BOOK_DIR> <BOOK_DIR>/curation.json` must be (nearly) clean.
Verify: `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/manifests.py <BOOK_DIR>/curation.json`, Workflow `verify-spreads.js` with `args:{bookDir, context, spreads:<n>, focus?}`, save the result, `python3 ${CLAUDE_SKILL_DIR}/scripts/apply_fixes.py <cur.json> <verify.json> <cur_v2.json>`, re-run layout; repeat until clean. **Show the user the cover and several spreads (preview/*.jpg) and get a go-ahead.**

## Step 6 — save to Mixbook
1. Re-read content (step 1 snippet; fresh `modified_at`), then `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/mb_export.py <BOOK_DIR>/put.json` (fails clearly if the book exceeds the product's page maximum).
2. Close other editor tabs of this project (a stale editor could save over the new content), then from a mixbook.com tab:
```js
const body=await fetch('http://127.0.0.1:8765/put.json').then(r=>r.text());
await new Promise(ok=>{const x=new XMLHttpRequest();x.open('PUT','/api/projects/PID');x.setRequestHeader('Content-Type','application/json');x.onload=()=>ok(x.status+' '+x.responseText.slice(0,80));x.send(body)});
```
3. **Finalize**: open the editor for this project fresh (navigate, discard any "leave site" prompt), wait ~10 s, click **Save** — the editor computes every text box's line layout. A Save clicked before the editor has finished loading may not stick, so check and repeat (wait a few seconds, Save again) until this prints `without layout 0` and the header shows **Saved**:
```js
const C=(await fetch('/api/v2/my/projects/PID/content',{credentials:'include'}).then(r=>r.json())).data.project;
const tx=C.pages.flatMap(p=>p.content_items.filter(i=>i.type==='page_text_item'));
'text items '+tx.length+' | without layout '+tx.filter(i=>!(i.text_document&&i.text_document.flow&&i.text_document.flow.length)).length+' | inside pages '+C.pages.filter(p=>p.position>0).length
```
   Then look at the cover and a few spreads in **Preview**.

## Step 7 — clean up
Delete only `<BOOK_DIR>/{export,up,thumbs,preview,sheets,review}` (keep the JSON files and the `content.orig.*.json` restore copy). Stop the helper servers.

## Mixbook API notes (for maintenance)
- **Read** `GET /api/v2/my/projects/{pid}/content` → `data.project`: `pages[]` (`position` -3 spine, -2 back cover, -1 front cover, 1..N inside; 1 = first right-hand page), `photos[]` (id, name = file name, width/height, `taken_at` = camera wall-clock, faces, focus_point, public preview `urls` 50–1400 px), `intended_product` (width/height inches, `max_page_count`), `modified_at`.
- **Write** `PUT /api/projects/{pid}` `{project:{creator, id, name, pages, photos:[{id}], deleted_photo_ids, hidden_background_ids, backgrounds, hidden_sticker_ids, stickers, variables, intended_product:{id}, template:{id}, modified_at}}`. Unchanged page = `{id, client_id}`; changed page = `{id?, client_id, creator, position, background, content_items}` (replaces content); page without `id` = new page; page left out = deleted.
- **Geometry**: per page, units = page height, origin = page centre; items `rel_x/rel_y` (centre), `rel_width/rel_height`; photo crop `image_offset_x/y`, `image_width/height` relative to the frame. Full bleed ≈ frame 1.035 × page.
- **Text**: `page_text_item`, `text_document.doc` = `<p text-align="…"><s font-family="Lobster" font-weight="400" font-style="normal" font-size="18" color="#ffffff" line-height="1.14">…</s></p>`, `flow: []` (the editor fills it on open+save). Mixbook fonts are Latin-only (Hebrew/Arabic are not printable as text).
- **Gotchas**: text items with any drop shadow are not rendered (use dark text on bright areas or a soft dark fill box, `style.fill_alpha`); Mixbook's own items (logo, spine text) must be re-sent as fresh items in this write format — echoing the GET format back returns HTTP 500.
