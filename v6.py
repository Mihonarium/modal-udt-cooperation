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
  D'  unreadable opponent: the threat-resistant response, not maxmin.  Treat the opponent as committed to the action
      b* it would profit most from committing to against a best-responder, and apply C's rule to b*.  (In the PD
      b* = D and the answer is D; in Chicken b* = Straight and the answer is Swerve 0.9 / Straight 0.1, so an
      unreadable non-swerver ends below its fair payoff; in the Ultimatum, as responder, the threat-resistant
      acceptance rule.)
  No level-0 rock.  The agent is verifiable to every PA-reasoner; it takes the rock payoff from every reciprocator
  that gives in to rocks (B' refuses them, C answers their fallback) and from every rock-giver reading in PA+2 or
  stronger; a PA-level reader that punishes non-rocks is answered as a commitment.  V5R is the variant with the
  level-0 rock (wins that case, loses the PA-level reciprocator that punishes non-cooperators).
"""
from rmodal import *
from v5 import fair_point, maxmin_val, KMAX

class V6(RAgent):
    def __init__(self, name="V6", fair=None, kmax=KMAX, read="threshold"):
        super().__init__(name); self.fair, self.kmax, self.read = fair, kmax, read
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
        # D': the most profitable commitment for the opponent against a best-responder, answered by C's rule
        D = {}
        for p in range(rnd.npub):
            bstar = max(range(nB), key=lambda b: (V(max(range(nA), key=lambda x: (U(x, b), -x)), b), -b))
            D[p] = self.respond(g, role, [1.0 if x == bstar else 0.0 for x in range(nB)], myF(p), rnd)
        return dict(B=B, C=C, D=D, myF=myF)
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._cache: self._cache[(me, opp)] = self.build(g, role, me, opp, ctx)
        s = self._cache[(me, opp)]; p, c, f = r
        dl = [(s["B"], s["myF"](p))]
        dl += [(cond, a_star if f < pm else a_ref) for _, cond, a_star, a_ref, pm in s["C"][p]]
        a_star, a_ref, pm = s["D"][p]
        return dl, (a_star if f < pm else a_ref)
