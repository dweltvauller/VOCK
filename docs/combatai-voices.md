# Investigation: voicing combat-AI taunts

Status: **investigation only — nothing here is implemented.**

Can V.O.C.K. produce voice-over audio for the combat barks NPCs shout during a fight
("Take that!", "Ow, my arm!"), the way it already does for talking-head dialogue and
ambient floats? This note records what the pipeline and the engine do today, where the
gap is, and what closing it would take on each side.

Prompted by the **`fission-ce`** engine fork (cambragol), whose `VockFloats` subsystem
already plays non-dialogue voice-over for ambient floats but stops short of combat barks —
even though its own docs describe "combat barks" as a float. Engine references below are to
that fork; `vock.py` references are to this repo at the time of writing.

## 1. How combat taunts work today (engine side)

Combat taunts are driven by `combatai.msg` (a.k.a. `combat_ai.msg`), a standard Fallout 2
message file:

- Every entry is `{<number>}{}{<text>}` — **the middle (audio) bracket is empty for all
  ~3,500 vanilla entries (~3,671 in RPU).** There is no voiced combat-taunt content
  anywhere in the game.
- Numbering is 100-wide blocks per critter archetype. Within a block the `00–99` offset
  encodes hit location (`00–09` head, `10–19` left arm, … `90–99` groin). `1000s` are
  victim-hit lines (Wimpy / Normal / Tough / Berserk / Robot / Primitive / Ghoul / Raider /
  Junkie); `2000s` are attacker taunts (same archetypes + Guard / Soldier / Leader);
  `4000–36000` are per-location / named-critter taunt blocks (Arroyo, Den, … Enclave,
  plus uniques like The Brain).
- Which sub-range a given critter draws from is set **per AI packet** in `data/ai.txt`
  (`run_start/end`, `move_*`, `attack_*`, `miss_*`, and `hit_<location>_*`), together with
  `chance` (taunt probability), `font`, `color`, `outline_color`.

Playback path (`fission-ce/src/combat_ai.cc`):

| Step | Function | What it does |
|------|----------|--------------|
| pick | `_combatai_msg()` `:3805` | gated on `preferences.combat_taunts`; rolls `randomBetween(1,100) > ai->chance`; picks `messageListItem.num = randomBetween(start, end)` for the RUN/MOVE/ATTACK/MISS/HIT type; `messageListGetItem(&gCombatAiMessageList, …)` `:3871`; copies **only `messageListItem.text`** into the bark string `:3877`; registers `_ai_print_msg` as an animation callback `:3880` |
| show | `_ai_print_msg()` `:3884` | **the entire body is** `textObjectAdd(critter, string, ai->font, ai->color, ai->outline_color, &rect)` + `tileWindowRefreshRect()` |

There is **no** `gsound` / `speechLoad` / `soundPlay` call anywhere on this path, in either
`fission-ce` or upstream Fallout2-CE. The only sound calls in `combat_ai.cc` are
weapon/impact SFX in attack resolution, unrelated to taunts. `combat_taunts` (the vanilla
preference) only gates whether the *text* float appears at all.

The message loader already parses the middle bracket into `MessageListItem::audio` for
*every* list, `combatai.msg` included — `_combatai_msg` simply never reads that field.

## 2. How VOCK handles audio today

- `parse_msg()` (`vock.py:381`) matches `MSG_LINE_RE` = `{num}{audio}{text}` (`vock.py:379`)
  and **keeps only lines whose middle bracket is non-empty** — it repurposes that field as
  the audio tag. A `combatai.msg` line `{2000}{}{…}` is skipped outright.
- The audio tag's trailing digits are stripped to derive the speech sub-folder:
  `_npc_folder("mor1") → "mor"` (`vock.py:665`). `collect_dat_entries()` (`vock.py:669`)
  then emits `sound\speech\<npc>\<tag>.acm` / `.lip` / `.txt`.
- **Talking-head assumption:** stems are discovered from `lip/` (`discover_from="lip"`),
  the pipeline aligns every line with MFA and writes a LIP, and the `lip` step marks a stem
  `FAIL` if it has no TextGrid.
- **Floats** are the existing exception and the closest analog. `float_filter.cfg`
  (`vock.py:248`–`313`, `README.md` "Float lines") lists `PREFIX  start-end` ranges over
  the numeric suffix of a tag; matching lines are packed into a **separate**
  `vock_floats.dat` discovered from `acm/` instead of `lip/` (`vock.py:1480`). Floats still
  land at `sound\speech\<npc>\<tag>.acm` — same sub-foldered path as dialogue.
- Nothing in this repo mentions combat, `combatai`, taunts, or narration today.

## 3. The gap

Combat taunts are conceptually floats — overhead text, no talking head, no lip-sync — but:

1. **VOCK won't parse them.** `combatai.msg` taunt lines have an empty audio field, so
   `parse_msg` drops all of them. Something has to put a tag in that field.
2. **VOCK would mis-file them.** Even tagged, they'd be treated as talking-head dialogue
   (MFA + LIP required, `sound\speech\<npc>\…` path) unless routed through the float path.
