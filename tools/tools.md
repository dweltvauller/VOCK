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
| `--lang