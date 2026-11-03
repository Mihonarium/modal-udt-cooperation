"""Exact evaluator for modal agents in finite 2-player games.

Semantics (Barasz et al. 2014, Sec. 4, Thm 4.7; Kripke chain for GL):
  levels n = 0, 1, 2, ...; level n "sees" every level m < n.
  Box(k, phi) is provability in PA+k:  true at level n  iff  phi is true at every
  level m with k <= m < n  (vacuously true when n <= k).
Every agent's choice is a decision list "if Box-cond_1 then a_1 elif ... else default",
with every letter inside a box (fully modalised), so the values at level n depend only
on levels < n and the forward pass gives the unique fixed point on the chain.
A closed GL formula is eventually constant along the chain, and its eventual value is
its truth value in the standard model (when PA is sound); we read actions off there.
"""
from itertools import product

# ---------------- formulas ----------------
class F:
    pass

class Top(F):
    def ev(self, val, n, memo): return True
class Bot(F):
    def ev(self, val, n, memo): return False
class Var(F):
    def __init__(self, key, a): self.key, self.a = key, a
    def ev(self, val, n, memo): return val[n][self.key] == self.a
class Not(F):
    def __init__(self, x): self.x = x
    def ev(self, val, n, memo): return not self.x.ev(val, n, memo)
class And(F):
    def __init__(self, *xs): self.xs = xs
    def ev(self, val, n, memo): return all(x.ev(val, n, memo) for x in self.xs)
class Or(F):
    def __init__(self, *xs): self.xs = xs
    def ev(self, val, n, memo): return any(x.ev(val, n, memo) for x in self.xs)
def Imp(a, b): return Or(Not(a), b)
class Box(F):
    """Provable in PA+k."""
    def __init__(self, x, k=0): self.x, self.k = x, k
    def ev(self, val, n, memo):
        # memoised running AND over levels k..n-1
        key = (id(self), n)
        if key in memo: return memo[key]
        if n <= self.k: r = True
        else: r = Box.ev(self, val, n - 1, memo) and self.x.ev(val, n - 1, memo)
        memo[key] = r
        return r

def fully_modalised(f, inside=False):
    if isinstance(f, Var): return inside
    if isinstance(f, (Top, Bot)): return True
    if isinstance(f, Box): return fully_modalised(f.x, True)
    if isinstance(f, Not): return fully_modalised(f.x, inside)
    return all(fully_modalised(x, inside) for x in f.xs)

# ---------------- games ----------------
class Game:
    def __init__(self, name, acts, U):
        """acts = (row actions, col actions); U[(i,j)] = (row payoff, col payoff)."""
        self.name, self.acts, self.U = name, acts, U
    def u(self, role, mine, theirs):
        i, j = (mine, theirs) if role == 0 else (theirs, mine)
        return self.U[(i, j)][role]
    def n(self, role): return len(self.acts[role])

# ---------------- agents ----------------
# A pair key is (agent, opponent, role): the action `agent` plays in `role` against `opponent`.
# An agent's program gets (game, role, me_key, opp_key) and returns (decision list, default)
# where the decision list is [(fully modalised condition, action index), ...].
# It may also refer to the opponent's play against lower-rank agents via opp_vs(Z).

class Agent:
    def __init__(self, name): self.name = name
    def __repr__(self): return self.name

class Const(Agent):
    def __init__(self, a, name=None):
        super().__init__(name or f"Const{a}"); self.a = a
    def program(self, g, role, me, opp, ctx): return [], self.a

class FairBot(Agent):
    """Play my part of target iff PA proves the opponent plays its part against me; else fallback.
    PD: target (C,C), fallback D  ->  [FB(X)=C] <-> Box[X(FB)=C]."""
    def __init__(self, target=None, fallback=None, name="FB"):
        super().__init__(name); self.target, self.fallback = target, fallback
    def program(self, g, role, me, opp, ctx):
        t = self.target or ctx.coop_target(g); f = self.fallback or ctx.fallback(g)
        return [(Box(Var(opp, t[1 - role])), t[role])], f[role]

