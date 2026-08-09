#!/usr/bin/env python3
"""
VOCK dialogue simulator — loads an NPC's .msg + .ssl (source, unexpanded macros) and lets you
play through the conversation in a terminal, picking PC options like the in-game dialogue UI.

Built first against Elise (scelise.msg / scelise.ssl); the parser/interpreter is written to be
NPC-agnostic, but engine-level game-state predicates (has_rep_slaver, dude_is_ranger, etc.) are
mocked via a small interactive setup wizard rather than truly simulating the whole engine.

Usage:
    python3 dialogue_sim.py <path/to/name.msg> <path/to/name.ssl> [--headers DIR ...]
"""

import argparse
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# .msg file parsing
# ---------------------------------------------------------------------------

def parse_msg_file(path: Path) -> dict:
    """Parse a Fallout .msg file into {id: text}. Handles multi-line entries and trailing comments."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    result = {}
    entry_re = re.compile(r'^\{(\d+)\}\{(\w*)\}\{(.*)$')
    i = 0
    while i < len(lines):
        m = entry_re.match(lines[i])
        if m:
            id_, tag, rest = m.groups()
            full = rest
            while not re.search(r'\}\s*(#.*)?$', full):
                i += 1
                if i >= len(lines):
                    break
                full += "\n" + lines[i]
            full = re.sub(r'\}\s*(#.*)?$', '', full)
            full = re.sub(r'\s+', ' ', full.replace("\n", " ")).strip()
            result[int(id_)] = full
        i += 1
    return result


# ---------------------------------------------------------------------------
# Header (#define) scanning — a tiny C-style macro table
# ---------------------------------------------------------------------------

DEFINE_RE = re.compile(r'^\s*#define\s+(\w+)(\([^)]*\))?\s+(.*?)\s*(//.*)?$')
INCLUDE_RE = re.compile(r'^\s*#include\s+"([^"]+)"')

def strip_c_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//.*', '', text)
    return text


def scan_headers(entry_file: Path, extra_header_dirs=None):
    """Follow #include chains from entry_file and collect every #define into a macro table.
    Returns dict[name] -> (params: list[str] | None, body: str)
    """
    visited = set()
    macros = {}
    search_dirs = [entry_file.parent]
    if extra_header_dirs:
        search_dirs.extend(Path(d) for d in extra_header_dirs)

    def resolve(rel_path: str, from_file: Path):
        candidate = (from_file.parent / rel_path).resolve()
        if candidate.exists():
            return candidate
        for d in search_dirs:
            c = (d / Path(rel_path).name).resolve()
            if c.exists():
                return c
        return None

    def visit(f: Path):
        try:
            rp = f.resolve()
        except OSError:
            return
        if rp in visited or not rp.exists():
            return
        visited.add(rp)
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        clean = strip_c_comments(raw)
        for line in clean.split("\n"):
            inc = INCLUDE_RE.match(line)
            if inc:
                target = resolve(inc.group(1), f)
                if target:
                    visit(target)
                continue
            d = DEFINE_RE.match(line)
            if d:
                name, params, body = d.group(1), d.group(2), d.group(3)
                if name in macros:
                    continue  # first definition wins (mirrors #ifndef guards roughly)
                plist = None
                if params is not None:
                    inner = params.strip("()").strip()
                    plist = [p.strip() for p in inner.split(",")] if inner else []
                macros[name] = (plist, body.strip())

    visit(entry_file)
    return macros


PROTECTED_MACROS = {
    "Reply", "Reply_Rand", "NOption", "GOption", "BOption", "NLowOption", "GLowOption",
    "BLowOption", "MOREOPTION", "ENDOPTION", "floater", "floater_rand", "floater_type",
    "floater_type_msg", "floater_bad", "floater_bad_rand", "floater_good", "floater_good_rand",
    "floater_sick", "floater_sick_rand", "floater_afraid", "floater_afraid_rand",
    "GMessage", "NMessage", "BMessage",
}

IDENT_RE = re.compile(r'[A-Za-z_]\w*')


def split_args(text: str):
    """Split a comma-separated argument string, respecting nested parens."""
    args, depth, cur = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def expand_macros(text: str, macros: dict, depth=0, _guard=None) -> str:
    """Textually expand #define macros in `text`, protecting PROTECTED_MACROS by name."""
    if depth > 25:
        return text
    if _guard is None:
        _guard = set()

    out = []
    i = 0
    n = len(text)
    while i < n:
        m = IDENT_RE.match(text, i)
        if not m:
            out.append(text[i])
            i += 1
            continue
        name = m.group(0)
        j = m.end()
        if (name in PROTECTED_MACROS or re.match(r'^(GVAR|LVAR|MVAR)_', name)
                or name not in macros or name in _guard):
            out.append(name)
            i = j
            continue
        params, body = macros[name]
        if params is None:
            # object-like macro
            expanded = expand_macros(body, macros, depth + 1, _guard | {name})
            out.append("(" + expanded + ")")
            i = j
        else:
            # function-like macro: expect '(' next (skip whitespace)
            k = j
            while k < n and text[k] in " \t":
                k += 1
            if k >= n or text[k] != "(":
                # not actually called here; leave bare
                out.append(name)
                i = j
                continue
            depth_p = 1
            start = k + 1
            p = start
            while p < n and depth_p > 0:
                if text[p] == "(":
                    depth_p += 1
                elif text[p] == ")":
                    depth_p -= 1
                p += 1
            arg_text = text[start:p - 1]
            args = split_args(arg_text)
            sub = body
            for pname, aval in zip(params, args):
                sub = re.sub(r'\b' + re.escape(pname) + r'\b', "(" + aval + ")", sub)
            expanded = expand_macros(sub, macros, depth + 1, _guard | {name})
            out.append("(" + expanded + ")")
            i = p
    return "".join(out)


