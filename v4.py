"""Version 4: V3-B (cooperative/neutral checks first, exploitative last) plus a payoff-derived
third-party probe, making the agent rank 1 (as A2 Thm 4.10 requires for exploiting CooperateBot).

Outcome tiers (m = pure maxmin values) as in v3.py: coop / neutral / exploit.
For a cooperative outcome o = (a, b) with my utility u:
  a_ex(b)  = my best response to b (lowest index on ties); Ex_b = constant agent playing a_ex(b) in my seat.
  If U(a_ex(b), b) > U(a, b) (exploiting b is possible), the check is
      Box(I play a -> my payoff >= u)  AND  Box_p(not [opponent plays b against Ex_b])        (probe in PA+p)
  otherwise just the first conjunct (nothing to exploit, so no probe).
Order (variant `order`):
  'coop-exploit-neutral' : coop checks (best u first), then exploit checks, then neutral checks;
  'coop-neutral-exploit' : V3-B order (exploit last).
Exploit checks: Box_1(I play a -> my payoff >= u) ; with gate=True they also require that some probe failed:
      not Box_p(not [opp plays b against Ex_b]) for some cooperative o=(a,b) with an exploit available.
Checks below my maxmin are dropped; fallback = maxmin action. So the agent never gets below its maxmin
(soundness of PA+k)."""
from modal import *

class V4(Agent):
    def __init__(self, name="V4", probe=1, order="coop-exploit-neutral", gate=False, rev=False):
        super().__init__(name); self.probe, self.order, self.gate, self.rev = probe, order, gate, rev
        self._consts = {}
    def const(self, a):
        if a not in self._consts: self._consts[a] = Const(a, f"{self.name}-Ex{a}")
        return self._consts[a]
    def program(self, g, role, me, opp, ctx):
        nA, nB = g.n(role), g.n(1 - role)
        acts = list(range(nA))[::-1] if self.rev else list(range(nA))
        U = lambda a, b: g.u(role, a, b); V = lambda a, b: g.u(1 - role, b, a)
        mm = lambda r: max(min(g.u(r, x, y) for y in range(g.n(1 - r))) for x in range(g.n(r)))
        m_me, m_op = mm(role), mm(1 - role)
        best = lambda b: max(range(nA), key=lambda x: (U(x, b), -x))
        groups = {"coop": [], "neutral": [], "exploit": []}
        probes = []
        for a in acts:
            for b in range(nB):
                u, v = U(a, b), V(a, b)
                if u < m_me: continue
                t = "exploit" if v < m_op else ("coop" if (u > m_me or v > m_op) else "neutral")
                groups[t].append((u, a, b))
        def ge(a, u):
            return Box(Imp(Var(me, a), Or(*[Var(opp, y) for y in range(nB) if U(a, y) >= u])))
        dl, seen = [], set()
        for u, a, b in sorted(groups["coop"], key=lambda c: (-c[0], acts.index(c[1]), c[2])):
            ax = best(b)
            if U(ax, b) > U(a, b):
                ex = self.const(ax)
                pr = Box(Not(Var((opp[0], ex, 1 - role), b)), self.probe)
                probes.append(pr)
                cond = And(ge(a, u), pr)
            else:
                cond = ge(a, u)
            dl.append((cond, a))
        def add(group, theory):
            for u, a, b in sorted(group, key=lambda c: (-c[0], acts.index(c[1]))):
                if (u, a, theory) in seen: continue
                seen.add((u, a, theory))
                c = ge(a, u) if theory == 0 else Box(ge(a, u).x, 1)
                if theory == 1 and self.gate and probes:
                    c = And(Or(*[Not(p) for p in probes]), c)
                dl.append((c, a))
        if self.order == "coop-exploit-neutral":
            add(groups["exploit"], 1); add(groups["neutral"], 0)
        else:
            add(groups["neutral"], 0); add(groups["exploit"], 1)
        maxmin_a = max(range(nA), key=lambda x: (min(U(x, y) for y in range(nB)), -x))
        return dl, maxmin_a
