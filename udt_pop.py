"""UDT over a population: a payoff-reading agent that derives its policy instead of following a hand-written
decision list.

The agent has a prior over opponent programs and chooses the policy that maximises its prior-expected payoff,
where the payoff of a candidate policy against each opponent is the EXACT fixed point of both programs reasoning
about each other (rmodal.rplay), and where a copy of the agent in the population runs the same candidate
(updateless: "if my program is pi, so is my copy's").  It then plays that policy against the actual opponent.

What is fixed by hand is the *language* of policies: which facts about the opponent the agent can read (the same
provability probes V5 uses) and what it can do in each case.  What the agent decides for itself is the action in
every case: whether to exploit, whether to reciprocate, how often to give in to a commitment and what to do when it
can prove nothing.  Threat-resistance is a conclusion here, with a condition on the prior, not a rule.

Situations (what PA can prove about the opponent), and the policy entry for each:
  ("exploit", b)  opponent plays b at every key against Const_{best response to b}      -> a pure action
  ("recip",)      I play F at all my keys -> opponent plays F at all its keys             -> "F" or a pure action
  ("commit", b)   opponent plays b at every key of this r_pub (a pure commitment)        -> (x, y, j): x when r_f < j else y
  ("unknown",)    nothing above is provable                                              -> (x, y, j)
Checks are read with V5's Con/patience guards and strata, in the order listed.

Prior population (weights are parameters):
  Const_b            a stone committed to b                                   weight w_stone, each b
  Threatener_b       commits to b iff PA+1 proves that the agent's response to a stone committed to b (read as a
                     threshold policy) pays it at least its fair payoff v_F; otherwise it is a copy of the agent
                                                                              weight w_threat, each b
  Mixer_b(rho)       a stone playing b with probability rho using its PRIVATE draw (unreadable: lands in "unknown")
                                                                              weight w_mix, each b and rho
  MixThreatener_b    private mix on b with probability rho iff that provably pays >= v_F against the agent's response
                     to Mixer_b(rho); otherwise a copy of the agent                    weight w_mixthreat
  FairBot-F, PrudentBot-F                                                     weight w_fair each
  a copy of the agent                                                         weight w_copy
F is the discretised Nash bargaining solution (v5.fair_point); it is the population's convention for "fair".
"""
import time
from itertools import product
from rmodal import *
from v5 import fair_point, maxmin_val, V5

class PolicyAgent(RAgent):
    """Reads the situation with V5's probes and plays the table's entry.  tab: situation -> entry."""
    def __init__(self, tab, name="UDT", kmax=6, patience=3, fair=None):
        super().__init__(name); self.tab, self.kmax, self.patience, self.fair = tab, kmax, patience, fair
        self._consts, self._cache, self._fp = {}, {}, {}
    def const(self, a):
        if a not in self._consts: self._consts[a] = RConst(a, f"{self.name}-Ex{a}")
        return self._consts[a]
    def fairpoint(self, g, ctx):
        if g.name not in self._fp: self._fp[g.name] = (self.fair or fair_point)(g, ctx.rnd.npub)
        return self._fp[g.name]
    def build(self, g, role, me, opp, ctx):
        rnd = ctx.rnd; nA, nB = g.n(role), g.n(1 - role)
        U = lambda a, b: g.u(role, a, b)
        pr, pc, uv, _ = self.fairpoint(g, ctx)
        myF, opF = (pr, pc) if role == 0 else (pc, pr); uF = uv[role]
        con = {k: Not(Box(Bot(), k + self.patience)) for k in range(1, self.kmax + 1)}
        conA = {k: Not(Box(Bot(), k + self.patience + 1)) for k in range(1, self.kmax + 1)}
        A = []
        for b in range(nB):
            a = max(range(nA), key=lambda x: (U(x, b), -x))
            if U(a, b) > uF:
                ex = self.const(a)
                for k in range(1, self.kmax + 1):
                    A.append((k, -U(a, b), And(conA[k], Box(ctx.plays((opp[0], ex, 1 - role), lambda p, b=b: b), k)), b))
        A.sort(key=lambda t: t[:2])
        B = Box(Imp(ctx.plays(me, myF), ctx.plays(opp, opF)))
        C = {p: [] for p in range(rnd.npub)}
        for p in range(rnd.npub):
            for b in range(nB):
                body = And(*[Var((opp[0], opp[1], opp[2], p, c, f), b) for c in range(rnd.k) for f in range(rnd.m)])
                for k in range(1, self.kmax + 1):
                    C[p].append((k, And(con[k], Box(body, k)), b))
            C[p].sort(key=lambda t: t[0])
        return dict(A=A, B=B, C=C, myF=myF, nA=nA)
    def entry_action(self, e, p, f, myF):
        if e == "F": return myF(p)
        if isinstance(e, int): return e
        x, y, j = e; return x if f < j else y
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._cache: self._cache[(me, opp)] = self.build(g, role, me, opp, ctx)
        s = self._cache[(me, opp)]; p, c, f = r; myF = s["myF"]
        T = lambda sit: self.tab[(role, sit)]
        dl = [(cond, self.entry_action(T(("exploit", b)), p, f, myF)) for _, _, cond, b in s["A"]]
        dl.append((s["B"], self.entry_action(T(("recip",)), p, f, myF)))
        dl += [(cond, self.entry_action(T(("commit", b)), p, f, myF)) for _, cond, b in s["C"][p]]
        return dl, self.entry_action(T(("unknown",)), p, f, myF)

