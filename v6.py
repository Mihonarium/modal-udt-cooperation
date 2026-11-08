"""V6: the simple agent.  No exploit tier.

  B'  reciprocate (PrudentBot-shaped, one positive condition):
        Box_0( I play F at all my keys -> the opponent plays F at all its keys )
        and, for every opponent action b that a best response a would exploit for more than u_F,
        Box_2( the opponent does NOT play b at every key against Const_a )          -> play F(r_pub)
      The second conjunct is PrudentBot's "defects against DefectBot": a reciprocator that would give in to a rock is
      not cooperated with; it then falls back, and tier C answers the fallback.  It is a positive provability
      claim, so an opponent reasoning in PA can verify that we cooperate (no "my exploit search fails" to prove).
  C   answer a commitment, as V5: Con_k and Box_k(opponent plays sigma at every key of this r_pub) -> best-respond
      if that leaves the committer at or below v_F, else give in with probability p (largest grid value keeping the
      committer strictly below v_F) and refuse otherwise.  A pushover (CooperateBot) is a committed opponent.
  D'  unreadable opponent: the constrained maxmin, not maxmin and not a best response.  A distribution d over my
      actions (on the private-draw grid) such that every opponent action b gets at most its fair payoff against d,
      strictly less for a threat (a b whose best response would hand it more than fair) where that is feasible; among
      those, the one that lexicographically maximises my guaranteed payoff (worst case over b first, then the next
      worst, ...).  Nothing is assumed about an opponent we cannot read, and no behaviour we cannot read pays more
      than being fair.  In the PD this is D; in Chicken Swerve 0.9 / Straight 0.1 (an unreadable non-swerver ends
      below fair); in the Stag Hunt Hare (not Stag: a default of Stag gets 0 against an unreadable Hare-player); as
      Ultimatum responder the offer-by-offer acceptance rule.  Falls back to answering the opponent's most profitable
      commitment b* with C's rule if nothing satisfies the constraints.
  Rock (first in the list, in games that pass the gate; absent elsewhere):
        Box_0( the opponent plays b at every key against Const_a ) and Box_0( the opponent plays b at every key against me )
                                                                                     -> play a
      for the exploitable (a, b) with the largest payoff.  Unguarded, so it passes vacuously at level 0: the agent
      opens with a and is a PA-provable rock.  Against "swerve iff PA proves the opponent goes Straight, else
      Straight" Löb closes the loop and it swerves.  The gate (matrix-only, both players compute it): rock-safe for
      both seats (a against the opponent's maxmin action pays at least fair, so a reciprocator that sees the rock and
      falls back costs nothing), not constant-sum, and copies of the rock agent still reach the fair point in this
      game.  Chicken passes; the PD, Stag Hunt, BoS, coordination games and Matching Pennies do not.  The cost is a
      PA-level reciprocator whose fallback is the threat action: it reads the rock as a non-cooperator and the agent
      gives in to its fallback.
"""
from rmodal import *
from v5 import fair_point, maxmin_val, KMAX

