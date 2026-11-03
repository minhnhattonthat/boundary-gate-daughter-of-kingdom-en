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
- Spelling: British (colour, harbour, armour, defence, rumour); "-ize" verbs are fine either way, keep one per line.
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
| 王国の娘 | Daughter of the Kingdom / Daughters of the Kingdom | | title of the girl who links to the Ancient Knowledge | Princess |
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
| ゲートの守護者 | Guardian of the Gate / Guardians of the Gate | | | |
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
| 設定 | Config | nocheck | field-menu label: the 6-cell column (D12) | |
| ＨＰ | HP | | | |
| ＭＰ | MP | | | |
| 経験値 | EXP/experience | | | |
| 毒 | Poison | nocheck | status | |
| 沈黙 | Silence | nocheck | status | |
| 睡眠 | Sleep | nocheck | status | |
| 気絶 | KO | nocheck | status (fainted) | |
| 瀕死 | Weak | nocheck | status (near death); 'Weak' fits the field-menu status row (phase 7) | |

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

## Common nouns, speakers, labels (from wave 1; guidance, not lint-enforced)
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 道具屋 | Item Shop | nocheck | lower case in running text | Items Shop, Tool Shop |
| 武具屋 | Arms Shop / Armoury | nocheck | room/NPC label "Arms Shop"; map name "... Armoury" | Armory |
| 武器屋 | Weapon Shop | nocheck | | |
| 鍛冶屋 | Smithy / Blacksmith | nocheck | | |
| 治療院 | Clinic | nocheck | also 治療所 | Infirmary |
| 酒場 | Tavern | nocheck | | |
| 宿屋 | Inn | nocheck | | |
| 連絡所 | Army Post | nocheck | | |
| 鉱山長 | Mine Overseer | nocheck | | Mine Chief |
| 坑夫長 | Head Miner | nocheck | | |
| 坑道 | Mine / Mine Shaft | nocheck | floor labels "Mine B1" | |
| 地下水道 | Waterway | nocheck | "Ambrose Waterway"; アモーク要塞地下水路 Fort Amok Waterway | Sewers |
| 倉庫街 | Warehouse District | nocheck | | |
| バラック | Shack | nocheck | Shack A/B/C | |
| 最後の迷宮 | Final Labyrinth | nocheck | exe map names (the banners say 失われた紋章の迷宮 Lost Crest Labyrinth: both as in the JP) | |
| 大男 | Giant | nocheck | speaker before Greystone is named | |
| 医師 | Doctor | nocheck | | |
| 番兵 | Guard | nocheck | Guard A/B | |
| 町人Ａ | Townsman A | nocheck | | |
| 主人 | Innkeeper / Barkeep / Shopkeeper | nocheck | by the room | |
| 生体端末 | living terminal | nocheck | 端末 terminal | |
| 多重人格型人工知能システム | multi-personality AI system | nocheck | | |
| 山羊のカギ | Goat Key | | 山羊の印 goat crest (Melissa: 山羊の紋章) | |
| 牙の印の鍵 | Fang Crest Key | | likewise 瞳/心臓/五芒星 -> Iris/Heart/Pentagram Crest Key | Fang Key |
| 五芒星のアミュレット | Pentagram Amulet | | | |
| 銀の鍵 | Silver Key | | | |
| 魔石 | Stone | nocheck | item category | |
| 水薬 | Potion | nocheck | item category | |
| 巻物 | Scroll | nocheck | item category | |

## Stats (exe)
攻撃 Attack, 防御 Defence, 武力 Combat, 魔力 Magic, 速力 Speed, 体力 Vitality, 筋力 Strength, 知力 Intellect,
能力値 Stats, ＬＶ LV, 経験値 EXP. Field menu: 常時 Anytime, 戦闘中 In Battle, 移動時/移動中 On Field, 特殊 Special.
Settings: 見る/見ない Show/Skip, 普通/少ない/多い Normal/Low/High.

## Decisions from earlier batches
- Narration person follows the JP: third person where it names フィン/フィン達/二人, Finn's first person in his monologues.
- Speaker lines keep the JP's trailing row break (`Name /`); the dialogue after starts on row 2.
- Item pickups: "Got the X!" / "Found a X." / "Obtained the X." (the JP varies too).
- Monster names: natural reading of the katakana, spelled to avoid accidental words (ラムビッチ Rambich, ビッチバス Bichbus).
- Battle and shop messages in past tense ("%s took %d damage.").
- 最後の迷宮 vs 失われた紋章の迷宮: kept as two names, as the JP has them.