# ---------------------------------------------------------------------------
# SSL tokenizer + statement parser
# ---------------------------------------------------------------------------

KEYWORDS = {"if", "then", "else", "begin", "end", "procedure", "variable", "import"}

TOKEN_RE = re.compile(r"""
    (?P<STRING>"(?:[^"\\]|\\.)*")
  | (?P<NUMBER>\d+)
  | (?P<IDENT>[A-Za-z_]\w*)
  | (?P<OP>:=|==|!=|<=|>=|\+=|-=|<>|[+\-*/<>])
  | (?P<PUNCT>[(),;])
  | (?P<WS>\s+)
""", re.VERBOSE)


def tokenize(text: str):
    toks = []
    for m in TOKEN_RE.finditer(text):
        kind = m.lastgroup
        val = m.group()
        if kind == "WS":
            continue
        toks.append(val)
    return toks


@dataclass
class Call:
    name: str
    args: list = field(default_factory=list)  # list of token-lists (raw)


@dataclass
class Assign:
    name: str
    op: str
    expr: list  # token list


@dataclass
class IfStmt:
    cond: list  # token list (contents of the parens)
    then_stmts: list
    else_stmts: list


def find_matching_paren(tokens, open_i):
    depth = 0
    i = open_i
    while i < len(tokens):
        if tokens[i] == "(":
            depth += 1
        elif tokens[i] == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced parens")


def split_top_level_commas(tokens):
    parts, depth, cur = [], 0, []
    for t in tokens:
        if t == "(":
            depth += 1
            cur.append(t)
        elif t == ")":
            depth -= 1
            cur.append(t)
        elif t == "," and depth == 0:
            parts.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        parts.append(cur)
    return parts


def parse_simple_stmt(tokens):
    if not tokens:
        return None
    if tokens[0] == "call" and len(tokens) >= 2:
        return Call("call", [[tokens[1]]])
    # IDENT (...) form
    if len(tokens) >= 2 and re.match(r'^[A-Za-z_]\w*$', tokens[0]) and tokens[1] == "(":
        close = find_matching_paren(tokens, 1)
        arg_tokens = tokens[2:close]
        args = split_top_level_commas(arg_tokens) if arg_tokens else []
        return Call(tokens[0], args)
    # assignment: IDENT := expr  or IDENT += expr
    if len(tokens) >= 2 and re.match(r'^[A-Za-z_]\w*$', tokens[0]) and tokens[1] in (":=", "+=", "-="):
        return Assign(tokens[0], tokens[1], tokens[2:])
    # bare identifier (ENDOPTION, CheckKarma, GetReaction, ReactToLevel, end_dialogue, etc.)
    if len(tokens) == 1 and re.match(r'^[A-Za-z_]\w*$', tokens[0]):
        return Call(tokens[0], [])
    # fallback: unrecognized statement shape, keep raw for debugging
    return Call("__raw__", [tokens])


