"""Version 5: a payoff-reading modal agent with an outside source of randomness that
(A) exploits the opponent when it provably can,
(B) otherwise cooperates on a fair point F read off the payoff matrix (Löb-style, as FairBot),
(C) otherwise reads the opponent's committed policy and gives in to it probabilistically, with a
    probability chosen so that the opponent gets strictly less than its fair payoff in expectation
    (Samin, "An approach to giving in to threats without incentivizing them"; the Ultimatum /
    Chicken rule from planecrash), and
(D) otherwise plays its maxmin action.

Fair point.  F = the Nash bargaining solution over the convex hull of the pure outcomes, with the
pure maxmin values as the disagreement point, discretised: F is a mix of at most two pure
outcomes with weight a multiple of 1/NPUB, realised by the public draw r_pub.  Both players
compute the same F from the same matrix, so this is also the shared ordering the README asked for.

Checks, for my key (r_pub, r_c, r_f), with Con_k = not Box_k(bottom) (false at levels <= k of the chain,
so a PA+k check cannot fire vacuously) and strata k = 1..KMAX:
  A  for each opponent action b whose best response a gives me more than u_F (best b first), each k:
        Con_k and Box_k( the opponent plays b at every key against Const_a )            -> play a
     (the PrudentBot probe turned around: the opponent is exploitable if it plays b even against
     the constant agent that punishes b.  The implication form "I play a -> they play b" is not
     used because it passes vacuously whenever I don't play a.)
  B  Box_0( I play F at all my keys -> the opponent plays F at all its keys )            -> play F(r_pub)
  C  for each k, for each policy sigma the opponent might have at this r_pub:
        Con_k and Box_k( opponent plays sigma at every (r_pub, r_c, r_f) )
     -> respond to the distribution q(sigma): a* = my best response to q (ties -> my F action, then
        lowest index), v_give = opp payoff under a*, a_r = the action minimising the opponent's payoff
        against q (ties -> my payoff, then my F action), v_ref its payoff;
        if v_give <= v_F play a*;
        else give in (a*) when r_f < p*M, refuse (a_r) otherwise, p the largest multiple of 1/M
        strictly below (v_F - v_ref)/(v_give - v_ref)  (p = 0 if v_ref >= v_F).
     Policies read: with K = 1, "x when r_f < j else y" (what a stone, a FairBot or a V5 in tier C plays);
     with K > 1, a pure action per coarse draw r_c.
  D  maxmin action (ties -> my F action).
Strata: a PA+k check reads the chain from level k on, so an opponent whose policy settles only after
a few levels (another V5 reading me, say) is read at a higher stratum; checks are ordered A, B, then C
by stratum.  Tier C can take the agent below its own maxmin (it accepts a small probability of the
refused outcome, as the paper intends); tiers A, B, D cannot.
"""
from rmodal import *

KMAX = 6

def maxmin_val(g, role):
    return max(min(g.u(role, a, b) for b in range(g.n(1 - role))) for a in range(g.n(role)))

def fair_point(g, npub, disagreement=None):
    """Discretised Nash bargaining solution.  Returns (policy_row, policy_col, (uF_row, uF_col), desc);
    policies map r_pub -> action.  Mix of two pure outcomes o1 (weight w/npub) and o2."""
    outs = list(g.U)
    d = disagreement or (maxmin_val(g, 0), maxmin_val(g, 1))
    best = None
    for o1 in outs:
        for o2 in outs:
            for w in range(npub + 1):
                if o1 == o2 and w != npub: continue
                lam = w / npub
                u = lam * g.U[o1][0] + (1 - lam) * g.U[o2][0]
                v = lam * g.U[o1][1] + (1 - lam) * g.U[o2][1]
                if u < d[0] or v < d[1]: continue
                # ties among payoff-equal outcomes: prefer the pure outcome, then actions that leave the other
                # player the least to gain by deviating (in the Ultimatum normal form this picks the
                # "accept iff offer >= 5" threshold over "accept everything", which pays the same at the fair point)
                dev = lambda o: (max(g.U[(i, o[1])][0] for i in range(g.n(0))) + max(g.U[(o[0], j)][1] for j in range(g.n(1))))
                score = ((u - d[0]) * (v - d[1]), u + v, -abs(2 * w - npub), -(dev(o1) + dev(o2)),
                         -outs.index(o1), -outs.index(o2))
                if best is None or score > best[0]: best = (score, o1, o2, w, (u, v))
    assert best is not None  # the maxmin pair itself is always feasible
    _, o1, o2, w, uv = best
    pr = lambda p: o1[0] if p < w else o2[0]
    pc = lambda p: o1[1] if p < w else o2[1]
    desc = f"{o1}" if w == npub else (f"{o2}" if w == 0 else f"{w}/{npub} {o1} + {npub-w}/{npub} {o2}")
    return pr, pc, uv, desc

