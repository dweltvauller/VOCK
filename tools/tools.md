# Tools

Standalone utility scripts for the VOCK project.

---

## dict_lookup.py

Interactive MFA pronunciation dictionary lookup. Type a word, get its ARPA/IPA transcription(s). If a word isn't found, suggests close matches via fuzzy lookup.

**Dependencies:** None (stdlib only)

**Usage:**
```
python3 tools/dict_lookup.py [dict_name]
```

`dict_name` defaults to `english_us_arpa`. The `.dict` extension is optional.

**Where it looks for dictionaries:**
1. MFA system folders:
   - `~/Documents/MFA/pretrained_models/dictionary/`
   - `~/.local/share/montreal-forced-aligner/pretrained_models/dictionary/`
2. Project custom dictionaries: `vock/dictionaries/custom.<dict_name>.dict`

Custom entries take priority over MFA entries for any word they define.

---

## msg_localize.py

This tool is under development.

Reads audio tags from the source-language MSG files (set by `language` in `vock.cfg`), injects them into matching foreign-language MSG files from an RPU repo, then rebuilds `vock.dat` with the tagged foreign MSGs added.

**Dependencies:** None (stdlib only)

**Configuration:** Defaults for source language and all paths are read from `vock.cfg` (`[general] language` and `[paths]`). `PATHS["rpu_text"]` (default `../rpu/data/text`) is resolved against `vock.cfg`'s own folder rather than `project_root`, since the RPU repo is a sibling of `vock/` itself, not part of whichever project `project_root` points at.

**Expected folder layout** (relative to the `vock/` project root):
```
<parent>/
  vock/          ← this repo
    msg/         ← tagged source-language MSGs (source of truth for audio tags)
    dat/
      vock.dat   ← source DAT
    loc/         ← output: rebuilt DAT and tagged foreign MSGs (created on first run)
  rpu/           ← RPU repo (sibling of vock)
    data/text/
      german/dialog/
      french/dialog/
      ...
```

**Usage:**
```
python3 tools/msg_localize.py [options]
```

| Option | Default | Description |
|---|---|---|
| `--msgdir PATH` | `vock/msg` (from `PATHS["msg"]`) | Tagged source-language MSG folder |
| `--rpu-text PATH` | `../rpu/data/text` (from `PATHS["rpu_text"]`) | RPU data/text folder |
| `--tagged PATH` | `vock/loc/tagged` (from `PATHS["loc"]`) | Output folder for injected foreign MSGs |
| `--dat-src PATH` | `vock/dat` (from `PATHS["dat"]`) | Source DAT folder |
| `--dat-out PATH` | `vock/loc` (from `PATHS["loc"]`) | Output folder for rebuilt DATs |
| `--dat-files FILE ...` | `vock.dat` (from `PATHS["dat"]`) | DAT filenames to rebuild |
| `--encoding ENC` | `cp1252` | Fallback encoding for MSG files |
| `--langs LANG ...` | all non-source languages | Languages to process (9 supported: english, german, french, spanish, italian, polish, russian, czech, hungarian) |
| `--dry-run` | — | Preview changes without writing |
| `--no-dat` | — | Tag MSGs but skip DAT rebuild |

---

## vock_tag.py

Assigns sequential audio tags (e.g. `mor1`, `mor2`, ...) to a character's talking-head and float lines in their MSG file, by cross-referencing the SSL script(s) that reference that MSG. Only touches lines with an empty tag field `{}` — already-tagged lines are left alone. The source MSG under `msg/` is never modified — the tagged result is written to a separate `tag/` folder instead.

**Dependencies:** None (stdlib only)

**Configuration:** Read from `vock.cfg`'s `[paths]`:
- `msg` — source MSG folder (resolved against `project_root`, like the main pipeline). Read-only — never written to.
- `tag` — output folder for tagged MSG copies (resolved against `project_root`; created automatically if missing).
- `characters` — the character table (`msg_stem, name, prefix, ssl_stems, head`), loaded dynamically from whatever `.py` file it points to.
- `scripts_src` — this project's own SSL source (flat folder, typically only the handful of characters whose dialog was modified for this mod).
- `rpu_scripts_src` — base RP SSL source folder (default `../rpu/scripts_src`), resolved against `vock.cfg`'s own folder rather than `project_root`, since the RPU repo is a sibling of `vock/` itself.

**SSL lookup order:** for each `ssl_stem` on the character's entry, the project's own `scripts_src` is checked first; if not found there, it falls back to `rpu_scripts_src` (searched recursively across area subfolders), the same "project first, RPU fallback" pattern `msg_localize.py` uses for translations.

**Usage:**
```
python3 tools/vock_tag.py <prefix>
python3 tools/vock_tag.py brige
```

Prints a report of talking-head lines, float lines, PC lines, unused lines, and any lines referenced in SSL but missing from the MSG — then writes the assigned tags to `tag/<msg_stem>.msg` (preserving original encoding and line endings). If a tagged copy already exists in `tag/`, it's used as the read source instead of the original, so re-running on the same prefix builds on earlier tagging rather than starting over.


## dialogue_sim.py

This tool is under development.

Point this tool to a msg and ssl file, and it will let you simulate the dialogue with that particular NPC.