# Polish-pass brief (phase 9)

You apply the deferred Minor findings in `docs/polish.md` to the English script. Read `AGENTS.md`, `glossary.md`,
`docs/style-reference.md`, `docs/synopsis.md` and `docs/translator-brief.md` first.

For every unticked line `- [ ] <id(s)> - <note>`:
1. Find the entry: ids are `<FILE>:<hex>` (search `"id": "<id>"` under `script/`, e.g. `EVENT06:21b5f` is in
   `script/EVMES0/EVENT06.json` or another EVMES dir; `exe:0xxxx` is `script/exe.json`). Read its `jp`, its `en`
   and the entries around it.
2. Decide: apply the suggested English (adjust it if it breaks voice, glossary or the surrounding lines), or waive
   it when the current English is already right or the note is optional and not an improvement.
3. Edit only the `en` value with your file-edit tool (apply_patch). Keep every control character exactly
   (`\r` row breaks on name/speaker rows, `\b` clears, `\u0010` waits...): the lint compares them with the JP.
   `en` is paragraph form: never add `\r` to dialogue to wrap it, the build wraps. Exe strings keep their
   `\n` rows and printf specifiers in order.
4. Tick the line: `- [x] <id(s)> - <note> -- fixed` or `-- waived: <reason>`.

Rules: edit only `script/**/*.json` `en` values and `docs/polish.md`. No other files, no git, no scripts that rewrite
files. After every ~20 lines and at the end run `python -X utf8 tools/lint.py` (it must report 0 errors; fix what it
reports). British spelling, glossary names exactly. Your final message: counts fixed / waived and any line you could
not resolve.