def parse_branch(tokens, i):
    """Parse a single branch after 'then'/'else': either a begin..end block or one statement
    (which may itself be a nested if without begin/end)."""
    if tokens[i] == "begin":
        i += 1
        depth = 1
        start = i
        while depth > 0:
            if tokens[i] == "begin":
                depth += 1
            elif tokens[i] == "end":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        inner = tokens[start:i]
        i += 1  # skip matching 'end'
        return parse_stmts(inner), i
    if tokens[i] == "if":
        stmt, i2 = parse_one_if(tokens, i)
        return [stmt], i2
    # single simple statement up to ';'
    j = i
    depth = 0
    while j < len(tokens):
        t = tokens[j]
        if t == "(":
            depth += 1
        elif t == ")":
            depth -= 1
        elif t == ";" and depth == 0:
            break
        j += 1
    stmt = parse_simple_stmt(tokens[i:j])
    return ([stmt] if stmt else []), j + 1


def parse_one_if(tokens, i):
    assert tokens[i] == "if"
    i += 1
    assert tokens[i] == "(", f"expected '(' after if, got {tokens[i:i+5]}"
    close = find_matching_paren(tokens, i)
    cond = tokens[i + 1:close]
    i = close + 1
    assert tokens[i] == "then", f"expected 'then', got {tokens[i:i+5]}"
    i += 1
    then_stmts, i = parse_branch(tokens, i)
    else_stmts = []
    if i < len(tokens) and tokens[i] == "else":
        i += 1
        else_stmts, i = parse_branch(tokens, i)
    return IfStmt(cond, then_stmts, else_stmts), i


def parse_stmts(tokens):
    stmts = []
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == "if":
            stmt, i = parse_one_if(tokens, i)
            stmts.append(stmt)
            continue
        if tokens[i] == ";":
            i += 1
            continue
        # simple statement up to top-level ';'
        j = i
        depth = 0
        while j < n:
            t = tokens[j]
            if t == "(":
                depth += 1
            elif t == ")":
                depth -= 1
            elif t == ";" and depth == 0:
                break
            j += 1
        stmt = parse_simple_stmt(tokens[i:j])
        if stmt:
            stmts.append(stmt)
        i = j + 1
    return stmts


def parse_procedures(tokens):
    """Find every 'procedure NAME begin ... end' definition (skips forward declarations)."""
    procs = {}
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == "procedure" and i + 1 < n:
            name = tokens[i + 1]
            k = i + 2
            if k < n and tokens[k] == ";":
                i = k + 1  # forward declaration, skip
                continue
            if k < n and tokens[k] == "begin":
                depth = 1
                start = k + 1
                p = start
                while depth > 0 and p < n:
                    if tokens[p] == "begin":
                        depth += 1
                    elif tokens[p] == "end":
                        depth -= 1
                        if depth == 0:
                            break
                    p += 1
                body_tokens = tokens[start:p]
                procs[name] = parse_stmts(body_tokens)
                i = p + 1
                continue
        i += 1
    return procs


def parse_variable_decls(tokens):
    """Find top-level 'variable NAME := EXPR;' / 'variable NAME;' declarations (script-level vars)."""
    decls = {}
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == "variable" and i + 1 < n:
            name = tokens[i + 1]
            j = i + 2
            if j < n and tokens[j] == ":=":
                k = j + 1
                depth = 0
                while k < n:
                    t = tokens[k]
                    if t == "(":
                        depth += 1
                    elif t == ")":
                        depth -= 1
                    elif t == ";" and depth == 0:
                        break
                    k += 1
                decls[name] = tokens[j + 1:k]
                i = k + 1
                continue
            elif j < n and tokens[j] == ";":
                decls[name] = ["0"]
                i = j + 1
                continue
        i += 1
    return decls


# ---------------------------------------------------------------------------
# Mock game state + condition evaluation
# ---------------------------------------------------------------------------

class Sym:
    """An opaque symbolic value for any identifier we can't/won't resolve to a real number
    (e.g. a GVAR_*/LVAR_* slot name we're keeping as a string key). Distinct names compare
    unequal to each other; `bwand` against one always reads as 'flag present' (truthy bit)."""
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if isinstance(other, Sym):
            return self.name == other.name
        return NotImplemented

    def __ne__(self, other):
        r = self.__eq__(other)
        return NotImplemented if r is NotImplemented else not r

    def __hash__(self):
        return hash(("Sym", self.name))

    def __and__(self, other):
        return 1

    def __rand__(self, other):
        if isinstance(other, int):
            return other & 1
        return 1

    def __bool__(self):
        return True

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class FallbackNames(dict):
    """A namespace for eval() that returns Sym(name) for any name it doesn't already contain."""

    def __missing__(self, key):
        return Sym(key)


