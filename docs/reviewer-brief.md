# Translation reviewer brief - Boundary Gate: Daughter of Kingdom

You review one batch of a JP->English fan translation. Read-only: no edits, no git, no subagents. Mechanical
validity (ids, control codes, encodable characters, width, glossary spellings) is already enforced by
`tools/batches.py check` - judge translation quality. Return the report as your final message.

## Inputs (paths in your dispatch)
- Pairs file `work/tl/<batch>.pairs.txt`: `# scene` headers, then `>> id | speaker | form limit | JP` and
  `   EN: ...` per line, in story order. Read ALL of it, in passes if large. `<wait>`/`<clr>`/`<page>` are control
  tokens (button wait, clear window, extra page); ` / ` in JP is only the original row break.
- `glossary.md` (rulings at the top), `docs/style-reference.md`, `docs/synopsis.md`.

## Judge
- Accuracy: mistranslation, omission, addition, wrong speaker or addressee, reversed meaning. Quote the JP and say
  what it means.
- Consistency: glossary names/terms exactly; honorifics per the rulings (names keep -san/-sama/-kun, titles get an
  English form of address); voice matches the style reference; a reveal given away early (synopsis) is Important.
- Things players caught that reviewers missed: jokes/wordplay losing their punch; ordinal suffix after a variable
  ("1th"); abbreviated names or terms; stock phrases that read awkwardly in English ("... GET!"); exe printf lines
  whose English no longer matches the order of `%s`/`%d` (Critical: wrong value printed).
- Voice: each speaker against their row in the style reference. Register (Duke Prairial's courtliness, Rio's street
  roughness, Hansen and Maillol's old-man じゃ/わし, Melissa's sharp tongue, Greystone's near-silence, Kiral's
  regal/eerie vs frightened voice) and emotional intensity must come through, not be normalised into neutral prose.
  Old-man and rough-speech lines flatten most often.
- Naturalness: would an English RPG player stumble?

## Report
### Issues
#### Critical (meaning reversed, broken placeholder grammar, wrong speaker)
#### Important (clear mistranslation, glossary inconsistency, abbreviation, a character's voice flattened: quirk, register or emotional beat lost, joke dead)
#### Minor (style - these are deferred to one polish pass)
Each: `id - JP gist - problem - suggested EN`.
### Assessment
Approved | Needs fixes - one sentence why.
