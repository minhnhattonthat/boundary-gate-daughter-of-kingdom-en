# Translator brief - Boundary Gate: Daughter of Kingdom (PS1, 1997)

You translate part of the Japanese script of Boundary Gate: Daughter of Kingdom into English for a fan patch. It is a
fantasy RPG with a late sci-fi twist: Finn, a wry young mercenary, escorts Risp, a sheltered girl from the Temple of
Knowledge, who is searching for her sister. Work only on the batches named in your dispatch, one at a time in the
order given, each to a passing check before the next. Do all translation yourself; do not dispatch subagents. Never
edit anything but your own `work/tl/<batch>.out.tsv` files.

## Read first
1. `docs/style-reference.md` - character voices, approved example pairs, conventions. Match this voice.
2. `work/tl/terms_<batch>.txt` - binding glossary rows for this batch (`JP<TAB>EN`); the full table and the
   rulings are in `glossary.md` (read its Rulings and Style rules sections once).
3. `docs/synopsis.md` - plot, who is who, the late reveals. Don't give a reveal away early.

## Input: `work/tl/<batch>.tsv`
`id<TAB>speaker<TAB>form<TAB>limit<TAB>Japanese`; `#` lines name the scene file (context only, no output).
- `form` = the op group: `dialogue` (message window), `speaker` (name line above dialogue), `location` (place
  banner), `npc` (name in the talk list), `building` (map destination), `menu` (room menu item), `choice` (yes/no
  option), or an exe group (`items`, `spells`, `battle`, `monsters`, `save`, `shop`, `ending`, `credits`...).
- `speaker` = the name shown above a dialogue line, when there is one.
- `limit`: `26x3` = dialogue, 26 cells per row and 3 rows per page; `26x2` = same under a speaker line. A plain
  number = cells per row for a one-row field; `~` = soft (a guess still to be measured; stay under it if you can).
- Japanese ` / ` is the original's row break. Rows are re-wrapped automatically for English: translate the page as
  one utterance and do not reproduce the Japanese line breaks.
- Tokens: `<wait>` = waits for a button, `<clr>` = clears the window (new page), `<17>`/`<19>` etc. = other control
  bytes, `<icon>` = an item icon, `<0c>` = colour switch (followed by its digit). **Copy every token**, in the same
  place in the flow of the text (a `<wait><clr>` between two sentences stays between the matching English sentences).
- **Speaker-name rows:** most spoken lines carry the speaker's name as their own first row: `リスプ / 「どうしても…`.
  Keep that shape: `Risp / "I simply must see my sister...` (name, ` / `, then the quote). The check enforces it.
- **Continuations:** a long speech is split over several ids; the later ones start indented (`  お願いします…`) and
  the last one ends with 」. Translate them as one flowing speech: only the first opens `"`, only the last closes `"`,
  and never start the English with spaces (the build indents quote rows itself).
- Each line is one unique Japanese string; identical copies elsewhere in the game get the same English.

## Output: `work/tl/<batch>.out.tsv`, written with your file-write tool (never a shell heredoc)
`id<TAB>English`, every input id exactly once, in input order, no `#` lines needed. Plain ASCII only: straight quotes
`"` and `'`, `...` for ellipses, `--` for a dash; no tabs inside the English, no Japanese or full-width characters,
no `@` or `\`. Colons are fine.
- **Dialogue pages:** the window is 26 cells x 3 rows (2 under a speaker). English is longer than Japanese; if a page
  does not fit, the build adds a page by itself at a row boundary. You may place an extra page break yourself with
  `<page>` where a sentence ends (better pacing than an automatic break mid-sentence). Aim for no more than about
  one extra page per original page. Preview any line: `python -X utf8 tools/batches.py fit "<English>" --rows 2`.
- `/` with spaces (` / `) forces a row break; use it only in `location` banners (place / floor) and exe strings
  whose Japanese has one.
- **Exe strings** (`exe:` ids) are not re-wrapped: keep the Japanese row breaks (` / `), a trailing ` / ` and any
  leading spaces that centre or indent a line. printf specifiers (`%s`, `%d`, `%-20s`, `%6ld`...) stay **in the same
  order** as in the Japanese. For a fixed field (item, spell, map name) the limit is the cells you may use.

## Validate
Run `python -X utf8 tools/batches.py check <batch>` from the repo root and fix every ERROR until it prints OK.
Warnings are information (soft limits, exe strings that will need relocation); reduce them where it costs no meaning.

## Style
- Faithful: keep the information and order of ideas; adapt idiom, not meaning. Don't add details the Japanese
  doesn't state; don't summarise or skip. Adapt wordplay so the joke still lands (no translator notes).
- Keep the speaker audible (style reference voice table). JP register markers must become English devices, not
  vanish: old men's じゃ/のう/わし ("eh?", "my girl", "heh"), rough men's ぜ/ねえ/だあ？ ("ain't", "ya", clipped
  grammar), Melissa's わよ/でしょ/insults (snappy, bossy), Duke Prairial's 申す (courtly). A line any speaker could
  have said is a mistake.
- Use names and terms exactly as in the glossary. Full names and terms, never abbreviate to fit; if a field can't
  hold the meaning, keep the meaning and report it as `LONG: id`.
- Honorifics on names are kept and hyphenated (キラル様 -> Kiral-sama, メリッサ君 -> Melissa-kun); titles become English
  forms of address (司祭長さま -> "High Priest", お嬢さん -> "young lady"/"miss"). Western name order.
- Punctuation: 「」 -> "...", 『』 -> '...' inside a quote, … -> `...`, ！？ -> `?!`, ～ -> stretch the word or drop it.
  A spoken line that opens with 「 opens with `"`; its last page closes with `"`. Never add leading spaces in dialogue.
- Speaker names are bare (`Finn`, not `Finn:`). Generic speakers: 娘 Girl, 男 Man, 女 Woman, 町人Ａ Townsman A.
- No suffix glued to a number variable (write "Level %d" not "%dth"); no a/an right before `%s`.
- Narration (lines without quotes) is mostly Finn's first-person past tense in events, neutral description in rooms
  ("The inn is cosy. The hall is bustling.") - present tense for room descriptions, as the JP does.
- Notes from earlier batches: (none yet)

## Consistency
Never edit `glossary.md`. For a recurring name or term not in it, pick a form, use it consistently, and report it.

## Report (reply with only this)
Files written and entry count; then any lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - note`.
