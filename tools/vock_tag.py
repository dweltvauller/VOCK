#!/usr/bin/env python3
"""
vock_tag.py  --  add sequential audio tags to NPC msg files.

Usage:
    python3 tools/vock_tag.py <prefix>
    python3 tools/vock_tag.py brige

Reads the msg file and its SSL script(s), assigns sequential tags to NPC
talking-head and float lines, and writes the tagged result to a separate
tag/ output folder (preserving the original encoding and line endings),
then prints a report. The source msg file under msg/ is never modified.

If a previously-tagged copy already exists in tag/, it is used as the
read source instead of the original in msg/, so re-running the tool on
the same prefix builds on earlier tagging rather than starting over.

Only lines with an empty tag field {} are modified.  Lines that already
carry a tag are left as-is.

Configuration comes from vock.cfg (see the Custom Configuration section of
README.md):
  - PATHS["msg"]         -- source MSG folder (resolved against project_root)
  - PATHS["tag"]         -- output folder for tagged MSG copies (resolved
                            against project_root); created if missing
  - PATHS["characters"]  -- characters.py-style table of
                            (msg_stem, name, prefix, ssl_stems, head)
  - PATHS["scripts_src"] -- this project's own SSL source (flat, only for
                            characters whose dialog was modified for this
                            mod). Falls back to the base RP scripts in
                            PATHS["rpu_scripts_src"] (searched recursively)
                            for everything else, mirroring how
                            msg_localize.py falls back to the RPU repo for
                            translations.
  - PATHS["rpu_scripts_src"] -- base RP SSL source folder (resolved against
                            this vock.cfg's own folder, not project_root --
                            the RPU repo is a sibling of vock/ itself).
"""

import configparser
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent   # vock/tools/
_VOCK_DIR   = _SCRIPT_DIR.parent                # vock/

_ini_parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
if not _ini_parser.read(_VOCK_DIR / "vock.cfg", encoding="utf-8"):
    sys.exit(f"[ERROR] Could not read config file: {_VOCK_DIR / 'vock.cfg'}")

_config = {
    "project_root": _ini_parser.get("general", "project_root", fallback="./"),
    "paths":        dict(_ini_parser["paths"]),
}
PATHS = _config["paths"]

# Every paths entry is resolved against config["project_root"] (default "./"),
# mirroring vock.py's resolve_path() and msg_localize.py -- so pointing
# project_root at another project's folder retargets this tool too, instead
# of always reading from vock/.
_PROJECT_ROOT = (_VOCK_DIR / _config.get("project_root", "./")).resolve()

MSG_DIR             = _PROJECT_ROOT / PATHS["msg"]
TAG_DIR             = _PROJECT_ROOT / PATHS["tag"]
CHARACTERS_PATH     = _PROJECT_ROOT / PATHS["characters"]
PROJECT_SCRIPTS_SRC = _PROJECT_ROOT / PATHS["scripts_src"]
# rpu_scripts_src is resolved against _VOCK_DIR, not project_root -- see vock.cfg.
RPU_SCRIPTS_SRC     = (_VOCK_DIR / PATHS["rpu_scripts_src"]).resolve()

MSG_ENCODING = "cp1252"   # Fallout dialog files use Windows-1252


# ---------------------------------------------------------------------------
#  Character table + SSL lookup
# ---------------------------------------------------------------------------

