---
name: picabook-album
description: Build or rebuild a Picabook (picabook.co.il) photo book end to end — curate hundreds of trip/event photos (dedupe, keep every occasion, heroes and panoramas with the people in them), lay them out right-to-left for a Hebrew book (mosaics, full bleeds, two-page panoramas, face-aware crops), add English place labels and short Hebrew (or English) lines on the photo they describe, and save the whole book in one call through the Picabook editor's own save API instead of clicking. Photos come from an iCloud Photos album (Mac), a folder, or photos already in the Picabook project. Also handles undated photos (WhatsApp copies), per-person editions and crop fixes. Use when the user asks to create, fill, edit, fix or re-focus a Picabook album / photo book.
---

# Picabook album builder

Scripts: `${CLAUDE_SKILL_DIR}/scripts/`; multi-agent workflow templates: `${CLAUDE_SKILL_DIR}/references/workflows/`. Each book gets its own **book folder** `BOOK_DIR` (e.g. `~/Picabooks/<book-name>`); all working files go there — never into the skill folder or the user's photo folders.

**Requirements**: macOS; Claude in Chrome connected (Chrome's claude.ai login = Claude Code's account) and signed in to Picabook (`editor.picabook.co.il` and `www.picabook.co.il` allowed); Python 3 with `pillow numpy opencv-python` (venv if `pip --user` is refused). If the Workflow tool is unavailable, run each workflow's prompts as subagents one group at a time.

**Direction**: Picabook books default to **right-to-left (Hebrew binding)**: the front cover is the LEFT half of the cover spread and on every spread the RIGHT page comes first. Keep `DIRECTION=RTL` (the exporter refuses anything else unless `ALLOW_LTR=1` is set for a deliberate English left-to-right book).

## Defaults (confirm with the user in the interview)
- Curate, don't dump: **never miss an occasion**, remove duplicates / near-duplicates, include some big images and panoramas.
- **Two-page panoramas must include the people**, and the centre fold must not cut a face.
- **Every caption sits on the photo it describes**; English place labels in a script font (LobsterCFF, ~75), short warm lines in Hebrew (AlefCFF, ~80) or English; each line unique; no people's names unless the user says so.
- Remove off-story photos; incidental objects/signs/food stay small.

## Safety rules (always)
- **Never** order, check out or pay; never change account settings.
- **Never** delete or modify the user's photos; clean-up deletes only this skill's subfolders in `BOOK_DIR`.
- Prefer a **new project** for the book. Saving REPLACES the project's pages — `pb_profile.py` keeps a restore copy (`save.orig.*.json`; POST it back to undo).
- **Show the previews and get a go-ahead before the first save.**
- After saving, **reload the editor tab with force** — a stale tab that saves later would overwrite the book.

## Step 0 — interview
Which photos (iCloud album — My Album, not a Shared Album —, folder, or already in the project); occasion, places and dates; who is in the photos, how to recognise them, names allowed?; focus people; caption language (Hebrew lines by default); cover title/subtitle; page budget (Picabook page counts come in steps of 4, with a product minimum/maximum).

## Step 1 — project
- New project: `https://www.picabook.co.il/HE-IL/Albums.asp?type=0` → album type (e.g. Picabook | פנורמי 29x22), cover (כריכה קשה), **פתיחה עברית** (Hebrew opening), design **עיצוב עצמי → קלאסי**, project name (letters/digits/spaces only — `&` is rejected). The wizard summary may say «פנורמי יהלום» even for regular print — trust the hidden `print` select (`הדפסה רגילה`).
- Start the helper: `ORIGIN=https://editor.picabook.co.il python3 -I ${CLAUDE_SKILL_DIR}/scripts/helper_server.py <BOOK_DIR> 8765` (background).