class MockState:
    """All the mutable 'game state' the interpreter reads/writes. Everything defaults to 0/blank
    so a fresh run behaves like a brand-new game unless the setup wizard (or --set flags) changes it."""

    def __init__(self):
        self.gvars = {}      # keyed by GVAR_* symbol name -> int
        self.lvars = {}      # keyed by LVAR_* symbol name -> int
        self.plain = {}      # script-level `variable X := ...;` vars, keyed by raw name
        self.skills = {}     # keyed by resolved skill id (int) -> value, default 50
        self.town_known = {} # keyed by resolved area id (int) -> mark-state int
        self.verbose = False

    def gvar(self, key):
        return self.gvars.get(str(key), 0)

    def set_gvar(self, key, val):
        self.gvars[str(key)] = val

    def lvar(self, key):
        return self.lvars.get(str(key), 0)

    def set_lvar(self, key, val):
        self.lvars[str(key)] = val


def make_eval_namespace(state: MockState):
    ns = FallbackNames()

    def _global_var(x):
        return state.gvar(x)

    def _local_var(x):
        return state.lvar(x)

    def _has_skill(obj, skill):
        return state.skills.get(int(skill) if isinstance(skill, int) else str(skill), 50)

    def _roll_vs_skill(obj, skill, modifier=0):
        val = _has_skill(obj, skill) + int(modifier)
        return random.randint(1, 100) <= max(5, min(95, val))

    def _is_success(x):
        return bool(x)

    def _metarule(rule, arg=None):
        if int(rule) == 17:  # METARULE_TOWN_KNOWN in sfall
            return state.town_known.get(str(arg), 0)
        return 0

    def _random(a, b):
        return random.randint(int(a), int(b))

    # Plain script-level `variable X := ...;` vars (e.g. Elise's Node021Rep) need to be visible
    # to conditions/expressions by their bare name, with their *current* live value -- otherwise
    # a bare identifier like Node021Rep falls through to the Sym() fallback and every comparison
    # against it silently reads as false.
    ns.update(state.plain)

    ns.update({
        "global_var": _global_var,
        "local_var": _local_var,
        "has_skill": _has_skill,
        "roll_vs_skill": _roll_vs_skill,
        "is_success": _is_success,
        "metarule": _metarule,
        "random": _random,
        "has_trait": lambda *a: 0,
        "ncr_flag": lambda x: 0,
        "gvar_bit": lambda g, b: 0,
        "dude_obj": Sym("dude_obj"),
        "self_obj": Sym("self_obj"),
        "True": True,
        "False": False,
    })
    return ns


def init_plain_vars(state: MockState, toks, macros):
    """Seed script-level `variable X := EXPR;` declarations with their real initial value, so a
    read that happens before any write (e.g. a Node021Rep == 0 check on the very first visit)
    sees the correct default instead of falling through to the Sym() fallback."""
    for name, expr_tokens in parse_variable_decls(toks).items():
        if name not in state.plain:
            state.plain[name] = eval_expr(expr_tokens, macros, state)


def eval_condition(cond_tokens, macros, state: MockState) -> bool:
    text = " ".join(cond_tokens)
    expanded = expand_macros(text, macros)
    py_expr = re.sub(r'\bbwand\b', '&', expanded)
    py_expr = re.sub(r'\bnot\b', ' not ', py_expr)
    py_expr = py_expr.replace("<>", "!=")
    ns = make_eval_namespace(state)
    try:
        result = eval(py_expr, {"__builtins__": {}}, ns)
    except Exception as e:
        if state.verbose:
            print(f"    [cond eval error: {cond_tokens!r} -> {py_expr!r}: {e}]", file=sys.stderr)
        result = False
    return bool(result)


def eval_expr(tokens, macros, state: MockState):
    """Evaluate a plain (non-boolean-specific) expression, e.g. an assignment RHS or a call arg."""
    text = " ".join(tokens)
    expanded = expand_macros(text, macros)
    py_expr = re.sub(r'\bbwand\b', '&', expanded)
    ns = make_eval_namespace(state)
    try:
        return eval(py_expr, {"__builtins__": {}}, ns)
    except Exception:
        return Sym(text)


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

def strip_outer_parens(tokens):
    while len(tokens) >= 2 and tokens[0] == "(" and tokens[-1] == ")":
        if find_matching_paren(tokens, 0) == len(tokens) - 1:
            tokens = tokens[1:-1]
        else:
            break
    return tokens


