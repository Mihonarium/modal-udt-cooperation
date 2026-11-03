"""Runnable bounded proof-based bots.

A bot is a program given as SOURCE TEXT. Run against an opponent's source text, it builds a formal
system from the two sources, searches that system for proofs of bounded size, and acts on what it finds.
Nothing is evaluated "ideally": every action printed by this file is the output of a terminating search.

The formal system (BPC, "bounded provability calculus"; full statement in README "Bounded agents"):
  language   propositional formulas over
               action atoms   [X|Y|r=a]  "program X, playing role r against program Y, outputs a"
               box atoms      Box(t, L, n, phi)  "phi has a T_t^L-derivation of height <= n"
                              (t = 0: the base theory; t = 1: base + consistency axioms, the analogue of PA+1;
                               L = the match system that is meant; n in {0..K} or inf)
               fixed points   psi(L, T, g) with defining axiom  psi <-> (Box(0, L, g, psi) -> T)
  axioms     (all are true statements about these programs and this calculus; README gives the argument)
    Unf      [X|Y|r=a] <-> condition under which X's decision list returns a against Y, read off X's source
    FP       the fixed-point definitions (Loeb-shaped only: T ranges over the joint actions of the match)
    Mono     Box(t,L,n,p) -> Box(t,L,n+1,p),  Box(t,L,K,p) -> Box(t,L,inf,p)
    Incl     Box(0,L,n,p) -> Box(1,L,n,p)
    Four     Box(0,L,n,psi) -> Box(0,L,n+1,Box(0,L,n,psi))                     (for fixed points psi)
    FPBox    Box(0,L,n,psi) -> Box(0,L,n,Box(0,L,g,psi) -> T)
    KFP      Box(0,L,n,Box(0,L,g,psi) -> T) & Box(0,L,n,Box(0,L,g,psi)) -> Box(0,L,n,T)
    Sigma1   Phi -> Box(t,L,m,Phi) for a box-positive Unf condition Phi whose boxes have index < m
    UnfBox   Box(t,L,n,Phi) <-> Box(t,L,n,[X|Y|r=a])  for such Phi = the Unf condition of [X|Y|r=a]
    Ent      Box(t,L,n,p) & Box(t,L,n,q) -> Box(t,L,n,s)  for box-free p, q, s with B, p, q |= s
             (B = "each program outputs exactly one action" + the constant programs' outputs)
    Con      (theory 1 only) not Box(0,L,inf,False) for every match system L mentioned
  rules      propositional consequence (free) and necessitation: from a derivation of phi of height h,
             infer Box(t,L,n,phi) for any n >= h, at height h+1.
  measure    height = the largest number of nested necessitations. NOT Critch's character count.

Necessitation is restricted to the finite set of formulas that occur inside boxes of the system, and fixed
points exist only in the Loeb shape above. With those two restrictions the set of formulas derivable at each
height is finite and is computed EXACTLY (by a SAT solver below), so the search is complete for this system.
"""
import ast, sys
from functools import lru_cache
from itertools import product

INF = 10 ** 9
K = 4                       # largest finite box index in the language (budgets 0..K or inf)
IDX = list(range(K + 1)) + [INF]
def succ(n): return n + 1 if n < K else INF
def idx_str(n): return "inf" if n == INF else str(n)

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
def Atom(game, X, Y, r, a): return ("atom", game, X, Y, r, a)
def Box(t, L, n, phi): return ("box", t, L, n, phi)
def FP(L, T, g): return ("fp", L, T, g)

def subformulas(f, acc=None):
    acc = set() if acc is None else acc
    if f in acc: return acc
    acc.add(f)
    if f[0] in ("not", "and", "or"):
        for x in f[1:]: subformulas(x, acc)
    return acc
def boxes_in(f):
    return {s for s in subformulas(f) if s[0] == "box"}
def atoms_in(f, deep=True):
    """Action atoms in f (deep=True also looks inside boxes and fixed-point targets)."""
    out, stack, seen = set(), [f], set()
    while stack:
        g = stack.pop()
        if g in seen: continue
        seen.add(g)
        if g[0] == "atom": out.add(g)
        elif g[0] in ("not", "and", "or"): stack.extend(g[1:])
        elif deep and g[0] == "box": stack.append(g[4])
        elif deep and g[0] == "fp": stack.append(g[2])
    return out
