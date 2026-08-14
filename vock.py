#!/usr/bin/env python3
"""
vock.py  ─  V.O.C.K.  Vocal Output Creation Kit
           Complete Fallout 2 voice modding pipeline.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  msg ────────[parse CP1252]────────────────► txt (one per dialog line)
                                              ↕ optional: edit manually here
  audio ──────[ffmpeg normalize + encode]───► wav  (22050 Hz mono 16-bit)
  wav ────────[snd2acm / wine]──────────────► acm
  wav + txt ──[MFA]─────────────────────────► textgrid
  textgrid ─────────────────────────────────► lip
  msg + acm + lip + txt + int ──────────────► dat/vock.dat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FOLDER STRUCTURE (all created automatically)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ./msg/          ← put your .MSG file(s) here
  ./audio/        ← put your audio files here (MP3, WAV, FLAC, M4A, …)
  ./txt/          ← generated/editable: one .txt per audio line
  ./wav/          ← generated: 22050 Hz mono 16-bit PCM (ready for ACM/MFA)
  ./acm/          ← generated: Fallout 2 ACM files
  ./textgrid/     ← generated: MFA TextGrid files
  ./lip/          ← generated: Fallout 2 LIP files
  ./scripts/      ← put pre-compiled Fallout 2 .INT script files here (packed into dat as scripts\*)
  ./unknown.txt   ← generated: words not recognized by the dictionary
  ./dat/vock.dat  ← generated: ready-to-install Fallout 2 DAT archive

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEPS  (run with --steps or skip with --skip)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  msg   Parse .MSG → individual .txt files in txt/
  wav   Convert audio/ → standardised 22050 Hz mono 16-bit in wav/
  acm   wav/ → ACM via snd2acm.exe
  mfa   MFA forced alignment → textgrid/
  lip   textgrid/ → lip/
  dat   Pack msg/ + acm/ + lip/ + txt/ → dat/vock.dat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Full pipeline:
  conda activate aligner
  python3 vock.py

  # Text-correction workflow (human-in-the-loop):
  python3 vock.py --steps msg          # extract TXT files
  #  … edit txt/mor1.txt, txt/mor2.txt, etc. …
  python3 vock.py --steps wav mfa lip dat   # resume from audio

  # Rebuild just the DAT:
  python3 vock.py --steps dat

  # Skip ACM generation (no snd2acm needed):
  python3 vock.py --skip acm

  # Change language:
  python3 vock.py --language spanish

  # All CLI options:
  python3 vock.py [--language LANG] [--steps STEP [STEP ...]] [--skip STEP [STEP ...]]

  All paths and settings are configured in vock.cfg.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUPPORTED LANGUAGES  (--language)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  arpabet   english_us_arpa   dictionaries/custom.english_us_arpa.dict
  english   english_mfa       dictionaries/custom.english_mfa.dict
  spanish   spanish_mfa       dictionaries/custom.spanish_mfa.dict
  russian   russian_mfa       dictionaries/custom.russian_mfa.dict
  german    german_mfa        dictionaries/custom.german_mfa.dict
  italian   italian_mfa       dictionaries/custom.italian_mfa.dict
  french    french_mfa        dictionaries/custom.french_mfa.dict
  hungarian hungarian_mfa     dictionaries/custom.hungarian_mfa.dict
  polish    polish_mfa        dictionaries/custom.polish_mfa.dict
  portuguese portuguese_mfa   dictionaries/custom.portuguese_mfa.dict

  Phoneme maps are loaded from ./phonemes/phonemes_<mfa_name>.py
  Each file must export exactly one dict named PHONEME_TABLE.
"""

import argparse
import configparser
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vock.cfg")
_parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
if not _parser.read(_CONFIG_PATH, encoding="utf-8"):
    sys.exit(f"[ERROR] Could not read config file: {_CONFIG_PATH}")

config = {
    "language":     _parser.get("general", "language"),
    "project_root": _parser.get("general", "project_root", fallback="./"),
    "paths":    dict(_parser["paths"]),
    "settings": {
        "mfa_env": _parser.get("settings", "mfa_env"),
        "lufs":    _parser.getfloat("settings", "lufs"),
        "no_norm": _parser.getboolean("settings", "no_norm"),
    },
}

# ─── Language configuration ───────────────────────────────────────────────────

#: Maps --language value → MFA model/dictionary name
LANGUAGE_CONFIG: dict[str, str] = {
    "arpabet":    "english_us_arpa",
    "english":    "english_mfa",
    "spanish":    "spanish_mfa",
    "russian":    "russian_mfa",
    "german":     "german_mfa",
    "italian":    "italian_mfa",
    "french":     "french_mfa",
    "hungarian":  "hungarian_mfa",
    "polish":     "polish_mfa",
    "portuguese": "portuguese_mfa",
    "czech":      "czech_mfa",
}

#: Maps --language value → Windows code page used by Fallout 2 MSG/TXT files.
#: CP1252 (Western European) covers English, Spanish, French, German, Italian,
#: Hungarian, and Portuguese.  Polish and Czech use CP1250 (Central European).
#: Russian uses CP1251 (Cyrillic).
LANG_ENCODING: dict[str, str] = {
    "arpabet":    "cp1252",
    "english":    "cp1252",
    "spanish":    "cp1252",
    "french":     "cp1252",
    "german":     "cp1252",
    "italian":    "cp1252",
    "hungarian":  "cp1252",
    "portuguese": "cp1252",
    "polish":     "cp1250",
    "czech":      "cp1250",
    "russian":    "cp1251",
}

def lang_enc(language: str) -> str:
    """Return the Windows code page for MSG/TXT files in the given language."""
    return LANG_ENCODING.get(language, "cp1252")