NO_OP_CALLS = {
    "start_gdialog", "gSay_Start", "gSay_End", "ndebug", "debug_msg", "script_overrides",
    "CheckKarma", "GetReaction", "ReactToLevel", "set_self_team", "set_self_ai",
    "inc_good_critter", "add_timer_event", "unset_ncr_flag", "reg_anim_clear",
    "reg_anim_begin", "reg_anim_end", "self_walk_to_tile", "load_map", "create_object",
    "create_object_sid", "tile_num",
}

FLAVOR_CALLS = {
    "give_xp": "+{0} XP",
    "give_exp_points": "+{0} XP",
    "dude_caps_adjust": "{0:+d} caps",
    "inc_general_rep": "general reputation +{0}",
    "inc_ncr_rep": "NCR reputation +{0}",
    "add_obj_to_inven": "receives an item",
}


class Accumulator:
    def __init__(self):
        self.lines = []   # list of (kind, text)  kind in {npc, float, narrate, flavor}
        self.options = []  # list of (text, target)
        self.ended = False

    def say(self, text):
        self.lines.append(("npc", text))

    def float(self, text):
        self.lines.append(("float", text))

    def narrate(self, text):
        self.lines.append(("narrate", text))

    def flavor(self, text):
        self.lines.append(("flavor", text))

    def offer(self, text, target):
        self.options.append((text, target))


class Interpreter:
    def __init__(self, procs, msgs, macros, state: MockState):
        self.procs = procs
        self.msgs = msgs
        self.macros = macros
        self.state = state

    def msg(self, mid):
        return self.msgs.get(mid, f"<<missing msg {mid}>>")

    def resolve_msg_id(self, arg_tokens):
        joined = "".join(arg_tokens)
        if re.fullmatch(r'-?\d+', joined):
            return int(joined)
        val = eval_expr(arg_tokens, self.macros, self.state)
        if isinstance(val, bool):
            return int(val)
        if isinstance(val, int):
            return val
        return None

    def run(self, proc_name, acc: Accumulator, depth=0):
        if depth > 60:
            return
        stmts = self.procs.get(proc_name)
        if stmts is None:
            return
        self.exec_stmts(stmts, acc, depth)

    def exec_stmts(self, stmts, acc: Accumulator, depth):
        # Note: `end_dialogue` is a bookkeeping flag for the outer dialogue window, not a halt
        # instruction -- statements after it (e.g. talk_p_proc's trailing LVAR_Herebefore update)
        # still run for real, so we don't short-circuit on acc.ended here.
        for stmt in stmts:
            self.exec_stmt(stmt, acc, depth)

    def exec_stmt(self, stmt, acc: Accumulator, depth):
        if isinstance(stmt, IfStmt):
            cond = eval_condition(stmt.cond, self.macros, self.state)
            branch = stmt.then_stmts if cond else stmt.else_stmts
            self.exec_stmts(branch, acc, depth)
            return
        if isinstance(stmt, Assign):
            val = eval_expr(stmt.expr, self.macros, self.state)
            cur = self.state.plain.get(stmt.name, 0)
            if stmt.op == ":=":
                self.state.plain[stmt.name] = val
            elif stmt.op == "+=":
                try:
                    self.state.plain[stmt.name] = cur + val
                except TypeError:
                    self.state.plain[stmt.name] = val
            elif stmt.op == "-=":
                try:
                    self.state.plain[stmt.name] = cur - val
                except TypeError:
                    self.state.plain[stmt.name] = val
            return
        if isinstance(stmt, Call):
            self.exec_call(stmt, acc, depth)
            return

    def exec_call(self, call: Call, acc: Accumulator, depth):
        name = call.name
        args = call.args

        if name == "call":
            target = args[0][0]
            self.run(target, acc, depth + 1)
            return

        if name == "Reply" or name == "NMessage" or name == "GMessage" or name == "BMessage":
            mid = self.resolve_msg_id(args[0])
            if mid is not None:
                acc.say(self.msg(mid))
            return

        if name == "Reply_Rand":
            a = self.resolve_msg_id([str(eval_expr(args[0], self.macros, self.state))])
            return

        if name in ("NOption", "GOption", "BOption"):
            text = self.option_text(args[0])
            target = args[1][0]
            acc.offer(text, target)
            return

        if name in ("NLowOption", "GLowOption", "BLowOption"):
            text = self.option_text(args[0])
            target = args[1][0]
            acc.offer(text, target)
            return

        if name == "MOREOPTION":
            target = args[0][0]
            acc.offer("Tell me more.", target)
            return

        if name == "ENDOPTION":
            acc.offer("Ok.", "Node999")
            return

        if name == "floater":
            mid = self.resolve_msg_id(args[0])
            if mid is not None:
                acc.float(self.msg(mid))
            return

        if name == "floater_rand":
            a = int("".join(args[0]))
            b = int("".join(args[1]))
            mid = random.randint(a, b)
            acc.float(self.msg(mid))
            return

        if name == "float_msg":
            # float_msg(obj, mstr(N), color)
            msg_arg = args[1] if len(args) > 1 else None
            if msg_arg and msg_arg[0] == "mstr":
                close = find_matching_paren(msg_arg, 1)
                mid = self.resolve_msg_id(msg_arg[2:close])
                if mid is not None:
                    acc.float(self.msg(mid))
            return

        if name == "display_msg":
            if args and args[0] and args[0][0] == "mstr":
                close = find_matching_paren(args[0], 1)
                mid = self.resolve_msg_id(args[0][2:close])
                if mid is not None:
                    acc.narrate(self.msg(mid))
            return

        if name == "end_dialogue":
            acc.ended = True
            return

        if name in ("set_global_var", "set_local_var"):
            key = "".join(args[0])
            val = eval_expr(args[1], self.macros, self.state)
            if name == "set_global_var":
                self.state.set_gvar(key, val)
            else:
                self.state.set_lvar(key, val)
            return

        if name in ("global_var", "local_var"):
            return  # bare read with no effect as a statement; ignore

        if name in NO_OP_CALLS:
            return

        if name in FLAVOR_CALLS:
            template = FLAVOR_CALLS[name]
            try:
                val = eval_expr(args[0], self.macros, self.state) if args else 0
                acc.flavor(template.format(val) if "{0" in template else template)
            except Exception:
                acc.flavor(template.split("{")[0].strip() or name)
            return

        if name == "__raw__":
            return

        # Unknown call: see if it's a macro that expands into something we DO understand
        # (e.g. Elise's own set_elise_seed(x) -> set_global_var(GVAR_NCR_ELISE_SEED, x)).
        arg_text = ", ".join(" ".join(a) for a in args)
        call_text = f"{name}({arg_text})" if args or name in self.macros and self.macros[name][0] is not None else name
        expanded = expand_macros(call_text, self.macros)
        if expanded != call_text and expanded.strip("()") != name:
            new_tokens = strip_outer_parens(tokenize(expanded))
            new_stmt = parse_simple_stmt(new_tokens)
            if new_stmt is not None and not (isinstance(new_stmt, Call) and new_stmt.name == name):
                self.exec_stmt(new_stmt, acc, depth)
                return
        if self.state.verbose:
            print(f"    [unhandled call: {name}({arg_text})]", file=sys.stderr)

    def option_text(self, id_tokens):
        joined = "".join(id_tokens)
        if joined == "MORESTRING":
            return "Tell me more."
        if joined == "ENDSTRING":
            return "Ok."
        mid = self.resolve_msg_id(id_tokens)
        if mid is not None:
            return self.msg(mid)
        return f"<<{joined}>>"