class Threatener(PolicyAgent):
    """Commits to b iff PA+1 proves the agent's response to Const_b (read as a threshold policy) pays it >= v_F;
    otherwise behaves as a copy of the agent (same policy table).  Rank 1: it reads the agent against a stone,
    not against itself, so there is no regress."""
    def __init__(self, b, tab, name=None, mix=None):
        super().__init__(tab, name or f"Threat{b}"); self.b, self.mix = b, mix   # mix = rho -> private mix instead of pure
        self._tcache = {}
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._tcache:
            rnd = ctx.rnd; b = self.b; nA = g.n(1 - role)
            V = lambda x: g.u(role, b, x)          # my payoff when I play b and the agent plays x
            pr, pc, uv, _ = fair_point(g, rnd.npub)
            myF, opF = (pr, pc) if role == 0 else (pc, pr); vF = uv[role]
            # the stone the agent is probed against
            if self.mix is None:
                stone = ctx.const(b); mypol = lambda c, f: b
            else:
                rho = self.mix; jj = round(rho * rnd.m)
                mypol = lambda c, f, jj=jj: b if f < jj else (b + 1) % g.n(role)
                stone = RPolicy(lambda p, c, f: mypol(c, f), f"Mix{b}@{rho}")
            probe_base = (opp[0], stone, 1 - role)
            my_other = (lambda c, f: mypol(c, f))
            conds = []
            # every threshold form of the agent's response; the agent's payoff-to-me is averaged over MY own mix too
            forms = [(x, x, rnd.m) for x in range(nA)] + [(x, y, j) for x in range(nA) for y in range(nA) if x != y for j in range(1, rnd.m)]
            for (x, y, j) in forms:
                if self.mix is None:
                    ev = (j / rnd.m) * V(x) + (1 - j / rnd.m) * V(y)
                else:
                    draws = [(c, f) for c in range(rnd.k) for f in range(rnd.m)]
                    ev = sum((j / rnd.m) * g.u(role, my_other(c, f), x) + (1 - j / rnd.m) * g.u(role, my_other(c, f), y) for c, f in draws) / len(draws)
                if ev >= vF - 1e-9:
                    body = And(*[Var((probe_base[0], probe_base[1], probe_base[2], p, c, f), x if f < j else y)
                                 for p in range(rnd.npub) for c in range(rnd.k) for f in range(rnd.m)])
                    conds.append(And(Not(Box(Bot(), 3)), Box(body, 1)))
            commit = Or(*conds) if conds else Bot()
            self._tcache[(me, opp)] = (commit, mypol)
        commit, mypol = self._tcache[(me, opp)]; p, c, f = r
        dl, d = PolicyAgent.program(self, g, role, me, opp, r, ctx)
        return [(commit, mypol(c, f))] + dl, d