class PrudentBot(Agent):
    """PD: [PB(X)] <-> Box[X(PB)=C] & Box_1 not[X(DB)=C]  (DB = constant fallback bot)."""
    def __init__(self, name="PB"): super().__init__(name)
    def program(self, g, role, me, opp, ctx):
        t = ctx.coop_target(g); f = ctx.fallback(g)
        db = ctx.const(f[role])
        opp_vs_db = ctx.key(opp[0], db, 1 - role)
        cond = And(Box(Var(opp, t[1 - role])), Box(Not(Var(opp_vs_db, t[1 - role])), 1))
        return [(cond, t[role])], f[role]

class ModalUDT(Agent):
    """Reverse-utility-order agent.  For (u, a) in `order`: if PA+k proves
    "I play a -> my payoff >= u" (or "== u" when exact=True), play a; else default.
    order: 'util-major' (u best->worst, then actions in action_order),
           'action-major' (actions in action_order, then u best->worst).
    chicken: prefix "if PA proves I don't play a, play a" for each a (Slepnev/chicken rule).
    strat: the i-th check (0-based) uses PA+i instead of PA (stratified proof strength)."""
    def __init__(self, name="UDT", default=None, exact=False, order="util-major",
                 action_order=None, chicken=False, strat=False):
        super().__init__(name)
        self.default, self.exact, self.order = default, exact, order
        self.action_order, self.chicken, self.strat = action_order, chicken, strat
    def program(self, g, role, me, opp, ctx):
        nA, nB = g.n(role), g.n(1 - role)
        acts = self.action_order(nA) if callable(self.action_order) else (self.action_order or list(range(nA)))
        utils = sorted({g.u(role, a, b) for a in range(nA) for b in range(nB)}, reverse=True)
        pairs = ([(u, a) for u in utils for a in acts] if self.order == "util-major"
                 else [(u, a) for a in acts for u in utils])
        dl = []
        if self.chicken:
            dl += [(Box(Not(Var(me, a))), a) for a in acts]
        for i, (u, a) in enumerate(pairs):
            good = [b for b in range(nB) if (g.u(role, a, b) == u if self.exact else g.u(role, a, b) >= u)]
            cons = Or(*[Var(opp, b) for b in good]) if good else Bot()
            dl.append((Box(Imp(Var(me, a), cons), i if self.strat else 0), a))
        d = self.default if self.default is not None else 0
        if callable(d): d = d(g, role)
        return dl, d

# ---------------- evaluation ----------------
class Ctx:
    def __init__(self, game, coop_target, fallback):
        self.game = game; self._ct, self._fb = coop_target, fallback
        self.consts = {}
    def coop_target(self, g): return self._ct
    def fallback(self, g): return self._fb
    def const(self, a):
        if a not in self.consts: self.consts[a] = Const(a, f"Const{a}")
        return self.consts[a]
    def key(self, A, B, role): return (A, B, role)

def play(game, X, Y, ctx, N=80, trace=False):
    """X in row (role 0), Y in column (role 1). Returns (row action, col action, stab level, full info)."""
    progs = {}
    todo = [(X, Y, 0), (Y, X, 1)]
    while todo:
        k = todo.pop()
        if k in progs: continue
        A, B, r = k
        dl, d = A.program(game, r, k, (B, A, 1 - r), ctx)
        for c, _ in dl:
            assert fully_modalised(c), (A, "not fully modalised")
        progs[k] = (dl, d)
        for c, _ in dl:
            for v in vars_of(c):
                if v not in progs: todo.append(v)
    val = []
    memo = {}
    for n in range(N):
        row = {}
        val.append(row)  # Box at level n only reads levels < n
        for k, (dl, d) in progs.items():
            act = d
            for c, a in dl:
                if c.ev(val, n, memo): act = a; break
            row[k] = act
    main = [(X, Y, 0), (Y, X, 1)]
    seq = [tuple(val[n][k] for k in main) for n in range(N)]
    # stabilisation level of the whole system
    allseq = [tuple(sorted(((repr(k), v) for k, v in val[n].items()))) for n in range(N)]
    stab = N - 1
    while stab > 0 and allseq[stab - 1] == allseq[N - 1]: stab -= 1
    assert stab < N // 2, f"not stabilised by level {N//2}: {X} vs {Y} in {game.name}"
    if trace: return seq, stab
    return seq[-1][0], seq[-1][1], stab

def vars_of(f):
    if isinstance(f, Var): yield f.key
    elif isinstance(f, (Top, Bot)): return
    elif isinstance(f, (Box, Not)): yield from vars_of(f.x)
    else:
        for x in f.xs: yield from vars_of(x)