class V5(RAgent):
    def __init__(self, name="V5", tiers=("A", "B", "C"), fair=None, kmax=KMAX, read="threshold", patience=3):
        super().__init__(name); self.tiers, self.fair, self.kmax, self.read = tiers, fair, kmax, read
        self.patience = patience
        self._consts, self._cache, self._fp = {}, {}, {}
    def const(self, a):
        if a not in self._consts: self._consts[a] = RConst(a, f"{self.name}-Ex{a}")
        return self._consts[a]
    def fairpoint(self, g, ctx):
        if g.name not in self._fp:
            self._fp[g.name] = (self.fair or fair_point)(g, ctx.rnd.npub)
        return self._fp[g.name]
    def policies(self, nB, rnd):
        """Opponent policies read in tier C, each as a function (r_c, r_f) -> action."""
        if rnd.k == 1:
            forms = [(x, x, rnd.m) for x in range(nB)]
            if self.read == "threshold":   # read="pure" reads only pure policies (cheap for games with many actions)
                forms += [(x, y, j) for x in range(nB) for y in range(nB) if x != y for j in range(1, rnd.m)]
            return [lambda c, f, x=x, y=y, j=j: x if f < j else y for x, y, j in forms]
        return [lambda c, f, s=s: s[c] for s in product(range(nB), repeat=rnd.k)]
    def build(self, g, role, me, opp, ctx):
        """Conditions shared by all my keys against this opponent (formula objects are reused so the
        evaluator memoises each box once per level)."""
        rnd = ctx.rnd; nA, nB = g.n(role), g.n(1 - role)
        U = lambda a, b: g.u(role, a, b); V = lambda a, b: g.u(1 - role, b, a)
        pr, pc, uv, _ = self.fairpoint(g, ctx)
        myF, opF = (pr, pc) if role == 0 else (pc, pr)
        uF, vF = (uv[role], uv[1 - role])
        # guard for a PA+k check: Con_{k+D} = not Box_{k+D}(bottom), false at levels <= k+D, so the check can first
        # fire at level k+D+1, after the box has been read over levels k..k+D (D = patience): a one-level transient
        # in the opponent's play (its tier-B/D play before it has read me) is not mistaken for its policy.
        con = {k: Not(Box(Bot(), k + self.patience)) for k in range(1, self.kmax + 1)}
        # tier A waits one level longer than tier C: an opponent that is itself waiting to read a constant bot
        # plays its fallback for exactly `patience` levels, and that fallback must not be read as its policy
        conA = {k: Not(Box(Bot(), k + self.patience + 1)) for k in range(1, self.kmax + 1)}
        A = []
        for b in range(nB):
            a = max(range(nA), key=lambda x: (U(x, b), -x))
            if U(a, b) > uF:
                ex = self.const(a)
                for k in range(1, self.kmax + 1):
                    A.append((-U(a, b), k, And(conA[k], Box(ctx.plays((opp[0], ex, 1 - role), lambda p, b=b: b), k)), a))
        A.sort(key=lambda t: (t[1], t[0]))   # stratum first (so nothing fires late for a weaker reason), then best payoff
        B = Box(Imp(ctx.plays(me, myF), ctx.plays(opp, opF)))
        C = {}
        for p in range(rnd.npub):
            lst = []
            fme = myF(p)
            for sigma in self.policies(nB, rnd):
                draws = [(c, f) for c in range(rnd.k) for f in range(rnd.m)]
                q = [sum(sigma(c, f) == b for c, f in draws) / len(draws) for b in range(nB)]
                myev = lambda a: sum(q[b] * U(a, b) for b in range(nB))
                opev = lambda a: sum(q[b] * V(a, b) for b in range(nB))
                a_star = max(range(nA), key=lambda a: (myev(a), a == fme, -a))
                v_give = opev(a_star)
                a_ref = min(range(nA), key=lambda a: (opev(a), -myev(a), a != fme, a))
                v_ref = opev(a_ref)
                if v_give <= vF: pm = rnd.m
                elif v_ref >= vF: pm = 0
                else:
                    thr = (vF - v_ref) / (v_give - v_ref)
                    pm = max(i for i in range(rnd.m + 1) if i / rnd.m < thr)
                body = And(*[Var((opp[0], opp[1], opp[2], p, c, f), sigma(c, f)) for c, f in draws])
                for k in range(1, self.kmax + 1):
                    lst.append((k, And(con[k], Box(body, k)), a_star, a_ref, pm))
            lst.sort(key=lambda t: t[0])
            C[p] = lst
        mm = maxmin_val(g, role)
        mmact = max(range(nA), key=lambda a: (min(U(a, b) for b in range(nB)), a == myF(0), -a))
        return dict(A=A, B=B, C=C, myF=myF, uF=uF, vF=vF, maxmin=mmact)
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._cache: self._cache[(me, opp)] = self.build(g, role, me, opp, ctx)
        s = self._cache[(me, opp)]; p, c, f = r
        dl = []
        if "A" in self.tiers: dl += [(cond, a) for _, _, cond, a in s["A"]]
        if "B" in self.tiers: dl.append((s["B"], s["myF"](p)))
        if "C" in self.tiers:
            dl += [(cond, a_star if f < pm else a_ref) for _, cond, a_star, a_ref, pm in s["C"][p]]
        return dl, s["maxmin"]
