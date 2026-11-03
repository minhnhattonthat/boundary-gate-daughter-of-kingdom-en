# Style reference

Pilot lines translated by the controller (2026-11-04, owner pre-approved the run, D6). Every translator matches this
voice; reviewers judge against it. Each row names the JP markers and the English devices that carry them.

## Voices
| Character | JP markers | English devices |
|---|---|---|
| Finn (narration) | 俺, plain past tense, だ/た | first person, past tense, short dry sentences, a wry last beat ("Fine by me.") |
| Finn (speech) | 俺, ぜ, よ, な, だろ, ～ぁ? (迷ったぁ？) | contractions, "pal", "huh?", teasing; mock-formal when sarcastic (でございましたか -> "Well, pardon me, milady") |
| Risp | 私/あたし, です/ます, …, ごめんなさい | polite, earnest, hesitant ellipses, no contractions when formal ("I do not..." only when solemn), apologises |
| Kiral (as herself) | お姉さん, …助けて | small, frightened, "Sister..." |
| Kiral (possessed / public) | なさい, 告げます, われは | regal, cold, archaic in the chant ("I am the Daughter of the Kingdom! ... Come forth, children of chaos!") |
| Melissa | あたし, わよ, でしょ, なによ, insults (ボケ！オタンコナス！) | bossy, quick, exclamatory; colourful insults ("Heartless! Idiot! Numbskull!"); with Ash ですわ -> crisp and proper |
| Greystone | うむ, terse | "Mm.", fragments, never more words than the JP |
| Rio, North District men | ねえ, だあ？, ～ちまう, rough | "ain't", dropped g's ("nothin'"), "pal", blunt |
| Hansen, Maillol (old men) | わし, じゃ, のう, ほっほっほ, ～さった | "eh?", "my girl/lad", "Ho ho ho", old-fashioned turns ("I'd wager", "in my granddad's day") |
| Merk (old woman) | あたしにゃ, ねえ, おいで | homely, "dearie", "bring 'em here" |
| Duke Prairial | 申す, なにとぞ, おまえ | formal, courtly ("I beg of you", "You will go with them. Is that understood?") |
| Ash | 私, だ, formal | measured commander |
| Demius | 私, ふん！, 俺 when cornered | pompous ("Hmph!"), venomous; "this I" -> breaks to raw rage |
| Townsfolk | varied | plain, natural; keep gossip and grumbles colourful |

## Approved pairs
Format: JP / EN (as written in the batch: ` / ` is only a forced break and is rarely needed; `<wait>`, `<clr>` copied).

- EVENT00 narration (Finn):
  - その国の噂を聞いたのは / 港の汚い酒場だった -> `I first heard of that kingdom in a filthy dockside tavern.`
  - 王国の名はモーダルグロウ / またの名を癒しの王国 -> `It was called Modalglow, also known as the Kingdom of Healing.`
  - 確かに俺はまだ一介の傭兵 / だが / 腕には自信がある -> `Sure, I was just another mercenary. But I knew what my sword arm could do.`
- EVENT01, Risp to Finn: 「どうしても妹に会いたいんです / お願いします…」 -> `"I simply must see my sister. Please... help me until I can see her.`
- EVENT01, Finn: 「どうやら傭兵の仕事は見つかりそうにないしな / 懐もさみしいときてる… / いいだろう あんたのボディガードを引き受けよう」
  -> `"Doesn't look like I'll find any mercenary work, and my purse is feeling light... Fine. I'll be your bodyguard."`
- EVENT06: 「迷ったぁ？」 -> `"Lost?!"`; 「とんだ世間知らずのお嬢様でございましたか」 -> `"Well, pardon me, milady. Didn't realise you were *that* sheltered."`
  (no asterisks in the game: write `"Well, pardon me, milady. Didn't know you were that sheltered."`)
- EVENT18, Hansen: 「ほっほっほ… / 知識聖堂にもこんなべっぴんがおったとはな」 -> `"Ho ho ho... Who'd have thought the Temple of Knowledge had a beauty like you, eh?"`
- EVENT39, Melissa: 「薄情者！ボケ！オタンコナス！」 -> `"Heartless! Moron! Numbskull!"`
- EVENT35, Greystone: 「上で音がする」 -> `"Noise. Upstairs."`
- EVENT02, Rio: 「大聖堂に行きたいだあ？ / 堀の内側にはネコの仔一匹入れねえよ」 -> `"The Cathedral? Ha! Not even a kitten gets past that moat."`
- **Corrected example** (first draft too flat): EVENT20, Hansen 「…肩を貸して… いや わしはお嬢さんのほうがいいのぉ」
  - flat: `"Lend me your shoulder... No, I'd prefer the young lady."`
  - approved: `"Lend me a shoulder, would ya... Ah, no, no. I'd much rather lean on the young lady, heh."`

## Conventions
- Speaker lines (form `speaker`, op 0x21) are just the name: `Finn`, `Risp`. 娘/男/女 as speaker -> `Girl`, `Man`,
  `Woman` until the name is known (don't reveal Kiral or Demius before the script names them).
- A quote that runs over several pages keeps one opening `"` at its start and one closing `"` at its end (the JP's
  「 ... 」 placement). The build indents quote rows by itself; never add leading spaces.
- Item pickups: `XXを手に入れた` -> `Got the XX!` ... keep it short: `Obtained XX.` for key items is fine too; be
  consistent within a batch. Party joins: `Greystone joined the party!`.
- Choice options (form `choice`, 10 cells): `Save` / `Don't save`, `Yes` / `No`, `Accept` / `Decline`.
- Exe printf lines: `%s` is a name, `%d`/`%ld` a number. Every specifier stays **in the same order** as the JP (the
  game passes the values in that order; swapping two would print the wrong value or crash): rephrase the English
  around them ("%s took %d damage" for %sは%dのダメージ). `%s%s` = a monster-letter prefix + name ("Goblin A"):
  keep them adjacent. `<icon>` and `<0c>1` (colour) stay where they are.
