# Body of a self-contained proof-based bot for the Prisoner's Dilemma (program-equilibrium rules).
#
# This file is NOT imported by anything. pe_env.make_bot(spec) builds a bot's whole source as
#     CODE = 'SPEC = <spec>\n' + <this file's text>
#     source = "CODE = %r\nexec(CODE)\n" % CODE
# so every bot carries its own copy of this prover. Run as `python3 -I -B -c <source>` with the opponent's
# source on stdin, it prints C or D. It reconstructs its own source from CODE (a quine), reads the opponent's
# source, and decides by an exact bounded search of BPC (README, "Bounded agents").
#
# Facts about the opponent come only from analysing the opponent's source string here:
#   - print("C") / print("D") (and nothing else) is a constant program;
#   - "CODE = <string>\nexec(CODE)\n" whose string is "SPEC = <literal>\n" followed by text identical,
#     character for character, to this bot's own body is a program running this same prover on that SPEC.
#     For such programs the bot writes down the Unf axiom (the opponent's action is what its decision list
#     returns, with each prove(...) read as derivability in the same calculus) itself.
#   - anything else is unknown: no Unf axiom, so nothing about its action is provable.
import ast, sys, hashlib
from functools import lru_cache
from itertools import product

SELF = "CODE = %r\nexec(CODE)\n" % CODE          # my own source (CODE is set by my first line)
BODY = CODE.split("\n", 1)[1]                    # my prover, i.e. everything after my SPEC line

INF = 10 ** 9
K = 4                       # largest finite box index in the language (budgets 0..K or inf)
IDX = list(range(K + 1)) + [INF]
def succ(n): return n + 1 if n < K else INF
def idx_str(n): return "inf" if n == INF else str(n)

# ---------------------------------------------------------------- the game (part of the bot)
ACTS = ["C", "D"]
PAYOFF = {(0, 0): (2, 2), (0, 1): (0, 3), (1, 0): (3, 0), (1, 1): (1, 1)}   # (mine, theirs) -> (me, them)
def u_me(mine, theirs): return PAYOFF[(mine, theirs)][0]
def u_them(mine, theirs): return PAYOFF[(mine, theirs)][1]

# ---------------------------------------------------------------- programs are named by a hash of their source
SRC = {}
def token(src):
    t = hashlib.sha256(src.encode()).hexdigest()[:16]
    assert SRC.setdefault(t, src) == src, "hash collision"
    return t
def const_src(a): return 'print("%s")\n' % a
CONST = {a: token(const_src(a)) for a in ACTS}
NAMES = {}                                       # optional display names (filled by a harness, never by a bot)

# ---------------------------------------------------------------- formulas (hashable tuples)
TOP, BOT = ("top",), ("bot",)
def Not(f):
    if f == TOP: return BOT
    if f == BOT: return TOP
    if f[0] == "not": return f[1]
    return ("not", f)
def _flat(op, fs):
    out = []
    for f in fs:
        if f[0] == op: out.extend(f[1:])
        else: out.append(f)
    seen, res = set(), []
    for f in out:
        if f not in seen: seen.add(f); res.append(f)
    return res
def And(*fs):
    fs = [f for f in _flat("and", fs) if f != TOP]
    if BOT in fs: return BOT
    return TOP if not fs else fs[0] if len(fs) == 1 else ("and",) + tuple(fs)
def Or(*fs):
    fs = [f for f in _flat("or", fs) if f != BOT]
    if TOP in fs: return TOP
    return BOT if not fs else fs[0] if len(fs) == 1 else ("or",) + tuple(fs)
def Imp(a, b): return Or(Not(a), b)
def Iff(a, b): return And(Imp(a, b), Imp(b, a))
def Atom(X, Y, a): return ("atom", X, Y, a)      # "program X, given program Y's source, outputs ACTS[a]"
def Box(t, L, n, phi): return ("box", t, L, n, phi)
def FP(L, T, g): return ("fp", L, T, g)

def subformulas(f, acc=None):
    acc = set() if acc is None else acc
    if f in acc: return acc
    acc.add(f)
    if f[0] in ("not", "and", "or"):
        for x in f[1:]: subformulas(x, acc)
    return acc
def boxes_in(f): return {s for s in subformulas(f) if s[0] == "box"}
def atoms_in(f):
    out, stack, seen = set(), [f], set()
    while stack:
        g = stack.pop()
        if g in seen: continue
        seen.add(g)
        if g[0] == "atom": out.add(g)
        elif g[0] in ("not", "and", "or"): stack.extend(g[1:])
        elif g[0] == "box": stack.append(g[4])
        elif g[0] == "fp": stack.append(g[2])
    return out