## Step 2 — photos into the project
- iCloud: `osascript ${CLAUDE_SKILL_DIR}/scripts/album_meta.applescript "<album>" > <BOOK_DIR>/meta.tsv`; stills only `awk -F'\t' 'tolower($2) !~ /\.(mov|mp4|m4v)$/ {print $1}' <BOOK_DIR>/meta.tsv > <BOOK_DIR>/ids.txt`; `osascript ${CLAUDE_SKILL_DIR}/scripts/export_ids.applescript <BOOK_DIR>/ids.txt <BOOK_DIR>/export` (background; wait until the file count stops growing).
- `python3 ${CLAUDE_SKILL_DIR}/scripts/prepare_upload.py <source_dir> <BOOK_DIR>` → `<BOOK_DIR>/up/` (resized, EXIF kept, safe names) and serve it: `ORIGIN=https://editor.picabook.co.il python3 -I ${CLAUDE_SKILL_DIR}/scripts/helper_server.py <BOOK_DIR>/up 8766`.
- In the editor click **הוספת תמונות** (add photos — the file input only exists on that screen), then per batch of 50 (set `A`):
```js
const A=0, list=await fetch('http://127.0.0.1:8766/list.json').then(r=>r.json());
const inp=[...document.querySelectorAll('input[type=file]')].find(i=>i.multiple);
const dt=new DataTransfer();
for(const n of list.slice(A,A+50)){const b=await fetch('http://127.0.0.1:8766/'+encodeURIComponent(n)).then(r=>r.blob());dt.items.add(new File([b],n,{type:'image/jpeg'}))}
inp.files=dt.files;inp.dispatchEvent(new Event('change',{bubbles:true}));dt.files.length
```
  Wait between batches until the upload bars finish, then click **סיום**. Keep the tab open until the panel count (תמונות N) matches.

