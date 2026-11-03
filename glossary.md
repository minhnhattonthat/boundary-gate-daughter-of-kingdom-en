# Glossary - Boundary Gate: Daughter of Kingdom

Binding for every translator and reviewer. Agents propose additions in reports; only the controller edits this file.
`tools/lint.py` enforces every table row: when a line's JP contains the JP term (katakana terms match whole runs
only), its English must contain one of the EN forms (`/`-separated, case-insensitive), and never an Avoid spelling.
Rows marked `nocheck` in notes are guidance only.

## Rulings (asked of the user once; options and reasons in docs/decisions.md)
- Honorifics: kept, hyphenated, on names (キラル様 -> Kiral-sama, メリッサ君 -> Melissa-kun). Titles take an English
  form of address instead (司祭長さま -> "High Priest", 公 -> "Duke", お嬢さん/お嬢様 -> "young lady"/"milady").
  Name order: Western (given name first); credits too.
- Romanisation source: no official English or earlier fan patch exists (searched 2026-11-04), so names are the
  natural English reading of the katakana (they are Western-style names), Hepburn without macrons for anything
  Japanese (staff credits). Decisions D10.
- Credits: English.
- Register / flavour: low-fantasy adventure with a sci-fi twist (late reveal). Plain modern English with a light
  period feel; no modern slang ("OK", "guys", "cool"). Finn narrates in first person, past tense, dry and wry.
- Sound effects / interjections: English equivalents (キャー -> "Eeek!", ウォッ -> "Whoa!", ほっほっほ -> "Ho ho ho").
- Abbreviations: full names and terms everywhere; prefer engine changes over shortening (flag any abbreviation as a
  last resort with `LONG:`). Floor labels are the one standing exception: 地下N階 -> "BN", N階 -> "NF", 屋上 -> "Roof".

## Style rules
- Punctuation map: 「」 -> "...", 『』 -> '...' (inside a quote) or "..." , …/・・・/‥‥ -> ..., ！？ -> ?!, ～ -> drop or
  stretch the word ("Ugh~" -> "Uuugh"), ､ and 、 -> comma, 　 -> space.