def box_free(f): return not any(s[0] in ("box", "fp") for s in subformulas(f))
def box_positive(f):
    """Built from boxes with and/or only (so it is a Sigma_1-style statement)."""
    if f[0] == "box": return True
    if f[0] in ("and", "or"): return all(box_positive(x) for x in f[1:])
    return False

def show(f):
    k = f[0]
    if k == "top": return "T"
    if k == "bot": return "F"
    if k == "atom":
        _, game, X, Y, r, a = f
        return f"[{name_of(X)}|{name_of(Y)}={GAMES[game].acts[r][a]}]"
    if k == "not": return "~" + show(f[1])
    if k == "and": return "(" + " & ".join(show(x) for x in f[1:]) + ")"
    if k == "or":
        # print a -> b for (~a | b)
        return "(" + " | ".join(show(x) for x in f[1:]) + ")"
    if k == "box": return f"Box{'+1' if f[1] else ''}_{idx_str(f[3])}{show(f[4])}"
    if k == "fp": return f"psi[{show(f[2])},g={idx_str(f[3])}]"
    return str(f)

# ---------------------------------------------------------------- games and programs
class Game:
    def __init__(self, name, acts, U):
        self.name, self.acts, self.U = name, acts, U
    def u(self, role, mine, theirs):
        i, j = (mine, theirs) if role == 0 else (theirs, mine)
        return self.U[(i, j)][role]
    def n(self, role): return len(self.acts[role])
GAMES = {}
def register(g): GAMES[g.name] = g; return g
def pd(T=3, R=2, P=1, S=0, name=None):
    name = name or f"PD{T}/{R}/{P}/{S}"
    return register(Game(name, (["C", "D"], ["C", "D"]),
                         {(0, 0): (R, R), (0, 1): (S, T), (1, 0): (T, S), (1, 1): (P, P)}))
PD = pd(name="PD")

def norm(src): return "\n".join(l.strip() for l in src.strip().splitlines() if l.split("#")[0].strip())
NAMES = {}
def name_of(src):
    return NAMES.get(norm(src), norm(src).replace("\n", "; ")[:30])
def const_src(a): return f"{a} otherwise"

def fairbot(k):
    s = f"C if prove(0, {idx_str(k)}, opp(self) == C)\nD otherwise"
    NAMES[norm(s)] = f"FB{idx_str(k)}"; return s
def prudentbot(k):
    s = f"C if prove(0, {idx_str(k)}, opp(self) == C) and prove(1, {idx_str(k)}, opp(CONST_D) != C)\nD otherwise"
    NAMES[norm(s)] = f"PB{idx_str(k)}"; return s
def v4bot(k, probe=1):
    s = f"V4 budget={idx_str(k)} probe={probe}"
    NAMES[norm(s)] = f"V4_{idx_str(k)}" + ("" if probe == 1 else f"p{probe}"); return s
CB, DB = const_src("C"), const_src("D")
NAMES[CB], NAMES[DB] = "CB", "DB"

# Abstract formulas inside a program: ("eq", Xref, Yref, action name), refs are "self", "opp", ("const", a);
# conditions: ("prove", t, n, F), and/or/not, True/False.
def _n(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int): return node.value
    if isinstance(node, ast.Name) and node.id == "inf": return INF
    raise SyntaxError("budget must be an integer or inf")
def _ref(node):
    if not isinstance(node, ast.Name): raise SyntaxError("program reference must be a name")
    if node.id in ("self", "opp"): return node.id
    if node.id.startswith("CONST_"): return ("const", node.id[6:])
    raise SyntaxError(f"unknown program {node.id}")