def population(g, rnd, w, seat):
    """Opponents for the agent in `seat`, as (weight, kind, factory(tab)); kinds name the opponent's own action b."""
    pop = []; oseat = 1 - seat; nO = g.n(oseat)
    pr, pc, uv, _ = fair_point(g, rnd.npub)
    mm = (max(range(g.n(0)), key=lambda x: (min(g.u(0, x, y) for y in range(g.n(1))), -x)),
          max(range(g.n(1)), key=lambda x: (min(g.u(1, x, y) for y in range(g.n(0))), -x)))
    for b in range(nO):
        pop.append((w.get("stone", 0), ("stone", b), lambda tab, b=b: RConst(b, f"Const{b}")))
        pop.append((w.get("threat", 0), ("threat", b), lambda tab, b=b: Threatener(b, tab)))
        for rho in w.get("rhos", ()):
            pop.append((w.get("mix", 0), ("mix", b, rho), lambda tab, b=b, rho=rho: RPolicy(lambda p, c, f, j=round(rho * rnd.m): b if f < j else (b + 1) % nO, f"Mix{b}@{rho}")))
            pop.append((w.get("mixthreat", 0), ("mixthreat", b, rho), lambda tab, b=b, rho=rho: Threatener(b, tab, f"MixThreat{b}@{rho}", mix=rho)))
    pop.append((w.get("fair", 0), ("fairbot",), lambda tab: RFairBot((pr, pc), mm, "FB-F")))
    pop.append((w.get("fair", 0), ("prudentbot",), lambda tab: RPrudentBot((pr, pc), mm, "PB-F")))
    pop.append((w.get("copy", 0), ("copy",), None))
    return [x for x in pop if x[0] > 0]

def situations(g, rnd, seat):
    nB = g.n(1 - seat)
    # search order: what to do about commitments first (the exploit entries only pay off once the agent's own answer
    # to a commitment is no longer one a copy could profit from committing against)
    return [("commit", b) for b in range(nB)] + [("unknown",)] + [("recip",)] + [("exploit", b) for b in range(nB)]

def candidates(sit, g, rnd, seat):
    nA = g.n(seat)
    if sit[0] == "exploit": return list(range(nA))
    if sit[0] == "recip": return ["F"] + list(range(nA))
    return [(x, x, rnd.m) for x in range(nA)] + [(x, y, j) for x in range(nA) for y in range(nA) if x != y for j in range(1, rnd.m)]

def deps(kind):
    """Which table entries a match against this opponent kind can depend on."""
    if kind == "stone": return {"exploit", "commit", "unknown"}
    if kind == "mix": return {"exploit", "unknown"}
    if kind in ("threat", "mixthreat"): return {"exploit", "commit", "recip", "unknown"}
    if kind in ("fairbot", "prudentbot"): return {"exploit", "recip", "unknown"}
    return {"exploit", "commit", "recip", "unknown"}

_memo = {}
def match_ev(g, rnd, tab, kind, make, seat):
    """Agent with table `tab` in `seat` vs opponent `kind`; memoised on the entries the match can depend on."""
    rel = tuple(sorted((k, e) for k, e in tab.items() if k[1][0] in deps(kind[0])))
    key = (g.name, kind, seat, rel)
    if key in _memo: return _memo[key]
    ctx = RCtx(g, rnd)
    X = PolicyAgent(tab, "UDT")
    Y = PolicyAgent(tab, "UDT'") if kind[0] == "copy" else make(tab)
    A, B = (X, Y) if seat == 0 else (Y, X)
    px, py, s, ev = rplay(g, A, B, ctx, N=60)
    _memo[key] = (ev[seat], ev[1 - seat])
    return _memo[key]

def expected(g, rnd, tab, pops):
    """Prior-expected payoff; the agent is in each seat with probability 1/2."""
    tot = 0.0; W = 0.0
    for seat in (0, 1):
        for w, kind, make in pops[seat]:
            if kind[0] == "copy":
                if seat == 1: continue
                e0, e1 = match_ev(g, rnd, tab, kind, make, 0); ev = (e0 + e1) / 2; ww = 2 * w   # counted for both seats
            else:
                ev, _ = match_ev(g, rnd, tab, kind, make, seat); ww = w
            tot += ww * ev; W += ww
    return tot / W

