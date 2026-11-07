# photobook-albums

A [Claude Code](https://claude.com/claude-code) plugin that turns a pile of trip photos into a finished photo book. It has two skills:

| Skill | Service | Book |
|---|---|---|
| **mixbook-album** | [Mixbook](https://www.mixbook.com) | English, left-to-right |
| **picabook-album** | [Picabook](https://www.picabook.co.il) | Hebrew, right-to-left (English place names, Hebrew lines) |

You tell Claude which photos to use: a Google Photos album, a folder on your computer or drive, an iCloud Photos album, or photos already in the project. Claude then:

- **curates** them: removes duplicates and blurry shots, keeps at least one photo of every place and moment, and picks the strongest images for full pages and two-page panoramas;
- **places undated photos** (WhatsApp copies, scans) at the right moment by looking at what's in them;
- **lays out** the book: mosaics that respect each photo's shape, full-bleed pages, panoramas across both pages, face-aware crops;
- **writes captions**: short place names and the occasional warm one-liner, each on the photo it describes;
- **has independent reviewers check every spread** (crops, captions, duplicates) and fixes what they find;
- **shows you the result for approval**, then saves the whole book into your project in one go.

You review it in the editor, change anything you like, and order it there yourself. The plugin never orders or pays for anything.

## What you need

- A **Mac** is recommended (iCloud Photos albums need one). Google Photos and folders also work on Windows, but that hasn't been tested yet.
- **Claude Code** (CLI or desktop app) and the **Claude in Chrome** extension, signed in to claude.ai with the **same account** as Claude Code.
- A **Mixbook** or **Picabook** account, signed in in that Chrome.
- **Python 3** with a few image libraries:
  ```bash
  python3 -m pip install --user pillow numpy opencv-python
  ```
  (On Windows also `pillow-heif`, for iPhone HEIC photos.) If that is refused ("externally managed environment"), use a virtual environment:
  ```bash
  python3 -m venv ~/.venvs/photobook && ~/.venvs/photobook/bin/pip install pillow numpy opencv-python
  ```
  and tell Claude to use `~/.venvs/photobook/bin/python3`.

## Install

In Claude Code:

```
/plugin marketplace add ydaromai/photobook-albums
/plugin install photobook-albums@photobook-albums
```

(Or from a terminal: `claude plugin marketplace add ydaromai/photobook-albums` then `claude plugin install photobook-albums@photobook-albums`.)

## Use it

1. Start a **new, blank** photo book in the size and cover you want, and leave the editor open in Chrome.
   - Mixbook: "Start from scratch".
   - Picabook: choose the album and cover, **פתיחה עברית** (Hebrew opening) and the design **עיצוב עצמי → קלאסי**.
2. In Claude Code, ask for example:
   > Make a Mixbook album from my iCloud album "Japan 2027".

   > Fill my open Picabook project with the photos in ~/Pictures/Galil — Hebrew captions.

   > Make a Mixbook album from the Google Photos album "Tasmania 2027" — I downloaded it to ~/Downloads/Tasmania.

   **Google Photos:** open the album on photos.google.com, click ⋮ → **Download all**, unzip it, and tell Claude the folder. Dates and places come with the photos. You never sign in to Google through Claude.
3. Claude asks a few short questions (who is in the photos, places and dates, names on captions or not, cover title, page budget), then does the work. Uploading and curating a few hundred photos takes a while.
4. Claude shows you the cover and some spreads. Say **go** and it saves the book to your project.
5. Review it in the editor, tweak anything, and order when you're happy.

Other things you can ask:
- "Make a second edition of this book where **Dana and Tom** are in focus."
- "The caption on page 12 is on the wrong photo, fix it."
- "Use fewer pages — aim for 40."

## Good to know

- **Your photos stay yours.** The plugin reads your album or folder but never changes or deletes it. It works in a separate book folder, and at the end it deletes only the temporary copies it made there.
- **Use a fresh project.** Saving **replaces** the project's pages. A restore copy of the original is kept in the book folder, but a fresh project is simpler.
- **Mixbook books are English, left-to-right.** Mixbook's fonts don't include Hebrew or Arabic letters. Mixbook's small logo on the back cover stays as Mixbook places it.
- **Picabook books are right-to-left.** The front cover is on the left, and every spread starts on the right page. Picabook page counts come in steps set by the product; Claude matches the book to the project's page count.
- **Panoramas** always include the people, never just scenery, and the fold never cuts through a face.
- **Unofficial**: the skills talk to the same web APIs the Mixbook and Picabook editors use. They aren't affiliated with or supported by either company, and may need an update if an editor changes. Always check the book in the editor before ordering.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Browser extension is not connected" | Sign in to claude.ai in Chrome with the same account as Claude Code, click the Claude extension icon, or restart Chrome. |
| Photos don't upload | Keep the editor tab open on the add-photos panel (Mixbook: **Photos → Add more photos**; Picabook: **הוספת תמונות**) while Claude uploads. |
| Mixbook text boxes look empty | Reload the editor and click **Save** once. Mixbook lays out text when it opens the project. |
| Picabook shows an old version | Reload the editor tab. Never keep the same project open in two tabs. |
| Book has too many pages | Ask Claude for a page target ("aim for 40 pages"). Each product also has a maximum. |

## How it works (for the curious)

Each skill's `SKILL.md` (in `skills/mixbook-album/` and `skills/picabook-album/`) is the full playbook Claude follows. `scripts/` holds the layout engine and the service's reader/writer; `references/workflows/` holds the multi-agent curation and review steps. Both skills share the same layout engine: Picabook books run it right-to-left, Mixbook books left-to-right. No photos, accounts or personal data are stored in this repository.

## License

MIT