def load_phoneme_module(mfa_name: str):
    """
    Dynamically import ./phonemes/phonemes_<mfa_name>.py and return the module.
    Exits with an error if the file does not exist.
    """
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(script_dir, "phonemes", f"phonemes_{mfa_name}.py")
    if not os.path.isfile(module_path):
        sys.exit(f"\n[ERROR] Phoneme file not found: {module_path}\n"
                 f"Cannot proceed without a valid phoneme mapping for {mfa_name}.")
    spec   = importlib.util.spec_from_file_location(f"phonemes_{mfa_name}", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_phoneme_converter(mfa_name: str, module) -> callable:
    """
    Return a ``(str) -> int`` callable for the given MFA model.

    Every phoneme file must export a dict named PHONEME_TABLE.
    The stripping/normalisation logic lives here, not in the phoneme files.

    ARPAbet (english_us_arpa):
      Strip trailing stress digits (0/1/2), upper-case, look up in PHONEME_TABLE.

    IPA-based models (everything else):
      Strip MFA stress markers (ˈ ˌ) and length mark (ː), lower-case,
      look up in PHONEME_TABLE.

    Falls back to 0x0D (open-mouth shape) for unknown symbols in both cases.
    """
    if not hasattr(module, "PHONEME_TABLE"):
        sys.exit(f"\n[ERROR] phonemes_{mfa_name}.py must export a dict named PHONEME_TABLE.")

    table    = module.PHONEME_TABLE
    FALLBACK = 0x0D

    if mfa_name == "english_us_arpa":
        def _convert(phoneme: str) -> int:
            p = re.sub(r"\d", "", phoneme.strip().upper())
            return table.get(p, FALLBACK)
    else:
        def _convert(phoneme: str) -> int:
            p = re.sub(r"[ˈˌː]", "", phoneme.strip().lower())
            return table.get(p, FALLBACK)

    return _convert

# ─── Character NPC include list ───────────────────────────────────────────────

def load_npc_prefixes(npc_file: str | None) -> set[str]:
    """
    Read npc_filter.cfg (or any path set in config["paths"]["npc_filter"]).
    Returns a set of lower-cased NPC tag prefixes to include in the pipeline.
    Returns an empty set when the file is absent or unset — meaning process all.

    File format: one prefix per line, # comments, blank lines ignored.
        arth    # King Arthur
        ahs7    # Oz
    """
    if not npc_file or not os.path.isfile(npc_file):
        return set()
    included: set[str] = set()
    with open(npc_file, encoding="utf-8") as fh:
        for raw in fh:
            token = raw.split("#", 1)[0].strip().lower()
            if token:
                included.add(token)
    return included


def filter_by_prefix(items: list, include: set[str], key=lambda x: x[0]) -> list:
    """
    Keep items whose NPC tag starts with a prefix listed in *include*.
    key(item) must return the tag string (e.g. 'mor1', 'ahs71').
    Returns items unchanged when include is empty (process all).
    Prefixes are matched longest-first to avoid shorter prefixes shadowing longer ones.
    """
    if not include:
        return items
    prefixes = sorted(include, key=len, reverse=True)
    return [it for it in items
            if any(key(it).lower().startswith(p) for p in prefixes)]


def load_float_ranges(float_file: str | None) -> dict[str, list[tuple[int, int]]]:
    """
    Read float_filter.cfg (or any path set in config["paths"]["float_filter"]).
    Returns {PREFIX: [(start, end), …]} mapping float audio-tag-number ranges per NPC prefix.
    Returns an empty dict when the file is absent or unset.

    File format: PREFIX  start-end  (# comments, blank lines ignored)
        mor   1-2       # Morlis floats (tags mor1, mor2)
        zaius 1         # Zaius float   (tag zaius1)
    Numbers refer to the numeric suffix of the audio tag, not the MSG line number.
    """
    result: dict[str, list[tuple[int, int]]] = {}
    if not float_file or not os.path.isfile(float_file):
        return result
    with open(float_file, encoding="utf-8") as fh:
        for raw in fh:
            token = raw.split("#", 1)[0].strip()
            if not token:
                continue
            parts = token.split(None, 1)   # split on first whitespace only
            if len(parts) < 2:
                continue
            prefix = parts[0].lower()
            for chunk in parts[1].split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                if "-" in chunk:
                    try:
                        lo, hi = chunk.split("-", 1)
                        result.setdefault(prefix, []).append((int(lo.strip()), int(hi.strip())))
                    except ValueError:
                        print(f"  [warn] float_filter.cfg: invalid range '{chunk}' for '{prefix}' — skipping")
                else:
                    try:
                        n = int(chunk)
                        result.setdefault(prefix, []).append((n, n))
                    except ValueError:
                        print(f"  [warn] float_filter.cfg: invalid entry '{chunk}' for '{prefix}' — skipping")
    return result


def is_float_line(tag: str, float_map: dict) -> bool:
    """Return True if this line should be treated as a float (ACM only, no LIP).

    Matching is done on the numeric suffix of the audio tag (e.g. 'eric3' → 3),
    not the MSG line number, so ranges in float_filter.cfg are version-stable.

    Prefix matching uses startswith (longest key first), mirroring filter_by_prefix,
    so digit-ending prefixes like 'ahs7' are handled correctly — e.g. 'ahs739' maps
    to prefix 'ahs7' with suffix '39', not prefix 'ahs' with suffix '739'.
    """
    if not float_map:
        return False
    tag_lower = tag.lower()
    for prefix in sorted(float_map, key=len, reverse=True):
        if tag_lower.startswith(prefix):
            suffix = tag_lower[len(prefix):]
            if not suffix.isdigit():
                break
            tag_num = int(suffix)
            for lo, hi in float_map[prefix]:
                if lo <= tag_num <= hi:
                    return True
            break
    return False


# ─── MFA alignment lock list ───────────────────────────────────────────────────

def load_mfa_lock(lock_file: str | None) -> set[str]:
    """
    Read mfa_lock.cfg (or any path set in config["paths"]["mfa_lock"]).
    Returns a set of lower-cased audio-tag stems whose TextGrid must never be
    regenerated by the 'mfa' step — e.g. after a bad MFA alignment (a batching
    artifact, a hand-tuned pause) has been manually corrected and should
    survive future full pipeline runs.

    Locked stems are excluded from the MFA corpus entirely; their existing
    TextGrid is left untouched. If a locked stem has no existing TextGrid,
    a warning is printed (there is nothing to protect, and 'lip' will fail
    for it) since that likely means the lock entry is stale.

    File format: one audio tag per line, # comments, blank lines ignored.
        arth2   # MFA batch-alignment bug, fixed by hand — see notes
    """
    if not lock_file or not os.path.isfile(lock_file):
        return set()
    locked: set[str] = set()
    with open(lock_file, encoding="utf-8") as fh:
        for raw in fh:
            token = raw.split("#", 1)[0].strip().lower()
            if token:
                locked.add(token)
    return locked


def resolve_custom_dict(mfa_name: str, explicit_path: str | None) -> str | None:
    """
    Return the path for the language-specific custom dictionary, or *explicit_path*
    if the caller supplied one.  Returns None when no file exists.
    """
    if explicit_path:
        return explicit_path
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    candidate   = os.path.join(script_dir, "dictionaries", f"custom.{mfa_name}.dict")
    return candidate if os.path.isfile(candidate) else None

def resolve_mfa_dict_paths(mfa_name: str) -> list[str]:
    """Return the default MFA pretrained dictionary search paths for *mfa_name*."""
    return [
        os.path.expanduser(
            f"~/Documents/MFA/pretrained_models/dictionary/{mfa_name}.dict"),
        os.path.expanduser(
            f"~/.local/share/montreal-forced-aligner/pretrained_models/dictionary/{mfa_name}.dict"),
    ]



ALL_STEPS = ["msg", "wav", "acm", "mfa", "lip", "dat"]

# ─── LIP constants ────────────────────────────────────────────────────────────

LIP_VERSION     = 0x00000002
LIP_UNKNOWN     = 0x00005800
LIP_SAMPLE_RATE = 22050
LIP_MULTIPLIER  = 2   # offset = seconds × 2 × 22050


# ─── MSG parser ───────────────────────────────────────────────────────────────

MSG_LINE_RE = re.compile(r"^\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\{(.*)\}\s*$")

def parse_msg(path: str, encoding: str = "cp1252") -> list:
    """Return [(line_num, audio_tag, text), …] for lines with a non-empty audio tag."""
    results = []
    with open(path, encoding=encoding) as fh:
        for line in fh:
            m = MSG_LINE_RE.match(line)
            if not m:
                continue
            try:
                line_num = int(m.group(1).strip())
            except ValueError:
                line_num = -1
            tag, text = m.group(2).strip(), m.group(3).strip()
            if tag:
                results.append((line_num, tag, text))
    return results

# ─── Audio helpers ────────────────────────────────────────────────────────────

# Supported audio input extensions
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}

