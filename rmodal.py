"""Exact evaluator for modal agents with an outside source of randomness.

Same GL/Kripke-chain semantics as modal.py (every closed formula is eventually constant
along the chain; Box_k phi at level n iff phi holds at every level k <= m < n), with one
change: an agent's play is a function of random inputs, which are *free atoms* of the
language.  The random inputs are discretised:

  r_pub  in range(NPUB) : one public draw, seen by both players (for correlated fair points);
  r_c    in range(K)    : a coarse private draw per player (the part of an opponent's private
                          mixing that other agents enumerate when reading its policy);
  r_f    in range(M)    : a fine private draw per player (the "dial" for probabilistic giving-in).

A *key* is (agent, opponent, role, r_pub, r_c, r_f): the action `agent` plays in `role`
against `opponent` when its random inputs are these.  Agents' programs are decision lists
of fully modalised conditions, as in modal.py, but a condition may mention the opponent's
keys at any r (a statement "PA proves the opponent plays b at every value of its private
draw" is a statement about the opponent's policy, which is what the opponent's source
reveals) and the agent's own keys at any r.  An agent's action may not depend on the
opponent's private draws except through what is provable about them, which the keys enforce:
the program for key (X, Y, role, r_pub, r_c, r_f) is a function of r_pub, r_c, r_f only.

The joint play is one fixed point of the whole system (all keys) on the chain, as before.
Expected payoffs average the eventual actions over r_pub and both players' private draws,
all uniform and independent.
"""
from modal import F, Top, Bot, Var, Not, And, Or, Imp, Box, Game, Agent, fully_modalised, vars_of
from itertools import product

class R:
    """Randomness parameters."""
    def __init__(self, npub=10, k=1, m=20): self.npub, self.k, self.m = npub, k, m
    def draws(self): return list(product(range(self.npub), range(self.k), range(self.m)))

class RCtx:
    def __init__(self, game, rnd, fair=None):
        self.game, self.rnd, self.fair = game, rnd, fair
        self.consts = {}
    def const(self, a):
        if a not in self.consts: self.consts[a] = RConst(a, f"Const{a}")
        return self.consts[a]
    def keys(self, base, r_pub=None):
        """All keys of a (agent, opponent, role) base; optionally only those with this r_pub."""
        A, B, role = base
        return [(A, B, role, p, c, f) for (p, c, f) in self.rnd.draws() if r_pub is None or p == r_pub]
    def plays(self, base, policy):
        """Formula: `base` plays policy(r_pub) at every one of its keys (policy ignores private draws)."""
        return And(*[Var(k, policy(k[3])) for k in self.keys(base)])

class RAgent(Agent):
    """program(g, role, base_me, base_opp, r, ctx) -> (decision list, default), r = (r_pub, r_c, r_f)."""
    def program(self, g, role, me, opp, r, ctx): raise NotImplementedError

class RConst(RAgent):
    def __init__(self, a, name=None):
        super().__init__(name or f"Const{a}"); self.a = a
    def program(self, g, role, me, opp, r, ctx): return [], self.a

class RPolicy(RAgent):
    """A stone whose action is a fixed function of (r_pub, r_c, r_f)."""
    def __init__(self, fn, name):
        super().__init__(name); self.fn = fn
    def program(self, g, role, me, opp, r, ctx): return [], self.fn(*r)

class RFairBot(RAgent):
    """Play my part of a target policy iff PA proves the opponent plays its part at every key.
    target: (policy_row, policy_col), each a function of r_pub; fallback: (a_row, a_col)."""
    def __init__(self, target, fallback, name="FB"):
        super().__init__(name); self.target, self.fallback = target, fallback
        self._cache = {}
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._cache:
            self._cache[(me, opp)] = Box(ctx.plays(opp, self.target[1 - role]))
        return [(self._cache[(me, opp)], self.target[role](r[0]))], self.fallback[role]

class RPrudentBot(RAgent):
    """RFairBot plus PA+1 proves the opponent does not play its part against the constant fallback bot."""
    def __init__(self, target, fallback, name="PB"):
        super().__init__(name); self.target, self.fallback = target, fallback
        self._cache = {}
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._cache:
            db = ctx.const(self.fallback[role])
            opp_vs_db = (opp[0], db, 1 - role)
            self._cache[(me, opp)] = And(Box(ctx.plays(opp, self.target[1 - role])),
                                         Box(Not(ctx.plays(opp_vs_db, self.target[1 - role])), 1))
        return [(self._cache[(me, opp)], self.target[role](r[0]))], self.fallback[role]

def rplay(game, X, Y, ctx, N=80, trace=False):
    """X row (role 0), Y column (role 1).  Returns (row policy, col policy, stab, expected payoffs)
    where a policy maps (r_pub, r_c, r_f) -> action (eventual values along the chain)."""
    progs, todo, done, seen = {}, [(X, Y, 0), (Y, X, 1)], set(), set()
    while todo:
        base = todo.pop()
        if base in done: continue
        done.add(base)
        A, B, role = base
        for k in ctx.keys(base):
            dl, d = A.program(game, role, base, (B, A, 1 - role), k[3:], ctx)
            progs[k] = (dl, d)
            for c, _ in dl:
                if id(c) in seen: continue
                seen.add(id(c))
                assert fully_modalised(c), (A, "not fully modalised")
                for v in vars_of(c):
                    if v[:3] not in done: todo.append(v[:3])
    val, memo = [], {}
    for n in range(N):
        row = {}
        val.append(row)
        for k, (dl, d) in progs.items():
            act = d
            for c, a in dl:
                if c.ev(val, n, memo): act = a; break
            row[k] = act
    stab = N - 1
    while stab > 0 and val[stab - 1] == val[N - 1]: stab -= 1
    assert stab < N // 2, f"not stabilised by level {N//2}: {X} vs {Y} in {game.name}"
    last = val[N - 1]
    polX = {k[3:]: last[k] for k in progs if k[:3] == (X, Y, 0)}
    polY = {k[3:]: last[k] for k in progs if k[:3] == (Y, X, 1)}
    ev = expected(game, polX, polY, ctx.rnd)
    if trace:
        seq = [({k[3:]: val[n][k] for k in progs if k[:3] == (X, Y, 0)},
                {k[3:]: val[n][k] for k in progs if k[:3] == (Y, X, 1)}) for n in range(N)]
        return seq, stab
    return polX, polY, stab, ev

def expected(game, polX, polY, rnd):
    """Expected (row, col) payoff: r_pub shared, private draws independent."""
    tot, cnt = [0.0, 0.0], 0
    for p in range(rnd.npub):
        xs = [polX[(p, c, f)] for c in range(rnd.k) for f in range(rnd.m)]
        ys = [polY[(p, c, f)] for c in range(rnd.k) for f in range(rnd.m)]
        for a in xs:
            for b in ys:
                u = game.U[(a, b)]; tot[0] += u[0]; tot[1] += u[1]; cnt += 1
    return (tot[0] / cnt, tot[1] / cnt)

def dist(game, pol, rnd, role):
    """Action distribution of a policy, marginal over everything."""
    n = game.n(role); d = [0] * n
    for v in pol.values(): d[v] += 1
    return [x / len(pol) for x in d]