def inits(g, rnd):
    """Starting tables: maxmin everywhere; best-respond everywhere; V5's rule."""
    pr, pc, uv, _ = fair_point(g, rnd.npub)
    T = {"maxmin": {}, "best-response": {}, "v5": {}}
    for seat in (0, 1):
        nA, nB = g.n(seat), g.n(1 - seat)
        mmact = max(range(nA), key=lambda x: (min(g.u(seat, x, y) for y in range(nB)), -x))
        br = lambda b: max(range(nA), key=lambda x: (g.u(seat, x, b), -x))
        vF = uv[1 - seat]
        def v5entry(b):
            a = br(b); v_give = g.u(1 - seat, b, a); a_r = min(range(nA), key=lambda x: (g.u(1 - seat, b, x), x)); v_ref = g.u(1 - seat, b, a_r)
            if v_give <= vF: return (a, a, rnd.m)
            if v_ref >= vF: return (a_r, a_r, rnd.m)
            thr = (vF - v_ref) / (v_give - v_ref); j = max(i for i in range(rnd.m + 1) if i / rnd.m < thr)
            return (a, a_r, j)
        for sit in situations(g, rnd, seat):
            k = (seat, sit)
            T["maxmin"][k] = mmact if sit[0] == "exploit" else "F" if sit[0] == "recip" else (mmact, mmact, rnd.m)
            T["best-response"][k] = br(sit[1]) if sit[0] == "exploit" else "F" if sit[0] == "recip" else (br(sit[1]), br(sit[1]), rnd.m) if sit[0] == "commit" else (mmact, mmact, rnd.m)
            T["v5"][k] = br(sit[1]) if sit[0] == "exploit" else "F" if sit[0] == "recip" else v5entry(sit[1]) if sit[0] == "commit" else (mmact, mmact, rnd.m)
    return T

def optimise(g, rnd, w, init=None, passes=3, log=print):
    pops = {seat: population(g, rnd, w, seat) for seat in (0, 1)}
    tab = dict(init) if init else inits(g, rnd)["maxmin"]
    best = expected(g, rnd, tab, pops)
    log(f"init EU {best:.4f}")
    for ps in range(passes):
        changed = False
        for seat in (0, 1):
            for sit in situations(g, rnd, seat):
                k = (seat, sit); cur = tab[k]; cbest, ebest = cur, best
                for e in candidates(sit, g, rnd, seat):
                    if e == cur: continue
                    tab[k] = e
                    eu = expected(g, rnd, tab, pops)
                    if eu > ebest + 1e-9: cbest, ebest = e, eu
                tab[k] = cbest
                if cbest != cur: changed = True; best = ebest; log(f"  pass {ps} seat {seat} {sit}: {cur} -> {cbest}   EU {best:.4f}")
        if not changed: break
    return tab, best, pops

def search(g, rnd, w, passes=3, log=lambda *a: None):
    """Best table over the three starting points."""
    best = None
    for name, init in inits(g, rnd).items():
        tab, eu, pops = optimise(g, rnd, w, init=init, passes=passes, log=log)
        if best is None or eu > best[1] + 1e-9: best = (tab, eu, name, pops)
    return best

def describe(g, rnd, tab):
    out = []
    for (seat, sit), e in tab.items():
        acts = g.acts[seat]; oacts = g.acts[1 - seat]
        if e == "F": d = "fair point F"
        elif isinstance(e, int): d = acts[e]
        else:
            x, y, j = e; d = acts[x] if j == rnd.m else f"{acts[x]} w.p. {j/rnd.m:.2f}, else {acts[y]}"
        label = {"exploit": lambda: f"opponent plays {oacts[sit[1]]} even against its exploiter",
                 "recip": lambda: "opponent reciprocates F",
                 "commit": lambda: f"opponent committed to {oacts[sit[1]]}",
                 "unknown": lambda: "nothing provable"}[sit[0]]()
        out.append(f"  seat {seat} ({'row' if seat == 0 else 'col'}): {label:48s} -> {d}")
    return "\n".join(out)