class V6(RAgent):
    def __init__(self, name="V6", fair=None, kmax=KMAX, read="threshold", rock="auto"):
        super().__init__(name); self.fair, self.kmax, self.read, self.rock = fair, kmax, read, rock
        self._consts, self._cache, self._fp = {}, {}, {}
    def const(self, a):
        if a not in self._consts: self._consts[a] = RConst(a, f"{self.name}-Rock{a}")
        return self._consts[a]
    def fairpoint(self, g, ctx):
        if g.name not in self._fp: self._fp[g.name] = (self.fair or fair_point)(g, ctx.rnd.npub)
        return self._fp[g.name]
    def policies(self, nB, rnd):
        if rnd.k == 1:
            forms = [(x, x, rnd.m) for x in range(nB)]
            if self.read == "threshold":
                forms += [(x, y, j) for x in range(nB) for y in range(nB) if x != y for j in range(1, rnd.m)]
            return [lambda c, f, x=x, y=y, j=j: x if f < j else y for x, y, j in forms]
        return [lambda c, f, s=s: s[c] for s in product(range(nB), repeat=rnd.k)]
    _gate = {}
    def gate(self, g, rnd):
        from v5 import rock_safe, constant_sum
        key = (g.name, rnd.npub, rnd.k, rnd.m, self.fair)
        if key not in V6._gate:
            uv = (self.fair or fair_point)(g, rnd.npub)[2]
            ok = rock_safe(g, 0, uv) and rock_safe(g, 1, uv) and not constant_sum(g)
            if ok:
                ctx = RCtx(g, rnd); X = V6("rock-test", fair=self.fair, rock="always"); Y = V6("rock-test'", fair=self.fair, rock="always")
                px, py, st, ev = rplay(g, X, Y, ctx, N=60)
                ok = abs(ev[0] - uv[0]) < 1e-9 and abs(ev[1] - uv[1]) < 1e-9
            V6._gate[key] = ok
        return V6._gate[key]
    def respond(self, g, role, q, myF_p, rnd):
        """C's rule against a distribution q over opponent actions: (a_star, a_ref, give-in count out of M)."""
        nA, nB = g.n(role), g.n(1 - role)
        U = lambda a, b: g.u(role, a, b); V = lambda a, b: g.u(1 - role, b, a)
        vF = self.fairpoint(g, self._ctx)[2][1 - role]
        myev = lambda a: sum(q[b] * U(a, b) for b in range(nB)); opev = lambda a: sum(q[b] * V(a, b) for b in range(nB))
        a_star = max(range(nA), key=lambda a: (myev(a), a == myF_p, -a)); v_give = opev(a_star)
        a_ref = min(range(nA), key=lambda a: (opev(a), -myev(a), a != myF_p, a)); v_ref = opev(a_ref)
        if v_give <= vF: return a_star, a_star, rnd.m
        if v_ref >= vF: return a_ref, a_ref, rnd.m
        thr = (vF - v_ref) / (v_give - v_ref)
        return a_star, a_ref, max(i for i in range(rnd.m + 1) if i / rnd.m < thr)
    _dm = {}
    def default_mix(self, g, role, myF_p, opF_p, rnd):
        ck = (g.name, role, myF_p, opF_p, rnd.m, self.fair)
        if ck not in V6._dm: V6._dm[ck] = self._default_mix(g, role, myF_p, opF_p, rnd)
        return V6._dm[ck]
    def _default_mix(self, g, role, myF_p, opF_p, rnd):
        """D': counts over my actions summing to M (the fine private draw picks one), see the module docstring.
        Objective, in order: my guaranteed payoff (min over the opponent's actions); my payoff if the opponent plays
        its fair action; my average payoff over its actions; the opponent's total payoff over its actions, lower
        first (unreadable behaviour is rewarded as little as possible); the weight on my fair action.  (Pure
        lexicographic maxmin is degenerate when some opponent action zeroes every default, e.g. a responder who
        rejects everything: it would then optimise against the next-greediest responder and offer 9 half the time.
        'Guarantee first, then assume fairness' offers 5.)
        Exact by enumeration of the grid for small games (2x2, 3x3, ...); hill-climbing from a few starts for medium
        ones (the 11-offer Ultimatum); the b* rule (None here) for games too large for pure Python."""
        nA, nB, M = g.n(role), g.n(1 - role), rnd.m
        Ur = [[g.u(role, a, b) for b in range(nB)] for a in range(nA)]           # my payoff rows
        Vr = [[g.u(1 - role, b, a) for b in range(nB)] for a in range(nA)]       # the opponent's payoff, by my action
        vF = self.fairpoint(g, self._ctx)[2][1 - role]
        threat = [Vr[max(range(nA), key=lambda a: (Ur[a][b], -a))][b] > vF + 1e-9 for b in range(nB)]
        lim = [M * (vF - 1e-9) if threat[b] else M * (vF + 1e-9) for b in range(nB)]   # strict for threats
        lim_lax = [M * (vF + 1e-9)] * nB
        def sums(d):   # (opponent's payoff sums, my payoff sums) over b, scaled by M
            so = [sum(d[a] * Vr[a][b] for a in range(nA) if d[a]) for b in range(nB)]
            sm = [sum(d[a] * Ur[a][b] for a in range(nA) if d[a]) for b in range(nB)]
            return so, sm
        def feasible(so, L): return all(so[b] <= L[b] for b in range(nB))
        def key(d, so, sm):
            return (round(min(sm), 6), round(sm[opF_p], 6), round(sum(sm), 6), -round(sum(so), 6), d[myF_p])
        from math import comb
        small = comb(M + nA - 1, nA - 1) <= 20000
        if not small and nA * nB * M > 200000: return None   # too large even to hill-climb in pure Python: b* rule
        def compositions(n, k):
            if k == 1: yield (n,); return
            for i in range(n + 1):
                for rest in compositions(n - i, k - 1): yield (i,) + rest
        def climb(d, so, sm, L):
            """Hill-climb from d by moving single units between actions (large games; exact for small ones is
            unnecessary).  Not guaranteed optimal, but feasible and never worse than the start."""
            d = list(d); k0 = key(d, so, sm); improved = True
            while improved:
                improved = False
                for a in range(nA):
                    if d[a] == 0: continue
                    for a2 in range(nA):
                        if a2 == a: continue
                        so2 = [so[b] - Vr[a][b] + Vr[a2][b] for b in range(nB)]
                        if not feasible(so2, L): continue
                        sm2 = [sm[b] - Ur[a][b] + Ur[a2][b] for b in range(nB)]
                        d[a] -= 1; d[a2] += 1; k2 = key(d, so2, sm2)
                        if k2 > k0: k0, so, sm, improved = k2, so2, sm2, True
                        else: d[a] += 1; d[a2] -= 1
            return k0, tuple(d)
        for L in (lim, lim_lax):
            best = None
            if small:
                for d in compositions(M, nA):
                    so, sm = sums(d)
                    if not feasible(so, L): continue
                    k = key(d, so, sm)
                    if best is None or k > best[0]: best = (k, d)
            else:
                starts = [tuple(M if a == myF_p else 0 for a in range(nA))]
                mm = max(range(nA), key=lambda a: (min(Ur[a]), -a)); starts.append(tuple(M if a == mm else 0 for a in range(nA)))
                bstar = max(range(nB), key=lambda b: (Vr[max(range(nA), key=lambda x: (Ur[x][b], -x))][b], -b))
                a_star, a_ref, pm = self.respond(g, role, [1.0 if x == bstar else 0.0 for x in range(nB)], myF_p, rnd)
                d = [0] * nA; d[a_star] += pm; d[a_ref] += M - pm; starts.append(tuple(d))
                starts += [tuple(M if a == x else 0 for a in range(nA)) for x in range(nA) if x not in (myF_p, mm)]
                tried = 0
                for d in starts:
                    so, sm = sums(d)
                    if not feasible(so, L): continue
                    k = climb(d, so, sm, L); tried += 1
                    if best is None or k > best: best = k
                    if tried >= 3: break
            if best is not None: return list(best[1])
        return None
    def build(self, g, role, me, opp, ctx):
        self._ctx = ctx; rnd = ctx.rnd; nA, nB = g.n(role), g.n(1 - role)
        U = lambda a, b: g.u(role, a, b); V = lambda a, b: g.u(1 - role, b, a)
        pr, pc, uv, _ = self.fairpoint(g, ctx)
        myF, opF = (pr, pc) if role == 0 else (pc, pr); uF, vF = uv[role], uv[1 - role]
        # B'
        probes = []
        for b in range(nB):
            a = max(range(nA), key=lambda x: (U(x, b), -x))
            if U(a, b) > uF:
                # read in PA+2: at level 1 an opponent facing the rock has not yet read it (its own commitment tier is
                # consistency-guarded and first fires at level 2) and plays its default, which can coincide with b
                probes.append(Box(Not(ctx.plays((opp[0], self.const(a), 1 - role), lambda p, b=b: b)), 2))
        B = And(Box(Imp(ctx.plays(me, myF), ctx.plays(opp, opF))), *probes)
        # rock
        R = []
        if self.rock == "always" or (self.rock == "auto" and self.gate(g, rnd)):
            best = None
            for b in range(nB):
                a = max(range(nA), key=lambda x: (U(x, b), -x))
                if U(a, b) > uF and (best is None or U(a, b) > best[0]): best = (U(a, b), a, b)
            if best:
                _, a, b = best
                R.append((And(Box(ctx.plays((opp[0], self.const(a), 1 - role), lambda p, b=b: b), 0),
                              Box(ctx.plays(opp, lambda p, b=b: b), 0)), a))
        # C
        con = {k: Not(Box(Bot(), k)) for k in range(1, self.kmax + 1)}
        C = {}
        for p in range(rnd.npub):
            lst = []
            for sigma in self.policies(nB, rnd):
                draws = [(c, f) for c in range(rnd.k) for f in range(rnd.m)]
                q = [sum(sigma(c, f) == b for c, f in draws) / len(draws) for b in range(nB)]
                a_star, a_ref, pm = self.respond(g, role, q, myF(p), rnd)
                body = And(*[Var((opp[0], opp[1], opp[2], p, c, f), sigma(c, f)) for c, f in draws])
                for k in range(1, self.kmax + 1): lst.append((k, And(con[k], Box(body, k)), a_star, a_ref, pm))
            lst.sort(key=lambda t: t[0]); C[p] = lst
        # D': the constrained maxmin as counts over my actions; fallback: the opponent's most profitable commitment
        # b* against a best-responder, answered by C's rule
        D = {}
        for p in range(rnd.npub):
            d = self.default_mix(g, role, myF(p), opF(p), rnd)
            if d is None:
                bstar = max(range(nB), key=lambda b: (V(max(range(nA), key=lambda x: (U(x, b), -x)), b), -b))
                a_star, a_ref, pm = self.respond(g, role, [1.0 if x == bstar else 0.0 for x in range(nB)], myF(p), rnd)
                d = [pm if a == a_star else 0 for a in range(nA)]; d[a_ref] += rnd.m - pm
            D[p] = d
        return dict(B=B, C=C, D=D, R=R, myF=myF)
    @staticmethod
    def pick(d, f):
        """The action the fine private draw f selects from counts d (summing to M)."""
        acc = 0
        for a, c in enumerate(d):
            acc += c
            if f < acc: return a
        return len(d) - 1
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._cache: self._cache[(me, opp)] = self.build(g, role, me, opp, ctx)
        s = self._cache[(me, opp)]; p, c, f = r
        dl = list(s["R"]) + [(s["B"], s["myF"](p))]
        dl += [(cond, a_star if f < pm else a_ref) for _, cond, a_star, a_ref, pm in s["C"][p]]
        return dl, self.pick(s["D"][p], f)