## Step 3 — page count, save template, project data
1. Set the page count in the editor first: bottom-left **הוסף עמודים** → choose the extra pages (steps of 4) → הוסף. (The book's inside pages must equal 2 + 2 × spreads.)
2. Install the hook, click **שמירה**, and keep the save body:
```js
window.__cap=[];const O=XMLHttpRequest.prototype.open,S=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return O.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(b){const x=this;x.addEventListener('load',()=>window.__cap.push({u:String(x.__u),req:typeof b==='string'?b:''}));return S.apply(this,arguments)};
```
   after the save finishes:
```js
const s=window.__cap.filter(c=>c.u.includes('SaveProjectComplete')).pop();
await fetch('http://127.0.0.1:8765/save_template.json',{method:'POST',body:s.req});
const t=JSON.parse(s.req), b='undefined'+t.shareCustomerID+'/albuns/'+t.albumName+'/';
const body={codProduct:t.albumName,albumXML:b+'album.xml',pagesXML:b+'pages.xml',clientCode:t.clientCode,sessionID:t.customer_id_session,
  typeUser:0,isoLanguage:t.project.choosedData.language||'iw_IL',idPrinter:t.id_printer,customerId:t.customer_id,currency:t.project.choosedData.currency||'ILS',idPartner:1,ipCountry:'IL'};
const g=await fetch('https://editor-api-picabook-v1.sunpics.online/api/v1/Project/GetProject',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.text());
await fetch('http://127.0.0.1:8765/getproject.json',{method:'POST',body:g});
```
3. `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/pb_profile.py <BOOK_DIR>/save_template.json RTL` → prints the project summary (**confirm it is the right project**), writes `profile.json` and the restore copy.
4. `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/pb_features.py` → images, previews, faces, duplicate hashes, dates and places. Photos uploaded in Step 2 are matched back to their files by pixels (Picabook renames uploads) and take their **true** date/place from `meta.tsv` or the file's EXIF; WhatsApp-style copies come out **undated** (place them in Step 4). Photos that were already in the project only have Picabook's stored date, shifted by the uploading computer's timezone: the script prints an estimated `TZ_OFFSET_H` — **confirm it with the user** (it can be an hour off) and re-run with `TZ_OFFSET_H=<h>` if needed.

## Step 4 — briefs, undated photos, curation
`BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/group.py` → write `<BOOK_DIR>/legs_config.json` (`[["A","title + place/GPS hints",["2027-05-01"],[30,40]],…]`) → `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/legs.py`.
Undated photos: `undated_brief.py "<route hints>"` → Workflow `place-undated-photos.js` `args:{bookDir,count}` → `apply_placement.py <result.json>` → re-run `pb_features.py`, `group.py`, `legs.py` (before curating).
Curate: Workflow `${CLAUDE_SKILL_DIR}/references/workflows/curate-and-review.js` with `args:{bookDir, context, groups:[{key,lo,hi}], direction:'RTL', captionLanguage:'Hebrew'}` (per-person edition: `person-focus-edition.js`, see its header). Merge into `<BOOK_DIR>/curation.json`; cap heroes; choose front/back cover, page 1, last page (remove them from the sections):
```json
{"sections":[{"date":"…","title":"…","title_on":12,"caption":"…","caption_on":14,"photos":[{"i":12,"role":"large"}]}],
 "front":5,"back":40,"page1":0,"last":99,"page1_text":"","last_text":"",
 "cover_text":{"title":"…","subtitle":"…","back":"","title_size":230,"sub_size":130},"crops":{},"textpos":{}}
```

## Step 5 — layout, verify, approve
`BOOK_DIR=… TARGET=5.6 python3 ${CLAUDE_SKILL_DIR}/scripts/layout.py <BOOK_DIR>/curation.json` (tune `TARGET` — photos per spread — until the book's pages = the project's pages; `export.py` says if they differ and refuses a count outside the product's range) → `hier_check.py`, `manifests.py`, Workflow `verify-spreads.js` → `apply_fixes.py` → re-layout until clean. **Show the user the cover and several spreads and get a go-ahead.**

## Step 6 — save and check
1. Measure caption widths in the editor tab (Lobster/Alef as the editor uses them) and save `widths.json`:
```js
const T=await fetch('http://127.0.0.1:8765/book.json').then(r=>r.json()), E=await fetch('http://127.0.0.1:8765/book_extra.json').then(r=>r.json());
const all=[...T.flatMap(s=>s.texts),...['cover','page1','last'].flatMap(k=>E[k].texts)];
const fam={LobsterCFF:'"Lobster Unicode"',AlefCFF:'"Alef Unicode"'};await document.fonts.load('75px "Lobster Unicode"');await document.fonts.load('80px "Alef Unicode"','שלום');
const c=document.createElement('canvas').getContext('2d'),out={};for(const t of all){c.font=t.size+'px '+(fam[t.font]||t.font);out[t.font+'|'+t.size+'|'+t.text]=c.measureText(t.text).width}
await fetch('http://127.0.0.1:8765/widths.json',{method:'POST',body:JSON.stringify(out)});
```
2. `BOOK_DIR=… python3 ${CLAUDE_SKILL_DIR}/scripts/export.py <BOOK_DIR>/save_template.json <BOOK_DIR>/jpages.json <BOOK_DIR>/widths.json` → `python3 ${CLAUDE_SKILL_DIR}/scripts/payload.py <BOOK_DIR>/save_template.json <BOOK_DIR>/jpages.json <BOOK_DIR>/upload.json`.
3. POST it from the editor tab, then **reload the tab with force**:
```js
const body=await fetch('http://127.0.0.1:8765/upload.json').then(r=>r.text());
await new Promise(ok=>{const x=new XMLHttpRequest();x.open('POST','https://editor-api-picabook-v1.sunpics.online/api/v1/Project/SaveProjectComplete');x.setRequestHeader('Content-Type','application/json');x.onload=()=>ok(x.status+' '+x.responseText.slice(0,80));x.send(body)});
```
4. Check the cover and a few spreads in the editor (right page first; captions on the right photos). Crop fix later without re-layout: `patch_crops.py`.

## Step 7 — clean up
Delete only `<BOOK_DIR>/{export,up,thumbs,preview,sheets,review}`; keep the JSON and the restore copy. Stop the helpers.

## Picabook editor notes (for maintenance)
- Whole book = one `Project/SaveProjectComplete` POST: the editor's save body with `jPages` (cover, page 1, spreads, last page), `project.pagesListOrder` (page `fixedUID`s) and `project.choosedData.numberOfPages`.
- Image object: preview size `imgWidth = width·M`; crop `imgX/imgY/imgW/imgH` in those units. Text = a `texto` object + an entry in the page's `texts` (font, size, colour, `paragraphs` with measured `linesWidth`).
- New uploads are renamed to UUIDs and stored on the editor's storage server (`idUrl` 3) — always use each image's own `url`.
- Opening the same project in a second window reloads the other one.