def ffprobe_duration(path: str) -> float:
    """Use ffprobe to get duration in seconds. Works for any container."""
    r = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed on '{path}': {r.stderr.strip()}")
    data = json.loads(r.stdout)
    dur = data.get("format", {}).get("duration")
    if dur is None:
        raise RuntimeError(f"ffprobe returned no duration for '{path}'")
    return float(dur)

def wav_is_standard(path: str) -> bool:
    """Return True if WAV is already 22050 Hz, mono, 16-bit PCM."""
    import wave
    try:
        with wave.open(path, "rb") as w:
            return (w.getframerate() == 22050 and
                    w.getnchannels() == 1 and
                    w.getsampwidth() == 2)
    except Exception:
        return False

# ─── TextGrid parser ──────────────────────────────────────────────────────────

def parse_textgrid_phones(tg_path: str) -> list:
    with open(tg_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    phones_match = re.search(
        r'name\s*=\s*"phones?"(.*?)(?=(?:item\s*\[|\Z))',
        content, re.DOTALL | re.IGNORECASE)
    if not phones_match:
        raise ValueError(f"No 'phones' tier in {tg_path}")
    tier_text = phones_match.group(1)
    intervals = re.findall(
        r'xmin\s*=\s*([\d.]+).*?xmax\s*=\s*([\d.]+).*?text\s*=\s*"([^"]*)"',
        tier_text, re.DOTALL)
    return [(float(xmin), float(xmax), label) for xmin, xmax, label in intervals]

def parse_textgrid_words(tg_path: str) -> list:
    """Return [(xmin, xmax, word), …] from the words tier."""
    with open(tg_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    words_match = re.search(
        r'name\s*=\s*"words?"(.*?)(?=(?:item\s*\[|\Z))',
        content, re.DOTALL | re.IGNORECASE)
    if not words_match:
        raise ValueError(f"No 'words' tier in {tg_path}")
    tier_text = words_match.group(1)
    intervals = re.findall(
        r'xmin\s*=\s*([\d.]+).*?xmax\s*=\s*([\d.]+).*?text\s*=\s*"([^"]*)"',
        tier_text, re.DOTALL)
    return [(float(xmin), float(xmax), label) for xmin, xmax, label in intervals]

def find_spn_ranges(tg_path: str) -> list:
    """Return [(xmin, xmax), …] for every 'spn' interval in the phones tier."""
    return [(xmin, xmax)
            for xmin, xmax, label in parse_textgrid_phones(tg_path)
            if label.strip().lower() == "spn"]

def report_unknown_words(textgrid_dir: str) -> None:
    """
    Scan all TextGrids in textgrid_dir.
    For each word whose time range contains a 'spn' phone interval,
    write a report to unknown_words.txt in the same folder.
    """
    findings = []
    tg_files = sorted(f for f in os.listdir(textgrid_dir) if f.endswith(".TextGrid"))
    if not tg_files:
        return findings

    for tg_file in tg_files:
        stem    = os.path.splitext(tg_file)[0]
        tg_path = os.path.join(textgrid_dir, tg_file)
        try:
            words      = parse_textgrid_words(tg_path)
            spn_ranges = find_spn_ranges(tg_path)
        except Exception as e:
            print(f"  [warn] could not scan {tg_file}: {e}")
            continue

        for xmin, xmax, word in words:
            if not word.strip():
                continue
            for smin, smax in spn_ranges:
                if smin >= xmin and smax <= xmax + 0.001:
                    findings.append((stem, word, xmin, xmax))
                    break

    out_path = "unknown.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        if findings:
            n_files = len({s for s, *_ in findings})
            f.write("Unknown words (MFA assigned 'spn')\n")
            f.write(f"{len(findings)} occurrence(s) in {n_files} file(s).\n")
            f.write("Add pronunciations for these words to your custom dictionary\n")
            f.write("(dictionaries/custom.<mfa_name>.dict) and re-run --steps mfa lip dat\n")
            current_stem = None
            for stem, word, xmin, xmax in findings:
                if stem != current_stem:
                    f.write(f"\n{stem}.txt\n")
                    current_stem = stem
                f.write(f"  {word:<20}  {xmin:.2f}s – {xmax:.2f}s\n")
            print(f"  {len(findings)} unknown word(s) found — see '{out_path}'")
        else:
            f.write("No unknown words — all words recognised by MFA.\n")
            print("  No unknown words — all words recognised by MFA.")

    return findings

def build_events_from_textgrid(tg_path: str, phoneme_to_code) -> list:
    """Build (timestamp, lip_code) events from a TextGrid file."""
    intervals = parse_textgrid_phones(tg_path)
    events = []
    for xmin, _xmax, label in intervals:
        code = phoneme_to_code(label)
        events.append((xmin, code))
    deduped = []
    for xmin, code in events:
        if not deduped or deduped[-1][1] != code:
            deduped.append((xmin, code))
    return deduped if deduped else [(0.0, 0x00)]

# ─── MFA ─────────────────────────────────────────────────────────────────────

def run_mfa(corpus_dir: str, output_dir: str, mfa_env: str,
            dict_path: str,
            mfa_name: str) -> bool:
    """Run MFA alignment via 'conda run'. Returns True on success."""
    cmd = [
        "conda", "run", "-n", mfa_env, "--no-capture-output",
        "mfa", "align", "--clean", "--single_speaker",
        "--output_format", "long_textgrid",
        corpus_dir,
        dict_path,
        mfa_name,
        output_dir,
    ]
    n = len([f for f in os.listdir(corpus_dir) if f.endswith(".wav")])
    print(f"\n  Running MFA on {n} file(s)…  (this may take a minute)\n")
    r = subprocess.run(cmd, text=True)
    return r.returncode == 0

# ─── snd2acm ─────────────────────────────────────────────────────────────────

DEFAULT_MFA_DICT_PATHS: list[str] = []  # populated at runtime via resolve_mfa_dict_paths()

def find_mfa_dict(mfa_name: str) -> str | None:
    for path in resolve_mfa_dict_paths(mfa_name):
        if os.path.isfile(path):
            return path
    return None

def merge_dictionaries(main_dict: str, custom_dict: str, out_path: str) -> None:
    """Append custom_dict entries to a copy of main_dict, written to out_path."""
    with open(main_dict, encoding="utf-8") as f:
        base = f.read()
    with open(custom_dict, encoding="utf-8") as f:
        custom = f.read().strip()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(base)
        if not base.endswith("\n"):
            f.write("\n")
        f.write(custom)
        f.write("\n")

def resolve_path(rel_path: str | None) -> str | None:
    """Resolve a config["paths"] entry against config["project_root"].

    Falls back to "./" if project_root isn't set, so existing vock.cfg
    files without it keep working unchanged.
    """
    if rel_path is None:
        return None
    root = config.get("project_root", "./")
    return os.path.normpath(os.path.join(root, rel_path))

def find_snd2acm(hint: str = None) -> str | None:
    candidates = []
    if hint:
        candidates.append(hint)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates += [
        "snd2acm",
        "snd2acm.exe",
        os.path.join(script_dir, "snd2acm.exe"),
        os.path.join(os.getcwd(), "snd2acm.exe"),
    ]
    for c in candidates:
        if shutil.which(c) or os.path.isfile(c):
            return c
    return None

def wav_to_acm(snd2acm_bin: str, wav_path: str, acm_path: str) -> None:
    cmd = [snd2acm_bin, "-16", wav_path, acm_path, "-q0"]
    if os.name != "nt" and snd2acm_bin.lower().endswith(".exe"):
        cmd.insert(0, "wine")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"snd2acm failed:\n{r.stderr.strip()}")
    if not os.path.isfile(acm_path) or os.path.getsize(acm_path) == 0:
        raise RuntimeError(f"snd2acm produced no output for '{wav_path}'")

# ─── LIP writer ──────────────────────────────────────────────────────────────

def write_lip(out_path: str, stem: str, duration: float, events: list) -> None:
    """Write a Fallout 2 .LIP binary file."""
    num_phonemes = len(events)
    num_markers  = num_phonemes + 1
    file_length  = round(LIP_MULTIPLIER * LIP_SAMPLE_RATE * duration)
    acm_field    = stem.lower().encode("ascii")[:8].ljust(8, b"\x00")

    with open(out_path, "wb") as f:
        f.write(struct.pack(">I", LIP_VERSION))
        f.write(struct.pack(">I", LIP_UNKNOWN))
        f.write(struct.pack(">I", 0))
        f.write(struct.pack(">I", 0))
        f.write(struct.pack(">I", file_length))
        f.write(struct.pack(">I", num_phonemes))
        f.write(struct.pack(">I", 0))
        f.write(struct.pack(">I", num_markers))
        f.write(acm_field)
        f.write(b"VOC\x00")
        # Phoneme code bytes
        for _ts, code in events:
            f.write(struct.pack("B", code))
        # Marker table: (type DWORD, offset DWORD) per event + end marker
        for idx, (ts, _code) in enumerate(events):
            if idx == 0:
                f.write(struct.pack(">I", 1))
                f.write(struct.pack(">I", 0))
            else:
                offset = round(LIP_MULTIPLIER * LIP_SAMPLE_RATE * ts)
                f.write(struct.pack(">I", 0))
                f.write(struct.pack(">I", offset))
        f.write(struct.pack(">I", 1))
        f.write(struct.pack(">I", file_length))

# ─── DAT2 packer ─────────────────────────────────────────────────────────────
#
# Fallout 2 DAT2 layout (little-endian):
#   [Data Block]   raw file bytes concatenated from offset 0
#   [Directory Tree]
#     DWORD  num_files
#     per file:
#       DWORD  filename_len
#       BYTES  filename (ASCII, backslash separators, lowercase)
#       BYTE   is_compressed  (0 = uncompressed)
#       DWORD  real_size
#       DWORD  packed_size
#       DWORD  offset_in_data_block
#   [Footer]
#     DWORD  tree_size   (bytes of Directory Tree)
#     DWORD  file_size   (total DAT bytes)
#
# Reference: https://fodev.net/files/fo2/dat.html

def _npc_folder(stem: str) -> str:
    """Derive the NPC folder from a stem like mor1 → mor."""
    return re.sub(r"\d+$", "", stem).lower()

def collect_dat_entries(msg_paths, acm_dir, lip_dir, txt_dir,
                        include_acm=True, only_stems=None,
                        include_msg=True, discover_from="lip",
                        int_dir=None):
    """
    Build [(dat_path, local_path), …] pairs with backslash separators.

    only_stems   : if given (set of lowercase stems), restrict output to those stems.
    include_msg  : whether to include MSG files (set False for the float DAT).
    discover_from: "lip" — find stems via lip/ dir (default, for talking-head DAT).
                   "acm" — find stems via acm/ dir (for float DAT, which has no LIP files).
    """
    entries = []

    # MSG files → text\english\dialog\
    if include_msg:
        for msg_path in msg_paths:
            if os.path.isfile(msg_path):
                msg_name = os.path.basename(msg_path).lower()
                entries.append((f"text\\english\\dialog\\{msg_name}", msg_path))

    # Discover stems from the requested source directory
    stem_files: dict[str, str] = {}   # stem → path of the discovery file (lip or acm)
    if discover_from == "lip" and os.path.isdir(lip_dir):
        for f in os.listdir(lip_dir):
            if f.lower().endswith(".lip"):
                stem = os.path.splitext(f)[0].lower()
                stem_files[stem] = os.path.join(lip_dir, f)
    elif discover_from == "acm" and os.path.isdir(acm_dir):
        for f in os.listdir(acm_dir):
            if f.lower().endswith(".acm"):
                stem = os.path.splitext(f)[0].lower()
                stem_files[stem] = os.path.join(acm_dir, f)

    # Apply stem whitelist
    if only_stems is not None:
        normalised = {s.lower() for s in only_stems}
        stem_files = {s: p for s, p in stem_files.items() if s in normalised}

    for stem in sorted(stem_files):
        folder = _npc_folder(stem)
        base   = f"sound\\speech\\{folder}"
        # LIP file — present for talking-head stems and floats (included as a safety net)
        lip_path = os.path.join(lip_dir, stem + ".lip")
        if os.path.isfile(lip_path):
            entries.append((f"{base}\\{stem}.lip", lip_path))
        # ACM file
        if include_acm:
            acm_path = os.path.join(acm_dir, stem + ".acm")
            if os.path.isfile(acm_path):
                entries.append((f"{base}\\{stem}.acm", acm_path))
        # TXT file
        txt_path = os.path.join(txt_dir, stem + ".txt")
        if os.path.isfile(txt_path):
            entries.append((f"{base}\\{stem}.txt", txt_path))

    # INT files → scripts\
    if int_dir and os.path.isdir(int_dir):
        for f in sorted(os.listdir(int_dir)):
            if f.lower().endswith(".int"):
                entries.append((f"scripts\\{f.lower()}", os.path.join(int_dir, f)))

    return entries

def write_dat2(out_path: str, entries: list) -> None:
    """Write a Fallout 2 DAT2 archive (pure Python, uncompressed)."""
    # Normalise paths to lowercase ASCII with backslashes, sort alphabetically
    entries = [(d.lower(), l) for d, l in entries]
    entries.sort(key=lambda x: x[0])

    # Read all file data upfront and track offsets
    file_data, offsets = [], []
    cursor = 0
    for _dat_path, local_path in entries:
        raw = open(local_path, "rb").read()
        file_data.append(raw)
        offsets.append(cursor)
        cursor += len(raw)

    # Build the directory tree
    tree = bytearray()
    tree += struct.pack("<I", len(entries))
    for i, (dat_path, _local) in enumerate(entries):
        raw      = file_data[i]
        fn_bytes = dat_path.encode("ascii")
        tree += struct.pack("<I", len(fn_bytes))
        tree += fn_bytes
        tree += struct.pack("<B", 0)            # is_compressed = 0
        tree += struct.pack("<I", len(raw))     # real_size
        tree += struct.pack("<I", len(raw))     # packed_size  (= real since uncompressed)
        tree += struct.pack("<I", offsets[i])   # offset in data block

    tree_size = len(tree)
    file_size = cursor + tree_size + 8  # +8 for the two footer DWORDs

    with open(out_path, "wb") as f:
        for raw in file_data:
            f.write(raw)
        f.write(tree)
        f.write(struct.pack("<I", tree_size))
        f.write(struct.pack("<I", file_size))

# ─── Dependency fast-fail check ──────────────────────────────────────────────

def check_dependencies(run: set, snd2acm_hint: str, mfa_env: str) -> None:
    """Exit with a clear error message if required tools are missing."""
    errors = []

    # ffmpeg and ffprobe are required by the wav step (and lip for duration)
    needs_ffmpeg = bool(run & {"wav", "lip"})
    if needs_ffmpeg:
        if not shutil.which("ffmpeg"):
            errors.append(
                "  ffmpeg  not found on PATH.\n"
                "  Install:  sudo apt install ffmpeg -y")
        if not shutil.which("ffprobe"):
            errors.append(
                "  ffprobe not found on PATH.\n"
                "  Install:  sudo apt install ffmpeg -y  (ffprobe is bundled with ffmpeg)")

    # snd2acm for the acm step
    if "acm" in run:
        if not find_snd2acm(snd2acm_hint):
            errors.append(
                "  snd2acm.exe  not found.\n"
                "  Download from https://fodev.net/files/mirrors/teamx-utils/snd2acm.rar\n"
                "  and place snd2acm.exe next to vock.py.  On Linux also install Wine:\n"
                "    sudo apt install wine -y")

    # conda for the mfa step
    if "mfa" in run:
        if not shutil.which("conda"):
            errors.append(
                "  conda  not found on PATH.\n"
                "  Install Miniconda:\n"
                "    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh\n"
                "    bash Miniconda3-latest-Linux-x86_64.sh -b\n"
                "    ~/miniconda3/bin/conda init bash && exec bash")

    if errors:
        print("\n[DEPENDENCY ERROR] The following required tools are missing:\n")
        for e in errors:
            print(e)
        print()
        sys.exit(1)

# ─── Utilities ────────────────────────────────────────────────────────────────

def print_section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def _scan_msg_dir(path: str) -> list:
    """Return sorted list of .MSG file paths found in *path* (a directory)."""
    if not os.path.isdir(path):
        sys.exit(f"MSG directory not found: '{path}'\n"
                 "Create a 'msg/' folder and put your .MSG file(s) in it, "
                 "or update the 'msg' path in vock.cfg.")
    found = sorted(
        os.path.join(path, f)
        for f in os.listdir(path)
        if f.lower().endswith(".msg"))
    if not found:
        sys.exit(f"No .MSG files found in '{path}/'")
    return found


def main():
    parser = argparse.ArgumentParser(
        description="V.O.C.K. — Vocal Output Creation Kit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--language", default=config["language"],
        choices=list(LANGUAGE_CONFIG.keys()),
        help=f"MFA language / phoneme set (default from vock.cfg: {config['language']}). "
             f"Choices: {', '.join(LANGUAGE_CONFIG)}")
    parser.add_argument("--steps", nargs="+", metavar="STEP", choices=ALL_STEPS,
        help=f"Run ONLY these step(s). Available: {', '.join(ALL_STEPS)}")
    parser.add_argument("--skip",  nargs="+", metavar="STEP", choices=ALL_STEPS,
        help="Skip these step(s) from the full pipeline.")
    args = parser.parse_args()

    # ── Resolve all paths and settings from vock.cfg ──────────────────────────
    # Every paths entry is resolved against config["project_root"] (default "./"),
    # so pointing project_root at another project's folder retargets the whole
    # pipeline without touching anything else here.
    paths = config["paths"]
    msgdir      = resolve_path(paths["msg"])
    audiodir    = resolve_path(paths["audio"])
    txtdir      = resolve_path(paths["txt"])
    wavdir      = resolve_path(paths["wav"])
    acmdir      = resolve_path(paths["acm"])
    textgriddir = resolve_path(paths["textgrid"])
    lipdir      = resolve_path(paths["lip"])
    datfile          = resolve_path(paths["dat"])
    float_datfile    = resolve_path(paths.get("float_dat", "./dat/vock_floats.dat"))
    intdir           = resolve_path(paths.get("scripts", "./scripts"))
    snd2acm_cfg      = resolve_path(paths["snd2acm"])
    npc_filter_file  = resolve_path(paths.get("npc_filter"))    # optional key; None if absent
    settings    = config["settings"]
    mfa_env     = settings["mfa_env"]
    lufs        = settings["lufs"]
    no_norm     = settings["no_norm"]

    npc_prefixes = load_npc_prefixes(npc_filter_file)
    float_filter_file = resolve_path(paths.get("float_filter"))
    float_map         = load_float_ranges(float_filter_file)
    mfa_lock_file = resolve_path(paths.get("mfa_lock"))
    mfa_lock      = load_mfa_lock(mfa_lock_file)

    # ── Language & Dictionary Resolution ──────────────────────────────────────
    mfa_name        = LANGUAGE_CONFIG[args.language]
    phoneme_mod     = load_phoneme_module(mfa_name)
    phoneme_to_code = make_phoneme_converter(mfa_name, phoneme_mod)

    custom_dict_path = resolve_custom_dict(mfa_name, None)
    main_dict_path   = find_mfa_dict(mfa_name)

    # Prepare printable strings
    custom_dict_print = custom_dict_path if custom_dict_path and os.path.isfile(custom_dict_path) else "None"
    main_dict_print   = main_dict_path if main_dict_path else f"{mfa_name} (MFA built-in/downloaded)"

    print_section("Configuration")
    print(f"  Language       : {args.language}")
    print(f"  Acoustic Model : {mfa_name}")
    print(f"  Dictionary     : {main_dict_print}")
    print(f"  Custom Dict    : {custom_dict_print}")
    print(f"  Phoneme Map    : phonemes_{mfa_name}.py")
    if npc_prefixes:
        print(f"  NPC filter     : {', '.join(sorted(npc_prefixes))}")
    else:
        print(f"  NPC filter     : all")
    if float_map:
        float_summary = ", ".join(
            f"{p}({','.join(f'{lo}-{hi}' for lo, hi in ranges)})"
            for p, ranges in sorted(float_map.items())
        )
        print(f"  Floats         : {float_summary}")
    if mfa_lock:
        print(f"  MFA lock       : {', '.join(sorted(mfa_lock))}  (existing TextGrid kept as-is)")

    # Resolve which steps to run
    if args.steps:
        run = set(args.steps)
    else:
        run = set(ALL_STEPS)
        if args.skip:
            for s in args.skip:
                run.discard(s)

    # Fast-fail dependency check
    check_dependencies(run, snd2acm_cfg, mfa_env)

    # ── Derive float_stems from MSG files (always, so mfa/lip steps see it even
    #    when the msg step is skipped) ─────────────────────────────────────────
    float_stems: set[str] = set()
    if float_map and os.path.isdir(msgdir):
        for _mp in sorted(
            os.path.join(msgdir, f)
            for f in os.listdir(msgdir)
            if f.lower().endswith(".msg")
        ):
            try:
                for ln, tag, _text in parse_msg(_mp, encoding=lang_enc(args.language)):
                    if is_float_line(tag, float_map):
                        float_stems.add(tag.lower())
            except Exception:
                pass

    # ── Pipeline state ────────────────────────────────────────────────────────
    msg_paths  = []
    txt_map    = {}      # stem → text (from msg step or loaded from txt/)
    wav_pairs  = []      # (stem, std_wav_path, txt_path) — 22050 Hz mono 16-bit

    acm_ok     = 0
    lip_ok     = 0
    lip_fail   = 0

    # ── STEP 1: MSG → TXT ────────────────────────────────────────────────────
    if "msg" in run:
        print_section("STEP 1 — Parse MSG → TXT")

        msg_paths = _scan_msg_dir(msgdir)

        all_entries = []
        for msg_path in msg_paths:
            print(f"  Reading {msg_path}")
            found = parse_msg(msg_path, encoding=lang_enc(args.language))
            if not found:
                print(f"  [warn] No tagged audio lines in '{msg_path}' — skipping.")
                continue
            all_entries.extend(found)
            print(f"  {len(found)} line(s) found.")

        if not all_entries:
            sys.exit("No audio-tagged lines found in any MSG file.")

        all_entries = filter_by_prefix(all_entries, npc_prefixes, key=lambda x: x[1])

        os.makedirs(txtdir, exist_ok=True)
        written = 0
        for _line_num, tag, text in all_entries:
            out = os.path.join(txtdir, f"{tag}.txt")
            # Only overwrite if content differs (preserve manual edits)
            if os.path.isfile(out):
                existing = open(out, encoding=lang_enc(args.language)).read().strip()
                if existing == text:
                    txt_map[tag] = text
                    continue
                # File was manually edited — keep the edit; don't overwrite
                txt_map[tag] = existing
                print(f"  [kept manual edit] {out}")
                continue
            with open(out, "w", encoding=lang_enc(args.language)) as fh:
                fh.write(text)
            txt_map[tag] = text
            written += 1

        print(f"  {written} new TXT file(s) written to '{txtdir}/'")
        print(f"  (Total {len(all_entries)} lines; existing files preserved if manually edited)")

    else:
        print_section("STEP 1 — Parse MSG → TXT  [skipped]")
        # Resolve msg_paths for the DAT step (best-effort; missing dir is not fatal here)
        if os.path.isdir(msgdir):
            msg_paths = _scan_msg_dir(msgdir)
        # Load txt_map from existing TXT files (respecting manual edits)
        if os.path.isdir(txtdir):
            for f in sorted(os.listdir(txtdir)):
                if f.endswith(".txt"):
                    stem = os.path.splitext(f)[0]
                    txt_map[stem] = open(
                        os.path.join(txtdir, f), encoding=lang_enc(args.language)).read().strip()

    # ── STEP 2: audio/ → wav/ (Universal Audio step) ─────────────────────────
    if "wav" in run:
        print_section("STEP 2 — Convert audio/ → wav/  (22050 Hz mono 16-bit)")
        os.makedirs(wavdir, exist_ok=True)

        # Scan audio/ for all supported formats
        audio_files_by_stem: dict[str, list[str]] = {}
        if os.path.isdir(audiodir):
            for f in sorted(os.listdir(audiodir)):
                ext = os.path.splitext(f)[1].lower()
                if ext in AUDIO_EXTS:
                    stem = os.path.splitext(f)[0]
                    audio_files_by_stem.setdefault(stem, []).append(f)
        else:
            print(f"  [warn] Audio folder '{audiodir}/' not found.")

        # Higher-priority format wins (wav > everything else) when a stem has
        # more than one source file -- e.g. a leftover take in another format
        # that never got cleaned up after a re-record. That's silent data loss
        # waiting to happen if nobody notices, so flag it every time it fires.
        audio_map: dict[str, str] = {}
        for stem, files in sorted(audio_files_by_stem.items()):
            if len(files) > 1:
                files_sorted = sorted(files, key=lambda f: (os.path.splitext(f)[1].lower() != ".wav", f))
                chosen, ignored = files_sorted[0], files_sorted[1:]
                print(f"  [warn] {stem}: {len(files)} audio source files found "
                      f"({', '.join(files)}) — using {chosen}, ignoring "
                      f"{', '.join(ignored)}. Delete the one(s) you don't want "
                      f"so this can't silently pick the wrong take later.")
                audio_map[stem] = os.path.join(audiodir, chosen)
            else:
                audio_map[stem] = os.path.join(audiodir, files[0])

        if not audio_map:
            sys.exit(f"No audio files found in '{audiodir}/'")

        enc_ok = 0
        skipped = 0
        for stem in filter_by_prefix(sorted(audio_map), npc_prefixes, key=lambda x: x):
            src_path = audio_map[stem]
            # Validate: must have a matching TXT
            txt_path = os.path.join(txtdir, stem + ".txt")
            if not os.path.isfile(txt_path):
                print(f"  [skip] {stem}: no matching .txt in '{txtdir}/' "
                      f"(run the 'msg' step first, or the tag is not in the MSG file)")
                skipped += 1
                continue

            out_wav = os.path.join(wavdir, stem + ".wav")
            try:
                ext = os.path.splitext(src_path)[1].lower()
                # Fast path: WAV already in correct format and norm disabled
                if no_norm and ext == ".wav" and wav_is_standard(src_path):
                    shutil.copy2(src_path, out_wav)
                    print(f"  copied   {out_wav}  (already 22050 Hz mono 16-bit)")
                else:
                    cmd = ["ffmpeg", "-y", "-i", src_path]
                    if not no_norm:
                        cmd.extend(["-af", f"loudnorm=I={lufs}:LRA=11:TP=-1.5"])
                    cmd.extend(["-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", out_wav])
                    r = subprocess.run(cmd, capture_output=True, text=True)
                    if r.returncode != 0:
                        raise RuntimeError(r.stderr.strip())
                    action = "enc+norm" if not no_norm else "encoded"
                    print(f"  {action.ljust(8)} {out_wav}")

                wav_pairs.append((stem, out_wav, txt_path))
                enc_ok += 1
            except RuntimeError as e:
                print(f"  [error] {stem}: ffmpeg failed: {e}")

        print(f"\n  {enc_ok} file(s) ready in '{wavdir}/'  "
              f"({skipped} skipped — no matching TXT)")

    else:
        print_section("STEP 2 — Convert audio/ → wav/  [skipped]")
        # Populate wav_pairs from existing standardised WAVs
        if os.path.isdir(wavdir):
            for f in sorted(os.listdir(wavdir)):
                if f.lower().endswith(".wav"):
                    stem     = os.path.splitext(f)[0]
                    txt_path = os.path.join(txtdir, stem + ".txt")
                    if os.path.isfile(txt_path) and \
                            filter_by_prefix([(stem,)], npc_prefixes, key=lambda x: x[0]):
                        wav_pairs.append((stem, os.path.join(wavdir, f), txt_path))

    # ── STEP 3: wav/ → ACM ───────────────────────────────────────────────────
    if "acm" in run:
        print_section("STEP 3 — Convert wav/ → acm/")
        if not wav_pairs:
            print("  No standardised WAV files found — run the 'wav' step first.")
        else:
            snd2acm_bin = find_snd2acm(snd2acm_cfg)
            if not snd2acm_bin:
                print("  snd2acm.exe not found — skipping ACM generation.")
                print("  Place snd2acm.exe next to vock.py and re-run.")
            else:
                os.makedirs(acmdir, exist_ok=True)
                for stem, wav_path, _txt in wav_pairs:
                    acm_path = os.path.join(acmdir, stem + ".acm")
                    try:
                        wav_to_acm(snd2acm_bin, wav_path, acm_path)
                        size_kb = os.path.getsize(acm_path) / 1024
                        print(f"  wrote  {acm_path}  ({size_kb:.1f} KB)")
                        acm_ok += 1
                    except RuntimeError as e:
                        print(f"  [error] {stem}: {e}")
                print(f"\n  {acm_ok}/{len(wav_pairs)} ACM file(s) written.")
    else:
        print_section("STEP 3 — Convert wav/ → acm/  [skipped]")

    # ── STEP 4: MFA alignment ─────────────────────────────────────────────────
    # All lines get MFA alignment and LIP files — floats included so that
    # vock_floats.dat carries a LIP as a safety net in case a line was
    # mis-classified as a float.
    head_wav_pairs  = wav_pairs
    float_wav_pairs = [(s, w, t) for s, w, t in wav_pairs
                       if s.lower() in float_stems]

    if "mfa" in run:
        print_section("STEP 4 — MFA forced alignment → TextGrid")
        if float_wav_pairs:
            print(f"  ({len(float_wav_pairs)} float line(s) included — TextGrid + LIP will be generated)")
        if not head_wav_pairs:
            print("  No WAV files available — run the 'wav' step first.")
        else:
            import tempfile
            os.makedirs(textgriddir, exist_ok=True)

            # Resolve dictionary — merge custom dict once, reuse across all groups
            dict_arg   = mfa_name   # MFA built-in name as fallback
            _merge_tmp = None       # holds TemporaryDirectory when we merge

            if custom_dict_path and os.path.isfile(custom_dict_path):
                if main_dict_path:
                    _merge_tmp = tempfile.TemporaryDirectory(prefix="vock_dict_")
                    merged = os.path.join(_merge_tmp.name, "merged.dict")
                    merge_dictionaries(main_dict_path, custom_dict_path, merged)
                    dict_arg = merged
                    print(f"  Using custom dictionary: {custom_dict_path}")
                else:
                    print(f"  [warn] Custom dictionary found ({custom_dict_path}) but the "
                          f"main MFA dictionary for '{mfa_name}' could not be located "
                          f"— passing '{mfa_name}' to MFA directly.")

            # Locked stems keep their existing TextGrid untouched — excluded from
            # the MFA corpus entirely so they can't skew the pooled per-speaker
            # normalization for the rest of their group either.
            alignable_pairs = []
            for item in head_wav_pairs:
                stem = item[0].lower()
                if stem in mfa_lock:
                    tg_path = os.path.join(textgriddir, item[0] + ".TextGrid")
                    if os.path.isfile(tg_path):
                        print(f"  [locked] {item[0]} — keeping existing TextGrid, skipped from MFA")
                    else:
                        print(f"  [warn] {item[0]} is in mfa_lock but has no TextGrid on disk — "
                              f"'lip' will fail for it until you unlock or supply one")
                else:
                    alignable_pairs.append(item)

            # Group head_wav_pairs by NPC tag prefix (e.g. MOR, ARTH, ZAIUS …)
            groups: dict[str, list] = {}
            for item in alignable_pairs:
                prefix = re.sub(r"\d+$", "", item[0].lower())
                groups.setdefault(prefix, []).append(item)

            total_tg      = 0
            failed_groups: list[str] = []

            for prefix, pairs in sorted(groups.items()):
                print(f"\n  [{prefix}]  {len(pairs)} file(s) …")
                with tempfile.TemporaryDirectory(prefix=f"vock_{prefix}_") as corpus_dir:
                    for stem, wav_path, txt_path in pairs:
                        shutil.copy2(wav_path, os.path.join(corpus_dir, stem + ".wav"))
                        text = open(txt_path, encoding=lang_enc(args.language)).read()
                        open(os.path.join(corpus_dir, stem + ".txt"), "w",
                             encoding="utf-8").write(text)

                    mfa_tmp_out = os.path.join(corpus_dir, "aligned")
                    os.makedirs(mfa_tmp_out)

                    ok = run_mfa(corpus_dir, mfa_tmp_out, mfa_env, dict_arg, mfa_name)

                    if ok:
                        group_tg = 0
                        for f in os.listdir(mfa_tmp_out):
                            if f.endswith(".TextGrid"):
                                shutil.copyfile(
                                    os.path.join(mfa_tmp_out, f),
                                    os.path.join(textgriddir, f))
                                total_tg += 1
                                group_tg += 1
                        print(f"    {group_tg}/{len(pairs)} TextGrid(s) exported")
                    else:
                        failed_groups.append(prefix)
                        print(f"    [warn] MFA failed for [{prefix}] — "
                              "text approximation will be used for these files.")

            if _merge_tmp:
                _merge_tmp.cleanup()

            print(f"\n  {total_tg} TextGrid(s) saved to '{textgriddir}/'")
            if failed_groups:
                print(f"  Failed groups: {', '.join(failed_groups)}")
            report_unknown_words(textgriddir)
    else:
        print_section("STEP 4 — MFA forced alignment  [skipped]")

    # ── STEP 5: LIP generation ────────────────────────────────────────────────
    if "lip" in run:
        print_section("STEP 5 — Generate LIP files")
        if not head_wav_pairs:
            print("  No WAV files available for duration — run the 'wav' step first.")
        else:
            os.makedirs(lipdir, exist_ok=True)
            if float_wav_pairs:
                print(f"  ({len(float_wav_pairs)} float line(s) included — LIP files packed into vock_floats.dat)")
            for stem, wav_path, _txt_path in head_wav_pairs:
                lip_path = os.path.join(lipdir, stem + ".lip")
                tg_path  = os.path.join(textgriddir, stem + ".TextGrid")

                try:
                    duration = ffprobe_duration(wav_path)
                except Exception as e:
                    print(f"  [error] {stem}: could not read duration: {e}")
                    lip_fail += 1
                    continue

                if os.path.isfile(tg_path):
                    try:
                        events = build_events_from_textgrid(tg_path, phoneme_to_code)
                        write_lip(lip_path, stem, duration, events)
                        print(f"  wrote  {lip_path}  "
                              f"({duration:.3f}s, {len(events)} events, MFA)")
                        lip_ok += 1
                    except Exception as e:
                        print(f"  [error] {stem}: TextGrid error ({e})")
                        lip_fail += 1
                else:
                    print(f"  [error] {stem}: Missing TextGrid (MFA failed or was skipped)")
                    lip_fail += 1

            print(f"\n  {lip_ok} MFA successfully mapped  +  {lip_fail} failed"
                  + (f"  ({len(wav_pairs) - len(head_wav_pairs)} floats skipped)"
                     if float_stems else ""))
    else:
        print_section("STEP 5 — Generate LIP files  [skipped]")

    # ── STEP 6: Build DAT ────────────────────────────────────────────────────
    if "dat" in run:
        include_acm = ("acm" not in (args.skip or []))
        os.makedirs(os.path.dirname(datfile) or ".", exist_ok=True)

        # ── 6a: Talking-head DAT ──────────────────────────────────────────────
        print_section("STEP 6a — Build vock.dat  (talking heads)")
        try:
            dat_entries = collect_dat_entries(
                msg_paths    = msg_paths,
                acm_dir      = acmdir,
                lip_dir      = lipdir,
                txt_dir      = txtdir,
                include_acm  = include_acm,
                include_msg  = True,
                discover_from = "lip",
                int_dir      = intdir,
            )
            if not dat_entries:
                print("  No files to pack — skipping.")
            else:
                write_dat2(datfile, dat_entries)
                total_kb = os.path.getsize(datfile) / 1024
                print(f"  wrote  {datfile}  "
                      f"({len(dat_entries)} file(s), {total_kb:.1f} KB)")
        except Exception as e:
            print(f"  [error] DAT creation failed: {e}")

        # ── 6b: Float DAT (only when float lines exist) ───────────────────────
        if float_stems:
            print_section("STEP 6b — Build vock_floats.dat  (floats)")
            os.makedirs(os.path.dirname(float_datfile) or ".", exist_ok=True)
            try:
                float_entries = collect_dat_entries(
                    msg_paths     = [],
                    acm_dir       = acmdir,
                    lip_dir       = lipdir,
                    txt_dir       = txtdir,
                    include_acm   = include_acm,
                    only_stems    = float_stems,
                    include_msg   = False,
                    discover_from = "acm",
                    int_dir       = None,      # INT scripts go in vock.dat only
                )
                if not float_entries:
                    print("  No float ACM files found — run the 'acm' step first.")
                else:
                    write_dat2(float_datfile, float_entries)
                    total_kb = os.path.getsize(float_datfile) / 1024
                    print(f"  wrote  {float_datfile}  "
                          f"({len(float_entries)} file(s), {total_kb:.1f} KB)")
            except Exception as e:
                print(f"  [error] Float DAT creation failed: {e}")
    else:
        print_section("STEP 6 — Build DAT  [skipped]")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print("  DONE")
    print(f"{'═'*60}")
    steps_run = [s for s in ALL_STEPS if s in run]
    print(f"  Steps run  : {', '.join(steps_run) or '(none)'}")
    print(f"  TXT files  : {len(txt_map)} known")
    print(f"  WAV files  : {len(wav_pairs)}")
    print(f"  ACM files  : {acm_ok if 'acm' in run else 'skipped'}")
    if "lip" in run:
        float_note = f"  ({len(float_wav_pairs)} float LIP(s) included in vock_floats.dat)" if float_wav_pairs else ""
        print(f"  LIP files  : {lip_ok} MFA generated  ({lip_fail} failed){float_note}")
    else:
        print("  LIP files  : skipped")
    if "dat" in run:
        print(f"  DAT file   : {datfile}")
        if float_stems:
            print(f"  Float DAT  : {float_datfile}")
    else:
        print(f"  DAT file   : skipped")
    print()


if __name__ == "__main__":
    main()