- Colons are allowed (the build doubles them for the printer). Never `@` or `\`.
- Spoken lines keep their quotes: a 0x22 line that starts with 「 starts with `"` and its last page ends with `"`.
- Voices: `docs/style-reference.md`.

## Characters
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| フィン | Finn | | hero, mercenary, narrator (俺) | Fin |
| リスプ | Risp | | heroine; twin elder sister; Temple of Knowledge | Lisp, Rispu |
| キラル | Kiral | | Risp's twin; the current Daughter of the Kingdom | Chiral, Kiraru |
| メリッサ | Melissa | | resistance agent, sharp-tongued | |
| グレイストーン | Greystone | | Duke Prairial's giant retainer, taciturn | Graystone |
| グレイ | Grey | | short default party name for Greystone | Gray |
| アッシュ | Ash | | resistance leader, the Duke's son | |
| シーダ | Sheeda | | Rio's daughter, captive at Fort Amok; the new King's sweetheart | Cida, Shida |
| リオ | Rio | | North District fixer, Sheeda's father | |
| トールマン | Tallman | | Rio's man sent to Caliphos | Toleman |
| メルク | Merk | | old woman tending the wounded at Caliphos | |
| ハンセン | Hansen | | old miner in Rhodedahl | |
| グリソム | Grissom | | Rhodedahl metal expert | |
| マイヨール | Maillol | | old boatman at Tornam | |
| デミウス | Demius | | Vice High Priest of the Temple of Sorcery, villain | |
| プリゴ | Prigo | | Demius's family name (デミウス･プリゴ) | |
| プレリアール | Prairial | | Duke Prairial (プレリアール公) | |
| ホムンクリ | Homunculi | | Demius's artificial soldiers | |
| 始まりの母 | First Mother | | the ancient founder ("the First Mother") | |
| 新国王 | new King | nocheck | the young new King | |
| 精神寄生体 | Mind Parasite | | final enemy | |

## Places
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| モーダルグロウ | Modalglow | | the kingdom ("the Kingdom of Healing") | Mordalglow |
| アンブローズ | Ambrose | | the capital | Anburo |
| ワイズブルーム | Wisebloom | | seat of the Temple of Knowledge | |
| カリフォス | Caliphos | | the town that vanished (crater) | |
| ロードダール | Rhodedahl | | snowy mining town | Roododaaru |
| トーナム | Tornam | | port town | Toonamu |
| エルシノア | Elsinore | | Lake Elsinore (エルシノア湖) | |
| アモーク | Amok | | Fort Amok (アモーク要塞) | |
| アルフォース | Alforce | | tavern in Ambrose West | |
| 大聖堂 | Cathedral | | the Great Cathedral in Ambrose (where the Daughter resides) | |
| 大門 | Great Gate | | the city gate of Ambrose's North District | |
| 北地区 | North District | | also 西地区 West, 東地区 East, 南 South | |
| 西地区 | West District | | | |
| 東地区 | East District | | | |
| 監視塔 | Watchtower | | 東の監視塔 East Watchtower, 南の監視塔 South Watchtower | |
| 迷宮 | Labyrinth | | 心臓の紋章の迷宮 Heart Crest Labyrinth | Maze, Dungeon |

## Organisations, titles
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 知識聖堂 | Temple of Knowledge | | | |
| 魔導聖堂 | Temple of Sorcery | | | |
| 医療聖堂 | Temple of Medicine | | | |
| 治療聖堂 | Temple of Healing | | map name | |
| 魔導聖堂長 | High Priest of Sorcery | | head of the Temple of Sorcery | |
| 医療聖堂長 | High Priest of Medicine | | | |
| 知識聖堂長 | High Priest of Knowledge | | | |
| 副司祭長 | Vice High Priest | | Demius's rank | |
| 司祭長 | High Priest | | | |
| 王国の娘 | Daughter of the Kingdom | | title of the girl who links to the Ancient Knowledge | Princess |
| 戒厳令 | martial law | | | |
| 傭兵 | mercenary/mercenaries | | | |
| 反魔導聖堂組織 | resistance | | "the resistance against the Temple of Sorcery"; 組織 alone = "the resistance" | |

## Lore terms
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| バウンダリーゲート | Boundary Gate | | the great vortex of light, source of all magic | |
| ゲート | Gate | | short for the Boundary Gate or a small gate like it | |
| いにしえの知識 | Ancient Knowledge | | capitalised: the AI left by the First Mother | |
| 紋章 | Crest | | the five Crests; 心臓 Heart, 牙 Fang, 瞳 Iris, 五芒星 Pentagram, 失われた Lost | Emblem, Symbol |
| 心臓の紋章 | Heart Crest | | | |
| 牙の紋章 | Fang Crest | | | |
| 瞳の紋章 | Iris Crest | | | Eye Crest |
| 五芒星の紋章 | Pentagram Crest | | | |
| 失われた紋章 | Lost Crest | | | |
| ゲートの守護者 | Guardian of the Gate | | | |
| サブシステム | subsystem | | | |
| 人工知能 | artificial intelligence/AI | | | |
| アイリス | Iris | | AI subsystem name | |
| ファング | Fang | | AI subsystem name | |
| ハート | Heart | | AI subsystem name | |
| ペンタグラム | Pentagram | | AI subsystem name | |

## Menus, stats, status effects
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 道具 | Items | nocheck | field menu | |
| 魔法 | Magic | nocheck | | |
| 装備 | Equip | nocheck | | |
| 状態 | Status | nocheck | | |
| 設定 | Settings | nocheck | | |
| ＨＰ | HP | | | |
| ＭＰ | MP | | | |
| 経験値 | EXP/experience | | | |
| 毒 | Poison | nocheck | status | |
| 沈黙 | Silence | nocheck | status | |
| 睡眠 | Sleep | nocheck | status | |
| 気絶 | KO | nocheck | status (fainted) | |
| 瀕死 | Critical | nocheck | status (near death) | |

## Spells (exe; name 22 cells)
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| ディスチャージ | Discharge | | escape from a labyrinth | |
| サイレント | Silent | | | |
| アスリープ | Asleep | | | |
| デフライズ | Defrise | | defense up | |
| チャージライズ | Charge Rise | | attack up | |
| リカバリー | Recovery | | | |
| アンチドーテ | Antidote | | spell; the potion is Anti-Poison | |
| リバイブ | Revive | | | |
| ライズ | Rise | | | |
| ヘブンズヒール | Heaven's Heal | | | |
| ヒールオール | Heal All | | | |
| ヒールスコール | Heal Squall | | | |
| ヒールシャワー | Heal Shower | | | |
| ヒール | Heal | | | |
| ゲライノ | Gelaino | | | |
| メガボンバー | Mega Bomber | | | |
| エクスプロージョン | Explosion | | | |
| ボンバー | Bomber | | | |
| バジェラ | Bajera | | | |
| スパークボール | Spark Ball | | | |
| ライトニング | Lightning | | | |
| ヘルファイア | Hellfire | | | |
| ファイアストーム | Firestorm | | | |
| ボーンファイア | Bonfire | | | |

## Items / equipment
Plain English equipment names: ショートソード Short Sword, レイピア Rapier, ロングソード Long Sword, アクス/アックス Axe,
ロッド Rod, ワンド Wand, スピア Spear, シールド Shield, メイル Mail, リング Ring, ポーション Potion, ストーン Stone,
ロール Scroll; シルバー Silver, セラミック Ceramic, フレイム Flame, サンダー Thunder, アイス Ice, アイアン Iron,
ヒーリング Healing, レザー Leather, ライト Light, スモール Small, ラージ Large, グレート Great, バトル Battle,
ハンド Hand, ブレスト Breast, プレート Plate, チェイン Chain, マスター Master, マジック Magic, ホーリー Holy, ライフ Life.
`+N` suffixes stay. 紋章のソード -> Crest Sword (Crest Axe, Crest Spear, Crest Wand).
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 大門の通行証 | Great Gate Pass | | | |
| アンチポイズン | Anti-Poison | | | |
| ラージポーション | Large Potion | | | |
| ポーション | Potion | | | |
| 山羊のカギ | Goat Key | | | |

## Decisions from earlier batches
- (none yet)