# ---------------------------------------------------------------------------
# Auto-generated setup wizard: statically walk the reachable dialogue graph and
# surface the game-state variables that actually gate a branch somewhere in it.
# ---------------------------------------------------------------------------

def walk_all_stmts(stmts):
    for s in stmts:
        yield s
        if isinstance(s, IfStmt):
            yield from walk_all_stmts(s.then_stmts)
            yield from walk_all_stmts(s.else_stmts)


def collect_reachable_procs(procs, start="talk_p_proc"):
    seen = set()
    queue = [start]
    while queue:
        p = queue.pop()
        if p in seen or p not in procs:
            continue
        seen.add(p)
        for stmt in walk_all_stmts(procs[p]):
            if not isinstance(stmt, Call):
                continue
            if stmt.name == "call" and stmt.args:
                queue.append(stmt.args[0][0])
            elif stmt.name in ("NOption", "GOption", "BOption", "NLowOption",
                                "GLowOption", "BLowOption") and len(stmt.args) >= 2:
                queue.append(stmt.args[1][0])
            elif stmt.name == "MOREOPTION" and stmt.args:
                queue.append(stmt.args[0][0])
            elif stmt.name == "ENDOPTION":
                queue.append("Node999")
    return seen


def resolve_const(name, macros):
    if re.fullmatch(r'-?\d+', name):
        return int(name)
    if name in macros and macros[name][0] is None:
        exp = expand_macros(macros[name][1], macros).strip()
        if re.fullmatch(r'\(*-?\d+\)*', exp):
            return int(exp.strip("()"))
    return None