def box_free(f): return not any(s[0] in ("box", "fp") for s in subformulas(f))
def box_positive(f):
    if f[0] == "box": return True
    if f[0] in ("and", "or"): return all(box_positive(x) for x in f[1:])
    return False
def name(tok): return NAMES.get(tok, tok[:6])
def show(f):
    k = f[0]
    if k == "top": return "T"
    if k == "bot": return "F"
    if k == "atom": return f"[{name(f[1])}|{name(f[2])}={ACTS[f[3]]}]"
    if k == "not": return "~" + show(f[1])
    if k == "and": return "(" + " & ".join(show(x) for x in f[1:]) + ")"
    if k == "or": return "(" + " | ".join(show(x) for x in f[1:]) + ")"
    if k == "box": return f"Box{'+1' if f[1] else ''}_{idx_str(f[3])}{show(f[4])}"
    if k == "fp": return f"psi[{show(f[2])},g={idx_str(f[3])}]"
    return str(f)

# ---------------------------------------------------------------- reading a program's source
# A SPEC is a decision list, e.g. "C if prove(0, 2, opp(self) == C)\nD otherwise", or "V4 budget=2 probe=1".
# Formulas: ("eq", Xref, Yref, action), refs "self", "opp", ("const", a); conditions ("prove", t, n, F).
def _n(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int): return node.value
    if isinstance(node, ast.Name) and node.id == "inf": return INF
    raise SyntaxError("budget must be an integer or inf")
def _ref(node):
    if not isinstance(node, ast.Name): raise SyntaxError("program reference must be a name")
    if node.id in ("self", "opp"): return node.id
    if node.id.startswith("CONST_") and node.id[6:] in ACTS: return ("const", node.id[6:])
    raise SyntaxError(f"unknown program {node.id}")
