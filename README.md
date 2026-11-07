# mixbook-album

A [Claude Code](https://claude.com/claude-code) plugin that turns a pile of trip photos into a finished **Mixbook** photo book.

You tell Claude which photos to use (an iCloud Photos album, a folder, Google Photos, or photos already in a Mixbook project). Claude then:

- **curates** them: removes duplicates and blurry shots, keeps at least one photo of every place and moment, and picks the strongest images for full pages and two-page panoramas;
- **places undated photos** (WhatsApp copies, scans) at the right moment by looking at what's in them;
- **lays out** the book: mosaics that respect each photo's shape, full-bleed pages, panoramas across both pages, face-aware crops;
- **writes captions**: short English place names and the occasional warm one-liner, each on the photo it describes;
- **has independent reviewers check every spread** (crops, captions, duplicates) and fixes what they find;
- **shows you the result for approval**, then saves the whole book into your Mixbook project in one go.

You review it in the Mixbook editor, change anything you like, and order it there yourself. The plugin never orders or pays for anything.

## What you need

- A **Mac** (for iCloud Photos albums; folders work too).
- **Claude Code** (CLI or desktop app) and the **Claude in Chrome** extension, signed in to claude.ai with the **same account** as Claude Code.
- A **Mixbook** account, signed in in that Chrome.
- **Python 3** with a few image libraries:
  ```bash
  python3 -m pip install --user pillow numpy opencv-python
  ```
  If that is refused ("externally managed environment"), use a virtual environment:
  ```bash
  python3 -m venv ~/.venvs/mixbook && ~/.venvs/mixbook/bin/pip install pillow numpy opencv-python
  ```
  and tell Claude to use `~/.venvs/mixbook/bin/python3`.

## Install

In Claude Code:

```
/plugin marketplace add ydaromai/mixbook-album
/plugin install mixbook-album@mixbook-album
```

(Or from a terminal: `claude plugin marketplace add ydaromai/mixbook-album` then `claude plugin install mixbook-album@mixbook-album`.)

## Use it

1. In Mixbook, start a **new, blank** photo book in the size and cover you want ("Start from scratch"), and leave the editor open in Chrome.
2. In Claude Code, ask for example:
   > Make a Mixbook album from my iCloud album "Japan 2027".

   or
   > Fill my open Mixbook project with the photos in ~/Pictures/Wedding — make the couple the focus.
3. Claude asks a few short questions (who is in the photos, places and dates, names on captions or not, cover title, page budget), then does the work. Photo uploads and curation of a few hundred photos take a while.
4. Claude shows you the cover and some spreads. Say **go** and it saves the book to your project, then opens it in the Mixbook editor.
5. Review it in Mixbook (Preview is the best way to look through it), tweak anything, and order when you're happy.

Other things you can ask:
- "Make a second edition of this book where **Dana and Tom** are in focus."
- "The caption on page 12 is on the wrong photo, fix it."
- "Use fewer pages — aim for 40."

## Good to know

- **Your photos stay yours.** The plugin reads your album or folder but never changes or deletes it. It works in a separate folder (default `~/Mixbooks/<book>`), and at the end it deletes only the temporary copies it made there.
- **Existing projects**: use a fresh project. If you point it at a project that already has pages, saving **replaces** them. A restore copy of the original is kept in the book folder, but a fresh project is simpler.
- **English, left-to-right books.** Mixbook's fonts don't include Hebrew or Arabic letters, so text in those languages won't print.
- **Mixbook's small logo** on the back cover stays as Mixbook places it.
- **Panoramas** always include the people, never just scenery, and the fold never cuts through a face.
- **Unofficial**: this talks to the same web API the Mixbook editor uses. It isn't affiliated with or supported by Mixbook, and it may need an update if Mixbook changes its editor. Always check the book in Mixbook before ordering.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Browser extension is not connected" | Sign in to claude.ai in Chrome with the same account as Claude Code, click the Claude extension icon, or restart Chrome. |
| Photos don't upload | Keep the Mixbook editor tab open on **Photos → Add more photos** while Claude uploads. |
| Text boxes look empty in the editor | Reload the editor and click **Save** once. Mixbook lays out text when it opens the project. |
| Book has too many pages | Ask Claude for a page target ("aim for 40 pages"). Each Mixbook product also has a maximum. |

## How it works (for the curious)

`skills/mixbook-album/SKILL.md` is the full playbook Claude follows. `skills/mixbook-album/scripts/` holds the layout engine and the Mixbook reader/writer. `skills/mixbook-album/references/workflows/` holds the multi-agent curation and review steps. No photos, accounts or personal data are stored in this repository.

## Credits

The layout engine is ported from the companion **picabook-album** skill, which builds Picabook photo books (including right-to-left Hebrew books).

## License

MIT