def build_setup_items(procs, macros, start="talk_p_proc"):
    reachable = collect_reachable_procs(procs, start)
    conds = []
    for name in reachable:
        for s in walk_all_stmts(procs.get(name, [])):
            if isinstance(s, IfStmt):
                conds.append(s.cond)

    items = {}  # (kind, varname) -> item dict

    def get_item(kind, varname, itype):
        key = (kind, varname)
        it = items.get(key)
        if it is None:
            it = {"type": itype, "kind": kind, "name": varname, "bools": {}, "enums": {}}
            items[key] = it
        return it

    for cond in conds:
        raw = " ".join(cond)
        # Fully expand once so predicate macros like dude_is_ranger / ncr_global_state(...) /
        # bad_critter_reaction reveal the global_var()/local_var() calls hiding inside them.
        exp_whole = expand_macros(raw, macros)

        for kind_w, varname in re.findall(r'(global_var|local_var)\s*\(\s*([A-Za-z_]\w*)\s*\)', exp_whole):
            kind = "gvar" if kind_w == "global_var" else "lvar"
            it = get_item(kind, varname, "int")

        for m in re.finditer(r'(global_var|local_var)\s*\(\s*([A-Za-z_]\w*)\s*\)\s*bwand\s*\(*\s*(-?\d+|[A-Za-z_]\w*)', exp_whole):
            kind = "gvar" if m.group(1) == "global_var" else "lvar"
            varname, flagraw = m.group(2), m.group(3)
            flag_val = resolve_const(flagraw, macros)
            if flag_val:
                it = get_item(kind, varname, "int")
                it["bools"][flagraw] = flag_val

        for m in re.finditer(r'(global_var|local_var)\s*\(\s*([A-Za-z_]\w*)\s*\)\s*(==|<=|>=|<|>|!=)\s*\(*\s*(-?\d+)', exp_whole):
            kind = "gvar" if m.group(1) == "global_var" else "lvar"
            varname, op, const = m.group(2), m.group(3), int(m.group(4))
            it = get_item(kind, varname, "int")
            label = f"{'==' if op in ('==','!=') else op} {const}"
            it["bools"][label] = const  # best-effort: "on" sets var to this constant

        for m in re.finditer(r'([A-Za-z_]\w*)\s*(==|<)\s*([A-Za-z_]\w*)', raw):
            left, op, right = m.groups()
            if left in macros and macros[left][0] is None:
                exp = expand_macros(macros[left][1], macros).strip()
                mm = re.fullmatch(r'\(*\s*(global_var|local_var)\s*\(\s*([A-Za-z_]\w*)\s*\)\s*\)*', exp)
                if mm:
                    rv = resolve_const(right, macros)
                    if rv is not None:
                        kind = "gvar" if mm.group(1) == "global_var" else "lvar"
                        it = get_item(kind, mm.group(2), "enum")
                        it["enums"][right] = rv

        for m in re.finditer(r'\btown_known\s*\(\s*([A-Za-z_]\w*)\s*\)\s*(==|!=)\s*([A-Za-z_]\w*)', raw):
            area, op, mark = m.groups()
            area_val = resolve_const(area, macros)
            mark_val = resolve_const(mark, macros)
            if area_val is not None and mark_val is not None:
                it = get_item("town", str(area_val), "enum")
                it["label"] = area
                it["enums"][mark] = mark_val

    # pick a final "kind" per item: enum takes priority (most informative), then bool-ish int, then plain int
    finalized = []
    for (kind, varname), it in sorted(items.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if it["enums"]:
            it["type"] = "enum"
        elif it["bools"]:
            it["type"] = "bool"
        else:
            it["type"] = "int"
        finalized.append(it)
    return finalized


# ---------------------------------------------------------------------------
# CLI: setup wizard + play loop
# ---------------------------------------------------------------------------

def guess_npc_name(ssl_path: Path) -> str:
    text = ssl_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'Name:\s*(.+)', text)
    if m:
        return m.group(1).strip()
    return ssl_path.stem