def _formula(node):
    if isinstance(node, ast.BoolOp):
        return ("and" if isinstance(node.op, ast.And) else "or",) + tuple(_formula(v) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return ("not", _formula(node.operand))
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        call, op, act = node.left, node.ops[0], node.comparators[0]
        if not (isinstance(call, ast.Call) and len(call.args) == 1 and isinstance(act, ast.Name)
                and act.id in ACTS):
            raise SyntaxError("expected X(Y) == a")
        eq = ("eq", _ref(call.func), _ref(call.args[0]), act.id)
        if isinstance(op, ast.Eq): return eq
        if isinstance(op, ast.NotEq): return ("not", eq)
    raise SyntaxError("unsupported formula")
def _cond(node):
    if isinstance(node, ast.BoolOp):
        return ("and" if isinstance(node.op, ast.And) else "or",) + tuple(_cond(v) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return ("not", _cond(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "prove":
        t, n, F = node.args
        if not (isinstance(t, ast.Constant) and t.value in (0, 1)): raise SyntaxError("theory must be 0 or 1")
        return ("prove", t.value, _n(n), _formula(F))
    raise SyntaxError("unsupported condition")
def parse_spec(spec):
    lines = [l.strip() for l in spec.strip().splitlines() if l.strip()]
    if lines[0].startswith("V4"):
        kw = dict(p.split("=") for p in lines[0].split()[1:])
        return v4_rules(_n(ast.parse(kw.get("budget", "inf"), mode="eval").body), int(kw.get("probe", 1)))
    rules, default = [], None
    for l in lines:
        act, rest = l.split(None, 1)
        if act not in ACTS: raise SyntaxError(l)
        if rest == "otherwise": default = ACTS.index(act)
        elif rest.startswith("if "): rules.append((_cond(ast.parse(rest[3:], mode="eval").body), ACTS.index(act)))
        else: raise SyntaxError(l)
    if default is None: raise SyntaxError("missing 'otherwise' line")
    return tuple(rules), default

def v4_rules(k, probe):
    """V4 (see v4.py) read off the payoff matrix: decision list with action indices."""
    n = len(ACTS)
    U, V = u_me, u_them
    m_me = max(min(U(x, y) for y in range(n)) for x in range(n))
    m_op = max(min(V(y, x) for y in range(n)) for x in range(n))    # the opponent's maxmin (symmetric game)
    best = lambda b: max(range(n), key=lambda x: (U(x, b), -x))
    groups = {"coop": [], "neutral": [], "exploit": []}
    for a in range(n):
        for b in range(n):
            u, v = U(a, b), V(a, b)
            if u < m_me: continue
            t = "exploit" if v < m_op else ("coop" if (u > m_me or v > m_op) else "neutral")
            groups[t].append((u, a, b))
    def ge(a, u, theory):
        good = [("eq", "opp", "self", ACTS[y]) for y in range(n) if U(a, y) >= u]
        return ("prove", theory, k, ("or", ("not", ("eq", "self", "opp", ACTS[a])), ("or",) + tuple(good)))
    rules, seen = [], set()
    for u, a, b in sorted(groups["coop"], key=lambda c: (-c[0], c[1], c[2])):
        ax = best(b)
        if U(ax, b) > U(a, b):
            pr = ("prove", probe, k, ("not", ("eq", "opp", ("const", ACTS[ax]), ACTS[b])))
            rules.append((("and", ge(a, u, 0), pr), a))
        else:
            rules.append((ge(a, u, 0), a))
    for grp, th in (("exploit", 1), ("neutral", 0)):
        for u, a, b in sorted(groups[grp], key=lambda c: (-c[0], c[1])):
            if (u, a, th) in seen: continue
            seen.add((u, a, th)); rules.append((ge(a, u, th), a))
    maxmin_a = max(range(n), key=lambda x: (min(U(x, y) for y in range(n)), -x))
    return tuple(rules), maxmin_a

@lru_cache(maxsize=None)
def analyse(tok):
    """What this bot can tell about program tok from its source alone.
    ("CONST", a): it prints ACTS[a] whatever its input.  ("DL", rules, default): it runs this very prover on
    the decision list (rules, default).  None: unknown."""
    src = SRC[tok]
    try: body = ast.parse(src).body
    except SyntaxError: return None
    if (len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Call)):
        c = body[0].value
        if (isinstance(c.func, ast.Name) and c.func.id == "print" and not c.keywords and len(c.args) == 1
                and isinstance(c.args[0], ast.Constant) and c.args[0].value in ACTS):
            return ("CONST", ACTS.index(c.args[0].value))
    if (len(body) == 2 and isinstance(body[0], ast.Assign) and len(body[0].targets) == 1
            and isinstance(body[0].targets[0], ast.Name) and body[0].targets[0].id == "CODE"
            and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
        code = body[0].value.value
        if src != "CODE = %r\nexec(CODE)\n" % code: return None     # must be exactly the quine form I use
        line, _, rest = code.partition("\n")
        if rest != BODY or not line.startswith("SPEC = "): return None   # a different prover: unknown
        try:
            spec = ast.literal_eval(line[len("SPEC = "):])
            if not isinstance(spec, str) or line != "SPEC = %r" % spec: return None
            return ("DL",) + parse_spec(spec)
        except Exception:
            return None
    return None

def lang(X, Y):
    """Name of the match system for the pair {X, Y} (both bots of a match compute the same name)."""
    return (X, Y) if X <= Y else (Y, X)

def _resolve_f(F, X, Y):
    k = F[0]
    if k == "eq":
        _, xr, yr, a = F
        ref = lambda r: X if r == "self" else Y if r == "opp" else CONST[r[1]]
        return Atom(ref(xr), ref(yr), ACTS.index(a))
    if k == "not": return Not(_resolve_f(F[1], X, Y))
    if k == "and": return And(*[_resolve_f(x, X, Y) for x in F[1:]])
    if k == "or": return Or(*[_resolve_f(x, X, Y) for x in F[1:]])
    raise ValueError(F)
def _resolve_c(c, X, Y):
    k = c[0]
    if k == "prove":
        _, t, n, F = c
        return Box(t, lang(X, Y), n, _resolve_f(F, X, Y))
    if k == "not": return Not(_resolve_c(c[1], X, Y))
    if k == "and": return And(*[_resolve_c(x, X, Y) for x in c[1:]])
    if k == "or": return Or(*[_resolve_c(x, X, Y) for x in c[1:]])
    raise ValueError(c)

@lru_cache(maxsize=None)
def unfold(atom):
    """Unf, derived from the source of X: the condition under which X outputs a given Y; None if X is unknown."""
    _, X, Y, a = atom
    p = analyse(X)
    if p is None: return None
    if p[0] == "CONST": return TOP if p[1] == a else BOT
    _, rules, default = p
    conds = [(_resolve_c(c, X, Y), b) for c, b in rules]
    alts, earlier = [], []
    for c, b in conds:
        if b == a: alts.append(And(c, *[Not(e) for e in earlier]))
        earlier.append(c)
    if default == a: alts.append(And(*[Not(e) for e in earlier]))
    return Or(*alts)

# ---------------------------------------------------------------- SAT (DPLL with watched literals)
class CNF:
    def __init__(self):
        self.var, self.clauses, self.n = {}, [], 0
        self.true = self.new()
        self.clauses.append([self.true])
    def new(self):
        self.n += 1; return self.n
    def lit(self, f):
        if f == TOP: return self.true
        if f == BOT: return -self.true
        if f[0] == "not": return -self.lit(f[1])
        if f in self.var: return self.var[f]
        if f[0] in ("atom", "box", "fp"):
            v = self.var[f] = self.new(); return v
        xs = [self.lit(x) for x in f[1:]]
        v = self.var[f] = self.new()
        if f[0] == "and":
            for x in xs: self.clauses.append([-v, x])
            self.clauses.append([v] + [-x for x in xs])
        else:
            for x in xs: self.clauses.append([v, -x])
            self.clauses.append([-v] + xs)
        return v
    def assert_(self, f): self.clauses.append([self.lit(f)])

class Solver:
    def __init__(self, n, clauses):
        self.n = n
        self.cls = [list(dict.fromkeys(c)) for c in clauses]
        self.cls = [c for c in self.cls if not any(-l in c for l in c)]
        self.units = [c[0] for c in self.cls if len(c) == 1]
        self.bad = any(len(c) == 0 for c in self.cls)
        self.watch = {}
        occ = [0] * (n + 1)
        for i, c in enumerate(self.cls):
            for l in c: occ[abs(l)] += 1
            if len(c) >= 2:
                self.watch.setdefault(c[0], []).append(i); self.watch.setdefault(c[1], []).append(i)
        self.order = sorted(range(1, n + 1), key=lambda v: -occ[v])
        self.base = None
        if not self.bad:
            b = self._search(None, (), base_only=True)
            if b is None: self.bad = True
            else: self.base = b
    def solve(self, assume=()):
        if self.bad: return None
        return self._search(self.base, assume)
    def _search(self, base, assume, base_only=False):
        if base is None:
            val = [0] * (self.n + 1); trail = []; q = 0
            assume = list(self.units) + list(assume)
        else:
            val = list(base[0]); trail = list(base[1]); q = len(trail)
        def setl(l):
            v = l if l > 0 else -l
            s = 1 if l > 0 else -1
            if val[v] == 0: val[v] = s; trail.append(l); return True
            return val[v] == s
        for l in assume:
            if not setl(l): return None
        dec = []
        cls, watch = self.cls, self.watch
        while True:
            confl = False
            while q < len(trail) and not confl:
                f = -trail[q]; q += 1
                ws = watch.get(f)
                if not ws: continue
                i = 0
                while i < len(ws):
                    ci = ws[i]; c = cls[ci]
                    if c[0] == f: c[0], c[1] = c[1], c[0]
                    o = c[0]; vo = val[abs(o)]
                    if vo != 0 and (vo > 0) == (o > 0): i += 1; continue
                    for j in range(2, len(c)):
                        lj = c[j]; vj = val[abs(lj)]
                        if vj == 0 or (vj > 0) == (lj > 0):
                            c[1], c[j] = lj, f
                            watch.setdefault(lj, []).append(ci)
                            ws[i] = ws[-1]; ws.pop()
                            break
                    else:
                        if vo == 0: setl(o); i += 1
                        else: confl = True; break
                        continue
            if confl:
                while dec:
                    tl, l, flipped = dec.pop()
                    for x in trail[tl:]: val[abs(x)] = 0
                    del trail[tl:]
                    q = tl
                    if not flipped:
                        dec.append((tl, -l, True)); setl(-l); break
                else:
                    return None
                continue
            if base_only: return (val, trail)
            for v in self.order:
                if val[v] == 0: break
            else:
                return val
            dec.append((len(trail), -v, False)); setl(-v)

# ---------------------------------------------------------------- the match system (built inside this process)
SYSTEMS = {}
def system(L):
    if L not in SYSTEMS: SYSTEMS[L] = System(L)
    return SYSTEMS[L]
def lang_of_atom(a): return lang(a[1], a[2])

class System:
    """BPC for the pair L: language generated by the two sources, axioms, exact derivability by height."""
    def __init__(self, L):
        self.L = L
        X, Y = L
        main = [Atom(X, Y, a) for a in range(len(ACTS))]
        other = [Atom(Y, X, b) for b in range(len(ACTS))]
        self.main = list(dict.fromkeys(main + other))
        atoms, todo = set(), list(self.main)
        while todo:
            a = todo.pop()
            if a in atoms: continue
            atoms.add(a)
            u = unfold(a)
            if u is not None: todo.extend(atoms_in(u) - atoms)
        self.atoms = atoms
        self.tags = {lang_of_atom(a) for a in atoms} | {L}
        ax = []
        for a in sorted(atoms):
            u = unfold(a)
            if u is not None: ax.append(("Unf", Iff(a, u)))
        self.targets = list(dict.fromkeys(And(p, q) for p in main for q in other))
        self.fps = [FP(L, T, gg) for T in self.targets for gg in IDX]
        for f in self.fps:
            _, _, T, gg = f
            inner = Imp(Box(0, L, gg, f), T)
            ax.append(("FP", Iff(f, inner)))
            for n in IDX:
                ax.append(("FPBox", Imp(Box(0, L, n, f), Box(0, L, n, inner))))
                ax.append(("KFP", Imp(And(Box(0, L, n, inner), Box(0, L, n, Box(0, L, gg, f))), Box(0, L, n, T))))
                ax.append(("Four", Imp(Box(0, L, n, f), Box(0, L, succ(n), Box(0, L, n, f)))))
        for a in sorted(atoms):
            phi = unfold(a)
            if phi is None or phi in (TOP, BOT) or not box_positive(phi): continue
            lam = lang_of_atom(a)
            mx_i = max(b[3] for b in boxes_in(phi))
            for t in (0, 1):
                for n in IDX:
                    if n == INF or n > mx_i:
                        ax.append(("Sigma1", Imp(phi, Box(t, lam, n, phi))))
                    ax.append(("UnfBox", Iff(Box(t, lam, n, phi), Box(t, lam, n, a))))
        self.base_ax = ax
        contents = {}
        for _, f in ax:
            for b in boxes_in(f):
                contents.setdefault(b[2], set()).add(b[4])
        for lam in self.tags: contents.setdefault(lam, set()).add(BOT)
        bg = self._background()
        ent = []
        for lam, cs in contents.items():
            bf = sorted(c for c in cs if box_free(c))
            for s in bf:
                prem = []
                for p in bf:
                    if p != s and _entails(bg, [p], s): prem.append((p,))
                singles = {p for (p,) in prem}
                for i, p in enumerate(bf):
                    for q in bf[i + 1:]:
                        if p in singles or q in singles or s in (p, q): continue
                        if _entails(bg, [p, q], s): prem.append((p, q))
                for pr in prem:
                    for t in (0, 1):
                        for n in IDX:
                            ent.append(("Ent", Imp(And(*[Box(t, lam, n, x) for x in pr]), Box(t, lam, n, s))))
        ax += ent
        fam = set()
        for _, f in ax:
            for b in boxes_in(f): fam.add((b[2], b[4]))
        for lam, phi in fam:
            for n in IDX:
                for t in (0, 1):
                    if n != INF: ax.append(("Mono", Imp(Box(t, lam, n, phi), Box(t, lam, succ(n), phi))))
                ax.append(("Incl", Imp(Box(0, lam, n, phi), Box(1, lam, n, phi))))
        self.axioms = {0: list(ax), 1: list(ax) + [("Con", Not(Box(0, lam, INF, BOT))) for lam in self.tags]}
        self.boxvars = sorted({b for _, f in self.axioms[1] for b in boxes_in(f)}, key=repr)
        self.contents = sorted({b[4] for b in self.boxvars if b[2] == L}, key=repr)
        self.levels, self.cnf, self.solver, self.mem, self.nec = {}, {}, {}, {}, {}
        self._stable = None

    def _background(self):
        """Each program outputs exactly one action; constant programs' outputs (box-free Unf)."""
        bg, groups = [], {}
        for a in self.atoms: groups.setdefault(a[1:3], []).append(a)
        for (X, Y) in groups:
            xs = [Atom(X, Y, i) for i in range(len(ACTS))]
            bg.append(Or(*xs))
            for i in range(len(xs)):
                for j in range(i + 1, len(xs)): bg.append(Not(And(xs[i], xs[j])))
        for a in self.atoms:
            u = unfold(a)
            if u is not None and box_free(u): bg.append(Iff(a, u))
        return bg

    def nec_facts(self, h):
        if h in self.nec: return self.nec[h]
        out = set()
        for b in self.boxvars:
            _, s, lam, n, phi = b
            sysl = self if lam == self.L else system(lam)
            if n != INF:
                if n < h and sysl.member(s, n, phi): out.add(b)
            elif h >= 1 and sysl.member(s, h - 1, phi): out.add(b)
        self.nec[h] = frozenset(out)
        return self.nec[h]
    def stable(self):
        if self._stable is None:
            h = K + 1
            while self.nec_facts(h + 1) != self.nec_facts(h):
                h += 1
                assert h < 60, "no stabilisation"
            self._stable = h
        return self._stable
    def _solver(self, t, h):
        key = (t, h)
        if key not in self.solver:
            cnf = CNF()
            for _, f in self.axioms[t]: cnf.assert_(f)
            for b in self.boxvars:
                if b[2] == self.L: cnf.lit(b[4])
            for b in self.nec_facts(h): cnf.assert_(b)
            self.cnf[key] = cnf
            self.solver[key] = Solver(cnf.n, cnf.clauses)
            assert self.solver[key].solve() is not None, f"inconsistent system t={t} h={h}"
        return self.cnf[key], self.solver[key]
    def level(self, t, h):
        key = (t, h)
        if key in self.levels: return self.levels[key]
        cnf, sol = self._solver(t, h)
        known = set(self.levels.get((t, h - 1), ())) if h > 0 else set()
        if t == 1: known |= self.level(0, h)
        m = sol.solve()
        cand = [c for c in self.contents if c not in known and _true(m, cnf.lit(c))]
        mem = set(known)
        while cand:
            c = cand.pop()
            r = sol.solve([-cnf.lit(c)])
            if r is None: mem.add(c)
            else: cand = [d for d in cand if _true(r, cnf.lit(d))]
        self.levels[key] = frozenset(mem)
        del self.solver[key], self.cnf[key]
        return self.levels[key]
    def member(self, t, h, phi):
        """Is phi derivable in theory t of this system with necessitation height <= h?"""
        if h == INF: h = self.stable()
        elif self._stable is not None and h > self._stable: h = self._stable
        if phi in self.contents: return phi in self.level(t, h)
        key = (t, h, phi)
        if key in self.mem: return self.mem[key]
        if t == 1 and self.mem.get((0, h, phi)): res = True
        elif h > 0 and self.mem.get((t, h - 1, phi)): res = True
        else:
            cnf, sol = self._solver(t, h)
            lit = cnf.lit(phi)
            if lit > sol.n:
                sol = self.solver[(t, h)] = Solver(cnf.n, cnf.clauses)
            res = sol.solve([-lit]) is None
        self.mem[key] = res
        return res

def _true(model, lit): return (model[abs(lit)] > 0) == (lit > 0)

def _entails(bg, prem, s):
    ats = set().union(*[atoms_in(f) for f in prem + [s]])
    ats |= {Atom(a[1], a[2], i) for a in ats for i in range(len(ACTS))}
    rel = [f for f in bg if atoms_in(f) <= ats]
    ats = sorted(ats)
    for vals in product((False, True), repeat=len(ats)):
        v = dict(zip(ats, vals))
        if all(ev(f, v) for f in rel + prem) and not ev(s, v): return False
    return True

def ev(f, v):
    k = f[0]
    if k == "top": return True
    if k == "bot": return False
    if k == "not": return not ev(f[1], v)
    if k == "and": return all(ev(x, v) for x in f[1:])
    if k == "or": return any(ev(x, v) for x in f[1:])
    return v[f]

# ---------------------------------------------------------------- deciding
def eval_cond(c, log=None):
    k = c[0]
    if k == "box":
        _, t, L, n, phi = c
        res = system(L).member(t, n, phi)
        if log is not None: log.append((c, res))
        return res
    if k == "not": return not eval_cond(c[1], log)
    if k == "and": return all(eval_cond(x, log) for x in c[1:])
    if k == "or": return any(eval_cond(x, log) for x in c[1:])
    if k == "top": return True
    if k == "bot": return False
    raise ValueError(c)

def decide(opp_src, log=None):
    X, Y = token(SELF), token(opp_src)
    me = analyse(X)
    assert me is not None and me[0] == "DL", "cannot read my own source"
    _, rules, default = me
    for c, a in rules:
        if eval_cond(_resolve_c(c, X, Y), log): return ACTS[a]
    return ACTS[default]

if __name__ == "__main__":
    sys.stdout.write(decide(sys.stdin.read()) + "\n")