def _load_characters(path):
    """Load the CHARACTERS list out of a characters.py-style data file."""
    if not path.exists():
        sys.exit(f"[ERROR] characters file not found: {path}")
    spec = importlib.util.spec_from_file_location("vock_characters", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CHARACTERS


CHARACTERS = _load_characters(CHARACTERS_PATH)

_rpu_ssl_index = None


def _rpu_ssl_path(ssl_stem):
    """Recursively look up <ssl_stem>.ssl under RPU_SCRIPTS_SRC (index cached)."""
    global _rpu_ssl_index
    if _rpu_ssl_index is None:
        _rpu_ssl_index = {}
        if RPU_SCRIPTS_SRC.exists():
            for p in RPU_SCRIPTS_SRC.rglob("*.ssl"):
                _rpu_ssl_index.setdefault(p.stem.lower(), p)
    return _rpu_ssl_index.get(ssl_stem.lower())


def find_ssl_path(ssl_stem):
    """
    Locate an SSL source file for ssl_stem.

    Checks the project's own scripts_src first (mod-specific edits, usually
    just a handful of files), then falls back to the base RP scripts under
    rpu/scripts_src (searched recursively across area subfolders).
    """
    project_path = PROJECT_SCRIPTS_SRC / (ssl_stem + ".ssl")
    if project_path.exists():
        return project_path
    return _rpu_ssl_path(ssl_stem)


def find_entry(prefix):
    for entry in CHARACTERS:
        msg_stem, name, pfx, ssl_stems, head = entry
        if pfx == prefix:
            return entry
    return None


# ---------------------------------------------------------------------------
#  MSG file I/O
# ---------------------------------------------------------------------------

def detect_eol(raw):
    """
    Detect file-level line endings by looking at the newline that follows a
    closing brace (i.e. between msg entries), not at newlines embedded inside
    text fields which may differ.  Falls back to any CRLF if no inter-entry
    newline is found.
    """
    m = re.search(rb'\}(\r?\n)', raw)
    if m:
        return b"\r\n" if m.group(1) == b"\r\n" else b"\n"
    return b"\r\n" if b"\r\n" in raw else b"\n"


def read_msg(path):
    """
    Read a msg file.  Returns:
        text  -- str with LF-only line endings (for uniform processing)
        eol   -- original line-ending bytes (b"\r\n" or b"\n")
    """
    raw = path.read_bytes()
    eol = detect_eol(raw)
    text = raw.decode(MSG_ENCODING, errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, eol


def write_msg(path, text, eol):
    """Write text back to path using the original encoding and line endings."""
    # Strip any stray \r before applying the target EOL
    text = text.replace("\r", "")
    if eol == b"\r\n":
        text = text.replace("\n", "\r\n")
    raw_out = text.encode(MSG_ENCODING, errors="replace")
    # Sanity-check: count CRLF vs LF-only in output
    crlf_count = raw_out.count(b"\r\n")
    lf_count   = raw_out.count(b"\n") - crlf_count
    print("  [write] EOL target=" + ("CRLF" if eol == b"\r\n" else "LF")
          + "  CRLF in output=" + str(crlf_count)
          + "  LF-only in output=" + str(lf_count), file=sys.stderr)
    path.write_bytes(raw_out)


def parse_msg(text):
    """Parse msg text (LF-normalised).  Returns {line_num: {"tag": str, "text": str}}."""
    lines = {}
    for m in re.finditer(r"\{(\d+)\}\{([^}]*)\}\{((?:[^{}]|\n)*)\}", text):
        num  = int(m.group(1))
        tag  = m.group(2).strip()
        body = m.group(3)
        lines[num] = {"tag": tag, "text": body}
    return lines


# ---------------------------------------------------------------------------
#  SSL parser helpers
# ---------------------------------------------------------------------------

def _resolve_expr(expr):
    """
    Turn an SSL expression into (set_of_line_nums, dynamic).
    dynamic=True means there may be additional lines not in the returned set.
    """
    expr = expr.strip()

    if re.fullmatch(r"\d+", expr):
        return {int(expr)}, False

    m = re.fullmatch(r"random\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", expr)
    if m:
        return set(range(int(m.group(1)), int(m.group(2)) + 1)), False

    m = re.fullmatch(r"(\d+)\s*\+\s*([A-Za-z_]\w*)", expr)
    if m:
        return {int(m.group(1))}, True

    return set(), True


def _find_var_max(ssl_text, var_name):
    """Heuristic upper bound for a simple counter variable."""
    v = re.escape(var_name)
    m = re.search(r"if\s*\(\s*" + v + r"\s*>\s*(\d+)\s*\)", ssl_text)
    if m:
        return int(m.group(1))
    m = re.search(r"if\s*\(\s*" + v + r"\s*>=\s*(\d+)\s*\)", ssl_text)
    if m:
        return int(m.group(1)) - 1
    m = re.search(r"if\s*\(\s*" + v + r"\s*==\s*(\d+)\s*\)", ssl_text)
    if m:
        return int(m.group(1)) - 1
    return None


def _extract_msg_str_refs(text, msg_id, ssl_text=""):
    """
    Pull all message_str(msg_id, EXPR) references from a snippet.
    Handles one level of nested parens (e.g. random(X,Y) inside message_str).
    """
    nums    = set()
    dynamic = False
    pattern = re.compile(
        r"message_str\s*\(\s*" + re.escape(str(msg_id))
        + r"\s*,\s*((?:[^()]+|\([^()]*\))+)\)"
    )
    for m in pattern.finditer(text):
        expr = m.group(1).strip()
        resolved, dyn = _resolve_expr(expr)
        if dyn and ssl_text:
            base_m = re.fullmatch(r"(\d+)\s*\+\s*([A-Za-z_]\w*)", expr)
            if base_m:
                base  = int(base_m.group(1))
                vname = base_m.group(2)
                vmax  = _find_var_max(ssl_text, vname)
                if vmax is not None:
                    resolved = set(range(base, base + vmax + 1))
                    dyn      = False
        nums    |= resolved
        dynamic  = dynamic or dyn
    return nums, dynamic


def find_msg_id(ssl_text, ssl_stem):
    """Find the primary dialog msg_id from start_gdialog or gsay_reply calls."""
    m = re.search(r"start_gdialog\s*\(\s*(\d+)", ssl_text)
    if m:
        return int(m.group(1))
    ids = re.findall(r"gsay_reply\s*\(\s*(\d+)", ssl_text)
    if ids:
        return int(Counter(ids).most_common(1)[0][0])
    return None


def parse_ssl(path, msg_id):
    """
    Classify every message reference belonging to msg_id.
    Returns dict with sets npc_head, npc_float, pc_head, pc_float, display
    and list dynamic of (ssl_lineno, description).
    """
    result = {
        "npc_head":  set(),
        "npc_float": set(),
        "pc_head":   set(),
        "pc_float":  set(),
        "display":   set(),
        "dynamic":   [],
    }

    text   = path.read_text(encoding="utf-8", errors="replace")
    sid_re = re.escape(str(msg_id))

    for lineno, line in enumerate(text.splitlines(), 1):
        s = line.strip()

        m = re.match(r"gsay_reply\s*\(\s*" + sid_re + r"\s*,\s*(.+?)\s*\)\s*;", s)
        if m:
            arg = m.group(1).strip()
            if re.fullmatch(r"\d+", arg):
                result["npc_head"].add(int(arg))
            else:
                refs, dyn = _extract_msg_str_refs(arg, msg_id, text)
                result["npc_head"] |= refs
                if dyn or not refs:
                    result["dynamic"].append((lineno, "gsay_reply expr: " + arg))
            continue

        m = re.match(
            r"giq_option\s*\([^,]+,\s*" + sid_re + r"\s*,\s*(.+?),\s*\w+\s*,\s*\d+\s*\)\s*;",
            s,
        )
        if m:
            arg = m.group(1).strip()
            if re.fullmatch(r"\d+", arg):
                result["pc_head"].add(int(arg))
            else:
                refs, dyn = _extract_msg_str_refs(arg, msg_id, text)
                result["pc_head"] |= refs
                if dyn or not refs:
                    result["dynamic"].append((lineno, "giq_option expr: " + arg))
            continue

        m = re.match(
            r"float_msg\s*\(\s*(self_obj|dude_obj)\s*,\s*(.+?)\s*,\s*[^,)]+\s*\)\s*;", s
        )
        if m:
            who  = m.group(1)
            body = m.group(2)
            refs, dyn = _extract_msg_str_refs(body, msg_id, text)
            if refs:
                bucket = "npc_float" if who == "self_obj" else "pc_float"
                result[bucket] |= refs
            if dyn:
                result["dynamic"].append((lineno, "float_msg(" + who + ") expr: " + body))
            continue

        m = re.match(r"display_msg\s*\((.+?)\)\s*;", s)
        if m:
            refs, dyn = _extract_msg_str_refs(m.group(1), msg_id, text)
            result["display"] |= refs
            if dyn:
                result["dynamic"].append((lineno, "display_msg expr: " + m.group(1)))
            continue

    return result


# ---------------------------------------------------------------------------
#  Tag assignment
# ---------------------------------------------------------------------------

def assign_tags(prefix, npc_head, npc_float):
    """
    Return {line_num: proposed_tag}.
    Order: gsay_reply lines first (sorted ascending), then float-only lines.
    """
    ordered = sorted(npc_head) + sorted(npc_float - npc_head)
    return {ln: prefix + str(i + 1) for i, ln in enumerate(ordered)}


# ---------------------------------------------------------------------------
#  Flatten multi-line text fields
# ---------------------------------------------------------------------------

def flatten_msg_text(text):
    """
    Collapse embedded newlines inside msg text fields into single spaces.

    {109}{mor4}{Bad times are coming
     and I'm going to be ready.}
    becomes
    {109}{mor4}{Bad times are coming and I'm going to be ready.}

    Returns (new_text, count_of_flattened_lines).
    """
    count = [0]

    def _flatten(m):
        num  = m.group(1)
        tag  = m.group(2)
        body = m.group(3)
        if "\n" in body:
            count[0] += 1
            body = re.sub(r"\n\s*", " ", body).strip()
        return "{" + num + "}{" + tag + "}{" + body + "}"

    new_text = re.sub(r"\{(\d+)\}\{([^}]*)\}\{((?:[^{}]|\n)*)\}", _flatten, text)
    return new_text, count[0]


# ---------------------------------------------------------------------------
#  Apply tags to raw msg text
# ---------------------------------------------------------------------------

def apply_tags(text, tags, msg_lines):
    """
    Replace {NUM}{}{...} with {NUM}{TAG}{...} for every line in tags that
    currently has an empty tag field.  Returns (new_text, written, skipped).
      written  -- {num: tag} for lines that were updated
      skipped  -- {num: existing_tag} for lines already carrying a tag
    """
    written = {}
    skipped = {}

    def replacer(m):
        num = int(m.group(1))
        if num not in tags:
            return m.group(0)          # not a line we want to tag
        existing = msg_lines.get(num, {}).get("tag", "")
        if existing:
            skipped[num] = existing    # already tagged -- leave alone
            return m.group(0)
        new_tag = tags[num]
        written[num] = new_tag
        return "{" + str(num) + "}{" + new_tag + "}{"

    new_text = re.sub(r"\{(\d+)\}\{\}\{", replacer, text)
    return new_text, written, skipped


# ---------------------------------------------------------------------------
#  Output helpers
# ---------------------------------------------------------------------------

def fmt_line(num, tag, text, proposed=""):
    display_tag = proposed if proposed else tag
    snippet = text.replace("\n", " ").strip()
    if len(snippet) > 72:
        snippet = snippet[:69] + "..."
    return "  {" + str(num) + "}{" + display_tag + "}{" + snippet + "}"


def section(title, entries):
    if not entries:
        return
    bar = "-" * max(0, 50 - len(title))
    print("\n-- " + title + " " + bar)
    for e in entries:
        print(e)


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def run(prefix):
    entry = find_entry(prefix)
    if entry is None:
        print("ERROR: prefix '" + prefix + "' not found in " + str(CHARACTERS_PATH), file=sys.stderr)
        sys.exit(1)

    msg_stem, name, _, ssl_stems, _ = entry
    msg_path = MSG_DIR / (msg_stem + ".msg")
    tag_path = TAG_DIR / (msg_stem + ".msg")

    if not msg_path.exists():
        print("ERROR: msg file not found: " + str(msg_path), file=sys.stderr)
        sys.exit(1)

    # Prefer a previously-tagged copy (if one exists) as the read source,
    # so re-runs build on earlier tagging instead of starting from scratch.
    # The original file under msg/ is never read back to after this point.
    read_path = tag_path if tag_path.exists() else msg_path
    msg_text, eol = read_msg(read_path)
    msg_lines      = parse_msg(msg_text)
    eol_name       = "CRLF" if eol == b"\r\n" else "LF"

    # Collect SSL references
    combined = {
        "npc_head":  set(),
        "npc_float": set(),
        "pc_head":   set(),
        "pc_float":  set(),
        "display":   set(),
        "dynamic":   [],
    }

    for ssl_stem in ssl_stems:
        ssl_path = find_ssl_path(ssl_stem)
        if ssl_path is None:
            print("WARNING: ssl not found (checked "
                  + str(PROJECT_SCRIPTS_SRC) + " and " + str(RPU_SCRIPTS_SRC)
                  + "): " + ssl_stem, file=sys.stderr)
            continue
        ssl_text = ssl_path.read_text(encoding="utf-8", errors="replace")
        msg_id   = find_msg_id(ssl_text, ssl_stem)
        if msg_id is None:
            print("WARNING: could not determine msg_id in " + ssl_path.name, file=sys.stderr)
            continue
        refs = parse_ssl(ssl_path, msg_id)
        for k in ("npc_head", "npc_float", "pc_head", "pc_float", "display"):
            combined[k] |= refs[k]
        combined["dynamic"].extend(refs["dynamic"])

    all_referenced = (
        combined["npc_head"] | combined["npc_float"]
        | combined["pc_head"] | combined["pc_float"]
        | combined["display"]
    )

    tags = assign_tags(prefix, combined["npc_head"], combined["npc_float"])

    # Apply tags and write file
    new_text, written, skipped = apply_tags(msg_text, tags, msg_lines)
    new_text, flattened = flatten_msg_text(new_text)
    if written or flattened:
        TAG_DIR.mkdir(parents=True, exist_ok=True)
        write_msg(tag_path, new_text, eol)

    # ── Report ───────────────────────────────────────────────────────────
    print("\nvock-tag  --  " + msg_stem + ".msg"
          + "  (" + name + ", prefix: " + prefix + ", EOL: " + eol_name + ")")
    print("Source : " + str(read_path))
    print("Output : " + str(tag_path) + ("" if (written or flattened) else "  [not written -- nothing to do]"))
    print("SSL(s): " + ", ".join(ssl_stems))

    entries = []
    for num in sorted(combined["npc_head"]):
        info = msg_lines.get(num)
        if info:
            proposed = tags.get(num, "")
            mark = "  [written]" if num in written else ("  [had: " + info["tag"] + "]" if info["tag"] else "")
            entries.append(fmt_line(num, info["tag"], info["text"], proposed) + mark)
        else:
            entries.append("  {" + str(num) + "}  [NOT IN MSG]")
    section("NPC TALKING HEAD  (gsay_reply)", entries)

    entries = []
    for num in sorted(combined["npc_float"]):
        info = msg_lines.get(num)
        marker = " [also head]" if num in combined["npc_head"] else ""
        if info:
            proposed = tags.get(num, "")
            mark = "  [written]" if num in written else ("  [had: " + info["tag"] + "]" if info["tag"] else "")
            entries.append(fmt_line(num, info["tag"], info["text"], proposed) + marker + mark)
        else:
            entries.append("  {" + str(num) + "}  [NOT IN MSG]" + marker)
    section("NPC FLOATS  (float_msg self_obj)", entries)

    entries = []
    for num in sorted(combined["pc_head"]):
        info = msg_lines.get(num)
        if info:
            entries.append(fmt_line(num, info["tag"], info["text"]))
        else:
            entries.append("  {" + str(num) + "}  [NOT IN MSG]")
    section("PC TALKING HEAD  (giq_option)", entries)

    other = (
        (combined["display"] | combined["pc_float"])
        - combined["npc_head"] - combined["npc_float"] - combined["pc_head"]
    )
    entries = []
    for num in sorted(other):
        info = msg_lines.get(num)
        label = []
        if num in combined["display"]:  label.append("display_msg")
        if num in combined["pc_float"]: label.append("float dude_obj")
        tag_label = " [" + ", ".join(label) + "]"
        if info:
            entries.append(fmt_line(num, info["tag"], info["text"]) + tag_label)
        else:
            entries.append("  {" + str(num) + "}  [NOT IN MSG]" + tag_label)
    section("DISPLAY / OTHER", entries)

    entries = []
    for num in sorted(msg_lines):
        if num not in all_referenced:
            info = msg_lines[num]
            entries.append(fmt_line(num, info["tag"], info["text"]))
    section("UNUSED BY SCRIPT", entries)

    missing = all_referenced - set(msg_lines)
    entries = []
    for num in sorted(missing):
        label = []
        if num in combined["npc_head"]:  label.append("npc_head")
        if num in combined["npc_float"]: label.append("npc_float")
        if num in combined["pc_head"]:   label.append("pc_head")
        if num in combined["display"]:   label.append("display")
        entries.append("  {" + str(num) + "}  [not in msg -- used as: " + ", ".join(label) + "]")
    section("MISSING FROM MSG  (in SSL, not in msg)", entries)

    if combined["dynamic"]:
        print("\n-- DYNAMIC REFS (unresolved) " + "-" * 23)
        for ssl_lineno, desc in combined["dynamic"]:
            print("  ssl:" + str(ssl_lineno) + "  " + desc)

    total_tagged = len(tags)
    already = sum(1 for n in tags if msg_lines.get(n, {}).get("tag"))
    print("\n-- SUMMARY " + "-" * 41)
    print("  Tags to assign : " + str(total_tagged)
          + "  (" + prefix + "1 to " + prefix + str(total_tagged) + ")")
    print("  Written        : " + str(len(written)))
    print("  Already tagged : " + str(already))
    print("  Flattened      : " + str(flattened))
    print("  Skipped (tag≠''): " + str(len(skipped)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 tools/vock_tag.py <prefix>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1].strip())