def prompt_item(it):
    name = it["name"]
    kind = it["kind"]
    if it["type"] == "enum":
        choices = list(it["enums"].items())
    elif it["type"] == "bool":
        choices = list(it["bools"].items())
    else:
        choices = []

    where = {"gvar": "global var", "lvar": "local var", "town": "town_known"}[kind]
    label = f" ({it['label']})" if it.get("label") else ""
    print(f"\n{name}{label}  [{where}, currently 0]")
    for i, (cname, cval) in enumerate(choices, 1):
        print(f"  {i}. {cname}  -> sets to {cval}")
    print("  Enter a number above, type a raw integer, or press Enter to leave at 0.")
    raw = input("  > ").strip()
    if not raw:
        return None
    if raw.lstrip("-").isdigit():
        n = int(raw)
        if choices and 1 <= n <= len(choices):
            return choices[n - 1][1]
        return n
    print("  (not understood, leaving at default)")
    return None


def run_setup_wizard(items, state: MockState):
    print("\n--- Setup: configure starting game state (Enter to skip any of these) ---")
    for it in items:
        val = prompt_item(it)
        if val is None:
            continue
        if it["kind"] == "gvar":
            state.set_gvar(it["name"], val)
        elif it["kind"] == "lvar":
            state.set_lvar(it["name"], val)
        elif it["kind"] == "town":
            state.town_known[it["name"]] = val
    print("\n--- Setup complete ---\n")


def play(interp: Interpreter, npc_name: str, start="talk_p_proc"):
    print(f"\n{'=' * 60}")
    print(f"  Talking to {npc_name}")
    print(f"{'=' * 60}")
    current = start
    while True:
        acc = Accumulator()
        interp.run(current, acc)
        for kind, text in acc.lines:
            if kind == "npc":
                print(f"\n{npc_name}: {text}")
            elif kind == "float":
                print(f"\n*{npc_name}: {text}*")
            elif kind == "narrate":
                print(f"\n[{text}]")
            elif kind == "flavor":
                print(f"    ({text})")
        if not acc.options:
            print("\n(The conversation ends.)")
            again = input("Approach again? [y/N] > ").strip().lower()
            if again == "y":
                current = start
                continue
            print("\nGoodbye.")
            return
        print()
        for i, (text, _target) in enumerate(acc.options, 1):
            print(f"  {i}. {text}")
        raw = input("> ").strip().lower()
        if raw in ("q", "quit", "exit"):
            print("\nGoodbye.")
            return
        if not raw.isdigit() or not (1 <= int(raw) <= len(acc.options)):
            print("  (invalid choice, try again)")
            continue
        text, target = acc.options[int(raw) - 1]
        print(f"\nYou: {text}")
        current = target


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("msg", type=Path, help="path to the NPC's .msg file")
    ap.add_argument("ssl", type=Path, help="path to the NPC's .ssl source file (unexpanded, e.g. the BEL/rpu scripts_src copy)")
    ap.add_argument("--headers", nargs="*", default=[], help="extra header search directories")
    ap.add_argument("--name", default=None, help="override the displayed NPC name")
    ap.add_argument("--start", default="talk_p_proc", help="procedure to start from (default: talk_p_proc)")
    ap.add_argument("--auto", action="store_true", help="skip the setup wizard, play with default (fresh-game) state")
    ap.add_argument("--seed", type=int, default=None, help="random seed, for reproducible skill rolls/random floats")
    ap.add_argument("--verbose", action="store_true", help="print parser/eval warnings to stderr")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if not args.msg.exists():
        sys.exit(f"msg file not found: {args.msg}")
    if not args.ssl.exists():
        sys.exit(f"ssl file not found: {args.ssl}")

    msgs = parse_msg_file(args.msg)
    macros = scan_headers(args.ssl, args.headers)
    raw = args.ssl.read_text(encoding="utf-8", errors="replace")
    clean = strip_c_comments(raw)
    toks = tokenize(clean)
    procs = parse_procedures(toks)

    if args.start not in procs:
        sys.exit(f"procedure '{args.start}' not found in {args.ssl.name}. "
                  f"Available: {', '.join(sorted(procs))}")

    state = MockState()
    state.verbose = args.verbose
    init_plain_vars(state, toks, macros)

    npc_name = args.name or guess_npc_name(args.ssl)

    if not args.auto:
        items = build_setup_items(procs, macros, start=args.start)
        if items:
            print(f"Loaded {args.ssl.name} — found {len(items)} game-state variable(s) that affect this conversation.")
            do_wizard = input("Configure them now? [y/N] > ").strip().lower()
            if do_wizard == "y":
                run_setup_wizard(items, state)

    interp = Interpreter(procs, msgs, macros, state)
    try:
        play(interp, npc_name, start=args.start)
    except (KeyboardInterrupt, EOFError):
        print("\n\nGoodbye.")


if __name__ == "__main__":
    main()