def _formula(node):
    if isinstance(node, ast.BoolOp):
        return ("and" if isinstance(node.op, ast.And) else "or",) + tuple(_formula(v) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return ("not", _formula(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "implies":
        return ("or", ("not", _formula(node.args[0])), _formula(node.args[1]))
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        call, op, act = node.left, node.ops[0], node.comparators[0]
        if not (isinstance(call, ast.Call) and len(call.args) == 1 and isinstance(act, ast.Name)):
            raise SyntaxError("expected X(Y) == a")
        eq = ("eq", _ref(call.func), _ref(call.args[0]), act.id)
        if isinstance(op, ast.Eq): return eq
        if isinstance(op, ast.NotEq): return ("not", eq)
    raise SyntaxError(f"unsupported formula {ast.dump(node)}")
def _cond(node):
    if isinstance(node, ast.BoolOp):
        return ("and" if isinstance(node.op, ast.And) else "or",) + tuple(_cond(v) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return ("not", _cond(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "prove":
        t, n, F = node.args
        if not (isinstance(t, ast.Constant) and t.value in (0, 1)): raise SyntaxError("theory must be 0 or 1")
        return ("prove", t.value, _n(n), _formula(F))
    raise SyntaxError(f"unsupported condition {ast.dump(node)}")

@lru_cache(maxsize=None)
def parse(src):
    lines = norm(src).splitlines()
    if lines[0].startswith("V4"):
        kw = dict(p.split("=") for p in lines[0].split()[1:])
        return ("V4", _n(ast.parse(kw.get("budget", "inf"), mode="eval").body), int(kw.get("probe", 1)))
    rules, default = [], None
    for l in lines:
        act, rest = l.split(None, 1)
        if rest == "otherwise": default = act
        elif rest.startswith("if "): rules.append((_cond(ast.parse(rest[3:], mode="eval").body), act))
        else: raise SyntaxError(l)
    if default is None: raise SyntaxError("missing 'otherwise' line")
    return ("DL", tuple(rules), default)

def v4_rules(g, role, k, probe):
    """V4 (see v4.py) read off the payoff matrix: returns rules with action NAMES, as a parsed program."""
    nA, nB = g.n(role), g.n(1 - role)
    A, B = g.acts[role], g.acts[1 - role]
    U = lambda a, b: g.u(role, a, b); V = lambda a, b: g.u(1 - role, b, a)
    mm = lambda r: max(min(g.u(r, x, y) for y in range(g.n(1 - r))) for x in range(g.n(r)))
    m_me, m_op = mm(role), mm(1 - role)
    best = lambda b: max(range(nA), key=lambda x: (U(x, b), -x))
    groups = {"coop": [], "neutral": [], "exploit": []}
    for a in range(nA):
        for b in range(nB):
            u, v = U(a, b), V(a, b)
            if u < m_me: continue
            t = "exploit" if v < m_op else ("coop" if (u > m_me or v > m_op) else "neutral")
            groups[t].append((u, a, b))
    def ge(a, u, theory):
        good = [("eq", "opp", "self", B[y]) for y in range(nB) if U(a, y) >= u]
        return ("prove", theory, k, ("or", ("not", ("eq", "self", "opp", A[a])), ("or",) + tuple(good)))
    rules, seen = [], set()
    for u, a, b in sorted(groups["coop"], key=lambda c: (-c[0], c[1], c[2])):
        ax = best(b)
        if U(ax, b) > U(a, b):
            pr = ("prove", probe, k, ("not", ("eq", "opp", ("const", A[ax]), B[b])))
            rules.append((("and", ge(a, u, 0), pr), A[a]))
        else:
            rules.append((ge(a, u, 0), A[a]))
    for grp, th in (("exploit", 1), ("neutral", 0)):
        for u, a, b in sorted(groups[grp], key=lambda c: (-c[0], c[1])):
            if (u, a, th) in seen: continue
            seen.add((u, a, th)); rules.append((ge(a, u, th), A[a]))
    maxmin_a = max(range(nA), key=lambda x: (min(U(x, y) for y in range(nB)), -x))
    return ("DL", tuple(rules), A[maxmin_a])

@lru_cache(maxsize=None)
def compiled(game, src, role):
    """The program's decision list for (game, role): [(abstract condition, action index)], default index."""
    g = GAMES[game]
    p = parse(src)
    if p[0] == "V4": p = v4_rules(g, role, p[1], p[2])
    _, rules, default = p
    return tuple((c, g.acts[role].index(a)) for c, a in rules), g.acts[role].index(default)

def lang(game, X, Y, r):
    """Canonical name of the match system for X (role r) vs Y."""
    X, Y = norm(X), norm(Y)
    return min((game, X, Y, r), (game, Y, X, 1 - r))

def _resolve_f(F, game, X, Y, r):
    k = F[0]
    if k == "eq":
        _, xr, yr, a = F
        src = lambda ref: X if ref == "self" else Y if ref == "opp" else const_src(ref[1])
        rx = r if xr == "self" else 1 - r if xr == "opp" else None
        ry = r if yr == "self" else 1 - r if yr == "opp" else None
        if rx is None: rx = 1 - ry if ry is not None else 0
        return Atom(game, norm(src(xr)), norm(src(yr)), rx, GAMES[game].acts[rx].index(a))
    if k == "not": return Not(_resolve_f(F[1], game, X, Y, r))
    if k == "and": return And(*[_resolve_f(x, game, X, Y, r) for x in F[1:]])
    if k == "or": return Or(*[_resolve_f(x, game, X, Y, r) for x in F[1:]])
    raise ValueError(F)
def _resolve_c(c, game, X, Y, r):
    k = c[0]
    if k == "prove":
        _, t, n, F = c
        return Box(t, lang(game, X, Y, r), n, _resolve_f(F, game, X, Y, r))
    if k == "not": return Not(_resolve_c(c[1], game, X, Y, r))
    if k == "and": return And(*[_resolve_c(x, game, X, Y, r) for x in c[1:]])
    if k == "or": return Or(*[_resolve_c(x, game, X, Y, r) for x in c[1:]])
    raise ValueError(c)

@lru_cache(maxsize=None)
def unfold(atom):
    """Unf: the condition (in boxes) under which X's program returns action a against Y."""
    _, game, X, Y, r, a = atom
    rules, default = compiled(game, X, r)
    conds = [(_resolve_c(c, game, X, Y, r), b) for c, b in rules]
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
                f = -trail[q]; q += 1           # literal f became false
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

# ---------------------------------------------------------------- the match system
SYSTEMS = {}
def system(L):
    if L not in SYSTEMS: SYSTEMS[L] = System(L)
    return SYSTEMS[L]
def lang_of_atom(a): return lang(a[1], a[2], a[3], a[4])

class System:
    """BPC for one match: language generated by the two sources, axioms, exact derivability by height."""
    def __init__(self, L):
        self.L = L
        game, X, Y, r = L
        g = GAMES[game]
        self.main = [Atom(game, X, Y, r, a) for a in range(g.n(r))] + \
                    [Atom(game, Y, X, 1 - r, b) for b in range(g.n(1 - r))]
        # closure of atoms under unfolding
        atoms, todo = set(), list(self.main)
        while todo:
            a = todo.pop()
            if a in atoms: continue
            atoms.add(a)
            todo.extend(atoms_in(unfold(a)) - atoms)
        self.atoms = atoms
        self.tags = {lang_of_atom(a) for a in atoms} | {L}
        ax = []                                    # axioms common to both theories
        for a in sorted(atoms):
            ax.append(("Unf", Iff(a, unfold(a))))
        # fixed points (Loeb-shaped) for joint actions of the match
        mx = [x for x in self.main if x[4] == r and x[2] == X]
        my = [x for x in self.main if not (x[4] == r and x[2] == X)]
        self.targets = [And(p, q) for p in mx for q in my]
        self.fps = [FP(L, T, gg) for T in self.targets for gg in IDX]
        for f in self.fps:
            _, _, T, gg = f
            inner = Imp(Box(0, L, gg, f), T)
            ax.append(("FP", Iff(f, inner)))
            for n in IDX:
                ax.append(("FPBox", Imp(Box(0, L, n, f), Box(0, L, n, inner))))
                ax.append(("KFP", Imp(And(Box(0, L, n, inner), Box(0, L, n, Box(0, L, gg, f))), Box(0, L, n, T))))
                ax.append(("Four", Imp(Box(0, L, n, f), Box(0, L, succ(n), Box(0, L, n, f)))))
        # Sigma1 / UnfBox for atoms whose condition is box-positive
        for a in sorted(atoms):
            phi = unfold(a)
            if phi in (TOP, BOT) or not box_positive(phi): continue
            lam = lang_of_atom(a)
            mx_i = max(b[3] for b in boxes_in(phi))
            for t in (0, 1):
                for n in IDX:
                    if n == INF or n > mx_i:
                        ax.append(("Sigma1", Imp(phi, Box(t, lam, n, phi))))
                    ax.append(("UnfBox", Iff(Box(t, lam, n, phi), Box(t, lam, n, a))))
        # Ent: two-premise entailments between box-free contents, per tag
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
        # Mono and Incl for every box family that occurs
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
        self.levels = {}
        self.cnf = {}
        self.solver = {}
        self.mem = {}
        self.nec = {}
        self._stable = None

    def _background(self):
        """'Each program outputs exactly one action' and the constant programs' outputs (box-free Unf)."""
        bg = []
        groups = {}
        for a in self.atoms: groups.setdefault(a[:5], []).append(a)
        for k, xs in groups.items():
            n = GAMES[k[1]].n(k[4])
            xs = [Atom(*k[1:5], i) for i in range(n)]
            bg.append(Or(*xs))
            for i in range(n):
                for j in range(i + 1, n): bg.append(Not(And(xs[i], xs[j])))
        for a in self.atoms:
            u = unfold(a)
            if box_free(u): bg.append(Iff(a, u))
        return bg

    # ---- heights
    def nec_facts(self, h):
        """Box atoms made true by necessitation in derivations of height <= h."""
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
                if b[2] == self.L: cnf.lit(b[4])          # encode own contents up front
            for b in self.nec_facts(h): cnf.assert_(b)
            self.cnf[key] = cnf
            self.solver[key] = Solver(cnf.n, cnf.clauses)
            assert self.solver[key].solve() is not None, f"inconsistent system {self.L} t={t} h={h}"
        return self.cnf[key], self.solver[key]
    def level(self, t, h):
        """All own contents derivable in theory t at height <= h (exact; SAT models prune candidates)."""
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
        del self.solver[key], self.cnf[key]            # keep memory small; rebuilt on demand
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
            if lit > sol.n:                   # new Tseitin variables: rebuild solver with them
                sol = self.solver[(t, h)] = Solver(cnf.n, cnf.clauses)
            res = sol.solve([-lit]) is None
        self.mem[key] = res
        return res

def _true(model, lit): return (model[abs(lit)] > 0) == (lit > 0)

def _entails(bg, prem, s):
    """Truth-table check: bg + prem |= s (all box-free)."""
    ats = set().union(*[atoms_in(f) for f in prem + [s]])
    ats |= {Atom(*a[1:5], i) for a in ats for i in range(GAMES[a[1]].n(a[4]))}   # action siblings
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

# ---------------------------------------------------------------- the bots
def act(game, X, Y, role, log=None):
    """Run program X (source text) in `role` against program Y (source text). Returns an action index.
    This is the bot itself: it parses its own source and the opponent's, and decides each prove(t, n, F)
    by the exact bounded search of the match system."""
    game = game if isinstance(game, str) else game.name
    X, Y = norm(X), norm(Y)
    rules, default = compiled(game, X, role)
    for c, a in rules:
        if _eval_cond(_resolve_c(c, game, X, Y, role), log):
            return a
    return default
def _eval_cond(c, log):
    k = c[0]
    if k == "box":
        _, t, L, n, phi = c
        res = system(L).member(t, n, phi)
        if log is not None: log.append((c, res))
        return res
    if k == "not": return not _eval_cond(c[1], log)
    if k == "and": return all(_eval_cond(x, log) for x in c[1:])
    if k == "or": return any(_eval_cond(x, log) for x in c[1:])
    if k == "top": return True
    if k == "bot": return False
    raise ValueError(c)

def play(game, X, Y):
    """X in role 0, Y in role 1."""
    return act(game, X, Y, 0), act(game, Y, X, 1)

# ---------------------------------------------------------------- soundness audit
def truth(f):
    """Truth of a formula in the actual world: atoms = the programs' real outputs, boxes = real derivability."""
    k = f[0]
    if k == "top": return True
    if k == "bot": return False
    if k == "atom":
        _, game, X, Y, r, a = f
        return act(game, X, Y, r) == a
    if k == "box":
        _, t, L, n, phi = f
        return system(L).member(t, n, phi)
    if k == "fp":
        _, L, T, g = f
        return (not system(L).member(0, g, f)) or truth(T)
    if k == "not": return not truth(f[1])
    if k == "and": return all(truth(x) for x in f[1:])
    if k == "or": return any(truth(x) for x in f[1:])
    raise ValueError(f)
def audit(L):
    """Check that every axiom of system L (both theories) is true in the actual world. Returns failures."""
    S = system(L)
    return [(name, show(f)) for name, f in S.axioms[1] if not truth(f)]

if __name__ == "__main__":
    srcs = sys.argv[1:3] if len(sys.argv) >= 3 else [fairbot(2), fairbot(2)]
    a, b = play("PD", *srcs)
    print(name_of(srcs[0]), "vs", name_of(srcs[1]), "->", PD.acts[0][a] + PD.acts[1][b])