3. **The engine won't play them.** `_combatai_msg` / `_ai_print_msg` never touch the audio
   field or any speech loader. `fission-ce`'s `VockFloats` voice path
   (`speechLoadFloat()`, `game_sound.cc:1363`) is reached from
   `_scr_get_msg_str_speech()` (`scripts.cc`, the `message_str`/`mstr` speech branch) —
   which the combat-AI code does not call.
4. **Path shape mismatch.** `speechLoadFloat()` resolves audio **flat**:
   `sound/speech/<audiofield>.acm|wav`, uppercased, no sub-folder
   (`gameSoundFindSpeechSoundPath`, `game_sound.cc:2322`). The deployed
   `FISSION/mods/mod_vock.dat` is likewise a loose folder of flat
   `sound/Speech/<tag>.wav` files — **not** VOCK's packed
   `sound\speech\<npc>\<tag>.acm` DAT2 output. Whatever currently ferries VOCK output into
   that FISSION install is already flattening the tree, converting ACM→WAV, and dropping
   LIP/TXT. Any taunt-voice output has to match that flat shape too.

## 4. Options for wiring it up

### Engine (fission-ce)

**Option A — one hook in `_combatai_msg` (recommended).** After `messageListGetItem`
(`combat_ai.cc:3871`), when `messageListItem.audio[0]` is set and
`settings.enhancements.vock_floats && settings.mod_settings.voiced_floats`, call
`speechLoadFloat(messageListItem.audio, critter)`. This mirrors `scripts.cc:3339`-ish and
reuses the whole existing float-speech machinery: the dedicated `gFloatSpeechSlots` pool
(so two critters can bark at once without cutting each other off), distance/Perception
volume falloff, obstruction dampening, censor bleep for badword-filtered lines, per-frame
volume upkeep. It is the same shape of change the `feature/holodisk-audio` branch used to
voice holodisk reading (`56746bc`, "Add voiced narration to holodisks, gated behind
VockFloats") — a solid precedent.

**Option B — route taunts through `_scr_get_msg_str_speech`.** Heavier; that function is
built around script `message_str` calls and dialogue-window state. No clear advantage over
A for this case.

No new sfall opcode or config key is needed — `VockFloats` (master switch, `fission.cfg
[enhancements]`) and `VoicedFloats` (`game.cfg [vock-floats]`) already exist and already
gate exactly this class of non-dialogue speech.

### VOCK (vock.py)

The taunt lines need to become a recognised **float-like** class:

1. **Tag the source.** Accept a `combatai.msg` whose taunt lines carry audio tags
   (`{2000}{cai2000}{…}`), or synthesise a tag from the entry number for a designated file
   (e.g. `combatai<num>`). A dedicated config key (`combatai_msg` / a `combatai_filter.cfg`
   analogous to `float_filter.cfg`) is the natural fit.
2. **Skip the talking-head machinery** for those stems — no head FRM, no LIP; MFA still
   runs on the `{text}` for timing only if wanted, but the `lip` step must not `FAIL` them
   for a missing TextGrid. The float path (`vock.py:1480`–`1507`, `discover_from="acm"`,
   `include_msg=False`) already does most of this.
3. **Emit flat.** Write taunt audio as `sound\speech\<tag>.acm` (no `_npc_folder`
   sub-folder) so `speechLoadFloat`'s flat lookup finds it — or add an explicit
   flatten/convert step matching the existing `mod_vock.dat` deployment. Pack into its own
   archive (`vock_combatai.dat`) or fold into `vock_floats.dat`.

## 5. Open questions / risks

- **Voice identity.** A `combatai.msg` message number is shared by every critter whose AI
  packet range covers it. A flat `sound/speech/<num>.acm` means a raider, a tribal and a
  mutant all say line `2000` in the same voice. Per-faction voicing needs either
  per-AI-packet keying in the engine lookup, or separate
  `combatai_<mod>.msg` blocks — `fission-ce` already supports the latter via
  `loadModCombatAiMsgFiles()` (`combat_ai.cc:4058`), merging `combatai_*.msg` at
  non-colliding base-ID offsets. Voicing would follow the same per-mod block boundary.
- **Volume of content.** ~3,500 lines. Even one voice for the common `1000`/`2000`
  archetype blocks is a large recording effort; the per-location `4000+` blocks multiply
  it. A realistic first pass is one archetype set, or one faction's `combatai_<mod>.msg`.
- **Line style.** Taunts are short exclamations, often with deliberate misspellings for
  slurred/injured delivery (`{1004}{}{By doath! Dew tore off by doath!}`). MFA alignment is
  optional here (no LIP), so this mostly affects the custom dictionary if alignment is run
  at all.
- **Badword filter.** Handled already on the engine side — a filtered taunt with audio
  plays the censor bleep instead of the real line (`CensorBleep`), same as any other float.
- **`combat_taunts=0`.** If the player has combat taunts off, `_combatai_msg` returns
  before any display; the Option A hook sits after that check, so audio inherits the same
  on/off switch for free.

## 6. Recommended next step

Prototype **Option A** on a `fission-ce` branch against a tiny hand-made
`combatai_test.msg` (a dozen tagged lines + flat `sound/speech/*.acm`), confirm
`speechLoadFloat` fires from the combat path with pool/falloff/bleep behaving, then design
the `vock.py` `combatai` class around whatever path shape that prototype settles on.
